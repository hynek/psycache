# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from psycopg import sql


def _cache_table(table: str) -> sql.Identifier:
    """
    Turn a dotted *table* name into a (schema-qualified) identifier.
    """
    parts = table.split(".")
    if not all(parts):
        msg = "the cache-table name must not be empty or have empty parts"
        raise ValueError(msg)

    return sql.Identifier(*parts)


def create_table(table: str) -> sql.Composed:
    return sql.SQL("""\
CREATE UNLOGGED TABLE IF NOT EXISTS {} (
    key text PRIMARY KEY,
    value jsonb NOT NULL,
    expires_at timestamptz NOT NULL
)
""").format(_cache_table(table))


def create_index(table: str) -> sql.Composed:
    cache_table = _cache_table(table)

    return sql.SQL("""\
CREATE INDEX IF NOT EXISTS {}
    ON {} (expires_at)
""").format(
        sql.Identifier(f"ix_{table.rsplit('.', 1)[-1]}_expires_at"),
        cache_table,
    )


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

    def __init__(self, table: str) -> None:
        cache_table = _cache_table(table)

        self.get = sql.SQL("""\
SELECT value, pg_column_size(value)
FROM {}
WHERE key = %s
  AND expires_at > statement_timestamp()
""").format(cache_table)

        self.put = sql.SQL("""\
INSERT INTO {} (key, value, expires_at)
VALUES (%s, %s, %s)
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    expires_at = EXCLUDED.expires_at
RETURNING pg_column_size(value)
""").format(cache_table)

        self.remove = sql.SQL("""\
DELETE FROM {}
WHERE key = %s
""").format(cache_table)

        self.cleanup_expired = sql.SQL("""\
DELETE FROM {}
WHERE expires_at < statement_timestamp()
""").format(cache_table)

        self.flush = sql.SQL("""\
DELETE FROM {}
""").format(cache_table)
