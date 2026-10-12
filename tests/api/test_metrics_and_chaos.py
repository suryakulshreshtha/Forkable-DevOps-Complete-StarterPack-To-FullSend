"""Metrics and chaos (fault injection), checked through the HTTP API."""

from __future__ import annotations

import random

from fastapi.testclient import TestClient

from fullsend.config import Settings
from fullsend.main import create_app
from fullsend.store import DeploymentStore

VALID = {"service": "api", "version": "1.0.0", "environment": "staging"}


def metric_lines(client: TestClient, prefix: str) -> list[str]:
    text = client.get("/metrics/").text
    return [line for line in text.splitlines() if line.startswith(prefix)]


def test_metrics_use_route_templates_not_raw_paths(client: TestClient) -> None:
    client.post("/api/v1/deployments", json=VALID)
    client.get("/api/v1/deployments/1")
    client.get("/api/v1/deployments/2")  # a 404, still the same template
    joined = "\n".join(metric_lines(client, "http_requests_total{"))
    assert 'route="/api/v1/deployments/{deployment_id}"' in joined
    assert 'route="/api/v1/deployments/1"' not in joined  # no time series per id
    assert 'status="404"' in joined


def test_unknown_paths_share_one_label(client: TestClient) -> None:
    client.get("/no/such/page")
    client.get("/another/missing/page")
    unmatched = [
        line for line in metric_lines(client, "http_requests_total{") if "unmatched" in line
    ]
    assert len(unmatched) == 1


def test_business_and_build_metrics(client: TestClient) -> None:
    client.post("/api/v1/deployments", json={**VALID, "status": "failed"})
    recorded = metric_lines(client, "fullsend_deployments_recorded_total{")
    assert any('environment="staging"' in m and 'status="failed"' in m for m in recorded)
    build = metric_lines(client, "fullsend_build_info{")
    assert build
    assert 'version="9.9.9"' in build[0]


def test_scrapes_are_not_counted_as_traffic(client: TestClient) -> None:
    client.get("/metrics/")
    client.get("/metrics/")
    assert not any("/metrics" in m for m in metric_lines(client, "http_requests_total{"))


def test_chaos_fails_api_requests_but_never_probes() -> None:
    always = Settings(chaos_error_rate=1.0)
    with TestClient(create_app(always, DeploymentStore())) as c:
        response = c.get("/api/v1/info")
        assert response.status_code == 503
        assert "chaos" in response.json()["detail"]
        assert c.get("/healthz/live").status_code == 200
        assert c.get("/healthz/ready").status_code == 200
        assert c.get("/metrics/").status_code == 200


def test_chaos_failures_are_counted_under_the_real_route() -> None:
    # Chaos answers before routing runs. The failure must still be labelled with the
    # real route template, or error-rate dashboards and SLO alerts would miss it.
    with TestClient(create_app(Settings(chaos_error_rate=1.0), DeploymentStore())) as c:
        c.get("/api/v1/deployments/7")
        lines = metric_lines(c, "http_requests_total{")
    assert any(
        'route="/api/v1/deployments/{deployment_id}"' in m and 'status="503"' in m for m in lines
    )
    assert not any("unmatched" in m for m in lines)


def test_chaos_rate_is_honoured_with_a_seeded_generator() -> None:
    app = create_app(Settings(chaos_error_rate=0.3), DeploymentStore(), rng=random.Random(42))
    with TestClient(app) as c:
        codes = [c.get("/api/v1/info").status_code for _ in range(400)]
    failure_share = codes.count(503) / len(codes)
    assert 0.2 < failure_share < 0.4


def test_chaos_latency_is_applied() -> None:
    with TestClient(create_app(Settings(chaos_latency_ms=50), DeploymentStore())) as c:
        assert c.get("/api/v1/info").status_code == 200
        buckets = metric_lines(c, "http_request_duration_seconds_bucket{")
    info = [b for b in buckets if 'route="/api/v1/info"' in b]
    # 50 ms of injected delay: nothing lands in the 25 ms bucket, the request is in the 100 ms one.
    assert any('le="0.025"' in b and b.endswith(" 0.0") for b in info)
    assert any('le="0.1"' in b and b.endswith(" 1.0") for b in info)
