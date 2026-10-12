"""Pure functions that turn a raw CI log into something a human can act on.

No network, no AI: deterministic rules first. An assistant built on top of these
tools reasons over clean, redacted, short evidence instead of megabytes of log.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Token shapes that must never be echoed back. Order matters: specific before generic.
_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b"), "[REDACTED_AWS_KEY_ID]"),
    (
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
        "[REDACTED_PRIVATE_KEY]",
    ),
    (re.compile(r"(?i)(authorization:\s*bearer\s+)[^\s]+"), r"\1[REDACTED]"),
    (
        re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key)(\s*[=:]\s*)[^\s'\"]+"),
        r"\1\2[REDACTED]",
    ),
]

# A GitHub Actions log line starts with an ISO timestamp; strip it for readability.
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z\s?")

_SIGNAL = re.compile(
    r"(##\[error\]|\berror\b|\bfailed\b|\bfailure\b|traceback|exception|assert|"
    r"^E\s{2,}|exit code [1-9]|timed out|fatal:)",
    re.IGNORECASE,
)

# (category, patterns) checked in order; first match wins.
_CATEGORIES: list[tuple[str, tuple[str, ...]]] = [
    ("timeout", ("timed out", "timeout", "exceeded the maximum execution time", "was canceled")),
    (
        "dependency-install",
        (
            "could not find a version",
            "no matching distribution",
            "resolutionimpossible",
            "npm err!",
            "pip install",
            "failed to download",
        ),
    ),
    ("lint-or-format", ("ruff", "would reformat", "flake8", "eslint", "lint")),
    ("type-check", ("mypy", "error: incompatible type", "type error")),
    ("test-failure", ("failed tests", "assertionerror", "pytest", "=== failures ===", " failed,")),
    ("security-scan", ("vulnerability", "cve-", "trivy", "pip-audit", "bandit")),
    ("container-build", ("docker", "buildx", "dockerfile", "failed to solve")),
    (
        "infrastructure",
        (
            "connection reset",
            "could not resolve host",
            "rate limit",
            "503 service unavailable",
            "no space left on device",
        ),
    ),
]


@dataclass(frozen=True)
class Excerpt:
    category: str
    lines: list[str]
    total_lines: int


def redact(text: str) -> str:
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def clean_line(line: str) -> str:
    return _TIMESTAMP.sub("", line).rstrip()


def classify(log: str) -> str:
    lowered = log.lower()
    for category, needles in _CATEGORIES:
        if any(needle in lowered for needle in needles):
            return category
    return "unknown"


def excerpt(log: str, max_lines: int = 40, context: int = 2) -> Excerpt:
    """Keep the lines that look like failure signals, plus a little context."""
    lines = [clean_line(line) for line in redact(log).splitlines()]
    keep: set[int] = set()
    for i, line in enumerate(lines):
        if _SIGNAL.search(line):
            keep.update(range(max(0, i - context), min(len(lines), i + context + 1)))
    chosen = [lines[i] for i in sorted(keep)]
    if len(chosen) > max_lines:  # the end of a log is usually where the real error is
        chosen = ["…", *chosen[-max_lines:]]
    return Excerpt(category=classify(log), lines=chosen, total_lines=len(lines))


def issue_markdown(
    *,
    repo: str,
    run_name: str,
    run_url: str,
    head_sha: str,
    failed_steps: list[str],
    findings: list[Excerpt],
) -> str:
    """A draft issue a human reviews before anything is posted."""
    categories = sorted({f.category for f in findings}) or ["unknown"]
    parts = [
        f"## CI failure: {run_name}",
        "",
        f"* Repository: `{repo}`",
        f"* Run: {run_url}",
        f"* Commit: `{head_sha[:12]}`",
        f"* Likely category: **{', '.join(categories)}**",
        "",
        "### Failed steps",
        *[f"- {step}" for step in failed_steps or ["(no step reported as failed)"]],
        "",
        "### Evidence (redacted)",
    ]
    for finding in findings:
        parts += ["```text", *finding.lines, "```"]
    parts += [
        "",
        "### Next steps",
        "- [ ] Reproduce locally with `python tasks.py check`",
        "- [ ] Confirm the category above; it is a rule-based guess",
        "- [ ] Link the fix PR here",
    ]
    return "\n".join(parts)
