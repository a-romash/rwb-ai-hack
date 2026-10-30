import copy
import json
import tempfile
import unittest
from pathlib import Path

from contracts.stage import ContractError, StageInput
from contracts.ui import REQUIRED_STATES, UiSpec, load_ui
from gates.g15_ui import check, check_ui, foreign_text
from harness.fakes import FakeLLM, FakeSandbox, run_stage_locally
from stages import ui as ui_stage
from stages.ui.appview import AppView, derived_event
from stages.ui.base import derive_base

ROOT = Path(__file__).resolve().parents[1]
UI_FIXTURE = ROOT / "contracts" / "fixtures" / "tickets" / "ui.json"
# Stand-ins for Sanya's fixtures until contracts/fixtures/tickets/{app,analysis}.json land.
APP = json.loads((ROOT / "tests" / "fixtures" / "ui" / "tickets" / "app.json").read_text(encoding="utf-8"))
ANALYSIS = json.loads((ROOT / "tests" / "fixtures" / "ui" / "tickets" / "analysis.json").read_text(encoding="utf-8"))


class AppViewTest(unittest.TestCase):
    def test_derived_events(self):
        self.assertEqual([derived_event("Ticket", t) for t in ("take", "expire", "resolve", "stop", "open", "copy")],
                         ["TicketTaken", "TicketExpired", "TicketResolved", "TicketStopped", "TicketOpened",
                          "TicketCopied"])
        view = AppView(APP)
        self.assertTrue(view.event_exists("TicketTaken"))
        self.assertFalse(view.event_exists("TicketVanished"))
        # Multi-word transition from the canonical spec: the name the ui stage derives must resolve.
        canonical = AppView(json.loads((ROOT / "contracts" / "fixtures" / "tickets" / "app.json").read_text(encoding="utf-8")))
        self.assertEqual(derived_event("Ticket", "take_overdue"), "TicketTakenOverdue")
        self.assertTrue(canonical.event_exists("TicketTakenOverdue"))

    def test_roles_and_fields(self):
        view = AppView(APP)
        self.assertEqual(view.roles_for("TakeTicket"), {"engineer"})
        self.assertEqual(view.field("ResolveTicket.resolution")["type"], "text")
        self.assertIsNone(view.field("Ticket.nothing"))
        self.assertTrue(view.operation_exists("Ticket.create"))
        self.assertFalse(view.operation_exists("Ticket.archive"))


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.ui = derive_base(APP)

    def test_screens_by_permissions(self):
        self.assertEqual(set(self.ui.screens), {"TicketList", "TicketDetail", "TicketForm", "ResolveTicketForm"})
        self.assertEqual(self.ui.screens["TicketList"].roles, ["dispatcher", "employee", "engineer"])
        self.assertEqual(self.ui.screens["TicketForm"].roles, ["employee"])
        self.assertEqual(self.ui.screens["ResolveTicketForm"].roles, ["engineer"])

    def test_widgets_actions_and_testids(self):
        listing = self.ui.screens["TicketList"]
        kinds = {w.field: w.kind for w in listing.widgets}
        self.assertEqual(kinds["Ticket.status"], "status")
        self.assertEqual(kinds["Ticket.due_at"], "countdown")
        self.assertNotIn("Ticket.description", kinds)                    # text is not a list column
        self.assertEqual([a.command for a in listing.actions], ["TakeTicket"])   # no-input commands only
        self.assertEqual({f.field for f in listing.filters}, {"Ticket.priority", "Ticket.status"})
        detail = self.ui.screens["TicketDetail"]
        self.assertIn("ResolveTicketForm", detail.nav)
        self.assertEqual([w.command for w in detail.widgets if w.kind == "action_button"],
                         ["TakeTicket", "ResolveTicket"])
        form_fields = {w.field for w in self.ui.screens["TicketForm"].widgets}
        self.assertNotIn("Ticket.status", form_fields)
        self.assertNotIn("Ticket.due_at", form_fields)                   # computed
        self.assertNotIn("Ticket.resolution", form_fields)               # set by a command
        self.assertEqual(self.ui.screens["TicketForm"].actions[0].command, "Ticket.create")

    def test_menus_states_and_round_trip(self):
        self.assertEqual(self.ui.home["employee"], {"web": "TicketList"})
        for screen in self.ui.screens.values():
            self.assertEqual(set(screen.states), set(REQUIRED_STATES["web"]))
        self.assertEqual(UiSpec.model_validate(self.ui.model_dump(mode="json")), self.ui)

    def test_base_passes_gate_except_walks(self):
        codes = {f.code for f in check_ui(self.ui, APP, ANALYSIS) if f.severity == "error"}
        self.assertEqual(codes, {"WALK_MISSING", "AC_UI_UNCOVERED"})

    def test_english_app_gets_english_states(self):
        app = copy.deepcopy(APP)
        app["meta"]["lang"] = "en-US"
        self.assertEqual(derive_base(app).screens["TicketList"].states["empty"], "Nothing here yet")


class StageTest(unittest.TestCase):
    def test_execute_locally(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            (workspace / "spec").mkdir()
            (workspace / "spec" / "app.json").write_text(json.dumps(APP), encoding="utf-8")
            (workspace / "spec" / "analysis.json").write_text(json.dumps(ANALYSIS), encoding="utf-8")
            inp = StageInput(run_id="t", stage="ui", attempt=1, requirements="r",
                             artifacts={"app": "spec/app.json", "analysis": "spec/analysis.json"})
            out = run_stage_locally(ui_stage, inp, workspace, FakeLLM({}, budget_after=0), FakeSandbox({}))
            self.assertEqual(out.artifacts, {"ui": "spec/ui.json"})
            self.assertIn("частично", out.summary)               # no model budget: base only
            self.assertIn("TicketList", load_ui(workspace / "spec" / "ui.json").screens)

    def test_missing_input_is_contract_error(self):
        with tempfile.TemporaryDirectory() as folder:
            inp = StageInput(run_id="t", stage="ui", attempt=1, requirements="r", artifacts={})
            with self.assertRaises(ContractError):
                ui_stage.execute(inp, Path(folder), FakeLLM({}), FakeSandbox({}))


class GateTest(unittest.TestCase):
    """One violation per code on top of the clean tickets fixture."""

    def setUp(self):
        self.raw = json.loads(UI_FIXTURE.read_text(encoding="utf-8"))

    def findings(self, mutate=None, app=APP, analysis=ANALYSIS):
        raw = copy.deepcopy(self.raw)
        if mutate:
            mutate(raw)
        return check_ui(UiSpec.model_validate(raw), app, analysis)

    def assertCode(self, code, mutate=None, path=None, severity="error", **kw):
        found = [f for f in self.findings(mutate, **kw) if f.code == code]
        self.assertTrue(found, f"нет находки {code}")
        self.assertEqual(found[0].severity, severity)
        if path is not None:
            self.assertEqual(found[0].path, path)

    def test_fixture_is_clean(self):
        self.assertEqual(self.findings(), [])

    def test_contract_ui(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace = Path(folder)
            (workspace / "ui.json").write_text(json.dumps({"schema_version": 1, "screens": {}}), encoding="utf-8")
            (workspace / "app.json").write_text(json.dumps(APP), encoding="utf-8")
            (workspace / "analysis.json").write_text(json.dumps(ANALYSIS), encoding="utf-8")
            artifacts = {"ui": "ui.json", "app": "app.json", "analysis": "analysis.json"}
            result = check(workspace, artifacts)
            self.assertFalse(result.passed)
            self.assertEqual([f.code for f in result.findings], ["CONTRACT_UI"])
            (workspace / "ui.json").write_text(UI_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
            result = check(workspace, artifacts)
            self.assertTrue(result.passed)
            self.assertEqual(result.gate, "G1.5")

    def test_ui_ref_unresolved(self):
        self.assertCode("UI_REF_UNRESOLVED", lambda r: r["screens"]["TicketList"]["source"].update(query="Nope"),
                        path="screens.TicketList.source")
        self.assertCode("UI_REF_UNRESOLVED", lambda r: r["screens"]["TicketList"]["widgets"][0].update(field="Ticket.nope"))
        self.assertCode("UI_REF_UNRESOLVED", lambda r: r["screens"]["TicketList"]["live"].append("TicketVanished"))
        self.assertCode("UI_REF_UNRESOLVED", lambda r: r["screens"]["TicketList"]["actions"][0].update(command="Fly"))
        self.assertCode("UI_REF_UNRESOLVED", lambda r: r["copy"].pop("ticket.take.confirm"))
        self.assertCode("UI_REF_UNRESOLVED", lambda r: r["walks"]["US-05"]["steps"][1]["expect"].update(status="lost"))
        self.assertCode("UI_REF_UNRESOLVED", lambda r: r["walks"]["US-01"]["steps"][2]["value"].update(seed="Ticket[9].title"))

    def test_walk_forbidden(self):
        def give_take_to_employee(raw):
            raw["screens"]["MyTickets"]["actions"] = [{"command": "TakeTicket", "testid": "my-tickets.take"}]
            raw["walks"]["US-01"]["steps"].insert(1, {"tap": "TakeTicket", "row": {"seed": "Ticket[0]"}})
        self.assertCode("WALK_FORBIDDEN", give_take_to_employee, path="walks.US-01.steps[1]")

    def test_walk_missing(self):
        self.assertCode("WALK_MISSING", lambda r: r["walks"].pop("US-04"), path="walks.US-04")

    def test_ac_ui_uncovered(self):
        self.assertCode("AC_UI_UNCOVERED", lambda r: r["walks"]["US-03"].update(covers=["AC-06"]))

    def test_walk_unreachable(self):
        def hide_alerts(raw):
            raw["screens"]["Dashboard"]["nav"] = ["TicketList"]
            raw["menus"]["dispatcher"]["web"].remove("Alerts")
        self.assertCode("WALK_UNREACHABLE", hide_alerts, path="walks.US-05.steps[0]")
        self.assertCode("WALK_UNREACHABLE", lambda r: r["walks"]["US-02"]["steps"][2]["expect"].update(screen="TicketList"))

    def test_walk_literal(self):
        self.assertCode("WALK_LITERAL", lambda r: r["walks"]["US-01"]["steps"][2].update(value="Сломан стул"),
                        severity="warning")

    def test_testid_dup(self):
        self.assertCode("TESTID_DUP", lambda r: r["screens"]["TicketList"]["widgets"][1].update(testid="ticket-list.title"))

    def test_state_missing(self):
        self.assertCode("STATE_MISSING", lambda r: r["screens"]["MobileQueue"]["states"].pop("offline"),
                        path="screens.MobileQueue.states")

    def test_copy_lang(self):
        self.assertCode("COPY_LANG", lambda r: r["copy"].update({"ticket.take.confirm": "Take this ticket?"}),
                        severity="warning")
        self.assertTrue(foreign_text("Заявки", "en-US"))
        self.assertFalse(foreign_text("SLA истёк", "ru-RU"))
        self.assertFalse(foreign_text("42", "ru-RU"))


if __name__ == "__main__":
    unittest.main()
