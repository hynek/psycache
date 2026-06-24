# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

"""
Generic span helpers.
"""

from collections.abc import Iterator, Sequence
from contextlib import ExitStack, contextmanager

from psycache.typing import (
    CacheCleanupSpan,
    CacheFlushSpan,
    CacheGetSpan,
    CacheInstrumentation,
    CachePutSpan,
    CacheRemoveSpan,
)


class _AggregatingGetSpan:
    def __init__(self, spans: Sequence[CacheGetSpan]) -> None:
        self._spans = spans

    def record_cache_hit(self, item_size: int) -> None:
        for span in self._spans:
            span.record_cache_hit(item_size)

    def record_cache_miss(self) -> None:
        for span in self._spans:
            span.record_cache_miss()


class _AggregatingPutSpan:
    def __init__(self, spans: Sequence[CachePutSpan]) -> None:
        self._spans = spans

    def record_put(self, item_size: int) -> None:
        for span in self._spans:
            span.record_put(item_size)


class _AggregatingRemoveSpan:
    def __init__(self, spans: Sequence[CacheRemoveSpan]) -> None:
        self._spans = spans

    def record_removed(self) -> None:
        for span in self._spans:
            span.record_removed()


class _AggregatingCleanupSpan:
    def __init__(self, spans: Sequence[CacheCleanupSpan]) -> None:
        self._spans = spans

    def record_cleanup(self, num_deleted: int) -> None:
        for span in self._spans:
            span.record_cleanup(num_deleted)


class _AggregatingFlushSpan:
    def __init__(self, spans: Sequence[CacheFlushSpan]) -> None:
        self._spans = spans

    def record_flush(self, num_flushed: int) -> None:
        for span in self._spans:
            span.record_flush(num_flushed)


class NoopAnySpan:
    def record_cache_hit(self, item_size: int) -> None:
        pass

    def record_cache_miss(self) -> None:
        pass

    def record_put(self, item_size: int) -> None:
        pass

    def record_removed(self) -> None:
        pass

    def record_cleanup(self, num_deleted: int) -> None:
        pass

    def record_flush(self, num_flushed: int) -> None:
        pass


@contextmanager
def _lookup_span(
    instrumentations: Sequence[CacheInstrumentation],
    key: str,
    name: str | None,
) -> Iterator[CacheGetSpan]:
    if not instrumentations:
        yield NoopAnySpan()
        return

    with ExitStack() as stack:
        spans = [
            stack.enter_context(inst.start_cache_get_span(key, name))
            for inst in instrumentations
        ]
        yield _AggregatingGetSpan(spans)


@contextmanager
def _put_span(
    instrumentations: Sequence[CacheInstrumentation],
    key: str,
    name: str | None,
) -> Iterator[CachePutSpan]:
    if not instrumentations:
        yield NoopAnySpan()
        return

    with ExitStack() as stack:
        spans = [
            stack.enter_context(inst.start_cache_put_span(key, name))
            for inst in instrumentations
        ]
        yield _AggregatingPutSpan(spans)


@contextmanager
def _remove_span(
    instrumentations: Sequence[CacheInstrumentation],
    key: str,
) -> Iterator[CacheRemoveSpan]:
    if not instrumentations:
        yield NoopAnySpan()
        return

    with ExitStack() as stack:
        spans = [
            stack.enter_context(inst.start_cache_remove_span(key))
            for inst in instrumentations
        ]
        yield _AggregatingRemoveSpan(spans)


@contextmanager
def _cleanup_span(
    instrumentations: Sequence[CacheInstrumentation],
) -> Iterator[CacheCleanupSpan]:
    if not instrumentations:
        yield NoopAnySpan()
        return

    with ExitStack() as stack:
        spans = [
            stack.enter_context(inst.start_cache_cleanup_span())
            for inst in instrumentations
        ]
        yield _AggregatingCleanupSpan(spans)


@contextmanager
def _flush_span(
    instrumentations: Sequence[CacheInstrumentation],
) -> Iterator[CacheFlushSpan]:
    if not instrumentations:
        yield NoopAnySpan()
        return

    with ExitStack() as stack:
        spans = [
            stack.enter_context(inst.start_cache_flush_span())
            for inst in instrumentations
        ]
        yield _AggregatingFlushSpan(spans)
