# Dissertation figure register â€” 29 October 2026

Current selection updated30October2026: **13 figures** across `figures/dissertation/v4`, `telemetry-quality-v1`, `event-training-v1` and `event-baselines-v1`. See `figures/dissertation/README.md` for the complete index. Every selected figure has a300dpi PNG and vectorPDF plus captions and a source/output hash manifest. Original results were not modified. Prefer PDF in the dissertation for scalable lines and text.

The six historical figures in **v4** are listed below. Its per-figure manifest maps source files and hashes, output hashes, plotting script hash and Matplotlib version.

| Figure | Content | Intended interpretation |
|---|---|---|
| 01_grid_studies | Original and finer-grid cell-solver studies | Numerical diagnostic including historical failure; finest output is not ground truth |
| 02_event_validation | Event solver sample-grid invariance and integration refinement | Output sampling and numerical integration are distinct; synthetic only |
| 03_calibration_identifiability | Assumed-mass coefficient scaling and refitted drag profile | Real development derivative-fit diagnostic, not a calibrated car or confidence interval |
| 04_reconstruction_errors | Synthetic exact/noisy inverse fit and action error | Trace matching can coexist with wrong actions; noisy case uses known base power |
| 05_reconstruction_maps | Alternative feasible maps under uncertain base power | Synthetic ambiguity; not a real team map |
| 06_synthetic_controller_comparison | Baselines, discrete DP/exhaustive and three PPO seeds | Original constant-force model only; no event/power-model result mixed in |

Read and retain the detailed captions with each figure. Reconstruction speed RMSE is residual against the fitted observations, including noisy observations, not error against noiseless truth. It is near machine precision because the endpoint inverse problem can fit those observations; the action error remains informative where synthetic truth is known. Multiple optimiser initialisations are not independent data replicates. The baseline chart uses a dot plot with a restricted elapsed-time axis, not zero-based bars.

## Reproduction
From the project folder:

```powershell
.\.venv\Scripts\python.exe scripts/plot_dissertation_results.py --output figures/dissertation/v5
```

Choose a new version directory. The script refuses to overwrite an existing folder. It reads saved artifacts and performs no simulation, fitting, training or data download. Later event-model training results need separate clearly labelled plots; do not combine their lap times with constant-force model results as if they were identical experiments.

## Visual verification and correction history
Viewed a contact sheet of all six v1 figures. That inspection found duplicate PPO points already embedded in the baseline artifact and an unrecognised noisy-case label. Corrected the script to exclude embedded PPO duplicates and include the exact noisy_sigma_0.1 source case, then generated v2. Inspected the corrected reconstruction plot. v1 remains a superseded draft and should not be used in the dissertation. A further visual check identified crowded log-axis tick labels in figure01; v3 uses exact grid positions with plain rotated labels and no minor tick labels. v4 updates event numerical evidence to the accepted event-validation-002 artifact with stronger envelope checks. This register identifies v4 as the deliverable; future script changes require a new version and manifest. All plots use saved numerical values, labelled units and explicit synthetic/development scope.

The three PPO seed results are shown as individual points, with no error bars or unsupported uncertainty estimate. All six v4 figures have PNG and PDF companions and hashed source mappings.

## Additional selected evidence — 30 October 2026

| Folder / figure | Evidence | Interpretation |
|---|---|---|
| telemetry-quality-v1 / telemetry_quality | Bahrain2025Q laps4/10/13/16 source speed and adjacent time gaps | Real development telemetry diagnostic, including lap16 gap problem; no hidden energy labels |
| event-training-v1 / 01_event_controller_comparison | Three event-model PPO seeds and common heuristics | Bounded synthetic4096-step pilots, not convergence |
| event-training-v1 / 02_event_training_curves | Recorded rolling stochastic episode returns | Training traces, not independent evaluation or confidence intervals |
| event-training-v1 / 03_event_replay_profiles | Dense speed/battery replay of saved nominal actions | Synthetic model battery; full and seed0 overlap |
| event-baselines-v1 / 01_event_dp_ppo_comparison | Shared-physics DP, five/nine-action exhaustive references and saved PPO | Finite action references; evaluation has now been inspected |
| event-baselines-v1 / 02_event_dp_refinement | Original failed energy grid and documented refinement | Nonmonotonic policy selection; rounded objective distinct from physical replay |
| event-baselines-v1 / 03_event_allocation | Four-segment requested actions and feasible elapsed gaps | Three-action development reference; no PPO or real-driver claim |

All three new event-baseline figures were visually inspected. The telemetry-quality figure and event training curves were inspected in this cycle, supplementing prior checks of the six historical figures and replay profiles. Seven existing run/figure directories passed their saved input/output hash checks; all36 outputs in three new baseline runs and the new figure set passed hash verification. Evidence: logs/agent_tools/2026-10-30/*audit*.json. Manifests use heterogeneous schemas; the v4 per-figure schema was verified directly rather than assumed compatible with scripts/verify_run.py.

Reproduce the latest plots from immutable canonical run001/003 results with `python scripts/plot_event_baselines.py --output figures/dissertation/event-baselines-v2`. The script rejects an existing destination. The earlier telemetry/event-training plotting scripts use fixed output folder names and refuse overwrite; use preserved files or intentionally change their output destinations before regeneration. No need to retrain or redownload data for these plots.
