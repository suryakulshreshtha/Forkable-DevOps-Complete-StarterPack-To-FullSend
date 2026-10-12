"""CI triage: an MCP server that helps an AI assistant explain failed GitHub Actions runs.

Design rules (see ai-ops/GUARDRAILS.md):
* Read-only by default. The only write tool refuses to act unless a human set
  CI_TRIAGE_ALLOW_WRITES=1 *and* the call passes confirm=true.
* Least privilege. A fine-grained token with "Actions: read" is enough for every
  read tool. "Issues: write" is needed only if you enable writes.
* Secrets never leave. Logs are redacted before any text is returned.
"""

__version__ = "1.0.0"
