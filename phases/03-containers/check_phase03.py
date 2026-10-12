"""Self-check for Phase 3. Run: python -m pytest phases/03-containers"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import image_audit
import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")

# A trimmed copy of what `docker image inspect` prints for a well-built image.
GOOD: dict[str, Any] = {
    "Size": 182_000_000,
    "Config": {
        "User": "10001:10001",
        "ExposedPorts": {"8000/tcp": {}},
        "Env": ["PATH=/usr/local/bin", "PORT=8000", "APP_GIT_SHA=abc"],
        "Entrypoint": ["python", "-m", "fullsend"],
        "Healthcheck": {"Test": ["CMD", "python", "-c", "..."]},
    },
}


def test_a_well_built_image_passes_every_check() -> None:
    assert all(f.passed for f in image_audit.audit(GOOD))


@pytest.mark.parametrize(
    ("patch", "failing"),
    [
        ({"User": ""}, "runs as non-root"),
        ({"User": "root"}, "runs as non-root"),
        ({"User": "0:0"}, "runs as non-root"),
        ({"Healthcheck": None}, "has a health check"),
        ({"ExposedPorts": {}}, "declares its port"),
        ({"Env": ["DB_PASSWORD=hunter2"]}, "no secrets in ENV"),
    ],
)
def test_each_problem_is_reported(patch: dict[str, Any], failing: str) -> None:
    image = json.loads(json.dumps(GOOD))
    image["Config"].update(patch)
    failed = [f.check for f in image_audit.audit(image) if not f.passed]
    assert failed == [failing]


def test_empty_secret_names_are_fine() -> None:
    image = json.loads(json.dumps(GOOD))
    image["Config"]["Env"] = ["API_KEY="]  # declared but empty: nothing leaked
    assert all(f.passed for f in image_audit.audit(image))


def test_size_budget() -> None:
    big = {**GOOD, "Size": 900_000_000}
    assert [f.passed for f in image_audit.audit(big) if f.check.startswith("size")] == [False]


def test_cli_reads_inspect_output(tmp_path: Path) -> None:
    path = tmp_path / "image.json"
    path.write_text(json.dumps([GOOD]))
    assert image_audit.main([str(path)]) == 0


# The repository's own Dockerfile must keep the practices this phase teaches.


def test_dockerfile_is_multi_stage() -> None:
    assert len(re.findall(r"^FROM ", DOCKERFILE, re.MULTILINE)) == 2


def test_dockerfile_drops_root() -> None:
    assert re.search(r"^USER 10001", DOCKERFILE, re.MULTILINE)


def test_dockerfile_has_a_healthcheck_and_exec_form_entrypoint() -> None:
    assert "HEALTHCHECK" in DOCKERFILE
    assert re.search(r'^ENTRYPOINT \["python", "-m", "fullsend"\]', DOCKERFILE, re.MULTILINE)


def test_dockerignore_allows_only_what_the_build_needs() -> None:
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert ignore[ignore.index("*")] == "*"  # ignore everything by default
    assert "!src/" in ignore
