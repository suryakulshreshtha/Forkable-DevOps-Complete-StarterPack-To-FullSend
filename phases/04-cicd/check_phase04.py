"""Self-check for Phase 4. Run: python -m pytest phases/04-cicd"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import dora_from_git as dora
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
DAY = 86400


# ------------------------------------------------------------------ DORA from git


@pytest.fixture
def tagged_repo(tmp_path: Path) -> tuple[Path, int]:
    """A repo with three commits and two release tags at known times."""
    if shutil.which("git") is None:
        pytest.skip("git not installed")
    base = 1_790_000_000  # a fixed moment in 2026
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Lab",
        "GIT_AUTHOR_EMAIL": "lab@example.com",
        "GIT_COMMITTER_NAME": "Lab",
        "GIT_COMMITTER_EMAIL": "lab@example.com",
    }

    def run(*args: str, at: int) -> None:
        stamp = f"@{at} +0000"
        subprocess.run(
            ["git", *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            env={**env, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp},
        )

    run("init", "-q", at=base)
    for i, at in enumerate([base, base + 3600 * 2]):
        (tmp_path / f"f{i}.txt").write_text(str(i))
        run("add", ".", at=at)
        run("commit", "-q", "-m", f"feat: change {i}", at=at)
    run("tag", "-a", "v1.0.0", "-m", "release", at=base + 3600 * 4)  # 4 h and 2 h lead times
    (tmp_path / "f2.txt").write_text("2")
    run("add", ".", at=base + DAY)
    run("commit", "-q", "-m", "fix: change 2", at=base + DAY)
    run("tag", "-a", "v1.0.1", "-m", "release", at=base + DAY + 3600 * 10)  # 10 h lead time
    return tmp_path, base


def test_releases_and_lead_times(tagged_repo: tuple[Path, int]) -> None:
    repo, _ = tagged_repo
    found = dora.releases(repo, "v*")
    assert [r.tag for r in found] == ["v1.0.0", "v1.0.1"]
    assert sorted(found[0].lead_times_h) == [2.0, 4.0]
    assert found[1].lead_times_h == [10.0]


def test_summary(tagged_repo: tuple[Path, int]) -> None:
    repo, base = tagged_repo
    summary = dora.summarise(dora.releases(repo, "v*"), days=7, now=base + 2 * DAY)
    assert summary["deployments"] == 2
    assert summary["per_week"] == 2.0
    assert summary["lead_time_median_h"] == 4.0
    assert summary["lead_time_p90_h"] == 10.0


def test_summary_with_no_releases() -> None:
    assert dora.summarise([], days=30)["deployments"] == 0


# ------------------------------------------------------------------ the workflows themselves

SHA_PIN = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")


def _steps() -> list[tuple[str, dict[str, object]]]:
    found = []
    for wf in WORKFLOWS:
        data = yaml.safe_load(wf.read_text(encoding="utf-8"))
        for job in data["jobs"].values():
            for step in job.get("steps", []):
                found.append((wf.name, step))
    return found


def test_every_action_is_pinned_to_a_full_commit_sha() -> None:
    unpinned = [
        f"{name}: {step['uses']}"
        for name, step in _steps()
        if "uses" in step and not SHA_PIN.match(str(step["uses"]))
    ]
    assert unpinned == []


def test_every_workflow_sets_least_privilege_permissions() -> None:
    for wf in WORKFLOWS:
        data = yaml.safe_load(wf.read_text(encoding="utf-8"))
        assert data.get("permissions") == {"contents": "read"}, wf.name


def test_checkouts_do_not_keep_credentials() -> None:
    for name, step in _steps():
        if str(step.get("uses", "")).startswith("actions/checkout@"):
            assert step.get("with", {}).get("persist-credentials") is False, name  # type: ignore[union-attr]


def test_every_job_has_a_timeout() -> None:
    for wf in WORKFLOWS:
        data = yaml.safe_load(wf.read_text(encoding="utf-8"))
        for job_name, job in data["jobs"].items():
            assert "timeout-minutes" in job, f"{wf.name}:{job_name}"
