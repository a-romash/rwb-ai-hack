import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from stages.develop import BudgetExceeded, execute

FIXTURES = Path(__file__).parent / "fixtures" / "hooks.json"
REPO = Path(__file__).resolve().parents[3]
STUB = b"ORIGINAL_STUB\n"


class Result:
    def __init__(self, ok, failed=None, output_tail=""):
        self.ok = ok
        self.failed = list(failed or [])
        self.output_tail = output_tail


class FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, task_class, system, user, output, task_id=None):
        self.calls.append(
            {"task_class": task_class, "system": system, "user": user, "output": output, "task_id": task_id}
        )
        item = self.replies.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class FakeSandbox:
    def __init__(self, script=None):
        self.script = list(script) if script is not None else None
        self.calls = []

    def run(self, kind, target, filter=None, timeout_s=600):
        self.calls.append({"kind": kind, "target": target, "filter": filter, "timeout_s": timeout_s})
        if self.script is None:
            return Result(True, [], "ok")
        ok, failed, tail = self.script.pop(0)
        return Result(ok, failed, tail)


def hooks(*ids):
    rows = json.loads(FIXTURES.read_text(encoding="utf-8"))
    wanted = set(ids)
    return [row for row in rows if row["id"] in wanted]


def layout(rows, stub=STUB):
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    for row in rows:
        path = root / "product" / row["file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(stub)
    (root / "product" / "hooks.json").write_text(json.dumps(rows), encoding="utf-8")
    return tmp, root


def report_of(root):
    return json.loads((root / "reports" / "develop.json").read_text(encoding="utf-8"))


class LadderTest(unittest.TestCase):
    def test_first_body_is_accepted(self):
        body = "public int Ok() { return 1; }\n"
        chosen = hooks("SlaDeadline")
        tmp, root = layout(chosen)
        sentinel = root / "product" / "backend" / "tests" / "App.Acceptance.Tests" / "Keep.cs"
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text("UNTOUCHED", encoding="utf-8")
        llm = FakeLLM([body])
        sandbox = FakeSandbox()
        try:
            result = execute(None, root, llm, sandbox)
            text = (root / "product" / chosen[0]["file"]).read_text(encoding="utf-8")
            kept = sentinel.read_text(encoding="utf-8")
            saved = report_of(root)
        finally:
            tmp.cleanup()
        self.assertEqual(text, body)
        self.assertEqual(kept, "UNTOUCHED")
        hook = saved["hooks"][0]
        self.assertEqual(hook["status"], "implemented")
        self.assertEqual(hook["attempts"], 1)
        self.assertTrue(hook["first_pass"])
        self.assertEqual(hook["tests"], {"passed": 1, "failed": 0})
        self.assertEqual(hook["disputes"], [])
        self.assertNotIn("reason", hook)
        self.assertEqual(saved["summary"], {"total": 1, "implemented": 1, "stub": 0, "first_pass": 1})
        self.assertEqual(saved["custom"], [])
        self.assertEqual(result.artifacts, {"develop": "reports/develop.json"})
        self.assertIn("Реализовано 1 из 1", result.summary)
        self.assertEqual([call["task_class"] for call in llm.calls], ["hook_1"])
        self.assertEqual(llm.calls[0]["output"], "code")
        self.assertEqual(sandbox.calls[0]["kind"], "build")
        self.assertEqual(sandbox.calls[1]["filter"], "AC-04")
        self.assertEqual(sandbox.calls[1]["timeout_s"], 600)
        self.assertIn("allowed_api", llm.calls[0]["user"])
        self.assertNotIn("previous body:", llm.calls[0]["user"])

    def test_second_attempt_replaces_failed_body(self):
        first = "FIRST_BODY_UNIQUE\n"
        second = "SECOND_BODY_UNIQUE\n"
        tail = "\n".join(f"FAIL-{i:02d}" for i in range(25))
        chosen = hooks("SlaDeadline")
        tmp, root = layout(chosen)
        llm = FakeLLM([first, second])
        sandbox = FakeSandbox([(False, ["CS1002"], tail), (True, [], "ok"), (True, [], "ok"), (True, [], "ok")])
        try:
            execute(None, root, llm, sandbox)
            text = (root / "product" / chosen[0]["file"]).read_text(encoding="utf-8")
            saved = report_of(root)
        finally:
            tmp.cleanup()
        self.assertEqual(text, second)
        self.assertNotIn("FIRST_BODY_UNIQUE", text)
        hook = saved["hooks"][0]
        self.assertEqual(hook["status"], "implemented")
        self.assertEqual(hook["attempts"], 2)
        self.assertFalse(hook["first_pass"])
        self.assertEqual([call["task_class"] for call in llm.calls], ["hook_1", "hook_2"])
        retried = llm.calls[1]["user"]
        self.assertIn(first, retried)
        self.assertIn("FAIL-00", retried)
        self.assertIn("FAIL-19", retried)
        self.assertNotIn("FAIL-20", retried)
        self.assertEqual(llm.replies, [])

    def test_prompt_carries_criterion_and_input_shapes(self):
        chosen = hooks("SlaDeadline")
        tmp, root = layout(chosen)
        ref = chosen[0]["refs"][0]
        (root / "spec").mkdir()
        (root / "spec" / "analysis.json").write_text(json.dumps({
            "rules": [{"id": ref, "text": "RULE_TEXT_UNIQUE"}],
            "acceptance": [{"id": "AC-X", "rules": [ref], "gherkin": "GHERKIN_UNIQUE"}]}), encoding="utf-8")
        cases = root / "product/backend/tests/App.Acceptance.Tests/cases/hooks" / f"{chosen[0]['id']}.json"
        cases.parent.mkdir(parents=True)
        cases.write_text(json.dumps({"cases": [{"inputs": {"x": "INPUT_UNIQUE"}, "expected": "EXPECTED_UNIQUE"}]}), encoding="utf-8")
        llm = FakeLLM(["return 1;\n"])
        try:
            execute(None, root, llm, FakeSandbox())
        finally:
            tmp.cleanup()
        user = llm.calls[0]["user"]
        for text in ("GHERKIN_UNIQUE", "INPUT_UNIQUE"):
            self.assertIn(text, user)
        self.assertNotIn("EXPECTED_UNIQUE", user)

    def test_cut_off_answer_fails_only_that_attempt(self):
        from contracts.stage import ContractError
        chosen = hooks("SlaDeadline")
        tmp, root = layout(chosen)
        llm = FakeLLM([ContractError("Ответ модели обрезан после трёх продолжений"), "return 1;\n"])
        try:
            execute(None, root, llm, FakeSandbox())
            hook = report_of(root)["hooks"][0]
        finally:
            tmp.cleanup()
        self.assertEqual((hook["status"], hook["attempts"]), ("implemented", 2))
        self.assertIn("обрезан", llm.calls[1]["user"])

    def test_all_attempts_restore_stub(self):
        bodies = [f"BODY-{i}\n" for i in range(6)]
        chosen = hooks("ResolutionRequired")
        tmp, root = layout(chosen)
        path = root / "product" / chosen[0]["file"]
        llm = FakeLLM(bodies)
        sandbox = FakeSandbox([(False, ["bad"], "bad line")] * 12)
        try:
            execute({"task_id": "run-1"}, root, llm, sandbox)
            data = path.read_bytes()
            saved = report_of(root)
        finally:
            tmp.cleanup()
        self.assertEqual(data, STUB)
        for body in bodies:
            self.assertNotIn(body, data.decode())
        hook = saved["hooks"][0]
        self.assertEqual(hook["status"], "stub")
        self.assertEqual(hook["attempts"], 4)
        self.assertFalse(hook["first_pass"])
        self.assertIn("4", hook["reason"])
        self.assertEqual([call["task_class"] for call in llm.calls], ["hook_1", "hook_2", "hook_3", "hook_4", "hook_4", "hook_4"])
        signature = chosen[0]["signature"]
        self.assertEqual(llm.calls[0]["user"].count(signature), 1)
        self.assertGreaterEqual(llm.calls[2]["user"].count(signature), 2)
        # Three hook_4 candidates must not share one cached answer.
        self.assertEqual(len({call["user"] for call in llm.calls[3:]}), 3)
        self.assertEqual(llm.calls[0]["task_id"], "ResolutionRequired")
        self.assertEqual(llm.replies, [])

    def test_budget_stops_later_hooks(self):
        chosen = list(reversed(hooks("SlaDeadline", "ResolutionRequired")))
        chosen.append(
            {
                "id": "ZHook",
                "file": "backend/src/App.Domain/Hooks/ZHook.cs",
                "signature": "public int Evaluate()",
                "refs": ["AC-01"],
                "allowed_api": ["int"],
            }
        )
        tmp, root = layout(chosen)
        llm = FakeLLM(["return 1;\n", BudgetExceeded("stop")])
        sandbox = FakeSandbox()
        try:
            result = execute(None, root, llm, sandbox)
            saved = report_of(root)
            first = (root / "product" / "backend/src/App.Domain/Hooks/ResolutionRequiredHook.cs").read_text(encoding="utf-8")
            second = (root / "product" / "backend/src/App.Domain/Hooks/SlaDeadlineHook.cs").read_bytes()
            third = (root / "product" / "backend/src/App.Domain/Hooks/ZHook.cs").read_bytes()
        finally:
            tmp.cleanup()
        self.assertEqual([row["id"] for row in saved["hooks"]], ["ResolutionRequired", "SlaDeadline", "ZHook"])
        self.assertEqual(first, "return 1;\n")
        self.assertEqual(second, STUB)
        self.assertEqual(third, STUB)
        by_id = {row["id"]: row for row in saved["hooks"]}
        self.assertEqual(by_id["ResolutionRequired"]["status"], "implemented")
        self.assertTrue(by_id["ResolutionRequired"]["first_pass"])
        self.assertEqual(by_id["SlaDeadline"]["status"], "stub")
        self.assertEqual(by_id["SlaDeadline"]["reason"], "бюджет исчерпан")
        self.assertEqual(by_id["SlaDeadline"]["attempts"], 1)
        self.assertEqual(by_id["ZHook"]["status"], "stub")
        self.assertEqual(by_id["ZHook"]["reason"], "бюджет исчерпан")
        self.assertEqual(by_id["ZHook"]["attempts"], 0)
        self.assertEqual(saved["summary"], {"total": 3, "implemented": 1, "stub": 2, "first_pass": 1})
        self.assertIn("Бюджет исчерпан", result.summary)
        self.assertEqual([call["task_class"] for call in llm.calls], ["hook_1", "hook_1"])
        self.assertEqual(len(sandbox.calls), 2)

    def test_dispute_is_not_written(self):
        dispute = "// DISPUTE: AC-04 — ожидание расходится с контрактом, AC-04\n"
        body = "return 7;\n"
        chosen = hooks("SlaDeadline")
        tmp, root = layout(chosen)
        path = root / "product" / chosen[0]["file"]
        llm = FakeLLM([dispute, body])
        sandbox = FakeSandbox()
        try:
            execute(None, root, llm, sandbox)
            text = path.read_text(encoding="utf-8")
            saved = report_of(root)
        finally:
            tmp.cleanup()
        self.assertEqual(text, body)
        self.assertNotIn("DISPUTE", text)
        hook = saved["hooks"][0]
        self.assertEqual(hook["status"], "implemented")
        self.assertEqual(hook["attempts"], 2)
        self.assertFalse(hook["first_pass"])
        self.assertEqual(hook["disputes"], [{"test": "AC-04", "reason": "ожидание расходится с контрактом, AC-04",
                                             "decision": "reject", "decision_reason": "спор не рассмотрен: Не читается tests"}])
        self.assertEqual(len(sandbox.calls), 2)
        self.assertEqual([call["task_class"] for call in llm.calls], ["hook_1", "hook_2"])
        self.assertIn("спор не рассмотрен", llm.calls[1]["user"])

    def test_dispute_goes_to_qa_and_the_verdict_back_to_the_ladder(self):
        from contracts.verification import DisputeDecision, PlannedTest, TestsManifest
        chosen = hooks("SlaDeadline")
        tmp, root = layout(chosen)
        test_file = root / "product" / "backend" / "tests" / "AC_04.cs"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("// AC-04 cases\n", encoding="utf-8")
        (root / "reports").mkdir()
        manifest = TestsManifest(tests=[PlannedTest(id="AC-04", ac="AC-04", file="product/backend/tests/AC_04.cs", level="unit")],
                                 hashes={}, acceptance=["AC-04"], build_ok=True)
        (root / "reports" / "tests.json").write_text(manifest.model_dump_json(), encoding="utf-8")
        (root / "spec").mkdir()
        (root / "spec" / "analysis.json").write_text(json.dumps({"acceptance": [{"id": "AC-04", "text": "SLA 4 часа"}]}), encoding="utf-8")
        llm = FakeLLM(["// DISPUTE: AC-04 — срок неверный\n", DisputeDecision(decision="reject", reason="Тест соответствует AC"), "return 7;\n"])
        try:
            execute(None, root, llm, FakeSandbox())
            saved = report_of(root)
            history = json.loads((root / "reports" / "disputes.json").read_text(encoding="utf-8"))
        finally:
            tmp.cleanup()
        self.assertEqual(saved["hooks"][0]["status"], "implemented")
        self.assertEqual(saved["hooks"][0]["disputes"][0]["decision"], "reject")
        self.assertEqual([call["task_class"] for call in llm.calls], ["hook_1", "qa", "hook_2"])
        self.assertNotIn("return", llm.calls[1]["user"])  # QA never sees the hook body
        self.assertIn("Тест соответствует AC", llm.calls[2]["user"])
        self.assertEqual(history[0]["decision"], "reject")


def _step(content="", tools=None):
    from harness.agent import MODEL

    message = {"role": "assistant", "content": content}
    if tools:
        message["tool_calls"] = tools
    return {"model": MODEL, "finish_reason": "stop", "usage": {}, "message": message}


def _call(name, args, call_id="c1"):
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


class Script:
    def __init__(self, steps):
        self.steps = list(steps)

    def complete(self, messages, tools, response_format=None):
        return self.steps.pop(0)


class AgentRootsTest(unittest.TestCase):
    def test_hook_task_class_and_developer_effort(self):
        import harness.agent as agent

        seen = {}

        class Capture:
            def __init__(self, **kwargs):
                seen.update(kwargs)

            def complete(self, messages, tools, response_format=None):
                raise AssertionError("complete")

        original = agent.OpenRouter
        agent.OpenRouter = Capture
        try:
            with tempfile.TemporaryDirectory() as tmp:
                seen.clear()
                agent.run("x", cwd=tmp, tools=[], max_turns=0)
                self.assertTrue(seen["thinking"])
                self.assertEqual(seen["effort"], "xhigh")
                self.assertIsNone(seen["task_class"])
                seen.clear()
                agent.run("x", cwd=tmp, tools=[], max_turns=0, task_class="hook_2")
                self.assertFalse(seen["thinking"])
                self.assertEqual(seen["effort"], "medium")
                seen.clear()
                agent.run("x", cwd=tmp, max_turns=0, agent=REPO / "agents" / "developer")
                self.assertFalse(seen["thinking"])  # R9: no reasoning for code
                self.assertEqual(seen["effort"], "medium")
        finally:
            agent.OpenRouter = original
        loaded = agent.load_agent(REPO / "agents" / "developer")
        self.assertEqual(loaded["config"]["effort"], "medium")
        self.assertIn("mobile-web/src/app/custom", loaded["config"]["write_roots"])
        self.assertIn("mobile-web/src/app/custom", agent.WRITE_ROOTS)
        gate = agent.OpenRouter(task_class="hook_4", api_key="test")
        self.assertFalse(gate.thinking)
        self.assertEqual(gate.effort, "medium")
        plain = agent.OpenRouter(api_key="test")
        self.assertTrue(plain.thinking)
        self.assertEqual(plain.effort, "xhigh")

    def test_pack_roots_and_backend_commands(self):
        import harness.agent as agent

        mobile = "mobile-web/src/app/custom/a.ts"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            client = Script([
                _step(tools=[_call("write_file", {"path": mobile, "content": "class A {}"})]),
                _step("done"),
                _step("done"),
            ])
            result = agent.run("write", cwd=root, client=client, max_turns=4)
            self.assertEqual(result["permission_denials"], [])
            self.assertEqual((root / mobile).read_text(encoding="utf-8"), "class A {}")

            denied = Script([
                _step(tools=[_call("write_file", {"path": mobile, "content": "no"})]),
                _step("done"),
                _step("done"),
            ])
            blocked = agent.run("write", cwd=root, client=denied, max_turns=4, write_roots=["db/seed"])
            self.assertTrue(blocked["permission_denials"])

            proc = type("Proc", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()
            tester = Script([
                _step(tools=[_call("run_tests", {"target": "backend"})]),
                _step("done"),
                _step("done"),
            ])
            with patch("harness.agent.subprocess.run", return_value=proc) as mocked:
                agent.run("test", cwd=root, client=tester, max_turns=4)
            argv = mocked.call_args.args[0]
            self.assertIn("--report-xunit-junit", argv)
            self.assertIn("/work/reports/junit/backend", argv)

            custom = Script([
                _step(tools=[_call("run_tests", {"target": "backend"})]),
                _step("done"),
                _step("done"),
            ])
            with patch("harness.agent.subprocess.run", return_value=proc) as mocked:
                agent.run(
                    "test",
                    cwd=root,
                    client=custom,
                    max_turns=4,
                    commands={"test": {"backend": ["echo", "custom"]}},
                )
            self.assertEqual(mocked.call_args.args[0], ["echo", "custom"])


if __name__ == "__main__":
    unittest.main()
