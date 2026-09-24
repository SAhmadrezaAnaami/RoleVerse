from dataclasses import dataclass
from threading import Lock
from time import monotonic


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._entries: dict[str, tuple[float, int]] = {}
        self._lock = Lock()

    def check(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitDecision:
        now = monotonic()
        with self._lock:
            started_at, count = self._entries.get(key, (now, 0))
            if now - started_at >= window_seconds:
                started_at = now
                count = 0
            if count >= limit:
                retry_after = max(1, int(window_seconds - (now - started_at)) + 1)
                self._entries[key] = (started_at, count)
                return RateLimitDecision(False, 0, retry_after)
            count += 1
            self._entries[key] = (started_at, count)
            return RateLimitDecision(True, max(0, limit - count), 0)
