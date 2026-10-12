#!/usr/bin/env python3
"""Estimate two DORA throughput metrics from git history alone.

Usage (run inside any repository that tags its releases):
  python phases/04-cicd/dora_from_git.py [--pattern "v*"] [--days 90]

Assumption, stated loudly: one tag = one production deployment. If your team
deploys without tagging, measure from your deploy tool instead.

* Deployment frequency: tags per week over the window.
* Change lead time: for each tag, the time from every commit it shipped to the
  tag itself; the report gives the median and the 90th percentile.

Instability metrics (change fail rate, rework rate, recovery time) need incident
data that git does not have; FullSend's /api/v1/dora endpoint covers change fail rate.
"""

from __future__ import annotations

import argparse
import math
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Release:
    tag: str
    timestamp: int
    lead_times_h: list[float]


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


def releases(repo: Path, pattern: str) -> list[Release]:
    lines = git(
        repo,
        "for-each-ref",
        "--sort=creatordate",
        "--format=%(refname:short)|%(creatordate:unix)",
        f"refs/tags/{pattern}",
    ).splitlines()
    found: list[Release] = []
    previous: str | None = None
    for line in lines:
        tag, stamp = line.rsplit("|", 1)
        span = f"{previous}..{tag}" if previous else tag
        commit_times = [int(t) for t in git(repo, "log", "--format=%ct", span).split()]
        lead = [(int(stamp) - t) / 3600 for t in commit_times]
        found.append(Release(tag, int(stamp), lead))
        previous = tag
    return found


def p90(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.9 * len(ordered)) - 1)]


def summarise(found: list[Release], days: int, now: float | None = None) -> dict[str, float | int]:
    now = now or time.time()
    recent = [r for r in found if r.timestamp >= now - days * 86400]
    leads = [h for r in recent for h in r.lead_times_h]
    return {
        "deployments": len(recent),
        "per_week": round(len(recent) / (days / 7), 2),
        "lead_time_median_h": round(statistics.median(leads), 1) if leads else 0.0,
        "lead_time_p90_h": round(p90(leads), 1) if leads else 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DORA throughput from git tags")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--pattern", default="v*")
    parser.add_argument("--days", type=int, default=90)
    args = parser.parse_args(argv)
    summary = summarise(releases(Path(args.repo), args.pattern), args.days)
    print(f"window                 last {args.days} days (one tag = one deployment)")
    print(f"deployments            {summary['deployments']}")
    print(f"deployment frequency   {summary['per_week']} per week")
    print(
        f"change lead time       median {summary['lead_time_median_h']} h, "
        f"p90 {summary['lead_time_p90_h']} h"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
