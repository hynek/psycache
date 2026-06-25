# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

"""
Integration with SQLAlchemy.
"""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

import psycopg

from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine


class SQLAlchemyCachePool:
    """
    A cache pool based on a SQLAlchemy engine.

    Args:
        engine: The SQLAlchemy engine to use.
    """

    __slots__ = ("_engine",)

    _engine: Engine

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        with self._engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as conn:
            yield conn.connection  # type: ignore[misc]  # ty: ignore[invalid-yield]


class AsyncSQLAlchemyCachePool:
    """
    A cache pool based on a SQLAlchemy async engine.
    """

    __slots__ = ("_engine",)

    _engine: AsyncEngine

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[psycopg.AsyncConnection]:
        async with self._engine.connect() as sa_conn:
            conn = await sa_conn.execution_options(
                isolation_level="AUTOCOMMIT"
            )
            raw = await conn.get_raw_connection()

            yield raw.driver_connection  # type: ignore[misc]  # ty: ignore[invalid-yield]
