#!/usr/bin/env python3
"""Stop a Terraform apply that would delete or replace something you did not expect.

Usage (macOS and Windows alike, run in infra/terraform/aws-eks):
  terraform plan -out=plan.out
  terraform show -json plan.out > plan.json
  python ../../../phases/05-kubernetes-iac-cloud/tf_plan_guard.py plan.json [--allow-destroy]

Reads the plan JSON format HashiCorp documents ("JSON Output Format"):
resource_changes[].change.actions is one of
["no-op"], ["create"], ["read"], ["update"], ["delete"],
["delete", "create"] or ["create", "delete"] (the last two are replacements).
Any action list containing "delete" removes an object, so that is what we look for.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Replacing these takes the whole environment down; they always need a human.
CRITICAL_TYPES = {"aws_eks_cluster", "aws_vpc", "aws_db_instance", "aws_s3_bucket"}


@dataclass(frozen=True)
class Verdict:
    counts: Counter[str]
    destructive: list[str]
    critical: list[str]

    @property
    def safe(self) -> bool:
        return not self.destructive


def label(actions: list[str]) -> str:
    if actions in (["delete", "create"], ["create", "delete"]):
        return "replace"
    return actions[0] if actions else "unknown"


def evaluate(plan: dict[str, Any]) -> Verdict:
    counts: Counter[str] = Counter()
    destructive: list[str] = []
    critical: list[str] = []
    for change in plan.get("resource_changes", []):
        actions = change["change"]["actions"]
        kind = label(actions)
        counts[kind] += 1
        if "delete" in actions:
            entry = f"{kind:<8} {change['address']}"
            destructive.append(entry)
            if change.get("type") in CRITICAL_TYPES:
                critical.append(entry)
    return Verdict(counts, destructive, critical)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    plan = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    verdict = evaluate(plan)
    order = ["create", "update", "replace", "delete", "read", "no-op"]
    print("plan: " + ", ".join(f"{k}={verdict.counts[k]}" for k in order if verdict.counts[k]))
    for line in verdict.destructive:
        print(f"  ! {line}")
    for line in verdict.critical:
        print(f"  !! critical resource: {line}")
    if verdict.safe:
        print("✓ nothing will be deleted or replaced")
        return 0
    if "--allow-destroy" in argv and not verdict.critical:
        print("! destructive changes allowed by --allow-destroy")
        return 0
    print("✗ destructive changes need review (critical ones cannot be overridden by a flag)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
