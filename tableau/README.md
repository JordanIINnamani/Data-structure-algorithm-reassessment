# Tableau Data Prep

This folder contains a small data-prep utility to generate **Tableau-ready CSV files** from:

- `Task C/experiment_results.csv` (sorting experiment timing runs)
- `TASK D/weights_*.csv` (Scales problem test-case weights)

## Run

From the repository root:

```bash
python tableau/prepare_tableau_data.py
```

Optional arguments:

```bash
python tableau/prepare_tableau_data.py --root /path/to/project --output /path/to/output
```

By default, output files are written to `tableau/output/`.

## Generated CSV Files

1. `task_c_runs_detail.csv`
   - One row per experiment run
   - Includes `dataset_size`, `algorithm`, `run_number`, `time_ms`, `time_seconds`, and `log10_time_ms`

2. `task_c_algorithm_summary.csv`
   - Aggregated metrics per dataset size + algorithm
   - Includes mean/median/std dev/min/max timings

3. `task_c_speedup_summary.csv`
   - Bubble Sort vs Binary Heap comparison by dataset size
   - Includes average timings, absolute time saved, and speedup ratio

4. `task_d_weights_long.csv`
   - Long-format weight rows (`case_name`, `weight_index`, `weight`)
   - Best suited for histograms, distributions, and strip/bar plots

5. `task_d_weights_summary.csv`
   - Per-case descriptive stats (`total_weight`, `range`, `mean`, `std dev`, etc.)

## Suggested Tableau Sheets

1. **Runtime Growth (Task C)**
   - Line chart: `dataset_size` on Columns, `avg_time_ms` on Rows
   - Color by `algorithm`
   - Source: `task_c_algorithm_summary.csv`

2. **Algorithm Speedup**
   - Bar chart: `dataset_size` vs `speedup_ratio`
   - Source: `task_c_speedup_summary.csv`

3. **Run Variability**
   - Box plot: `dataset_size` and `time_ms`, split by `algorithm`
   - Source: `task_c_runs_detail.csv`

4. **Weight Distribution by Case (Task D)**
   - Histogram or strip plot by `case_name`
   - Source: `task_d_weights_long.csv`

5. **Case Metrics Table**
   - Text table with totals and dispersion columns
   - Source: `task_d_weights_summary.csv`
