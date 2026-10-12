#!/usr/bin/env python3
"""Find secrets before they reach Git: tokens, cloud keys, private keys.

Usage:
  python phases/07-security-ai/secret_scan.py src tests          # scan paths
  python phases/07-security-ai/secret_scan.py --staged           # scan files staged for commit

Add `secret-scan: allow` on a line to accept a known false positive (a test
fixture, a documented example). A secret that reached a remote must be treated
as leaked: revoke and rotate it; deleting the commit is not enough.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ALLOW = "secret-scan: allow"
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".cache", ".terraform"}

RULES: list[tuple[str, re.Pattern[str]]] = [
    ("GitHub token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})\b")),
    ("AWS access key ID", re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("Private key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |)PRIVATE KEY-----")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    (
        "Hard-coded credential",
        re.compile(
            r"(?i)\b(password|passwd|secret|api_?key|token)\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"
        ),
    ),
]


@dataclass(frozen=True)
class Hit:
    path: str
    line: int
    rule: str


def scan_text(text: str, path: str) -> list[Hit]:
    hits = []
    for number, line in enumerate(text.splitlines(), start=1):
        if ALLOW in line:
            continue
        for rule, pattern in RULES:
            if pattern.search(line):
                hits.append(Hit(path, number, rule))
    return hits


def iter_files(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        p = Path(target)
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files += [
                f for f in p.rglob("*") if f.is_file() and not SKIP_DIRS.intersection(f.parts)
            ]
    return sorted(files)


def staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def scan(targets: list[str]) -> list[Hit]:
    hits: list[Hit] = []
    for path in iter_files(targets):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable
        hits += scan_text(text, str(path))
    return hits


def main(argv: list[str]) -> int:
    targets = staged_files() if argv == ["--staged"] else (argv or ["."])
    hits = scan(targets)
    for hit in hits:
        print(f"✗ {hit.path}:{hit.line}: possible {hit.rule}")
    print(f"secret scan: {len(hits)} finding(s)")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
