from __future__ import annotations

import logging
import sys
from typing import Any

import pytest
from fastapi import FastAPI

from fullsend import __main__ as entrypoint
from fullsend.config import Settings
from fullsend.observability import setup_tracing

LOGGER = logging.getLogger("fullsend.test")


def test_tracing_is_off_by_default() -> None:
    assert setup_tracing(FastAPI(), Settings(), LOGGER) is False


def test_tracing_turns_on_with_console_exporter(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("opentelemetry.sdk", reason="needs the 'observability' extra")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    app = FastAPI()
    assert setup_tracing(app, Settings(otel_enabled=True), LOGGER) is True
    app.state.tracer_provider.shutdown()


def test_tracing_uses_otlp_when_an_endpoint_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("opentelemetry.exporter.otlp.proto.http", reason="needs the extra")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318")
    app = FastAPI()
    assert setup_tracing(app, Settings(otel_enabled=True), LOGGER) is True
    app.state.tracer_provider.shutdown()


def test_tracing_degrades_gracefully_without_the_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "opentelemetry", None)  # makes the import fail
    assert setup_tracing(FastAPI(), Settings(otel_enabled=True), LOGGER) is False


def test_entrypoint_reads_host_port_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(entrypoint.uvicorn, "run", lambda app, **kw: captured.update(app=app, **kw))
    monkeypatch.setenv("HOST", "0.0.0.0")  # noqa: S104 - asserting the container setting
    monkeypatch.setenv("PORT", "9000")
    entrypoint.main()
    assert captured["app"] == "fullsend.main:app"
    assert (captured["host"], captured["port"]) == ("0.0.0.0", 9000)  # noqa: S104


def test_app_flushes_spans_on_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("opentelemetry.sdk", reason="needs the 'observability' extra")
    from fastapi.testclient import TestClient

    from fullsend.main import create_app

    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    app = create_app(settings=Settings(otel_enabled=True))
    provider = app.state.tracer_provider
    real_shutdown = provider.shutdown
    calls: list[int] = []
    monkeypatch.setattr(provider, "shutdown", lambda: calls.append(1))
    with TestClient(app) as client:
        client.get("/healthz/live")
    assert calls == [1]
    real_shutdown()
