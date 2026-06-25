# psycache

*A psycopg-backed PostgreSQL cache.*

---

**psycache** is a simple key-value cache that stores JSON in PostgreSQL through [*psycopg*](https://www.psycopg.org/psycopg3/docs/) 3, with TTL-based expiration, and pluggable instrumentation.

- **Sync and async**: [`PostgresCache`][psycache.PostgresCache] and a fully async [`AsyncPostgresCache`][psycache.AsyncPostgresCache] that mirrors its API.

- **Type-safe**: fully typed, checked using Mypy, *ty*, Pyrefly, and Pyright.

- **Bring your own pool**: first-class adapters for [SQLAlchemy](https://www.sqlalchemy.org) and [*psycopg-pool*](https://www.psycopg.org/psycopg3/docs/api/pool.html), or implement a tiny protocol (*one* method!) yourself.


## Why PostgreSQL?

Modern PostgreSQL on modern servers is fast enough for almost everyone's use cases.

*psycache* stores values as [JSONB](https://www.postgresql.org/docs/current/datatype-json.html) in an [unlogged table](https://www.postgresql.org/docs/current/sql-createtable.html#SQL-CREATETABLE-UNLOGGED).
Unlogged tables skip the [write-ahead log](https://www.postgresql.org/docs/current/wal.html) for speed, while JSONB keeps values flexible and queryable.

It's a great fit when you **already run PostgreSQL** and want a fast cache without operating another piece of infrastructure like Redis.
You can even share an existing SQLAlchemy [`Engine`][sqlalchemy.engine.Engine] (or [`AsyncEngine`][sqlalchemy.ext.asyncio.AsyncEngine]) with *psycache*, so the cache rides on the connections you already have.


## Get started

<div class="grid cards" markdown>

- :material-rocket-launch: **[Getting Started](getting-started.md)**: install *psycache*, initialize the table, and store your first value.
- :material-book-open-variant: **[Raw Queries][]**: Our low-level API: `get_raw`, `put_raw`, TTLs, and instrumentation span names.
- :material-cog: **[Connection Pool Adapters][]**: wire up SQLAlchemy, *psycopg-pool*, or your own pool.
- :material-beach: **[Quality of Life][]**: embrace the simple life.

</div>


--8<-- "README.md:credits"
