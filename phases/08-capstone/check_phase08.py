"""Self-check for Phase 8: the course itself stays consistent.

Run: python -m pytest phases/08-capstone
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PHASES = sorted(p for p in (ROOT / "phases").iterdir() if p.is_dir() and p.name[:2].isdigit())


def test_there_are_nine_phases_in_order() -> None:
    assert [p.name[:2] for p in PHASES] == [f"{n:02d}" for n in range(9)]


@pytest.mark.parametrize("phase", PHASES, ids=lambda p: p.name)
def test_every_phase_has_a_readme_and_a_self_check(phase: Path) -> None:
    assert (phase / "README.md").is_file()
    assert list(phase.glob("check_phase*.py")), "each phase ships its own checks"


@pytest.mark.parametrize("phase", PHASES[1:8], ids=lambda p: p.name)
def test_lessons_have_the_standard_sections(phase: Path) -> None:
    text = (phase / "README.md").read_text(encoding="utf-8")
    for heading in (
        "## Why hiring teams care",
        "## Check yourself",
        "## Interview questions",
        "## AI exercise (with guardrails)",
        "## Done when",
    ):
        assert heading in text, f"{phase.name} is missing '{heading}'"
    assert re.search(r"## Official docs", text), f"{phase.name} must link official docs"


def test_root_readme_links_every_phase() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for phase in PHASES:
        assert f"phases/{phase.name}/README.md" in readme, phase.name
