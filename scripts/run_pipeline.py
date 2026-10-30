"""Start a pipeline run through the platform API and follow it to the end.

    python scripts/run_pipeline.py --requirements examples/case1/requirements.md
    python scripts/run_pipeline.py --text "Сотрудники подают заявки..." --base-url http://localhost:8080

Prints stage statuses as they change and the final metrics; exit code 0 means the run
finished as succeeded or partial. Standard library only, so it runs anywhere.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

FINAL = {"succeeded", "partial", "failed", "cancelled"}


def call(base: str, method: str, path: str, body: dict | None = None):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    request = urllib.request.Request(base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read() or b"null")
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"{method} {path}: {exc.code} {exc.read().decode('utf-8', 'replace')}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--requirements", type=Path, help="файл с бизнес-требованиями")
    source.add_argument("--text", help="требования строкой")
    parser.add_argument("--name", default="Прогон из CLI")
    parser.add_argument("--attach", type=Path, action="append", default=[], help="файл данных к требованиям")
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--autonomy", default="A2", choices=["A0", "A1", "A2"])
    parser.add_argument("--tokens", type=int, default=1_500_000)
    parser.add_argument("--minutes", type=int, default=60)
    parser.add_argument("--timeout", type=int, default=3600, help="сколько ждать конца прогона, с")
    args = parser.parse_args(argv)

    sys.stdout.reconfigure(encoding="utf-8")
    base = args.base_url.rstrip("/") + "/api"
    text = args.text if args.text is not None else args.requirements.read_text(encoding="utf-8")
    project = call(base, "POST", "/projects", {"name": args.name, "requirements": text})
    for file in args.attach:
        upload(base, project["id"], file)
    run = call(base, "POST", f"/projects/{project['id']}/runs",
               {"autonomy": args.autonomy, "budget": {"tokens": args.tokens, "minutes": args.minutes}})
    print(f"Проект {project['id']}, прогон {run['id']}")

    seen: dict[str, str] = {}
    deadline = time.monotonic() + args.timeout
    while True:
        run = call(base, "GET", f"/runs/{run['id']}")
        for stage in run["stages"]:
            state = f"{stage['status']}#{stage['attempt']}"
            if seen.get(stage["key"]) != state:
                seen[stage["key"]] = state
                gate = stage.get("gate") or {}
                verdict = "" if not gate else f" [{gate.get('gate')}: {'ok' if gate.get('passed') else 'находки ' + str(len(gate.get('findings', [])))}]"
                note = stage.get("summary") or stage.get("error") or ""
                print(f"  {stage['key']:<9} {stage['status']:<13}{verdict} {note[:160]}")
        if run["status"] in FINAL or time.monotonic() > deadline:
            break
        time.sleep(3)

    metrics = call(base, "GET", f"/runs/{run['id']}/metrics")["totals"]
    print(f"Итог: {run['status']}; вызовов модели {metrics['calls']}, токены вход/выход "
          f"{metrics['tokens_in']}/{metrics['tokens_out']}, флагов {len(run.get('flags', []))}")
    return 0 if run["status"] in ("succeeded", "partial") else 1


def upload(base: str, project_id: str, file: Path) -> None:
    url = f"{base}/projects/{project_id}/attachments?name={urllib.parse.quote(file.name)}"
    request = urllib.request.Request(url, data=file.read_bytes(), method="POST",
                                     headers={"Content-Type": "application/octet-stream"})
    try:
        with urllib.request.urlopen(request, timeout=120):
            print(f"Вложение {file.name} загружено")
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Загрузка {file.name}: {exc.code} {exc.read().decode('utf-8', 'replace')}") from exc


if __name__ == "__main__":
    sys.exit(main())
