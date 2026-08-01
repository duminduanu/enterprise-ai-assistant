"""Token-bucket rate limiter keyed per user."""

from __future__ import annotations

import asyncio
import time

from backend.app.core.exceptions import RateLimitError


class TokenBucketRateLimiter:
    """In-process token bucket: `rate_per_minute` requests sustained per key."""

    def __init__(self, rate_per_minute: int) -> None:
        self._rate = max(1, rate_per_minute)
        self._capacity = float(self._rate)
        self._refill_per_second = self._rate / 60.0
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = asyncio.Lock()

    @property
    def rate_per_minute(self) -> int:
        return self._rate

    async def acquire(self, key: str) -> None:
        """Consume one token for `key` or raise RateLimitError."""
        async with self._lock:
            now = time.monotonic()
            tokens, last = self._buckets.get(key, (self._capacity, now))
            elapsed = max(0.0, now - last)
            tokens = min(self._capacity, tokens + elapsed * self._refill_per_second)

            if tokens < 1.0:
                retry_after = int(max(1, (1.0 - tokens) / self._refill_per_second))
                raise RateLimitError(
                    f"Rate limit exceeded ({self._rate} requests/minute). "
                    f"Retry after ~{retry_after}s.",
                    retry_after=retry_after,
                )

            self._buckets[key] = (tokens - 1.0, now)

    async def reset(self, key: str | None = None) -> None:
        """Clear bucket state (used in tests)."""
        async with self._lock:
            if key is None:
                self._buckets.clear()
            else:
                self._buckets.pop(key, None)
