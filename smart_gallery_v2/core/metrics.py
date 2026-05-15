"""Local metrics for Smart Gallery maintenance and operations.

Tracks:
- Files processed (total, successes, failures)
- Cleanup operations (orphans removed, links removed, duration)
- Maintenance task status and exit codes
- Performance timings
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable


class Metrics:
    """Simple internal metrics collector for Smart Gallery."""

    _instance: Metrics | None = None

    def __new__(cls) -> Metrics:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = {
                "files_processed": 0,
                "files_successful": 0,
                "files_failed": 0,
                "cleanup_orphans_total": 0,
                "cleanup_links_total": 0,
                "maintenance_runs": 0,
                "maintenance_errors": 0,
                "last_maintenance_duration_seconds": 0.0,
                "faiss_reindexes": 0,
            }
        return cls._instance

    def increment(self, key: str, value: int = 1) -> None:
        if key in self._data:
            self._data[key] += value

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str) -> Any:
        return self._data.get(key, 0)

    def get_all(self) -> dict[str, Any]:
        return dict(self._data)

    @contextmanager
    def timer(self, key_suffix: str):
        """Context manager for timing operations."""
        start = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start
            self.set(f"last_{key_suffix}_seconds", elapsed)

    def record_cleanup(self, orphans: int, links: int, duration: float) -> None:
        """Record a cleanup operation."""
        self.increment("cleanup_orphans_total", orphans)
        self.increment("cleanup_links_total", links)
        self.increment("maintenance_runs")
        self.set("last_maintenance_duration_seconds", duration)

    def record_maintenance_error(self) -> None:
        """Record a maintenance error."""
        self.increment("maintenance_errors")


# Singleton instance
metrics = Metrics()


def timed_operation(operation_name: str) -> Callable:
    """Decorator to time function execution and record in metrics."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.time() - start
                metrics.set(f"last_{operation_name}_duration_seconds", elapsed)

        return wrapper

    return decorator
