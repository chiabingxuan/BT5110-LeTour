"""Task 4: runs each representative query on the normalised and the star schema and compares them.

    python src/benchmark.py            50 timed runs per query (after 5 warm-up runs)
    python src/benchmark.py --runs 200

For each pair it checks that both schemas return identical rows, then records PostgreSQL's own
planning and execution times from EXPLAIN (ANALYZE), plus simple complexity measures of the SQL.
Results are written to docs/task4/benchmark.csv and docs/task4/benchmark.md.
"""
import argparse
import csv
import json
import os
import re
import statistics
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
QUERIES = ROOT / "src" / "sql" / "queries"
OUT = ROOT / "docs" / "task4"
NAMES = {
    "q1_gc": "Q1 Cumulative time per rider (GC)",
    "q2_best_team": "Q2 Best team classification",
    "q3_stage_performance": "Q3 Stage-by-stage performance",
    "q4_speed_cube": "Q4 Speed roll-up by type and nation",
}


def complexity(sql):
    """Counts that show how much a query has to say: joins, tables touched, lines of SQL."""
    body = "\n".join(line for line in sql.splitlines() if line.strip() and not line.strip().startswith("--"))
    tables = set(re.findall(r"\b(?:FROM|JOIN)\s+([a-z_.]+)", body, flags=re.IGNORECASE)) - {"ranked"}
    return {"joins": len(re.findall(r"\bJOIN\b", body, flags=re.IGNORECASE)), "tables": len(tables), "lines": len(body.splitlines())}


def timed(cursor, sql, runs):
    planning, execution = [], []
    for i in range(runs + 5):
        cursor.execute("EXPLAIN (ANALYZE, FORMAT JSON) " + sql)
        plan = cursor.fetchone()[0]
        plan = plan[0] if isinstance(plan, list) else json.loads(plan)[0]
        if i >= 5:  # the first runs warm the caches
            planning.append(plan["Planning Time"])
            execution.append(plan["Execution Time"])
    return planning, execution


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=50)
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    connection = psycopg2.connect(
        host=os.environ["DB_HOST"], port=os.environ["DB_PORT"], dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
    )
    cursor = connection.cursor()
    cursor.execute("SELECT version()")
    version = cursor.fetchone()[0].split(" on ")[0]

    rows = []
    for stem, title in NAMES.items():
        result = {"query": title}
        outputs = {}
        for schema in ("normalized", "star"):
            sql = (QUERIES / schema / f"{stem}.sql").read_text(encoding="utf-8")
            cursor.execute(sql)
            outputs[schema] = cursor.fetchall()
            planning, execution = timed(cursor, sql, args.runs)
            stats = complexity(sql)
            result.update({
                f"{schema}_rows": len(outputs[schema]),
                f"{schema}_joins": stats["joins"],
                f"{schema}_tables": stats["tables"],
                f"{schema}_lines": stats["lines"],
                f"{schema}_planning_ms": round(statistics.median(planning), 3),
                f"{schema}_execution_ms": round(statistics.median(execution), 3),
                f"{schema}_execution_p95_ms": round(sorted(execution)[int(0.95 * (len(execution) - 1))], 3),
            })
        result["same_rows"] = outputs["normalized"] == outputs["star"]
        rows.append(result)
        print(f"{title}: normalised {result['normalized_execution_ms']} ms, star {result['star_execution_ms']} ms, "
              f"same rows: {result['same_rows']}")

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "benchmark.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Normalised vs star schema benchmark",
        "",
        f"{version}; median of {args.runs} runs after 5 warm-up runs; times from EXPLAIN (ANALYZE), in milliseconds.",
        "",
        "| Query | Rows | Joins (norm / star) | Tables (norm / star) | Planning ms (norm / star) | Execution ms (norm / star) | Same rows |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        lines.append(
            f"| {r['query']} | {r['normalized_rows']} | {r['normalized_joins']} / {r['star_joins']} | "
            f"{r['normalized_tables']} / {r['star_tables']} | {r['normalized_planning_ms']} / {r['star_planning_ms']} | "
            f"{r['normalized_execution_ms']} / {r['star_execution_ms']} | {'yes' if r['same_rows'] else 'NO'} |"
        )
    (OUT / "benchmark.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT / 'benchmark.csv'} and {OUT / 'benchmark.md'}")


if __name__ == "__main__":
    main()
