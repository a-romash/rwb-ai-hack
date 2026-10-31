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
    match = re.fullmatch(r"([A-Za-z0-9_]+)\[(\d+)\](?:\.([A-Za-z0-9_]+))?", ref)
    rows = (app.get("seed") or {}).get(match.group(1), []) if match else []
    if not match or int(match.group(2)) >= len(rows):
        raise ContractError(f"Нет seed-значения {ref}")
    row = rows[int(match.group(2))]
    if match.group(3) is not None and row.get(match.group(3)) is None:
        raise ContractError(f"Нет seed-значения {ref}")
    return row if match.group(3) is None else row[match.group(3)]


# A generated value the form input accepts; inputs follow screen-page.ts input().
_GENERATED = {"datetime": "2030-01-01T10:00", "date": "2030-01-01", "int": "1", "decimal": "1", "money": "1", "number": "1"}


def _value(app: dict, value, field: str = ""):
    if isinstance(value, dict) and "seed" in value:
        return _seed(app, value["seed"])
    if isinstance(value, dict) and "param" in value:
        return ((app.get("params") or {}).get(value["param"]) or {}).get("value")
    if isinstance(value, dict) and "gen" in value:
        return _GENERATED.get(_field_type(app, field), "e2e-value")
    return value


def _widget(screen: dict, field: str, kinds: tuple[str, ...]) -> str:
    found = [w["testid"] for w in screen.get("widgets", []) if w.get("field") == field and w.get("kind") in kinds]
    if len(found) != 1:
        raise ContractError(f"Нет однозначного виджета {field}")
    return found[0]


def _field_type(app: dict, ref: str):
    """Type of Entity.field or Command.input."""
    owner, _, name = ref.partition(".")
    entity = ((app.get("entities") or {}).get(owner) or {}).get("fields") or {}
    command = ((app.get("commands") or {}).get(owner) or {}).get("input") or {}
    return (entity.get(name) or command.get(name) or {}).get("type")


def _row(app: dict, screen: dict, name: str, ref: str) -> str:
    """The list row of a seed record, found by the text it shows: a query filters and orders rows,
    so the seed index is not the row position."""
    record = _seed(app, ref)
    shown = [w["field"].split(".", 1)[1] for w in screen.get("widgets", []) if w.get("kind") == "field" and "." in w.get("field", "")]
    text = next((record[f] for f in shown if isinstance(record.get(f), str) and record[f]), None)
    rows = f"page.getByTestId({json.dumps(_kebab(name) + '.row')})"
    if text is None:
        raise ContractError(f"Строку {ref} на экране {name} не узнать: экран не показывает её текстовых полей")
    # Walks share the stand, so a record created by another walk may show the same text.
    return f"{rows}.filter({{hasText: {json.dumps(text, ensure_ascii=False)}}}).first()"


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
            value = _value(app, step.get("value"), step[kind])
            lines.append(f"await page.getByTestId({json.dumps(testid)}).fill({json.dumps(str(value), ensure_ascii=False)});")
        elif kind == "tap":
            target = step["tap"]
            actions = [a["testid"] for a in screen.get("actions", []) if a.get("command") == target]
            actions += [w["testid"] for w in screen.get("widgets", []) if w.get("kind") == "action_button" and w.get("command") == target]
            row = step.get("row")
            scope = "page"
            if row:
                scope = _row(app, screen, current, row["seed"])
            if len(actions) == 1:
                lines.append(f"await {scope}.getByTestId({json.dumps(actions[0])}).click();")
                if any(a.get("confirm") for a in screen.get("actions", []) if a.get("testid") == actions[0]):
                    lines.append('await page.getByTestId("confirm.ok").click();')
            elif target in screens and target in screen.get("nav", []):
                if row:
                    lines.append(f"await {scope}.click();")
                elif screens[target].get("pattern") != "detail":
                    # The screen's nav link carries the open record (?id=), a bare URL would lose it.
                    lines.append(f"await page.getByTestId({json.dumps(_kebab(current) + '.nav-' + target)}).click();")
                elif screen.get("pattern") == "list":
                    # A bare detail URL carries no id; any row of the list opens a real record.
                    lines.append(f"await page.getByTestId({json.dumps(_kebab(current) + '.row')}).first().click();")
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
                # An enum that is not a state machine field is drawn as a plain field and still shows the value.
                testids = testids or [w["testid"] for w in screen.get("widgets", []) if w.get("kind") == "field"
                                      and _field_type(app, w.get("field", "")) in ("enum", "state")]
                if not testids:
                    raise ContractError(f"На экране {current} нет виджета статуса")
                # Case is a wire detail: a spec may seed "Active" for the value "active".
                pattern = json.dumps(re.escape(expect["status"]))
                lines.append(f"await expect(page.getByTestId({json.dumps(testids[0])}).first()).toContainText(new RegExp({pattern}, 'i'));")
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
                lines.append(f"await expect({_row(app, screen, current, expect['row']['seed'])}).toBeVisible();")
        else:
            raise ContractError("Неподдерживаемый шаг UI")
    return lines


def generate(root, ui: dict, app: dict | None = None) -> tuple[list[str], dict[str, str]]:
    """Spec files written and walks skipped with the reason: one broken walk does not stop the rest."""
    files, skipped = [], {}
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
        try:
            lines += ["  " + line for line in _steps(walk, ui, app)]
        except ContractError as error:
            skipped[ident] = str(error)
            continue
        lines.append("});")
        relative = f"product/{target}/e2e/{ident}.spec.ts"
        path = workspace_path(root, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        files.append(relative)
    return files, skipped
