import json
import shutil
import tempfile
import unittest
from pathlib import Path

from stages.scaffold import execute
from stages.scaffold.generate import template_copy_paths

FIXTURES = Path(__file__).resolve().parent / "fixtures"

EQUIPMENT_FILES = [
    "product/admin-web/e2e/pages/ItemList.ts",
    "product/admin-web/src/app/generated/model.ts",
    "product/admin-web/src/app/generated/routes.ts",
    "product/mobile-web/e2e/pages/PhoneItem.ts",
    "product/mobile-web/src/app/generated/model.ts",
    "product/mobile-web/src/app/generated/routes.ts",
    "product/backend/src/App.Api/seed.json",
    "product/backend/src/App.Domain/Generated/IMaxLaptopsHook.cs",
    "product/backend/src/App.Domain/Generated/Model.cs",
    "product/backend/src/App.Domain/Generated/Params.cs",
    "product/backend/src/App.Domain/Hooks/MaxLaptopsHook.cs",
    "product/backend/src/App.Api/Features/Generated/Endpoints.cs",
    "product/backend/src/App.Infrastructure/Generated/AppDbContext.Model.cs",
    "product/backend/src/App.Infrastructure/Generated/Timers.cs",
    "product/backend/tests/App.Generated.Tests/cases/api.json",
    "product/hooks.json",
    "product/infra/roles.json",
    "product/openapi.json",
]


class GenerateTests(unittest.TestCase):
    def test_hooks_json_contains_sla_and_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = _run(workspace, FIXTURES)
            self.assertEqual(result.artifacts["product"], "product")
            self.assertEqual(result.artifacts["hooks"], "product/hooks.json")
            self.assertEqual(result.artifacts["openapi"], "product/openapi.json")
            self.assertIsInstance(result.summary, str)
            self.assertTrue(result.summary)
            hooks_path = workspace / "product" / "hooks.json"
            openapi_path = workspace / "product" / "openapi.json"
            _assert_canonical(hooks_path)
            _assert_canonical(openapi_path)
            hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
            by_id = {hook["id"]: hook for hook in hooks}
            self.assertEqual(list(by_id), ["ResolutionRequired", "SlaDeadline"])
            sla = by_id["SlaDeadline"]
            self.assertEqual(sla["kind"], "calculator")
            self.assertEqual(sla["language"], "csharp")
            self.assertEqual(sla["stub"], "neutral")
            self.assertEqual(sla["max_lines"], 60)
            self.assertEqual(sla["file"], "backend/src/App.Domain/Hooks/SlaDeadlineHook.cs")
            self.assertEqual(sla["refs"], ["AC-04", "AC-05", "BR-02"])
            self.assertEqual(sla["contract"]["summary"], "BR-02")
            self.assertEqual(sla["examples"], [])
            self.assertEqual(sla["allowed_api"], ["SLA_HIGH", "Ticket"])
            self.assertIn("DateTimeOffset", sla["signature"])
            required = by_id["ResolutionRequired"]
            self.assertEqual(required["kind"], "validator")
            self.assertEqual(required["contract"]["summary"], "BR-03")
            self.assertEqual(required["examples"], [])
            sla_file = workspace / "product/backend/src/App.Domain/Hooks/SlaDeadlineHook.cs"
            self.assertIn("return default(DateTimeOffset);", sla_file.read_text(encoding="utf-8"))
            required_file = workspace / "product/backend/src/App.Domain/Hooks/ResolutionRequiredHook.cs"
            self.assertIn("return true;", required_file.read_text(encoding="utf-8"))
            spec = json.loads(openapi_path.read_text(encoding="utf-8"))
            self.assertEqual(spec["openapi"], "3.1.0")
            self.assertEqual(spec["paths"]["/api/Ticket"]["get"]["x-roles"], ["dispatcher", "engineer"])
            self.assertEqual(spec["paths"]["/api/Ticket/commands/TakeTicket"]["post"]["x-roles"], ["engineer"])
            routes = (workspace / "product/admin-web/src/app/generated/routes.ts").read_text(encoding="utf-8")
            self.assertIn("TicketList", routes)
            model = (workspace / "product/admin-web/src/app/generated/model.ts").read_text(encoding="utf-8")
            self.assertIn('"TicketList"', model)
            self.assertNotIn('"MobileQueue"', model)
            seed = json.loads((workspace / "product/backend/src/App.Api/seed.json").read_text(encoding="utf-8"))
            self.assertIn(seed["Ticket"][0]["id"], model)                      # walks and screens agree on ids
            page = (workspace / "product/admin-web/e2e/pages/TicketList.ts").read_text(encoding="utf-8")
            self.assertIn("ticket-list.due", page)
            self.assertIn("ticket-list.take", page)
            cases = json.loads((workspace / "product/backend/tests/App.Generated.Tests/cases/api.json").read_text(encoding="utf-8"))
            expected = {case["id"]: case["expected"] for case in cases["cases"]}
            self.assertEqual(expected["Ticket.read.engineer"], 200)
            self.assertEqual(expected["Ticket.create.engineer"], 403)
            self.assertEqual(expected["Ticket.read.anonymous"], 401)
            self.assertEqual(expected["TakeTicket.engineer"], 404)
            endpoints = (workspace / "product/backend/src/App.Api/Features/Generated/Endpoints.cs").read_text(encoding="utf-8")
            self.assertIn('"engineer|Ticket.read"', endpoints)
            self.assertIn("ResolutionRequiredHook().Validate(cmd)", endpoints)
            # Copy, labels and seed rows live only in the data files the renderer and the stand read.
            data = ("src/app/generated/model.ts", "src/App.Api/seed.json")
            blob = b"\n".join(v for k, v in _tree(workspace).items() if not k.endswith(data))
            self.assertNotIn("Не работает кондиционер".encode(), blob)
            self.assertNotIn("Взять заявку в работу?".encode(), blob)
            self.assertNotIn("Нет открытых заявок".encode(), blob)
            self.assertNotIn("Приоритет".encode(), blob)

    def test_second_run_keeps_hook_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            _run(workspace, FIXTURES)
            hook = workspace / "product/backend/src/App.Domain/Hooks/SlaDeadlineHook.cs"
            marked = hook.read_bytes() + b"// MARKER-UNIQUE\n"
            hook.write_bytes(marked)
            interface = workspace / "product/backend/src/App.Domain/Generated/ISlaDeadlineHook.cs"
            interface.write_text("MUTATED\n", encoding="utf-8")
            _run(workspace, FIXTURES)
            self.assertEqual(hook.read_bytes(), marked)
            self.assertNotIn("MUTATED", interface.read_text(encoding="utf-8"))
            self.assertIn("ISlaDeadlineHook", interface.read_text(encoding="utf-8"))

    def test_two_runs_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            left = Path(first)
            right = Path(second)
            _run(left, FIXTURES)
            snapshot = _tree(left)
            _run(left, FIXTURES)
            self.assertEqual(snapshot, _tree(left))
            _run(right, FIXTURES)
            self.assertEqual(snapshot, _tree(right))

    def test_missing_app_json_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            spec = workspace / "spec"
            spec.mkdir()
            shutil.copy(FIXTURES / "ui.json", spec / "ui.json")
            with self.assertRaises(ValueError):
                execute(_input("spec/app.json", "spec/ui.json"), workspace, None, None)

    def test_schema_version_must_be_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            spec = workspace / "spec"
            spec.mkdir()
            app = json.loads((FIXTURES / "app.json").read_text(encoding="utf-8"))
            app["schema_version"] = 2
            (spec / "app.json").write_text(json.dumps(app), encoding="utf-8")
            shutil.copy(FIXTURES / "ui.json", spec / "ui.json")
            with self.assertRaises(Exception) as caught:
                execute(_input("spec/app.json", "spec/ui.json"), workspace, None, None)
            self.assertIn(caught.exception.__class__.__name__, {"ValueError", "ContractError"})

    def test_admin_and_pwa_share_the_renderer(self):
        # Two copies so each app builds alone (its own Docker context); they must not drift.
        root = Path(__file__).resolve().parents[3] / "templates" / "product"
        for folder in ("src/app/screens", "src/app/ui"):
            admin = {p.name: p.read_bytes() for p in (root / "admin-web" / folder).iterdir()}
            mobile = {p.name: p.read_bytes() for p in (root / "mobile-web" / folder).iterdir()}
            admin.pop("menu.ts", None)                          # the PWA has a tab bar in app.ts instead
            self.assertEqual(admin, mobile, folder)

    def test_seed_refs_are_rows_of_the_referenced_entity(self):
        from stages.scaffold.generate import _seed
        app = {"entities": {"Ticket": {"fields": {"author": {"type": "ref", "ref": "Employee"}}}},
               "seed": {"Employee": [{"name": "A"}, {"name": "B"}], "Ticket": [{"author": 1}]}}
        seed = _seed(app)
        self.assertEqual(seed["Ticket"][0]["author"], seed["Employee"][1]["id"])
        self.assertEqual(_seed(app), seed)                                     # stable ids

    def test_timer_transition_is_applied_by_the_worker(self):
        from stages.scaffold.api import timers_cs
        app = json.loads((FIXTURES / "app.json").read_text(encoding="utf-8"))
        text = timers_cs(app)
        self.assertIn("x.Status == TicketFlowState.InProgress) && x.DueAt != null && x.DueAt <= now", text)
        self.assertIn("item.Status = TicketFlowState.Overdue;", text)
        app["state_machines"]["TicketFlow"]["transitions"][1]["trigger"] = {"timer": "title"}
        self.assertIn("wire it in custom", timers_cs(app))

    def test_equipment_file_list_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            _run(workspace, FIXTURES / "equipment")
            files = set(_tree(workspace))
            self.assertLessEqual(set(EQUIPMENT_FILES), files)
            self.assertLessEqual(files - set(EQUIPMENT_FILES), set(template_copy_paths()))
            self.assertNotIn("product/admin-web/e2e/pages/PhoneItem.ts", files)
            self.assertNotIn("product/mobile-web/e2e/pages/ItemList.ts", files)
            hooks = json.loads((workspace / "product" / "hooks.json").read_text(encoding="utf-8"))
            self.assertEqual(hooks[0]["id"], "MaxLaptops")
            self.assertEqual(hooks[0]["kind"], "policy")
            stub = (workspace / "product/backend/src/App.Domain/Hooks/MaxLaptopsHook.cs").read_text(encoding="utf-8")
            self.assertIn("return true;", stub)


def _run(workspace: Path, fixture: Path):
    spec = workspace / "spec"
    spec.mkdir(parents=True, exist_ok=True)
    shutil.copy(fixture / "app.json", spec / "app.json")
    shutil.copy(fixture / "ui.json", spec / "ui.json")
    return execute(_input("spec/app.json", "spec/ui.json"), workspace, None, None)


def _input(app: str, ui: str) -> dict:
    return {
        "run_id": "run-1",
        "stage": "scaffold",
        "attempt": 1,
        "autonomy": "A2",
        "requirements": "",
        "artifacts": {"app": app, "ui": ui},
    }


def _tree(workspace: Path) -> dict[str, bytes]:
    found = {}
    product = workspace / "product"
    for path in product.rglob("*"):
        if path.is_file():
            found[path.relative_to(workspace).as_posix()] = path.read_bytes()
    return dict(sorted(found.items()))


def _assert_canonical(path: Path) -> None:
    raw = path.read_bytes()
    data = json.loads(raw)
    canonical = (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
    if raw != canonical:
        raise AssertionError(f"{path.name} is not canonical JSON")
