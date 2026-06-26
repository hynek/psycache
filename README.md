# *psycache*: *psycopg*-Backed PostgreSQL Cache

[![License: MIT](https://img.shields.io/badge/license-MIT-C06524)](https://github.com/hynek/psycache/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/Docs-Read%20the%20Docs-black)](https://psycache.hynek.me/)
[![PyPI version](https://img.shields.io/pypi/v/psycache)](https://pypi.org/project/psycache/)
[![No AI slop inside.](https://img.shields.io/badge/no-slop-purple)](https://github.com/hynek/psycache/blob/main/.github/AI_POLICY.md)


A key-value cache that stores JSON in PostgreSQL through [*psycopg*](https://www.psycopg.org/) 3, with TTL-based expiration and pluggable instrumentation.

- Sync and async ✔︎
- Type-safe ✔︎
- Adapters for [SQLAlchemy](https://www.sqlalchemy.org) and [*psycopg-pool*](https://www.psycopg.org/psycopg3/docs/api/pool.html) ✔︎

---

*psycache* uses an [unlogged table](https://www.postgresql.org/docs/current/sql-createtable.html#SQL-CREATETABLE-UNLOGGED) for performance and stores values as [JSONB](https://www.postgresql.org/docs/current/datatype-json.html) for versatility.

It's a great fit when you already have PostgreSQL and need a fast cache without introducing another piece of infrastructure like Redis.
For example, you can safely share a SQLAlchemy [`Engine`](https://docs.sqlalchemy.org/en/20/core/connections.html#sqlalchemy.engine.Engine) (or [`AsyncEngine`](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.AsyncEngine)) with *psycache*.


## Quick Start

Let's hitch-hike on a SQLAlchemy engine as a quick example!

First, install *psycache* from PyPI with the `sqlalchemy` extra:

```console
$ uv pip install "psycache[sqlalchemy]"
```

Initialize the cache table once[^cli] then store and retrieve JSON with a TTL:

[^cli]: `python -Im psycache init-db <dsn>` does the same from the shell.
  Add `--schema <schema>` to use a non-default PostgreSQL schema.
  Omit `<dsn>` to print the SQL.

```python
import psycopg

from sqlalchemy import create_engine

import psycache

from psycache import PostgresCache
from psycache.sqlalchemy import SQLAlchemyCachePool


with psycopg.connect(
    "postgresql://psycache@127.0.0.1/psycache", autocommit=True
) as conn:
    psycache.init_db(conn)

engine = create_engine("postgresql+psycopg://psycache@127.0.0.1/psycache")
cache = PostgresCache(SQLAlchemyCachePool(engine))

cache.put_raw("user:alice", {"score": 42}, ttl=300)
value = cache.get_raw("user:alice")
# {"score": 42}

engine.dispose()
```


## Documentation

Full documentation lives at **<https://psycache.hynek.me/>**.


<!-- --8<-- [start:credits] -->
## Credits

*psycache* is written by [Hynek Schlawack](https://hynek.me/) and distributed under the terms of the [MIT license](https://choosealicense.com/licenses/mit/).

The development is kindly supported by my employer [Variomedia AG](https://www.variomedia.de/) and all my fabulous [GitHub Sponsors](https://github.com/sponsors/hynek).
<!-- --8<-- [end:credits] -->
