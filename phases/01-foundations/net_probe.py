#!/usr/bin/env python3
"""Walk the network path to a service one layer at a time: DNS -> TCP -> TLS -> HTTP.

Usage:
  python phases/01-foundations/net_probe.py example.org            # HTTPS on 443
  python phases/01-foundations/net_probe.py 127.0.0.1 --port 8000 --http

When "the site is down", the useful question is *which layer* fails. Name
resolution, a closed port, an expired certificate and a 500 error are four very
different problems with four different owners.
"""

from __future__ import annotations

import argparse
import socket
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class Step:
    layer: str
    ok: bool
    detail: str
    ms: float


def resolve(host: str, port: int) -> Step:
    start = time.perf_counter()
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        return Step("DNS", False, f"cannot resolve {host}: {exc}", _ms(start))
    addresses = sorted({info[4][0] for info in infos})
    return Step("DNS", True, ", ".join(addresses), _ms(start))


def connect(host: str, port: int, timeout: float) -> Step:
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except OSError as exc:
        return Step("TCP", False, f"port {port} unreachable: {exc}", _ms(start))
    return Step("TCP", True, f"port {port} open", _ms(start))


def days_until(not_after: str, now: datetime | None = None) -> int:
    """Days until a certificate's notAfter date, as Python's ssl module formats it."""
    expires = datetime.fromtimestamp(ssl.cert_time_to_seconds(not_after), UTC)
    return (expires - (now or datetime.now(UTC))).days


def tls(host: str, port: int, timeout: float) -> Step:
    start = time.perf_counter()
    context = ssl.create_default_context()
    try:
        with (
            socket.create_connection((host, port), timeout=timeout) as raw,
            context.wrap_socket(raw, server_hostname=host) as conn,
        ):
            cert = conn.getpeercert() or {}
            version = conn.version()
    except (OSError, ssl.SSLError) as exc:
        return Step("TLS", False, f"handshake failed: {exc}", _ms(start))
    left = days_until(str(cert.get("notAfter")))
    ok = left > 14
    return Step("TLS", ok, f"{version}, certificate expires in {left} days", _ms(start))


def http(url: str, timeout: float) -> Step:
    start = time.perf_counter()
    request = urllib.request.Request(url, headers={"User-Agent": "net-probe/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as res:  # nosec B310
            status = res.status
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.close()  # Python 3.14 warns about an error response left open
    except (urllib.error.URLError, OSError) as exc:
        return Step("HTTP", False, f"request failed: {exc}", _ms(start))
    return Step("HTTP", status < 500, f"{url} -> {status}", _ms(start))


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 1)


def probe(host: str, port: int, use_tls: bool, path: str, timeout: float) -> list[Step]:
    steps = [resolve(host, port)]
    if not steps[-1].ok:
        return steps
    steps.append(connect(host, port, timeout))
    if not steps[-1].ok:
        return steps
    if use_tls:
        steps.append(tls(host, port, timeout))
    scheme = "https" if use_tls else "http"
    steps.append(http(f"{scheme}://{host}:{port}{path}", timeout))
    return steps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("host")
    parser.add_argument("--port", type=int, default=443)
    parser.add_argument("--http", action="store_true", help="plain HTTP instead of HTTPS")
    parser.add_argument("--path", default="/")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args(argv)
    steps = probe(args.host, args.port, not args.http, args.path, args.timeout)
    for step in steps:
        mark = "✓" if step.ok else "✗"
        print(f"{mark} {step.layer:<5} {step.ms:>8.1f} ms  {step.detail}")
    return 0 if all(s.ok for s in steps) else 1


if __name__ == "__main__":
    raise SystemExit(main())
