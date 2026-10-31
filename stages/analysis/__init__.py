"""S2: извлечение → домен → вопросы → синтез → ограниченная ревизия."""
from __future__ import annotations

import re
from pathlib import Path
from pydantic import TypeAdapter

from contracts.analysis import Analysis, Assumption, Role
from stages.analysis.compat import (
    BudgetExceeded, ContractError, ElementFlag, Finding, LLM, Question,
    Sandbox, StageInput, StageOutput, validate_input,
)
from stages.analysis.inputs import InputManifest, ingest
from stages.analysis.models import Acceptance, Constraints, Extraction, Lint, Rules, Skeleton, Stories, stories_schema
from stages.analysis.patching import PatchRejected, PatchResponse, apply_patch, pointer
from stages.analysis.runtime import ask, batches, encoded, size, window
from stages.analysis.storage import file_fingerprint, fingerprint, inside, read_json, write_json
from stages.analysis.symbols import role_id

CHECKPOINT = "spec/analysis-checkpoint.json"
MANIFEST = "spec/analysis-inputs.json"
ARTIFACT = "spec/analysis.json"


def _initial(manifest: InputManifest) -> dict:
    return {
        "schema_version": 1,
        **{key: [] for key in ("requirements", "roles", "glossary", "issues", "questions", "assumptions", "user_stories", "rules", "acceptance", "nfr", "out_of_scope")},
        "sources": [source.model_dump() for source in manifest.sources],
        "data_cards": [card.model_dump() for card in manifest.data_cards],
        "profile": {"modules": ["core"], "platforms": ["web"]},
    }


def _normalize(text: str) -> str:
    return re.sub(r"\W+", " ", text.casefold()).strip()


def _append(data: dict, section: str, values: list[dict], prefix: str) -> None:
    # Последующие шаги видят уже канонические ID; модель их не перенумеровывает.
    for value in values:
        if section == "acceptance":
            from stages.spec.semantics import normalize_gherkin
            value["gherkin"] = normalize_gherkin(value["gherkin"])
        key = "text" if "text" in value else "want" if "want" in value else "gherkin" if "gherkin" in value else None
        previous = next((item for item in data[section] if key and _normalize(item[key]) == _normalize(value[key])), None)
        if previous is not None:
            for name in ("req", "source", "rules", "stories"):
                if name in value:
                    previous[name] = list(dict.fromkeys(previous.get(name, []) + value[name]))
            continue
        value["id"] = f"{prefix}-{len(data[section]) + 1:02d}"
        data[section].append(value)


def _resolve(data: dict, inp: StageInput) -> list[Question]:
    pending: list[Question] = []
    for question in data["questions"]:
        if question["id"] in inp.answers:
            question["answer"] = inp.answers[question["id"]]
            question["answered_by"] = "human"
        elif question.get("answer") is None and inp.autonomy == "A2":
            question["answer"], question["answered_by"] = question["default"], "default"
        if question.get("answer") is None:
            pending.append(Question.model_validate({key: question[key] for key in ("id", "text", "options", "default", "why", "blocking")}))
        elif not any(assumption["source"] == question["id"] for assumption in data["assumptions"]):
            text = f"{question['text']} Ответ: {question['answer']}."
            if question["answered_by"] == "default":
                text = "Требует подтверждения: " + text
            assumption = Assumption(id=f"ASM-{len(data['assumptions']) + 1:02d}", text=text, source=question["id"], params={})
            data["assumptions"].append(assumption.model_dump())
    return pending


def _findings(analysis: Analysis) -> list[Finding]:
    from gates.g0_inputs import validate_quotes
    from gates.g1_spec import ac_not_testable, br_no_ac, br_no_boundary, ref_unresolved, req_uncovered
    from stages.spec.context import empty_app
    from contracts.app import App
    empty = App.model_validate(empty_app(analysis))
    findings = validate_quotes(analysis)
    for validator in (ref_unresolved, req_uncovered, br_no_ac, br_no_boundary, ac_not_testable):
        findings.extend(validator(analysis, empty))
    return [f for f in findings if f.path.startswith("analysis.")]


def _revise(data: dict, llm: LLM, findings: list[Finding], task_id: str, rejected: list[Finding] | None = None) -> dict:
    normalized_by_path = {}
    for finding in findings:
        address = finding.path.removeprefix("analysis.")
        if address in normalized_by_path:
            normalized_by_path[address].message += " " + finding.message
        else:
            normalized_by_path[address] = finding.model_copy(update={"path": address})
    normalized = list(normalized_by_path.values())
    # Один запрос на находку: в контекст попадает только затронутый элемент.
    for index, finding in enumerate(normalized):
        location = pointer(data, finding.path)
        current = data
        for token in location[1:].split("/"):
            token = token.replace("~1", "/").replace("~0", "~")
            current = current[int(token)] if isinstance(current, list) else current.get(token)
        related = set(re.findall(r"(?:REQ|US|BR|AC|ASM)-\d+", finding.message + (encoded(current) if not isinstance(current, list) else "")))
        for _ in range(3):
            for section in ("rules", "user_stories", "acceptance"):
                for item in data[section]:
                    if item["id"] in related:
                        for name in ("req", "rules", "stories"):
                            related.update(item.get(name, []))
        references = {name: [item for item in data[name] if item.get("id") in related] for name in ("requirements", "rules", "user_stories", "acceptance")}
        references["roles"] = data["roles"]
        if isinstance(current, list):
            current = [{key: value for key, value in item.items() if key in ("id", "req", "rules", "stories")} for item in current]
        sources = {source for req in references["requirements"] for source in req["source"]}
        payload = {"finding": finding.model_dump(), "target_pointer": location, "target_value": current,
                   "section_schema": TypeAdapter(Analysis.model_fields[location.split('/')[1]].annotation).json_schema(),
                   "references": references, "sources": [source for source in data["sources"] if source["id"] in sources] if finding.code == "REQ_NO_QUOTE" else []}
        response = ask(llm, task_class="patch", agent="analyst-repair", payload=payload, output=PatchResponse, task_id=f"{task_id}.{index}")
        try:
            patched = apply_patch(data, response, [finding])
            Analysis.model_validate(patched)
            data = patched
        except (PatchRejected, ValueError, TypeError):
            if rejected is not None:
                rejected.append(finding)
    return data


def execute(inp: StageInput, workspace: Path, llm: LLM, sandbox: Sandbox) -> StageOutput:
    inp = validate_input(inp, "analysis")
    manifest = ingest(inp.requirements, inp.attachments, workspace)
    signature_parts = [inp.requirements, encoded(manifest.model_dump(mode="json"))]
    signature_parts += [file_fingerprint(inside(workspace, name)) for name in inp.attachments if inside(workspace, name).is_file()]
    signature = fingerprint("\n".join(signature_parts))
    data = _initial(manifest)
    flags: list[ElementFlag] = []
    if not manifest.sources:
        flags.append(ElementFlag(path="analysis", status="questioned", reason="Не найдено текстовых бизнес-требований; результаты требуют подтверждения."))
    resumed = False
    if inside(workspace, CHECKPOINT).is_file():
        saved = read_json(workspace, CHECKPOINT)
        if not isinstance(saved, dict):
            raise ContractError("Контрольная точка анализа не соответствует схеме")
        if inp.answers and saved.get("signature") != signature:
            raise ContractError("Источники изменились после вопросов; старые ответы применять нельзя")
        if saved.get("signature") == signature and saved.get("phase") == "questions":
            data = saved["analysis"]
            Analysis.model_validate(data)
            manifest = InputManifest.model_validate(saved["manifest"])
            resumed = True
            flags = [ElementFlag.model_validate(item) for item in saved.get("flags", [])]
    try:
        write_json(workspace, ARTIFACT, Analysis.model_validate(data))
        write_json(workspace, MANIFEST, manifest)
        if not resumed:
            pieces = []
            for source in manifest.sources:
                # Максимум 3000 UTF-8 байтов — заведомо не больше 3000 токенов.
                fragment = ""
                for character in source.text:
                    if len((fragment + character).encode()) > 3000:
                        pieces.append({"id": source.id, "file": source.file, "text": fragment})
                        fragment = ""
                    fragment += character
                if fragment:
                    pieces.append({"id": source.id, "file": source.file, "text": fragment})
            for index, payload in enumerate(batches(llm, "analyst-extract", Extraction, pieces, "sources")):
                extracted = ask(llm, task_class="req_extract", agent="analyst-extract", payload=payload, output=Extraction, task_id=f"analysis.extract.{index}")
                _append(data, "requirements", [item.model_dump() for item in extracted.requirements], "REQ")
                source_ids = {source["id"] for source in payload["sources"]}
                manifest.noise.extend(source for source in extracted.noise if source in source_ids)
                write_json(workspace, ARTIFACT, Analysis.model_validate(data))
            covered = {source for req in data["requirements"] for source in req["source"]}
            manifest.noise = sorted(set(manifest.noise) - covered)
            if not data["requirements"]:
                flags.append(ElementFlag(path="analysis", status="questioned", reason="Из источников не извлечено ни одного требования; полнота не подтверждена."))
            write_json(workspace, MANIFEST, manifest)
            for index, payload in enumerate(batches(llm, "analyst-domain", Skeleton, data["requirements"], "requirements")):
                skeleton = ask(llm, task_class="req_extract", agent="analyst-domain", payload=payload, output=Skeleton, task_id=f"analysis.domain.{index}")
                for section, key in (("roles", "id"), ("glossary", "term")):
                    for item in getattr(skeleton, section):
                        value = item.model_dump()
                        if not any(old[key] == value[key] for old in data[section]):
                            data[section].append(value)
                for key in ("modules", "platforms"):
                    data["profile"][key] = list(dict.fromkeys((data["profile"][key] if index else []) + getattr(skeleton.profile, key)))
                write_json(workspace, ARTIFACT, Analysis.model_validate(data))
            cards = data["data_cards"]
            lint_base = {"roles": data["roles"], "data_cards": cards}
            for index, payload in enumerate(batches(llm, "analyst-lint", Lint, data["requirements"], "requirements", lint_base)):
                lint = ask(llm, task_class="req_lint", agent="analyst-lint", payload=payload, output=Lint, task_id=f"analysis.lint.{index}")
                mapping: dict[str, str] = {}
                for question in lint.questions:
                    value = question.model_dump()
                    if len(data["questions"]) < 8:
                        value["id"] = f"Q-{len(data['questions']) + 1:02d}"
                        value["answer"] = value["answered_by"] = None
                        mapping[question.id] = value["id"]
                        data["questions"].append(value)
                    else:
                        origin = next((issue.req for issue in lint.issues if issue.action == question.id), payload["requirements"][0]["id"] if payload["requirements"] else data["sources"][0]["id"] if data["sources"] else question.id)
                        assumption = Assumption(id=f"ASM-{len(data['assumptions']) + 1:02d}", text=f"Требует подтверждения: {question.text} Ответ по умолчанию: {question.default}.", source=origin, params={})
                        mapping[question.id] = assumption.id
                        data["assumptions"].append(assumption.model_dump())
                for assumption in lint.assumptions:
                    value = assumption.model_dump()
                    mapping[assumption.id] = f"ASM-{len(data['assumptions']) + 1:02d}"
                    value["id"] = mapping[assumption.id]
                    value["source"] = mapping.get(value["source"], value["source"])
                    data["assumptions"].append(value)
                for issue in lint.issues:
                    value = issue.model_dump()
                    value["id"] = f"ISS-{len(data['issues']) + 1:02d}"
                    value["action"] = mapping.get(value["action"], value["action"])
                    known_actions = {question["id"] for question in data["questions"]} | {assumption["id"] for assumption in data["assumptions"]}
                    if value["action"] not in known_actions:
                        assumption = Assumption(id=f"ASM-{len(data['assumptions']) + 1:02d}", text=f"Требует подтверждения: {value['problem']} Ответ не определён; связанное требование остаётся под вопросом.", source=value["req"], params={})
                        data["assumptions"].append(assumption.model_dump())
                        value["action"] = assumption.id
                        flags.append(ElementFlag(path=f"analysis.requirements[{value['req']}]", status="questioned", reason="Модель не связала неоднозначность с вопросом или определённым допущением."))
                    data["issues"].append(value)
        if set(inp.answers) - {question["id"] for question in data["questions"]}:
            raise ContractError("Ответы содержат неизвестные идентификаторы вопросов")
        pending = _resolve(data, inp)
        if pending:
            write_json(workspace, CHECKPOINT, {"schema_version": 1, "signature": signature, "phase": "questions", "analysis": data, "manifest": manifest.model_dump(mode="json"), "flags": [flag.model_dump() for flag in flags]})
            write_json(workspace, MANIFEST, manifest)
            write_json(workspace, ARTIFACT, Analysis.model_validate(data))
            return StageOutput(artifacts={"analysis": ARTIFACT, "analysis_inputs": MANIFEST}, summary="Анализ источников выполнен; ожидаются ответы на уточняющие вопросы.", questions=pending, flags=flags)
        base = {"roles": data["roles"], "assumptions": data["assumptions"]}
        declared_roles = [Role.model_validate(role) for role in data["roles"]]
        for section, prefix, response, agent in (("user_stories", "US", Stories, "analyst-stories"), ("rules", "BR", Rules, "analyst-rules"), ("constraints", "NFR", Constraints, "analyst-constraints")):
            if section == "user_stories":
                response = stories_schema(declared_roles)
            for index, payload in enumerate(batches(llm, agent, response, data["requirements"], "requirements", base)):
                result = ask(llm, task_class="req_extract", agent=agent, payload=payload, output=response, task_id=f"analysis.{section}.{index}")
                if section == "constraints":
                    _append(data, "nfr", [item.model_dump() for item in result.nfr], "NFR")
                    for item in result.out_of_scope:
                        if item.model_dump() not in data["out_of_scope"]:
                            data["out_of_scope"].append(item.model_dump())
                else:
                    values = [item.model_dump() for item in getattr(result, section)]
                    if section == "user_stories":
                        for value in values:
                            value["role"] = role_id(value["role"], declared_roles)
                    _append(data, section, values, prefix)
                write_json(workspace, ARTIFACT, Analysis.model_validate(data))
        # AC получает только связанные истории/правила одной группы требований.
        for index, payload in enumerate(batches(llm, "analyst-acceptance", Acceptance, data["rules"] + data["user_stories"], "elements", {"roles": data["roles"]})):
            result = ask(llm, task_class="req_extract", agent="analyst-acceptance", payload=payload, output=Acceptance, task_id=f"analysis.acceptance.{index}")
            _append(data, "acceptance", [item.model_dump() for item in result.acceptance], "AC")
            write_json(workspace, ARTIFACT, Analysis.model_validate(data))
        covered = {rule for item in data["acceptance"] for rule in item["rules"]}
        missing = [rule for rule in data["rules"] if rule["id"] not in covered]
        # A large valid JSON response may still omit rules; regenerate only missing rules in small groups.
        for index, payload in enumerate(batches(llm, "analyst-acceptance", Acceptance, missing, "elements", {"roles": data["roles"]}, item_limit=3) if missing else []):
            requirements = {req for rule in payload["elements"] for req in rule["req"]}
            for story in data["user_stories"]:
                if requirements.intersection(story["req"]):
                    candidate = {**payload, "elements": [*payload["elements"], story]}
                    if size("analyst-acceptance", candidate, Acceptance) <= window(llm):
                        payload = candidate
            result = ask(llm, task_class="req_extract", agent="analyst-acceptance", payload=payload, output=Acceptance, task_id=f"analysis.acceptance.missing.{index}")
            _append(data, "acceptance", [item.model_dump() for item in result.acceptance], "AC")
            write_json(workspace, ARTIFACT, Analysis.model_validate(data))
        covered = {rule for item in data["acceptance"] for rule in item["rules"]}
        missing_ids = [rule["id"] for rule in data["rules"] if rule["id"] not in covered]
        if missing_ids:
            raise ContractError(f"Не созданы критерии приёмки для правил: {', '.join(missing_ids)}")
        for attempt in range(2):
            issues = _findings(Analysis.model_validate(data))
            if not issues:
                break
            before = encoded(data)
            data = _revise(data, llm, issues, f"analysis.revise.{attempt}")
            if encoded(data) == before:
                break
    except BudgetExceeded as exc:
        flags.append(ElementFlag(path="analysis", status="questioned", reason=f"Лимит модели: {exc}; сохранён частичный анализ."))
    except (ValueError, TypeError) as exc:
        raise ContractError("Промежуточный анализ нарушает контракт") from exc
    covered = {rule for item in data["acceptance"] for rule in item["rules"]}
    missing_ids = [rule["id"] for rule in data["rules"] if rule["id"] not in covered]
    if missing_ids:
        raise ContractError(f"Не созданы критерии приёмки для правил: {', '.join(missing_ids)}")
    analysis = Analysis.model_validate(data)
    for issue in _findings(analysis):
        flags.append(ElementFlag(path=issue.path, status="questioned", reason=issue.message, gate="G0" if issue.code == "REQ_NO_QUOTE" else "G1"))
    write_json(workspace, ARTIFACT, analysis)
    write_json(workspace, MANIFEST, manifest)
    write_json(workspace, CHECKPOINT, {"schema_version": 1, "signature": signature, "phase": "complete"})
    return StageOutput(artifacts={"analysis": ARTIFACT, "analysis_inputs": MANIFEST}, summary=f"Разобрано требований: {len(analysis.requirements)}; правил: {len(analysis.rules)}; критериев приёмки: {len(analysis.acceptance)}.", flags=flags)


def repair(inp: StageInput, workspace: Path, llm: LLM, findings: list[Finding]) -> StageOutput:
    validate_input(inp, "analysis")
    data = read_json(workspace, inp.artifacts.get("analysis", ARTIFACT))
    Analysis.model_validate(data)
    original = encoded(data)
    rejected: list[Finding] = []
    # A patch cannot invent requirements from nothing; an empty extraction needs a fresh stage attempt.
    empty = [ElementFlag(path=finding.path, status="questioned", reason="Требования не извлечены; нужен повторный запуск анализа.", gate="G0") for finding in findings if finding.code == "REQ_EMPTY"]
    try:
        data = _revise(data, llm, [finding for finding in findings if finding.code != "REQ_EMPTY"], f"analysis.repair.{inp.attempt}", rejected)
        flags = empty + [ElementFlag(path=f"analysis.{finding.path}", status="questioned", reason="Предложенный патч отклонён; исходный артефакт сохранён.", gate="G0") for finding in rejected]
    except BudgetExceeded:
        flags = empty + [ElementFlag(path=f.path, status="questioned", reason="Бюджет ремонта исчерпан.", gate="G0") for f in findings if f.code != "REQ_EMPTY"]
    write_json(workspace, ARTIFACT, Analysis.model_validate(data))
    summary = "Применён адресный ремонт анализа." if encoded(data) != original else "Изменений в анализ не внесено; требуется повторная проверка гейтом."
    return StageOutput(artifacts={"analysis": ARTIFACT}, summary=summary, flags=flags)
