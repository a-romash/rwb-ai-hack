"""G1: контракт приложения и 18 независимых семантических валидаторов."""
from __future__ import annotations

import itertools
import re
from decimal import Decimal
from pathlib import Path
from typing import Callable

from contracts.analysis import Analysis, FieldType
from contracts.app import App
from stages.analysis.compat import ContractError, Finding, GateResult
from stages.analysis.storage import read_json
from stages.spec.semantics import implicit_events, number, operation_exists, parse_gherkin, scenarios
from typing import get_args


def finding(code: str, path: str, message: str, severity: str = "error") -> Finding:
    return Finding(code=code, path=path, message=message, severity=severity)


def ref_unresolved(analysis: Analysis, app: App) -> list[Finding]:
    result: list[Finding] = []
    ids = {item.id for name in ("requirements", "user_stories", "rules", "acceptance", "nfr", "assumptions") for item in getattr(analysis, name)}

    def ref(value: str | None, choices, path: str) -> None:
        if value not in choices:
            result.append(finding("REF_UNRESOLVED", path, f"Ссылка «{value}» не разрешается."))

    sources = {s.id for s in analysis.sources}
    reqs = {r.id for r in analysis.requirements}
    rules = {r.id for r in analysis.rules}
    stories = {s.id for s in analysis.user_stories}
    actions = {q.id for q in analysis.questions} | {a.id for a in analysis.assumptions}
    for req in analysis.requirements:
        for source in req.source:
            ref(source, sources, f"analysis.requirements[{req.id}]")
    for issue in analysis.issues:
        ref(issue.req, reqs, f"analysis.issues[{issue.id}]")
        ref(issue.action, actions, f"analysis.issues[{issue.id}]")
    for assumption in analysis.assumptions:
        ref(assumption.source, sources | actions | reqs, f"analysis.assumptions[{assumption.id}]")
    for story in analysis.user_stories:
        ref(story.role, {r.id for r in analysis.roles}, f"analysis.user_stories[{story.id}]")
        for req in story.req:
            ref(req, reqs, f"analysis.user_stories[{story.id}]")
    for rule in analysis.rules:
        for req in rule.req:
            ref(req, reqs, f"analysis.rules[{rule.id}]")
    for ac in analysis.acceptance:
        for value in ac.rules:
            ref(value, rules, f"analysis.acceptance[{ac.id}]")
        for value in ac.stories:
            ref(value, stories, f"analysis.acceptance[{ac.id}]")
    for item in analysis.out_of_scope:
        ref(item.req, reqs, "analysis.out_of_scope")

    def traces(values: list[str], path: str) -> None:
        for value in values:
            ref(value, ids, path)

    def field_refs(field, path: str) -> None:
        if field.type in ("enum", "ref"):
            ref(field.ref, app.types.root if field.type == "enum" else app.entities.root, path)
        if field.computed_by:
            ref(field.computed_by, app.hooks.root, path)
        if field.machine or field.type == "state":
            ref(field.machine, app.state_machines.root, path)

    for name, entity in app.entities.root.items():
        path = f"entities.{name}"
        traces(entity.traces, path)
        if entity.owner:
            ref(entity.owner, entity.fields, path + ".owner")
        for key, field in entity.fields.items():
            field_refs(field, path + f".fields.{key}")
    for name, parameter in app.params.root.items():
        traces(parameter.traces, f"params.{name}")
    events = set(app.events.root) | implicit_events(app)
    for name, machine in app.state_machines.root.items():
        path = f"state_machines.{name}"
        ref(machine.entity, app.entities.root, path + ".entity")
        ref(machine.initial, machine.states, path + ".initial")
        for state in machine.final:
            ref(state, machine.states, path + ".final")
        for index, transition in enumerate(machine.transitions):
            target = path + f".transitions[{index}]"
            traces(transition.traces, target)
            for state in transition.from_ + [transition.to]:
                ref(state, machine.states, target)
            for role in transition.roles:
                ref(role, app.roles.root, target + ".roles")
            if transition.guard:
                ref(transition.guard, app.hooks.root, target + ".guard")
            if transition.trigger:
                trigger = transition.trigger
                if trigger.command:
                    ref(trigger.command, app.commands.root, target + ".trigger.command")
                if trigger.event:
                    ref(trigger.event, events, target + ".trigger.event")
                if trigger.schedule:
                    ref(trigger.schedule, app.schedules.root, target + ".trigger.schedule")
                if trigger.timer:
                    entity = app.entities.root.get(machine.entity)
                    ref(trigger.timer, entity.fields if entity else {}, target + ".trigger.timer")
    # `now`: the current moment, passed in because hooks never read the clock.
    known_inputs = set(app.entities.root) | set(app.commands.root) | set(app.types.root) | set(get_args(FieldType)) | {"now"}
    known_inputs |= {f"{name}.{field}" for name, entity in app.entities.root.items() for field in entity.fields}
    for name, hook in app.hooks.root.items():
        path = f"hooks.{name}"
        ref(hook.rule, rules, path + ".rule")
        traces(hook.traces, path)
        for value in hook.in_:
            ref(value, known_inputs, path + ".in")
        if hook.out:
            ref(hook.out, known_inputs, path + ".out")
        for param in hook.params:
            ref(param, app.params.root, path + ".params")
        if hook.select:
            ref(hook.select, app.queries.root, path + ".select")
    for section in ("commands", "queries"):
        for name, operation in getattr(app, section).root.items():
            path = f"{section}.{name}"
            ref(operation.entity, app.entities.root, path + ".entity")
            for role in operation.roles:
                ref(role, app.roles.root, path + ".roles")
            if section == "commands":
                traces(operation.traces, path)
                for key, field in operation.input.items():
                    field_refs(field, path + f".input.{key}")
                for effect in operation.effects:
                    if effect.startswith("transition:"):
                        machine_name, _, transition_name = effect.removeprefix("transition:").partition(".")
                        machine = app.state_machines.root.get(machine_name)
                        ref(transition_name, {t.name for t in machine.transitions} if machine else {}, path + ".effects")
    for index, permission in enumerate(app.permissions.root):
        ref(permission.role, app.roles.root, f"permissions[{index}].role")
        if not operation_exists(app, permission.op):
            result.append(finding("REF_UNRESOLVED", f"permissions[{index}].op", "Операция права доступа не существует."))
    for name, notification in app.notifications.root.items():
        ref(notification.to, app.roles.root, f"notifications.{name}.to")
    for name in app.seed.root:
        ref(name, app.entities.root, f"seed.{name}")
    return result


def req_uncovered(analysis: Analysis, app: App) -> list[Finding]:
    covered = {req for item in analysis.user_stories + analysis.rules for req in item.req}
    covered |= {item.req for item in analysis.out_of_scope}
    # В текущем контракте NFR не имеет req; явно записанные ID также учитываются.
    covered |= {req for nfr in analysis.nfr for req in re.findall(r"REQ-\d+", nfr.text)}
    return [finding("REQ_UNCOVERED", "analysis.user_stories", f"Требование {req.id} не связано с историей, правилом, NFR или исключением из объёма.") for req in analysis.requirements if req.id not in covered]


def br_no_ac(analysis: Analysis, app: App) -> list[Finding]:
    covered = {rule for ac in analysis.acceptance for rule in ac.rules}
    return [finding("BR_NO_AC", "analysis.acceptance", f"Для бизнес-правила {rule.id} отсутствует критерий приёмки.") for rule in analysis.rules if rule.id not in covered]


def br_no_boundary(analysis: Analysis, app: App) -> list[Finding]:
    result: list[Finding] = []
    for rule in analysis.rules:
        targets = [(number(p.value), p.type == "duration" or isinstance(p.value, str) and bool(re.fullmatch(r"\d{2}:\d{2}(?::\d{2})?", p.value))) for p in rule.params.values() if p.type in ("int", "decimal", "money", "duration", "date", "datetime", "string")]
        targets = [(target, temporal) for target, temporal in targets if target is not None]
        if not targets:
            targets = [(Decimal(value), False) for value in re.findall(r"(?<![\w-])\d+(?:\.\d+)?(?![\w-])", rule.text)]
        if not targets:
            continue
        columns: list[tuple[set[Decimal], set[Decimal], Decimal]] = []
        for ac in analysis.acceptance:
            if rule.id not in ac.rules:
                continue
            document = parse_gherkin(ac.gherkin)
            if not document:
                continue
            for scenario in scenarios(document):
                for examples in scenario.get("examples", []):
                    rows = examples.get("tableBody", [])
                    for index, header in enumerate(examples.get("tableHeader", {}).get("cells", [])):
                        cells = [row["cells"][index]["value"] for row in rows if len(row["cells"]) > index]
                        values = {number(cell) for cell in cells} - {None}
                        label = header["value"].casefold()
                        clocks = [cell for cell in cells if re.fullmatch(r"\d{2}:\d{2}(?::\d{2})?", cell)]
                        durations = [cell for cell in cells if re.fullmatch(r"P[\d.DTHMS]+", cell)]
                        scale = 86400 if re.search(r"day|дн|день|сут", label) else 3600 if re.search(r"hour|час", label) else 60 if re.search(r"minute|мин", label) else 1
                        if durations:
                            epsilon = min(1 if "S" in cell else 60 if "M" in cell else 3600 if "H" in cell else 86400 for cell in durations)
                        else:
                            epsilon = 60 if clocks and all(len(cell) == 5 for cell in clocks) else 1 if clocks else scale
                        scaled = values if clocks or durations else {value * scale for value in values}
                        columns.append((values, scaled, Decimal(epsilon)))
        if any(not any({target - (epsilon if temporal else 1), target, target + (epsilon if temporal else 1)} <= (scaled if temporal else values) for values, scaled, epsilon in columns) for target, temporal in targets):
            related = next((ac for ac in analysis.acceptance if rule.id in ac.rules), None)
            path = f"analysis.acceptance[{related.id}]" if related else "analysis.acceptance"
            result.append(finding("BR_NO_BOUNDARY", path, f"У порога правила {rule.id} нет примеров N−1, N и N+1 в одной колонке таблицы сценария."))
    return result


def br_no_hook(analysis: Analysis, app: App) -> list[Finding]:
    result: list[Finding] = []
    for rule in analysis.rules:
        acs = {ac.id for ac in analysis.acceptance if rule.id in ac.rules}
        hooks = [hook for hook in app.hooks.root.values() if hook.rule == rule.id]
        declarative = [item for item in app.custom.root if item.get("rule") == rule.id and item.get("kind") == "declarative"]
        if not hooks and not declarative:
            result.append(finding("BR_NO_HOOK", "hooks", f"Правило {rule.id} не представлено хуком или декларативным правилом."))
        for name, hook in app.hooks.root.items():
            if hook.rule == rule.id and not set(hook.traces) & acs:
                result.append(finding("BR_NO_HOOK", f"hooks.{name}", "Хук не ссылается на критерий приёмки своего правила."))
    return result


def ac_not_testable(analysis: Analysis, app: App) -> list[Finding]:
    result: list[Finding] = []
    for ac in analysis.acceptance:
        document = parse_gherkin(ac.gherkin)
        cases = scenarios(document) if document else []
        valid = ac.gherkin.lstrip().startswith("# language: ru") and bool(cases)
        for scenario in cases:
            steps = scenario.get("steps", [])
            kinds = {step.get("keywordType") for step in steps}
            then = []
            phase = None
            for step in steps:
                if step.get("keywordType") in ("Context", "Action", "Outcome"):
                    phase = step["keywordType"]
                if phase == "Outcome":
                    then.append(step.get("text", ""))
            expanded = list(then)
            placeholders = {name for step in steps for name in re.findall(r"<([^>]+)>", step.get("text", ""))}
            examples_list = scenario.get("examples", [])
            if placeholders:
                valid = valid and bool(examples_list)
                for examples in examples_list:
                    headers = [cell["value"] for cell in examples.get("tableHeader", {}).get("cells", [])]
                    valid = valid and placeholders <= set(headers) and bool(examples.get("tableBody"))
                    for row in examples.get("tableBody", []):
                        values = dict(zip(headers, (cell["value"] for cell in row["cells"])))
                        expanded.extend(re.sub(r"<([^>]+)>", lambda match: values.get(match[1], match[0]), text) for text in then)
            valid = valid and {"Context", "Action", "Outcome"} <= kinds
            valid = valid and any(re.search(r"\d|рав(?:н|ен)|содерж|сохран|статус|отказ|ошиб|показ|отображ|уведом|создан|назнач|закрыт|отсутств|не пуст|не измен|запрещ|не разреш|успех|неуспех", text, re.I) for text in expanded)
        if not valid:
            result.append(finding("AC_NOT_TESTABLE", f"analysis.acceptance[{ac.id}]", "Критерий не содержит корректный русский Gherkin с предусловием, действием и проверяемым результатом."))
    return result


def nfr_not_measurable(analysis: Analysis, app: App) -> list[Finding]:
    return [finding("NFR_NOT_MEASURABLE", f"analysis.nfr[{nfr.id}]", "Для NFR не заданы числовая метрика и способ проверки.", "warning") for nfr in analysis.nfr if not re.search(r"\d", nfr.metric) or not nfr.verify.strip()]


def vague_word(analysis: Analysis, app: App) -> list[Finding]:
    result: list[Finding] = []
    for section, items, attribute in (("acceptance", analysis.acceptance, "gherkin"), ("nfr", analysis.nfr, "text")):
        for item in items:
            text = getattr(item, attribute)
            if re.search(r"\b(быстр\w*|удобн\w*|оперативн\w*|больш\w*|маленьк\w*|надёжн\w*|эффективн\w*)", text, re.I) and not re.search(r"\d", text + getattr(item, "metric", "")):
                result.append(finding("VAGUE_WORD", f"analysis.{section}[{item.id}]", "Неопределённая характеристика не подкреплена числом.", "warning"))
    return result


def sm_unreachable(analysis: Analysis, app: App) -> list[Finding]:
    result: list[Finding] = []
    for name, machine in app.state_machines.root.items():
        reachable = {machine.initial}
        while True:
            expanded = reachable | {t.to for t in machine.transitions if set(t.from_) & reachable}
            if expanded == reachable:
                break
            reachable = expanded
        for index, state in enumerate(machine.states):
            if state not in reachable:
                result.append(finding("SM_UNREACHABLE", f"state_machines.{name}.states[{index}]", "Состояние недостижимо из начального."))
    return result


def sm_deadlock(analysis: Analysis, app: App) -> list[Finding]:
    result: list[Finding] = []
    for name, machine in app.state_machines.root.items():
        for index, state in enumerate(machine.states):
            if state not in machine.final and not any(state in t.from_ and t.to != state for t in machine.transitions):
                result.append(finding("SM_DEADLOCK", f"state_machines.{name}.states[{index}]", "Нетерминальное состояние не имеет выхода."))
    return result


def sm_no_trigger(analysis: Analysis, app: App) -> list[Finding]:
    return [finding("SM_NO_TRIGGER", f"state_machines.{name}.transitions[{index}]", "Переход не содержит непустого триггера.") for name, machine in app.state_machines.root.items() for index, transition in enumerate(machine.transitions) if not transition.trigger or not any(transition.trigger.model_dump(exclude_none=True).values())]


def sm_guard_overlap(analysis: Analysis, app: App) -> list[Finding]:
    result: list[Finding] = []
    for name, machine in app.state_machines.root.items():
        for (i, a), (j, b) in itertools.combinations(enumerate(machine.transitions), 2):
            if set(a.from_) & set(b.from_) and a.trigger == b.trigger:
                message = "Условия переходов одного действия пересекаются." if not a.guard or not b.guard or a.guard == b.guard else "Непересекаемость произвольных условий переходов не доказана."
                result.append(finding("SM_GUARD_OVERLAP", f"state_machines.{name}.transitions[{j}]", message, "warning"))
    return result


def rbac_orphan(analysis: Analysis, app: App) -> list[Finding]:
    result: list[Finding] = []
    allowed = {(p.role, p.op) for p in app.permissions.root}
    for name, command in app.commands.root.items():
        if not command.roles:
            result.append(finding("RBAC_ORPHAN", f"commands.{name}.roles", "У команды отсутствует роль."))
        for role in command.roles:
            if (role, name) not in allowed:
                result.append(finding("RBAC_ORPHAN", "permissions", f"Роль {role} не имеет права выполнять команду {name}."))
    for role in app.roles.root:
        if not any(r == role for r, _ in allowed) and not any(role in q.roles for q in app.queries.root.values()):
            result.append(finding("RBAC_ORPHAN", f"roles.{role}", "Роль не имеет разрешённых действий."))
    for story in analysis.user_stories:
        commands = [command for command in app.commands.root.values() if story.id in command.traces]
        if story.role not in app.roles.root or (commands and not any(story.role in command.roles for command in commands)):
            result.append(finding("RBAC_ORPHAN", f"analysis.user_stories[{story.id}]", "Роль истории не может выполнить связанное действие."))
    for name, machine in app.state_machines.root.items():
        for index, transition in enumerate(machine.transitions):
            if transition.trigger and transition.trigger.command and not transition.roles:
                result.append(finding("RBAC_ORPHAN", f"state_machines.{name}.transitions[{index}].roles", "У перехода по команде не задана роль."))
    return result


def evt_incomplete(analysis: Analysis, app: App) -> list[Finding]:
    return [finding("EVT_INCOMPLETE", f"events.{name}", "Событие не содержит производителя, потребителя или ключа.") for name, event in app.events.root.items() if not event.get("producer") or not (event.get("consumer") or event.get("consumers")) or not event.get("key")]


def ntf_bad_event(analysis: Analysis, app: App) -> list[Finding]:
    known = set(app.events.root) | implicit_events(app)
    return [finding("NTF_BAD_EVENT", f"notifications.{name}.on", "Уведомление ссылается на неизвестное событие.") for name, notification in app.notifications.root.items() if notification.on not in known]


def us_no_endpoint(analysis: Analysis, app: App) -> list[Finding]:
    result: list[Finding] = []
    for story in analysis.user_stories:
        commands = any(story.id in command.traces and story.role in command.roles and any(p.role == story.role and p.op == name for p in app.permissions.root) for name, command in app.commands.root.items())
        crud = any(story.id in entity.traces and any(p.role == story.role and p.op.startswith(name + ".") for p in app.permissions.root) for name, entity in app.entities.root.items())
        custom = any(item.get("location") in ("endpoint", "api") and (story.id in item.get("traces", []) or any(story.id in ac.stories and ac.id in item.get("acceptance", []) for ac in analysis.acceptance)) for item in app.custom.root)
        if not commands and not crud and not custom:
            result.append(finding("US_NO_ENDPOINT", f"analysis.user_stories[{story.id}]", "История не связана с доступной своей роли операцией API."))
    return result


def data_unknown_field(analysis: Analysis, app: App) -> list[Finding]:
    result: list[Finding] = []
    for name, rows in app.seed.root.items():
        entity = app.entities.root.get(name)
        for index, row in enumerate(rows):
            for key in row:
                if entity and key not in entity.fields and key != "id":
                    result.append(finding("DATA_UNKNOWN_FIELD", f"seed.{name}[{index}].{key}", "Поле начальных данных отсутствует в сущности."))
    cards = {card.file: card for card in analysis.data_cards}

    def visit(value, path: str) -> None:
        if isinstance(value, dict):
            if "file" in value and "field" in value:
                card = cards.get(value["file"])
                fields = card.data_schema.get("fields", card.data_schema) if card else {}
                if not card or value["field"] not in fields:
                    result.append(finding("DATA_UNKNOWN_FIELD", path, "Поле набора данных отсутствует в карточке."))
                elif not value.get("unit"):
                    info = fields[value["field"]]
                    types = info.get("types", {}) if isinstance(info, dict) else {}
                    if set(types) & {"int", "decimal", "money", "duration", "geo_point", "geo_line", "geo_polygon"}:
                        result.append(finding("DATA_UNKNOWN_FIELD", path, "Для числовых или пространственных данных не заданы единицы."))
            for key, item in value.items():
                visit(item, f"{path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")
    for section in ("seed", "scenarios", "custom"):
        visit(getattr(app, section).root, section)
    return result


def param_literal(analysis: Analysis, app: App) -> list[Finding]:
    result: list[Finding] = []
    by_id = {rule.id: rule for rule in analysis.rules}
    for name, hook in app.hooks.root.items():
        rule = by_id.get(hook.rule)
        if rule and re.search(r"(?<![\w-])\d+(?:\.\d+)?(?![\w-])", rule.text) and not hook.params:
            result.append(finding("PARAM_LITERAL", f"hooks.{name}", "Числовой порог связанного правила не вынесен в параметры хука.", "warning"))
    return result


VALIDATORS: dict[str, Callable[[Analysis, App], list[Finding]]] = {
    "REF_UNRESOLVED": ref_unresolved, "REQ_UNCOVERED": req_uncovered,
    "BR_NO_AC": br_no_ac, "BR_NO_BOUNDARY": br_no_boundary,
    "BR_NO_HOOK": br_no_hook, "AC_NOT_TESTABLE": ac_not_testable,
    "NFR_NOT_MEASURABLE": nfr_not_measurable, "VAGUE_WORD": vague_word,
    "SM_UNREACHABLE": sm_unreachable, "SM_DEADLOCK": sm_deadlock,
    "SM_NO_TRIGGER": sm_no_trigger, "SM_GUARD_OVERLAP": sm_guard_overlap,
    "RBAC_ORPHAN": rbac_orphan, "EVT_INCOMPLETE": evt_incomplete,
    "NTF_BAD_EVENT": ntf_bad_event, "US_NO_ENDPOINT": us_no_endpoint,
    "DATA_UNKNOWN_FIELD": data_unknown_field, "PARAM_LITERAL": param_literal,
}


def validate(analysis: Analysis, app: App) -> list[Finding]:
    return [item for validator in VALIDATORS.values() for item in validator(analysis, app)]


def check(workspace: Path, artifacts: dict[str, str]) -> GateResult:
    try:
        app = App.model_validate(read_json(workspace, artifacts.get("app", "spec/app.json")))
    except (ContractError, ValueError, TypeError):
        return GateResult(gate="G1", passed=False, findings=[finding("CONTRACT_APP", "app", "Спецификация отсутствует или не соответствует схеме.")])
    try:
        analysis = Analysis.model_validate(read_json(workspace, artifacts.get("analysis", "spec/analysis.json")))
    except (ContractError, ValueError, TypeError):
        return GateResult(gate="G1", passed=False, findings=[finding("REF_UNRESOLVED", "analysis", "Принятый анализ отсутствует или не соответствует схеме.")])
    findings = validate(analysis, app)
    return GateResult(gate="G1", passed=not any(f.severity == "error" for f in findings), findings=findings)
