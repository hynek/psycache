---
icon: material/cog
---


# Connection Pool Adapters

[`PostgresCache`][psycache.PostgresCache] doesn't open connections itself.
It needs an implementation for the [`psycache.typing.CachePool`][] [`Protocol`][typing.Protocol]: anything with a `connect()` context manager that yields a [`psycopg.Connection`][].

The shipped pool adapters are optional and each lives behind a packaging extra; the cache itself needs only *psycopg*.

Pick the one that matches the infrastructure you already have.


## SQLAlchemy

[`SQLAlchemyCachePool`][psycache.sqlalchemy.SQLAlchemyCachePool] wraps a SQLAlchemy [`Engine`][sqlalchemy.engine.Engine] (requires `psycache[sqlalchemy]`).
This lets the cache ride on the very same engine – and therefore the same pool – that the rest of your application already uses:

```python
from sqlalchemy import create_engine

from psycache import PostgresCache
from psycache.sqlalchemy import SQLAlchemyCachePool


engine = create_engine("postgresql+psycopg://psycache@127.0.0.1/psycache")
cache = PostgresCache(SQLAlchemyCachePool(engine))

engine.dispose()
```


## psycopg-pool

[`PsycopgCachePool`][psycache.psycopg_pool.PsycopgCachePool] wraps a [`psycopg_pool.ConnectionPool`][] (requires `psycache[pool]`):

```python
from psycopg_pool import ConnectionPool

from psycache import PostgresCache
from psycache.psycopg_pool import PsycopgCachePool


with ConnectionPool(
    "postgresql://psycache@127.0.0.1/psycache", open=False
) as pool:
    cache = PostgresCache(PsycopgCachePool(pool))
```


## Your own pool

If neither adapter fits, implement the [`psycache.typing.CachePool`][] protocol directly.
All it requires is a `connect()` context manager that yields a [`psycopg.Connection`][]:

```python
from collections.abc import Iterator
from contextlib import contextmanager

import attrs
import psycopg


@attrs.frozen
class MyCachePool:
    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]: ...
```
