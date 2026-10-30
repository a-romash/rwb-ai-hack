"""Stage ui: app.json + analysis.json -> spec/ui.json.

A1 derives the base by code; A2 refines it with short checked model calls (stages/ui/steps.py).
If the budget runs out the stage still writes a valid ui.json and reports what is missing.
"""
import json
from pathlib import Path
from typing import TYPE_CHECKING

from contracts.gates import Finding
from contracts.stage import BudgetExceeded, ContractError, ElementFlag, LLM, Sandbox, StageInput, StageOutput
from contracts.ui import UiSpec
from harness.fakes import workspace_path

# Model steps import gate G1.5, which imports stages.ui.appview; keep this package import-light.
if TYPE_CHECKING:
    from stages.ui.steps import Builder

OUTPUT = "spec/ui.json"


def _read(workspace: Path, inp: StageInput, name: str) -> dict:
    if name not in inp.artifacts:
        raise ContractError(f"Этапу ui нужен артефакт {name}")
    try:
        return json.loads(workspace_path(workspace, inp.artifacts[name]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"Не удалось прочитать {name}: {exc}") from exc


def _write(workspace: Path, builder: "Builder") -> None:
    path = workspace_path(workspace, OUTPUT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(builder.ui.model_dump_json(indent=2, by_alias=True, exclude_defaults=True) + "\n",
                    encoding="utf-8")


def _output(builder: "Builder", done: str) -> StageOutput:
    stories = len(builder.stories)
    missing = [s["id"] for s in builder.stories if s["id"] not in builder.ui.walks]
    flags = list(builder.flags)
    known = {f.path for f in flags}
    flags += [ElementFlag(path=f"walks.{us}", status="questioned", gate="G1.5", reason="Проход не составлен")
              for us in missing if f"walks.{us}" not in known]
    summary = (f"{done}: {len(builder.ui.screens)} экранов, проходов {stories - len(missing)} из {stories}"
               + (f"; {'; '.join(builder.notes[:3])}" if builder.notes else ""))
    return StageOutput(artifacts={"ui": OUTPUT}, summary=summary, flags=flags)


def execute(inp: StageInput, workspace: Path, llm: LLM, sandbox: Sandbox) -> StageOutput:
    from stages.ui.base import derive_base
    from stages.ui.steps import Builder

    app = _read(workspace, inp, "app")
    analysis = _read(workspace, inp, "analysis")
    builder = Builder(app_raw=app, analysis=analysis, ui=derive_base(app), requirements=inp.requirements)
    done = "Интерфейс спроектирован"
    try:
        builder.plan_platforms(llm)
        builder.refine(llm)
        builder.make_walks(llm)
        builder.texts(llm)
        builder.devices(llm)
    except BudgetExceeded:
        builder.notes.insert(0, "бюджет модели исчерпан, часть шагов пропущена")
        done = "Интерфейс спроектирован частично"
    _write(workspace, builder)
    return _output(builder, done)


def repair(inp: StageInput, workspace: Path, llm: LLM, findings: list[Finding]) -> StageOutput:
    from stages.ui.steps import Builder

    app = _read(workspace, inp, "app")
    analysis = _read(workspace, inp, "analysis")
    try:
        ui = UiSpec.model_validate(json.loads(workspace_path(workspace, OUTPUT).read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        raise ContractError(f"Нечего исправлять: {OUTPUT} не читается") from exc
    builder = Builder(app_raw=app, analysis=analysis, ui=ui, requirements=inp.requirements)
    done = "Интерфейс исправлен по G1.5"
    try:
        builder.repair(llm, findings)
    except BudgetExceeded:
        builder.notes.insert(0, "бюджет модели исчерпан во время исправления")
        done = "Интерфейс исправлен частично"
    _write(workspace, builder)
    return _output(builder, done)
