#!/usr/bin/env python3
"""Prepare benchmark CSV exports for Tableau dashboard development.

This script converts Task C experiment output into curated Tableau tables:
1) Run-level data with derived metrics
2) Dataset-size + algorithm summary statistics
3) Overall algorithm KPIs
4) Bubble-vs-Heap speedup metrics by dataset size
"""

from __future__ import annotations

import argparse
import csv
import io
import math
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path


REQUIRED_COLUMNS = {"dataset_size", "algorithm", "run_number", "time_ms"}
DEFAULT_INPUT = Path("Task C/experiment_results.csv")
DEFAULT_ARCHIVE = Path("DATA STRUCTURE AND ALGORITHM REASSESSMENT.zip")
DEFAULT_ARCHIVE_MEMBER = "Task C/experiment_results.csv"


def _safe_float(raw_value: str, column_name: str) -> float:
    """Convert a field to float with a clear error message."""
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"Could not parse '{raw_value}' as float in '{column_name}'") from exc


def _safe_int(raw_value: str, column_name: str) -> int:
    """Convert a field to int with a clear error message."""
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Could not parse '{raw_value}' as int in '{column_name}'") from exc


def _fmt(value: float | None, decimals: int = 6) -> str:
    """Format floating values for CSV output."""
    if value is None:
        return ""
    return f"{value:.{decimals}f}"


def _read_runs_from_reader(reader: csv.DictReader, source_name: str) -> list[dict]:
    """Validate and convert rows from a CSV DictReader."""
    source_columns = set(reader.fieldnames or [])
    missing = REQUIRED_COLUMNS - source_columns
    if missing:
        missing_fields = ", ".join(sorted(missing))
        raise ValueError(f"Missing required columns in {source_name}: {missing_fields}")

    runs: list[dict] = []
    for row in reader:
        dataset_size = _safe_int(row["dataset_size"], "dataset_size")
        run_number = _safe_int(row["run_number"], "run_number")
        time_ms = _safe_float(row["time_ms"], "time_ms")
        algorithm = row["algorithm"].strip()
        runs.append(
            {
                "dataset_size": dataset_size,
                "algorithm": algorithm,
                "run_number": run_number,
                "time_ms": time_ms,
            }
        )

    if not runs:
        raise ValueError(f"No benchmark rows found in {source_name}")

    return runs


def read_runs(input_path: Path) -> list[dict]:
    """Read and validate raw experiment rows from a CSV file path."""
    with input_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return _read_runs_from_reader(reader, str(input_path))


def read_runs_from_zip(zip_path: Path, member_path: str) -> list[dict]:
    """Read and validate benchmark rows from a member within a ZIP archive."""
    with zipfile.ZipFile(zip_path, "r") as archive:
        try:
            member = archive.open(member_path, "r")
        except KeyError as exc:
            raise FileNotFoundError(
                f"Archive member does not exist: {zip_path}!/{member_path}"
            ) from exc

        with member, io.TextIOWrapper(member, encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            return _read_runs_from_reader(reader, f"{zip_path}!/{member_path}")


def _p95(values: list[float]) -> float:
    """Compute an interpolated 95th percentile."""
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = 0.95 * (len(ordered) - 1)
    low_index = math.floor(rank)
    high_index = math.ceil(rank)
    if low_index == high_index:
        return ordered[low_index]
    weight = rank - low_index
    return ordered[low_index] + (ordered[high_index] - ordered[low_index]) * weight


def build_run_level_rows(runs: list[dict]) -> list[dict]:
    """Create row-level table with derived Tableau metrics."""
    min_time_by_dataset: dict[int, float] = {}
    grouped: dict[int, list[float]] = defaultdict(list)
    for row in runs:
        grouped[row["dataset_size"]].append(row["time_ms"])
    for dataset_size, times in grouped.items():
        min_time_by_dataset[dataset_size] = min(times)

    run_rows: list[dict] = []
    for row in sorted(runs, key=lambda r: (r["dataset_size"], r["algorithm"], r["run_number"])):
        dataset_min_time = min_time_by_dataset[row["dataset_size"]]
        relative_to_fastest = row["time_ms"] / dataset_min_time if dataset_min_time > 0 else None
        log_time_ms = math.log10(row["time_ms"]) if row["time_ms"] > 0 else None

        run_rows.append(
            {
                "dataset_size": row["dataset_size"],
                "algorithm": row["algorithm"],
                "run_number": row["run_number"],
                "time_ms": _fmt(row["time_ms"], 4),
                "time_seconds": _fmt(row["time_ms"] / 1000.0, 6),
                "dataset_min_time_ms": _fmt(dataset_min_time, 4),
                "relative_to_fastest_in_size": _fmt(relative_to_fastest, 6),
                "is_fastest_in_size": int(abs(row["time_ms"] - dataset_min_time) < 1e-12),
                "log10_dataset_size": _fmt(math.log10(row["dataset_size"]), 6),
                "log10_time_ms": _fmt(log_time_ms, 6),
            }
        )
    return run_rows


def build_size_algorithm_summary(runs: list[dict]) -> tuple[list[dict], dict[tuple[int, str], float]]:
    """Aggregate per dataset size and algorithm statistics."""
    grouped: dict[tuple[int, str], list[float]] = defaultdict(list)
    for row in runs:
        key = (row["dataset_size"], row["algorithm"])
        grouped[key].append(row["time_ms"])

    summary_rows: list[dict] = []
    avg_lookup: dict[tuple[int, str], float] = {}
    for (dataset_size, algorithm), times in sorted(grouped.items()):
        avg_time = statistics.mean(times)
        median_time = statistics.median(times)
        min_time = min(times)
        max_time = max(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0.0
        coefficient_of_variation_pct = (std_dev / avg_time * 100.0) if avg_time > 0 else None

        summary_rows.append(
            {
                "dataset_size": dataset_size,
                "algorithm": algorithm,
                "run_count": len(times),
                "avg_time_ms": _fmt(avg_time, 4),
                "median_time_ms": _fmt(median_time, 4),
                "min_time_ms": _fmt(min_time, 4),
                "max_time_ms": _fmt(max_time, 4),
                "std_dev_time_ms": _fmt(std_dev, 4),
                "coefficient_of_variation_pct": _fmt(coefficient_of_variation_pct, 4),
            }
        )
        avg_lookup[(dataset_size, algorithm)] = avg_time
    return summary_rows, avg_lookup


def build_algorithm_overview(runs: list[dict]) -> list[dict]:
    """Aggregate high-level KPIs for each algorithm."""
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in runs:
        grouped[row["algorithm"]].append(row["time_ms"])

    overview_rows: list[dict] = []
    for algorithm, times in sorted(grouped.items()):
        overview_rows.append(
            {
                "algorithm": algorithm,
                "total_runs": len(times),
                "avg_time_ms": _fmt(statistics.mean(times), 4),
                "median_time_ms": _fmt(statistics.median(times), 4),
                "p95_time_ms": _fmt(_p95(times), 4),
                "min_time_ms": _fmt(min(times), 4),
                "max_time_ms": _fmt(max(times), 4),
            }
        )
    return overview_rows


def build_speedup_rows(avg_lookup: dict[tuple[int, str], float]) -> list[dict]:
    """Create Bubble Sort vs Binary Heap speedup metrics by dataset size."""
    dataset_sizes = sorted({dataset_size for dataset_size, _ in avg_lookup.keys()})
    rows: list[dict] = []
    for dataset_size in dataset_sizes:
        bubble_avg = avg_lookup.get((dataset_size, "Bubble Sort"))
        heap_avg = avg_lookup.get((dataset_size, "Binary Heap"))
        if bubble_avg is None or heap_avg is None:
            continue

        speedup_factor = bubble_avg / heap_avg if heap_avg > 0 else None
        time_saved_pct = ((bubble_avg - heap_avg) / bubble_avg * 100.0) if bubble_avg > 0 else None
        rows.append(
            {
                "dataset_size": dataset_size,
                "bubble_sort_avg_ms": _fmt(bubble_avg, 4),
                "binary_heap_avg_ms": _fmt(heap_avg, 4),
                "speedup_factor_bubble_div_heap": _fmt(speedup_factor, 4),
                "time_saved_pct_vs_bubble": _fmt(time_saved_pct, 4),
            }
        )
    return rows


def write_csv(output_path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """Write a table to CSV with a stable schema."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description="Convert benchmark results into Tableau dashboard data tables."
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="Path to raw experiment CSV (default: Task C/experiment_results.csv)",
    )
    parser.add_argument(
        "--archive",
        default=str(DEFAULT_ARCHIVE),
        help=(
            "ZIP archive used as fallback when --input is missing and --input is the default "
            "Task C path"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="tableau_dashboard/data",
        help="Directory where Tableau-ready CSV files are written",
    )
    return parser.parse_args()


def main() -> None:
    """Run the Tableau data preparation pipeline."""
    args = parse_args()
    input_path = Path(args.input)
    archive_path = Path(args.archive)
    output_dir = Path(args.output_dir)

    source_name = str(input_path)
    if input_path.exists():
        runs = read_runs(input_path)
    elif input_path == DEFAULT_INPUT and archive_path.exists():
        runs = read_runs_from_zip(archive_path, DEFAULT_ARCHIVE_MEMBER)
        source_name = f"{archive_path}!/{DEFAULT_ARCHIVE_MEMBER}"
    else:
        raise FileNotFoundError(
            f"Input file does not exist: {input_path}. "
            f"Archive fallback also unavailable: {archive_path}"
        )

    run_rows = build_run_level_rows(runs)
    summary_rows, avg_lookup = build_size_algorithm_summary(runs)
    overview_rows = build_algorithm_overview(runs)
    speedup_rows = build_speedup_rows(avg_lookup)

    write_csv(
        output_dir / "tableau_run_level.csv",
        [
            "dataset_size",
            "algorithm",
            "run_number",
            "time_ms",
            "time_seconds",
            "dataset_min_time_ms",
            "relative_to_fastest_in_size",
            "is_fastest_in_size",
            "log10_dataset_size",
            "log10_time_ms",
        ],
        run_rows,
    )
    write_csv(
        output_dir / "tableau_size_algorithm_summary.csv",
        [
            "dataset_size",
            "algorithm",
            "run_count",
            "avg_time_ms",
            "median_time_ms",
            "min_time_ms",
            "max_time_ms",
            "std_dev_time_ms",
            "coefficient_of_variation_pct",
        ],
        summary_rows,
    )
    write_csv(
        output_dir / "tableau_algorithm_overview.csv",
        [
            "algorithm",
            "total_runs",
            "avg_time_ms",
            "median_time_ms",
            "p95_time_ms",
            "min_time_ms",
            "max_time_ms",
        ],
        overview_rows,
    )
    write_csv(
        output_dir / "tableau_speedup.csv",
        [
            "dataset_size",
            "bubble_sort_avg_ms",
            "binary_heap_avg_ms",
            "speedup_factor_bubble_div_heap",
            "time_saved_pct_vs_bubble",
        ],
        speedup_rows,
    )

    print(f"Read {len(runs)} benchmark rows from: {source_name}")
    print(f"Wrote Tableau tables to: {output_dir}")


if __name__ == "__main__":
    main()
