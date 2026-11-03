# Columnar Query Benchmarks: CSV vs Parquet

A reproducible Python benchmark comparing **DuckDB queries over CSV and Parquet** using the exact same synthetic dataset and analytical SQL. Focuses on correctness, query execution time, columnar storage, and thoughtful measurement.

## Quick start

```bash
python -m pip install -r requirements.txt
python benchmark.py --rows 100000 --runs 3
python -m unittest discover -s tests -v
```

On Windows PowerShell, the same commands work after installing Python 3.10+.

Generated outputs in `results/`:
- `events.csv` / `events.parquet`: identical synthetic source data in two formats
- `benchmark_results.json`: median measured execution times, sizes, engine version
- `RESULTS.md`: formatted results table for a README or interview portfolio

## What is being tested?

1. `selective_grouping`: group by region after filtering category
2. `projection_and_filter`: select only two columns and filter
3. `daily_grouping`: aggregate counts by date

Each query is executed against both formats; result sets are compared **before** recording the benchmark. All performance numbers come from running the code, not from this README.

## Caveats

- `read_csv` and `read_parquet` have different parsing costs; this is not an apples-to-apples comparison of only the internal query operators.
- OS filesystem cache, CPU load, datasets, DuckDB version and thread count influence timings.
- Small input data may give misleading differences; try multiple scales.
- This script does not claim to benchmark Apache Spark, distributed execution or production workloads.

## Extend for Palantir Query Engines

- Add DuckDB `EXPLAIN ANALYZE` output to show scan and operator choices.
- Compare wide vs narrow projections and varying filter selectivity.
- Test multiple Parquet row group sizes and record the effect on scan time.
- Optional: use PyArrow to inspect Parquet metadata or produce datasets with different row groups.

No client, FMG, trading or proprietary data is included.
