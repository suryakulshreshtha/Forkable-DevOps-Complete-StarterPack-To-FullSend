"""Shared fixtures for the unit and API test layers."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from fullsend.config import Settings
from fullsend.main import create_app
from fullsend.store import DeploymentStore


class FakeClock:
    """A clock the test controls, so time-based results are exact and never flaky."""

    def __init__(self, start: datetime | None = None) -> None:
        self.now = start or datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs: float) -> None:
        self.now += timedelta(**kwargs)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def store(clock: FakeClock) -> DeploymentStore:
    return DeploymentStore(capacity=100, clock=clock)


@pytest.fixture
def settings() -> Settings:
    return Settings(environment="test", version="9.9.9", git_sha="abc1234")


@pytest.fixture
def client(settings: Settings, store: DeploymentStore) -> Iterator[TestClient]:
    with TestClient(create_app(settings, store)) as test_client:
        yield test_client
