"""In-memory sliding-window rate limiter (per client IP and tier) and trusted-proxy-aware client IP.
Per process, resets on restart; documented in docs/API_HARDENING.md."""
import ipaddress
import math
from collections import deque

from app import runtime


class SlidingWindowLimiter:
    def __init__(self, limits: dict[str, int], window: float = 60.0, max_keys: int = 20_000):
        self.limits, self.window, self.max_keys = limits, window, max_keys
        self._hits: dict[tuple, deque] = {}

    def reset(self) -> None:
        self._hits.clear()

    def check(self, key: str, tier: str) -> tuple[bool, int]:
        """Record a hit. Returns (allowed, retry_after_seconds)."""
        now = runtime.now()
        if len(self._hits) > self.max_keys:
            self._purge(now)
        q = self._hits.setdefault((key, tier), deque())
        while q and q[0] <= now - self.window:
            q.popleft()
        if len(q) >= self.limits[tier]:
            return False, max(1, math.ceil(q[0] + self.window - now))
        q.append(now)
        return True, 0

    def _purge(self, now: float) -> None:
        for k in [k for k, q in self._hits.items() if not q or q[-1] <= now - self.window]:
            del self._hits[k]
        if len(self._hits) > self.max_keys:  # still too many distinct clients: drop the oldest half
            for k in list(self._hits)[: len(self._hits) // 2]:
                del self._hits[k]


def client_ip(scope: dict, trusted_hops: int) -> str:
    """Socket address by default. With N trusted proxies, the client is the Nth entry from the RIGHT of X-Forwarded-For
    (each trusted proxy appends the address it saw), so anything a client prepends is ignored."""
    peer = (scope.get("client") or ("unknown", 0))[0]
    if trusted_hops <= 0:
        return peer
    raw = ",".join(v.decode("latin-1") for k, v in scope.get("headers", []) if k == b"x-forwarded-for")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) < trusted_hops:
        return peer
    try:
        return str(ipaddress.ip_address(parts[-trusted_hops]))
    except ValueError:
        return peer
