# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import datetime as dt
import logging
import threading

from collections.abc import Callable, Sequence
from typing import Any, Self

import attrs

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


@attrs.frozen
class CleanupService:
    """
    Handle for a periodic cache cleanup thread.

    Can be used as a context manager or stopped manually via `stop()`.
    """

    _thread: threading.Thread = attrs.field(alias="thread")
    _stop_event: threading.Event = attrs.field(alias="stop_event")

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


@attrs.frozen
class PostgresCache:
    """
    A Postgres-based cache.
    """

    pool: CachePool
    instrumentations: Sequence[CacheInstrumentation] = attrs.field(
        default=(), kw_only=True
    )

    def get_raw(
        self, key: str, span_name: str | None = None
    ) -> dict[str, Any] | None:
        with _lookup_span(self.instrumentations, key, span_name) as span:
            with self.pool.connect() as conn:
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
        with _put_span(self.instrumentations, key, span_name) as span:
            if isinstance(ttl, int):
                ttl = dt.timedelta(seconds=ttl)

            expires_at = dt.datetime.now().astimezone() + ttl

            with self.pool.connect() as conn:
                row = conn.execute(
                    _sql.PUT, (key, Jsonb(value), expires_at)
                ).fetchone()

            span.record_put(row[0])  # type: ignore[index]  # ty: ignore[not-subscriptable]

    def remove(self, key: str) -> None:
        with _remove_span(self.instrumentations, key) as span:
            with self.pool.connect() as conn:
                conn.execute(_sql.REMOVE, (key,))

            span.record_removed()

    def cleanup_expired(self) -> int:
        """
        Delete all expired cache entries.

        Return the number of deleted entries.
        """
        with _cleanup_span(self.instrumentations) as span:
            with self.pool.connect() as conn:
                num_deleted: int = conn.execute(_sql.CLEANUP_EXPIRED).rowcount

            span.record_cleanup(num_deleted)

        return num_deleted

    def flush(self) -> int:
        """
        Flush all cache entries.

        Return the number of flushed entries.
        """
        with _flush_span(self.instrumentations) as span:
            with self.pool.connect() as conn:
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
