# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import datetime as dt
import secrets

import psycopg
import pytest

from psycache import AsyncPostgresCache, init_db


pytestmark = pytest.mark.asyncio


async def test_raw_get_and_set(acache):
    """
    A stored dict without an expiration time is returned as sent and nothing
    else.
    """

    key = secrets.token_urlsafe()

    assert None is await acache.get_raw(key)

    await acache.put_raw(key, {"foo": "bar"}, ttl=10)

    assert {"foo": "bar"} == await acache.get_raw(key)
    assert None is await acache.get_raw(secrets.token_urlsafe())


async def test_raw_set_conflict(acache):
    """
    A second set overwrites the first. Both value and expiration time are
    updated.
    """

    key = secrets.token_urlsafe()
    await acache.put_raw(key, {"foo": "first"}, ttl=10)
    await acache.put_raw(key, {"foo": "second"}, ttl=100)

    assert {"foo": "second"} == await acache.get_raw(key)

    async with acache._pool.connect() as conn:
        cur = await conn.execute(
            "SELECT expires_at FROM psycache WHERE key = %s",
            (key,),
        )
        expires_at = (await cur.fetchone())[0]

    assert expires_at > dt.datetime.now().astimezone() + dt.timedelta(
        seconds=10
    )


async def test_remove(acache):
    """
    A deleted cache entry is not returned.
    """

    key = secrets.token_urlsafe()

    await acache.put_raw(key, {"foo": "bar"}, ttl=10)

    assert await acache.get_raw(key) is not None

    await acache.remove(key)

    assert await acache.get_raw(key) is None


async def test_schema_is_isolated(acache, db_dsn):
    """
    A cache configured with a schema uses that schema's table.
    """
    schema = "psycache_raw_async_test"

    with psycopg.connect(db_dsn, autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        conn.execute(f"CREATE SCHEMA {schema}")
        init_db(conn, schema=schema)

    schema_cache = AsyncPostgresCache(
        acache._pool,
        schema=schema,
        instrumentations=acache._instrumentations,
    )
    key = secrets.token_urlsafe()

    await acache.put_raw(key, {"schema": False}, ttl=10)
    await schema_cache.put_raw(key, {"schema": True}, ttl=10)

    assert {"schema": False} == await acache.get_raw(key)
    assert {"schema": True} == await schema_cache.get_raw(key)


async def test_cleanup_expired(acache):
    """
    Expired cache entries are deleted. Unexpired aren't touched.
    """

    gone_key = secrets.token_urlsafe()
    alive_key = secrets.token_urlsafe()
    alive_key_2 = secrets.token_urlsafe()

    await acache.put_raw(gone_key, {"foo": "bar"}, ttl=-1)
    await acache.put_raw(alive_key, {"foo": "bar"}, ttl=10)
    await acache.put_raw(alive_key_2, {"foo": "bar"}, ttl=dt.timedelta(days=1))

    assert 1 == await acache.cleanup_expired()
    assert await acache.get_raw(gone_key) is None
    assert {"foo": "bar"} == await acache.get_raw(alive_key)
    assert {"foo": "bar"} == await acache.get_raw(alive_key_2)


async def test_flush(acache):
    """
    Flushing the cache deletes all entries.
    """

    for _ in range(4):
        await acache.put_raw(secrets.token_urlsafe(), {"foo": "bar"}, ttl=10)

    assert 4 == await acache.flush()

    async with acache._pool.connect() as conn:
        cur = await conn.execute("SELECT count(*) FROM psycache")
        count = (await cur.fetchone())[0]

    assert 0 == count
