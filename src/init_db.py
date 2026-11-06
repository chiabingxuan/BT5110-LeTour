"""Rebuilds the LeTour database with one command: schema, then data, then analytics views.

    python src/init_db.py               full rebuild (deletes and reloads everything)
    python src/init_db.py --views-only  recreate only the analytics views and functions
"""
import argparse
import hashlib
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql

from loading import build_tables, insert_tables, read_clean_data, validate_tables

ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT / "src" / "sql"


def db_config(dbname=None):
    return {
        "host": os.environ["DB_HOST"],
        "port": os.environ["DB_PORT"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "dbname": dbname or os.environ["DB_NAME"],
    }


def create_database_if_missing():
    name = os.environ["DB_NAME"]
    connection = psycopg2.connect(**db_config("postgres"))
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
        if cursor.fetchone() is None:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            print(f"Created database {name}")
    connection.close()


def run_file(cursor, path, quiet=False):
    cursor.execute(path.read_text(encoding="utf-8"))
    if not quiet:
        print(f"Ran {path.relative_to(ROOT)}")


def view_files():
    return [SQL_DIR / "drop_analytics.sql", *sorted((SQL_DIR / "views").glob("*.sql"))]


def views_fingerprint():
    """A hash of every analytics SQL file. Line endings are normalised so Windows and Mac checkouts agree."""
    digest = hashlib.sha256()
    for path in view_files():
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()[:16]


# The fingerprint of the installed views is kept as a comment on fn_stage_selection, so no table is added
FINGERPRINT_TARGET = "FUNCTION fn_stage_selection(int, int, text[])"


def create_views(cursor):
    for path in view_files():
        run_file(cursor, path)
    cursor.execute(f"COMMENT ON {FINGERPRINT_TARGET} IS %s", (f"letour-views:{views_fingerprint()}",))


def installed_fingerprint(cursor):
    cursor.execute("""
        SELECT obj_description(p.oid, 'pg_proc') FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public' AND p.proname = 'fn_stage_selection'
    """)
    row = cursor.fetchone()
    return (row[0] or "").removeprefix("letour-views:") if row else None


def refresh_views_if_stale(cursor):
    """Recreates the analytics views when the SQL files changed since they were installed.

    Pulling new code updates the SQL files but not the database, so the app calls this at startup.
    The race data is not touched. Returns True when the views were rebuilt.
    """
    if installed_fingerprint(cursor) == views_fingerprint():
        return False
    create_views(cursor)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--views-only", action="store_true", help="keep the data and recreate only the views")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    create_database_if_missing()

    # A single transaction, so a failed rebuild leaves the previous database intact
    with psycopg2.connect(**db_config()) as connection, connection.cursor() as cursor:
        if not args.views_only:
            tables = build_tables(*read_clean_data(ROOT / "data"))
            validate_tables(tables)
            run_file(cursor, SQL_DIR / "drop_analytics.sql")
            run_file(cursor, SQL_DIR / "drop_tables.sql")
            run_file(cursor, SQL_DIR / "schema.sql")
            insert_tables(cursor, tables)
        create_views(cursor)
    print("Database ready.")


if __name__ == "__main__":
    main()
