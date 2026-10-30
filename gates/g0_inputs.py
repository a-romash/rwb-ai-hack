"""G0: чистая проверка контракта, разобранных входов и точности цитат."""
from __future__ import annotations

from pathlib import Path

from contracts.analysis import Analysis
from stages.analysis.compat import ContractError, Finding, GateResult
from stages.analysis.inputs import InputManifest
from stages.analysis.storage import inside, read_json


def validate_quotes(analysis: Analysis, trusted: dict[str, str] | None = None) -> list[Finding]:
    sources = {source.id: source.text for source in analysis.sources}
    findings: list[Finding] = []
    for req in analysis.requirements:
        valid_sources = [source for source in req.source if source in sources]
        valid = bool(req.quote.strip()) and len(valid_sources) == len(req.source) and bool(valid_sources)
        valid = valid and any(req.quote in sources[source] for source in valid_sources)
        if trusted is not None:
            valid = valid and all(source in trusted and trusted[source] == sources[source] for source in valid_sources)
        if not valid:
            findings.append(Finding(path=f"analysis.requirements[{req.id}]", code="REQ_NO_QUOTE", severity="error", message="Цитата требования не подтверждена точным фрагментом исходного источника."))
    return findings


def validate_coverage(analysis: Analysis, noise: list[str]) -> list[Finding]:
    covered = {source for req in analysis.requirements for source in req.source} | set(noise)
    return [Finding(path=f"analysis.sources[{source.id}]", code="SRC_UNCOVERED", severity="warning", message="Фрагмент не покрыт требованием и не отмечен как шум.") for source in analysis.sources if source.id not in covered]


def check(workspace: Path, artifacts: dict[str, str]) -> GateResult:
    workspace = workspace.resolve()
    try:
        analysis = Analysis.model_validate(read_json(workspace, artifacts.get("analysis", "spec/analysis.json")))
    except (ContractError, ValueError, TypeError):
        return GateResult(gate="G0", passed=False, findings=[Finding(path="analysis", code="CONTRACT_ANALYSIS", severity="error", message="Артефакт анализа отсутствует или не соответствует схеме.")])
    findings: list[Finding] = []
    noise: list[str] = []
    trusted: dict[str, str] | None = None
    manifest_name = artifacts.get("analysis_inputs", "spec/analysis-inputs.json")
    if inside(workspace, manifest_name).is_file():
        try:
            manifest = InputManifest.model_validate(read_json(workspace, manifest_name))
            trusted = {source.id: source.text for source in manifest.sources}
            noise = manifest.noise
            for file in manifest.files:
                if file.status != "parsed":
                    findings.append(Finding(path=f"inputs[{file.file}]", code="IN_UNPARSED", severity="warning", message=f"Вход разобран не полностью: {file.reason}."))
        except (ContractError, ValueError, TypeError):
            findings.append(Finding(path="inputs", code="IN_UNPARSED", severity="warning", message="Паспорт разбора входов повреждён."))
    else:
        # Поддержка автономной проверки фикстуры без служебного паспорта.
        trusted = {}
        for source in analysis.sources:
            candidates = [source.file, f"input/{source.file}"]
            for relative in candidates:
                try:
                    path = inside(workspace, relative)
                    if path.is_file() and source.text in path.read_text(encoding="utf-8-sig"):
                        trusted[source.id] = source.text
                        break
                except (OSError, ValueError, ContractError):
                    continue
        inputs = inside(workspace, "input")
        if inputs.is_dir():
            known = {source.file for source in analysis.sources} | {card.file for card in analysis.data_cards}
            for path in sorted(inputs.rglob("*")):
                if path.is_file() and str(path.relative_to(workspace)) not in known and path.name not in known:
                    findings.append(Finding(path=f"inputs[{path.name}]", code="IN_UNPARSED", severity="warning", message="Входной файл отсутствует в разобранных источниках и карточках данных."))
    findings.extend(validate_quotes(analysis, trusted))
    findings.extend(validate_coverage(analysis, noise))
    return GateResult(gate="G0", passed=not any(f.severity == "error" for f in findings), findings=findings)
