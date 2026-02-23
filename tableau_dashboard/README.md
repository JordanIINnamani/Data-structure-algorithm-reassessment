# Tableau Dashboard Workspace

This folder contains a reproducible data-prep flow for building a Tableau dashboard from Task C benchmark results.

## 1) Generate Tableau-ready data

From the repository root:

```bash
python3 tableau_dashboard/prepare_tableau_data.py
```

This reads `Task C/experiment_results.csv` and writes curated CSVs to `tableau_dashboard/data/`.
If that CSV is not extracted yet, the script automatically falls back to reading
`Task C/experiment_results.csv` from the repository ZIP archive:
`DATA STRUCTURE AND ALGORITHM REASSESSMENT.zip`.

## 2) Output tables

- `tableau_run_level.csv`
  - Grain: one row per benchmark run
  - Includes derived fields such as `time_seconds`, `relative_to_fastest_in_size`, and log-scale helpers
- `tableau_size_algorithm_summary.csv`
  - Grain: dataset size + algorithm
  - Includes average, median, min/max, standard deviation, and coefficient of variation
- `tableau_algorithm_overview.csv`
  - Grain: one row per algorithm
  - Includes KPI fields (average, median, P95, min/max)
- `tableau_speedup.csv`
  - Grain: one row per dataset size
  - Bubble-vs-Heap speedup factor and percent time saved

## 3) Suggested Tableau dashboard build

### Sheet A: Runtime by Dataset Size (Line)
- Data source: `tableau_size_algorithm_summary.csv`
- Columns: `dataset_size`
- Rows: `avg_time_ms`
- Color: `algorithm`

### Sheet B: Speedup by Dataset Size (Bar)
- Data source: `tableau_speedup.csv`
- Columns: `dataset_size`
- Rows: `speedup_factor_bubble_div_heap`
- Tooltip: `time_saved_pct_vs_bubble`

### Sheet C: Run Variability (Box Plot)
- Data source: `tableau_run_level.csv`
- Columns: `dataset_size`
- Rows: `time_ms`
- Color: `algorithm`

### Sheet D: KPI Cards
- Data source: `tableau_algorithm_overview.csv`
- KPI examples:
  - `avg_time_ms`
  - `p95_time_ms`
  - `max_time_ms`

## 4) Recommended dashboard filters

- `algorithm`
- `dataset_size`
- `run_number` (for run-level diagnostics)

## 5) Notes

- Some `log10_time_ms` values can be blank if measured runtime is zero.
- Keep `dataset_size` as a numeric dimension to preserve sort order.
