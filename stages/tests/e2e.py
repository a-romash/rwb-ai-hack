"""Compile ui.json walks (contracts/ui.py) into Playwright specs; selectors come from testids only.

Routes follow the scaffold: every screen is served at /<ScreenName> (admin-web generated routes).
A step that cannot be resolved to a known screen, testid or seed value stops the stage instead of
guessing a selector.
"""
import json
import re

from contracts.stage import ContractError
from harness.fakes import workspace_path


def _kebab(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "-", name).lower()


def _seed(app: dict, ref: str):
    """'Ticket[0]' or 'Ticket[0].title' from app.json seed."""
    match = re.fullmatch(r"([A-Za-z0-9_]+)\[(\d+)\](?:\.([a-z0-9_]+))?", ref)
    rows = (app.get("seed") or {}).get(match.group(1), []) if match else []
    if not match or int(match.group(2)) >= len(rows):
        raise ContractError(f"Нет seed-значения {ref}")
    row = rows[int(match.group(2))]
    return row if match.group(3) is None else row.get(match.group(3))


def _value(app: dict, value):
    if isinstance(value, dict) and "seed" in value:
        return _seed(app, value["seed"])
    if isinstance(value, dict) and "param" in value:
        return ((app.get("params") or {}).get(value["param"]) or {}).get("value")
    if isinstance(value, dict) and "gen" in value:
        return "e2e-value"
    return value


def _widget(screen: dict, field: str, kinds: tuple[str, ...]) -> str:
    found = [w["testid"] for w in screen.get("widgets", []) if w.get("field") == field and w.get("kind") in kinds]
    if len(found) != 1:
        raise ContractError(f"Нет однозначного виджета {field}")
    return found[0]


def _steps(walk: dict, ui: dict, app: dict) -> list[str]:
    screens = ui.get("screens", {})
    copy = ui.get("copy", {})
    current = None
    lines = []
    for step in walk.get("steps", []):
        kind = next((key for key in ("open", "fill", "tap", "scan", "expect") if key in step), None)
        if kind == "open":
            if step["open"] not in screens:
                raise ContractError(f"Неизвестный экран {step['open']}")
            current = step["open"]
            lines.append(f"await page.goto({json.dumps('/' + current)});")
            continue
        screen = screens.get(current) if current else None
        if screen is None:
            raise ContractError("Шаг прохода до открытия экрана")
        if kind in ("fill", "scan"):
            testid = _widget(screen, step[kind], ("field", "scan", "file"))
            value = _value(app, step.get("value"))
            lines.append(f"await page.getByTestId({json.dumps(testid)}).fill({json.dumps(str(value), ensure_ascii=False)});")
        elif kind == "tap":
            target = step["tap"]
            actions = [a["testid"] for a in screen.get("actions", []) if a.get("command") == target]
            actions += [w["testid"] for w in screen.get("widgets", []) if w.get("kind") == "action_button" and w.get("command") == target]
            row = step.get("row")
            scope = "page"
            if row:
                index = int(re.search(r"\[(\d+)\]", row["seed"]).group(1))
                scope = f"page.getByTestId({json.dumps(_kebab(current) + '.row')}).nth({index})"
            if len(actions) == 1:
                lines.append(f"await {scope}.getByTestId({json.dumps(actions[0])}).click();")
                if any(a.get("confirm") for a in screen.get("actions", []) if a.get("testid") == actions[0]):
                    lines.append('await page.getByTestId("confirm.ok").click();')
            elif target in screens and target in screen.get("nav", []):
                if row:
                    lines.append(f"await {scope}.click();")
                else:
                    lines.append(f"await page.goto({json.dumps('/' + target)});")
                current = target
            else:
                raise ContractError(f"Неоднозначное действие {target} на экране {current}")
            # `then` happens only on success; the walk states the next screen with expect.screen.
        elif kind == "expect":
            expect = step["expect"]
            if expect.get("screen"):
                current = expect["screen"]
                lines.append(f"await expect(page).toHaveURL(new RegExp({json.dumps('/' + current + '(?:[/?#]|$)')}));")
                screen = screens.get(current, screen)
            if expect.get("status"):
                testids = [w["testid"] for w in screen.get("widgets", []) if w.get("kind") == "status"]
                if not testids:
                    raise ContractError(f"На экране {current} нет виджета статуса")
                lines.append(f"await expect(page.getByTestId({json.dumps(testids[0])}).first()).toContainText({json.dumps(expect['status'])});")
            for testid in expect.get("visible", []):
                lines.append(f"await expect(page.getByTestId({json.dumps(testid)}).first()).toBeVisible();")
            if expect.get("copy"):
                text = copy.get(expect["copy"])
                if text is None:
                    raise ContractError(f"Нет текста {expect['copy']}")
                lines.append(f"await expect(page.getByText({json.dumps(text, ensure_ascii=False)})).toBeVisible();")
            if expect.get("error"):
                lines.append("await expect(page.getByRole('alert').first()).toBeVisible();")
            if expect.get("row"):
                lines.append(f"await expect(page.getByTestId({json.dumps(_kebab(current) + '.row')}).first()).toBeVisible();")
        else:
            raise ContractError("Неподдерживаемый шаг UI")
    return lines


def generate(root, ui: dict, app: dict | None = None) -> list[str]:
    files = []
    app = app or {}
    for ident, walk in (ui or {}).get("walks", {}).items():
        if not re.fullmatch(r"US-[0-9A-Za-z_-]+", ident):
            raise ContractError("Некорректный ID прохода")
        target = "mobile-web" if walk.get("platform") == "mobile" else "admin-web"
        lines = ["import {test, expect, devices} from '@playwright/test';"]
        if target == "mobile-web":
            lines.append("test.use({...devices['Pixel 7']});")
        title = " ".join("@" + ac for ac in walk.get("covers", [])) + " " + ident
        lines.append("test(" + json.dumps(title.strip()) + ", async ({page}) => {")
        # Demo sign-in: the app reads the role from localStorage and logs in through /api/auth/login.
        lines.append(f"  await page.addInitScript((role) => localStorage.setItem('role', role), {json.dumps(walk.get('role', ''))});")
        lines += ["  " + line for line in _steps(walk, ui, app)]
        lines.append("});")
        relative = f"product/{target}/e2e/{ident}.spec.ts"
        path = workspace_path(root, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        files.append(relative)
    return files
