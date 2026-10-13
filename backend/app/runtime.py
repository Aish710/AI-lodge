"""Single time source for limiter, circuit breaker and deadlines. Tests monkeypatch `now` (no sleeping)."""
import time


def now() -> float:
    return time.monotonic()
