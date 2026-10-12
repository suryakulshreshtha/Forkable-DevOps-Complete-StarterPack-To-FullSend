#!/usr/bin/env python3
"""Summarise an Nginx access log: traffic, errors, slow paths and busy clients.

Usage:
  python phases/01-foundations/log_report.py phases/01-foundations/sample-access.log
  docker compose -f phases/01-foundations/nginx-lab/compose.yaml logs nginx --no-log-prefix \
      | python phases/01-foundations/log_report.py -

Expected line format: Nginx's "combined" format followed by $request_time, which
is what nginx-lab/default.conf writes:
  1.2.3.4 - - [12/Oct/2026:10:00:01 +0000] "GET /api/v1/info HTTP/1.1" 200 93 "-" "curl/8.0" 0.004
"""

from __future__ import annotations

import math
import re
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

LINE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] "(?P<method>[A-Z]+) (?P<path>\S+) [^"]*" '
    r'(?P<status>\d{3}) (?P<bytes>\d+|-) "[^"]*" "[^"]*"(?: (?P<rt>\d+\.\d+))?'
)


@dataclass
class Report:
    total: int = 0
    unparsed: int = 0
    status_classes: Counter[str] = field(default_factory=Counter)
    paths: Counter[str] = field(default_factory=Counter)
    errors_by_path: Counter[str] = field(default_factory=Counter)
    clients: Counter[str] = field(default_factory=Counter)
    latencies: list[float] = field(default_factory=list)

    @property
    def error_rate(self) -> float:
        return self.status_classes["5xx"] / self.total if self.total else 0.0


def percentile(values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile: the smallest value with at least pct% of values at or below it."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def analyse(lines: Iterable[str]) -> Report:
    report = Report()
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        match = LINE.match(line)
        if not match:
            report.unparsed += 1
            continue
        report.total += 1
        status = match["status"]
        path = match["path"].split("?", 1)[0]
        report.status_classes[f"{status[0]}xx"] += 1
        report.paths[path] += 1
        report.clients[match["ip"]] += 1
        if status.startswith("5"):
            report.errors_by_path[path] += 1
        if match["rt"]:
            report.latencies.append(float(match["rt"]))
    return report


def render(report: Report, top: int = 5) -> str:
    out = [
        f"requests      {report.total}  (unparsed lines: {report.unparsed})",
        "status        " + "  ".join(f"{k}={v}" for k, v in sorted(report.status_classes.items())),
        f"error rate    {report.error_rate:.2%}  (5xx / all)",
    ]
    if report.latencies:
        p50, p95, p99 = (percentile(report.latencies, p) for p in (50, 95, 99))
        out.append(f"latency       p50={p50:.3f}s  p95={p95:.3f}s  p99={p99:.3f}s")
    out.append("top paths     " + ", ".join(f"{p} ({n})" for p, n in report.paths.most_common(top)))
    if report.errors_by_path:
        out.append(
            "5xx by path   "
            + ", ".join(f"{p} ({n})" for p, n in report.errors_by_path.most_common(top))
        )
    out.append(
        "top clients   " + ", ".join(f"{c} ({n})" for c, n in report.clients.most_common(top))
    )
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "-":
        report = analyse(sys.stdin)
    else:
        with open(argv[0], encoding="utf-8") as handle:
            report = analyse(handle)
    print(render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
