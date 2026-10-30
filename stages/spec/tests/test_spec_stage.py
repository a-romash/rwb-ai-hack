from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from contracts.app import App
from gates.g1_spec import check as g1
from stages.analysis.compat import BudgetExceeded, ContractError, Finding, StageInput
from stages.analysis.patching import PatchResponse, apply_patch
from stages.analysis.testing import FakeLLM, FakeSandbox
from stages.spec import execute, repair

ROOT = Path(__file__).resolve().parents[3]


class SpecStageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name)
        (self.workspace / "spec").mkdir()
        self.requirements = (ROOT / "contracts/fixtures/tickets/requirements.md").read_text()
        (self.workspace / "spec/analysis.json").write_text((ROOT / "contracts/fixtures/tickets/analysis.json").read_text())
        self.responses = json.loads((Path(__file__).parent / "fixtures/tickets-responses.json").read_text())
        self.inp = StageInput(run_id="test", stage="spec", attempt=1, requirements=self.requirements, artifacts={"analysis": "spec/analysis.json", "app": "spec/app.json"})

    def test_spec_seven_steps_seventeen_sections(self) -> None:
        llm = FakeLLM(self.responses)
        out = execute(self.inp, self.workspace, llm, FakeSandbox())
        self.assertFalse(out.flags)
        self.assertTrue(g1(self.workspace, out.artifacts | {"analysis": "spec/analysis.json"}).passed)
        self.assertEqual(len(llm.calls), 17)
        self.assertEqual(len({call["output"] for call in llm.calls}), 17)
        self.assertTrue(all(call["task_class"] == "spec_step" for call in llm.calls))

    def test_spec_budget_creates_partial_app(self) -> None:
        self.responses["spec.state_machines.0"] = BudgetExceeded()
        out = execute(self.inp, self.workspace, FakeLLM(self.responses), FakeSandbox())
        self.assertTrue(out.flags)
        model = App.model_validate_json((self.workspace / "spec/app.json").read_text())
        self.assertTrue(model.entities.root)
        self.assertEqual(model.state_machines.root, {})

    def test_addressed_repair_fixes_unreachable_state(self) -> None:
        self.responses["spec.state_machines.0"]["TicketFlow"]["states"].append("isolated")
        execute(self.inp, self.workspace, FakeLLM(self.responses), FakeSandbox())
        before = json.loads((self.workspace / "spec/app.json").read_text())
        findings = [f for f in g1(self.workspace, self.inp.artifacts).findings if f.code == "SM_UNREACHABLE"]
        llm = FakeLLM({"patch": {"operations": [{"op": "remove", "path": "/state_machines/TicketFlow/states/4"}]}})
        repair(self.inp, self.workspace, llm, findings)
        after = json.loads((self.workspace / "spec/app.json").read_text())
        before["state_machines"]["TicketFlow"]["states"].pop()
        self.assertEqual(before, after)
        self.assertTrue(g1(self.workspace, self.inp.artifacts).passed)

    def test_patch_rejects_outside_changes_and_document_is_unchanged(self) -> None:
        original = {"state_machines": {"Flow": {"states": ["new", "extra"]}}, "meta": {"name": "old"}}
        findings = [Finding(path="state_machines.Flow.states[1]", code="SM_UNREACHABLE", severity="error", message="Недостижимо.")]
        patch = PatchResponse.model_validate({"operations": [{"op": "remove", "path": "/state_machines/Flow/states/1"}, {"op": "replace", "path": "/meta/name", "value": "changed"}]})
        before = copy.deepcopy(original)
        with self.assertRaises(ContractError):
            apply_patch(original, patch, findings)
        self.assertEqual(before, original)

    def test_patch_test_copy_move_and_pointer_escaping(self) -> None:
        original = {"items": {"a/b": {"x": 1, "y": 2}}}
        findings = [Finding(path="/items/a~1b", code="TEST", severity="error", message="Тест.")]
        patch = PatchResponse.model_validate({"operations": [
            {"op": "test", "path": "/items/a~1b/x", "value": 1},
            {"op": "copy", "from": "/items/a~1b/x", "path": "/items/a~1b/z"},
            {"op": "move", "from": "/items/a~1b/y", "path": "/items/a~1b/w"},
        ]})
        self.assertEqual(apply_patch(original, patch, findings)["items"]["a/b"], {"x": 1, "z": 1, "w": 2})

    def test_whole_section_replacement_rejected(self) -> None:
        findings = [Finding(path="hooks", code="BR_NO_HOOK", severity="error", message="Нет хука.")]
        patch = PatchResponse.model_validate({"operations": [{"op": "replace", "path": "/hooks", "value": {}}]})
        with self.assertRaises(ContractError):
            apply_patch({"hooks": {"Existing": {}}}, patch, findings)

    def test_patch_cannot_rename_stable_ids(self) -> None:
        document = {"requirements": [{"id": "REQ-01", "text": "Исходный текст"}]}
        findings = [Finding(path="requirements[REQ-01]", code="REQ_NO_QUOTE", severity="error", message="Цитата.")]
        for operation in ({"op": "remove", "path": "/requirements/0"}, {"op": "replace", "path": "/requirements/0/id", "value": "REQ-99"}, {"op": "replace", "path": "/requirements/0", "value": {"id": "REQ-99", "text": "Другой текст"}}):
            with self.subTest(operation=operation), self.assertRaises(ContractError):
                apply_patch(document, PatchResponse.model_validate({"operations": [operation]}), findings)

    def test_repair_context_limit_preserves_valid_artifacts(self) -> None:
        execute(self.inp, self.workspace, FakeLLM(self.responses), FakeSandbox())
        before = (self.workspace / "spec/app.json").read_bytes()
        finding = Finding(path="hooks", code="BR_NO_HOOK", severity="error", message="Требуется ремонт.")
        llm = FakeLLM({}, context_window=1024)
        output = repair(self.inp, self.workspace, llm, [finding])
        self.assertEqual(before, (self.workspace / "spec/app.json").read_bytes())
        self.assertTrue(output.flags)
        self.assertIn("окна", output.flags[-1].reason)
        self.assertEqual(llm.calls, [])

    def test_bad_contract_cannot_be_repaired_silently(self) -> None:
        self.responses["spec.entities.0"] = {"Bad": {"extra": "unsupported"}}
        with self.assertRaises(ContractError):
            execute(self.inp, self.workspace, FakeLLM(self.responses), FakeSandbox())


if __name__ == "__main__":
    unittest.main()
