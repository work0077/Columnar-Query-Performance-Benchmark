"""Reproducible CSV vs Parquet analytics benchmark using DuckDB.

Install: pip install -r requirements.txt
Run: python benchmark.py --rows 100000 --runs 3
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import time
from pathlib import Path

import duckdb


def generate_csv(path: Path, rows: int, seed: int = 42) -> None:
    """Generate synthetic business events. No confidential data is used."""
    rng = random.Random(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["event_id", "region", "category", "quantity", "amount", "event_date"])
        for i in range(rows):
            writer.writerow([
                i, rng.choice(["North", "South", "East", "West"]),
                rng.choice(["Hardware", "Software", "Services"]),
                rng.randint(1, 8), f"{rng.randint(150, 90000) / 100:.2f}",
                f"2026-{1 + i % 12:02d}-{1 + i % 28:02d}",
            ])


def create_parquet(con: duckdb.DuckDBPyConnection, csv_path: Path, parquet_path: Path) -> None:
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    csv_literal = str(csv_path).replace("'", "''")
    parquet_literal = str(parquet_path).replace("'", "''")
    con.execute(f"COPY (SELECT * FROM read_csv('{csv_literal}', header=true)) "
                f"TO '{parquet_literal}' (FORMAT PARQUET, COMPRESSION ZSTD)")


def sql_queries(source: str) -> dict[str, str]:
    """Pass a constant table expression constructed from our own output paths."""
    return {
        "selective_grouping": f"SELECT region, ROUND(SUM(amount), 2) AS total FROM {source} "
                              "WHERE category = 'Software' GROUP BY region ORDER BY region",
        "projection_and_filter": f"SELECT event_id, amount FROM {source} "
                                 "WHERE quantity >= 7 AND region = 'West' ORDER BY event_id LIMIT 50",
        "daily_grouping": f"SELECT event_date, COUNT(*) AS n FROM {source} "
                          "WHERE region = 'North' GROUP BY event_date ORDER BY event_date LIMIT 50",
    }


def run_benchmark(output: Path, rows: int, repetitions: int) -> dict:
    if rows <= 0 or repetitions <= 0:
        raise ValueError("rows and runs must be positive")
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / "events.csv"
    parquet_path = output / "events.parquet"
    generate_csv(csv_path, rows)
    con = duckdb.connect()
    con.execute("SET threads = 1")  # Avoid noisy parallelism comparisons in this demonstration.
    create_parquet(con, csv_path, parquet_path)

    sources = {
        "CSV": "read_csv('" + str(csv_path).replace("'", "''") + "', header=true)",
        "Parquet": "read_parquet('" + str(parquet_path).replace("'", "''") + "')",
    }
    results = []
    for query_name in sql_queries("SOURCE"):
        benchmark_rows = {}
        for format_name, table_expr in sources.items():
            query = sql_queries(table_expr)[query_name]
            expected = con.execute(query).fetchall()
            # Warmup does not count towards the measured repetitions.
            con.execute(query).fetchall()
            samples = []
            for _ in range(repetitions):
                start = time.perf_counter()
                observed = con.execute(query).fetchall()
                samples.append(time.perf_counter() - start)
                assert observed == expected
            benchmark_rows[format_name] = (expected, statistics.median(samples) * 1000)
        if benchmark_rows["CSV"][0] != benchmark_rows["Parquet"][0]:
            raise AssertionError(f"CSV / Parquet results disagree for: {query_name}")
        results.append({
            "query": query_name,
            "csv_median_ms": round(benchmark_rows["CSV"][1], 3),
            "parquet_median_ms": round(benchmark_rows["Parquet"][1], 3),
            "rows_returned": len(benchmark_rows["CSV"][0]),
            "results_match": True,
        })

    output_json = {
        "duckdb_version": duckdb.__version__,
        "synthetic_rows": rows,
        "runs_per_query": repetitions,
        "csv_bytes": csv_path.stat().st_size,
        "parquet_bytes": parquet_path.stat().st_size,
        "results": results,
        "note": "Wall-clock measurements are environment-dependent; do not generalise from a single run.",
    }
    (output / "benchmark_results.json").write_text(json.dumps(output_json, indent=2) + "\n", encoding="utf-8")
    markdown = ["# Measured CSV vs Parquet results", "",
                f"DuckDB `{duckdb.__version__}`, {rows:,} synthetic rows, {repetitions} repeated timings.", "",
                "| Query | CSV median (ms) | Parquet median (ms) | Same results? |",
                "|---|---:|---:|---|"]
    for item in results:
        markdown.append(f"| {item['query']} | {item['csv_median_ms']} | {item['parquet_median_ms']} | Yes |")
    markdown += ["", "Timings are local measurements, not universal performance guarantees."]
    (output / "RESULTS.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    con.close()
    return output_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=100000)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    report = run_benchmark(args.output, args.rows, args.runs)
    print(json.dumps(report, indent=2))
    print(f"\nGenerated: {args.output / 'RESULTS.md'}")


if __name__ == "__main__":
    main()
