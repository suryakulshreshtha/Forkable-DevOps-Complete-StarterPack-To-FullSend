"""API tests: real HTTP requests against the app, in-process (no network, no server)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import FakeClock

VALID = {"service": "checkout-api", "version": "1.4.2", "environment": "production"}


def test_health_endpoints(client: TestClient) -> None:
    assert client.get("/healthz/live").json() == {"status": "ok"}
    ready = client.get("/healthz/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready", "deployments_stored": 0}


def test_info_reports_build_details(client: TestClient) -> None:
    assert client.get("/api/v1/info").json() == {
        "app": "fullsend",
        "version": "9.9.9",
        "git_sha": "abc1234",
        "environment": "test",
    }


def test_create_then_read_deployment(client: TestClient) -> None:
    created = client.post("/api/v1/deployments", json=VALID)
    assert created.status_code == 201
    body = created.json()
    assert body["id"] == 1
    assert body["status"] == "succeeded"  # the default outcome
    fetched = client.get(f"/api/v1/deployments/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


@pytest.mark.parametrize(
    "bad",
    [
        {**VALID, "service": "Checkout API"},  # capitals and spaces are not allowed
        {**VALID, "service": ""},
        {**VALID, "environment": "moon"},
        {**VALID, "status": "maybe"},
        {**VALID, "commit_sha": "XYZ"},
        {**VALID, "unexpected": "field"},  # extra fields are rejected, not silently dropped
        {"service": "api"},  # required fields missing
    ],
)
def test_validation_rejects_bad_input(client: TestClient, bad: dict[str, str]) -> None:
    assert client.post("/api/v1/deployments", json=bad).status_code == 422


def test_list_filters_by_environment_and_limits(client: TestClient) -> None:
    for env in ("dev", "staging", "production"):
        client.post("/api/v1/deployments", json={**VALID, "environment": env})
    assert len(client.get("/api/v1/deployments").json()) == 3
    prod = client.get("/api/v1/deployments", params={"environment": "production"}).json()
    assert [d["environment"] for d in prod] == ["production"]
    assert len(client.get("/api/v1/deployments", params={"limit": 2}).json()) == 2
    assert client.get("/api/v1/deployments", params={"limit": 0}).status_code == 422


def test_patch_status_moves_dora_change_fail_rate(client: TestClient, clock: FakeClock) -> None:
    first = client.post("/api/v1/deployments", json=VALID).json()
    clock.advance(hours=2)
    client.post("/api/v1/deployments", json=VALID)
    patched = client.patch(f"/api/v1/deployments/{first['id']}", json={"status": "rolled_back"})
    assert patched.status_code == 200
    assert patched.json()["status"] == "rolled_back"
    report = client.get("/api/v1/dora", params={"window_days": 7}).json()
    assert report["window_days"] == 7
    assert report["environments"]["production"] == {
        "deployments": 2,
        "deployment_frequency_per_day": round(2 / 7, 3),
        "needed_intervention": 1,
        "change_fail_rate": 0.5,
        "recovery_time_median_hours": 2.0,
    }


def test_dora_window_is_validated(client: TestClient) -> None:
    assert client.get("/api/v1/dora", params={"window_days": 0}).status_code == 422
    assert client.get("/api/v1/dora", params={"window_days": 366}).status_code == 422


def test_missing_deployment_is_404(client: TestClient) -> None:
    assert client.get("/api/v1/deployments/42").status_code == 404
    assert client.patch("/api/v1/deployments/42", json={"status": "failed"}).status_code == 404


def test_request_id_is_echoed_or_generated(client: TestClient) -> None:
    echoed = client.get("/healthz/live", headers={"X-Request-ID": "trace-me"})
    assert echoed.headers["X-Request-ID"] == "trace-me"
    assert len(client.get("/healthz/live").headers["X-Request-ID"]) == 32


def test_ui_is_served_with_strict_security_headers(client: TestClient) -> None:
    page = client.get("/")
    assert page.status_code == 200
    assert "FullSend Deploy Log" in page.text
    assert "default-src 'self'" in page.headers["Content-Security-Policy"]
    assert page.headers["X-Content-Type-Options"] == "nosniff"
    js = client.get("/static/app.js")
    assert js.status_code == 200
    assert "Content-Security-Policy" in js.headers
    # The interactive API docs load assets from a CDN, so they must not get the strict policy.
    assert "Content-Security-Policy" not in client.get("/docs").headers
