---
icon: material/rocket-launch
---

# Getting Started

!!! note

    This documentation uses [*uv*](https://docs.astral.sh/uv/) for package management and so should you.
    It's trivial, though, to translate the commands to your package manager of choice.


## Installation

*psycache* is published on [PyPI](https://pypi.org/project/psycache/), so install it with your favorite package manager:

```console
$ uv pip install psycache
```

The core package depends only on [*psycopg*](https://www.psycopg.org/).
The pool adapters are optional and each lives behind an extra.
The examples here use SQLAlchemy, so install the `sqlalchemy` extra too:

```console
$ uv pip install "psycache[sqlalchemy]"
```

!!! tip

    See [Connection Pool Adapters][] for the full list of extras and how to bring your own pool.


## Initialize the database

*psycache* keeps everything in a single [unlogged table](https://www.postgresql.org/docs/current/sql-createtable.html#SQL-CREATETABLE-UNLOGGED).
Create it once – either from Python:

```python
import psycopg

import psycache


with psycopg.connect(
    "postgresql://psycache@127.0.0.1/psycache", autocommit=True
) as conn:
    psycache.init_db(conn)
```

…or from the command line:

```console
$ python -Im psycache init-db postgresql://psycache@127.0.0.1/psycache
```

This creates the `psycache` unlogged table and an index on `expires_at`.
[`init_db()`][psycache.init_db] is idempotent, so running it again leaves existing data untouched.


## Store and retrieve

Assuming you already have a SQLAlchemy [`Engine`][sqlalchemy.engine.Engine] in your application, wrap it in a [`SQLAlchemyCachePool`][psycache.sqlalchemy.SQLAlchemyCachePool] and hand it to [`PostgresCache`][psycache.PostgresCache]:

```python
from sqlalchemy import create_engine

from psycache import PostgresCache
from psycache.sqlalchemy import SQLAlchemyCachePool


engine = create_engine("postgresql+psycopg://psycache@127.0.0.1/psycache")
cache = PostgresCache(SQLAlchemyCachePool(engine))

# Store a value with a TTL of 300 seconds.
cache.put_raw("user:alice", {"score": 42}, ttl=300)

# Retrieve it (returns None if missing or expired).
value = cache.get_raw("user:alice")
# {"score": 42}

engine.dispose()
```

That's it!
You've got a working cache.
