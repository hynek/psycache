# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import asyncio
import datetime as dt
import logging

from collections.abc import Awaitable, Callable, Sequence
from contextlib import suppress
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
from .typing import AsyncCachePool, CacheInstrumentation


logger = logging.getLogger(__name__)


async def _cleanup_loop(
    cleanup: Callable[[], Awaitable[int]],
    interval_seconds: float,
    stop_event: asyncio.Event,
) -> None:
    while not stop_event.is_set():
        try:
            await cleanup()
        except Exception:
            logger.exception("Periodic cache cleanup failed")

        with suppress(TimeoutError):
            await asyncio.wait_for(stop_event.wait(), interval_seconds)


class AsyncCleanupService:
    """
    Handle for a periodic cache cleanup task.

    Can be used as an async context manager or stopped manually via `stop()`.
    """

    __slots__ = ("_stop_event", "_task")

    _task: asyncio.Task[None]
    _stop_event: asyncio.Event

    def __init__(
        self,
        task: asyncio.Task[None],
        stop_event: asyncio.Event,
    ) -> None:
        self._task = task
        self._stop_event = stop_event

    async def stop(
        self,
        timeout: dt.timedelta | float | None = 5.0,  # noqa: ASYNC109
    ) -> bool:
        """
        Stop the cleanup task and wait for it to finish.

        Return whether the task exited before the timeout elapsed.
        """
        self._stop_event.set()
        try:
            await asyncio.wait_for(
                asyncio.shield(self._task),
                _coerce_stop_timeout_seconds(timeout),
            )
        except TimeoutError:
            logger.warning(
                "Cleanup task did not stop within timeout=%s", timeout
            )
            return False

        return True

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.stop()


class AsyncPostgresCache:
    """
    An asyncio-based Postgres cache.
    """

    __slots__ = ("_instrumentations", "_pool")

    _pool: AsyncCachePool
    _instrumentations: Sequence[CacheInstrumentation]

    def __init__(
        self,
        pool: AsyncCachePool,
        *,
        instrumentations: Sequence[CacheInstrumentation] = (),
    ):
        self._pool = pool
        self._instrumentations = instrumentations

    async def get_raw(
        self, key: str, span_name: str | None = None
    ) -> dict[str, Any] | None:
        """
        Same as [`PostgresCache.get_raw`][psycache.PostgresCache.get_raw],
        but async.
        """
        with _lookup_span(self._instrumentations, key, span_name) as span:
            async with self._pool.connect() as conn:
                cur = await conn.execute(_sql.GET, (key,))
                row = await cur.fetchone()

            if row is None:
                span.record_cache_miss()
                return None

            span.record_cache_hit(row[1])

        return row[0]  # type: ignore[no-any-return]

    async def put_raw(
        self,
        key: str,
        value: dict[str, Any],
        ttl: int | dt.timedelta,
        span_name: str | None = None,
    ) -> None:
        """
        Same as [`PostgresCache.put_raw`][psycache.PostgresCache.put_raw],
        but async.
        """
        with _put_span(self._instrumentations, key, span_name) as span:
            if isinstance(ttl, int):
                ttl = dt.timedelta(seconds=ttl)

            expires_at = dt.datetime.now().astimezone() + ttl

            async with self._pool.connect() as conn:
                cur = await conn.execute(
                    _sql.PUT, (key, Jsonb(value), expires_at)
                )
                row = await cur.fetchone()

            span.record_put(row[0])  # type: ignore[index]  # ty: ignore[not-subscriptable]

    async def remove(self, key: str) -> None:
        """
        Same as [`PostgresCache.remove`][psycache.PostgresCache.remove],
        but async.
        """
        with _remove_span(self._instrumentations, key) as span:
            async with self._pool.connect() as conn:
                await conn.execute(_sql.REMOVE, (key,))

            span.record_removed()

    async def cleanup_expired(self) -> int:
        """
        Same as [`PostgresCache.cleanup_expired`][psycache.PostgresCache.cleanup_expired],
        but async.
        """
        with _cleanup_span(self._instrumentations) as span:
            async with self._pool.connect() as conn:
                cur = await conn.execute(_sql.CLEANUP_EXPIRED)
                num_deleted: int = cur.rowcount

            span.record_cleanup(num_deleted)

        return num_deleted

    def start_cleanup_task(
        self, interval: dt.timedelta | float
    ) -> AsyncCleanupService:
        """
        Start a [`Task`][asyncio.Task] that periodically deletes expired
        cache entries.

        Must be called within a running asyncio event loop.

        Args:
            interval:
                Time between cleanup runs. In seconds or as a timedelta.

        Returns:
            An `AsyncCleanupService` that can be used to stop the task.
        """
        interval_seconds = _coerce_cleanup_interval_seconds(interval)

        stop_event = asyncio.Event()
        task = asyncio.create_task(
            _cleanup_loop(
                self.cleanup_expired,
                interval_seconds,
                stop_event,
            ),
            name="psycache-cleanup",
        )

        return AsyncCleanupService(task=task, stop_event=stop_event)

    async def flush(self) -> int:
        """
        Same as [`PostgresCache.flush`][psycache.PostgresCache.flush],
        but async.
        """
        with _flush_span(self._instrumentations) as span:
            async with self._pool.connect() as conn:
                cur = await conn.execute(_sql.FLUSH)
                num_flushed: int = cur.rowcount

            span.record_flush(num_flushed)

        return num_flushed
