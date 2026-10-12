#!/usr/bin/env python3
"""Error budgets and burn rates, worked out so you can sanity-check any alert.

Usage:
  python phases/06-reliability/slo_calc.py --slo 99.9 --window 30
  python phases/06-reliability/slo_calc.py --slo 99 --errors 250 --requests 10000

Definitions (Google SRE Workbook, "Alerting on SLOs"):
* error budget  = 1 - SLO              (99.9% -> 0.1% of requests may fail)
* burn rate     = observed error ratio / error budget
                  ("how fast, relative to the SLO, the service consumes the error budget")
* a burn rate of 1 uses exactly the whole budget over the SLO window
"""

from __future__ import annotations

import argparse
import sys

# Severity, long window (h), short window (h), burn rate: the workbook's recommended
# multiwindow, multi-burn-rate parameters (its Table 5-8, for a 30-day window).
WORKBOOK_ALERTS = [
    ("page", 1.0, 5 / 60, 14.4),
    ("page", 6.0, 0.5, 6.0),
    ("ticket", 72.0, 6.0, 1.0),
]


def error_budget(slo_pct: float) -> float:
    if not 0 < slo_pct < 100:
        raise ValueError("SLO must be between 0 and 100 percent (exclusive)")
    return round(1 - slo_pct / 100, 10)


def allowed_downtime_minutes(slo_pct: float, window_days: float) -> float:
    return error_budget(slo_pct) * window_days * 24 * 60


def burn_rate(error_ratio: float, slo_pct: float) -> float:
    return error_ratio / error_budget(slo_pct)


def days_to_exhaustion(rate: float, window_days: float) -> float:
    """Days until the whole budget is gone if this burn rate continues from a full budget."""
    return float("inf") if rate <= 0 else window_days / rate


def budget_consumed(rate: float, alert_window_h: float, window_days: float) -> float:
    """Share of the total budget used while burning at `rate` for `alert_window_h` hours."""
    return rate * alert_window_h / (window_days * 24)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SLO error budget calculator")
    parser.add_argument("--slo", type=float, default=99.0, help="target in percent, e.g. 99.9")
    parser.add_argument("--window", type=float, default=30, help="SLO window in days")
    parser.add_argument("--errors", type=int, help="failed requests observed")
    parser.add_argument("--requests", type=int, help="total requests observed")
    args = parser.parse_args(argv)

    budget = error_budget(args.slo)
    print(f"SLO {args.slo}% over {args.window:g} days")
    print(f"  error budget        {budget:.4%} of requests")
    print(f"  as pure downtime    {allowed_downtime_minutes(args.slo, args.window):.1f} minutes")
    print("\nWorkbook alert thresholds for this SLO:")
    print("  severity  long win  short win  burn  error ratio  budget used")
    for severity, long_h, short_h, rate in WORKBOOK_ALERTS:
        used = budget_consumed(rate, long_h, args.window)
        print(
            f"  {severity:<8}  {long_h:>6g} h  {short_h * 60:>6g} min  {rate:>4g}  "
            f"{rate * budget:>10.4%}  {used:>10.1%}"
        )
    if args.errors is not None and args.requests:
        ratio = args.errors / args.requests
        rate = burn_rate(ratio, args.slo)
        print(f"\nObserved error ratio {ratio:.4%} -> burn rate {rate:.2f}")
        days = days_to_exhaustion(rate, args.window)
        print(f"  a full budget would last {days:.1f} days at this rate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
