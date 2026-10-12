#!/usr/bin/env python3
"""Check which tools are installed and whether they are new enough.

Usage: python phases/00-setup/doctor.py [--strict]

Works the same on macOS, Windows and Linux. Missing tools are fine early on:
the table says which phase first needs each one. --strict exits with 1 when a
tool needed by Phase 0 to 2 is missing (CI uses that).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Tool:
    name: str
    command: list[str]
    minimum: tuple[int, ...]
    phase: int
    install_hint: str


TOOLS = [
    Tool("git", ["git", "--version"], (2, 40), 0, "phases/00-setup/README.md#2-install-the-tools"),
    Tool("docker", ["docker", "--version"], (25, 0), 3, "Docker Desktop (macOS/Windows)"),
    Tool("kubectl", ["kubectl", "version", "--client"], (1, 36), 5, "phases/05 install table"),
    Tool("kind", ["kind", "version"], (0, 33), 5, "phases/05 install table"),
    Tool("helm", ["helm", "version", "--short"], (4, 0), 5, "phases/05 install table"),
    Tool("terraform", ["terraform", "version"], (1, 10), 5, "phases/05 install table"),
    Tool("aws", ["aws", "--version"], (2, 0), 5, "AWS CLI v2 (optional cloud lab)"),
]

VERSION = re.compile(r"v?(\d+)\.(\d+)(?:\.(\d+))?")


def parse_version(text: str) -> tuple[int, ...] | None:
    match = VERSION.search(text)
    if not match:
        return None
    return tuple(int(part) for part in match.groups() if part is not None)


def probe(tool: Tool) -> tuple[str, tuple[int, ...] | None]:
    """Return (status, version). Status is ok, old, missing or error."""
    if shutil.which(tool.command[0]) is None:
        return "missing", None
    try:
        result = subprocess.run(
            tool.command, capture_output=True, text=True, timeout=20, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return "error", None
    version = parse_version(result.stdout + result.stderr)
    if version is None:
        return "error", None
    return ("ok" if version >= tool.minimum else "old"), version


def fmt(version: tuple[int, ...] | None) -> str:
    return ".".join(map(str, version)) if version else "-"


def main(argv: list[str]) -> int:
    strict = "--strict" in argv
    rows = [
        (
            "python",
            "ok" if sys.version_info >= (3, 12) else "old",
            fmt(sys.version_info[:3]),
            "3.12",
            0,
        )
    ]
    for tool in TOOLS:
        status, version = probe(tool)
        rows.append((tool.name, status, fmt(version), fmt(tool.minimum), tool.phase))

    icons = {"ok": "✓", "old": "↑", "missing": "·", "error": "?"}
    print(f"{'tool':<10} {'status':<9} {'found':<10} {'minimum':<8} first needed")
    for name, status, found, minimum, phase in rows:
        print(f"{name:<10} {icons[status]} {status:<7} {found:<10} {minimum:<8} phase {phase}")
    print("\n✓ ready   ↑ upgrade   · not installed yet   ? installed but version unreadable")

    blocking = [r for r in rows if r[4] <= 2 and r[1] != "ok"]
    if blocking:
        print("\nNeeded now:", ", ".join(r[0] for r in blocking))
    return 1 if strict and blocking else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
