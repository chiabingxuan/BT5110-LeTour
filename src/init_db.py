"""Rebuilds the LeTour database with one command: schema, then data, then analytics views.

    python src/init_db.py               full rebuild (deletes and reloads everything)
    python src/init_db.py --views-only  recreate only the analytics views and functions
"""
import argparse
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


def run_file(cursor, path):
    cursor.execute(path.read_text(encoding="utf-8"))
    print(f"Ran {path.relative_to(ROOT)}")


def create_views(cursor):
    run_file(cursor, SQL_DIR / "drop_analytics.sql")
    for path in sorted((SQL_DIR / "views").glob("*.sql")):
        run_file(cursor, path)


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
