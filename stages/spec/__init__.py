"""S4: семь последовательных шагов с валидацией каждого раздела."""
from __future__ import annotations

import copy
import re
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

ARTIFACT = "spec/app.json"
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


def _requests(analysis: Analysis, data: dict, section: str, model: type[BaseModel], llm: LLM) -> list[dict]:
    req_ids = [req.id for req in analysis.requirements]
    groups: list[list[str]] = [req_ids]
    result: list[dict] = []
    while groups:
        group = groups.pop(0)
        payload = _context(analysis, data, section, set(group))
        if size("system-analyst-" + next(step for step, sections in STEPS if any(name == section for name, _ in sections)), payload, model) <= window(llm):
            result.append(payload)
        elif len(group) > 1:
            middle = len(group) // 2
            groups[0:0] = [group[:middle], group[middle:]]
        else:
            # Сохраняем полные определения только затронутых сущностей.
            selected = {story.id for story in analysis.user_stories if set(story.req) & set(group)}
            entities = payload["app"].get("entities", {})
            for name, entity in list(entities.items()):
                if not set(entity.get("traces", [])) & selected:
                    entities[name] = {"fields": list(entity["fields"])}
            agent = "system-analyst-" + next(step for step, sections in STEPS if any(name == section for name, _ in sections))
            if size(agent, payload, model) > window(llm):
                raise BudgetExceeded("Даже контекст одной фичи не помещается в профиль окна")
            result.append(payload)
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
    write_json(workspace, ARTIFACT, App.model_validate(data))
    try:
        for step, sections in STEPS:
            for section, model in sections:
                requests = _requests(analysis, data, section, model, llm)
                for part, payload in enumerate(requests):
                    response = ask(llm, task_class="spec_step", agent=f"system-analyst-{step}", payload=payload, output=model, task_id=f"spec.{section}.{part}")
                    value = response.model_dump(mode="json", by_alias=True, exclude_none=True)
                    value = normalize_section_roles(section, value, analysis.roles)
                    if section == "meta":
                        if not part:
                            data[section] = value
                    else:
                        data[section] = _merge(data[section], value, section, conflicts)
                    # Валидация объединённого раздела на каждом узком шаге.
                    model.model_validate(data[section])
                    write_json(workspace, ARTIFACT, App.model_validate(data))
                completed.append(section)
    except BudgetExceeded as exc:
        flags.append(ElementFlag(path="app", status="questioned", reason=f"Лимит модели: {exc}; сохранена частичная спецификация."))
        notes.append({"stage": "spec", "text": "Незавершённые разделы сохранены пустыми и требуют реализации.", "completed": completed})
    except (ValueError, TypeError) as exc:
        raise ContractError("Раздел спецификации не соответствует контракту") from exc
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
    return StageOutput(artifacts={"app": ARTIFACT, "spec_notes": "spec/spec-notes.json"}, summary=f"Спецификация содержит сущностей: {len(app.entities.root)}; правил в хуках: {len(app.hooks.root)}; команд: {len(app.commands.root)}.", flags=flags)


def repair(inp: StageInput, workspace: Path, llm: LLM, findings: list[Finding]) -> StageOutput:
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
    try:
        for index_, finding in enumerate(findings):
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
            response = ask(llm, task_class="patch", agent="system-analyst-repair", payload=payload, output=PatchResponse, task_id=f"spec.repair.{inp.attempt}.{index_}")
            try:
                updated = apply_patch(document, response, [normalized])
                if is_analysis:
                    Analysis.model_validate(updated)
                    changed_analysis = changed_analysis or updated != analysis_data
                    analysis_data = updated
                else:
                    App.model_validate(updated)
                    changed_app = changed_app or updated != app_data
                    app_data = updated
            except (PatchRejected, ValueError, TypeError):
                flags.append(ElementFlag(path=finding.path, status="questioned", reason="Предложенный патч отклонён; исходный артефакт сохранён.", gate="G1"))
    except BudgetExceeded as exc:
        flags.extend(ElementFlag(path=f.path, status="questioned", reason=f"Лимит адресного ремонта: {exc}.", gate="G1") for f in findings)
    write_json(workspace, ARTIFACT, App.model_validate(app_data))
    artifacts = {"app": ARTIFACT}
    if changed_analysis:
        write_json(workspace, analysis_name, Analysis.model_validate(analysis_data))
        artifacts["analysis"] = analysis_name
    summary = "Применён адресный JSON Patch по находкам G1." if changed_app or changed_analysis else "Изменений по находкам G1 не внесено; требуется повторная проверка гейтом."
    return StageOutput(artifacts=artifacts, summary=summary, flags=flags)
