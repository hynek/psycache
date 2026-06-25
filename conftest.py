# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import importlib.util

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from doctest import ELLIPSIS

import attrs
import psycopg
import pytest

from sybil import Sybil
from sybil.parsers import markdown

from psycache import AsyncPostgresCache, PostgresCache, init_db
from psycache.instrumentation.prometheus import PrometheusInstrumentation
from psycache.instrumentation.sentry import SentryInstrumentation


collect_ignore = [
    f"tests/test_{name}.py"
    for name in ["sqlalchemy", "psycopg_pool"]
    if importlib.util.find_spec(name) is None
]

# The docs are CommonMark/Material (Zensical), so use the Markdown parsers.
# Executable examples use plain ```python fences; illustrative snippets are
# preceded by an HTML comment <!-- skip: next -->.
pytest_collect_file = Sybil(
    parsers=[
        markdown.PythonCodeBlockParser(doctest_optionflags=ELLIPSIS),
        markdown.SkipParser(),
    ],
    patterns=["*.md"],
    fixtures=["psycache_database"],
).pytest()


@pytest.fixture(name="db_dsn", scope="session")
def _db_dsn():
    return "postgresql://psycache@127.0.0.1/psycache"


@pytest.fixture(name="psycache_database", scope="session", autouse=True)
def _psycache_database(db_dsn) -> None:
    """
    At the beginning of each test run, re-create the whole database.
    """
    with psycopg.connect(
        "postgresql://postgres@127.0.0.1/postgres", autocommit=True
    ) as conn:
        conn.execute("DROP DATABASE IF EXISTS psycache WITH (FORCE)")
        conn.execute("DROP ROLE IF EXISTS psycache")
        conn.execute("CREATE ROLE psycache LOGIN")
        conn.execute(
            "CREATE DATABASE psycache"
            " OWNER psycache TEMPLATE template0 LOCALE 'en_US.UTF-8'"
        )

    with psycopg.connect(db_dsn, autocommit=True) as conn:
        init_db(conn)


@pytest.fixture(autouse=True)
def _clean_tables(db_dsn) -> None:
    """
    At the beginning of each test case, wipe the table.
    """
    with psycopg.connect(db_dsn, autocommit=True) as conn:
        conn.execute("TRUNCATE psycache")


_INSTRUMENTATIONS = [
    (),
    (SentryInstrumentation(), PrometheusInstrumentation()),
]


@attrs.frozen
class _RawCachePool:
    """
    A minimal CachePool that opens a psycopg connection per checkout.

    Needs nothing beyond psycopg, so the core cache is exercised without any
    optional pool dependency.
    """

    dsn: str

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        """
        Yield a fresh autocommit psycopg connection.
        """
        with psycopg.connect(self.dsn, autocommit=True) as conn:
            yield conn


@pytest.fixture(
    name="cache",
    params=_INSTRUMENTATIONS,
    ids=["none", "both"],
)
def _cache(request: pytest.FixtureRequest, db_dsn: str):
    return PostgresCache(_RawCachePool(db_dsn), instrumentations=request.param)


@attrs.frozen
class _RawAsyncCachePool:
    """
    A minimal AsyncCachePool that opens a psycopg connection per checkout.
    """

    dsn: str

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[psycopg.AsyncConnection]:
        """
        Yield a fresh autocommit psycopg async connection.
        """
        conn = await psycopg.AsyncConnection.connect(self.dsn, autocommit=True)
        try:
            yield conn
        finally:
            await conn.close()


@pytest.fixture(
    name="acache",
    params=_INSTRUMENTATIONS,
    ids=["none", "both"],
)
def _acache(request: pytest.FixtureRequest, db_dsn):
    return AsyncPostgresCache(
        _RawAsyncCachePool(db_dsn), instrumentations=request.param
    )
