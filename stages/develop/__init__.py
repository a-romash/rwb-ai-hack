"""Ladder that fills hook bodies one file at a time."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from contracts.stage import BudgetExceeded, ContractError, StageOutput
from stages.tests.cases import CASES, contradictions


LADDER = ("hook_1", "hook_2", "hook_3", "hook_4")


def execute(inp, workspace: Path, llm, sandbox) -> StageOutput:
    workspace = Path(workspace)
    hooks = _load_hooks(workspace)
    system = _system()
    rows: list[dict] = []
    budget = False
    for hook in hooks:
        if budget:
            rows.append(_row(hook, "stub", 0, False, _zeros(), [], "бюджет исчерпан"))
            continue
        blocked = _blocked(workspace, hook)
        if blocked:
            # R13: the ladder cannot pass these tests, so the hook stays a stub with the real reason.
            rows.append(_row(hook, "stub", 0, False, _zeros(), [], blocked))
            continue
        # Accounting and recorded answers are per hook, not per run.
        row, budget = _one(hook, workspace, llm, sandbox, system, str(hook.get("id") or _task_id(inp)))
        rows.append(row)
    summary = {
        "total": len(rows),
        "implemented": sum(row["status"] == "implemented" for row in rows),
        "stub": sum(row["status"] == "stub" for row in rows),
        "first_pass": sum(1 for row in rows if row["first_pass"]),
    }
    report = {"schema_version": 1, "hooks": rows, "custom": [], "summary": summary}
    out = workspace / "reports" / "develop.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    text = (
        f"Реализовано {summary['implemented']} из {summary['total']} хуков. "
        f"Заглушек: {summary['stub']}. С первой попытки: {summary['first_pass']}."
    )
    if budget:
        text += " Бюджет исчерпан, оставшиеся хуки оставлены заглушками."
    return StageOutput(artifacts={"develop": "reports/develop.json"}, summary=text)


def _one(hook, workspace, llm, sandbox, system, task_id):
    path = _hook_path(workspace, hook)
    context = _context(workspace, hook)
    ac = _first_ac(hook.get("refs"))
    disputes: list[dict] = []
    previous = ""
    failures = ""
    tests = _zeros()
    attempts = 0
    accepted = False
    for task_class in LADDER:
        attempts += 1
        user = _user(hook, task_class, previous, failures, context)
        samples = 3 if task_class == "hook_4" else 1
        for sample in range(samples):
            # Same messages hit the same cache entry: without a marker three candidates are one answer.
            asked = user + (f"\n\ncandidate {sample + 1} of {samples}" if samples > 1 else "")
            try:
                raw = llm(task_class=task_class, system=system, user=asked, output="code", task_id=task_id)
            except ContractError as exc:
                # An unusable answer (cut off, too long) fails this attempt of this hook, not the stage.
                failures = f"Ответ не принят: {exc}"
                continue
            except Exception as exc:
                if not _is_budget(exc):
                    raise
                return _row(hook, "stub", attempts, False, tests, disputes, "бюджет исчерпан"), True
            if not isinstance(raw, str):
                raw = str(raw)
            dispute = _dispute(raw)
            if dispute:
                try:
                    dispute.update(_arbitrate(dispute, hook, ac, workspace, llm, sandbox))
                except Exception as exc:
                    if not _is_budget(exc):
                        raise
                    disputes.append(dispute)
                    return _row(hook, "stub", attempts, False, tests, disputes, "бюджет исчерпан"), True
                disputes.append(dispute)
                failures = f"Спор по тесту: {dispute['decision']} — {dispute['decision_reason']}"
                previous = raw
                continue
            ok, tests, failures = _apply(path, raw, sandbox, ac, workspace, str(hook.get("id") or ""))
            previous = raw
            if ok:
                accepted = True
                break
        if accepted:
            break
    if accepted:
        return _row(hook, "implemented", attempts, attempts == 1, tests, disputes), False
    return _row(hook, "stub", attempts, False, tests, disputes, _fail_reason(hook, attempts, failures, disputes)), False


def _apply(path: Path, body: str, sandbox, ac: str | None, workspace: Path | None = None, hook_id: str = ""):
    before = path.read_bytes() if path.is_file() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    # dotnet test compiles the solution itself: a separate build step compiled every candidate twice.
    # A JUnit report appears only when the candidate compiled and the tests ran.
    test = sandbox.run("test", "backend", filter=ac, timeout_s=600)
    # A filter that matches no test exits 0: a hook without a single test is not accepted.
    ran = _ran(workspace, test) if workspace is not None else None
    if ran == 0:
        test = test.model_copy(update={"ok": False, "failed": [f"нет ни одного теста для {ac or 'хука'}"]})
    own = _own(workspace, test, hook_id) if ran and hook_id else None
    if own:
        # The hook is judged by its own cases: an API scenario of the same AC tests generated code
        # (verify reports it), and its log tail hid the hook's assertion from the model.
        failed = [f"{name}: {message}" for name, message in own if message is not None]
        test = test.model_copy(update={"ok": not failed, "failed": failed, "output_tail": ""})
    ok = bool(test.ok)
    if not ok:
        if before is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(before)
    return ok, _counts(test, test), _failure_text(None, test)


def _ran(workspace: Path, result) -> int | None:
    """Number of test cases in the JUnit report, None when the sandbox gave no report."""
    report = (getattr(result, "reports", None) or {}).get("junit")
    if not report:
        return None
    try:
        return sum(1 for _ in ET.parse(Path(workspace) / report).iter("testcase"))
    except (OSError, ET.ParseError):
        return None


def _own(workspace: Path, result, hook_id: str) -> list[tuple[str, str | None]]:
    """(test, failure message or None) of the hook's own cases: their key is "<hook id>:<case>"."""
    report = (getattr(result, "reports", None) or {}).get("junit")
    try:
        cases = ET.parse(Path(workspace) / report).iter("testcase") if report else []
    except (OSError, ET.ParseError):
        return []
    found = []
    for case in cases:
        name = case.get("name") or ""
        if f'"{hook_id}:' in name:
            failure = case.find("failure")
            found.append((name, None if failure is None else (failure.get("message") or "failed")))
    return found


def _load_hooks(workspace: Path) -> list[dict]:
    raw = json.loads((workspace / "product" / "hooks.json").read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("hooks.json must be an array")
    return sorted(raw, key=lambda item: str(item.get("id", "")))


def _hook_path(workspace: Path, hook: dict) -> Path:
    rel = Path(str(hook.get("file") or ""))
    if not rel.parts or rel.is_absolute() or any(part == ".." for part in rel.parts):
        raise ValueError("bad hook path")
    return workspace / "product" / rel


def _system() -> str:
    path = Path(__file__).resolve().parents[2] / "agents" / "developer" / "prompt.md"
    base = path.read_text(encoding="utf-8").strip() if path.is_file() else "Ты разработчик."
    return base + "\nВерни только тело файла хука. Если тест неверен, одна строка // DISPUTE: <тест> — <причина>."





def _json(workspace: Path, relative: str) -> dict:
    path = Path(workspace) / relative
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _blocked(workspace: Path, hook: dict) -> str | None:
    """Why no hook body can pass, known before any model call; None when the ladder may run."""
    cases = _json(workspace, f"{CASES}/{hook.get('id')}.json").get("cases") or []
    for _, message in contradictions(cases):
        return f"{message} — тесты противоречат друг другу (G2 CASES_CONTRADICT)"
    manifest = _json(workspace, "reports/tests.json")
    ac = _first_ac(hook.get("refs"))
    if not cases and manifest and ac and not any(test.get("ac") == ac for test in manifest.get("tests") or []):
        return f"для {ac} нет ни одного теста (G2 AC_NO_TEST)"
    return None


def _context(workspace: Path, hook: dict) -> str:
    """Criterion scenarios and input shapes: hooks.json has the rule text and table rows, not the
    scenario text, and test cases come after scaffold. Expected values of the cases stay hidden."""
    analysis = _json(workspace, "spec/analysis.json")
    refs = {str(ref) for ref in hook.get("refs") or []}
    parts = [criterion.get("gherkin", "") for criterion in analysis.get("acceptance", [])
             if criterion.get("id") in refs or refs & set(criterion.get("rules", []))]
    inputs = [case.get("inputs") for case in (_json(workspace, f"{CASES}/{hook.get('id')}.json").get("cases") or [])[:3]]
    if inputs:
        parts.append("input examples (the C# test runner deserializes these):\n" + json.dumps(inputs, ensure_ascii=False))
    return "\n\n".join(part for part in parts if part)


def _user(hook: dict, task_class: str, previous: str, failures: str, context: str = "") -> str:
    allowed = "\n".join(str(item) for item in (hook.get("allowed_api") or []))
    parts = [json.dumps(hook, ensure_ascii=False, indent=2), "allowed_api:\n" + allowed]
    if context:
        parts.append("acceptance:\n" + context)
    if task_class != "hook_1":
        parts.append("previous body:\n" + previous)
        parts.append("failures:\n" + failures)
    if task_class in ("hook_3", "hook_4"):
        parts.append("signature:\n" + str(hook.get("signature") or ""))
    return "\n\n".join(parts)


def _first_ac(refs) -> str | None:
    for ref in refs or []:
        text = str(ref)
        if text.startswith("AC"):
            return text
    return None


def _dispute(text: str) -> dict | None:
    marker = "// DISPUTE:"
    for line in text.splitlines():
        if marker not in line:
            continue
        rest = line.split(marker, 1)[1].strip()
        if "—" in rest:
            test, reason = rest.split("—", 1)
        elif " - " in rest:
            test, reason = rest.split(" - ", 1)
        else:
            test, _, reason = rest.partition(" ")
            if not reason:
                reason = rest
        return {"test": test.strip(), "reason": reason.strip()}
    return None


def _arbitrate(dispute: dict, hook: dict, ac: str | None, workspace: Path, llm, sandbox) -> dict:
    """QA judges the test against the AC without seeing the hook; a test that cannot be judged stays as is."""
    from contracts.stage import ContractError
    from contracts.verification import Dispute
    from stages.tests.dispute import resolve

    try:
        if not ac:
            raise ContractError("у хука нет критерия приёмки")
        decision = resolve(Dispute(test=ac, ac=ac, reason=dispute["reason"], hook=str(hook.get("id", ""))),
                           workspace, llm, sandbox)
    except ContractError as exc:
        return {"decision": "reject", "decision_reason": f"спор не рассмотрен: {exc}"}
    return {"decision": decision.decision, "decision_reason": decision.reason}


def _failure_text(build, test) -> str:
    lines: list[str] = []
    for result in (build, test):
        if not result or result.ok:
            continue
        lines.extend((getattr(result, "output_tail", None) or "").splitlines())
        for item in getattr(result, "failed", None) or []:
            text = str(item)
            if text not in lines:
                lines.append(text)
    return "\n".join(lines[:20])


def _counts(build, test) -> dict:
    # ponytail: sandbox has no passed-count; a green filtered run counts as 1.
    failed = [str(item) for item in (getattr(test, "failed", None) or [])]
    if build.ok and test.ok:
        return {"passed": 1, "failed": 0}
    if not build.ok and not failed:
        failed = [str(item) for item in (getattr(build, "failed", None) or [])] or ["build"]
    return {"passed": 0, "failed": len(failed) or 1}


def _fail_reason(hook, attempts: int, failures: str, disputes: list) -> str:
    ac = _first_ac(hook.get("refs")) or "тесты"
    if failures:
        return f"тест {ac} красный после {attempts} попыток: {failures.splitlines()[-1][:200]}"
    if disputes:
        return f"спор с тестом после {attempts} попыток"
    return f"тест {ac} красный после {attempts} попыток"


def _zeros() -> dict:
    return {"passed": 0, "failed": 0}


def _row(hook, status, attempts, first_pass, tests, disputes, reason=None) -> dict:
    row = {
        "id": str(hook.get("id", "")),
        "status": status,
        "attempts": attempts,
        "first_pass": first_pass,
        "tests": tests,
        "disputes": disputes,
    }
    if reason:
        row["reason"] = reason
    return row


def _task_id(inp):
    if inp is None:
        return None
    if isinstance(inp, dict):
        return inp.get("task_id") or inp.get("run_id")
    return getattr(inp, "task_id", None) or getattr(inp, "run_id", None)


def _is_budget(exc: BaseException) -> bool:
    return isinstance(exc, BudgetExceeded) or type(exc).__name__ == "BudgetExceeded"
