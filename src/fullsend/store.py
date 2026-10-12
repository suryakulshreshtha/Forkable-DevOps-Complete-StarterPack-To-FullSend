"""A thread-safe, size-bounded, in-memory deployment store.

In-memory keeps the course focused on DevOps instead of databases. Because the
store sits behind one small class, swapping in a real database later only
touches this file: that is "design for change" in practice.
"""

from __future__ import annotations

import statistics
import threading
from collections import OrderedDict
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fullsend.models import (
    NEEDS_INTERVENTION,
    Deployment,
    DeploymentIn,
    DoraReport,
    DoraSnapshot,
    Environment,
    Status,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class DeploymentStore:
    """Keeps the newest ``capacity`` deployments; the oldest are dropped first."""

    def __init__(self, capacity: int = 10_000, clock: Callable[[], datetime] = utcnow) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self._capacity = capacity
        self._clock = clock
        self._items: OrderedDict[int, Deployment] = OrderedDict()
        self._next_id = 1
        self._lock = threading.Lock()

    def add(self, data: DeploymentIn) -> Deployment:
        with self._lock:
            deployment = Deployment(id=self._next_id, created_at=self._clock(), **data.model_dump())
            self._items[deployment.id] = deployment
            self._next_id += 1
            while len(self._items) > self._capacity:
                self._items.popitem(last=False)
            return deployment

    def get(self, deployment_id: int) -> Deployment | None:
        with self._lock:
            return self._items.get(deployment_id)

    def update_status(self, deployment_id: int, status: Status) -> Deployment | None:
        with self._lock:
            current = self._items.get(deployment_id)
            if current is None:
                return None
            updated = current.model_copy(update={"status": status})
            self._items[deployment_id] = updated
            return updated

    def list(self, environment: Environment | None = None, limit: int = 100) -> list[Deployment]:
        """Newest first, optionally only one environment."""
        with self._lock:
            result: list[Deployment] = []
            for item in reversed(self._items.values()):
                if environment is not None and item.environment != environment:
                    continue
                result.append(item)
                if len(result) >= limit:
                    break
            return result

    def dora(self, window_days: int = 30) -> DoraReport:
        """DORA-style delivery metrics per environment over the last ``window_days``."""
        if window_days < 1:
            raise ValueError("window_days must be at least 1")
        since = self._clock() - timedelta(days=window_days)
        with self._lock:
            recent = [d for d in self._items.values() if d.created_at >= since]
        environments = {
            env.value: _snapshot([d for d in recent if d.environment == env], window_days)
            for env in Environment
        }
        return DoraReport(window_days=window_days, environments=environments)

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)


def _snapshot(items: list[Deployment], window_days: int) -> DoraSnapshot:
    failed = [d for d in items if d.status in NEEDS_INTERVENTION]
    recoveries: list[float] = []
    for bad in failed:
        fix = next(
            (
                d
                for d in items
                if d.service == bad.service
                and d.status is Status.SUCCEEDED
                and d.created_at > bad.created_at
            ),
            None,
        )
        if fix is not None:
            recoveries.append((fix.created_at - bad.created_at).total_seconds() / 3600)
    return DoraSnapshot(
        deployments=len(items),
        deployment_frequency_per_day=round(len(items) / window_days, 3),
        needed_intervention=len(failed),
        change_fail_rate=round(len(failed) / len(items), 4) if items else 0.0,
        recovery_time_median_hours=round(statistics.median(recoveries), 2) if recoveries else None,
    )
