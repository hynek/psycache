# Async

*psycache* ships asyncio-native API that mirror the synchronous ones.

So, [`AsyncPostgresCache`][psycache.AsyncPostgresCache] exposes `get_raw`, `put_raw`, `remove`, `cleanup_expired`, and `flush` – all async methods with the same signatures as their synchronous counterparts.
It needs an [`AsyncCachePool`][psycache.typing.AsyncCachePool]: anything with an async `connect()` that yields a [`psycopg.AsyncConnection`][].

Two adapters are included, again, mirroring their synchronous counterparts.


## SQLAlchemy

[`AsyncSQLAlchemyCachePool`][psycache.sqlalchemy.AsyncSQLAlchemyCachePool] wraps a SQLAlchemy [`AsyncEngine`][sqlalchemy.ext.asyncio.AsyncEngine] (requires `psycache[sqlalchemy-asyncio]`):

```python
import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from psycache import AsyncPostgresCache
from psycache.sqlalchemy import AsyncSQLAlchemyCachePool


async def main() -> None:
    engine = create_async_engine(
        "postgresql+psycopg://psycache@127.0.0.1/psycache"
    )
    cache = AsyncPostgresCache(AsyncSQLAlchemyCachePool(engine))

    await cache.put_raw("my-key", {"user": "alice"}, ttl=300)
    value = await cache.get_raw("my-key")

    await engine.dispose()


asyncio.run(main())
```


## psycopg-pool

[`AsyncPsycopgCachePool`][psycache.psycopg_pool.AsyncPsycopgCachePool] wraps a [`psycopg_pool.AsyncConnectionPool`][psycopg_pool.AsyncConnectionPool] (requires `psycache[pool]`):

```python
import asyncio

from psycopg_pool import AsyncConnectionPool

from psycache import AsyncPostgresCache
from psycache.psycopg_pool import AsyncPsycopgCachePool


async def main() -> None:
    async with AsyncConnectionPool(
        "postgresql://psycache@127.0.0.1/psycache", open=False
    ) as pool:
        cache = AsyncPostgresCache(AsyncPsycopgCachePool(pool))

        await cache.put_raw("my-key", {"user": "alice"}, ttl=300)
        value = await cache.get_raw("my-key")


asyncio.run(main())
```
