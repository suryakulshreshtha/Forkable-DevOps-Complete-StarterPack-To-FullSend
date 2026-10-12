# AI operations: the CI triage MCP server

A small MCP server, written in Python with the official MCP Python SDK (v2), that
helps an AI assistant explain failed GitHub Actions runs. It is the hands-on part
of [Phase 7](../phases/07-security-ai/README.md).

| Piece | File |
|---|---|
| MCP server and its four tools | [`src/ci_triage/server.py`](../src/ci_triage/server.py) |
| GitHub REST client (five endpoints) | [`src/ci_triage/github.py`](../src/ci_triage/github.py) |
| Log redaction, classification, excerpts, issue drafts | [`src/ci_triage/triage.py`](../src/ci_triage/triage.py) |
| Tests: fake GitHub plus an in-process MCP client | [`tests/agent/`](../tests/agent/) |
| Try it without any AI | [`try_triage.py`](try_triage.py) |
| Why each guardrail exists | [`GUARDRAILS.md`](GUARDRAILS.md) |

## Tools

| Tool | Kind | Returns |
|---|---|---|
| `list_failed_runs(repo, branch=None, limit=5)` | read | Recent failed workflow runs |
| `explain_failure(repo, run_id)` | read | Failed jobs and steps, a rule-based category, redacted evidence lines |
| `draft_issue(repo, run_id)` | read | A Markdown issue draft; nothing is posted |
| `open_issue(repo, run_id, confirm=False)` | write | Posts the draft only if `CI_TRIAGE_ALLOW_WRITES=1` **and** `confirm=true` |

## 1. Install

With your virtual environment active (same on every OS):

| Step | Command |
|---|---|
| Install the agent extra (already done by `python tasks.py setup`) | `python -m pip install -e ".[agent]"` |
| Run the tests | `python -m pytest tests/agent` |

## 2. Create a least-privilege token

GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate:

| Setting | Value |
|---|---|
| Repository access | Only select repositories → your fork |
| Permissions → Actions | Read-only |
| Permissions → Issues | No access (Read and write **only** if you will enable `open_issue`) |
| Expiration | Short, for example 30 days |

For a public repository the read endpoints also work without a token, but
unauthenticated requests have much lower rate limits.

## 3. Try it without an AI

Set the token for this terminal, then call the tools directly.

| Step | macOS / Linux | Windows PowerShell |
|---|---|---|
| Set the token | `export GITHUB_TOKEN=<your token>` | `$env:GITHUB_TOKEN = "<your token>"` |
| List failed runs | `python ai-ops/try_triage.py <owner>/<repo>` | same |
| Explain one | `python ai-ops/try_triage.py <owner>/<repo> <run_id>` | same |

## 4. Connect an MCP-compatible assistant

Desktop assistants and IDEs that support MCP start local servers over **stdio**
from a JSON configuration. The exact file and key names differ by client, so check
your client's MCP documentation; the usual shape is in
[`mcp-client-config.example.json`](mcp-client-config.example.json):

```json
{
  "mcpServers": {
    "ci-triage": {
      "command": "/absolute/path/to/your/.venv/bin/ci-triage-mcp",
      "env": { "GITHUB_TOKEN": "<fine-grained, read-only token>" }
    }
  }
}
```

| | macOS / Linux | Windows |
|---|---|---|
| Path to the server command | `<repo>/.venv/bin/ci-triage-mcp` | `<repo>\.venv\Scripts\ci-triage-mcp.exe` |
| Find it | `which ci-triage-mcp` (venv active) | `Get-Command ci-triage-mcp` (venv active) |

Keep `CI_TRIAGE_ALLOW_WRITES` out of the configuration unless you are deliberately
testing `open_issue`.

## 5. Use it well

Ask: *"Which recent runs failed on my fork, and why did the newest one fail?"* Then
check the answer against the real log on GitHub. The category is a rule-based
guess and the evidence is an excerpt: the assistant can still misread both.
