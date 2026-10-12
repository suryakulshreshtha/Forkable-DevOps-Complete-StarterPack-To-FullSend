#!/usr/bin/env python3
"""Check a commit message against the Conventional Commits 1.0.0 format.

Usage:
  python phases/02-workflow/commit_msg_check.py .git/COMMIT_EDITMSG   # as a git hook
  python phases/02-workflow/commit_msg_check.py --message "feat: add dora endpoint"

Format:  <type>[optional scope][!]: <description>
  feat(api): record rollbacks as a separate status
  fix!: reject service names with uppercase letters

Why bother? Structured messages make history searchable, let tools generate
changelogs and pick version numbers (feat -> minor, fix -> patch, ! -> major),
and make "what changed in this release?" a query instead of an archaeology dig.

The hook also rejects AI attribution (AI co-author trailers, tool footers, session
links): commits carry your name only. It reuses the hashed deny-list in
scripts/repo_audit.py, so the list lives in one place.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from functools import cache
from pathlib import Path
from types import ModuleType

REPO_AUDIT = Path(__file__).resolve().parents[2] / "scripts" / "repo_audit.py"
ATTRIBUTION = "AI-attribution marker"

TYPES = (
    "build",
    "chore",
    "ci",
    "docs",
    "feat",
    "fix",
    "perf",
    "refactor",
    "revert",
    "style",
    "test",
)
HEADER = re.compile(
    rf"^(?P<type>{'|'.join(TYPES)})(?:\((?P<scope>[a-z0-9-]+)\))?(?P<breaking>!)?: (?P<desc>\S.*)$"
)
MAX_HEADER = 72


@cache
def _repo_audit() -> ModuleType | None:
    """Load scripts/repo_audit.py by path; None if this file was copied elsewhere."""
    spec = importlib.util.spec_from_file_location("repo_audit", REPO_AUDIT)
    if spec is None or spec.loader is None or not REPO_AUDIT.is_file():
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def attribution_lines(lines: list[str]) -> list[int]:
    """Return 1-based numbers of lines that carry AI attribution."""
    audit = _repo_audit()
    if audit is None:
        return []
    return [
        number
        for number, line in enumerate(lines, start=1)
        if any(category == ATTRIBUTION for category, _ in audit.line_findings(line))
    ]


def check(message: str) -> list[str]:
    """Return a list of problems; an empty list means the message is fine."""
    lines = [line for line in message.splitlines() if not line.startswith("#")]
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return ["the message is empty"]
    header = lines[0]
    problems = [
        f"remove AI credit from line {number} ({lines[number - 1].strip()[:50]!r});"
        " no AI co-author trailers, tool footers or session links"
        for number in attribution_lines(lines)
    ]
    if header.startswith(("Merge ", 'Revert "')):
        return problems  # headers git writes for you are fine
    match = HEADER.match(header)
    if not match:
        problems.append(
            f"header must look like '<type>(scope): description'; types: {', '.join(TYPES)}"
        )
    else:
        desc = match["desc"]
        if desc[0].isupper():
            problems.append("start the description in lower case")
        if desc.endswith("."):
            problems.append("do not end the header with a period")
    if len(header) > MAX_HEADER:
        problems.append(f"keep the header to {MAX_HEADER} characters (it is {len(header)})")
    if len(lines) > 1 and lines[1].strip():
        problems.append("leave a blank line between the header and the body")
    return problems


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    message = argv[1] if argv[0] == "--message" else Path(argv[0]).read_text(encoding="utf-8")
    problems = check(message)
    for problem in problems:
        print(f"✗ commit message: {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
