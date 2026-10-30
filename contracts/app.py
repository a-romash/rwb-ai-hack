"""Контракт устройства приложения v1 (§3.6) и зависимости внутри app.json.

Структуры, для которых §3.6 даёт только пустой контейнер, сохраняются как
JSON-объекты. Это не добавляет полей в общий контракт. Семантику проверяет G1.
"""

from __future__ import annotations

import re
from collections import deque
from typing import Annotated, Literal, Self

from pydantic import Field, JsonValue, RootModel, StringConstraints, model_validator

from contracts.analysis import ContractModel, FieldType, ModuleName, Text

HookKind = Literal["validator", "calculator", "decider", "policy", "reaction"]
PermissionScope = Literal["own", "team", "all"]
NotificationChannel = Literal["web", "mobile", "email", "sms"]
OperationName = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z_][A-Za-z0-9_]*(?:\.(?:create|read|update|delete))?$"),
]


class MetaSection(ContractModel):
    name: Text
    title: Text
    lang: Text
    timezone: Text
    modules: list[ModuleName]


class Parameter(ContractModel):
    type: FieldType
    value: JsonValue
    traces: list[Text]


class ParamsSection(RootModel[dict[str, Parameter]]):
    pass


class EnumType(ContractModel):
    kind: Literal["enum"]
    values: list[Text]
    labels: dict[str, str]


class TypesSection(RootModel[dict[str, EnumType]]):
    pass


class FieldSpec(ContractModel):
    type: FieldType
    required: bool = False
    label: str | None = None
    max: int | None = None
    ref: str | None = None
    nullable: bool = False
    computed_by: str | None = None
    machine: str | None = None


class Entity(ContractModel):
    label: Text
    fields: dict[str, FieldSpec]
    owner: str | None = None
    traces: list[Text]


class EntitiesSection(RootModel[dict[str, Entity]]):
    pass


class Role(ContractModel):
    name: Text
    demo_users: list[Text]


class RolesSection(RootModel[dict[str, Role]]):
    pass


class Permission(ContractModel):
    role: Text
    op: OperationName
    scope: PermissionScope


class PermissionsSection(RootModel[list[Permission]]):
    pass


class Trigger(ContractModel):
    command: str | None = None
    event: str | None = None
    schedule: str | None = None
    timer: str | None = None
    geo: str | dict[str, JsonValue] | None = None

    @model_validator(mode="after")
    def one_kind(self) -> Self:
        if sum(getattr(self, key) is not None for key in type(self).model_fields) > 1:
            raise ValueError("Триггер должен задавать не более одного вида события")
        return self


class Transition(ContractModel):
    name: Text
    from_: list[Text] = Field(alias="from")
    to: Text
    trigger: Trigger | None = None
    guard: str | None = None
    roles: list[Text] = Field(default_factory=list)
    traces: list[Text]


class StateMachine(ContractModel):
    entity: Text
    initial: Text
    final: list[Text]
    states: list[Text]
    transitions: list[Transition]


class StateMachinesSection(RootModel[dict[str, StateMachine]]):
    pass


class Hook(ContractModel):
    kind: HookKind
    in_: list[Text] = Field(alias="in")
    out: str | None = None
    params: list[Text] = Field(default_factory=list)
    rule: Text
    traces: list[Text]
    select: str | None = None


class HooksSection(RootModel[dict[str, Hook]]):
    pass


class Command(ContractModel):
    entity: Text
    roles: list[Text]
    input: dict[str, FieldSpec]
    effects: list[Text]
    traces: list[Text]


class CommandsSection(RootModel[dict[str, Command]]):
    pass


class Query(ContractModel):
    entity: Text
    filter: str | None = None
    roles: list[Text]
    order: str | None = None


class QueriesSection(RootModel[dict[str, Query]]):
    pass


class EventsSection(RootModel[dict[str, dict[str, JsonValue]]]):
    pass


class IntegrationsSection(RootModel[dict[str, dict[str, JsonValue]]]):
    pass


class SchedulesSection(RootModel[dict[str, dict[str, JsonValue]]]):
    pass


class Notification(ContractModel):
    on: Text
    to: Text
    channels: list[NotificationChannel]
    text: Text


class NotificationsSection(RootModel[dict[str, Notification]]):
    pass


class SeedSection(RootModel[dict[str, list[dict[str, JsonValue]]]]):
    pass


class ScenariosSection(RootModel[list[dict[str, JsonValue]]]):
    pass


class CustomSection(RootModel[list[dict[str, JsonValue]]]):
    pass


class App(ContractModel):
    schema_version: Literal[1]
    meta: MetaSection
    params: ParamsSection
    types: TypesSection
    entities: EntitiesSection
    roles: RolesSection
    permissions: PermissionsSection
    state_machines: StateMachinesSection
    hooks: HooksSection
    commands: CommandsSection
    queries: QueriesSection
    events: EventsSection
    integrations: IntegrationsSection
    schedules: SchedulesSection
    notifications: NotificationsSection
    seed: SeedSection
    scenarios: ScenariosSection
    custom: CustomSection


def _segments(path: str) -> tuple[str | int, ...]:
    """Разбирает адреса a.b[2], a[Name] и JSON Pointer без потерь индексов."""
    if path.startswith("app."):
        path = path[4:]
    if path.startswith("/"):
        return tuple(
            int(part) if part.isdecimal() else part
            for part in (token.replace("~1", "/").replace("~0", "~") for token in path[1:].split("/"))
        )
    tokens = re.findall(r"[^.\[\]]+", path)
    return tuple(int(token) if token.isdecimal() else token for token in tokens)


def _path(parts: tuple[str | int, ...]) -> str:
    result = ""
    for part in parts:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            result += ("." if result else "") + part
    return result


def _contains(parent: tuple[str | int, ...], child: tuple[str | int, ...]) -> bool:
    return child[:len(parent)] == parent


def dependents(app: App | dict, path: str) -> list[str]:
    """Возвращает прямые и транзитивные зависимости, включая циклы.

    Имена разрешаются в контексте свойства (role, ref, trigger и т. п.).
    Выражения фильтра и эффекты дополнительно разбираются по границам имён.
    Для непрозрачных разделов учитываются явные имена/пути, но новая грамматика
    выражений здесь не вводится. Исходный элемент в результат не включается.
    """
    if not isinstance(app, App):
        app = App.model_validate(app)
    data = app.model_dump(mode="json", by_alias=True, exclude_none=True)
    graph: dict[tuple[str | int, ...], set[tuple[str | int, ...]]] = {}

    def link(target: str, dependent: str) -> None:
        graph.setdefault(_segments(target), set()).add(_segments(dependent))

    def names(section: str, refs: list[str], dependent: str) -> None:
        for ref in refs:
            link(f"{section}.{ref}", dependent)

    def fields(entity: str, expression: str, dependent: str) -> None:
        for name in data["entities"].get(entity, {}).get("fields", {}):
            if re.search(rf"(?<![\w]){re.escape(name)}(?![\w])", expression):
                link(f"entities.{entity}.fields.{name}", dependent)

    for name, entity in data["entities"].items():
        base = f"entities.{name}"
        for field_name, spec in entity["fields"].items():
            current = f"{base}.fields.{field_name}"
            if spec.get("ref"):
                section = "types" if spec["type"] == "enum" else "entities"
                names(section, [spec["ref"]], current)
            for prop, section in (("computed_by", "hooks"), ("machine", "state_machines")):
                if spec.get(prop):
                    names(section, [spec[prop]], current)
        if entity.get("owner"):
            link(f"{base}.fields.{entity['owner']}", base)

    for index, permission in enumerate(data["permissions"]):
        current = f"permissions[{index}]"
        names("roles", [permission["role"]], current)
        op = permission["op"]
        if "." in op:
            names("entities", [op.split(".")[0]], current)
        else:
            names("commands", [op], current)

    for name, machine in data["state_machines"].items():
        base = f"state_machines.{name}"
        names("entities", [machine["entity"]], base)
        for index, transition in enumerate(machine["transitions"]):
            current = f"{base}.transitions[{index}]"
            names("roles", transition["roles"], current)
            if transition.get("guard"):
                names("hooks", [transition["guard"]], current)
            for kind, target in (transition.get("trigger") or {}).items():
                if kind == "timer":
                    link(f"entities.{machine['entity']}.fields.{target}", current)
                elif kind in ("command", "event", "schedule"):
                    section = {"command": "commands", "event": "events", "schedule": "schedules"}[kind]
                    names(section, [target], current)
            for state_index, state in enumerate(machine["states"]):
                if state in transition["from"] or state == transition["to"]:
                    link(f"{base}.states[{state_index}]", current)

    for name, hook in data["hooks"].items():
        current = f"hooks.{name}"
        names("params", hook["params"], current)
        if hook.get("select"):
            names("queries", [hook["select"]], current)
        for ref in hook["in"] + ([hook["out"]] if hook.get("out") else []):
            if ref in data["entities"]:
                names("entities", [ref], current)
            elif ref in data["commands"]:
                names("commands", [ref], current)
            elif ref in data["types"]:
                names("types", [ref], current)
            elif "." in ref:
                entity, field_name = ref.split(".", 1)
                link(f"entities.{entity}.fields.{field_name}", current)

    for section in ("commands", "queries"):
        for name, operation in data[section].items():
            current = f"{section}.{name}"
            names("entities", [operation["entity"]], current)
            names("roles", operation["roles"], current)
            for prop in ("filter", "order"):
                if operation.get(prop):
                    fields(operation["entity"], operation[prop], current)
            for field_name, spec in operation.get("input", {}).items():
                dependent = f"{current}.input.{field_name}"
                if spec.get("ref"):
                    names("types" if spec["type"] == "enum" else "entities", [spec["ref"]], dependent)
                if spec.get("computed_by"):
                    names("hooks", [spec["computed_by"]], dependent)
                if spec.get("machine"):
                    names("state_machines", [spec["machine"]], dependent)
            for effect in operation.get("effects", []):
                if effect.startswith("transition:"):
                    machine_name, _, transition_name = effect.removeprefix("transition:").partition(".")
                    machine = data["state_machines"].get(machine_name, {})
                    for index, transition in enumerate(machine.get("transitions", [])):
                        if transition["name"] == transition_name:
                            link(f"state_machines.{machine_name}.transitions[{index}]", current)

    for name, notification in data["notifications"].items():
        current = f"notifications.{name}"
        names("events", [notification["on"]], current)
        names("roles", [notification["to"]], current)
        if notification["on"] not in data["events"]:
            # Имя неявного события выводит генератор. Пока его соглашение
            # не закреплено, сохраняем зависимость от всех машин состояний.
            for machine_name in data["state_machines"]:
                names("state_machines", [machine_name], current)

    for entity, records in data["seed"].items():
        names("entities", [entity], f"seed.{entity}")
        for index, record in enumerate(records):
            for field_name in record:
                link(f"entities.{entity}.fields.{field_name}", f"seed.{entity}[{index}].{field_name}")

    # Из неизвестных структур извлекаются только однозначные ссылки.
    symbols: dict[str, list[str]] = {}
    for section in ("entities", "types", "roles", "params", "hooks", "commands", "queries",
                    "events", "integrations", "schedules", "notifications", "state_machines"):
        for name in data[section]:
            symbols.setdefault(name, []).append(f"{section}.{name}")

    def opaque(value: JsonValue, current: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                opaque(item, f"{current}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                opaque(item, f"{current}[{index}]")
        elif isinstance(value, str):
            refs = symbols.get(value, [])
            if len(refs) == 1:
                link(refs[0], current)
            if value.startswith(tuple(f"{key}." for key in data)):
                link(value, current)
            for entity, definition in data["entities"].items():
                for field_name in definition["fields"]:
                    ref = f"{entity}.{field_name}"
                    if re.search(rf"(?<![\w.]){re.escape(ref)}(?![\w.])", value):
                        link(f"entities.{ref.split('.', 1)[0]}.fields.{field_name}", current)

    for section in ("events", "integrations", "schedules", "scenarios", "custom"):
        opaque(data[section], section)

    trace_sections = {"REQ": "requirements", "US": "user_stories", "BR": "rules", "AC": "acceptance", "NFR": "nfr", "ASM": "assumptions"}

    def traces(value: JsonValue, current: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ("rule", "traces"):
                    refs = [item] if isinstance(item, str) else item
                    if isinstance(refs, list):
                        for ref in refs:
                            if isinstance(ref, str):
                                section = trace_sections.get(ref.partition("-")[0])
                                if section:
                                    link(f"analysis.{section}[{ref}]", current)
                else:
                    traces(item, f"{current}.{key}" if current else key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                traces(item, f"{current}[{index}]")

    traces(data, "")

    start = _segments(path)
    visited = {start}
    pending = deque([start])
    result: set[str] = set()
    while pending:
        changed = pending.popleft()
        for target, consumers in graph.items():
            # Ссылка на сущность/раздел зависит также от его дочерних элементов.
            if not (_contains(changed, target) or _contains(target, changed)):
                continue
            # Транзитивно задетое поле не меняет форму сущности: права, CRUD и seed по ней не помечаются.
            if changed != start and len(target) == 2 and target[0] == "entities" and target != changed:
                continue
            for consumer in consumers:
                if consumer in visited or _contains(start, consumer):
                    continue
                visited.add(consumer)
                result.add(_path(consumer))
                pending.append(consumer)
    return sorted(result)
