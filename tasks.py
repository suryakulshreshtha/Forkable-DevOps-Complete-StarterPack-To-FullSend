#!/usr/bin/env python3
"""One task runner for macOS, Windows and Linux: python tasks.py <task>

Why not Make? Make is not installed on Windows by default, and the shell
commands inside a Makefile differ between platforms. Python is already the
language of this repository, so the same command works everywhere.

Run `python tasks.py` with no arguments to list every task.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable  # the Python running this file, i.e. your active virtual environment

TASKS: dict[str, tuple[str, Callable[[list[str]], int]]] = {}


def task(help_text: str) -> Callable[[Callable[[list[str]], int]], Callable[[list[str]], int]]:
    def register(fn: Callable[[list[str]], int]) -> Callable[[list[str]], int]:
        TASKS[fn.__name__.replace("_", "-")] = (help_text, fn)
        return fn

    return register


def run(cmd: Sequence[str], **kwargs: object) -> int:
    print(f"\n$ {' '.join(cmd)}", flush=True)
    return subprocess.call(list(cmd), cwd=ROOT, **kwargs)  # type: ignore[call-overload]


def run_all(*cmds: Sequence[str]) -> int:
    for cmd in cmds:
        code = run(cmd)
        if code != 0:
            return code
    return 0


@task("Install the app and every tool used by the labs into the active virtual env")
def setup(_: list[str]) -> int:
    if sys.prefix == sys.base_prefix:
        print("Activate a virtual environment first (see phases/00-setup/README.md).")
        return 1
    return run_all(
        [PY, "-m", "pip", "install", "--upgrade", "pip"],
        [PY, "-m", "pip", "install", "-e", ".[all]"],
        [PY, "-m", "playwright", "install", "chromium"],
    )


@task("Lint and format-check with Ruff")
def lint(_: list[str]) -> int:
    return run_all([PY, "-m", "ruff", "check", "."], [PY, "-m", "ruff", "format", "--check", "."])


@task("Auto-fix lint issues and format code")
def fmt(_: list[str]) -> int:
    return run_all([PY, "-m", "ruff", "check", "--fix", "."], [PY, "-m", "ruff", "format", "."])


@task("Type-check the app with mypy (strict)")
def typecheck(_: list[str]) -> int:
    return run([PY, "-m", "mypy"])


@task("Unit, API, script and lab-check tests with coverage (no browser)")
def test(extra: list[str]) -> int:
    return run([PY, "-m", "pytest", "--cov", "--cov-report=term", *extra])


@task("Browser end-to-end tests with Playwright (add --headed to watch)")
def e2e(extra: list[str]) -> int:
    return run([PY, "-m", "pytest", "tests/e2e", "-m", "e2e", *extra])


@task("Security checks: dependency CVEs (pip-audit) and code issues (Bandit, medium and up)")
def audit(_: list[str]) -> int:
    # Bandit fails the build on medium and high findings. Low ones (for example
    # "subprocess is imported") are covered by Ruff's S rules, where every exception
    # is written next to the code with its reason. List them all with:
    #   python -m bandit -r src scripts phases ai-ops
    bandit = [PY, "-m", "bandit", "-q", "-r", "src", "scripts", "phases", "ai-ops"]
    return run_all(
        [PY, "-m", "pip_audit", "--skip-editable"],
        [*bandit, "-x", "*/check_phase*.py,*/test_*.py", "--severity-level", "medium"],
    )


@task("Validate YAML/JSON files and Kubernetes manifests against the official API schema")
def validate(_: list[str]) -> int:
    return run_all(
        [PY, "scripts/validate_files.py"],
        [PY, "scripts/validate_k8s.py", "infra/k8s"],
    )


@task("Repository hygiene: links in Markdown, banned tools, attribution lines")
def repo_audit(extra: list[str]) -> int:
    return run([PY, "scripts/repo_audit.py", *extra])


@task("Run the app on http://127.0.0.1:8000 (Ctrl+C to stop)")
def serve(_: list[str]) -> int:
    return run([PY, "-m", "fullsend"], env={**os.environ, "APP_ENV": "local"})


@task("Everything CI runs before a merge: lint, typecheck, test, validate, audit")
def check(_: list[str]) -> int:
    for name in ["lint", "typecheck", "test", "validate", "audit"]:
        code = TASKS[name][1]([])
        if code != 0:
            print(f"\n✗ {name} failed")
            return code
    print("\n✓ all checks passed")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in TASKS:
        width = max(len(n) for n in TASKS)
        print("Usage: python tasks.py <task> [extra args]\n")
        for name, (help_text, _) in TASKS.items():
            print(f"  {name.ljust(width)}  {help_text}")
        return 0 if not argv else 2
    return TASKS[argv[0]][1](argv[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
