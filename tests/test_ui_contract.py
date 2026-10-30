import copy
import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from contracts.ui import (PATTERN_SOURCES, PATTERN_WIDGETS, REQUIRED_STATES, ExpectStep, FillStep, GenRef,
                          OpenStep, SeedRef, TapStep, UiSpec, load_ui, screen_kebab)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "contracts" / "fixtures" / "tickets" / "ui.json"


class UiContractTest(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def invalid(self, mutate):
        raw = copy.deepcopy(self.raw)
        mutate(raw)
        with self.assertRaises(ValidationError):
            UiSpec.model_validate(raw)

    def test_fixture_loads_and_round_trips(self):
        ui = load_ui(FIXTURE)
        self.assertIn("TicketList", ui.screens)
        self.assertEqual(set(ui.walks), {f"US-0{i}" for i in range(1, 7)})
        dumped = ui.model_dump(mode="json", exclude_defaults=True)
        self.assertIn("copy", dumped)
        self.assertEqual(UiSpec.model_validate(dumped), ui)

    def test_fixture_screens_with_data_have_required_states(self):
        for name, screen in load_ui(FIXTURE).screens.items():
            if screen.has_data:
                self.assertTrue(set(REQUIRED_STATES[screen.platform]) <= set(screen.states), name)

    def test_steps_are_discriminated(self):
        steps = load_ui(FIXTURE).walks["US-03"].steps
        self.assertIsInstance(steps[0], OpenStep)
        self.assertIsInstance(steps[1], TapStep)
        self.assertIsInstance(steps[4], ExpectStep)
        self.assertEqual(steps[4].expect.copy_key, "error.ResolutionRequired")
        self.assertIsInstance(steps[5], FillStep)
        self.assertIsInstance(steps[5].value, GenRef)
        self.assertIsInstance(load_ui(FIXTURE).walks["US-01"].steps[2].value, SeedRef)

    def test_literal_value_is_schema_valid(self):
        raw = copy.deepcopy(self.raw)
        raw["walks"]["US-01"]["steps"][2]["value"] = "Не работает принтер"
        self.assertEqual(UiSpec.model_validate(raw).walks["US-01"].steps[2].value, "Не работает принтер")

    def test_catalog_tables_cover_vocabularies(self):
        patterns = {"list", "detail", "form", "wizard", "dashboard", "map", "feed",
                    "action", "settings", "calendar", "kanban"}
        self.assertEqual(set(PATTERN_SOURCES), patterns)
        self.assertEqual(set(PATTERN_WIDGETS), patterns)

    def test_screen_kebab(self):
        self.assertEqual(screen_kebab("TicketList"), "ticket-list")
        self.assertEqual(screen_kebab("ResolveTicketForm"), "resolve-ticket-form")
        self.assertEqual(screen_kebab("KPIBoard"), "kpi-board")

    def test_rejects_unknown_vocabulary(self):
        self.invalid(lambda r: r["screens"]["TicketList"].update(pattern="grid"))
        self.invalid(lambda r: r["screens"]["TicketList"]["widgets"][0].update(kind="chart"))
        self.invalid(lambda r: r["walks"]["US-02"]["steps"].insert(0, {"swipe": "TicketList"}))
        self.invalid(lambda r: r["device"].update(mobile=["background_location"]))
        self.invalid(lambda r: r["screens"]["TicketList"]["states"].update(hidden="…"))
        self.invalid(lambda r: r.update(schema_version=2))
        self.invalid(lambda r: r["screens"]["TicketList"].update(extra=True))

    def test_rejects_widget_not_allowed_by_pattern(self):
        self.invalid(lambda r: r["screens"]["TicketList"]["widgets"].append(
            {"kind": "kpi", "query": "OpenTickets", "testid": "ticket-list.kpi"}))

    def test_rejects_widget_without_reference(self):
        self.invalid(lambda r: r["screens"]["TicketDetail"]["widgets"][-2].pop("command"))
        self.invalid(lambda r: r["screens"]["Dashboard"]["widgets"][2].pop("field"))
        self.invalid(lambda r: r["screens"]["TicketList"]["widgets"][0].update(agg="count"))

    def test_rejects_bad_source(self):
        self.invalid(lambda r: r["screens"]["TicketList"].pop("source"))
        self.invalid(lambda r: r["screens"]["TicketDetail"].update(source={"query": "OpenTickets"}))
        self.invalid(lambda r: r["screens"]["TicketList"].update(source={"query": "A", "entity": "B"}))
        self.invalid(lambda r: r["screens"]["Dashboard"].update(source={"query": "OpenTickets"}))

    def test_rejects_bad_testid(self):
        self.invalid(lambda r: r["screens"]["TicketList"]["widgets"][0].update(testid="TicketList.title"))
        self.invalid(lambda r: r["screens"]["TicketList"]["widgets"][0].update(testid="ticket-detail.title"))
        self.invalid(lambda r: r["screens"]["TicketList"]["widgets"][0].update(testid="ticket-list.row"))
        self.invalid(lambda r: r["screens"]["TicketList"]["widgets"][0].update(testid="ticket-list.state-empty"))

    def test_rejects_offline_on_web_and_bad_refs(self):
        self.invalid(lambda r: r["screens"]["TicketList"]["states"].update(offline="…"))
        self.invalid(lambda r: r["walks"]["US-02"]["steps"][1].update(row={"seed": "Ticket[0].title"}))
        self.invalid(lambda r: r["walks"]["US-01"]["steps"][2].update(value={"gen": "invalid"}))
        self.invalid(lambda r: r["walks"]["US-04"]["steps"][1].update(expect={}))
        self.invalid(lambda r: r["walks"].update({"STORY-1": r["walks"]["US-01"]}))


if __name__ == "__main__":
    unittest.main()
