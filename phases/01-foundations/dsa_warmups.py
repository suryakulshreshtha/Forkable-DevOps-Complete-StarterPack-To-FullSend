"""Five classic data-structure problems, each one taken from real operations work.

Big-tech SRE and platform interviews include a coding round (Google's SRE postings
list data structures and algorithms in their minimum qualifications). These are
warm-ups in that style. Read each docstring, cover the code, and try it yourself
first; check_phase01.py tests your version.
"""

from __future__ import annotations

import heapq
from collections import Counter, OrderedDict, deque
from collections.abc import Iterable
from graphlib import CycleError, TopologicalSorter


def top_k_clients(ips: Iterable[str], k: int) -> list[tuple[str, int]]:
    """Which k IPs send the most requests? (Think: finding a misbehaving client.)

    Counter gives counts in O(n); heapq.nlargest picks the top k in O(n log k),
    which beats sorting everything when k is small. Ties break by IP for stable output.
    """
    counts = Counter(ips)
    return heapq.nlargest(k, counts.items(), key=lambda item: (item[1], _reverse_key(item[0])))


def _reverse_key(text: str) -> tuple[int, ...]:
    # Larger tuple for alphabetically earlier text, so nlargest prefers "a" over "b" on ties.
    return tuple(-ord(ch) for ch in text)


class SlidingWindowLimiter:
    """Allow at most `limit` requests in any `window` seconds. (Think: an API rate limit.)

    A deque holds the timestamps of accepted requests; old ones fall off the left.
    Each call is amortised O(1).
    """

    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window
        self._hits: deque[float] = deque()

    def allow(self, now: float) -> bool:
        while self._hits and self._hits[0] <= now - self.window:
            self._hits.popleft()
        if len(self._hits) < self.limit:
            self._hits.append(now)
            return True
        return False


class LRUCache:
    """Keep the `capacity` most recently used items. (Think: a DNS or config cache.)

    OrderedDict remembers order; move_to_end marks an item as fresh and
    popitem(last=False) evicts the stalest. Both operations are O(1).
    """

    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self._data: OrderedDict[str, str] = OrderedDict()

    def get(self, key: str) -> str | None:
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key: str, value: str) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)


def merge_windows(windows: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping maintenance windows (start, end) into the fewest blocks.

    Sort by start, then extend the last block while the next one overlaps or touches it.
    O(n log n) for the sort.
    """
    merged: list[tuple[int, int]] = []
    for start, end in sorted(windows):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def deploy_order(depends_on: dict[str, set[str]]) -> list[str]:
    """Order services so each deploys after everything it depends on.

    This is a topological sort; the standard library ships one (graphlib).
    A dependency cycle means no valid order exists, which is a design bug worth surfacing.
    """
    sorter = TopologicalSorter(depends_on)
    try:
        sorter.prepare()
    except CycleError as exc:
        raise ValueError(f"dependency cycle: {' -> '.join(exc.args[1])}") from exc
    order: list[str] = []
    while sorter.is_active():
        ready = sorted(sorter.get_ready())  # sorted: deterministic output
        order.extend(ready)
        sorter.done(*ready)
    return order
