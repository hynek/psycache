# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import argparse
import sys

from collections.abc import Sequence

import psycopg

from . import _sql
from ._tables import init_db


def _dump_init_db_sql(schema: str | None = None) -> None:
    print(f"{_sql.create_table(schema).as_string().rstrip()};")
    print(f"{_sql.create_index(schema).as_string().rstrip()};")


def _do_init_db(dsn: str | None, schema: str | None = None) -> int:
    try:
        if dsn is None:
            _dump_init_db_sql(schema)
            return 0

        with psycopg.connect(dsn, autocommit=True) as conn:
            init_db(conn, schema=schema)
    except (ValueError, psycopg.Error) as e:
        print(f"psycache: init-db failed: {e}", file=sys.stderr)
        return 1

    print("psycache: initialized the cache table.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m psycache",
        description="Maintenance commands for psycache.",
    )
    subparsers = parser.add_subparsers(required=True)

    init_db_parser = subparsers.add_parser(
        "init-db",
        help="Create the psycache table and index.",
        description="Create the psycache table and index in the database "
        "identified by DSN, or print the SQL to stdout if DSN is omitted.",
    )
    init_db_parser.add_argument(
        "--schema",
        help="PostgreSQL schema in which to create the cache table.",
    )
    init_db_parser.add_argument(
        "dsn",
        nargs="?",
        metavar="DSN",
        help="A libpq connection string, e.g. postgresql://user@host/db. "
        "If omitted, print the SQL to stdout.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    return _do_init_db(args.dsn, schema=args.schema)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
