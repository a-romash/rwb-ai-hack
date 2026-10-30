#!/usr/bin/env python3
"""Smoke probe for the product stack.

Auth contract (this skeleton has no auth yet):
Roles engineer and dispatcher do not POST /api/auth/login.
Both roles use the same unauthenticated probe:
GET {BASE_URL}/health
A 200 response prints ok and exits 0. Any other result exits 1.

BASE_URL defaults to http://localhost:8080.
check(base) does not need Docker or the compose stack.
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request


def check(base: str) -> bool:
    """GET {base}/health. Login is not called for engineer or dispatcher."""
    url = base.rstrip("/") + "/health"
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.getcode() == 200
    except urllib.error.HTTPError as exc:
        exc.close()
        return False
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


def main() -> int:
    base = os.environ.get("BASE_URL", "http://localhost:8080")
    if check(base):
        print("ok")
        return 0
    print("health check failed", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
