import importlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel, ValidationError

from contracts.api import MetricsRead, MetricTotals, RunCreate
from contracts.gates import ElementFlag as GateFlag
from contracts.stage import BudgetExceeded, ContractError, ElementFlag, SandboxResult, StageInput, StageOutput
from harness.fakes import FakeLLM, FakeSandbox, run_stage_locally
from harness.registry import STAGES


class Answer(BaseModel):
    value: int


class ContractTest(unittest.TestCase):
    def call(self, llm, **kwargs):
        return llm(task_class="qa", system="s", user="u", output=Answer, **kwargs)

    def inp(self, **kwargs):
        return StageInput(run_id="test", stage="analysis", attempt=1, requirements="r", artifacts={}, **kwargs)

    def test_llm_typed_responses_task_priority_and_order(self):
        fake = FakeLLM({"qa": [{"value": 1}, '{"value":2}'], ("qa", "AC-01"): [{"value": 3}]})
        self.assertEqual(self.call(fake, task_id="AC-01").value, 3)
        self.assertEqual(self.call(fake).value, 1)
        self.assertEqual(self.call(fake).value, 2)
        self.assertEqual(len(fake.calls), 3)
        with self.assertRaises(AssertionError):
            self.call(fake)

    def test_invalid_model_is_contract_error(self):
        with self.assertRaises(ContractError):
            self.call(FakeLLM({"qa": [{"value": "bad"}]}))

    def test_budget_and_scripted_exception(self):
        fake = FakeLLM({"qa": [{"value": 1}]}, budget_after=1)
        self.call(fake)
        with self.assertRaises(BudgetExceeded):
            self.call(fake)
        self.assertEqual(len(fake.calls), 2)
        with self.assertRaises(RuntimeError):
            self.call(FakeLLM({"qa": [RuntimeError("offline")]}))

    def test_text_and_code_return_decoded_content(self):
        fake = FakeLLM({"writer": ["# Отчёт"], "hook_1": ["return 1;"]})
        for key, mode, expected in [("writer", "text", "# Отчёт"), ("hook_1", "code", "return 1;")]:
            self.assertEqual(fake(task_class=key, system="", user="", output=mode), expected)

    def test_sandbox_calls_and_results(self):
        result = SandboxResult(ok=False, exit_code=1, duration_ms=2, failed=["AC-01"], output_tail="failed")
        fake = FakeSandbox({("test", "backend"): [result]})
        self.assertFalse(fake.run("test", "backend", filter="AC-01", timeout_s=3).ok)
        self.assertEqual(fake.calls[0]["filter"], "AC-01")
        self.assertEqual(fake.calls[0]["timeout_s"], 3)
        with self.assertRaises(AssertionError):
            fake.run("test", "backend")

    def test_mutable_defaults_and_flag_identity(self):
        first, second = self.inp(), self.inp()
        first.answers["Q-01"] = "yes"
        self.assertEqual(second.answers, {})
        self.assertIs(ElementFlag, GateFlag)
        self.assertEqual(RunCreate().budget.tokens, 1_500_000)
        with self.assertRaises(ValidationError):
            RunCreate(budget={"tokens": 0})
        self.assertIsNone(MetricsRead(totals=MetricTotals()).totals.tokens_in)

    def test_runner_rejects_bad_outputs_and_missing_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for output in ({"artifacts": {}}, {"artifacts": {"x": "missing"}, "summary": "x"}):
                module = SimpleNamespace(execute=lambda *args: output)
                with self.assertRaises(ContractError):
                    run_stage_locally(module, self.inp(), root, FakeLLM({}), FakeSandbox({}))
            inp = self.inp(attachments=["input/missing.pdf"])
            with self.assertRaises(ContractError):
                run_stage_locally(SimpleNamespace(), inp, root, FakeLLM({}), FakeSandbox({}))

    def test_runner_rejects_traversal_absolute_and_symlink_paths(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            (root / "link").symlink_to(outside, target_is_directory=True)
            (root / "folder").mkdir()
            (root / "folder" / "link").symlink_to(outside, target_is_directory=True)
            for relative in ("../escape", outside, "link", "folder", ""):
                module = SimpleNamespace(execute=lambda *args: StageOutput(artifacts={"x": relative}, summary="x"))
                with self.assertRaises(ContractError, msg=relative):
                    run_stage_locally(module, self.inp(), root, FakeLLM({}), FakeSandbox({}))

    def test_all_fake_stages_run_without_platform(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = {}
            llm, sandbox = FakeLLM({}), FakeSandbox({})
            seen = set()
            for stage in STAGES:
                self.assertTrue(set(stage.deps) <= seen)
                module = importlib.import_module(f"harness.fake_stages.{stage.key}")
                inp = StageInput(run_id="test", stage=stage.key, attempt=1, requirements="r", artifacts=artifacts)
                output = run_stage_locally(module, inp, Path(tmp), llm, sandbox)
                artifacts.update(output.artifacts)
                seen.add(stage.key)
            self.assertTrue(json.loads((Path(tmp) / artifacts["report"]).read_text())["fake"])
            self.assertEqual(llm.calls, [])
            self.assertEqual(sandbox.calls, [])
            self.assertEqual(len(seen), 8)

    def test_docker_stages_use_build_queue(self):
        stages = {stage.key: stage for stage in STAGES}
        for key in ("scaffold", "tests", "develop", "verify"):
            self.assertEqual(stages[key].queue, "build")
        self.assertTrue(stages["report"].always)
        self.assertEqual(stages["verify"].gates, ("G3", "G4"))


if __name__ == "__main__":
    unittest.main()
