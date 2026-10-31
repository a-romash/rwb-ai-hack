"""S4: семь последовательных шагов с валидацией каждого раздела."""
from __future__ import annotations

import copy
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from contracts.analysis import Analysis
from contracts.app import (
    App, CommandsSection, CustomSection, EntitiesSection, EventsSection, HooksSection,
    IntegrationsSection, MetaSection, NotificationsSection, ParamsSection,
    PermissionsSection, QueriesSection, RolesSection, ScenariosSection,
    SchedulesSection, SeedSection, StateMachinesSection, TypesSection, dependents,
)
from stages.analysis.compat import BudgetExceeded, ContractError, ElementFlag, Finding, LLM, Sandbox, StageInput, StageOutput, validate_input
from stages.analysis.patching import PatchRejected, PatchResponse, apply_patch, pointer, tokens
from stages.analysis.runtime import ask, encoded, size, window
from stages.analysis.storage import read_json, write_json
from stages.analysis.symbols import normalize_section_roles
from stages.spec.context import analysis_slice, empty_app, index

from harness.normalization import normalize_app, normalize_patch, record, within

ARTIFACT = "spec/app.json"
FOUNDATION_REPAIR_ATTEMPTS = 3


def bind_entities(value: dict, data: dict) -> dict:
    """Name the obvious targets the model leaves out: `ref` of ref/enum fields by the field name, and drop an
    owner that is not a field of the entity (the model writes aggregate names like ParkingDomain there)."""
    # shortcut: binding by name only takes a unique match; anything ambiguous stays for G1 and repair.
    entities = list(dict.fromkeys([*data.get("entities", {}), *value]))
    enums = [name for name, item in data.get("types", {}).items() if item.get("kind") == "enum"]

    def pick(names: list[str], field: str, owner: str) -> str | None:
        words = re.findall(r"[A-Za-z][a-z0-9]*", re.sub(r"_?[Ii]ds?$", "", field))
        for key in dict.fromkeys(["".join(words).lower(), words[-1].lower() if words else ""]):
            for candidates in ([n for n in names if n.lower() == key], [n for n in names if n.lower().endswith(key) and n.lower().startswith(owner.lower())],
                               [n for n in names if n.lower().endswith(key)], [n for n in names if n.lower().endswith(key.removesuffix("s"))]):
                if key and len(candidates) == 1:
                    return candidates[0]
        return None

    for name, entity in value.items():
        fields = entity.get("fields", {})
        if entity.get("owner") and entity["owner"] not in fields:
            del entity["owner"]
        for key, field in fields.items():
            if field.get("type") in ("ref", "enum") and not field.get("ref"):
                target = pick(entities if field["type"] == "ref" else enums, key, name)
                if target:
                    field["ref"] = target
    return value


STEPS: tuple[tuple[str, tuple[tuple[str, type[BaseModel]], ...]], ...] = (
    ("domain", (("meta", MetaSection), ("types", TypesSection), ("entities", EntitiesSection))),
    ("access", (("roles", RolesSection), ("permissions", PermissionsSection))),
    ("behavior", (("state_machines", StateMachinesSection),)),
    ("rules", (("params", ParamsSection), ("hooks", HooksSection))),
    ("api", (("commands", CommandsSection), ("queries", QueriesSection))),
    ("environment", (("events", EventsSection), ("integrations", IntegrationsSection), ("schedules", SchedulesSection), ("notifications", NotificationsSection))),
    ("data", (("seed", SeedSection), ("scenarios", ScenariosSection), ("custom", CustomSection))),
)


def _merge(old, new, path: str, conflicts: list[str]):
    if isinstance(old, dict) and isinstance(new, dict):
        for key, value in new.items():
            if key in old:
                old[key] = _merge(old[key], value, f"{path}.{key}", conflicts)
            else:
                old[key] = copy.deepcopy(value)
        return old
    if isinstance(old, list) and isinstance(new, list):
        for item in new:
            if item not in old:
                old.append(copy.deepcopy(item))
        return old
    if old != new:
        conflicts.append(path)
    return old


def _context(analysis: Analysis, data: dict, section: str, req_ids: set[str]) -> dict:
    slice_ = analysis_slice(analysis, req_ids)
    relevant = {
        "meta": ("requirements",), "types": ("requirements", "glossary"),
        "entities": ("requirements", "user_stories", "glossary"),
        "roles": ("roles", "user_stories"), "permissions": ("roles", "user_stories"),
        "state_machines": ("user_stories", "rules"),
        "params": ("rules", "assumptions"), "hooks": ("rules", "acceptance", "assumptions"),
        "commands": ("user_stories", "rules"), "queries": ("user_stories",),
        "events": ("requirements", "rules"), "integrations": ("requirements", "nfr"),
        "schedules": ("requirements", "rules"), "notifications": ("requirements", "user_stories"),
        "seed": ("acceptance",), "scenarios": ("acceptance",), "custom": ("requirements", "acceptance"),
    }[section]
    context = {key: slice_[key] for key in relevant}
    if section in ("entities", "seed", "scenarios"):
        context["data_cards"] = [card.model_dump(mode="json") for card in analysis.data_cards]
    snapshot = index(data)
    # Раздел видит имена зависимостей, но подробности только своего шага.
    needed = {
        "meta": (), "types": ("types",), "entities": ("types", "entities"),
        "roles": ("entities", "roles"), "permissions": ("entities", "roles", "permissions"),
        "state_machines": ("entities", "roles", "state_machines"),
        "params": ("params",), "hooks": ("entities", "state_machines", "params", "hooks"),
        "commands": ("entities", "roles", "permissions", "state_machines", "hooks", "commands"),
        "queries": ("entities", "roles", "queries"),
        "events": ("entities", "state_machines", "commands", "events"),
        "integrations": ("integrations",), "schedules": ("entities", "events", "schedules"),
        "notifications": ("entities", "roles", "state_machines", "events", "notifications"),
        "seed": ("entities", "types", "roles"), "scenarios": ("entities", "commands", "queries"),
        "custom": ("entities", "commands", "hooks"),
    }[section]
    shapes = {"meta": "A single metadata object, with name/title/lang/timezone/modules.",
              "permissions": "A list of permission objects, never an object with a permissions key.",
              "scenarios": "A list of scenario objects.", "custom": "A list of custom extension objects."}
    shape = shapes.get(section, f"A map keyed by the actual English business names of {section}. Never use '{section}' as the outer key or as a placeholder business name.")
    return {"section": section, "output_shape": shape, "analysis": context, "app": {key: snapshot[key] for key in needed}}


def _requests(analysis: Analysis, data: dict, section: str, model: type[BaseModel], llm: LLM, *, validation_errors: list[dict] | None = None) -> list[dict]:
    req_ids = [req.id for req in analysis.requirements]
    groups = [(req_ids, validation_errors)]
    result: list[dict] = []
    while groups:
        group, errors = groups.pop(0)
        payload = _context(analysis, data, section, set(group))
        if errors is not None:
            payload["validation_errors"] = errors
        if size("system-analyst-" + next(step for step, sections in STEPS if any(name == section for name, _ in sections)), payload, model) <= window(llm):
            result.append(payload)
        elif len(group) > 1:
            middle = len(group) // 2
            groups[0:0] = [(group[:middle], errors), (group[middle:], errors)]
        elif errors is not None and len(errors) > 1:
            middle = len(errors) // 2
            groups[0:0] = [(group, errors[:middle]), (group, errors[middle:])]
        else:
            # Сохраняем полные определения только затронутых сущностей.
            selected = {story.id for story in analysis.user_stories if set(story.req) & set(group)}
            entities = payload["app"].get("entities", {})
            for name, entity in list(entities.items()):
                if not set(entity.get("traces", [])) & selected:
                    entities[name] = {"fields": list(entity["fields"])}
            agent = "system-analyst-" + next(step for step, sections in STEPS if any(name == section for name, _ in sections))
            if size(agent, payload, model) > window(llm):
                if errors is not None:
                    raise ContractError("Даже минимальный контекст исправления связей не помещается в окно модели")
                raise BudgetExceeded("Даже контекст одной фичи не помещается в профиль окна")
            result.append(payload)
    return result


def _foundation_findings(analysis: Analysis, data: dict) -> list[Finding]:
    # Commands are generated later; only check role and CRUD references already decidable here.
    from gates.g1_spec import ref_unresolved
    app = App.model_validate(data)
    result = []
    for finding in ref_unresolved(analysis, app):
        match = re.fullmatch(r"permissions\[(\d+)\]\.(role|op)", finding.path)
        if match and (match[2] == "role" or "." in app.permissions.root[int(match[1])].op):
            result.append(finding)
    return result


def execute(inp: StageInput, workspace: Path, llm: LLM, sandbox: Sandbox) -> StageOutput:
    inp = validate_input(inp, "spec")
    try:
        analysis = Analysis.model_validate(read_json(workspace, inp.artifacts.get("analysis", "spec/analysis.json")))
    except (ValueError, TypeError) as exc:
        raise ContractError("Входной анализ не соответствует схеме") from exc
    data = empty_app(analysis)
    # Параметры правил уже заданы бизнес-анализом; переносим их без LLM.
    for rule in analysis.rules:
        for name, parameter in rule.params.items():
            data["params"][name] = parameter.model_dump(mode="json") | {"traces": [rule.id]}
    conflicts: list[str] = []
    for assumption in analysis.assumptions:
        for name, value in assumption.params.items():
            if name in data["params"]:
                if data["params"][name]["value"] != value:
                    conflicts.append(f"params.{name}")
                continue
            kind = "bool" if isinstance(value, bool) else "int" if isinstance(value, int) else "decimal" if isinstance(value, float) else "duration" if isinstance(value, str) and re.fullmatch(r"P[0-9.DTHMS]+", value) else "string" if isinstance(value, str) else "json"
            data["params"][name] = {"type": kind, "value": value, "traces": [assumption.id]}
    flags: list[ElementFlag] = []
    completed: list[str] = []
    notes: list[dict] = []
    aliases = {}

    def persist():
        nonlocal data
        data, changes = normalize_app(data, aliases)
        record(workspace, changes, "spec", llm)
        write_json(workspace, "spec/name-map.json", aliases)
        write_json(workspace, ARTIFACT, App.model_validate(data))

    write_json(workspace, ARTIFACT, App.model_validate(data))
    try:
        for step, sections in STEPS:
            for section, model in sections:
                requests = _requests(analysis, data, section, model, llm)
                for part, payload in enumerate(requests):
                    response = ask(llm, task_class="spec_step", agent=f"system-analyst-{step}", payload=payload, output=model, task_id=f"spec.{section}.{part}")
                    value = response.model_dump(mode="json", by_alias=True, exclude_none=True)
                    value = normalize_section_roles(section, value, analysis.roles)
                    if section == "entities":
                        value = bind_entities(value, data)
                    if section == "meta":
                        if not part:
                            data[section] = value
                    else:
                        data[section] = _merge(data[section], value, section, conflicts)
                    # Валидация объединённого раздела на каждом узком шаге.
                    model.model_validate(data[section])
                    persist()
                completed.append(section)
            if step == "access":
                repair_issue = None
                for attempt in range(FOUNDATION_REPAIR_ATTEMPTS):
                    findings = _foundation_findings(analysis, data)
                    if not findings:
                        break
                    targets = []
                    if any(f.path.endswith(".op") for f in findings):
                        targets.append(("entities", EntitiesSection))
                    if any(f.path.endswith(".role") for f in findings):
                        targets.append(("roles", RolesSection))
                    for section, model in targets:
                        relevant = [f for f in findings if f.path.endswith(".op" if section == "entities" else ".role")]
                        errors = [{"path": f.path, "message": f.message,
                                   "permission": data["permissions"][int(re.search(r"\[(\d+)\]", f.path)[1])]} for f in relevant]
                        try:
                            requests = _requests(analysis, data, section, model, llm, validation_errors=errors)
                        except ContractError as exc:
                            repair_issue = f"Не удалось подготовить контекст исправления: {exc}"
                            break
                        replacement = {}
                        try:
                            for part, payload in enumerate(requests):
                                payload["repair_attempt"] = attempt + 1
                                response = ask(llm, task_class="spec_step", agent=f"system-analyst-{'domain' if section == 'entities' else 'access'}", payload=payload, output=model, task_id=f"spec.foundation.{section}.{attempt}.{part}")
                                value = normalize_section_roles(section, response.model_dump(mode="json", by_alias=True, exclude_none=True), analysis.roles)
                                if section == "entities":
                                    value = bind_entities(value, data)
                                replacement = _merge(replacement, value, section, conflicts)
                            model.model_validate(replacement)
                        except BudgetExceeded as exc:
                            repair_issue = f"Лимит модели: {exc}"
                            break
                        except ContractError:
                            continue
                        data[section] = replacement
                        persist()
                    if repair_issue:
                        break
                remaining = _foundation_findings(analysis, data)
                if remaining:
                    reason = f"Не исправлено после {FOUNDATION_REPAIR_ATTEMPTS} попыток: " if not repair_issue else f"Исправление остановлено ({repair_issue}); "
                    for finding in remaining:
                        flags.append(ElementFlag(path=finding.path, status="questioned", reason=reason + finding.message, gate="G1"))
                    notes.append({"stage": "spec", "text": "Связи ролей и операций остались неразрешёнными; спецификация проходит структурную схему и передана дальше.",
                                  "findings": [f.model_dump() for f in remaining]})
                    App.model_validate(data)
    except BudgetExceeded as exc:
        if not {"entities", "roles", "permissions"}.issubset(completed) or _foundation_findings(analysis, data):
            raise ContractError(f"Не удалось проверить связи сущностей, ролей и прав: лимит модели: {exc}") from exc
        flags.append(ElementFlag(path="app", status="questioned", reason=f"Лимит модели: {exc}; сохранена частичная спецификация."))
        notes.append({"stage": "spec", "text": "Незавершённые разделы сохранены пустыми и требуют реализации.", "completed": completed})
    except (ValueError, TypeError) as exc:
        raise ContractError("Раздел спецификации не соответствует контракту") from exc
    persist()
    app = App.model_validate(data)
    for item in app.custom.root:
        if item.get("requires_confirmation") or item.get("kind") == "assumption":
            note = {"id": f"ASM-{len(analysis.assumptions) + len(notes) + 1:02d}", "stage": "spec", "text": item.get("description", item.get("text", "Требуется подтверждение нетипового поведения.")), "requires_confirmation": True}
            notes.append(note)
            flags.append(ElementFlag(path=f"custom[{app.custom.root.index(item)}]", status="questioned", reason=str(note["text"]), gate="G1"))
    for path in sorted(set(conflicts)):
        flags.append(ElementFlag(path=path, status="questioned", reason="Шаги предложили несовместимые значения; сохранено первое значение.", gate="G1"))
        for dependent in dependents(app, path):
            flags.append(ElementFlag(path=dependent, status="blocked_by", reason=f"Зависит от спорного элемента {path}.", gate="G1"))
    write_json(workspace, ARTIFACT, app)
    write_json(workspace, "spec/spec-notes.json", {"schema_version": 1, "stage": "spec", "notes": notes})
    return StageOutput(artifacts={"app": ARTIFACT, "spec_notes": "spec/spec-notes.json", "name_map": "spec/name-map.json"}, summary=f"Спецификация содержит сущностей: {len(app.entities.root)}; правил в хуках: {len(app.hooks.root)}; команд: {len(app.commands.root)}.", flags=flags)


REPAIR_PARALLEL = 8


def _fit_repair(payload: dict, limit: int) -> dict | None:
    """Shrink the repair context step by step so one large finding does not stop the repair of the others."""
    analysis, app = payload["analysis"], payload["app"]
    compact_app = {section: {name: sorted(item.get("fields", {})) for name, item in value.items()} if section == "entities"
                   else sorted(value) if isinstance(value, dict) else value
                   for section, value in app.items() if section != "permissions"}
    candidates = (
        payload,
        {**payload, "analysis": {key: analysis[key] for key in ("requirements", "roles", "rules") if key in analysis}},
        {**payload, "analysis": {key: analysis[key] for key in ("requirements", "roles") if key in analysis}, "app": compact_app},
    )
    return next((item for item in candidates if size("system-analyst-repair", item, PatchResponse) <= limit), None)


def _repair_request(analysis_data: dict, app_data: dict, finding: Finding, limit: int) -> tuple[bool, Finding, dict | None]:
    """Context for one repair call, built from the documents as they were at the start of the round."""
    is_analysis = finding.path.startswith("analysis.")
    document = analysis_data if is_analysis else app_data
    address = finding.path.removeprefix("analysis.").removeprefix("app.")
    normalized = finding.model_copy(update={"path": address})
    location = pointer(document, address)
    element = document
    for key in tokens(location):
        element = element[int(key)] if isinstance(element, list) else element.get(key)
    analysis = Analysis.model_validate(analysis_data)
    related = (encoded(element) if len(tokens(location)) > 1 else "") + finding.message
    ancestors = app_data
    if not is_analysis:
        for key in tokens(location)[:-1]:
            if isinstance(ancestors, dict):
                related += " " + encoded(ancestors.get("traces", []))
                ancestors = ancestors.get(key, {})
            elif isinstance(ancestors, list) and key.isdecimal() and int(key) < len(ancestors):
                ancestors = ancestors[int(key)]
            else:
                break
    req_ids = {req.id for req in analysis.requirements if req.id in related}
    for story in analysis.user_stories:
        if story.id in related:
            req_ids.update(story.req)
    for rule in analysis.rules:
        if rule.id in related:
            req_ids.update(rule.req)
    snapshot = index(app_data)
    selected_stories = {story.id for story in analysis.user_stories if set(story.req) & req_ids}
    for name, entity in snapshot["entities"].items():
        if name not in related and not set(entity.get("traces", [])) & selected_stories:
            snapshot["entities"][name] = {"fields": list(entity["fields"])}
    snapshot["state_machines"] = {name: {"entity": machine["entity"], "transitions": [{key: t.get(key) for key in ("name", "guard", "trigger")} for t in machine["transitions"]]} for name, machine in snapshot["state_machines"].items()}
    relevant = analysis_slice(analysis, req_ids)
    relevant.pop("glossary", None)
    relevant.pop("nfr", None)
    if isinstance(element, list):
        element = [{key: value for key, value in item.items() if key in ("id", "req", "rules", "stories")} for item in element if isinstance(item, dict)]
    payload = {"finding": normalized.model_dump(), "target_pointer": location, "target_value": element,
               "analysis": relevant, "app": snapshot}
    section_name = tokens(location)[0]
    section_model = Analysis if is_analysis else App
    payload["section_schema"] = TypeAdapter(section_model.model_fields[section_name].annotation).json_schema()
    payload["binding_rules"] = {"owner": "A key of a field inside the same entity, never an aggregate or service name.",
                                "enum": "Use ref for the name of a declared enum type.", "ref": "Use ref for a declared entity name.",
                                "state": "Use machine for a declared state machine name.", "computed_by": "Only a declared hook name.",
                                "roles": "Use declared role IDs, not human display labels."}
    return is_analysis, normalized, _fit_repair(payload, limit)


def repair(inp: StageInput, workspace: Path, llm: LLM, findings: list[Finding], previous_output: StageOutput | None = None) -> StageOutput:
    validate_input(inp, "spec")
    analysis_name = inp.artifacts.get("analysis", "spec/analysis.json")
    app_name = inp.artifacts.get("app", ARTIFACT)
    analysis_data = read_json(workspace, analysis_name)
    app_data = read_json(workspace, app_name)
    Analysis.model_validate(analysis_data)
    App.model_validate(app_data)
    flags: list[ElementFlag] = []
    changed_analysis = False
    changed_app = False
    # One request per element: findings on the same path share a patch.
    grouped: dict[str, Finding] = {}
    for finding in findings:
        same = grouped.get(finding.path)
        grouped[finding.path] = same.model_copy(update={"message": f"{same.message} {finding.message}"}) if same else finding
    requests = []
    for finding in grouped.values():
        try:
            is_analysis, normalized, payload = _repair_request(analysis_data, app_data, finding, window(llm))
        except PatchRejected:
            flags.append(ElementFlag(path=finding.path, status="questioned", reason="Адрес находки не разрешается в элемент спецификации.", gate="G1"))
            continue
        feedback = [flag.reason for flag in (previous_output.flags if previous_output else [])
                    if flag.path == finding.path and flag.reason.startswith(("Предложенный патч отклонён:", "Ответ модели на ремонт не соответствует контракту:"))]
        if payload is not None and feedback:
            payload = _fit_repair({**payload, "previous_repair_errors": feedback}, window(llm))
        if payload is None:
            flags.append(ElementFlag(path=finding.path, status="questioned", reason="Контекст ремонта не помещается в профиль окна модели.", gate="G1"))
        else:
            requests.append((finding, is_analysis, normalized, payload))
    # The model answers in parallel; patches are applied one by one, and a stale one is rejected until the next round.
    with ThreadPoolExecutor(REPAIR_PARALLEL) as pool:
        futures = [pool.submit(ask, llm, task_class="patch", agent="system-analyst-repair", payload=payload, output=PatchResponse,
                               task_id=f"spec.repair.{inp.attempt}.{number}") for number, (_, _, _, payload) in enumerate(requests)]
        for future, (finding, is_analysis, normalized, _) in zip(futures, requests):
            try:
                response = future.result()
            except BudgetExceeded as exc:
                flags.append(ElementFlag(path=finding.path, status="questioned", reason=f"Лимит адресного ремонта: {exc}.", gate="G1"))
                continue
            except ContractError as exc:
                flags.append(ElementFlag(path=finding.path, status="questioned", reason=f"Ответ модели на ремонт не соответствует контракту: {str(exc)[:500]}", gate="G1"))
                continue
            try:
                document = analysis_data if is_analysis else app_data
                patch_data, changes = normalize_patch(response.model_dump(mode="json", by_alias=True), document)
                record(workspace, changes, "spec.patch", llm)
                updated = apply_patch(document, PatchResponse.model_validate(patch_data), [normalized])
                if not is_analysis:
                    updated, changes = normalize_app(updated)
                    root = pointer(document, normalized.path)
                    if not within(changes, lambda p: p == root or p.startswith(root + "/")):
                        raise PatchRejected("Нормализация патча меняет ссылки вне разрешённого адреса")
                    record(workspace, changes, "spec.patch.result", llm)
                if updated == (analysis_data if is_analysis else app_data):
                    flags.append(ElementFlag(path=finding.path, status="questioned", reason="Предложенный патч отклонён: патч не изменил документ; исправление не выполнено.", gate="G1"))
                    continue
                if is_analysis:
                    Analysis.model_validate(updated)
                    changed_analysis = changed_analysis or updated != analysis_data
                    analysis_data = updated
                else:
                    App.model_validate(updated)
                    changed_app = changed_app or updated != app_data
                    app_data = updated
            except (PatchRejected, ValueError, TypeError) as exc:
                flags.append(ElementFlag(path=finding.path, status="questioned", reason=f"Предложенный патч отклонён: {str(exc)[:500]}", gate="G1"))
    write_json(workspace, ARTIFACT, App.model_validate(app_data))
    artifacts = {"app": ARTIFACT}
    if changed_analysis:
        write_json(workspace, analysis_name, Analysis.model_validate(analysis_data))
        artifacts["analysis"] = analysis_name
    summary = "Применён адресный JSON Patch по находкам G1." if changed_app or changed_analysis else "Изменений по находкам G1 не внесено; требуется повторная проверка гейтом."
    return StageOutput(artifacts=artifacts, summary=summary, flags=flags)
