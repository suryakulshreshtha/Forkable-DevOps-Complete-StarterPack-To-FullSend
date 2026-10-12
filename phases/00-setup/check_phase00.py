"""Self-check for Phase 0. Run: python -m pytest phases/00-setup"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any

import doctor
import pytest


def test_python_is_new_enough() -> None:
    assert sys.version_info >= (3, 12), "Install Python 3.14 (see the setup table)"


@pytest.mark.skipif(os.environ.get("CI") == "true", reason="CI runners use a managed Python")
def test_you_are_inside_a_virtual_environment() -> None:
    assert sys.prefix != sys.base_prefix, "Activate .venv before running the labs"


def test_the_app_package_is_installed() -> None:
    import fullsend

    assert fullsend.__version__


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("git version 2.56.0", (2, 56, 0)),
        ("Docker version 29.8.2, build 7fc2dff", (29, 8, 2)),
        ("Client Version: v1.37.1", (1, 37, 1)),
        ("kind v0.33.0 go1.25 linux/amd64", (0, 33, 0)),
        ("v4.3.0+gbec5b06", (4, 3, 0)),
        ("Terraform v1.16.5", (1, 16, 5)),
        ("aws-cli/2.27.41 Python/3.11.6", (2, 27, 41)),
        ("no digits here", None),
    ],
)
def test_doctor_reads_real_version_strings(text: str, expected: tuple[int, ...] | None) -> None:
    assert doctor.parse_version(text) == expected


def test_doctor_reports_missing_and_old_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None if name == "kind" else name)

    def fake_run(cmd: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        out = {"git": "git version 2.10.0"}.get(cmd[0], "v99.0.0")
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)
    by_name = {t.name: doctor.probe(t) for t in doctor.TOOLS}
    assert by_name["kind"] == ("missing", None)
    assert by_name["git"][0] == "old"
    assert by_name["helm"][0] == "ok"
    assert doctor.main(["--strict"]) == 1  # git is needed in phase 0 and is too old
