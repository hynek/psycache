# *psycache*: *psycopg*-Backed PostgreSQL Cache

[![License: MIT](https://img.shields.io/badge/license-MIT-C06524)](https://github.com/hynek/argon2-cffi-bindings/blob/main/LICENSE)
[![No AI slop inside.](https://img.shields.io/badge/no-slop-purple)](https://github.com/hynek/argon2-cffi-bindings/blob/main/.github/AI_POLICY.md)


A simple key-value cache that stores JSON in PostgreSQL through [*psycopg*](https://www.psycopg.org/) 3, with TTL-based expiration and pluggable instrumentation.

- Sync and async ✔︎
- Type-safe ✔︎
- Adapters for [SQLAlchemy](https://www.sqlalchemy.org) and [*psycopg-pool*](https://www.psycopg.org/psycopg3/docs/api/pool.html) ✔︎

---

*psycache* uses an [unlogged table](https://www.postgresql.org/docs/current/sql-createtable.html#SQL-CREATETABLE-UNLOGGED) for performance and stores values as [JSONB](https://www.postgresql.org/docs/current/datatype-json.html) for versatility.

It's a great fit when you already have PostgreSQL and need a fast cache without introducing another infrastructure parts like Redis.
For example, you can safely share a SQLAlchemy [`Engine`](https://docs.sqlalchemy.org/en/20/core/connections.html#sqlalchemy.engine.Engine) (or [`AsyncEngine`](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.AsyncEngine)) with *psycache*.


## Setup

Install the `psycache` package from PyPI.
If you plan to use it with SQLAlchemy like in the following example, install the `sqlalchemy` extra (for example, `uv pip install psycache[sqlalchemy]`).

Initialize the database table either programmatically:

```python
import psycopg, psycache

with psycopg.connect("postgresql://psycache@127.0.0.1/psycache", autocommit=True) as conn:
    psycache.init_db(conn)
```

Or from the command line:

```console
$ python -m psycache init-db postgresql://psycache@127.0.0.1/psycache
```

This creates the `psycache` unlogged table and an index on `expires_at`.


## Basic Usage

Assuming you already have a SQLAlchemy `Engine` in your application, you can use `SQLAlchemyCachePool` to adapt it for use with `PostgresCache` and have a very fast cache without any further steps:

```python
from psycache import PostgresCache
from psycache.sqlalchemy import SQLAlchemyCachePool

from sqlalchemy import create_engine

engine = create_engine("postgresql+psycopg://psycache@127.0.0.1/psycache")
cache = PostgresCache(SQLAlchemyCachePool(engine))

# Store a value with a TTL of 300 seconds.
cache.put_raw("user:alice", {"score": 42}, ttl=300)

# Retrieve it (returns None if missing or expired).
value = cache.get_raw("user:alice")
# {"score": 42}
```

You can also pass a `datetime.timedelta` to `ttl`:

```python
import datetime as dt

cache.put_raw("other-key", {"data": "value"}, ttl=dt.timedelta(hours=1))
```

Both `get_raw` and `put_raw` accept an optional *span_name* argument that is used by instrumentation.
Sentry uses it as the span name and Prometheus adds it as a label.

```python
cache.put_raw(
    "user:alice", {"name": "alice"}, ttl=300, span_name="store user score"
)
value = cache.get_raw("user:alice", span_name="look up user score")
```

*psycache* ignores expired keys, but you still need ways to delete keys manually:

```python
# Remove a single key.
cache.remove("user:alice")

# Delete all expired entries.
num_deleted = cache.cleanup_expired()

# Delete everything.
num_flushed = cache.flush()

engine.dispose()
```


### Higher level

In practice, you don't want to sling raw dictionaries and remember to add span names.
So, wrap the cache in your own class to store and retrieve structured data:

```python
from dataclasses import dataclass
from typing import Self

from psycache import PostgresCache
from psycache.sqlalchemy import SQLAlchemyCachePool
from sqlalchemy import Engine

@dataclass
class UserScore:
    name: str
    score: int


class UserCache:
    @classmethod
    def from_engine(cls, engine: Engine, *, ttl: int = 300) -> Self:
        return cls(PostgresCache(SQLAlchemyCachePool(engine)), ttl)

    def __init__(self, cache: PostgresCache, ttl: int) -> None:
        self._raw_cache = cache
        self._ttl = ttl

    def look_up_user(self, user_name: str) -> UserScore | None:
        data = self._raw_cache.get_raw(
            f"user:{user_name}",
            span_name="look up user score",
        )
        if data is None:
            return None

        return UserScore(name=user_name, score=data["score"])

    def store_user(self, user: UserScore) -> None:
        self._raw_cache.put_raw(
            f"user:{user.name}", {"score": user.score},
            ttl=self._ttl,
            span_name="store user score",
        )
```

Packages like [*cattrs*](https://cattrs.org/) or [Pydantic](https://docs.pydantic.dev/) can reduce this boilerplate to a single line even for more complex models.


## Connection Pool

`PostgresCache` needs a `CachePool`: anything with a `connect()` method that yields a `psycopg.Connection`.
The pool adapters are optional and each lives behind an extra; the cache itself needs only `psycopg`.

`SQLAlchemyCachePool` wraps a SQLAlchemy `Engine` (requires `psycache[sqlalchemy]`):

```python
from psycache.sqlalchemy import SQLAlchemyCachePool

pool = SQLAlchemyCachePool(engine)
cache = PostgresCache(pool)
```

`PsycopgCachePool` wraps a `psycopg_pool.ConnectionPool` (requires `psycache[pool]`):

```python
from psycopg_pool import ConnectionPool
from psycache.psycopg_pool import PsycopgCachePool


with ConnectionPool("postgresql://psycache@127.0.0.1/psycache") as pool:
    cache = PostgresCache(PsycopgCachePool(pool))
```

Or implement the `psycache.typing.CachePool` protocol directly:

```python
from collections.abc import Iterator
from contextlib import contextmanager

import attrs


@attrs.frozen
class MyCachePool:
    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]: ...
```


## Cleanup

For sync pools, *psycache* comes with `PostgresCache.start_cleanup_thread()` which starts a daemon thread that periodically deletes expired cache entries.

It can be used as a context manager to automatically stop the cleanup thread:

```python
with cache.start_cleanup_thread(interval=60):
    ...
```

Or it can be stopped manually via the returned `CleanupService`'s `stop()` method:

```python
# Or, to manage the lifecycle manually:
svc = cache.start_cleanup_thread(interval=60)
try:
    ...
finally:
    svc.stop()
```


## Async

*psycache* also ships an asyncio-native API.
`AsyncPostgresCache` mirrors `PostgresCache`, but every operation is a coroutine.
It needs an `AsyncCachePool` (the `psycache.typing.AsyncCachePool` protocol): anything with an async `connect()` that yields a `psycopg.AsyncConnection`.

Two adapters are included.

`AsyncSQLAlchemyCachePool` (`psycache.sqlalchemy`) wraps a SQLAlchemy `AsyncEngine` (requires `psycache[sqlalchemy-asyncio]`):

```python
from sqlalchemy.ext.asyncio import create_async_engine

from psycache import AsyncPostgresCache
from psycache.sqlalchemy import AsyncSQLAlchemyCachePool


engine = create_async_engine("postgresql+psycopg://psycache@127.0.0.1/psycache")
cache = AsyncPostgresCache(AsyncSQLAlchemyCachePool(engine))
```

`AsyncPsycopgCachePool` (`psycache.psycopg_pool`) wraps a psycopg `psycopg_pool.AsyncConnectionPool` (requires `psycache[pool]`):

```python
import asyncio

from psycopg_pool import AsyncConnectionPool

from psycache import AsyncPostgresCache
from psycache.psycopg_pool import AsyncPsycopgCachePool


async def main() -> None:
    async with AsyncConnectionPool(
        "postgresql://psycache@127.0.0.1/psycache"
    ) as pool:
        cache = AsyncPostgresCache(AsyncPsycopgCachePool(pool))

        await cache.put_raw("my-key", {"user": "alice"}, ttl=300)
        value = await cache.get_raw("my-key")


asyncio.run(main())
```

---

`AsyncPostgresCache` exposes `get_raw`, `put_raw`, `remove`, `cleanup_expired`, and `flush` – all coroutines with the same signatures as their synchronous counterparts, and it accepts the same `instrumentations`.


### Async cleanup

For async pools, use `AsyncPostgresCache.start_cleanup_task()` inside a running event loop.

It starts an `asyncio.Task` that periodically deletes expired cache entries.
It can be used as an async context manager to automatically stop the cleanup task, or it can be stopped manually via the returned `AsyncCleanupService`'s `stop()` method.

```python
async def main():
    async with cache.start_cleanup_task(interval=60):
        ...

# Or, to manage the lifecycle manually:
async def main():
    svc = cache.start_cleanup_task(interval=60)
    try:
        ...
    finally:
        await svc.stop()
```


## Instrumentation

*psycache* has pluggable instrumentation for observability.
Pass one or more providers to the `instrumentations` parameter:

```python
from psycache import PostgresCache
from psycache.instrumentation.sentry import SentryInstrumentation
from psycache.instrumentation.prometheus import PrometheusInstrumentation

cache = PostgresCache(
    pool,
    instrumentations=(
        SentryInstrumentation(),
        PrometheusInstrumentation(),
    ),
)
```


### Prometheus

`PrometheusInstrumentation` (`psycache.instrumentation.prometheus`) exports the following metrics:

| Metric | Type | Labels | Description |
| --- | --- | --- | --- |
| `psycache_hits_total` | Counter | `span_name` | Cache hits |
| `psycache_misses_total` | Counter | `span_name` | Cache misses |
| `psycache_get_duration_seconds` | Histogram | `span_name` | Get operation latency |
| `psycache_put_duration_seconds` | Histogram | `span_name` | Put operation latency |
| `psycache_remove_duration_seconds` | Histogram | | Remove operation latency |
| `psycache_flush_duration_seconds` | Histogram | | Flush operation latency |
| `psycache_item_size_bytes` | Histogram | `span_name` | Size of cache items (from `pg_column_size`) |
| `psycache_flushed_entries` | Histogram | | Entries removed per flush |
| `psycache_cleanup_last_run_timestamp_seconds` | Gauge | | Timestamp of last cleanup |
| `psycache_cleanup_deleted_entries` | Gauge | | Entries removed in last cleanup |

The `span_name` label is set from the `span_name` argument to `get_raw()` and `put_raw()`. It defaults to `""` when not provided.

Requires the `prometheus` extra (`uv pip install psycache[prometheus]`).


### Sentry

`SentryInstrumentation` (`psycache.instrumentation.sentry`) creates [Sentry cache spans](https://docs.sentry.io/platforms/python/tracing/instrumentation/custom-instrumentation/caches-module/) for `get`, `put`, `remove`, and `flush` operations, recording `cache.hit`, `cache.item_size`, and `cache.key` data.
The `span_name` argument to `get_raw()` and `put_raw()` is used as the Sentry span name (defaults to `"psycache get"` / `"psycache put"`).

Requires the `sentry` extra (`uv pip install psycache[sentry]`).


### Custom Instrumentation

You can write your own provider by implementing the `psycache.typing.CacheInstrumentation` protocol.


## Credits

*psycache* is written by [Hynek Schlawack](https://hynek.me/) and distributed under the terms of the [MIT license](https://choosealicense.com/licenses/mit/).

The development is kindly supported by my employer [Variomedia AG](https://www.variomedia.de/) and all my fabulous [GitHub Sponsors](https://github.com/sponsors/hynek).
