"""Self-check for Phase 7. Run: python -m pytest phases/07-security-ai"""

from __future__ import annotations

from pathlib import Path

import pytest
import secret_scan
import yaml

ROOT = Path(__file__).resolve().parents[2]

# Fake secrets are assembled at run time so this file never contains one.
FAKE_GH = "ghp_" + "a1B2c3D4" * 5
FAKE_AWS = "AKIA" + "ABCDEFGHIJKLMNOP"


@pytest.mark.parametrize(
    ("line", "rule"),
    [
        (f"token = {FAKE_GH}", "GitHub token"),
        (f"aws_access_key_id={FAKE_AWS}", "AWS access key ID"),
        ("-----BEGIN OPENSSH " + "PRIVATE KEY-----", "Private key"),
        ('password = "' + "correct-horse-battery" + '"', "Hard-coded credential"),
    ],
)
def test_each_rule_fires(line: str, rule: str) -> None:
    hits = secret_scan.scan_text(line, "x.py")
    assert [h.rule for h in hits] == [rule]


@pytest.mark.parametrize(
    "line",
    [
        'password = os.environ["DB_PASSWORD"]',  # read from the environment: fine
        'token = ""',
        "the word token appears in prose",
        f"fixture = '{FAKE_GH}'  # secret-scan: allow",
    ],
)
def test_safe_lines_pass(line: str) -> None:
    assert secret_scan.scan_text(line, "x.py") == []


def test_scan_walks_folders_and_skips_binaries(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("print('hi')\n")
    (tmp_path / "bad.env").write_text(f"GITHUB_TOKEN={FAKE_GH}\n")
    (tmp_path / "blob.bin").write_bytes(b"\xff\xfe\x00\x01")
    hits = secret_scan.scan([str(tmp_path)])
    assert [(Path(h.path).name, h.line) for h in hits] == [("bad.env", 1)]


def test_this_repository_has_no_secrets() -> None:
    targets = [
        str(ROOT / d) for d in ("src", "tests", "scripts", "phases", "infra", "observability")
    ]
    assert secret_scan.scan(targets) == []


# ------------------------------------------------------------------ supply-chain guarantees in CI


def test_trivy_action_is_pinned_to_the_reviewed_commit() -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25" in ci


def test_only_the_image_job_can_write_packages() -> None:
    ci = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    writers = [name for name, job in ci["jobs"].items() if "packages" in job.get("permissions", {})]
    assert writers == ["image"]


def test_pods_get_no_kubernetes_api_token() -> None:
    dep = yaml.safe_load((ROOT / "infra/k8s/deployment.yaml").read_text(encoding="utf-8"))
    assert dep["spec"]["template"]["spec"]["automountServiceAccountToken"] is False


def test_agent_write_tool_is_off_by_default() -> None:
    server = (ROOT / "src/ci_triage/server.py").read_text(encoding="utf-8")
    assert 'os.environ.get("CI_TRIAGE_ALLOW_WRITES") != "1"' in server
    assert "confirm: bool = False" in server
