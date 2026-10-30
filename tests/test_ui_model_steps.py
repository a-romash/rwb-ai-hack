import copy
import json
import tempfile
import unittest
from pathlib import Path

from contracts.stage import StageInput
from contracts.ui import load_ui
from gates.g15_ui import check_ui
from harness.fakes import FakeLLM, FakeSandbox, run_stage_locally
from stages import ui as ui_stage
from stages.ui.llm_io import PatchOp
from stages.ui.patch import PatchError, apply_patch

ROOT = Path(__file__).resolve().parents[1]
APP = json.loads((ROOT / "tests" / "fixtures" / "ui" / "tickets" / "app.json").read_text(encoding="utf-8"))
ANALYSIS = json.loads((ROOT / "tests" / "fixtures" / "ui" / "tickets" / "analysis.json").read_text(encoding="utf-8"))

STATES = {"loading": "Считаем…", "empty": "Нет данных", "error": "Не удалось загрузить", "forbidden": "Нет доступа"}
PLAN = {"stories": [{"us": f"US-0{i}", "role": r, "platform": "mobile" if i == 6 else "web"}
                    for i, r in enumerate(["employee", "engineer", "engineer", "dispatcher", "dispatcher", "engineer"], 1)],
        "drop": []}
DISPATCHER = {"ops": [
    {"op": "add", "path": "/screens/Dashboard", "value": {
        "platform": "web", "roles": ["dispatcher"], "pattern": "dashboard", "title": "Сводка", "states": STATES,
        "widgets": [{"kind": "kpi", "query": "OpenTickets", "agg": "count", "testid": "dashboard.open"},
                    {"kind": "kpi", "query": "OverdueTickets", "testid": "dashboard.overdue"}],
        "live": ["TicketExpired"], "nav": ["TicketList"]}},
    {"op": "replace", "path": "/home/dispatcher/web", "value": "Dashboard"},
    {"op": "add", "path": "/menus/dispatcher/web/0", "value": "Dashboard"}]}
WALKS = {
    "US-01": {"role": "employee", "platform": "web", "covers": ["AC-01"], "steps": [
        {"open": "TicketList"}, {"tap": "TicketForm"},
        {"fill": "Ticket.title", "value": {"seed": "Ticket[0].title"}},
        {"fill": "Ticket.priority", "value": {"seed": "Ticket[0].priority"}},
        {"tap": "Ticket.create"}, {"expect": {"screen": "TicketDetail", "status": "new"}}]},
    "US-02": {"role": "engineer", "platform": "web", "covers": ["AC-02"], "steps": [
        {"open": "TicketList"}, {"tap": "TakeTicket", "row": {"seed": "Ticket[0]"}},
        {"expect": {"screen": "TicketDetail", "status": "in_progress"}}]},
    "US-03": {"role": "engineer", "platform": "web", "covers": ["AC-06", "AC-07"], "steps": [
        {"open": "TicketList"}, {"tap": "TicketDetail", "row": {"seed": "Ticket[1]"}},
        {"tap": "ResolveTicketForm"}, {"tap": "ResolveTicket"},
        {"expect": {"error": "ResolutionRequired", "copy": "error.ResolutionRequired"}},
        {"fill": "ResolveTicket.resolution", "value": {"gen": "valid"}}, {"tap": "ResolveTicket"},
        {"expect": {"screen": "TicketDetail", "status": "resolved"}}]},
    "US-04": {"role": "dispatcher", "platform": "web", "covers": ["AC-08"], "steps": [
        {"open": "Dashboard"}, {"expect": {"visible": ["dashboard.open", "dashboard.overdue"]}}]},
    "US-05": {"role": "dispatcher", "platform": "web", "covers": ["AC-09"], "steps": [
        {"open": "TicketList"}, {"expect": {"row": {"seed": "Ticket[2]"}, "status": "overdue"}}]},
    "US-06": {"role": "engineer", "platform": "mobile", "covers": ["AC-10"], "steps": [
        {"open": "MobileTicketList"}, {"expect": {"row": {"seed": "Ticket[0]"}}},
        {"tap": "MobileTicketDetail", "row": {"seed": "Ticket[0]"}},
        {"expect": {"screen": "MobileTicketDetail"}}]},
}
BAD_US02 = {**WALKS["US-02"], "steps": [{"open": "TicketList"}, {"tap": "ResolveTicket"},
                                        {"expect": {"screen": "TicketDetail"}}]}
TEXTS = {"titles": {"TicketList": "Заявки", "ResolveTicketForm": "Закрытие заявки",
                    "MobileResolveTicketForm": "Закрытие заявки"},
         "states": {"TicketList": {"empty": "Открытых заявок нет"}},
         "copy": {"error.ResolutionRequired": "Опишите решение, чтобы закрыть заявку"}}


def script(overrides: dict | None = None) -> dict:
    responses = {("ui", "platforms"): [PLAN],
                 ("ui", "refine:dispatcher"): [DISPATCHER],
                 ("ui", "refine:employee"): [{"ops": []}],
                 ("ui", "refine:engineer"): [{"ops": []}],
                 ("ui", "texts:0"): [TEXTS],
                 ("ui", "devices"): [{"features": ["local_notification"]}]}
    responses.update({("ui", us): [walk] for us, walk in WALKS.items()})
    responses.update(overrides or {})
    return responses


def workspace(folder: str) -> tuple[Path, StageInput]:
    root = Path(folder)
    (root / "spec").mkdir()
    (root / "spec" / "app.json").write_text(json.dumps(APP, ensure_ascii=False), encoding="utf-8")
    (root / "spec" / "analysis.json").write_text(json.dumps(ANALYSIS, ensure_ascii=False), encoding="utf-8")
    inp = StageInput(run_id="t", stage="ui", attempt=1, requirements="Заявки на ремонт",
                     artifacts={"app": "spec/app.json", "analysis": "spec/analysis.json"})
    return root, inp


class PatchTest(unittest.TestCase):
    def test_add_replace_remove(self):
        doc = {"a": {"b": [1, 2]}, "c": 1}
        out = apply_patch(doc, [PatchOp(op="add", path="/a/b/-", value=3), PatchOp(op="add", path="/a/b/0", value=0),
                                PatchOp(op="replace", path="/c", value=2), PatchOp(op="remove", path="/a/b/1"),
                                PatchOp(op="add", path="/d~1e", value=True)])
        self.assertEqual(out, {"a": {"b": [0, 2, 3]}, "c": 2, "d/e": True})
        self.assertEqual(doc, {"a": {"b": [1, 2]}, "c": 1})

    def test_errors(self):
        for op in (PatchOp(op="remove", path="/x"), PatchOp(op="replace", path="/a/b/5", value=1),
                   PatchOp(op="add", path="/a/x/y", value=1), PatchOp(op="add", path="a", value=1)):
            with self.assertRaises(PatchError):
                apply_patch({"a": {"b": []}}, [op])


class ModelStepsTest(unittest.TestCase):
    def run_stage(self, llm):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root, inp = workspace(folder.name)
        out = run_stage_locally(ui_stage, inp, root, llm, FakeSandbox({}))
        return root, inp, out, load_ui(root / "spec" / "ui.json")

    def test_full_run_passes_gate(self):
        llm = FakeLLM(script({("ui", "US-02"): [BAD_US02, WALKS["US-02"]]}))
        _, _, out, ui = self.run_stage(llm)
        self.assertEqual([f for f in check_ui(ui, APP, ANALYSIS) if f.severity == "error"], [])
        self.assertEqual(out.flags, [])
        self.assertIn("проходов 6 из 6", out.summary)
        # step 1: mobile screens for the engineer, menu and home on mobile
        self.assertEqual(ui.home["engineer"]["mobile"], "MobileTicketList")
        self.assertIn("offline", ui.screens["MobileTicketList"].states)
        self.assertTrue(all(t.startswith("mobile-ticket-list.") for t in ui.screens["MobileTicketList"].testids()))
        # step 2: dispatcher patch accepted
        self.assertEqual(ui.home["dispatcher"]["web"], "Dashboard")
        # step 3: retry carried the gate findings
        retry = [c for c in llm.calls if c["task_id"] == "US-02"][1]
        self.assertIn("previous_errors", json.loads(retry["user"]))
        # step 4/5: texts and devices
        self.assertEqual(ui.screens["ResolveTicketForm"].title, "Закрытие заявки")
        self.assertEqual(ui.copy_texts["error.ResolutionRequired"], "Опишите решение, чтобы закрыть заявку")
        self.assertEqual(ui.device["mobile"], ["local_notification"])
        # every call is one-shot with a bounded prompt
        self.assertTrue(all(len(c["user"]) < 30_000 for c in llm.calls))

    def test_invalid_answers_fall_back(self):
        bad_patch = {"ops": [{"op": "add", "path": "/screens/TicketList/widgets/-",
                              "value": {"kind": "kpi", "query": "OpenTickets", "testid": "ticket-list.kpi"}}]}
        foreign = {"titles": {"TicketList": "Tickets"}, "copy": {"error.ResolutionRequired": "Add a resolution"}}
        llm = FakeLLM(script({("ui", "platforms"): [{"stories": []}, {"stories": [], "drop": []}],
                                ("ui", "refine:dispatcher"): [bad_patch, {"ops": [{"op": "remove", "path": "/nope"}]}],
                                ("ui", "texts:0"): [foreign, foreign],
                                ("ui", "US-04"): [WALKS["US-04"]] * 2,      # Dashboard was rejected
                                ("ui", "US-06"): [WALKS["US-06"]] * 2}))   # no mobile screens
        _, _, out, ui = self.run_stage(llm)
        self.assertNotIn("Dashboard", ui.screens)                    # patch rejected twice
        self.assertFalse(any(s.platform == "mobile" for s in ui.screens.values()))   # default plan: all web
        self.assertEqual(ui.screens["TicketList"].title, "Заявка")   # foreign title ignored
        self.assertTrue(ui.copy_texts["error.ResolutionRequired"])   # fallback text, not empty
        self.assertIn("платформы выбраны по умолчанию", out.summary)
        codes = {f.code for f in check_ui(ui, APP, ANALYSIS) if f.severity == "error"}
        self.assertTrue(codes)                                       # left for the G1.5 repair rounds

    def test_budget_exhausted_returns_valid_partial_result(self):
        _, _, out, ui = self.run_stage(FakeLLM(script(), budget_after=3))
        self.assertIn("частично", out.summary)
        self.assertTrue(out.flags)
        self.assertTrue(all(f.status == "questioned" and f.path.startswith("walks.") for f in out.flags))
        self.assertIn("TicketList", ui.screens)

    def test_repair_fixes_gate_findings(self):
        root, inp, _, ui = self.run_stage(FakeLLM(script()))
        raw = json.loads((root / "spec" / "ui.json").read_text(encoding="utf-8"))
        raw["walks"].pop("US-02")
        raw["screens"]["TicketDetail"]["states"].pop("forbidden")
        raw["screens"]["TicketForm"]["widgets"][1]["testid"] = "ticket-form.title"
        (root / "spec" / "ui.json").write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        broken = load_ui(root / "spec" / "ui.json")
        findings = [f for f in check_ui(broken, APP, ANALYSIS) if f.severity == "error"]
        self.assertEqual({f.code for f in findings}, {"WALK_MISSING", "AC_UI_UNCOVERED", "STATE_MISSING", "TESTID_DUP"})
        llm = FakeLLM({("ui", "US-02"): [WALKS["US-02"]]})
        repaired_inp = inp.model_copy(update={"artifacts": {**inp.artifacts, "ui": "spec/ui.json"}})
        ui_stage.repair(repaired_inp, root, llm, findings)
        fixed = load_ui(root / "spec" / "ui.json")
        self.assertEqual([f for f in check_ui(fixed, APP, ANALYSIS) if f.severity == "error"], [])
        self.assertEqual(len(llm.calls), 1)                          # states and testids fixed by code


if __name__ == "__main__":
    unittest.main()
