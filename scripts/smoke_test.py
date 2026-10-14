#!/usr/bin/env python3
"""Smoke test a running FullSend instance: the five checks that prove a deploy worked.

Usage: python scripts/smoke_test.py http://127.0.0.1:8000

Used after `docker run`, after `kubectl port-forward`, and by the Infrastructure
workflow after it deploys to a kind cluster. Standard library only, so it runs
anywhere Python runs, with nothing to install.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any


def request(url: str, method: str = "GET", body: dict[str, Any] | None = None) -> tuple[int, str]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as res:  # nosec B310  # URL given by the operator
            return res.status, res.read().decode()
    except urllib.error.HTTPError as exc:
        with exc:  # close the error response; Python 3.14 warns about one left open
            return exc.code, exc.read().decode()


def wait_until_ready(base: str, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if request(f"{base}/healthz/ready")[0] == 200:
                return True
        except OSError:
            pass
        time.sleep(1)
    return False


def run(base: str, timeout: float = 60) -> list[str]:
    base = base.rstrip("/")
    failures: list[str] = []
    if not wait_until_ready(base, timeout):
        return [f"{base}/healthz/ready did not answer 200 within {timeout:.0f}s"]

    checks: list[tuple[str, int, str, str, dict[str, Any] | None]] = [
        ("liveness", 200, "GET", "/healthz/live", None),
        ("info", 200, "GET", "/api/v1/info", None),
        (
            "record a deployment",
            201,
            "POST",
            "/api/v1/deployments",
            {"service": "smoke-test", "version": "0.0.1", "environment": "dev"},
        ),
        ("list deployments", 200, "GET", "/api/v1/deployments", None),
        ("metrics", 200, "GET", "/metrics/", None),
    ]
    for name, expected, method, path, body in checks:
        status, text = request(f"{base}{path}", method, body)
        mark = "✓" if status == expected else "✗"
        print(f"{mark} {name}: {method} {path} -> {status}")
        if status != expected:
            failures.append(f"{name}: expected {expected}, got {status}: {text[:200]}")
    return failures


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    failures = run(argv[0])
    for failure in failures:
        print(f"FAILED {failure}")
    print("smoke test passed" if not failures else f"smoke test failed ({len(failures)})")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
