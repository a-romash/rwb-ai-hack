"""S7: воспроизводимый eval analysis/spec; python -m stages.spec.eval."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from contracts.analysis import Analysis
from contracts.app import App, dependents
from gates.g0_inputs import check as g0, validate_quotes
from gates.g1_spec import check as g1
from stages.analysis import execute as analyze, repair as repair_analysis
from stages.analysis.compat import ContractError, ElementFlag, StageInput
from stages.analysis.testing import FakeLLM, FakeSandbox
from stages.analysis.storage import write_json
from stages.spec import execute as specify, repair as repair_spec
from stages.spec.eval_gateway import EvalGateway, load_env

ROOT = Path(__file__).resolve().parents[2]


def prompt_hashes() -> dict[str, str]:
    return {path.parent.name: hashlib.sha256(path.read_bytes()).hexdigest() for pattern in ("analyst-*/prompt.md", "system-analyst-*/prompt.md") for path in sorted((ROOT / "agents").glob(pattern))}


def _errors(gate) -> list:
    # Несколько кодов одного адреса чинятся одним запросом, без устаревших индексов.
    unique = {}
    for finding in gate.findings:
        if finding.severity == "error":
            if finding.path in unique:
                unique[finding.path].message += " " + finding.message
            else:
                unique[finding.path] = finding.model_copy()
    return list(unique.values())


def evaluate(name: str, requirements: Path | None, workspace: Path, *, mode: str,
             model: str, context_window: int, max_tokens: int, max_calls: int) -> dict:
    result = {"case": name, "mode": mode, "status": "started", "model": model if mode == "live" else None,
              "req_count": None, "quote_rate": None, "issue_count": None, "question_count": None,
              "br_ac_rate": None, "g0_before": None, "g0_after": None,
              "g1_before": None, "g1_after": None, "calls": [], "tokens": None,
              "flags": [], "elapsed_ms": 0}
    if requirements is None or not requirements.is_file():
        return result | {"status": "missing_input", "reason": "Не предоставлен оригинальный текст слайдов 13–17 кейса №1."}
    if mode == "recorded" and not all((ROOT / f"stages/{stage}/tests/fixtures/{name}-responses.json").is_file() for stage in ("analysis", "spec")):
        return result | {"status": "missing_recording", "reason": "Для этого текста пока нет записанного прогона; требуется live-режим."}
    if workspace.is_dir() and any(workspace.iterdir()):
        return result | {"status": "failed", "reason": "Для независимого eval нужна пустая рабочая папка."}
    workspace.mkdir(parents=True, exist_ok=True)
    text = requirements.read_text(encoding="utf-8")
    result["requirements_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    (workspace / "input").mkdir(exist_ok=True)
    (workspace / "input/requirements.md").write_text(text, encoding="utf-8")
    llm = EvalGateway(model=model, workspace=workspace, context_window=context_window, max_tokens=max_tokens, max_calls=max_calls) if mode == "live" else FakeLLM({**json.loads((ROOT / f"stages/analysis/tests/fixtures/{name}-responses.json").read_text()), **json.loads((ROOT / f"stages/spec/tests/fixtures/{name}-responses.json").read_text())}, context_window=context_window)
    started = time.monotonic()
    artifacts: dict[str, str] = {}
    flags: list[ElementFlag] = []
    try:
        inp = StageInput(run_id=f"eval-{name}", stage="analysis", attempt=1, requirements=text, artifacts=artifacts)
        output = analyze(inp, workspace, llm, FakeSandbox())
        flags.extend(output.flags)
        artifacts.update(output.artifacts)
        gate = g0(workspace, artifacts)
        result["g0_before"] = len(gate.findings)
        for attempt in range(1, 3):
            if gate.passed:
                break
            inp = inp.model_copy(update={"attempt": attempt, "artifacts": artifacts})
            output = repair_analysis(inp, workspace, llm, _errors(gate))
            artifacts.update(output.artifacts)
            flags.extend(output.flags)
            gate = g0(workspace, artifacts)
        result["g0_after"] = len(gate.findings)
        g0_errors = _errors(gate)
        inp = inp.model_copy(update={"stage": "spec", "attempt": 1, "artifacts": artifacts})
        output = specify(inp, workspace, llm, FakeSandbox())
        flags.extend(output.flags)
        artifacts.update(output.artifacts)
        write_json(workspace, "reports/g1-before-app.json", App.model_validate_json((workspace / artifacts["app"]).read_text()))
        write_json(workspace, "reports/g1-before-analysis.json", Analysis.model_validate_json((workspace / artifacts["analysis"]).read_text()))
        gate = g1(workspace, artifacts)
        result["g1_before"] = len(gate.findings)
        for attempt in range(1, 3):
            if gate.passed:
                break
            inp = inp.model_copy(update={"attempt": attempt, "artifacts": artifacts})
            output = repair_spec(inp, workspace, llm, _errors(gate))
            artifacts.update(output.artifacts)
            flags.extend(output.flags)
            gate = g1(workspace, artifacts)
        # Ремонт анализа на G1 не должен нарушать доказательность источников G0.
        g0_gate = g0(workspace, artifacts)
        result["g0_after"] = len(g0_gate.findings)
        result["g1_after"] = len(gate.findings)
        analysis = Analysis.model_validate_json((workspace / artifacts["analysis"]).read_text())
        app = App.model_validate_json((workspace / artifacts["app"]).read_text())
        for finding in _errors(g0_gate) + _errors(gate):
            flags.append(ElementFlag(path=finding.path, status="questioned", reason=finding.message, gate="G0" if finding.code == "REQ_NO_QUOTE" else "G1"))
            for dependent in dependents(app, finding.path):
                flags.append(ElementFlag(path=dependent, status="blocked_by", reason=f"Зависит от {finding.path}.", gate="G1"))
        result.update(req_count=len(analysis.requirements),
                      quote_rate=(len(analysis.requirements) - len(validate_quotes(analysis))) / len(analysis.requirements) if analysis.requirements else None,
                      issue_count=len(analysis.issues), question_count=len(analysis.questions),
                      br_ac_rate=sum(any(rule.id in ac.rules for ac in analysis.acceptance) for rule in analysis.rules) / len(analysis.rules) if analysis.rules else None,
                      g0_findings=[finding.model_dump() for finding in g0_gate.findings],
                      g1_findings=[finding.model_dump() for finding in gate.findings],
                      status="passed" if gate.passed and g0_gate.passed and not flags else "partial")
    except Exception as exc:
        # Eval обязан сохранить честный результат и продолжить другие кейсы.
        result.update(status="contract_error" if isinstance(exc, ContractError) else "failed", error_type=type(exc).__name__, reason=str(exc)[:300])
    finally:
        calls = llm.calls
        if mode == "live":
            result["calls"] = calls
            result["tokens"] = sum(call.get("total_tokens") or 0 for call in calls) if all(call.get("total_tokens") is not None for call in calls) else None
        else:
            result["calls"] = [{"task_id": call["task_id"], "task_class": call["task_class"], "status": "recorded"} for call in calls]
        result["flags"] = [flag.model_dump() for flag in flags]
        result["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        result["workspace"] = str(workspace)
        result["artifacts"] = artifacts
        result["partial_artifacts"] = {name: f"spec/{name}.json" for name in ("analysis", "app") if name not in artifacts and (workspace / f"spec/{name}.json").is_file()}
        analysis_name = artifacts.get("analysis", result["partial_artifacts"].get("analysis"))
        if analysis_name and result["req_count"] is None:
            partial = Analysis.model_validate_json((workspace / analysis_name).read_text())
            result.update(req_count=len(partial.requirements), issue_count=len(partial.issues), question_count=len(partial.questions), quote_rate=(len(partial.requirements) - len(validate_quotes(partial))) / len(partial.requirements) if partial.requirements else None)
        write_json(workspace, "reports/eval.json", result | {"schema_version": 1})
    return result


def report(results: list[dict], destination: Path, *, mode: str) -> None:
    hashes = prompt_hashes()
    data = {"schema_version": 1, "mode": mode, "timestamp": datetime.now(timezone.utc).isoformat(), "prompt_hashes": hashes, "results": results}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.with_suffix(".json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Оценка analysis/spec", "", f"Режим: `{mode}`. Дата UTC: {data['timestamp']}.", "", "Записанные ответы не являются прогоном настоящей модели; неизвестные метрики обозначены `—`.", "", "| Кейс | Статус | REQ | Цитаты | ISS / Q | BR с AC | G1 до → после | Вызовы | Токены |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    def value(item):
        return "—" if item is None else str(item)
    for result in results:
        lines.append(f"| {result['case']} | {result['status']} | {value(result['req_count'])} | {value(result['quote_rate'])} | {value(result['issue_count'])} / {value(result['question_count'])} | {value(result['br_ac_rate'])} | {value(result['g1_before'])} → {value(result['g1_after'])} | {len(result['calls'])} | {value(result['tokens'])} |")
    for result in results:
        lines += ["", f"## {result['case']}", "", f"Статус: `{result['status']}`. Время: {result['elapsed_ms']} мс."]
        if result.get("reason"):
            lines += ["", result["reason"]]
        if result.get("workspace"):
            lines += ["", f"Артефакты и сырые выходы модели: `{result['workspace']}`."]
        if result.get("revalidation"):
            lines += ["", result["revalidation"]]
        if result.get("continuation"):
            lines += ["", result["continuation"], "", f"Исходный сбой: `{result['prior_failure']['status']}` — {result['prior_failure']['reason']}."]
        if result.get("g1_findings"):
            lines += ["", "Находки после ремонта:", ""] + [f"- `{f['code']}` `{f['path']}`: {f['message']}" for f in result["g1_findings"]]
        if result["flags"]:
            lines += ["", f"Честных флагов сомнения/зависимости: {len(result['flags'])}."]
    lines += ["", "## Версии промптов", "", "Версия указана в каждой карточке и config.yaml; SHA-256 фиксирует точный текст:", ""]
    lines += [f"- `{name}`: `{digest}`" for name, digest in hashes.items()]
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def revalidate(result: dict) -> dict:
    """Повторяет только чистые гейты над сохранёнными выходами настоящей модели.

    Используется после исправления валидатора; модель и артефакты не меняются.
    Исходные метрики выполнения и реальные API-вызовы сохраняются отдельно.
    """
    if result["status"] not in ("passed", "partial"):
        return result
    workspace = Path(result["workspace"])
    artifacts = result["artifacts"]
    updated = dict(result)
    updated["execution_gate_counts"] = {key: result[key] for key in ("g0_before", "g0_after", "g1_before", "g1_after")}
    updated["execution_flags"] = result["flags"]
    baseline_app = workspace / "reports/g1-before-app.json"
    baseline_analysis = workspace / "reports/g1-before-analysis.json"
    if baseline_app.is_file() and baseline_analysis.is_file():
        from gates.g1_spec import validate
        before = validate(Analysis.model_validate_json(baseline_analysis.read_text()), App.model_validate_json(baseline_app.read_text()))
        updated["g1_before"] = len(before)
    after_g0 = g0(workspace, artifacts)
    after_g1 = g1(workspace, artifacts)
    updated["g0_after"] = len(after_g0.findings)
    updated["g1_after"] = len(after_g1.findings)
    updated["g0_findings"] = [finding.model_dump() for finding in after_g0.findings]
    updated["g1_findings"] = [finding.model_dump() for finding in after_g1.findings]
    app = App.model_validate_json((workspace / artifacts["app"]).read_text())
    remaining = [flag for flag in result["flags"] if flag.get("gate") is None or flag["path"].startswith("custom[") or "несовместим" in flag["reason"]]
    for gate in (after_g0, after_g1):
        for finding in _errors(gate):
            remaining.append(ElementFlag(path=finding.path, status="questioned", reason=finding.message, gate=gate.gate).model_dump())
            remaining.extend(ElementFlag(path=path, status="blocked_by", reason=f"Зависит от {finding.path}.", gate=gate.gate).model_dump() for path in dependents(app, finding.path))
    updated["flags"] = list({(flag["path"], flag["status"], flag["reason"]): flag for flag in remaining}.values())
    updated["status"] = "passed" if after_g0.passed and after_g1.passed and not updated["flags"] else "partial"
    updated["revalidation"] = "Чистые гейты повторены после уточнения Gherkin Examples/единиц; артефакты и вызовы модели не менялись. Счётчики G1 до и после вычислены одной текущей версией валидаторов."
    write_json(workspace, "reports/eval-rechecked.json", updated | {"schema_version": 1})
    return updated


def continue_context_limited_repair(result: dict, *, context_window: int = 32768,
                                    max_tokens: int = 300000, max_calls: int = 120) -> dict:
    """Явное продолжение старого сбоя окна, без повторения генерации или первого ремонта.

    Учитывает уже оплаченные вызовы и разрешает только второй круг ремонта.
    Исходный неуспешный отчёт остаётся в reports/eval.json.
    """
    if (result.get("mode") != "live" or result.get("status") != "contract_error"
            or result.get("reason") != "Контекст запроса превышает профиль окна"
            or not result.get("calls")
            or not result["calls"][-1]["task_id"].startswith("spec.repair.1.")):
        raise ValueError("Продолжение допускается только после сбоя окна в первом ремонте G1")
    if result.get("tokens") is None:
        raise ValueError("Для продолжения нужен известный фактический расход токенов")
    workspace = Path(result["workspace"])
    artifacts = dict(result["artifacts"])
    analysis = Analysis.model_validate_json((workspace / artifacts["analysis"]).read_text())
    App.model_validate_json((workspace / artifacts["app"]).read_text())
    gateway = EvalGateway(model=result["model"], workspace=workspace, context_window=context_window,
                          max_tokens=max_tokens, max_calls=max_calls)
    gateway.calls = list(result["calls"])
    gateway.tokens_used = result["tokens"]
    started = time.monotonic()
    gate = g1(workspace, artifacts)
    inp = StageInput(run_id=f"eval-{result['case']}", stage="spec", attempt=2,
                     requirements=(workspace / "input/requirements.md").read_text(), artifacts=artifacts)
    output = repair_spec(inp, workspace, gateway, _errors(gate))
    artifacts.update(output.artifacts)
    gate = g1(workspace, artifacts)
    input_gate = g0(workspace, artifacts)
    analysis = Analysis.model_validate_json((workspace / artifacts["analysis"]).read_text())
    app = App.model_validate_json((workspace / artifacts["app"]).read_text())
    flags = list(result["flags"]) + [flag.model_dump() for flag in output.flags]
    for checked in (input_gate, gate):
        for finding in _errors(checked):
            flags.append(ElementFlag(path=finding.path, status="questioned", reason=finding.message, gate=checked.gate).model_dump())
            flags.extend(ElementFlag(path=path, status="blocked_by", reason=f"Зависит от {finding.path}.", gate=checked.gate).model_dump() for path in dependents(app, finding.path))
    updated = dict(result)
    updated["prior_failure"] = {key: result[key] for key in ("status", "error_type", "reason", "elapsed_ms")}
    updated.pop("error_type", None)
    updated.pop("reason", None)
    updated.update(status="partial", artifacts=artifacts, flags=flags,
                   calls=gateway.calls, tokens=sum(call["total_tokens"] for call in gateway.calls),
                   elapsed_ms=result["elapsed_ms"] + int((time.monotonic() - started) * 1000),
                   g0_after=len(input_gate.findings), g1_after=len(gate.findings),
                   g0_findings=[finding.model_dump() for finding in input_gate.findings],
                   g1_findings=[finding.model_dump() for finding in gate.findings],
                   br_ac_rate=sum(any(rule.id in ac.rules for ac in analysis.acceptance) for rule in analysis.rules) / len(analysis.rules) if analysis.rules else None,
                   continuation="После исправления обработки окна выполнен только второй круг ремонта над сохранёнными артефактами. Все прежние вызовы и токены учтены; незаписанные изменения прерванного первого круга потеряны. Исходный неуспешный отчёт сохранён.")
    write_json(workspace, "reports/eval-continued.json", updated | {"schema_version": 1})
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Оценка двух этапов на эталонных доменах")
    parser.add_argument("--mode", choices=("recorded", "live"), default="recorded")
    parser.add_argument("--model", default="qwen/qwen3.8-27b")
    parser.add_argument("--case1", type=Path, default=ROOT / "stages/spec/eval/case1/requirements.md")
    parser.add_argument("--cases", nargs="+", choices=("tickets", "equipment", "case1"))
    parser.add_argument("--output", type=Path, default=ROOT / "stages/spec/EVAL.md")
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--context-window", type=int, default=32768)
    parser.add_argument("--max-tokens", type=int, default=300000)
    parser.add_argument("--max-calls", type=int, default=120)
    args = parser.parse_args()
    load_env(ROOT / ".env")
    workspace = args.workspace or ROOT / "workspaces/eval" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    cases = {name: ROOT / f"contracts/fixtures/{name}/requirements.md" for name in ("tickets", "equipment")}
    cases["case1"] = args.case1
    results: list[dict] = []
    selected = args.cases or (["tickets", "equipment"] if args.mode == "recorded" else ["tickets", "equipment", "case1"])
    for name in selected:
        print(f"Начат {name}, режим {args.mode}", flush=True)
        result = evaluate(name, cases[name], workspace / name, mode=args.mode, model=args.model, context_window=args.context_window, max_tokens=args.max_tokens, max_calls=args.max_calls)
        results.append(result)
        report(results, args.output, mode=args.mode)
        print(f"{name}: {result['status']}; вызовов: {len(result['calls'])}; токенов: {result['tokens']}", flush=True)
    return 0 if all(result["status"] in ("passed", "partial") for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
