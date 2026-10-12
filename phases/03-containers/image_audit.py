#!/usr/bin/env python3
"""Audit a container image's configuration for production readiness.

Usage (same on macOS and Windows):
  docker image inspect fullsend:dev > image.json
  python phases/03-containers/image_audit.py image.json [--max-mb 300]

It reads the JSON that `docker image inspect` prints, so it needs no Docker SDK
and works on any machine. The checks are the ones reviewers ask about first.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SECRET_NAME = re.compile(r"(PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|PRIVATE_?KEY)", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    check: str
    passed: bool
    detail: str


def audit(image: dict[str, Any], max_mb: float = 300.0) -> list[Finding]:
    config = image.get("Config") or {}
    findings: list[Finding] = []

    user = (config.get("User") or "").strip()
    non_root = bool(user) and user.split(":")[0] not in {"root", "0"}
    findings.append(Finding("runs as non-root", non_root, f"User={user or '(empty = root)'}"))

    health = config.get("Healthcheck") or {}
    has_health = bool(health.get("Test")) and health.get("Test") != ["NONE"]
    findings.append(Finding("has a health check", has_health, str(health.get("Test", "none"))))

    ports = sorted((config.get("ExposedPorts") or {}).keys())
    findings.append(Finding("declares its port", bool(ports), ", ".join(ports) or "none"))

    entry = config.get("Entrypoint") or config.get("Cmd")
    findings.append(Finding("has a start command", bool(entry), str(entry)))

    leaked = [
        env.split("=", 1)[0]
        for env in config.get("Env") or []
        if "=" in env and SECRET_NAME.search(env.split("=", 1)[0]) and env.split("=", 1)[1]
    ]
    findings.append(
        Finding("no secrets in ENV", not leaked, ", ".join(leaked) or "nothing secret-looking")
    )

    size_mb = round((image.get("Size") or 0) / 1_000_000, 1)
    findings.append(Finding(f"size under {max_mb:.0f} MB", size_mb <= max_mb, f"{size_mb} MB"))
    return findings


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    max_mb = float(argv[argv.index("--max-mb") + 1]) if "--max-mb" in argv else 300.0
    data = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    image = data[0] if isinstance(data, list) else data
    findings = audit(image, max_mb=max_mb)
    for f in findings:
        print(f"{'✓' if f.passed else '✗'} {f.check:<22} {f.detail}")
    failed = [f for f in findings if not f.passed]
    print(f"\n{len(findings) - len(failed)}/{len(findings)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
