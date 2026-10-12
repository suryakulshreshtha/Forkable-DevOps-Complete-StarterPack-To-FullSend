"""Tests drive the MCP server exactly as an assistant would: through an MCP client.

The client connects in-process (no subprocess, no network) and GitHub is faked.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from mcp import Client

from ci_triage.github import GitHubClient
from ci_triage.server import create_server
from tests.agent.fake_github import FakeGitHub

TEST_TOKEN = "test-token"  # noqa: S105 - fake; secret-scan: allow


def call(fake: FakeGitHub, tool: str, args: dict[str, Any]) -> Any:
    server = create_server(lambda: GitHubClient(token=TEST_TOKEN, transport=fake.transport))

    async def go() -> Any:
        async with Client(server) as client:
            return await client.call_tool(tool, args)

    return asyncio.run(go())


def test_every_tool_is_listed_with_honest_hints() -> None:
    server = create_server(lambda: GitHubClient(transport=FakeGitHub().transport))

    async def go() -> Any:
        async with Client(server) as client:
            return await client.list_tools()

    tools = {t.name: t for t in asyncio.run(go()).tools}
    assert set(tools) == {"list_failed_runs", "explain_failure", "draft_issue", "open_issue"}
    for name in ["list_failed_runs", "explain_failure", "draft_issue"]:
        assert tools[name].annotations.read_only_hint is True
    assert tools["open_issue"].annotations.read_only_hint is False


def test_list_failed_runs_sends_versioned_authenticated_request() -> None:
    fake = FakeGitHub()
    result = call(fake, "list_failed_runs", {"repo": "acme/shop"})
    assert not result.is_error
    assert result.structured_content["result"][0]["id"] == 101
    sent = fake.requests[0]
    assert sent.url.params["status"] == "failure"
    assert sent.headers["Authorization"] == f"Bearer {TEST_TOKEN}"
    assert sent.headers["X-GitHub-Api-Version"] == "2026-03-10"


def test_explain_failure_reports_only_failed_jobs_with_redacted_evidence() -> None:
    result = call(FakeGitHub(), "explain_failure", {"repo": "acme/shop", "run_id": 101})
    assert not result.is_error
    jobs = result.structured_content["failed_jobs"]
    assert [j["job"] for j in jobs] == ["test (3.14)"]
    assert jobs[0]["failed_steps"] == ["Run tests"]
    assert jobs[0]["category"] == "test-failure"
    assert not any("ghp_" in line for line in jobs[0]["evidence"])


def test_draft_issue_never_posts() -> None:
    fake = FakeGitHub()
    result = call(fake, "draft_issue", {"repo": "acme/shop", "run_id": 101})
    assert "## CI failure: CI" in result.content[0].text
    assert all(r.method == "GET" for r in fake.requests)


def test_open_issue_refuses_when_writes_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CI_TRIAGE_ALLOW_WRITES", raising=False)
    fake = FakeGitHub()
    result = call(fake, "open_issue", {"repo": "acme/shop", "run_id": 101, "confirm": True})
    assert result.structured_content["created"] is False
    assert fake.requests == []


def test_open_issue_needs_explicit_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI_TRIAGE_ALLOW_WRITES", "1")
    fake = FakeGitHub()
    result = call(fake, "open_issue", {"repo": "acme/shop", "run_id": 101})
    assert result.structured_content["created"] is False
    assert not any(r.method == "POST" for r in fake.requests)


def test_open_issue_posts_when_enabled_and_confirmed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI_TRIAGE_ALLOW_WRITES", "1")
    fake = FakeGitHub()
    result = call(fake, "open_issue", {"repo": "acme/shop", "run_id": 101, "confirm": True})
    assert result.structured_content == {
        "created": True,
        "message": "Issue created.",
        "url": "https://github.com/acme/shop/issues/9",
    }
    posts = [r for r in fake.requests if r.method == "POST"]
    assert len(posts) == 1
    assert b"ghp_" not in posts[0].content


@pytest.mark.parametrize(
    ("status", "expected"),
    [(401, "GITHUB_TOKEN"), (404, "GITHUB_TOKEN"), (500, "GitHub answered 500")],
)
def test_github_errors_become_clean_tool_errors(status: int, expected: str) -> None:
    result = call(FakeGitHub(status_override=status), "list_failed_runs", {"repo": "acme/shop"})
    assert result.is_error
    assert expected in result.content[0].text


def test_bad_repo_and_limits_are_rejected_before_any_request() -> None:
    fake = FakeGitHub()
    assert call(fake, "list_failed_runs", {"repo": "not a repo"}).is_error
    assert call(fake, "list_failed_runs", {"repo": "acme/shop", "limit": 50}).is_error
    assert fake.requests == []
