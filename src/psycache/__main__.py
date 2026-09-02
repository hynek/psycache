# SPDX-FileCopyrightText: 2026 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import argparse
import sys

from collections.abc import Sequence

import psycopg

from . import _sql
from ._tables import init_db


def _dump_init_db_sql(table: str) -> None:
    print(f"{_sql.create_table(table).as_string().rstrip()};")
    print(f"{_sql.create_index(table).as_string().rstrip()};")


def _do_init_db(dsn: str | None, table: str) -> int:
    try:
        if dsn is None:
            _dump_init_db_sql(table)
            return 0

        with psycopg.connect(dsn, autocommit=True) as conn:
            init_db(conn, table)
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
        "--table",
        default="psycache",
        help="Name of the cache table, optionally schema-qualified with a "
        "dot (default: %(default)s).",
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

    return _do_init_db(args.dsn, args.table)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
