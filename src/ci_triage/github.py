"""A small GitHub REST API client for the endpoints the triage tools need.

Endpoints (GitHub REST API docs, "Actions" and "Issues" sections):
  GET  /repos/{owner}/{repo}/actions/runs?status=failure
  GET  /repos/{owner}/{repo}/actions/runs/{run_id}
  GET  /repos/{owner}/{repo}/actions/runs/{run_id}/jobs
  GET  /repos/{owner}/{repo}/actions/jobs/{job_id}/logs   (302 redirect to a plain-text log)
  POST /repos/{owner}/{repo}/issues
"""

from __future__ import annotations

import re
from typing import Any

import httpx
from pydantic import BaseModel

API = "https://api.github.com"
API_VERSION = "2026-03-10"
MAX_LOG_BYTES = 400_000  # keep only the tail of very long logs
_REPO = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$")


class RepoError(ValueError):
    pass


class Run(BaseModel):
    id: int
    name: str
    head_branch: str | None
    head_sha: str
    status: str
    conclusion: str | None
    html_url: str
    created_at: str


class Step(BaseModel):
    name: str
    conclusion: str | None


class Job(BaseModel):
    id: int
    name: str
    conclusion: str | None
    steps: list[Step] = []


def parse_repo(repo: str) -> tuple[str, str]:
    """'owner/name' -> ('owner', 'name'), rejecting anything that is not a repo slug."""
    if not _REPO.match(repo):
        raise RepoError(f"expected 'owner/name', got {repo!r}")
    owner, name = repo.split("/", 1)
    return owner, name


class GitHubClient:
    def __init__(self, token: str | None = None, transport: httpx.BaseTransport | None = None):
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": API_VERSION}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._http = httpx.Client(
            base_url=API,
            headers=headers,
            timeout=20.0,
            follow_redirects=True,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def _get(self, path: str, **params: Any) -> Any:
        response = self._http.get(path, params={k: v for k, v in params.items() if v is not None})
        response.raise_for_status()
        return response.json()

    def failed_runs(self, repo: str, branch: str | None = None, limit: int = 5) -> list[Run]:
        owner, name = parse_repo(repo)
        data = self._get(
            f"/repos/{owner}/{name}/actions/runs", status="failure", branch=branch, per_page=limit
        )
        return [Run.model_validate(r) for r in data["workflow_runs"][:limit]]

    def run(self, repo: str, run_id: int) -> Run:
        owner, name = parse_repo(repo)
        return Run.model_validate(self._get(f"/repos/{owner}/{name}/actions/runs/{run_id}"))

    def jobs(self, repo: str, run_id: int) -> list[Job]:
        owner, name = parse_repo(repo)
        data = self._get(f"/repos/{owner}/{name}/actions/runs/{run_id}/jobs", per_page=100)
        return [Job.model_validate(j) for j in data["jobs"]]

    def job_log(self, repo: str, job_id: int) -> str:
        owner, name = parse_repo(repo)
        response = self._http.get(f"/repos/{owner}/{name}/actions/jobs/{job_id}/logs")
        response.raise_for_status()
        return response.content[-MAX_LOG_BYTES:].decode("utf-8", errors="replace")

    def create_issue(self, repo: str, title: str, body: str) -> str:
        owner, name = parse_repo(repo)
        response = self._http.post(
            f"/repos/{owner}/{name}/issues", json={"title": title, "body": body}
        )
        response.raise_for_status()
        return str(response.json()["html_url"])
