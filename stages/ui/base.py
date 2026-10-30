"""A1: derive a valid base ui.json from app.json without the model.

Per entity: list + detail for roles that read it, form for roles that create or update it,
a form per command with input. Menus, home screens, states and testids follow fixed rules.
The model only refines this base afterwards (platforms, extra widgets, walks, texts).
"""
import re

from contracts.ui import REQUIRED_STATES, Action, Filter, Screen, Source, UiSpec, Widget, screen_kebab
from stages.ui.appview import AppView

LIST_FIELDS = 5     # columns of a base list
NO_LIST_TYPES = {"text", "json", "file", "geo_point", "geo_line", "geo_polygon"}
FILTER_TYPES = {"enum", "state", "bool"}

STATE_TEXTS = {
    "ru": {"loading": "Загрузка…", "empty": "Записей пока нет", "error": "Не удалось загрузить данные. Попробуйте ещё раз.",
           "forbidden": "У вас нет доступа к этому разделу", "offline": "Нет сети. Показаны последние загруженные данные."},
    "en": {"loading": "Loading…", "empty": "Nothing here yet", "error": "Could not load data. Please try again.",
           "forbidden": "You do not have access to this section", "offline": "Offline. Showing the last loaded data."},
}


def state_texts(lang: str, platform: str) -> dict[str, str]:
    texts = STATE_TEXTS.get(lang.split("-")[0].lower(), STATE_TEXTS["en"])
    return {state: texts[state] for state in REQUIRED_STATES[platform]}


def kebab(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", screen_kebab(name)).strip("-")


def _widget(app: AppView, entity: str, name: str, field: dict, prefix: str) -> Widget:
    kind = {"state": "status", "file": "file"}.get(field.get("type"), "field")
    if field.get("type") == "datetime" and name in app.timer_fields(entity):
        kind = "countdown"
    return Widget(kind=kind, field=f"{entity}.{name}", testid=f"{prefix}.{kebab(name)}")


def _commands(app: AppView, entity: str) -> list[str]:
    return [name for name, command in app.commands.items() if command.get("entity") == entity]


def _has_input(app: AppView, command: str) -> bool:
    return bool(app.commands[command].get("input"))


def derive_base(raw_app: dict) -> UiSpec:
    app = AppView(raw_app)
    lang = app.lang
    screens: dict[str, Screen] = {}

    for entity, spec in app.entities.items():
        label = spec.get("label") or entity
        readers = sorted(app.roles_for(f"{entity}.read"))
        writers = sorted(app.roles_for(f"{entity}.create") | app.roles_for(f"{entity}.update"))
        fields = app.fields(entity)
        commands = _commands(app, entity)
        live = sorted(app.events(entity))
        list_name, detail_name, form_name = f"{entity}List", f"{entity}Detail", f"{entity}Form"

        command_forms = {}
        for command in commands:
            roles = sorted(app.roles_for(command))
            if not _has_input(app, command) or not roles:
                continue
            name = f"{command}Form"
            prefix = kebab(name)
            command_forms[command] = name
            screens[name] = Screen(
                platform="web", roles=roles, pattern="form", title=command, source=Source(command=command),
                widgets=[Widget(kind="file" if f.get("type") == "file" else "field", field=f"{command}.{n}",
                                testid=f"{prefix}.{kebab(n)}")
                         for n, f in app.commands[command]["input"].items()],
                actions=[Action(command=command, testid=f"{prefix}.submit", then=detail_name if readers else None)],
                states=state_texts(lang, "web"))

        if readers:
            prefix = kebab(list_name)
            columns = [(n, f) for n, f in fields.items() if f.get("type") not in NO_LIST_TYPES][:LIST_FIELDS]
            screens[list_name] = Screen(
                platform="web", roles=readers, pattern="list", title=label, source=Source(entity=entity),
                widgets=[_widget(app, entity, n, f, prefix) for n, f in columns],
                filters=[Filter(field=f"{entity}.{n}", testid=f"{prefix}.filter-{kebab(n)}")
                         for n, f in fields.items() if f.get("type") in FILTER_TYPES],
                actions=[Action(command=c, testid=f"{prefix}.{kebab(c)}", confirm=True, then=detail_name)
                         for c in commands if not _has_input(app, c) and app.roles_for(c)],
                live=live, states=state_texts(lang, "web"),
                nav=[detail_name] + ([form_name] if writers else []))

            prefix = kebab(detail_name)
            widgets = [_widget(app, entity, n, f, prefix) for n, f in fields.items()]
            widgets += [Widget(kind="action_button", command=c, testid=f"{prefix}.{kebab(c)}")
                        for c in commands if app.roles_for(c)]
            state_field = next((n for n, f in fields.items() if f.get("type") == "state"), None)
            if state_field:
                widgets.append(Widget(kind="timeline", field=f"{entity}.{state_field}", testid=f"{prefix}.history"))
            screens[detail_name] = Screen(
                platform="web", roles=readers, pattern="detail", title=label, source=Source(entity=entity),
                widgets=widgets, live=live, states=state_texts(lang, "web"),
                nav=[command_forms[c] for c in commands if c in command_forms]
                    + ([form_name] if app.roles_for(f"{entity}.update") else []))

        if writers:
            prefix = kebab(form_name)
            by_commands = {n for c in commands for n in app.commands[c].get("input") or {}}
            editable = [(n, f) for n, f in fields.items()
                        if f.get("type") != "state" and not f.get("computed_by") and n not in by_commands]
            ops = [op for op in ("create", "update") if app.roles_for(f"{entity}.{op}")]
            screens[form_name] = Screen(
                platform="web", roles=writers, pattern="form", title=label, source=Source(entity=entity),
                widgets=[_widget(app, entity, n, f, prefix) for n, f in editable],
                actions=[Action(command=f"{entity}.{op}", testid=f"{prefix}.{op}", then=detail_name if readers else None)
                         for op in ops],
                states=state_texts(lang, "web"))

    menus: dict[str, dict] = {}
    home: dict[str, dict] = {}
    for role in app.roles:
        entries = [n for n, s in screens.items() if s.pattern == "list" and role in s.roles]
        if not entries:   # a role that only writes still needs an entry point
            entries = [n for n, s in screens.items() if s.pattern == "form" and role in s.roles
                       and s.source and s.source.kind == "entity"]
        if entries:
            menus[role] = {"web": entries}
            home[role] = {"web": entries[0]}

    return UiSpec(schema_version=1, screens=screens, menus=menus, home=home)
