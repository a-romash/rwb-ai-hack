import json
from pathlib import Path

from contracts.stage import ContractError, LLM, Sandbox, StageInput, StageOutput
from harness.fakes import workspace_path

OUTPUTS = {
    "analysis": {"analysis": "spec/analysis.json"},
    "spec": {"app": "spec/app.json"},
    "ui": {"ui": "spec/ui.json"},
    "scaffold": {"product": "product", "hooks": "product/hooks.json", "openapi": "product/openapi.json"},
    "tests": {"tests": "reports/tests.json"},
    "develop": {"develop": "reports/develop.json"},
    "verify": {"verification": "reports/verification.json"},
    "report": {"report": "reports/report.json", "report_markdown": "reports/report.md"},
}


def execute(inp: StageInput, workspace: Path, llm: LLM, sandbox: Sandbox) -> StageOutput:
    """Write platform-only placeholders, not artifacts conforming to business schemas."""
    if inp.stage not in OUTPUTS:
        raise ContractError(f"Неизвестный фейковый этап: {inp.stage}")
    artifacts = OUTPUTS[inp.stage]
    for name, relative in artifacts.items():
        path = workspace_path(workspace, relative)
        if name == "product":
            path.mkdir(parents=True, exist_ok=True)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": 1, "fake": True, "stage": inp.stage}
        if inp.stage == "report":
            payload["snapshot"] = inp.snapshot
        if path.suffix == ".md":
            path.write_text("# Фейковый отчёт\n\nТолько проверка связности. Продукт не проверен.\n", encoding="utf-8")
        else:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return StageOutput(artifacts=artifacts, summary=f"Фейковый этап {inp.stage}: только проверка связности")
