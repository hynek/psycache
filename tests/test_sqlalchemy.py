# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import secrets

from sqlalchemy import create_engine

from psycache import PostgresCache
from psycache.sqlalchemy import SQLAlchemyCachePool


def test_sync_cache(sqla_url):
    """
    SQLAlchemyCachePool round-trips through the whole cache API.
    """
    engine = create_engine(sqla_url)
    cache = PostgresCache(SQLAlchemyCachePool(engine))

    key = secrets.token_urlsafe()

    assert cache.get_raw(key) is None

    cache.put_raw(key, {"foo": "bar"}, ttl=10)

    assert {"foo": "bar"} == cache.get_raw(key)

    cache.remove(key)

    assert cache.get_raw(key) is None

    cache.put_raw("gone", {"v": 1}, ttl=-1)

    assert 1 == cache.cleanup_expired()

    cache.put_raw("here", {"v": 2}, ttl=10)

    assert 1 == cache.flush()

    engine.dispose()
