#!/usr/bin/env python3
"""Call the CI triage tools directly, through a real MCP client, with no AI involved.

Usage:
  python ai-ops/try_triage.py <owner>/<repo>            # list recent failed runs
  python ai-ops/try_triage.py <owner>/<repo> <run_id>   # explain one run and draft an issue

Reads GITHUB_TOKEN from the environment. Useful to check your token and to see
exactly what an assistant would receive.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from mcp import Client

from ci_triage.server import create_server


async def call(tool: str, args: dict[str, Any]) -> Any:
    async with Client(create_server()) as client:
        return await client.call_tool(tool, args)


def show(result: Any) -> int:
    if result.is_error:
        print(f"error: {result.content[0].text}")
        return 1
    if result.structured_content is not None:
        print(json.dumps(result.structured_content, indent=2))
    else:
        print(result.content[0].text)
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    repo = argv[0]
    if len(argv) == 1:
        return show(asyncio.run(call("list_failed_runs", {"repo": repo})))
    run_id = int(argv[1])
    code = show(asyncio.run(call("explain_failure", {"repo": repo, "run_id": run_id})))
    print("\n--- issue draft (not posted) ---\n")
    return code or show(asyncio.run(call("draft_issue", {"repo": repo, "run_id": run_id})))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
