"""Self-check for Phase 2. Run: python -m pytest phases/02-workflow"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import commit_msg_check as cmc
import pytest

HOOK = Path(__file__).parent / "hooks" / "commit-msg"


@pytest.mark.parametrize(
    "message",
    [
        "feat: add dora endpoint",
        "fix(api): reject empty service names",
        "feat!: drop the v0 API",
        "docs(phase-02): explain rebase\n\nLonger body here.",
        "# comment lines are ignored\nci: pin actions to commit SHAs",
        "Merge branch 'main' into feature",
    ],
)
def test_good_messages_pass(message: str) -> None:
    assert cmc.check(message) == []


@pytest.mark.parametrize(
    ("message", "fragment"),
    [
        ("added stuff", "header must look like"),
        ("feature: add x", "header must look like"),
        ("feat: Add x", "lower case"),
        ("feat: add x.", "period"),
        ("feat: " + "x" * 80, "72 characters"),
        ("feat: add x\nbody without blank line", "blank line"),
        ("", "empty"),
    ],
)
def test_bad_messages_explain_the_problem(message: str, fragment: str) -> None:
    assert any(fragment in problem for problem in cmc.check(message))


# Built from pieces so this file never contains the whole denied phrase.
AI_TRAILER = "Co-Authored-" + "By: Example Bot <bot@example.com>"
AI_FOOTER = "Written with " + "Chat" + "GPT"


@pytest.mark.parametrize(
    "message",
    [
        f"feat: add x\n\n{AI_TRAILER}",
        f"fix: add y\n\nBody.\n\n{AI_FOOTER}",
        f"Merge branch 'main'\n\n{AI_TRAILER}",
    ],
)
def test_ai_attribution_is_rejected(message: str) -> None:
    assert any("AI credit" in problem for problem in cmc.check(message))


def test_human_trailers_are_fine() -> None:
    message = "feat: add x\n\nSigned-off-by: Jane Doe <jane@example.com>\nRefs: #12"
    assert cmc.check(message) == []


def test_the_hook_script_exists_and_calls_the_checker() -> None:
    text = HOOK.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/sh")
    assert "commit_msg_check.py" in text


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_hook_blocks_a_bad_commit_in_a_real_repository(tmp_path: Path) -> None:
    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=tmp_path, capture_output=True, text=True)

    git("init", "-q")
    git("config", "user.name", "Lab")
    git("config", "user.email", "lab@example.com")
    git("config", "core.hooksPath", str(HOOK.parent))
    (tmp_path / "a.txt").write_text("a")
    git("add", "a.txt")
    assert git("commit", "-q", "-m", "did things").returncode != 0
    assert git("commit", "-q", "-m", "feat: add a.txt", "-m", AI_TRAILER).returncode != 0
    assert git("commit", "-q", "-m", "feat: add a.txt").returncode == 0
