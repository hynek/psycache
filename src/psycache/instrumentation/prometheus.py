# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

"""
Prometheus-backed cache instrumentation.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from prometheus_client import Counter, Gauge, Histogram

from psycache.typing import (
    CacheCleanupSpan,
    CacheFlushSpan,
    CacheGetSpan,
    CachePutSpan,
    CacheRemoveSpan,
)


_LABEL_NAMES = ["span_name"]

CACHE_HITS = Counter(
    "psycache_hits_total",
    "Number of cache hits",
    labelnames=_LABEL_NAMES,
)

CACHE_MISSES = Counter(
    "psycache_misses_total",
    "Number of cache misses",
    labelnames=_LABEL_NAMES,
)

CACHE_GET_DURATION = Histogram(
    "psycache_get_duration_seconds",
    "Time taken for cache get operations",
    labelnames=_LABEL_NAMES,
)

CACHE_PUT_DURATION = Histogram(
    "psycache_put_duration_seconds",
    "Time taken for cache put operations",
    labelnames=_LABEL_NAMES,
)

CACHE_REMOVE_DURATION = Histogram(
    "psycache_remove_duration_seconds",
    "Time taken for cache remove operations",
)

CACHE_FLUSH_DURATION = Histogram(
    "psycache_flush_duration_seconds",
    "Time taken for cache flush operations",
)

CACHE_ITEM_SIZE = Histogram(
    "psycache_item_size_bytes",
    "Size of cache items in bytes",
    labelnames=_LABEL_NAMES,
    buckets=[64, 256, 1024, 4096, 16384, 65536, 262144, 1048576],
)

CACHE_FLUSHED_ENTRIES = Histogram(
    "psycache_flushed_entries",
    "Number of entries flushed per flush operation",
    buckets=[0, 1, 5, 10, 25, 50, 100, 250, 500, 1000],
)

CACHE_CLEANUP_LAST_RUN = Gauge(
    "psycache_cleanup_last_run_timestamp_seconds",
    "Timestamp of the last expired-entry cleanup run",
)

CACHE_CLEANUP_DELETED = Gauge(
    "psycache_cleanup_deleted_entries",
    "Number of expired entries deleted in the last cleanup run",
)


class _PrometheusCacheGetSpan:
    def __init__(self, span_name: str) -> None:
        self._span_name = span_name

    def record_cache_hit(self, item_size: int) -> None:
        CACHE_HITS.labels(span_name=self._span_name).inc()
        CACHE_ITEM_SIZE.labels(span_name=self._span_name).observe(item_size)

    def record_cache_miss(self) -> None:
        CACHE_MISSES.labels(span_name=self._span_name).inc()


class _PrometheusCachePutSpan:
    def __init__(self, span_name: str) -> None:
        self._span_name = span_name

    def record_put(self, item_size: int) -> None:
        CACHE_ITEM_SIZE.labels(span_name=self._span_name).observe(item_size)


class _PrometheusCacheRemoveSpan:
    def record_removed(self) -> None:
        pass


class _PrometheusCacheCleanupSpan:
    def record_cleanup(self, num_deleted: int) -> None:
        CACHE_CLEANUP_LAST_RUN.set_to_current_time()
        CACHE_CLEANUP_DELETED.set(num_deleted)


class _PrometheusCacheFlushSpan:
    def record_flush(self, num_flushed: int) -> None:
        CACHE_FLUSHED_ENTRIES.observe(num_flushed)


class PrometheusInstrumentation:
    """
    Prometheus-backed instrumentation for cache operations.
    """

    @contextmanager
    def start_cache_get_span(
        self, key: str, name: str | None
    ) -> Iterator[CacheGetSpan]:
        span_name = name or ""
        with CACHE_GET_DURATION.labels(span_name=span_name).time():
            yield _PrometheusCacheGetSpan(span_name)

    @contextmanager
    def start_cache_put_span(
        self, key: str, name: str | None
    ) -> Iterator[CachePutSpan]:
        span_name = name or ""
        with CACHE_PUT_DURATION.labels(span_name=span_name).time():
            yield _PrometheusCachePutSpan(span_name)

    @contextmanager
    def start_cache_remove_span(self, key: str) -> Iterator[CacheRemoveSpan]:
        with CACHE_REMOVE_DURATION.time():
            yield _PrometheusCacheRemoveSpan()

    @contextmanager
    def start_cache_cleanup_span(
        self,
    ) -> Iterator[CacheCleanupSpan]:
        yield _PrometheusCacheCleanupSpan()

    @contextmanager
    def start_cache_flush_span(
        self,
    ) -> Iterator[CacheFlushSpan]:
        with CACHE_FLUSH_DURATION.time():
            yield _PrometheusCacheFlushSpan()
