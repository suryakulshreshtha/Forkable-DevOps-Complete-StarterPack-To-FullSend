#!/usr/bin/env python3
"""Send steady traffic to FullSend so dashboards and alerts have something to show.

Usage (same on every OS):
  python phases/06-reliability/load_gen.py http://127.0.0.1:8000 --seconds 120 --workers 4

Mostly reads, some writes, roughly like a real API. Standard library only.
Point it only at systems you own.
"""

from __future__ import annotations

import argparse
import json
import random
import threading
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field

SERVICES = ["checkout-api", "search-api", "payments-api", "web"]


@dataclass
class Results:
    statuses: Counter[int] = field(default_factory=Counter)
    latencies: list[float] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def record(self, status: int, seconds: float) -> None:
        with self.lock:
            self.statuses[status] += 1
            self.latencies.append(seconds)


def one_request(base: str, rng: random.Random) -> tuple[int, float]:
    roll = rng.random()
    if roll < 0.15:
        body = {
            "service": rng.choice(SERVICES),
            "version": f"1.{rng.randint(0, 9)}.{rng.randint(0, 20)}",
            "environment": rng.choice(["dev", "staging", "production"]),
            "status": "failed" if rng.random() < 0.1 else "succeeded",
        }
        req = urllib.request.Request(
            f"{base}/api/v1/deployments",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
    else:
        path = rng.choice(["/api/v1/deployments", "/api/v1/dora", "/api/v1/info"])
        req = urllib.request.Request(f"{base}{path}")
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=5) as res:  # nosec B310  # operator-given URL
            status = res.status
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.close()  # Python 3.14 warns about an error response left open
    except (urllib.error.URLError, OSError):
        status = 0  # connection failure
    return status, time.perf_counter() - start


def run(base: str, seconds: float, workers: int, seed: int = 0) -> Results:
    results = Results()
    deadline = time.monotonic() + seconds

    def worker(n: int) -> None:
        rng = random.Random(seed + n)  # noqa: S311 - traffic shaping, not security
        while time.monotonic() < deadline:
            results.record(*one_request(base.rstrip("/"), rng))

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate traffic against FullSend")
    parser.add_argument("base_url")
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)
    results = run(args.base_url, args.seconds, args.workers)
    total = sum(results.statuses.values())
    errors = sum(n for code, n in results.statuses.items() if code == 0 or code >= 500)
    ordered = sorted(results.latencies)
    p95 = ordered[int(0.95 * (len(ordered) - 1))] if ordered else 0.0
    print(
        f"requests {total}  rate {total / args.seconds:.1f}/s  errors {errors} "
        f"({errors / total if total else 0:.2%})  p95 {p95 * 1000:.1f} ms"
    )
    print("by status:", dict(sorted(results.statuses.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
