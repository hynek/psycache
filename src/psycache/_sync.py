# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import datetime as dt
import logging
import threading

from collections.abc import Callable, Sequence
from typing import Any, Self

from psycopg.types.json import Jsonb

from . import _sql
from ._durations import (
    _coerce_cleanup_interval_seconds,
    _coerce_stop_timeout_seconds,
)
from .instrumentation._spans import (
    _cleanup_span,
    _flush_span,
    _lookup_span,
    _put_span,
    _remove_span,
)
from .typing import CacheInstrumentation, CachePool


logger = logging.getLogger(__name__)


def _cleanup_loop(
    cleanup: Callable[[], int],
    interval_seconds: float,
    stop_event: threading.Event,
) -> None:
    while not stop_event.is_set():
        try:
            cleanup()
        except Exception:
            logger.exception("Periodic cache cleanup failed")

        stop_event.wait(interval_seconds)


class CleanupService:
    """
    Handle for a periodic cache cleanup thread.

    Can be used as a context manager or stopped manually via `stop()`.
    """

    __slots__ = ("_stop_event", "_thread")

    _thread: threading.Thread
    _stop_event: threading.Event

    def __init__(
        self, thread: threading.Thread, stop_event: threading.Event
    ) -> None:
        self._thread = thread
        self._stop_event = stop_event

    def stop(self, timeout: dt.timedelta | float | None = 5.0) -> bool:
        """
        Stop the cleanup thread and wait for it to finish.

        Return whether the thread exited before the timeout elapsed.
        """
        self._stop_event.set()
        self._thread.join(
            _coerce_stop_timeout_seconds(
                timeout, max_seconds=threading.TIMEOUT_MAX
            )
        )

        stopped = not self._thread.is_alive()
        if not stopped:
            logger.warning(
                "Cleanup thread did not stop within timeout=%s", timeout
            )

        return stopped

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()


class PostgresCache:
    """
    A Postgres-based cache.
    """

    __slots__ = ("_instrumentations", "_pool")

    _pool: CachePool
    _instrumentations: Sequence[CacheInstrumentation]

    def __init__(
        self,
        pool: CachePool,
        *,
        instrumentations: Sequence[CacheInstrumentation] = (),
    ):
        """
        Args:
            pool: The cache pool to use.
            instrumentations: Sequence of instrumentations to use.
        """
        self._pool = pool
        self._instrumentations = instrumentations

    def get_raw(
        self, key: str, span_name: str | None = None
    ) -> dict[str, Any] | None:
        """
        Get a raw dict from the cache for *key*.

        Args:
            key: The key to look up.

            span_name: Name for the span that is passed to instrumentation.

        Returns:
            The raw dict for *key*, or None if the key is not found or
                expired.
        """
        with _lookup_span(self._instrumentations, key, span_name) as span:
            with self._pool.connect() as conn:
                row = conn.execute(_sql.GET, (key,)).fetchone()

            if row is None:
                span.record_cache_miss()
                return None

            span.record_cache_hit(row[1])

        return row[0]  # type: ignore[no-any-return]

    def put_raw(
        self,
        key: str,
        value: dict[str, Any],
        ttl: int | dt.timedelta,
        span_name: str | None = None,
    ) -> None:
        """
        Put *value* into the cache under *key* with time-to-live of *ttl*.

        Args:
            key: The key under which to store the value.

            value: The value to store in the cache.

            ttl: The time-to-live for the cache entry.

            span_name:  Name for the span that is passed to instrumentation.
        """
        with _put_span(self._instrumentations, key, span_name) as span:
            if isinstance(ttl, int):
                ttl = dt.timedelta(seconds=ttl)

            expires_at = dt.datetime.now().astimezone() + ttl

            with self._pool.connect() as conn:
                row = conn.execute(
                    _sql.PUT, (key, Jsonb(value), expires_at)
                ).fetchone()

            span.record_put(row[0])  # type: ignore[index]  # ty: ignore[not-subscriptable]

    def remove(self, key: str) -> None:
        """
        Remove the cache entry for *key*.

        Trying to remove a non-existent key is a no-op.

        Args:
            key: The key to remove.
        """
        with _remove_span(self._instrumentations, key) as span:
            with self._pool.connect() as conn:
                conn.execute(_sql.REMOVE, (key,))

            span.record_removed()

    def cleanup_expired(self) -> int:
        """
        Delete all expired cache entries.

        Return the number of deleted entries.
        """
        with _cleanup_span(self._instrumentations) as span:
            with self._pool.connect() as conn:
                num_deleted: int = conn.execute(_sql.CLEANUP_EXPIRED).rowcount

            span.record_cleanup(num_deleted)

        return num_deleted

    def flush(self) -> int:
        """
        Flush all cache entries.

        Return the number of flushed entries.
        """
        with _flush_span(self._instrumentations) as span:
            with self._pool.connect() as conn:
                num_flushed: int = conn.execute(_sql.FLUSH).rowcount

            span.record_flush(num_flushed)

        return num_flushed

    def start_cleanup_thread(
        self, interval: dt.timedelta | float
    ) -> CleanupService:
        """
        Start a daemon thread that periodically deletes expired cache entries.

        Args:
            interval:
                Time between cleanup runs. In seconds or as a timedelta.

        Returns:
            A `CleanupService` that can be used to stop the thread.
        """
        interval_seconds = _coerce_cleanup_interval_seconds(
            interval, max_seconds=threading.TIMEOUT_MAX
        )

        stop_event = threading.Event()
        thread = threading.Thread(
            name="psycache-cleanup",
            target=_cleanup_loop,
            args=(
                self.cleanup_expired,
                interval_seconds,
                stop_event,
            ),
            daemon=True,
        )
        thread.start()

        return CleanupService(thread=thread, stop_event=stop_event)
