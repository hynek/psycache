# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

"""
Sentry-backed cache instrumentation.

See also:

  - <https://docs.sentry.io/platforms/python/tracing/instrumentation/custom-instrumentation/caches-module/>
  - <https://develop.sentry.dev/sdk/telemetry/traces/modules/caches/>

Span instances are not frozen because they're instantiated a lot so we go for
performance.
"""

from collections.abc import Generator
from contextlib import contextmanager

import sentry_sdk

from sentry_sdk.traces import Span

from psycache.instrumentation import NoopAnySpan
from psycache.typing import (
    CacheCleanupSpan,
    CacheFlushSpan,
    CacheGetSpan,
    CachePutSpan,
    CacheRemoveSpan,
)


class _SentryCacheGetSpan:
    """
    Sentry-backed span for cache get operations.
    """

    __slots__ = ("_key", "_span")

    _key: str
    _span: Span

    def __init__(self, key: str, span: Span) -> None:
        self._key = key
        self._span = span

    def record_cache_hit(self, item_size: int) -> None:
        self._span.set_attributes(
            {
                "cache.hit": True,
                "cache.item_size": item_size,
                "cache.success": True,
            }
        )

    def record_cache_miss(self) -> None:
        self._span.set_attributes({"cache.hit": False, "cache.success": True})


class _SentryCachePutSpan:
    """
    Sentry-backed span for cache put operations.
    """

    __slots__ = ("_key", "_span")

    _key: str
    _span: Span

    def __init__(self, key: str, span: Span) -> None:
        self._key = key
        self._span = span

    def record_put(self, item_size: int) -> None:
        self._span.set_attributes(
            {"cache.item_size": item_size, "cache.success": True}
        )


class _SentryCacheRemoveSpan:
    """
    Sentry-backed span for cache removal operations.
    """

    __slots__ = ("_key", "_span")

    _key: str
    _span: Span

    def __init__(self, key: str, span: Span) -> None:
        self._key = key
        self._span = span

    def record_removed(self) -> None:
        self._span.set_attribute("cache.success", True)


class _SentryCacheFlushSpan:
    """
    Sentry-backed span for cache flush operations.
    """

    __slots__ = ("_span",)

    _span: Span

    def __init__(self, span: Span) -> None:
        self._span = span

    def record_flush(self, num_flushed: int) -> None:
        self._span.set_attribute("cache.num_flushed", num_flushed)


class SentryInstrumentation:
    """
    Sentry-backed instrumentation for cache operations.
    """

    @contextmanager
    def start_cache_get_span(
        self, key: str, name: str | None
    ) -> Generator[CacheGetSpan]:
        with sentry_sdk.start_span(
            name=name or "psycache get",
            attributes={"sentry.op": "cache.get", "cache.key": [key]},
        ) as span:
            yield _SentryCacheGetSpan(key, span)

    @contextmanager
    def start_cache_put_span(
        self, key: str, name: str | None
    ) -> Generator[CachePutSpan]:
        with sentry_sdk.start_span(
            name=name or "psycache put",
            attributes={"sentry.op": "cache.put", "cache.key": [key]},
        ) as span:
            yield _SentryCachePutSpan(key, span)

    @contextmanager
    def start_cache_remove_span(self, key: str) -> Generator[CacheRemoveSpan]:
        with sentry_sdk.start_span(
            name="psycache remove",
            attributes={"sentry.op": "cache.remove", "cache.key": [key]},
        ) as span:
            yield _SentryCacheRemoveSpan(key, span)

    @contextmanager
    def start_cache_cleanup_span(self) -> Generator[CacheCleanupSpan]:
        yield NoopAnySpan()

    @contextmanager
    def start_cache_flush_span(self) -> Generator[CacheFlushSpan]:
        with sentry_sdk.start_span(
            name="psycache flush", attributes={"sentry.op": "cache.flush"}
        ) as span:
            yield _SentryCacheFlushSpan(span)
