"""Metrics, structured logs and optional tracing.

* Metrics: Prometheus client library, served at /metrics.
* Logs: one JSON object per line on stdout, so any log collector can parse them.
* Tracing: OpenTelemetry, only when OTEL_ENABLED=true and the optional
  'observability' extra is installed.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram
from prometheus_client.gc_collector import GCCollector
from prometheus_client.platform_collector import PlatformCollector
from prometheus_client.process_collector import ProcessCollector

from fullsend.config import Settings

# Buckets in seconds, tuned for a fast API: most requests should land under 100 ms.
LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)


class Metrics:
    """Every metric lives on its own registry, so tests can build many apps safely."""

    def __init__(self, settings: Settings) -> None:
        self.registry = CollectorRegistry()
        # The library's default collectors live on its global registry. Fresh
        # ones bound to this registry keep process and runtime metrics exposed.
        ProcessCollector(registry=self.registry)
        PlatformCollector(registry=self.registry)
        GCCollector(registry=self.registry)

        self.requests = Counter(
            "http_requests_total",
            "HTTP requests handled, by method, route template and status code.",
            ["method", "route", "status"],
            registry=self.registry,
        )
        self.latency = Histogram(
            "http_request_duration_seconds",
            "Time spent handling HTTP requests.",
            ["method", "route"],
            buckets=LATENCY_BUCKETS,
            registry=self.registry,
        )
        self.deployments = Counter(
            "fullsend_deployments_recorded_total",
            "Deployments recorded through the API.",
            ["environment", "status"],
            registry=self.registry,
        )
        self.build_info = Gauge(
            "fullsend_build_info",
            "Always 1. Labels describe the running build.",
            ["version", "git_sha", "environment"],
            registry=self.registry,
        )
        self.build_info.labels(settings.version, settings.git_sha, settings.environment).set(1)


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("fullsend")
    if not any(isinstance(h.formatter, JsonFormatter) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def setup_tracing(app: FastAPI, settings: Settings, logger: logging.Logger) -> bool:
    """Instrument the app with OpenTelemetry. Returns True when tracing is active.

    Spans go to an OTLP/HTTP endpoint when OTEL_EXPORTER_OTLP_ENDPOINT is set
    (the exporter reads that variable itself), otherwise to the console.
    """
    if not settings.otel_enabled:
        return False
    try:
        import os

        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
            SpanExporter,
        )
    except ImportError:
        logger.warning(
            "tracing requested but the 'observability' extra is not installed",
            extra={"fields": {"hint": "pip install -e '.[observability]'"}},
        )
        return False

    resource = Resource.create(
        {
            "service.name": settings.app_name,
            "service.version": settings.version,
            "deployment.environment.name": settings.environment,
        }
    )
    provider = TracerProvider(resource=resource)
    exporter: SpanExporter
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter()
    else:
        exporter = ConsoleSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    app.state.tracer_provider = provider  # kept so shutdown can flush pending spans
    logger.info("tracing enabled", extra={"fields": {"exporter": type(exporter).__name__}})
    return True
