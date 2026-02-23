#!/usr/bin/env python3
"""Prepare Tableau-ready CSV exports from Task C and Task D data."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Dict[str, object]]) -> None:
    """Write rows to a CSV file with consistent UTF-8 output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def round_or_zero(value: float, digits: int = 6) -> float:
    """Round float values while keeping zero stable."""
    if value == 0:
        return 0.0
    return round(value, digits)


def load_task_c_details(experiment_results_path: Path) -> List[Dict[str, object]]:
    """Load and normalize Task C experiment runs for Tableau."""
    if not experiment_results_path.exists():
        raise FileNotFoundError(f"Missing Task C results file: {experiment_results_path}")

    detail_rows: List[Dict[str, object]] = []
    with experiment_results_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            dataset_size = int(row["dataset_size"])
            algorithm = row["algorithm"].strip()
            run_number = int(row["run_number"])
            time_ms = float(row["time_ms"])
            slug = algorithm.lower().replace(" ", "_")

            detail_rows.append(
                {
                    "dataset_size": dataset_size,
                    "algorithm": algorithm,
                    "algorithm_slug": slug,
                    "run_number": run_number,
                    "time_ms": round_or_zero(time_ms, 6),
                    "time_seconds": round_or_zero(time_ms / 1000.0, 6),
                    "log10_time_ms": round(math.log10(time_ms), 6) if time_ms > 0 else "",
                }
            )

    return detail_rows


def summarize_task_c(detail_rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    """Build per-algorithm summary metrics by dataset size."""
    grouped: Dict[Tuple[int, str], List[float]] = defaultdict(list)
    for row in detail_rows:
        key = (int(row["dataset_size"]), str(row["algorithm"]))
        grouped[key].append(float(row["time_ms"]))

    summary_rows: List[Dict[str, object]] = []
    for (dataset_size, algorithm), values in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1])):
        std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
        summary_rows.append(
            {
                "dataset_size": dataset_size,
                "algorithm": algorithm,
                "runs": len(values),
                "avg_time_ms": round_or_zero(statistics.mean(values), 6),
                "median_time_ms": round_or_zero(statistics.median(values), 6),
                "std_dev_time_ms": round_or_zero(std_dev, 6),
                "min_time_ms": round_or_zero(min(values), 6),
                "max_time_ms": round_or_zero(max(values), 6),
            }
        )

    return summary_rows


def build_task_c_speedup(summary_rows: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    """Compute Bubble Sort vs Binary Heap speedup per dataset size."""
    lookup: Dict[int, Dict[str, float]] = defaultdict(dict)
    for row in summary_rows:
        dataset_size = int(row["dataset_size"])
        algorithm = str(row["algorithm"])
        lookup[dataset_size][algorithm] = float(row["avg_time_ms"])

    speedup_rows: List[Dict[str, object]] = []
    for dataset_size in sorted(lookup):
        bubble_avg = lookup[dataset_size].get("Bubble Sort")
        heap_avg = lookup[dataset_size].get("Binary Heap")
        if bubble_avg is None or heap_avg is None:
            continue

        speedup_ratio = bubble_avg / heap_avg if heap_avg > 0 else ""
        speedup_rows.append(
            {
                "dataset_size": dataset_size,
                "bubble_sort_avg_time_ms": round_or_zero(bubble_avg, 6),
                "binary_heap_avg_time_ms": round_or_zero(heap_avg, 6),
                "absolute_time_saved_ms": round_or_zero(bubble_avg - heap_avg, 6),
                "speedup_ratio": round(speedup_ratio, 6) if isinstance(speedup_ratio, float) else "",
            }
        )

    return speedup_rows


def load_task_d_weights(task_d_directory: Path) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    """Load Task D weight CSVs and produce long-format + summary outputs."""
    csv_paths = sorted(task_d_directory.glob("weights_*.csv"))
    if not csv_paths:
        raise FileNotFoundError(f"No Task D weights files found in: {task_d_directory}")

    long_rows: List[Dict[str, object]] = []
    summary_rows: List[Dict[str, object]] = []

    for csv_path in csv_paths:
        case_name = csv_path.stem
        if case_name.startswith("weights_"):
            case_name = case_name[len("weights_") :]

        weights: List[int] = []
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            for row in reader:
                for value in row:
                    stripped = value.strip()
                    if stripped:
                        weights.append(int(stripped))

        for index, weight in enumerate(weights, start=1):
            long_rows.append(
                {
                    "case_name": case_name,
                    "weight_index": index,
                    "weight": weight,
                }
            )

        std_dev = statistics.stdev(weights) if len(weights) > 1 else 0.0
        even_count = sum(1 for weight in weights if weight % 2 == 0)
        odd_count = len(weights) - even_count
        total_weight = sum(weights)
        min_weight = min(weights)
        max_weight = max(weights)

        summary_rows.append(
            {
                "case_name": case_name,
                "weights_count": len(weights),
                "total_weight": total_weight,
                "target_group_weight": round_or_zero(total_weight / 2.0, 6),
                "min_weight": min_weight,
                "max_weight": max_weight,
                "weight_range": max_weight - min_weight,
                "mean_weight": round_or_zero(statistics.mean(weights), 6),
                "median_weight": round_or_zero(statistics.median(weights), 6),
                "std_dev_weight": round_or_zero(std_dev, 6),
                "even_weights": even_count,
                "odd_weights": odd_count,
            }
        )

    summary_rows.sort(key=lambda row: str(row["case_name"]))
    return long_rows, summary_rows


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    project_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=project_root,
        help="Project root containing 'Task C' and 'TASK D' directories.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "output",
        help="Directory where Tableau-ready CSV files will be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    task_c_results_path = args.root / "Task C" / "experiment_results.csv"
    task_d_directory = args.root / "TASK D"

    task_c_details = load_task_c_details(task_c_results_path)
    task_c_summary = summarize_task_c(task_c_details)
    task_c_speedup = build_task_c_speedup(task_c_summary)
    task_d_long, task_d_summary = load_task_d_weights(task_d_directory)

    write_csv(
        args.output / "task_c_runs_detail.csv",
        [
            "dataset_size",
            "algorithm",
            "algorithm_slug",
            "run_number",
            "time_ms",
            "time_seconds",
            "log10_time_ms",
        ],
        task_c_details,
    )
    write_csv(
        args.output / "task_c_algorithm_summary.csv",
        [
            "dataset_size",
            "algorithm",
            "runs",
            "avg_time_ms",
            "median_time_ms",
            "std_dev_time_ms",
            "min_time_ms",
            "max_time_ms",
        ],
        task_c_summary,
    )
    write_csv(
        args.output / "task_c_speedup_summary.csv",
        [
            "dataset_size",
            "bubble_sort_avg_time_ms",
            "binary_heap_avg_time_ms",
            "absolute_time_saved_ms",
            "speedup_ratio",
        ],
        task_c_speedup,
    )
    write_csv(args.output / "task_d_weights_long.csv", ["case_name", "weight_index", "weight"], task_d_long)
    write_csv(
        args.output / "task_d_weights_summary.csv",
        [
            "case_name",
            "weights_count",
            "total_weight",
            "target_group_weight",
            "min_weight",
            "max_weight",
            "weight_range",
            "mean_weight",
            "median_weight",
            "std_dev_weight",
            "even_weights",
            "odd_weights",
        ],
        task_d_summary,
    )

    print(f"Wrote Tableau CSV exports to: {args.output}")
    print("- task_c_runs_detail.csv")
    print("- task_c_algorithm_summary.csv")
    print("- task_c_speedup_summary.csv")
    print("- task_d_weights_long.csv")
    print("- task_d_weights_summary.csv")


if __name__ == "__main__":
    main()
