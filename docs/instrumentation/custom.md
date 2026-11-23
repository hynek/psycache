# Custom Instrumentation

The bundled [Prometheus][prometheus] and [Sentry][sentry] providers are nothing special: they implement the [`CacheInstrumentation`][psycache.typing.CacheInstrumentation] protocol.
You can write your own to feed any other system.

A provider returns a context manager for each kind of operation.
Each one yields a *span* object on which psycache records what happened – a cache hit, the item size, the number of flushed entries, and so on.
The full set of span protocols ([`CacheGetSpan`][psycache.typing.CacheGetSpan]), [`CachePutSpan`][psycache.typing.CachePutSpan], [`CacheRemoveSpan`][psycache.typing.CacheRemoveSpan], [`CacheFlushSpan`][psycache.typing.CacheFlushSpan], and [`CacheCleanupSpan`][psycache.typing.CacheCleanupSpan]) is in the [types API reference](../api-types.md).

A minimal, do-nothing provider looks like this:

<!-- skip: next -->
```python
from collections.abc import Generator
from contextlib import contextmanager


class MyInstrumentation:
    @contextmanager
    def start_cache_get_span(
        self, key: str, name: str | None
    ) -> Generator[CacheGetSpan]: ...

    @contextmanager
    def start_cache_put_span(
        self, key: str, name: str | None
    ) -> Generator[CachePutSpan]: ...

    @contextmanager
    def start_cache_remove_span(
        self, key: str
    ) -> Generator[CacheRemoveSpan]: ...

    @contextmanager
    def start_cache_cleanup_span(self) -> Generator[CacheCleanupSpan]: ...

    @contextmanager
    def start_cache_flush_span(self) -> Generator[CacheFlushSpan]: ...
```

Because the protocol is [structural](https://typing.python.org/en/latest/spec/protocol.html), you don't need to inherit from anything.
Any object with these methods qualifies, and type checkers will verify the fit where you pass it to [`PostgresCache`](psycache.PostgresCache].
