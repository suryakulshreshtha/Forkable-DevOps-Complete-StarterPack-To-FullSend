"""The FastAPI application.

Run it locally with:   python tasks.py serve
Or with uvicorn:       uvicorn fullsend.main:app
Tests build isolated copies with create_app(...).
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from importlib import resources
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app
from starlette.routing import Match
from starlette.types import Scope

from fullsend.config import Settings
from fullsend.models import (
    Deployment,
    DeploymentIn,
    DoraReport,
    Environment,
    Info,
    StatusUpdate,
)
from fullsend.observability import Metrics, configure_logging, setup_tracing
from fullsend.store import DeploymentStore

STATIC_DIR = resources.files("fullsend") / "static"
REQUEST_ID_HEADER = "X-Request-ID"
QUIET_ROUTES = frozenset({"/metrics", "/healthz/live", "/healthz/ready"})

# The built-in web page may only load scripts, styles and data from this same origin.
UI_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    ),
}
COMMON_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


def _route_template(request: Request, original_scope: Scope) -> str:
    """The matched route pattern, e.g. '/api/v1/deployments/{deployment_id}'.

    Labelling metrics with raw paths would create one time series per id and
    overload Prometheus (a high-cardinality problem); templates are bounded.

    Two cases need the routes matched here:
    * chaos answers a request *before* routing runs, so there is no route yet;
      matching keeps those failures under their real route, where error-rate
      graphs and SLO alerts can see them;
    * mounted apps (/static, /metrics) do not record a route. ``original_scope``
      is a copy taken before routing, because routing rewrites the path fields.
    """
    route = request.scope.get("route")
    if route is None:
        for candidate in request.app.router.routes:
            match, _ = candidate.matches(original_scope)
            if match is Match.FULL:
                route = candidate
                break
    path = getattr(route, "path", None)
    if isinstance(path, str) and path:
        return path
    return "unmatched"


def create_app(
    settings: Settings | None = None,
    store: DeploymentStore | None = None,
    rng: random.Random | None = None,
) -> FastAPI:
    if settings is None:
        settings = Settings.from_env()
    # `is None`, not `or`: an empty store has len() == 0, which Python treats as false.
    if store is None:
        store = DeploymentStore(capacity=settings.max_deployments)
    chaos = rng if rng is not None else random.Random()  # noqa: S311 - fault injection, not security
    metrics = Metrics(settings)
    logger = logging.getLogger("fullsend")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.ready = True
        logger.info("starting", extra={"fields": {"version": settings.version}})
        yield
        # Uvicorn reaches this point on SIGTERM after it has stopped accepting new
        # connections and let in-flight requests finish (see __main__.py).
        app.state.ready = False
        logger.info("stopping", extra={"fields": {"stored": len(store)}})
        provider = getattr(app.state, "tracer_provider", None)
        if provider is not None:
            provider.shutdown()  # flush spans that are still buffered

    app = FastAPI(
        title="FullSend Deploy Log",
        version=settings.version,
        description=(
            "Practice service for the Forkable DevOps StarterPack: records deployments "
            "and reports DORA-style delivery metrics."
        ),
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.store = store
    app.state.metrics = metrics

    @app.middleware("http")
    async def observe(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        original_scope = dict(request.scope)
        started = time.perf_counter()
        response = await _with_chaos(request, call_next)
        elapsed = time.perf_counter() - started
        route = _route_template(request, original_scope)
        if not route.startswith("/metrics"):
            metrics.requests.labels(request.method, route, str(response.status_code)).inc()
            metrics.latency.labels(request.method, route).observe(elapsed)
        response.headers[REQUEST_ID_HEADER] = request_id
        for key, value in COMMON_SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        if route in ("/", "/static"):
            for key, value in UI_SECURITY_HEADERS.items():
                response.headers.setdefault(key, value)
        if route not in QUIET_ROUTES:
            logger.info(
                "request",
                extra={
                    "fields": {
                        "request_id": request_id,
                        "method": request.method,
                        "route": route,
                        "status": response.status_code,
                        "duration_ms": round(elapsed * 1000, 2),
                    }
                },
            )
        return response

    async def _with_chaos(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Reliability-lab switch: slow down or fail a share of /api requests.

        Health probes and metrics are never affected, so Kubernetes keeps the
        pod running and Prometheus keeps scraping while the API misbehaves.
        """
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        if settings.chaos_latency_ms:
            await asyncio.sleep(settings.chaos_latency_ms / 1000)
        if settings.chaos_error_rate and chaos.random() < settings.chaos_error_rate:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "chaos: injected failure (CHAOS_ERROR_RATE is set)"},
            )
        return await call_next(request)

    # ------------------------------------------------------------ health
    @app.get("/healthz/live", tags=["health"], summary="Liveness: the process is running")
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/healthz/ready", tags=["health"], summary="Readiness: ready for traffic")
    def ready(request: Request) -> JSONResponse:
        if not getattr(request.app.state, "ready", False):
            return JSONResponse({"status": "not ready"}, status_code=503)
        return JSONResponse({"status": "ready", "deployments_stored": len(store)})

    # ------------------------------------------------------------ API
    @app.get("/api/v1/info", tags=["info"], response_model=Info)
    def info() -> Info:
        return Info(
            app=settings.app_name,
            version=settings.version,
            git_sha=settings.git_sha,
            environment=settings.environment,
        )

    @app.post(
        "/api/v1/deployments",
        tags=["deployments"],
        status_code=status.HTTP_201_CREATED,
        response_model=Deployment,
    )
    def record_deployment(payload: DeploymentIn) -> Deployment:
        deployment = store.add(payload)
        metrics.deployments.labels(deployment.environment.value, deployment.status.value).inc()
        return deployment

    @app.get("/api/v1/deployments", tags=["deployments"], response_model=list[Deployment])
    def list_deployments(
        environment: Environment | None = None,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> list[Deployment]:
        return store.list(environment=environment, limit=limit)

    @app.get("/api/v1/deployments/{deployment_id}", tags=["deployments"], response_model=Deployment)
    def get_deployment(deployment_id: int) -> Deployment:
        found = store.get(deployment_id)
        if found is None:
            raise HTTPException(status_code=404, detail="deployment not found")
        return found

    @app.patch(
        "/api/v1/deployments/{deployment_id}", tags=["deployments"], response_model=Deployment
    )
    def update_deployment(deployment_id: int, update: StatusUpdate) -> Deployment:
        updated = store.update_status(deployment_id, update.status)
        if updated is None:
            raise HTTPException(status_code=404, detail="deployment not found")
        return updated

    @app.get("/api/v1/dora", tags=["deployments"], response_model=DoraReport)
    def dora(window_days: Annotated[int, Query(ge=1, le=365)] = 30) -> DoraReport:
        return store.dora(window_days)

    # ------------------------------------------------------------ UI and metrics
    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(str(STATIC_DIR / "index.html"), media_type="text/html")

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.mount("/metrics", make_asgi_app(registry=metrics.registry))

    setup_tracing(app, settings, logger)
    return app


def _default_app() -> FastAPI:
    settings = Settings.from_env()
    configure_logging(logging.getLevelNamesMapping()[settings.log_level])
    return create_app(settings)


# Module-level app for `uvicorn fullsend.main:app` and `python -m fullsend`.
app = _default_app()
