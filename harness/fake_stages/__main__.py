"""Run: python -m harness.fake_stages [--workspace /path/to/empty/directory]."""
import argparse
import importlib
import tempfile
from pathlib import Path

from contracts.stage import StageInput
from harness.fakes import FakeLLM, FakeSandbox, run_stage_locally
from harness.registry import STAGES


def run(workspace: Path) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    for stage in STAGES:
        module = importlib.import_module(f"harness.fake_stages.{stage.key}")
        inp = StageInput(run_id="local-fake", stage=stage.key, attempt=1,
                         requirements="Проверка платформы без доменной логики", artifacts=artifacts,
                         snapshot={"fake": True} if stage.key == "report" else None)
        result = run_stage_locally(module, inp, workspace, FakeLLM({}), FakeSandbox({}))
        artifacts.update(result.artifacts)
        print(result.summary)
    return artifacts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path)
    args = parser.parse_args()
    if args.workspace is None:
        with tempfile.TemporaryDirectory() as folder:
            run(Path(folder))
    else:
        if args.workspace.exists() and any(args.workspace.iterdir()):
            parser.error("workspace должен быть пустым: фейковые этапы записывают артефакты")
        run(args.workspace)


if __name__ == "__main__":
    main()
