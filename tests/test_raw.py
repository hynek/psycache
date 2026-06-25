# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import datetime as dt
import secrets

from psycache import PostgresCache


def test_raw_get_and_set(cache: PostgresCache):
    """
    A stored dict without an expiration time is returned as sent and nothing
    else.
    """

    key = secrets.token_urlsafe()

    assert None is cache.get_raw(key)

    cache.put_raw(key, {"foo": "bar"}, ttl=10)

    assert {"foo": "bar"} == cache.get_raw(key)
    assert None is cache.get_raw(secrets.token_urlsafe())


def test_raw_set_conflict(cache: PostgresCache):
    """
    A second set overwrites the first. Both value and expiration time are
    updated.
    """

    key = secrets.token_urlsafe()
    cache.put_raw(key, {"foo": "first"}, ttl=10)
    cache.put_raw(key, {"foo": "second"}, ttl=100)

    assert {"foo": "second"} == cache.get_raw(key)

    with cache._pool.connect() as conn:
        expires_at = conn.execute(
            "SELECT expires_at FROM psycache WHERE key = %s",
            (key,),
        ).fetchone()[0]

    assert expires_at > dt.datetime.now().astimezone() + dt.timedelta(
        seconds=10
    )


def test_remove(cache: PostgresCache):
    """
    A deleted cache entry is not returned.
    """

    key = secrets.token_urlsafe()

    cache.put_raw(key, {"foo": "bar"}, ttl=10)

    assert cache.get_raw(key) is not None

    cache.remove(key)

    assert cache.get_raw(key) is None
