import time
from typing import Any, Callable, Optional, Tuple


class TTLCache:
    """Tiny in-memory TTL cache with size cap.

    - Evicts oldest item on overflow
    - Per-key TTL (seconds)
    - Thread-unsafe (sufficient for Flask dev single-process)
    """

    def __init__(self, maxsize: int = 256, default_ttl: float = 30.0):
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self._store: dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        item = self._store.get(key)
        if not item:
            return None
        expiry, value = item
        if expiry < now:
            # expired
            try:
                del self._store[key]
            except KeyError:
                pass
            return None
        return value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        expiry = time.time() + (ttl if ttl is not None else self.default_ttl)
        if len(self._store) >= self.maxsize:
            # Evict the oldest (smallest expiry)
            oldest_key = min(self._store.items(), key=lambda kv: kv[1][0])[0]
            try:
                del self._store[oldest_key]
            except KeyError:
                pass
        self._store[key] = (expiry, value)

    def get_or_set(self, key: str, producer: Callable[[], Any], ttl: Optional[float] = None) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = producer()
        self.set(key, value, ttl)
        return value
