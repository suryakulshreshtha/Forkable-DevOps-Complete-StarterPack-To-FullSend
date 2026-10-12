"""Settings read from environment variables (the twelve-factor way).

Every value has a safe default, so the app runs with zero configuration on a
laptop, and every value can be overridden in a container or Kubernetes pod.

| Variable          | Default     | Meaning                                              |
|-------------------|-------------|------------------------------------------------------|
| APP_ENV           | dev         | Environment name shown in /api/v1/info and metrics   |
| APP_VERSION       | package ver | Version string (CI sets it to the release)           |
| APP_GIT_SHA       | unknown     | Commit the image was built from (CI sets it)         |
| HOST              | 127.0.0.1   | Interface to listen on (containers set 0.0.0.0)      |
| PORT              | 8000        | Port to listen on                                    |
| LOG_LEVEL         | INFO        | DEBUG, INFO, WARNING, ERROR or CRITICAL              |
| CHAOS_ERROR_RATE  | 0           | Share of /api requests to fail with 503 (0 to 1)     |
| CHAOS_LATENCY_MS  | 0           | Extra delay added to every /api request              |
| MAX_DEPLOYMENTS   | 10000       | Oldest deployments are dropped beyond this           |
| OTEL_ENABLED      | false       | Turn on OpenTelemetry tracing                        |
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from fullsend import __version__

VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
TRUE_WORDS = frozenset({"1", "true", "yes", "on"})
FALSE_WORDS = frozenset({"0", "false", "no", "off", ""})


class SettingsError(ValueError):
    """Raised when an environment variable holds an invalid value."""


def _number(env: Mapping[str, str], name: str, default: float, lo: float, hi: float) -> float:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise SettingsError(f"{name} must be a number, got {raw!r}") from exc
    if not lo <= value <= hi:
        raise SettingsError(f"{name} must be between {lo:g} and {hi:g}, got {value:g}")
    return value


def _whole(env: Mapping[str, str], name: str, default: int, lo: int, hi: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise SettingsError(f"{name} must be a whole number, got {raw!r}") from exc
    if not lo <= value <= hi:
        raise SettingsError(f"{name} must be between {lo} and {hi}, got {value}")
    return value


def _flag(env: Mapping[str, str], name: str) -> bool:
    raw = env.get(name, "").strip().lower()
    if raw in TRUE_WORDS:
        return True
    if raw in FALSE_WORDS:
        return False
    raise SettingsError(f"{name} must be true or false, got {raw!r}")


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings. Build one from the environment with :meth:`Settings.from_env`."""

    app_name: str = "fullsend"
    environment: str = "dev"
    version: str = __version__
    git_sha: str = "unknown"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    chaos_error_rate: float = 0.0
    chaos_latency_ms: int = 0
    max_deployments: int = 10_000
    otel_enabled: bool = False

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if environ is None else environ
        log_level = env.get("LOG_LEVEL", "INFO").strip().upper() or "INFO"
        if log_level not in VALID_LOG_LEVELS:
            raise SettingsError(
                f"LOG_LEVEL must be one of {sorted(VALID_LOG_LEVELS)}, got {log_level!r}"
            )
        return cls(
            environment=env.get("APP_ENV", "").strip() or "dev",
            version=env.get("APP_VERSION", "").strip() or __version__,
            git_sha=env.get("APP_GIT_SHA", "").strip() or "unknown",
            host=env.get("HOST", "").strip() or "127.0.0.1",
            port=_whole(env, "PORT", 8000, 1, 65535),
            log_level=log_level,
            chaos_error_rate=_number(env, "CHAOS_ERROR_RATE", 0.0, 0.0, 1.0),
            chaos_latency_ms=_whole(env, "CHAOS_LATENCY_MS", 0, 0, 30_000),
            max_deployments=_whole(env, "MAX_DEPLOYMENTS", 10_000, 1, 1_000_000),
            otel_enabled=_flag(env, "OTEL_ENABLED"),
        )
