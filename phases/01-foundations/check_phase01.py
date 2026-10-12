"""Self-check for Phase 1. Run: python -m pytest phases/01-foundations"""

from __future__ import annotations

import http.server
import socket
import threading
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import dsa_warmups as dsa
import log_report
import net_probe
import pytest
import sysinfo

HERE = Path(__file__).parent

# ------------------------------------------------------------------ sysinfo


def test_sysinfo_report_has_the_basics() -> None:
    data = sysinfo.report()
    assert data["cpu_count"] >= 1
    assert 0 <= data["disk"]["used_pct"] <= 100


def test_sysinfo_warns_on_full_disk_and_overload() -> None:
    data = {"disk": {"path": "/", "used_pct": 95.0}, "load_average": [9.0, 1, 1], "cpu_count": 4}
    assert len(sysinfo.warnings(data)) == 2


# ------------------------------------------------------------------ log_report


def test_log_report_numbers_for_the_sample_log() -> None:
    with open(HERE / "sample-access.log", encoding="utf-8") as handle:
        report = log_report.analyse(handle)
    assert report.total == 60
    assert report.unparsed == 1
    assert report.status_classes == {"2xx": 55, "4xx": 3, "5xx": 2}
    assert report.errors_by_path.most_common(1) == [("/api/v1/dora", 2)]
    assert report.clients.most_common(1)[0][0] == "203.0.113.99"
    # Query strings are stripped, so /api/v1/deployments?limit=10 counts as /api/v1/deployments.
    assert not any("?" in p for p in report.paths)


@pytest.mark.parametrize(
    ("values", "pct", "expected"),
    [([1, 2, 3, 4], 50, 2), ([1, 2, 3, 4], 100, 4), ([5], 95, 5), ([], 50, None)],
)
def test_nearest_rank_percentile(values: list[float], pct: float, expected: float | None) -> None:
    assert log_report.percentile(values, pct) == expected


# ------------------------------------------------------------------ net_probe


@pytest.fixture
def local_http() -> Iterator[int]:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200 if self.path == "/" else 500)
            self.end_headers()

        def log_message(self, *args: object) -> None:
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_address[1]
    server.shutdown()
    server.server_close()


def test_probe_walks_dns_tcp_http(local_http: int) -> None:
    steps = net_probe.probe("127.0.0.1", local_http, use_tls=False, path="/", timeout=2)
    assert [s.layer for s in steps] == ["DNS", "TCP", "HTTP"]
    assert all(s.ok for s in steps)


def test_probe_flags_server_errors(local_http: int) -> None:
    steps = net_probe.probe("127.0.0.1", local_http, use_tls=False, path="/boom", timeout=2)
    assert steps[-1].ok is False
    assert "500" in steps[-1].detail


def test_probe_stops_at_the_first_broken_layer() -> None:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        closed_port = s.getsockname()[1]
    steps = net_probe.probe("127.0.0.1", closed_port, use_tls=False, path="/", timeout=1)
    assert [s.layer for s in steps] == ["DNS", "TCP"]
    assert steps[-1].ok is False


def test_unresolvable_names_fail_at_dns() -> None:
    steps = net_probe.probe("name.invalid", 443, use_tls=True, path="/", timeout=1)
    assert [(s.layer, s.ok) for s in steps] == [("DNS", False)]


def test_certificate_expiry_math() -> None:
    now = datetime(2026, 10, 12, tzinfo=UTC)
    assert net_probe.days_until("Nov  1 00:00:00 2026 GMT", now=now) == 20


# ------------------------------------------------------------------ DSA warm-ups


def test_top_k_clients() -> None:
    ips = ["a", "b", "a", "c", "b", "a", "d", "c"]
    assert dsa.top_k_clients(ips, 2) == [("a", 3), ("b", 2)]


def test_sliding_window_limiter() -> None:
    limiter = dsa.SlidingWindowLimiter(limit=2, window=10)
    assert [limiter.allow(t) for t in (0, 1, 2)] == [True, True, False]
    assert limiter.allow(10.5) is True  # the hit at t=0 has left the window


def test_lru_cache_evicts_the_least_recently_used() -> None:
    cache = dsa.LRUCache(capacity=2)
    cache.put("a", "1")
    cache.put("b", "2")
    assert cache.get("a") == "1"  # "a" is now fresh
    cache.put("c", "3")  # evicts "b"
    assert cache.get("b") is None
    assert (cache.get("a"), cache.get("c")) == ("1", "3")


def test_merge_windows() -> None:
    assert dsa.merge_windows([(5, 7), (1, 3), (2, 4), (7, 9), (11, 12)]) == [
        (1, 4),
        (5, 9),
        (11, 12),
    ]


def test_deploy_order_respects_dependencies() -> None:
    order = dsa.deploy_order({"api": {"db", "cache"}, "web": {"api"}, "db": set(), "cache": set()})
    assert order == ["cache", "db", "api", "web"]


def test_deploy_order_rejects_cycles() -> None:
    with pytest.raises(ValueError, match="cycle"):
        dsa.deploy_order({"a": {"b"}, "b": {"a"}})
