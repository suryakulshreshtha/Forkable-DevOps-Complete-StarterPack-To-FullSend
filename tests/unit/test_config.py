from __future__ import annotations

import pytest

from fullsend.config import Settings, SettingsError


def test_defaults_are_safe() -> None:
    s = Settings.from_env({})
    assert s.host == "127.0.0.1"  # never listen on every interface by accident
    assert s.port == 8000
    assert s.chaos_error_rate == 0.0
    assert s.chaos_latency_ms == 0
    assert s.otel_enabled is False


def test_reads_every_variable() -> None:
    s = Settings.from_env(
        {
            "APP_ENV": "staging",
            "APP_VERSION": "2.0.0",
            "APP_GIT_SHA": "deadbee",
            "HOST": "0.0.0.0",  # noqa: S104 - value under test, not a bind
            "PORT": "9000",
            "LOG_LEVEL": "debug",
            "CHAOS_ERROR_RATE": "0.25",
            "CHAOS_LATENCY_MS": "150",
            "MAX_DEPLOYMENTS": "50",
            "OTEL_ENABLED": "true",
        }
    )
    assert (s.environment, s.version, s.git_sha, s.log_level) == (
        "staging",
        "2.0.0",
        "deadbee",
        "DEBUG",
    )
    assert (s.port, s.chaos_error_rate, s.chaos_latency_ms, s.max_deployments) == (
        9000,
        0.25,
        150,
        50,
    )
    assert s.otel_enabled is True


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"CHAOS_ERROR_RATE": "1.5"}, "between"),
        ({"CHAOS_ERROR_RATE": "lots"}, "must be a number"),
        ({"PORT": "0"}, "between"),
        ({"PORT": "eighty"}, "whole number"),
        ({"LOG_LEVEL": "LOUD"}, "LOG_LEVEL"),
        ({"OTEL_ENABLED": "maybe"}, "true or false"),
    ],
)
def test_rejects_bad_values_with_a_clear_message(env: dict[str, str], message: str) -> None:
    with pytest.raises(SettingsError, match=message):
        Settings.from_env(env)


def test_blank_values_fall_back_to_defaults() -> None:
    s = Settings.from_env({"PORT": " ", "APP_ENV": "", "OTEL_ENABLED": " "})
    assert (s.port, s.environment, s.otel_enabled) == (8000, "dev", False)
