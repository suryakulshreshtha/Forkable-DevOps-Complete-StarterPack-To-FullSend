# syntax=docker/dockerfile:1
#
# Two stages: "build" turns the project into wheels, "runtime" installs only
# those wheels into a clean image. Build tools never reach production.
#
# Base image: the Docker Official Image for Python, Debian 13 (trixie), slim variant.
# For production, pin the base image by digest too (python:3.14-slim-trixie@sha256:...)
# and let Dependabot raise PRs when it changes.

ARG PYTHON_VERSION=3.14

FROM python:${PYTHON_VERSION}-slim-trixie AS build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /src
# Copy dependency metadata first so this layer is cached until pyproject.toml changes.
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
RUN python -m pip wheel --wheel-dir /wheels .

FROM python:${PYTHON_VERSION}-slim-trixie AS runtime
ARG GIT_SHA=unknown
ARG VERSION=1.0.0
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    APP_GIT_SHA=${GIT_SHA} \
    APP_VERSION=${VERSION}

# A fixed, unprivileged user. Kubernetes can verify "runAsNonRoot" against this UID.
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

COPY --from=build /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels fullsend \
 && rm -rf /wheels

USER 10001:10001
EXPOSE 8000

# Docker-level health check (Kubernetes uses its own probes instead).
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz/live', timeout=2).status == 200 else 1)"]

ENTRYPOINT ["python", "-m", "fullsend"]
