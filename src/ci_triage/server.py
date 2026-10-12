"""MCP server exposing CI triage tools to any MCP-compatible AI assistant.

Start it (stdio transport, which is what desktop assistants and IDEs launch):
    ci-triage-mcp

Environment:
    GITHUB_TOKEN            fine-grained token; "Actions: read" for the read tools
    CI_TRIAGE_ALLOW_WRITES  set to 1 to let open_issue post (also needs "Issues: write")
"""

from __future__ import annotations

import os
from collections.abc import Callable

import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from ci_triage.github import GitHubClient, RepoError, Run
from ci_triage.triage import Excerpt, excerpt, issue_markdown

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=True)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=True)

INSTRUCTIONS = """\
Tools for explaining failed GitHub Actions runs.
Typical flow: list_failed_runs -> explain_failure -> draft_issue.
open_issue posts to GitHub and is disabled unless the human enabled writes;
always show the draft to the human and get explicit approval before calling it.
"""


class FailedJob(BaseModel):
    job: str
    failed_steps: list[str]
    category: str
    evidence: list[str]
    log_lines_scanned: int


class Explanation(BaseModel):
    run: Run
    failed_jobs: list[FailedJob]


class IssueResult(BaseModel):
    created: bool
    message: str
    url: str | None = None


ClientFactory = Callable[[], GitHubClient]


def _default_client() -> GitHubClient:
    return GitHubClient(token=os.environ.get("GITHUB_TOKEN"))


def create_server(client_factory: ClientFactory = _default_client) -> MCPServer:
    server = MCPServer("ci-triage", instructions=INSTRUCTIONS)

    def call[T](fn: Callable[[GitHubClient], T]) -> T:
        client = client_factory()
        try:
            return fn(client)
        except RepoError as exc:
            raise ToolError(str(exc)) from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            hint = " (check GITHUB_TOKEN and its permissions)" if status in (401, 403, 404) else ""
            raise ToolError(f"GitHub answered {status}{hint}") from exc
        except httpx.HTTPError as exc:
            raise ToolError(f"could not reach GitHub: {type(exc).__name__}") from exc
        finally:
            client.close()

    def explain(client: GitHubClient, repo: str, run_id: int) -> Explanation:
        run = client.run(repo, run_id)
        failed = []
        for job in client.jobs(repo, run_id):
            if job.conclusion != "failure":
                continue
            found = excerpt(client.job_log(repo, job.id))
            failed.append(
                FailedJob(
                    job=job.name,
                    failed_steps=[s.name for s in job.steps if s.conclusion == "failure"],
                    category=found.category,
                    evidence=found.lines,
                    log_lines_scanned=found.total_lines,
                )
            )
        return Explanation(run=run, failed_jobs=failed)

    @server.tool(annotations=READ_ONLY)
    def list_failed_runs(repo: str, branch: str | None = None, limit: int = 5) -> list[Run]:
        """List the most recent failed workflow runs for 'owner/name', newest first."""
        if not 1 <= limit <= 20:
            raise ToolError("limit must be between 1 and 20")
        return call(lambda c: c.failed_runs(repo, branch=branch, limit=limit))

    @server.tool(annotations=READ_ONLY)
    def explain_failure(repo: str, run_id: int) -> Explanation:
        """Explain one failed run: failed jobs and steps, a rule-based category,
        and a short redacted log excerpt for each failed job."""
        return call(lambda c: explain(c, repo, run_id))

    @server.tool(annotations=READ_ONLY)
    def draft_issue(repo: str, run_id: int) -> str:
        """Write a Markdown issue draft for a failed run. Nothing is posted."""
        result = call(lambda c: explain(c, repo, run_id))
        return issue_markdown(
            repo=repo,
            run_name=result.run.name,
            run_url=result.run.html_url,
            head_sha=result.run.head_sha,
            failed_steps=[s for j in result.failed_jobs for s in j.failed_steps],
            findings=[
                Excerpt(category=j.category, lines=j.evidence, total_lines=j.log_lines_scanned)
                for j in result.failed_jobs
            ],
        )

    @server.tool(annotations=WRITE)
    def open_issue(repo: str, run_id: int, confirm: bool = False) -> IssueResult:
        """Post the draft as a GitHub issue. Requires CI_TRIAGE_ALLOW_WRITES=1 on the
        server AND confirm=true, which must only be set after a human approved the draft."""
        if os.environ.get("CI_TRIAGE_ALLOW_WRITES") != "1":
            return IssueResult(
                created=False,
                message="Writes are disabled. A human must set CI_TRIAGE_ALLOW_WRITES=1.",
            )
        if not confirm:
            return IssueResult(
                created=False,
                message="Show the draft to the human and call again with confirm=true "
                "only after they approve it.",
            )
        body = draft_issue(repo, run_id)
        title = f"CI failure in run {run_id}"
        url = call(lambda c: c.create_issue(repo, title, body))
        return IssueResult(created=True, message="Issue created.", url=url)

    return server


def main() -> None:
    create_server().run("stdio")


if __name__ == "__main__":
    main()
