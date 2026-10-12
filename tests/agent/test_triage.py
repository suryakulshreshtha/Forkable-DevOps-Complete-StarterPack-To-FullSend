from __future__ import annotations

import pytest

from ci_triage.github import RepoError, parse_repo
from ci_triage.triage import classify, excerpt, issue_markdown, redact
from tests.agent.fake_github import LOG


@pytest.mark.parametrize(
    "secret",
    [
        "ghp_abcdefghijklmnopqrstuvwxyz0123456789",  # secret-scan: allow
        "github_pat_11ABCDEFG0123456789_abcdefghijklmnopqrstuvwxyz",  # secret-scan: allow
        "AKIAABCDEFGHIJKLMNOP",  # secret-scan: allow
    ],
)
def test_redact_removes_token_shapes(secret: str) -> None:
    assert secret not in redact(f"value {secret} end")


def test_redact_masks_key_value_and_bearer_forms() -> None:
    text = redact("password=hunter2 Authorization: Bearer abc.def.ghi api_key: xyz")
    assert "hunter2" not in text
    assert "abc.def.ghi" not in text
    assert "xyz" not in text


def test_redact_masks_private_keys() -> None:
    header = "-----BEGIN RSA PRIVATE KEY-----"  # secret-scan: allow
    key = f"{header}\nMIIabc\n-----END RSA PRIVATE KEY-----"
    assert "MIIabc" not in redact(key)


@pytest.mark.parametrize(
    ("log", "category"),
    [
        ("The job running on runner X has exceeded the maximum execution time", "timeout"),
        (
            "ERROR: Could not find a version that satisfies the requirement foo",
            "dependency-install",
        ),
        ("Would reformat: src/app.py", "lint-or-format"),
        ("src/x.py:3: error: Incompatible types in assignment", "type-check"),
        ("==== 1 failed, 39 passed ====\nAssertionError", "test-failure"),
        ("curl: (6) Could not resolve host: example", "infrastructure"),
        ("all good", "unknown"),
    ],
)
def test_classify(log: str, category: str) -> None:
    assert classify(log) == category


def test_excerpt_keeps_signal_strips_timestamps_and_redacts() -> None:
    found = excerpt(LOG)
    joined = "\n".join(found.lines)
    assert found.category == "test-failure"
    assert "AssertionError: assert 500 == 201" in joined
    assert "##[error]Process completed with exit code 1." in joined
    assert "ghp_" not in joined
    assert not any(line.startswith("2026-") for line in found.lines)
    assert found.total_lines == 7


def test_excerpt_is_bounded() -> None:
    noisy = "\n".join(f"error number {i}" for i in range(500))
    found = excerpt(noisy, max_lines=10)
    assert len(found.lines) == 11  # ellipsis marker + last 10
    assert found.lines[-1] == "error number 499"


def test_issue_markdown_contains_the_essentials() -> None:
    md = issue_markdown(
        repo="acme/shop",
        run_name="CI",
        run_url="https://github.com/acme/shop/actions/runs/101",
        head_sha="0123456789abcdef",
        failed_steps=["Run tests"],
        findings=[excerpt(LOG)],
    )
    assert md.startswith("## CI failure: CI")
    assert "`0123456789ab`" in md
    assert "- Run tests" in md
    assert "**test-failure**" in md


@pytest.mark.parametrize("bad", ["acme", "acme/shop/extra", "../etc/passwd", "a b/c", ""])
def test_parse_repo_rejects_non_slugs(bad: str) -> None:
    with pytest.raises(RepoError):
        parse_repo(bad)
