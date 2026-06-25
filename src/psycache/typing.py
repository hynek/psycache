# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from contextlib import AbstractAsyncContextManager, AbstractContextManager
from typing import Protocol

import psycopg


class CachePool(Protocol):
    """
    Protocol for a class that provides a way to connect to a
    [`psycopg.Connection`][].

    Implemented by adapters that wrap a higher-level connection source
    (for example, a psycopg pool or a SQLAlchemy engine) and hand
    out an auto-commit [`psycopg.Connection`][].
    """

    def connect(self) -> AbstractContextManager[psycopg.Connection]:
        """
        Connect to the database and return a context manager for an
        auto-commit connection.
        """
        ...


class AsyncCachePool(Protocol):
    """
    Protocol for a class that provides a way to connect to a
    [`psycopg.AsyncConnection`][].

    Implemented by adapters that wrap a higher-level connection source
    (for example, a psycopg pool or a SQLAlchemy engine) and hand
    out an auto-commit [`psycopg.AsyncConnection`][].
    """

    def connect(
        self,
    ) -> AbstractAsyncContextManager[psycopg.AsyncConnection]:
        """
        Connect to the database and return a context manager for an
        auto-commit connection.
        """
        ...


class CacheInstrumentation(Protocol):
    """
    Cache instrumentation provider.
    """

    def start_cache_get_span(
        self, key: str, name: str | None
    ) -> AbstractContextManager[CacheGetSpan]:
        """
        Start a span for a cache get operation.
        """
        ...

    def start_cache_put_span(
        self, key: str, name: str | None
    ) -> AbstractContextManager[CachePutSpan]:
        """
        Start a span for a cache put operation.
        """
        ...

    def start_cache_remove_span(
        self, key: str
    ) -> AbstractContextManager[CacheRemoveSpan]:
        """
        Start a span for a cache removal operation.
        """
        ...

    def start_cache_flush_span(
        self,
    ) -> AbstractContextManager[CacheFlushSpan]:
        """
        Start a span for a cache flush operation.
        """
        ...

    def start_cache_cleanup_span(
        self,
    ) -> AbstractContextManager[CacheCleanupSpan]:
        """
        Start a span for a cache cleanup operation.
        """
        ...


class CacheGetSpan(Protocol):
    """
    Span interface for cache get operations.
    """

    def record_cache_hit(self, item_size: int) -> None:
        """
        Record a successful cache hit with the item size in bytes.
        """

    def record_cache_miss(self) -> None:
        """
        Record a cache miss (key not found or expired).
        """


class CachePutSpan(Protocol):
    """
    Span interface for cache write (put) operations.
    """

    def record_put(self, item_size: int) -> None:
        """
        Record a successful cache write with the item size in bytes.
        """


class CacheFlushSpan(Protocol):
    """
    Span interface for cache flush operations.
    """

    def record_flush(self, num_flushed: int) -> None:
        """
        Record a successful cache flush with the number of flushed entries.
        """


class CacheCleanupSpan(Protocol):
    """
    Span interface for cache cleanup operations.
    """

    def record_cleanup(self, num_deleted: int) -> None:
        """
        Record a successful cleanup with the number of deleted entries.
        """


class CacheRemoveSpan(Protocol):
    """
    Span interface for cache remove operations.
    """

    def record_removed(self) -> None:
        """
        Record a successful cache removal.
        """
