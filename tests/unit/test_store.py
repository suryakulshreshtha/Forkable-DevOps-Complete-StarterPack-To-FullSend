"""Unit tests: the store on its own, no HTTP involved. Fast and exact."""

from __future__ import annotations

import threading

import pytest

from fullsend.models import DeploymentIn, Environment, Status
from fullsend.store import DeploymentStore
from tests.conftest import FakeClock


def make(service: str = "api", env: str = "dev", status: str = "succeeded") -> DeploymentIn:
    return DeploymentIn(
        service=service, version="1.0.0", environment=Environment(env), status=Status(status)
    )


def test_add_assigns_increasing_ids_and_timestamps(
    store: DeploymentStore, clock: FakeClock
) -> None:
    first = store.add(make())
    clock.advance(minutes=5)
    second = store.add(make())
    assert (first.id, second.id) == (1, 2)
    assert second.created_at > first.created_at


def test_list_is_newest_first_and_filters_by_environment(store: DeploymentStore) -> None:
    store.add(make("api", "dev"))
    store.add(make("web", "production"))
    store.add(make("api", "production"))
    assert [d.id for d in store.list()] == [3, 2, 1]
    assert [d.id for d in store.list(environment=Environment.PRODUCTION)] == [3, 2]
    assert [d.id for d in store.list(limit=1)] == [3]


def test_capacity_drops_the_oldest_first(clock: FakeClock) -> None:
    small = DeploymentStore(capacity=2, clock=clock)
    for _ in range(3):
        small.add(make())
    assert len(small) == 2
    assert small.get(1) is None
    assert small.get(3) is not None


def test_capacity_must_be_positive() -> None:
    with pytest.raises(ValueError, match="capacity"):
        DeploymentStore(capacity=0)


def test_update_status(store: DeploymentStore) -> None:
    created = store.add(make())
    updated = store.update_status(created.id, Status.ROLLED_BACK)
    assert updated is not None
    assert updated.status is Status.ROLLED_BACK
    assert store.update_status(999, Status.FAILED) is None


def test_dora_change_fail_rate_and_frequency(store: DeploymentStore) -> None:
    for status in ("succeeded", "succeeded", "failed", "rolled_back"):
        store.add(make(env="production", status=status))
    store.add(make(env="staging"))
    report = store.dora(window_days=2)
    prod = report.environments["production"]
    assert (prod.deployments, prod.needed_intervention, prod.change_fail_rate) == (4, 2, 0.5)
    assert prod.deployment_frequency_per_day == 2.0
    assert report.environments["dev"].change_fail_rate == 0.0


def test_dora_recovery_time_is_measured_per_service(
    store: DeploymentStore, clock: FakeClock
) -> None:
    store.add(make("api", "production", "failed"))
    clock.advance(minutes=30)
    store.add(make("web", "production"))  # a different service does not count as the fix
    clock.advance(minutes=30)
    store.add(make("api", "production"))  # fixed one hour after the failure
    clock.advance(hours=1)
    store.add(make("web", "production", "rolled_back"))  # not recovered yet
    prod = store.dora().environments["production"]
    assert prod.recovery_time_median_hours == 1.0


def test_dora_ignores_deployments_outside_the_window(
    store: DeploymentStore, clock: FakeClock
) -> None:
    store.add(make(env="production", status="failed"))
    clock.advance(days=10)
    store.add(make(env="production"))
    prod = store.dora(window_days=7).environments["production"]
    assert (prod.deployments, prod.change_fail_rate) == (1, 0.0)
    assert prod.recovery_time_median_hours is None


def test_dora_window_must_be_positive(store: DeploymentStore) -> None:
    with pytest.raises(ValueError, match="window_days"):
        store.dora(0)


def test_store_is_thread_safe(clock: FakeClock) -> None:
    shared = DeploymentStore(capacity=10_000, clock=clock)

    def worker() -> None:
        for _ in range(250):
            shared.add(make())

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    ids = [d.id for d in shared.list(limit=10_000)]
    assert len(ids) == 2_000
    assert len(set(ids)) == 2_000
