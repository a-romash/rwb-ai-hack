from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from contracts.analysis import Analysis
from contracts.app import App
from stages.analysis.compat import BudgetExceeded, StageFailed
from stages.analysis.models import Extraction
from stages.spec.eval import continue_context_limited_repair, evaluate, prompt_hashes
from stages.spec.eval_gateway import EvalGateway

ROOT = Path(__file__).resolve().parents[3]


class FakeHTTPResponse:
    def __init__(self, payload: dict):
        self.payload = json.dumps(payload).encode()

    def read(self, *args):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None


class EvalTests(unittest.TestCase):
    def test_repair_continuation_preserves_prior_failure_and_spend(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = evaluate("tickets", ROOT / "contracts/fixtures/tickets/requirements.md", workspace,
                              mode="recorded", model="unused", context_window=32768, max_tokens=100000, max_calls=100)
            app_path = workspace / "spec/app.json"
            app = json.loads(app_path.read_text())
            del app["hooks"]["ResolutionRequired"]
            app_path.write_text(json.dumps(app))
            result.update(mode="live", model="qwen/qwen3.8-27b", status="contract_error",
                          error_type="ContractError", reason="Контекст запроса превышает профиль окна", tokens=100,
                          calls=[{"task_id": "spec.repair.1.0", "total_tokens": 100}])
            with patch("stages.spec.eval.EvalGateway") as factory:
                factory.return_value.side_effect = BudgetExceeded("Тестовый лимит")
                continued = continue_context_limited_repair(result)
            self.assertEqual(continued["status"], "partial")
            self.assertEqual(continued["tokens"], 100)
            self.assertEqual(continued["prior_failure"]["status"], "contract_error")
            self.assertGreater(continued["g1_after"], 0)
            self.assertTrue(continued["flags"])
            self.assertEqual(result["status"], "contract_error")
            self.assertTrue((workspace / "reports/eval-continued.json").is_file())

    def test_unrelated_contract_errors_cannot_be_promoted_by_continuation(self) -> None:
        with self.assertRaises(ValueError):
            continue_context_limited_repair({"mode": "live", "status": "contract_error", "reason": "Неверная схема"})

    def test_both_domains_recorded_pass_end_to_end(self) -> None:
        for name in ("tickets", "equipment"):
            with self.subTest(case=name), tempfile.TemporaryDirectory() as tmp:
                folder = ROOT / "contracts/fixtures" / name
                Analysis.model_validate_json((folder / "analysis.json").read_text())
                App.model_validate_json((folder / "app.json").read_text())
                result = evaluate(name, folder / "requirements.md", Path(tmp), mode="recorded", model="unused", context_window=32768, max_tokens=100000, max_calls=100)
                self.assertEqual(result["status"], "passed", result.get("reason"))
                self.assertEqual(result["g0_after"], 0)
                self.assertEqual(result["g1_after"], 0)
                self.assertEqual(result["quote_rate"], 1)
                self.assertEqual(result["br_ac_rate"], 1)
                self.assertIsNone(result["tokens"])

    def test_missing_case_is_not_reported_as_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = evaluate("case1", None, Path(tmp), mode="live", model="qwen/qwen3.8-27b", context_window=32768, max_tokens=100000, max_calls=100)
        self.assertEqual(result["status"], "missing_input")
        self.assertIsNone(result["quote_rate"])
        self.assertEqual(result["calls"], [])

    def test_prompt_changes_require_a_new_recorded_eval(self) -> None:
        results = json.loads((ROOT / "stages/spec/EVAL-recorded.json").read_text())
        self.assertEqual(results["prompt_hashes"], prompt_hashes())
        self.assertTrue(all(row["status"] == "passed" for row in results["results"] if row["case"] in ("tickets", "equipment")))

    def test_gateway_is_stateless_and_records_actual_usage(self) -> None:
        sent: list[dict] = []
        def request(req, timeout):
            sent.append(json.loads(req.data))
            return FakeHTTPResponse({"model": "qwen/qwen3.8-27b", "choices": [{"message": {"content": json.dumps({"result": {"requirements": [], "noise": []}})}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}})
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-only-secret"}), patch("urllib.request.urlopen", request):
            gateway = EvalGateway(workspace=Path(tmp))
            for index in range(2):
                result = gateway(task_class="req_extract", system="System", user=f"Input {index}", output=Extraction, task_id=str(index))
                self.assertEqual(result.requirements, [])
            self.assertEqual(gateway.tokens_used, 30)
            self.assertEqual(len(sent[0]["messages"]), 2)
            self.assertIn("OUTPUT_SCHEMA", sent[0]["messages"][0]["content"])
            self.assertIn('"requirements"', sent[0]["messages"][0]["content"])
            self.assertEqual(len(sent[1]["messages"]), 2)
            self.assertNotIn("Input 0", str(sent[1]))
            self.assertNotIn("test-only-secret", str(gateway.calls))
            self.assertEqual(gateway.calls[0]["total_tokens"], 15)

    def test_gateway_enforces_budget_before_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gateway = EvalGateway(workspace=Path(tmp), max_calls=0)
            with self.assertRaises(BudgetExceeded):
                gateway(task_class="req_extract", system="", user="", output=Extraction)

    def test_gateway_reserves_input_tokens_in_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-only-secret"}), patch("urllib.request.urlopen") as network:
            gateway = EvalGateway(workspace=Path(tmp), max_tokens=100)
            with self.assertRaises(BudgetExceeded):
                gateway(task_class="req_extract", system="System", user="Input", output=Extraction)
            network.assert_not_called()
            self.assertEqual(gateway.calls, [])

    def test_gateway_rejects_model_substitution(self) -> None:
        response = {"model": "different/model", "choices": [], "usage": {}}
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-only-secret"}), patch("urllib.request.urlopen", return_value=FakeHTTPResponse(response)):
            gateway = EvalGateway(workspace=Path(tmp))
            with self.assertRaises(StageFailed):
                gateway(task_class="req_extract", system="", user="", output=Extraction)


if __name__ == "__main__":
    unittest.main()
