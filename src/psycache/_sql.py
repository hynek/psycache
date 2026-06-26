# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from psycopg import sql


_TABLE_NAME = "psycache"
_EXPIRES_AT_INDEX_NAME = "ix_psycache_expires_at"


def _cache_table(schema: str | None = None) -> sql.Identifier:
    if schema == "":
        msg = "schema must not be empty"
        raise ValueError(msg)

    if schema is None:
        return sql.Identifier(_TABLE_NAME)

    return sql.Identifier(schema, _TABLE_NAME)


def create_table(schema: str | None = None) -> sql.Composed:
    return sql.SQL("""\
CREATE UNLOGGED TABLE IF NOT EXISTS {} (
    key text PRIMARY KEY,
    value jsonb NOT NULL,
    expires_at timestamptz NOT NULL
)
""").format(_cache_table(schema))


def create_index(schema: str | None = None) -> sql.Composed:
    return sql.SQL("""\
CREATE INDEX IF NOT EXISTS {}
    ON {} (expires_at)
""").format(sql.Identifier(_EXPIRES_AT_INDEX_NAME), _cache_table(schema))


class CacheQueries:
    """
    SQL queries for a cache table.
    """

    __slots__ = ("cleanup_expired", "flush", "get", "put", "remove")

    cleanup_expired: sql.Composed
    flush: sql.Composed
    get: sql.Composed
    put: sql.Composed
    remove: sql.Composed

    def __init__(self, schema: str | None) -> None:
        table = _cache_table(schema)

        self.get = sql.SQL("""\
SELECT value, pg_column_size(value)
FROM {}
WHERE key = %s
  AND expires_at > statement_timestamp()
""").format(table)

        self.put = sql.SQL("""\
INSERT INTO {} (key, value, expires_at)
VALUES (%s, %s, %s)
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    expires_at = EXCLUDED.expires_at
RETURNING pg_column_size(value)
""").format(table)

        self.remove = sql.SQL("""\
DELETE FROM {}
WHERE key = %s
""").format(table)

        self.cleanup_expired = sql.SQL("""\
DELETE FROM {}
WHERE expires_at < statement_timestamp()
""").format(table)

        self.flush = sql.SQL("""\
DELETE FROM {}
""").format(table)


DEFAULT_QUERIES = CacheQueries(None)
