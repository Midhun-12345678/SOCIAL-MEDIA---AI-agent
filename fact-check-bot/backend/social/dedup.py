import threading
import time
import logging

logger = logging.getLogger(__name__)


class DedupTracker:
    """
    TTL-based deduplication tracker.
    Stores (platform, post_id) → timestamp.
    Entries older than ttl_hours are evicted on each check cycle.
    """

    def __init__(self, ttl_hours: float = 24.0):
        self._seen: dict[tuple[str, str], float] = {}
        self._ttl_seconds = ttl_hours * 3600
        self._lock = threading.Lock()

    def is_seen(self, platform: str, post_id: str) -> bool:
        key = (platform, post_id)
        with self._lock:
            self._evict_stale()
            return key in self._seen

    def mark_seen(self, platform: str, post_id: str) -> None:
        key = (platform, post_id)
        with self._lock:
            self._seen[key] = time.time()

    def _evict_stale(self) -> None:
        cutoff = time.time() - self._ttl_seconds
        stale_keys = [k for k, ts in self._seen.items() if ts < cutoff]
        for k in stale_keys:
            del self._seen[k]
        if stale_keys:
            logger.debug(f"DedupTracker evicted {len(stale_keys)} stale entries")

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._seen)
