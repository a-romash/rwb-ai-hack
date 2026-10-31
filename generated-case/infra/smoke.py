#!/usr/bin/env python3
"""Smoke probe for the product stand.

1. GET {BASE_URL}/health must answer 200; otherwise the probe fails (exit 1).
2. With --report, every role from infra/roles.json (written by scaffold from app.json) logs in
   through POST {BASE_URL}/api/auth/login {"role": ...} and makes one authorised request.
   The JSON report lists login and request per role; verify decides what passed.

BASE_URL defaults to http://backend:8080, the backend service inside the stand network.
check(base) does not need Docker or the stand.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROLES = Path(__file__).resolve().parent / "roles.json"


def _request(url: str, *, data: dict | None = None, token: str | None = None) -> tuple[int, bytes]:
    body = json.dumps(data).encode() if data is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.getcode(), response.read()
    except urllib.error.HTTPError as exc:
        exc.close()
        return exc.code, b""
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return 0, b""


def check(base: str) -> bool:
    """GET {base}/health answers 200."""
    return _request(base.rstrip("/") + "/health")[0] == 200


def roles(base: str, names: list[str]) -> dict[str, dict[str, bool]]:
    result = {}
    for role in names:
        status, body = _request(base.rstrip("/") + "/api/auth/login", data={"role": role})
        token = None
        if status == 200:
            try:
                token = json.loads(body).get("token")
            except (ValueError, AttributeError):
                token = None
        request = _request(base.rstrip("/") + "/api/auth/me", token=token)[0] == 200 if token else False
        result[role] = {"login": bool(token), "request": request}
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args, _ = parser.parse_known_args(sys.argv[1:] if argv is None else argv)
    base = os.environ.get("BASE_URL", "http://backend:8080")
    healthy = check(base)
    if args.report:
        names = json.loads(ROLES.read_text(encoding="utf-8")) if ROLES.is_file() else []
        evidence = {"health": healthy, "roles": roles(base, names) if healthy else {}}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if healthy:
        print("ok")
        return 0
    print("health check failed", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
