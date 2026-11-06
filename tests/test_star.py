"""Task 4: the star schema must hold exactly the normalised data, and each paired query must agree."""
import os
from pathlib import Path

import psycopg2
import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
QUERIES = ROOT / "src" / "sql" / "queries"
load_dotenv(ROOT / ".env")


@pytest.fixture(scope="module")
def cur():
    connection = psycopg2.connect(
        host=os.environ["DB_HOST"], port=os.environ["DB_PORT"], dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
    )
    yield connection.cursor()
    connection.close()


def one(cur, query):
    cur.execute(query)
    return cur.fetchone()[0]


@pytest.mark.parametrize("star_table, source_table", [
    ("dim_country", "countries"), ("dim_team", "teams"), ("dim_rider", "riders"),
    ("dim_stage", "stages"), ("fact_results", "stage_results"),
])
def test_star_tables_hold_every_source_row(cur, star_table, source_table):
    assert one(cur, f"SELECT COUNT(*) FROM star.{star_table}") == one(cur, f"SELECT COUNT(*) FROM {source_table}")


def test_stored_adjusted_time_matches_its_definition(cur):
    assert one(cur, "SELECT COUNT(*) FROM star.fact_results WHERE adjusted_time <> finish_time - time_bonus + time_penalty") == 0
    assert one(cur, "SELECT SUM(adjusted_time) FROM star.fact_results") == \
        one(cur, "SELECT SUM(finish_time - time_bonus + time_penalty) FROM stage_results")


def test_date_dimension_covers_the_race(cur):
    assert one(cur, "SELECT COUNT(*) FROM star.dim_date") == 23  # 5 to 27 July 2025, rest days included
    assert one(cur, "SELECT COUNT(*) FROM star.fact_results f LEFT JOIN star.dim_date d USING (date_key) WHERE d.date_key IS NULL") == 0


@pytest.mark.parametrize("stem", sorted(p.stem for p in (QUERIES / "normalized").glob("*.sql")))
def test_paired_queries_return_identical_rows(cur, stem):
    results = {}
    for schema in ("normalized", "star"):
        cur.execute((QUERIES / schema / f"{stem}.sql").read_text(encoding="utf-8"))
        results[schema] = cur.fetchall()
    assert results["normalized"] == results["star"]
    assert results["star"]


def test_star_gc_matches_the_official_winner(cur):
    cur.execute((QUERIES / "star" / "q1_gc.sql").read_text(encoding="utf-8"))
    assert cur.fetchone()[0] == "Tadej Pogacar"
