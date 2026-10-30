from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from contracts.analysis import Analysis
from contracts.app import App
from gates import g0_inputs, g1_spec

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "contracts/fixtures/tickets"


class GateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.analysis = json.loads((FIXTURE / "analysis.json").read_text())
        self.app = json.loads((FIXTURE / "app.json").read_text())
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name)
        (self.workspace / "spec").mkdir()
        (self.workspace / "requirements.md").write_text((FIXTURE / "requirements.md").read_text())
        self.save()

    def save(self) -> None:
        for name, value in (("analysis", self.analysis), ("app", self.app)):
            (self.workspace / f"spec/{name}.json").write_text(json.dumps(value, ensure_ascii=False))

    def errors(self, code: str):
        before = copy.deepcopy((self.analysis, self.app))
        result = g1_spec.VALIDATORS[code](Analysis.model_validate(self.analysis), App.model_validate(self.app))
        self.assertTrue(result, code)
        self.assertTrue(all(finding.code == code and finding.path and finding.message for finding in result))
        self.assertEqual(before, (self.analysis, self.app))
        return result

    def test_clean_fixture_passes_both_gates(self) -> None:
        self.assertEqual(g0_inputs.check(self.workspace, {}).findings, [])
        self.assertEqual(g1_spec.check(self.workspace, {}).findings, [])
        self.assertEqual(len(g1_spec.VALIDATORS), 18)

    def test_contract_analysis(self) -> None:
        self.analysis["unexpected"] = True
        self.save()
        result = g0_inputs.check(self.workspace, {})
        self.assertFalse(result.passed)
        self.assertEqual(result.findings[0].code, "CONTRACT_ANALYSIS")

    def test_req_no_quote(self) -> None:
        self.analysis["requirements"][0]["quote"] = "Этой цитаты не было"
        self.save()
        self.assertIn("REQ_NO_QUOTE", [f.code for f in g0_inputs.check(self.workspace, {}).findings])

    def test_sources_cannot_be_fabricated_to_justify_quote(self) -> None:
        self.analysis["sources"][0]["text"] = "Выдуманная цитата"
        self.analysis["requirements"][0]["quote"] = "Выдуманная цитата"
        self.save()
        self.assertFalse(g0_inputs.check(self.workspace, {}).passed)

    def test_src_uncovered(self) -> None:
        self.analysis["sources"].append({"id": "S-999", "file": "requirements.md", "text": "Заголовок"})
        self.save()
        self.assertIn("SRC_UNCOVERED", [f.code for f in g0_inputs.check(self.workspace, {}).findings])

    def test_noise_is_not_uncovered(self) -> None:
        manifest = {"schema_version": 1, "files": [], "sources": self.analysis["sources"], "noise": [source["id"] for source in self.analysis["sources"]], "data_cards": []}
        (self.workspace / "spec/analysis-inputs.json").write_text(json.dumps(manifest))
        self.analysis["requirements"] = []
        self.save()
        self.assertNotIn("SRC_UNCOVERED", [f.code for f in g0_inputs.check(self.workspace, {}).findings])

    def test_no_requirements_from_sources_blocks_g0(self) -> None:
        self.analysis["requirements"] = []
        self.save()
        result = g0_inputs.check(self.workspace, {})
        self.assertFalse(result.passed)
        self.assertIn("REQ_EMPTY", [f.code for f in result.findings if f.severity == "error"])

    def test_in_unparsed(self) -> None:
        (self.workspace / "input").mkdir()
        (self.workspace / "input/image.png").write_bytes(b"image")
        result = g0_inputs.check(self.workspace, {})
        self.assertTrue(result.passed)
        self.assertIn("IN_UNPARSED", [f.code for f in result.findings])

    def test_contract_app(self) -> None:
        self.app["schema_version"] = 2
        self.save()
        result = g1_spec.check(self.workspace, {})
        self.assertFalse(result.passed)
        self.assertEqual(result.findings[0].code, "CONTRACT_APP")

    def test_ref_unresolved(self) -> None:
        self.app["entities"]["Ticket"]["fields"]["assignee"]["ref"] = "Missing"
        self.errors("REF_UNRESOLVED")

    def test_req_uncovered(self) -> None:
        self.analysis["user_stories"][0]["req"] = []
        self.errors("REQ_UNCOVERED")

    def test_br_no_ac(self) -> None:
        for ac in self.analysis["acceptance"]:
            ac["rules"] = [rule for rule in ac["rules"] if rule != "BR-01"]
        self.errors("BR_NO_AC")

    def test_br_no_boundary(self) -> None:
        self.analysis["acceptance"][4]["gherkin"] = self.analysis["acceptance"][4]["gherkin"].replace("14399", "14398")
        self.errors("BR_NO_BOUNDARY")

    def test_boundary_numbers_outside_examples_do_not_count(self) -> None:
        self.analysis["acceptance"][4]["gherkin"] = "# language: ru\nФункция: Граница\n  Сценарий: Числа в прозе\n    Дано порог 14399, 14400, 14401\n    Когда проверен срок\n    Тогда статус равен new"
        self.errors("BR_NO_BOUNDARY")

    def test_duration_boundaries_use_explicit_example_units(self) -> None:
        self.analysis["rules"][1]["params"] = {"NOTICE": {"type": "duration", "value": "PT10M"}}
        self.analysis["acceptance"][3]["gherkin"] = "# language: ru\nФункция: Порог\n  Структура сценария: Остаток времени\n    Дано осталось <remaining_minutes> минут\n    Когда проверен срок\n    Тогда статус равен <result>\n    Примеры:\n      | remaining_minutes | result |\n      | 9 | after |\n      | 10 | at |\n      | 11 | before |"
        self.assertEqual(g1_spec.br_no_boundary(Analysis.model_validate(self.analysis), App.model_validate(self.app)), [])
        self.analysis["acceptance"][3]["gherkin"] = self.analysis["acceptance"][3]["gherkin"].replace("remaining_minutes", "duration").replace("| 9 |", "| PT9M |").replace("| 10 |", "| PT10M |").replace("| 11 |", "| PT11M |")
        self.assertEqual(g1_spec.br_no_boundary(Analysis.model_validate(self.analysis), App.model_validate(self.app)), [])

    def test_br_no_hook(self) -> None:
        del self.app["hooks"]["ResolutionRequired"]
        self.errors("BR_NO_HOOK")

    def test_hook_must_trace_its_own_rule_acceptance(self) -> None:
        self.app["hooks"]["ResolutionRequired"]["traces"] = ["AC-01"]
        self.errors("BR_NO_HOOK")

    def test_ac_not_testable(self) -> None:
        self.analysis["acceptance"][0]["gherkin"] = "Должно работать удобно"
        self.errors("AC_NOT_TESTABLE")

    def test_then_conjunction_may_contain_the_observable_result(self) -> None:
        self.analysis["acceptance"][0]["gherkin"] = "# language: ru\nФункция: Проверка\n  Сценарий: Результат\n    Дано исходное состояние\n    Когда выполнено действие\n    Тогда действие завершено\n    И статус равен resolved"
        self.assertEqual(g1_spec.ac_not_testable(Analysis.model_validate(self.analysis), App.model_validate(self.app)), [])

    def test_outline_result_is_checked_after_example_substitution(self) -> None:
        self.analysis["acceptance"][0]["gherkin"] = "# language: ru\nФункция: Порог\n  Структура сценария: Вход\n    Дано значение <value>\n    Когда выполнена проверка\n    Тогда <result>\n    Примеры:\n      | value | result |\n      | 1 | получен отказ |\n      | 2 | данные сохранены |"
        self.assertEqual(g1_spec.ac_not_testable(Analysis.model_validate(self.analysis), App.model_validate(self.app)), [])
        self.analysis["acceptance"][0]["gherkin"] = self.analysis["acceptance"][0]["gherkin"].replace("<result>", "<undefined>")
        self.errors("AC_NOT_TESTABLE")

    def test_nfr_not_measurable(self) -> None:
        self.analysis["nfr"] = [{"id": "NFR-01", "text": "Время ответа", "metric": "быстро", "verify": ""}]
        result = self.errors("NFR_NOT_MEASURABLE")
        self.assertTrue(all(f.severity == "warning" for f in result))

    def test_vague_word(self) -> None:
        self.analysis["nfr"] = [{"id": "NFR-01", "text": "Система работает быстро", "metric": "малое время", "verify": "Осмотр"}]
        self.errors("VAGUE_WORD")

    def test_sm_unreachable(self) -> None:
        self.app["state_machines"]["TicketFlow"]["states"].append("isolated")
        self.errors("SM_UNREACHABLE")

    def test_sm_deadlock(self) -> None:
        self.app["state_machines"]["TicketFlow"]["final"] = []
        self.errors("SM_DEADLOCK")

    def test_sm_no_trigger(self) -> None:
        del self.app["state_machines"]["TicketFlow"]["transitions"][0]["trigger"]
        self.errors("SM_NO_TRIGGER")

    def test_sm_guard_overlap(self) -> None:
        transition = copy.deepcopy(self.app["state_machines"]["TicketFlow"]["transitions"][0])
        transition["name"] = "take_again"
        self.app["state_machines"]["TicketFlow"]["transitions"].append(transition)
        self.errors("SM_GUARD_OVERLAP")

    def test_rbac_orphan(self) -> None:
        self.app["roles"]["observer"] = {"name": "Наблюдатель", "demo_users": []}
        self.errors("RBAC_ORPHAN")

    def test_evt_incomplete(self) -> None:
        self.app["events"]["SystemPulse"] = {"producer": "Ticket"}
        self.errors("EVT_INCOMPLETE")

    def test_ntf_bad_event(self) -> None:
        self.app["notifications"]["TicketOverdue"]["on"] = "DoesNotExist"
        self.errors("NTF_BAD_EVENT")

    def test_us_no_endpoint(self) -> None:
        self.app["entities"]["Ticket"]["traces"].remove("US-01")
        self.errors("US_NO_ENDPOINT")

    def test_data_unknown_field(self) -> None:
        self.app["seed"]["Ticket"][0]["missing_field"] = 7
        self.errors("DATA_UNKNOWN_FIELD")

    def test_data_mapping_requires_known_field_and_units(self) -> None:
        self.analysis["data_cards"] = [{"file": "data.csv", "records": 1, "schema": {"fields": {"amount": {"types": {"int": 1}}}}, "samples": [], "anomalies": []}]
        self.app["scenarios"] = [{"mapping": {"file": "data.csv", "field": "amount"}}]
        self.errors("DATA_UNKNOWN_FIELD")
        self.app["scenarios"][0]["mapping"]["unit"] = "items"
        self.assertEqual(g1_spec.data_unknown_field(Analysis.model_validate(self.analysis), App.model_validate(self.app)), [])

    def test_param_literal(self) -> None:
        self.analysis["rules"][1]["text"] = "Срок не более 5 рабочих часов."
        self.analysis["rules"][1]["params"] = {}
        self.app["hooks"]["SlaDeadline"]["params"] = []
        self.errors("PARAM_LITERAL")

    def test_check_does_not_write_to_workspace(self) -> None:
        before = {str(p): p.read_bytes() for p in self.workspace.rglob("*") if p.is_file()}
        g0_inputs.check(self.workspace, {})
        g1_spec.check(self.workspace, {})
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.workspace.rglob("*") if p.is_file()})


if __name__ == "__main__":
    unittest.main()
