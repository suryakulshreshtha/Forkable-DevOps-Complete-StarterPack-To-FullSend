"""An in-memory stand-in for the GitHub REST API, built on httpx.MockTransport.

No network and no token: every test is fast and repeatable.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

RUN = {
    "id": 101,
    "name": "CI",
    "head_branch": "main",
    "head_sha": "0123456789abcdef0123456789abcdef01234567",
    "status": "completed",
    "conclusion": "failure",
    "html_url": "https://github.com/acme/shop/actions/runs/101",
    "created_at": "2026-10-01T10:00:00Z",
}

JOBS = {
    "total_count": 2,
    "jobs": [
        {
            "id": 7,
            "name": "test (3.14)",
            "conclusion": "failure",
            "steps": [
                {"name": "Set up job", "conclusion": "success"},
                {"name": "Run tests", "conclusion": "failure"},
            ],
        },
        {"id": 8, "name": "lint", "conclusion": "success", "steps": []},
    ],
}

FAKE_TOKEN = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"  # noqa: S105 - fake; secret-scan: allow

LOG = "\n".join(
    [
        "2026-10-01T10:01:00.0000000Z ##[group]Run python -m pytest",
        "2026-10-01T10:01:01.0000000Z collected 40 items",
        "2026-10-01T10:01:02.0000000Z tests/api/test_api.py::test_create FAILED",
        "2026-10-01T10:01:02.5000000Z E   AssertionError: assert 500 == 201",
        f"2026-10-01T10:01:03.0000000Z using token {FAKE_TOKEN}",
        "2026-10-01T10:01:04.0000000Z ==== 1 failed, 39 passed in 3.2s ====",
        "2026-10-01T10:01:05.0000000Z ##[error]Process completed with exit code 1.",
    ]
)


class FakeGitHub:
    """Records every request so tests can assert on what was (not) sent."""

    def __init__(self, status_override: int | None = None) -> None:
        self.requests: list[httpx.Request] = []
        self.status_override = status_override

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.status_override:
            return httpx.Response(self.status_override, json={"message": "nope"})
        path = request.url.path
        routes: dict[tuple[str, str], Any] = {
            ("GET", "/repos/acme/shop/actions/runs"): {"total_count": 1, "workflow_runs": [RUN]},
            ("GET", "/repos/acme/shop/actions/runs/101"): RUN,
            ("GET", "/repos/acme/shop/actions/runs/101/jobs"): JOBS,
        }
        if (request.method, path) in routes:
            return httpx.Response(200, json=routes[(request.method, path)])
        if path == "/repos/acme/shop/actions/jobs/7/logs":
            # The real API answers 302 with a short-lived download URL.
            return httpx.Response(302, headers={"Location": "https://logs.example/job-7.txt"})
        if request.url.host == "logs.example":
            return httpx.Response(200, text=LOG)
        if (request.method, path) == ("POST", "/repos/acme/shop/issues"):
            body = json.loads(request.content)
            return httpx.Response(
                201,
                json={"html_url": "https://github.com/acme/shop/issues/9", "title": body["title"]},
            )
        return httpx.Response(404, json={"message": "Not Found"})

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)
