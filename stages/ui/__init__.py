"""Stage ui: app.json + analysis.json -> spec/ui.json.

A1 (this version): the base is derived by code. Model steps (platforms, refinement, walks,
texts, mobile) come next; until then walks are empty and G1.5 reports WALK_MISSING.
"""
import json
from pathlib import Path

from contracts.stage import ContractError, LLM, Sandbox, StageInput, StageOutput
from harness.fakes import workspace_path
from stages.ui.base import derive_base

OUTPUT = "spec/ui.json"


def _read(workspace: Path, inp: StageInput, name: str) -> dict:
    if name not in inp.artifacts:
        raise ContractError(f"Этапу ui нужен артефакт {name}")
    try:
        return json.loads(workspace_path(workspace, inp.artifacts[name]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"Не удалось прочитать {name}: {exc}") from exc


def execute(inp: StageInput, workspace: Path, llm: LLM, sandbox: Sandbox) -> StageOutput:
    app = _read(workspace, inp, "app")
    _read(workspace, inp, "analysis")
    ui = derive_base(app)
    path = workspace_path(workspace, OUTPUT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ui.model_dump_json(indent=2, exclude_defaults=True) + "\n", encoding="utf-8")
    roles = len(ui.menus)
    return StageOutput(artifacts={"ui": OUTPUT},
                       summary=f"Построено {len(ui.screens)} экранов для {roles} ролей; проходы историй ещё не составлены")
