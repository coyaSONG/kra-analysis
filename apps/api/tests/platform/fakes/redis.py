"""
Deterministic Redis fake shared by API tests.
"""

from __future__ import annotations

import fnmatch
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


@dataclass
class _FailurePlan:
    error: Exception
    remaining: int


class FakeRedisPipeline:
    """Minimal async Redis pipeline for rate-limit tests."""

    def __init__(self, redis: "FakeRedis"):
        self._redis = redis
        self._ops: list[tuple[str, tuple[Any, ...]]] = []

    def zremrangebyscore(self, key: str, min_score: float, max_score: float):
        self._ops.append(("zremrangebyscore", (key, min_score, max_score)))
        return self

    def zadd(self, key: str, mapping: dict[str, float]):
        self._ops.append(("zadd", (key, mapping)))
        return self

    def zcount(self, key: str, min_score: float, max_score: float):
        self._ops.append(("zcount", (key, min_score, max_score)))
        return self

    def expire(self, key: str, seconds: int):
        self._ops.append(("expire", (key, seconds)))
        return self

    async def execute(self) -> list[Any]:
        await self._redis._maybe_fail("pipeline.execute")
        results: list[Any] = []
        for op_name, args in self._ops:
            if op_name == "zremrangebyscore":
                results.append(self._redis._zremrangebyscore(*args))
            elif op_name == "zadd":
                results.append(self._redis._zadd(*args))
            elif op_name == "zcount":
                results.append(self._redis._zcount(*args))
            elif op_name == "expire":
                results.append(await self._redis.expire(*args))
            else:
                raise RuntimeError(f"Unsupported fake Redis pipeline op: {op_name}")
        return results


class FakeRedis:
    """In-memory Redis fake covering the subset used by this repository."""

    def __init__(self):
        self._values: dict[str, str] = {}
        self._expires_at: dict[str, float] = {}
        self._sorted_sets: dict[str, dict[str, float]] = {}
        self._failures: dict[str, _FailurePlan] = {}
        self.closed = False

    def inject_failure(self, method: str, error: Exception, count: int = 1) -> None:
        """Make the next `count` calls to `method` raise `error`."""
        self._failures[method] = _FailurePlan(error=error, remaining=count)

    async def _maybe_fail(self, method: str) -> None:
        plan = self._failures.get(method)
        if not plan:
            return
        plan.remaining -= 1
        if plan.remaining <= 0:
            self._failures.pop(method, None)
        raise plan.error

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [key for key, ts in self._expires_at.items() if ts <= now]
        for key in expired:
            self._values.pop(key, None)
            self._sorted_sets.pop(key, None)
            self._expires_at.pop(key, None)

    async def ping(self) -> bool:
        await self._maybe_fail("ping")
        self._cleanup_expired()
        return True

    async def get(self, key: str) -> str | None:
        await self._maybe_fail("get")
        self._cleanup_expired()
        return self._values.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        await self._maybe_fail("set")
        self._cleanup_expired()
        self._values[key] = value
        if ex is not None:
            self._expires_at[key] = time.time() + ex
        else:
            self._expires_at.pop(key, None)
        return True

    async def setex(self, key: str, ttl: int, value: str) -> bool:
        await self._maybe_fail("setex")
        return await self.set(key, value, ex=ttl)

    async def delete(self, *keys: str) -> int:
        await self._maybe_fail("delete")
        self._cleanup_expired()
        deleted = 0
        for key in keys:
            existed = key in self._values or key in self._sorted_sets
            self._values.pop(key, None)
            self._sorted_sets.pop(key, None)
            self._expires_at.pop(key, None)
            if existed:
                deleted += 1
        return deleted

    async def exists(self, key: str) -> int:
        await self._maybe_fail("exists")
        self._cleanup_expired()
        return int(key in self._values or key in self._sorted_sets)

    async def incr(self, key: str) -> int:
        await self._maybe_fail("incr")
        self._cleanup_expired()
        current = int(self._values.get(key, "0"))
        current += 1
        self._values[key] = str(current)
        return current

    async def expire(self, key: str, seconds: int) -> bool:
        await self._maybe_fail("expire")
        self._cleanup_expired()
        if key not in self._values and key not in self._sorted_sets:
            return False
        self._expires_at[key] = time.time() + seconds
        return True

    async def ttl(self, key: str) -> int:
        await self._maybe_fail("ttl")
        self._cleanup_expired()
        if key not in self._values and key not in self._sorted_sets:
            return -2
        expires_at = self._expires_at.get(key)
        if expires_at is None:
            return -1
        remaining = int(expires_at - time.time())
        return max(0, remaining)

    async def flushdb(self) -> bool:
        await self._maybe_fail("flushdb")
        self._values.clear()
        self._expires_at.clear()
        self._sorted_sets.clear()
        return True

    async def close(self) -> None:
        self.closed = True

    async def scan_iter(self, match: str = "*") -> AsyncIterator[str]:
        await self._maybe_fail("scan_iter")
        self._cleanup_expired()
        seen = sorted(set(self._values) | set(self._sorted_sets))
        for key in seen:
            if fnmatch.fnmatch(key, match):
                yield key

    def pipeline(self) -> FakeRedisPipeline:
        return FakeRedisPipeline(self)

    def _zremrangebyscore(self, key: str, min_score: float, max_score: float) -> int:
        self._cleanup_expired()
        items = self._sorted_sets.setdefault(key, {})
        to_remove = [
            member for member, score in items.items() if min_score <= score <= max_score
        ]
        for member in to_remove:
            items.pop(member, None)
        return len(to_remove)

    def _zadd(self, key: str, mapping: dict[str, float]) -> int:
        self._cleanup_expired()
        items = self._sorted_sets.setdefault(key, {})
        added = 0
        for member, score in mapping.items():
            if member not in items:
                added += 1
            items[member] = score
        return added

    def _zcount(self, key: str, min_score: float, max_score: float) -> int:
        self._cleanup_expired()
        items = self._sorted_sets.get(key, {})
        return sum(1 for score in items.values() if min_score <= score <= max_score)


class MockRedisClient(FakeRedis):
    """Compatibility alias for legacy tests."""

