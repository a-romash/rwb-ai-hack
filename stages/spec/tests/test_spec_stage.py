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

    def test_invalid_foundation_is_regenerated_before_behavior(self) -> None:
        original = copy.deepcopy(self.responses["spec.entities.0"])
        self.responses["spec.entities.0"] = {"section": next(iter(original.values()))}
        self.responses["spec.foundation.entities.0"] = original
        llm = FakeLLM(self.responses)
        execute(self.inp, self.workspace, llm, FakeSandbox())
        model = App.model_validate_json((self.workspace / "spec/app.json").read_text())
        self.assertIn("Ticket", model.entities.root)
        ids = [call["task_id"] for call in llm.calls]
        self.assertLess(ids.index("spec.foundation.entities.0"), ids.index("spec.state_machines.0"))

    def test_foundation_feedback_is_included_when_splitting_context(self) -> None:
        from types import SimpleNamespace
        from contracts.analysis import Analysis
        from contracts.app import EntitiesSection
        from stages.analysis.runtime import size
        from stages.spec import _requests
        from stages.spec.context import empty_app
        analysis = Analysis.model_validate_json((self.workspace / "spec/analysis.json").read_text())
        errors = [{"path": f"permissions[{i}].op", "message": "x" * 400} for i in range(50)]
        requests = _requests(analysis, empty_app(analysis), "entities", EntitiesSection, SimpleNamespace(context_window=16000), validation_errors=errors)
        self.assertGreater(len(requests), 1)
        self.assertTrue(all(size("system-analyst-domain", payload, EntitiesSection) <= 16000 for payload in requests))
        self.assertEqual({error["path"] for payload in requests for error in payload["validation_errors"]}, {error["path"] for error in errors})

    def test_one_oversized_foundation_error_reports_context_limit(self) -> None:
        from types import SimpleNamespace
        from contracts.analysis import Analysis
        from contracts.app import EntitiesSection
        from stages.spec import _requests
        from stages.spec.context import empty_app
        analysis = Analysis.model_validate_json((self.workspace / "spec/analysis.json").read_text())
        with self.assertRaisesRegex(ContractError, "контекст"):
            _requests(analysis, empty_app(analysis), "entities", EntitiesSection, SimpleNamespace(context_window=16000), validation_errors=[{"message": "x" * 40000}])

    def test_invalid_foundation_after_retry_is_not_accepted(self) -> None:
        original = self.responses["spec.entities.0"]
        self.responses["spec.entities.0"] = {"section": next(iter(original.values()))}
        self.responses["spec.foundation.entities.0"] = self.responses["spec.entities.0"]
        with self.assertRaisesRegex(ContractError, "связ"):
            execute(self.inp, self.workspace, FakeLLM(self.responses), FakeSandbox())

    def test_budget_exhaustion_during_foundation_repair_stops_stage(self) -> None:
        original = self.responses["spec.entities.0"]
        self.responses["spec.entities.0"] = {"section": next(iter(original.values()))}
        self.responses["spec.foundation.entities.0"] = BudgetExceeded()
        with self.assertRaisesRegex(ContractError, "связ"):
            execute(self.inp, self.workspace, FakeLLM(self.responses), FakeSandbox())

    def test_future_command_permissions_are_not_checked_early(self) -> None:
        from stages.spec import _foundation_findings
        from contracts.analysis import Analysis
        execute(self.inp, self.workspace, FakeLLM(self.responses), FakeSandbox())
        data = json.loads((self.workspace / "spec/app.json").read_text())
        data["permissions"].append({"role": data["permissions"][0]["role"], "op": "FutureCommand", "scope": "all"})
        analysis = Analysis.model_validate_json((self.workspace / "spec/analysis.json").read_text())
        self.assertFalse(_foundation_findings(analysis, data))

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

    def test_findings_on_one_element_share_one_repair_call(self) -> None:
        self.responses["spec.state_machines.0"]["TicketFlow"]["states"].append("isolated")
        execute(self.inp, self.workspace, FakeLLM(self.responses), FakeSandbox())
        finding = next(f for f in g1(self.workspace, self.inp.artifacts).findings if f.code == "SM_UNREACHABLE")
        llm = FakeLLM({"patch": {"operations": [{"op": "remove", "path": "/state_machines/TicketFlow/states/4"}]}})
        repair(self.inp, self.workspace, llm, [finding, finding.model_copy(update={"code": "SM_DEADLOCK", "message": "Тупик."})])
        self.assertEqual(len(llm.calls), 1)
        self.assertIn("Тупик.", llm.calls[0]["user"])
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

    def test_second_repair_receives_reason_first_patch_was_rejected(self) -> None:
        execute(self.inp, self.workspace, FakeLLM(self.responses), FakeSandbox())
        finding = Finding(path="hooks", code="BR_NO_HOOK", severity="error", message="Нет хука.")
        first = repair(self.inp, self.workspace, FakeLLM({"patch": {"operations": [{"op": "replace", "path": "/hooks", "value": {}}]}}), [finding])
        llm = FakeLLM({"patch": {"operations": []}})
        repair(self.inp, self.workspace, llm, [finding], previous_output=first)
        self.assertIn("Замена корня или целого раздела запрещена", llm.calls[0]["user"])

    def test_second_repair_is_told_when_patch_did_not_change_document(self) -> None:
        execute(self.inp, self.workspace, FakeLLM(self.responses), FakeSandbox())
        finding = Finding(path="hooks", code="BR_NO_HOOK", severity="error", message="Нет хука.")
        first = repair(self.inp, self.workspace, FakeLLM({"patch": {"operations": []}}), [finding])
        llm = FakeLLM({"patch": {"operations": []}})
        repair(self.inp, self.workspace, llm, [finding], previous_output=first)
        self.assertIn("не изменил", llm.calls[0]["user"])

    def test_repair_context_shrinks_before_giving_up(self) -> None:
        from stages.spec import _fit_repair
        payload = {"finding": {}, "target_pointer": "/hooks", "target_value": {}, "section_schema": {}, "binding_rules": {}, "app": {"entities": {}},
                   "analysis": {"requirements": [], "roles": [], "rules": [], "user_stories": [{"text": "x" * 40000}]}}
        self.assertNotIn("user_stories", _fit_repair(payload, 32768)["analysis"])
        self.assertIsNone(_fit_repair({**payload, "target_value": "x" * 40000}, 32768))

    def test_obvious_entity_targets_are_bound_by_field_name(self) -> None:
        from stages.spec import bind_entities
        # Shape of the case 1 answer: no ref targets and aggregate names in owner.
        value = {"Vehicle": {"owner": "FleetDomain", "fields": {"driver": {"type": "ref"}, "currentZone": {"type": "ref"}, "movementState": {"type": "enum"}, "points": {"type": "ref"}}},
                 "ParkingSession": {"owner": "vehicleId", "fields": {"vehicleId": {"type": "ref"}, "status": {"type": "enum"}}},
                 "Driver": {"fields": {}}, "ParkingZone": {"fields": {}}, "Tariff": {"fields": {"periods": {"type": "ref"}}}, "TariffPeriod": {"fields": {}}}
        data = {"types": {"ParkingSessionStatus": {"kind": "enum"}, "RouteStatus": {"kind": "enum"}, "MovementState": {"kind": "enum"}}}
        bound = bind_entities(value, data)
        self.assertEqual({key: field.get("ref") for key, field in bound["Vehicle"]["fields"].items()},
                         {"driver": "Driver", "currentZone": "ParkingZone", "movementState": "MovementState", "points": None})
        self.assertEqual(bound["ParkingSession"]["fields"]["vehicleId"]["ref"], "Vehicle")
        self.assertEqual(bound["ParkingSession"]["fields"]["status"]["ref"], "ParkingSessionStatus")
        self.assertEqual(bound["Tariff"]["fields"]["periods"]["ref"], "TariffPeriod")
        self.assertNotIn("owner", bound["Vehicle"])
        self.assertEqual(bound["ParkingSession"]["owner"], "vehicleId")

    def test_bad_contract_cannot_be_repaired_silently(self) -> None:
        self.responses["spec.entities.0"] = {"Bad": {"extra": "unsupported"}}
        with self.assertRaises(ContractError):
            execute(self.inp, self.workspace, FakeLLM(self.responses), FakeSandbox())


if __name__ == "__main__":
    unittest.main()
