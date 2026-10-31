"""G1.5: ui.json against app.json and analysis.json — references, walks, testids, states, language.

Pure check: no model, no network, no side effects. `check_ui` is reused by the ui stage
to validate its own patches before writing the artifact.
"""
import json
import re
from collections import deque
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from contracts.gates import Finding, GateResult
from contracts.stage import ContractError
from contracts.ui import (REQUIRED_STATES, ExpectStep, FillStep, GenRef, OpenStep, ParamRef, ScanStep, Screen,
                          SeedRef, TapStep, UiSpec, Walk)
from harness.fakes import workspace_path
from stages.ui.appview import AppView

SEED_REF = re.compile(r"^(?P<entity>[A-Z][A-Za-z0-9]*)\[(?P<index>\d+)\](\.(?P<field>[A-Za-z_][A-Za-z0-9_]*))?$")
CYRILLIC = re.compile(r"[А-Яа-яЁё]")
LATIN_WORD = re.compile(r"[A-Za-z]{2,}")
CYRILLIC_LANGS = {"ru", "uk", "be", "kk", "bg", "sr", "mk", "ky", "tg", "mn"}


class _Findings(list):
    def add(self, path: str, code: str, message: str, severity: str = "error") -> None:
        self.append(Finding(path=path, code=code, severity=severity, message=message))


def _load(workspace: Path, artifacts: dict[str, str], name: str) -> Any:
    if name not in artifacts:
        raise ContractError(f"G1.5: нет артефакта {name}")
    return json.loads(workspace_path(workspace, artifacts[name]).read_text(encoding="utf-8"))


def check(workspace: Path, artifacts: dict[str, str]) -> GateResult:
    app = _load(workspace, artifacts, "app")
    analysis = _load(workspace, artifacts, "analysis")
    try:
        raw_ui = _load(workspace, artifacts, "ui")
        findings = check_ui(UiSpec.model_validate(raw_ui), app, analysis)
    except (ValidationError, ValueError, OSError) as exc:
        first = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
        findings = [Finding(path="", code="CONTRACT_UI", severity="error",
                            message=f"ui.json не проходит схему: {first}")]
    return GateResult(gate="G1.5", passed=not any(f.severity == "error" for f in findings), findings=findings)


def check_ui(ui: UiSpec, raw_app: dict, analysis: dict) -> list[Finding]:
    app = AppView(raw_app)
    out = _Findings()
    _check_screens(ui, app, out)
    _check_navigation(ui, app, out)
    _check_testids(ui, out)
    _check_walks(ui, app, analysis, out)
    _check_language(ui, app.lang, out)
    return list(out)


# --- screens -----------------------------------------------------------------------------------

def _check_screens(ui: UiSpec, app: AppView, out: _Findings) -> None:
    for name, screen in ui.screens.items():
        p = f"screens.{name}"
        for role in screen.roles:
            if role not in app.roles:
                out.add(f"{p}.roles", "UI_REF_UNRESOLVED", f"Роль {role} не описана в app.json")
        if screen.source is not None:
            _check_source(screen, app, f"{p}.source", out)
        for i, widget in enumerate(screen.widgets):
            wp = f"{p}.widgets[{i}]"
            if widget.field is not None:
                definition = app.field(widget.field)
                if definition is None:
                    out.add(wp, "UI_REF_UNRESOLVED", f"Поле {widget.field} не существует")
                elif widget.kind in ("status", "timeline") and definition.get("type") != "state":
                    out.add(wp, "UI_REF_UNRESOLVED", f"Виджет {widget.kind} требует поле состояния, а {widget.field} — нет")
            if widget.query is not None and widget.query not in app.queries:
                out.add(wp, "UI_REF_UNRESOLVED", f"Query {widget.query} не существует")
            if widget.command is not None and not app.operation_exists(widget.command):
                out.add(wp, "UI_REF_UNRESOLVED", f"Команда {widget.command} не существует")
            for key in (widget.label, widget.group):
                if key is not None and key not in ui.copy_texts:
                    out.add(wp, "UI_REF_UNRESOLVED", f"Нет текста copy[{key}]")
        for i, flt in enumerate(screen.filters):
            if app.field(flt.field) is None:
                out.add(f"{p}.filters[{i}]", "UI_REF_UNRESOLVED", f"Поле {flt.field} не существует")
        for i, action in enumerate(screen.actions):
            ap = f"{p}.actions[{i}]"
            if not app.operation_exists(action.command):
                out.add(ap, "UI_REF_UNRESOLVED", f"Команда {action.command} не существует")
            if action.then is not None and action.then not in ui.screens:
                out.add(ap, "UI_REF_UNRESOLVED", f"Экран {action.then} не существует")
            if action.copy_key is not None and action.copy_key not in ui.copy_texts:
                out.add(ap, "UI_REF_UNRESOLVED", f"Нет текста copy[{action.copy_key}]")
        for event in screen.live:
            if not app.event_exists(event):
                out.add(f"{p}.live", "UI_REF_UNRESOLVED", f"Событие {event} не существует")
        for target in screen.nav:
            if target not in ui.screens:
                out.add(f"{p}.nav", "UI_REF_UNRESOLVED", f"Экран {target} не существует")
        if screen.has_data:
            missing = [s for s in REQUIRED_STATES[screen.platform] if not screen.states.get(s, "").strip()]
            if missing:
                out.add(f"{p}.states", "STATE_MISSING", f"Нет состояний: {', '.join(missing)}")


def _check_source(screen: Screen, app: AppView, path: str, out: _Findings) -> None:
    source = screen.source
    assert source is not None
    if source.query is not None and source.query not in app.queries:
        out.add(path, "UI_REF_UNRESOLVED", f"Query {source.query} не существует")
    if source.entity is not None and source.entity not in app.entities:
        out.add(path, "UI_REF_UNRESOLVED", f"Сущность {source.entity} не существует")
    if source.command is not None and source.command not in app.commands:
        out.add(path, "UI_REF_UNRESOLVED", f"Команда {source.command} не существует")
    for param in source.params or []:
        if param not in app.params:
            out.add(path, "UI_REF_UNRESOLVED", f"Параметр {param} не существует")


# --- navigation --------------------------------------------------------------------------------

def _check_navigation(ui: UiSpec, app: AppView, out: _Findings) -> None:
    for section, table in (("menus", ui.menus), ("home", ui.home)):
        for role, platforms in table.items():
            if role not in app.roles:
                out.add(f"{section}.{role}", "UI_REF_UNRESOLVED", f"Роль {role} не описана в app.json")
            for platform, value in platforms.items():
                for screen in [value] if isinstance(value, str) else value:
                    if screen not in ui.screens:
                        out.add(f"{section}.{role}.{platform}", "UI_REF_UNRESOLVED", f"Экран {screen} не существует")
                    elif ui.screens[screen].platform != platform:
                        out.add(f"{section}.{role}.{platform}", "UI_REF_UNRESOLVED",
                                f"Экран {screen} относится к платформе {ui.screens[screen].platform}")


def reachable(ui: UiSpec, role: str, platform: str) -> set[str]:
    """Screens a role can reach on a platform from its home screen and menu via nav and action.then."""
    def visible(name: str) -> bool:
        screen = ui.screens.get(name)
        return screen is not None and screen.platform == platform and role in screen.roles

    starts = [ui.home.get(role, {}).get(platform)] + ui.menus.get(role, {}).get(platform, [])
    queue = deque(s for s in starts if s and visible(s))
    seen = set(queue)
    while queue:
        screen = ui.screens[queue.popleft()]
        for target in screen.nav + [a.then for a in screen.actions if a.then]:
            if target not in seen and visible(target):
                seen.add(target)
                queue.append(target)
    return seen


# --- testids -----------------------------------------------------------------------------------

def _check_testids(ui: UiSpec, out: _Findings) -> None:
    owners: dict[str, str] = {}
    for name, screen in ui.screens.items():
        for testid in screen.testids():
            if testid in owners:
                out.add(f"screens.{name}", "TESTID_DUP", f"data-testid {testid} уже есть на экране {owners[testid]}")
            else:
                owners[testid] = name


# --- walks -------------------------------------------------------------------------------------

def _check_walks(ui: UiSpec, app: AppView, analysis: dict, out: _Findings) -> None:
    stories = {s["id"] for s in analysis.get("user_stories") or []}
    acceptance = {a["id"]: a for a in analysis.get("acceptance") or []}
    for story in sorted(stories - set(ui.walks)):
        out.add(f"walks.{story}", "WALK_MISSING", f"У {story} нет прохода по экранам")
    covered: set[str] = set()
    for story, walk in ui.walks.items():
        p = f"walks.{story}"
        if story not in stories:
            out.add(p, "UI_REF_UNRESOLVED", f"Пользовательской истории {story} нет в анализе")
        for ac in walk.covers:
            if ac not in acceptance:
                out.add(f"{p}.covers", "UI_REF_UNRESOLVED", f"Критерия {ac} нет в анализе")
        covered.update(walk.covers)
        _simulate(ui, app, walk, p, out)
    for ac_id, ac in acceptance.items():
        if ac.get("ui") and ac_id not in covered:
            out.add("walks", "AC_UI_UNCOVERED", f"{ac_id} проверяется через интерфейс, но ни один проход его не покрывает")


def _simulate(ui: UiSpec, app: AppView, walk: Walk, p: str, out: _Findings) -> None:
    if walk.role not in app.roles:
        out.add(f"{p}.role", "UI_REF_UNRESOLVED", f"Роль {walk.role} не описана в app.json")
        return
    reach = reachable(ui, walk.role, walk.platform)
    current: Screen | None = None
    current_name = ""
    for i, step in enumerate(walk.steps):
        sp = f"{p}.steps[{i}]"
        if isinstance(step, OpenStep):
            if not _enter(ui, walk, step.open, reach, sp, out):
                return
            current_name, current = step.open, ui.screens[step.open]
            continue
        if current is None:
            out.add(sp, "UI_REF_UNRESOLVED", "Проход должен начинаться с шага open")
            return
        if isinstance(step, (FillStep, ScanStep)):
            target = step.fill if isinstance(step, FillStep) else step.scan
            kinds = {"field", "file", "scan"} if isinstance(step, FillStep) else {"scan"}
            if not any(w.field == target and w.kind in kinds for w in current.widgets):
                out.add(sp, "UI_REF_UNRESOLVED", f"На экране {current_name} нет поля ввода {target}")
            _check_value(step.value, app, sp, out)
        elif isinstance(step, TapStep):
            if step.row is not None:
                _check_seed(step.row.seed, app, f"{sp}.row", out)
            if step.tap in ui.screens:
                if step.tap not in current.nav:
                    out.add(sp, "WALK_UNREACHABLE", f"С экрана {current_name} нет перехода на {step.tap}")
                    return
                if not _enter(ui, walk, step.tap, reach, sp, out):
                    return
                current_name, current = step.tap, ui.screens[step.tap]
                continue
            action = next((a for a in current.actions if a.command == step.tap), None)
            button = next((w for w in current.widgets if w.kind == "action_button" and w.command == step.tap), None)
            if action is None and button is None:
                out.add(sp, "UI_REF_UNRESOLVED", f"На экране {current_name} нет действия или экрана {step.tap}")
                continue
            if walk.role not in app.roles_for(step.tap):
                out.add(sp, "WALK_FORBIDDEN", f"Роли {walk.role} не разрешено {step.tap}")
            rejected = i + 1 < len(walk.steps) and isinstance(walk.steps[i + 1], ExpectStep) \
                and walk.steps[i + 1].expect.error is not None
            if action is not None and action.then and not rejected:
                current_name, current = action.then, ui.screens.get(action.then)
                if current is None:
                    return   # already reported as an unresolved reference
        elif isinstance(step, ExpectStep):
            expect = step.expect
            if expect.screen is not None and expect.screen != current_name:
                out.add(sp, "WALK_UNREACHABLE", f"Ожидается экран {expect.screen}, а после шагов открыт {current_name}")
            if expect.status is not None and expect.status not in app.states():
                out.add(sp, "UI_REF_UNRESOLVED", f"Состояния {expect.status} нет ни в одной машине")
            if expect.error is not None and expect.error not in app.hooks:
                out.add(sp, "UI_REF_UNRESOLVED", f"Хука {expect.error} нет в app.json")
            if expect.copy_key is not None and expect.copy_key not in ui.copy_texts:
                out.add(sp, "UI_REF_UNRESOLVED", f"Нет текста copy[{expect.copy_key}]")
            for testid in expect.visible:
                if testid not in current.testids():
                    out.add(sp, "UI_REF_UNRESOLVED", f"На экране {current_name} нет элемента {testid}")
            if expect.row is not None:
                _check_seed(expect.row.seed, app, f"{sp}.row", out)


def _enter(ui: UiSpec, walk: Walk, name: str, reach: set[str], path: str, out: _Findings) -> bool:
    screen = ui.screens.get(name)
    if screen is None:
        out.add(path, "UI_REF_UNRESOLVED", f"Экран {name} не существует")
        return False
    if walk.role not in screen.roles:
        out.add(path, "WALK_FORBIDDEN", f"Экран {name} недоступен роли {walk.role}")
        return False
    if name not in reach:
        out.add(path, "WALK_UNREACHABLE",
                f"Экран {name} недостижим для роли {walk.role} на платформе {walk.platform} от главного экрана")
        return False
    return True


def _check_value(value: Any, app: AppView, path: str, out: _Findings) -> None:
    if isinstance(value, SeedRef):
        _check_seed(value.seed, app, f"{path}.value", out)
    elif isinstance(value, ParamRef):
        if value.param not in app.params:
            out.add(f"{path}.value", "UI_REF_UNRESOLVED", f"Параметр {value.param} не существует")
    elif not isinstance(value, GenRef):
        out.add(f"{path}.value", "WALK_LITERAL", "Значение записано литералом; нужна ссылка на seed или params",
                severity="warning")


def _check_seed(ref: str, app: AppView, path: str, out: _Findings) -> None:
    match = SEED_REF.match(ref)
    if match is None:
        out.add(path, "UI_REF_UNRESOLVED", f"Неверная ссылка на сид {ref}")
        return
    rows = app.seed.get(match["entity"]) or []
    if int(match["index"]) >= len(rows):
        out.add(path, "UI_REF_UNRESOLVED", f"В сиде нет записи {match['entity']}[{match['index']}]")
    elif match["field"] and match["field"] not in app.fields(match["entity"]):
        out.add(path, "UI_REF_UNRESOLVED", f"У {match['entity']} нет поля {match['field']}")


# --- language ----------------------------------------------------------------------------------

def foreign_text(text: str, lang: str) -> bool:
    """True when the text is clearly not in lang: no letters of its script, only the other one."""
    cyrillic_lang = lang.split("-")[0].lower() in CYRILLIC_LANGS
    has_cyrillic = bool(CYRILLIC.search(text))
    if cyrillic_lang:
        return not has_cyrillic and bool(LATIN_WORD.search(text))
    return has_cyrillic


def _check_language(ui: UiSpec, lang: str, out: _Findings) -> None:
    texts = [(f"screens.{n}.title", s.title) for n, s in ui.screens.items()]
    texts += [(f"screens.{n}.states.{k}", v) for n, s in ui.screens.items() for k, v in s.states.items()]
    texts += [(f"copy.{k}", v) for k, v in ui.copy_texts.items()]
    for path, text in texts:
        if foreign_text(text, lang):
            out.add(path, "COPY_LANG", f"Текст «{text[:40]}» не на языке {lang}", severity="warning")
