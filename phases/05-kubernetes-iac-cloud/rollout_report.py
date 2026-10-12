#!/usr/bin/env python3
"""Report Deployments that are not fully rolled out, from kubectl's JSON output.

Usage (same on macOS and Windows):
  kubectl get deployments -A -o json > deploys.json
  python phases/05-kubernetes-iac-cloud/rollout_report.py deploys.json

Python reading kubectl's JSON is a pattern worth copying: no cluster libraries,
easy to test with saved output, and it works against any cluster kubectl reaches.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Rollout:
    name: str
    desired: int
    ready: int
    updated: int
    problem: str

    @property
    def healthy(self) -> bool:
        return not self.problem


def assess(item: dict[str, Any]) -> Rollout:
    meta, spec, status = item["metadata"], item.get("spec", {}), item.get("status", {})
    name = f"{meta.get('namespace', 'default')}/{meta['name']}"
    desired = spec.get("replicas", 1)
    ready = status.get("readyReplicas", 0)
    updated = status.get("updatedReplicas", 0)
    conditions = {c["type"]: c for c in status.get("conditions", [])}
    progressing = conditions.get("Progressing", {})
    if progressing.get("reason") == "ProgressDeadlineExceeded":
        problem = "rollout stuck (ProgressDeadlineExceeded): check pod events and logs"
    elif updated < desired:
        problem = f"rollout in progress: {updated}/{desired} pods on the new version"
    elif ready < desired:
        problem = f"only {ready}/{desired} pods ready: check readiness probes"
    else:
        problem = ""
    return Rollout(name, desired, ready, updated, problem)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    data = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    rollouts = [assess(item) for item in data.get("items", [])]
    for r in rollouts:
        mark = "✓" if r.healthy else "✗"
        print(f"{mark} {r.name:<40} ready {r.ready}/{r.desired}  {r.problem}")
    unhealthy = [r for r in rollouts if not r.healthy]
    print(f"\n{len(rollouts) - len(unhealthy)}/{len(rollouts)} deployments fully rolled out")
    return 1 if unhealthy else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
