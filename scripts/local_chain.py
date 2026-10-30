"""Run the build half of the pipeline on a canonical fixture with the real Docker sandbox.

    docker compose run --rm --no-deps -v ./scripts:/app/scripts worker-build \
        python scripts/local_chain.py --fixture tickets

Takes analysis.json, app.json and ui.json from contracts/fixtures/<fixture>, then runs
scaffold -> tests -> develop -> verify -> report with their gates. No model: every model
call raises BudgetExceeded, so stages must degrade honestly (R13) instead of crashing.
The point is the mechanics: restore/build/test in rwb/tool-* images, stand up, smoke.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from contracts.stage import BudgetExceeded, StageInput
from gates.core import run_gate
from harness.fakes import run_stage_locally
from harness.registry import STAGES_BY_KEY
from harness.sandbox import DockerSandbox, host_workspaces_dir

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ("scaffold", "tests", "develop", "verify", "report")


def no_model(**_):
    raise BudgetExceeded("Локальная цепочка запущена без модели")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fixture", default="tickets")
    parser.add_argument("--stages", default=",".join(CHAIN), help="подмножество этапов через запятую")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    base = Path(os.environ.get("WORKSPACES_DIR", ROOT / "workspaces")).resolve()
    root = base / "local" / args.fixture
    run_id = f"local-{args.fixture}"
    fixture = ROOT / "contracts" / "fixtures" / args.fixture
    if "scaffold" in args.stages.split(","):
        shutil.rmtree(root, ignore_errors=True)
        (root / "spec").mkdir(parents=True)
        for name in ("analysis", "app", "ui"):
            shutil.copy(fixture / f"{name}.json", root / "spec" / f"{name}.json")
    artifacts = {name: f"spec/{name}.json" for name in ("analysis", "app", "ui")}
    state = root / "chain.json"
    if state.is_file():
        artifacts.update(json.loads(state.read_text(encoding="utf-8")))

    manifest = json.loads((ROOT / "templates" / "product" / "pack.json").read_text(encoding="utf-8"))
    host_root = host_workspaces_dir(base) / root.relative_to(base)
    sandbox = DockerSandbox(root / "product", run_id, manifest, host_workspace=host_root / "product",
                            report_prefix="product", record=lambda kind, target, r: print(
                                f"    sandbox {kind:<7} {target:<8} {'ok' if r.ok else 'FAIL'} {r.duration_ms / 1000:.1f}s"
                                + ("" if r.ok else f" :: {(r.failed or [''])[0][:200]}")))
    history = []
    for key in args.stages.split(","):
        stage = STAGES_BY_KEY[key]
        module = __import__(stage.module, fromlist=["execute"])
        snapshot = {"status": "partial", "stages": history, "flags": [], "gates": [], "llm_calls": [], "tool_runs": [],
                    "metrics": {"totals": {"calls": 0}}} if key == "report" else None
        inp = StageInput(run_id=run_id, stage=key, attempt=1, autonomy="A2", requirements=(fixture / "requirements.md").read_text(encoding="utf-8"),
                         artifacts=artifacts, snapshot=snapshot)
        print(f"== {key}")
        output = run_stage_locally(module, inp, root, no_model, sandbox)
        for gate in stage.gates:
            output, results = run_gate(gate, module, inp, root, no_model, output, allow_missing=False, sandbox=sandbox)
            last = results[-1]
            print(f"    {gate}: {'ok' if last.passed else 'не пройден'}, находок {len(last.findings)}")
            for finding in last.findings[:8]:
                print(f"      {finding.severity:<7} {finding.code:<22} {finding.path} — {finding.message[:140]}")
        artifacts.update(output.artifacts)
        state.write_text(json.dumps(artifacts, ensure_ascii=False, indent=2), encoding="utf-8")
        history.append({"stage": key, "status": "succeeded", "attempt": 1, "error": None})
        print(f"    {output.summary}")
        for flag in output.flags[:5]:
            print(f"    flag {flag.status}: {flag.path} — {flag.reason[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
