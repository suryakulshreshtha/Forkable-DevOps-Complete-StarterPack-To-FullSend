#!/usr/bin/env python3
"""Print a short system report, the same way on macOS, Windows and Linux.

Usage: python phases/01-foundations/sysinfo.py [--json]

The first thing you do when you log in to an unfamiliar server is answer:
what is this machine, how busy is it, and is the disk full? This script answers
those with the Python standard library only.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import sys
from pathlib import Path
from typing import Any


def disk_report(path: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(path)
    return {
        "path": str(path),
        "total_gb": round(usage.total / 1e9, 1),
        "free_gb": round(usage.free / 1e9, 1),
        "used_pct": round(100 * usage.used / usage.total, 1) if usage.total else 0.0,
    }


def load_average() -> list[float] | None:
    """1, 5 and 15 minute load averages. Not available on Windows."""
    try:
        return [round(x, 2) for x in os.getloadavg()]
    except (AttributeError, OSError):
        return None


def report() -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "load_average": load_average(),
        "python": platform.python_version(),
        "disk": disk_report(Path(Path.home().anchor or "/")),  # system drive: / or C:\\
        "in_container": Path("/.dockerenv").exists(),
    }


def warnings(data: dict[str, Any]) -> list[str]:
    found = []
    if data["disk"]["used_pct"] >= 90:
        found.append(f"disk {data['disk']['path']} is {data['disk']['used_pct']}% full")
    load = data["load_average"]
    if load and data["cpu_count"] and load[0] > data["cpu_count"]:
        found.append(f"1-minute load {load[0]} is above the CPU count {data['cpu_count']}")
    return found


def main(argv: list[str]) -> int:
    data = report()
    if "--json" in argv:
        print(json.dumps(data, indent=2))
    else:
        for key, value in data.items():
            print(f"{key:<13} {value}")
    for warning in warnings(data):
        print(f"WARNING {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
