# Dissertation figure register

## Core dissertation comparisons as of 19 November 2026

Each linked PDF has a 300 dpi PNG alongside it. The linked reports explain the axes, units, scope and verification.

| Comparison | Figure | Interpretation |
|---|---|---|
| Frozen PPO and imitation on calibrated Bahrain | [Finish speed and delivered energy by location](../figures/dissertation/bahrain-learned-transfer-v1/01_bahrain_learned_transfer.pdf) | [Closed-loop test against planner and spread](bahrain_learned_transfer.md) |
| Two equal-work budgets | [Time saved and extra work used by distance](../figures/dissertation/bahrain-equal-work-v1/03_bahrain_matched_by_distance.pdf) · [Higher work match](../figures/dissertation/bahrain-equal-work-v1/01_bahrain_spread_work_match.pdf) · [Lower work match](../figures/dissertation/bahrain-equal-work-v1/02_bahrain_selected_work_match.pdf) | [Work tolerance, timing and feasibility](bahrain_equal_work.md) |
| Bahrain driving line and transfer to another driver | [T1, T8 and T14 positions and curvature](../figures/dissertation/bahrain-corner-paths-v1/corner_paths.pdf) · [Same-driver speed errors](../figures/dissertation/bahrain-path-candidate-v1/path_comparison.pdf) · [Three paired cross-driver laps](../figures/dissertation/bahrain-driver-transfer-v1/01_paired_transfer.pdf) | [Single change to path](bahrain_path_candidate.md) · [One-time transfer scores](bahrain_driver_transfer.md) |
| Bahrain wheel assist by location | [Circuit map](../figures/dissertation/bahrain-deployment-zones-v1/01_bahrain_wheel_assist.pdf) · [Power and lap-time profiles](../figures/dissertation/bahrain-deployment-zones-v1/02_bahrain_deployment_profiles.pdf) | [Delivered energy, matched timing shifts and sensitivity](bahrain_deployment_zones.md) |
| Bahrain lap-time discrepancy | [Historical gap](../figures/dissertation/bahrain-pace-diagnosis-v1/01_historic_gap.pdf) · [Lap 4](../figures/dissertation/bahrain-pace-calibration-v1/lap-4.pdf) · [Lap 10](../figures/dissertation/bahrain-pace-calibration-v1/lap-10.pdf) · [Physical assumptions and corner speeds](../figures/dissertation/bahrain-pace-mechanisms-v1/pace_mechanisms.pdf) | [Signed errors, conditions and gate outcomes](bahrain_qualifying_pace.md) |
| Local speed error where deployment recurs | [Two observed laps with shared zones shaded](../figures/dissertation/bahrain-zone-support-v1/zone_motion_support.pdf) | [Per-zone wheel work and motion RMSE](../results/bahrain-zone-support-001/metrics.json) |
| Conditional deployment on observed Bahrain windows | [Reconstruction](../figures/dissertation/bounded-real-reconstruction-v2/01_bounded_real_inverse.pdf) | [Feasible fits and omitted segments](bounded_real_reconstruction.md) |
| Nominal regenerative controllers and optimization | [Three-seed figures](../figures/dissertation/regeneration-multiseed-v1/) · [DP figures](../figures/dissertation/regeneration-dp-v1/) | [Primary comparator and costs](regeneration_dp_study.md) |
| Width-only search | [Lap time and adjacent-width gains](../figures/dissertation/regeneration-dp-width-v1/width_comparison.pdf) | [50 ms stability criterion](regeneration_dp_width.md) |
| PPO network width | [Lap times and paired gains](../figures/dissertation/ppo-actor-width-v1/01_actor_width.pdf) · [GPU execution cost](../figures/dissertation/ppo-actor-width-cost-v1/actor_width_cost.pdf) | [Three seeds at each width](ppo_actor_width.md) |
| Energy, recovery and drag changes | [Lap time and feasibility](../figures/dissertation/regeneration-robustness-v1/01_transfer_feasibility.pdf) · [Grid checks](../figures/dissertation/regeneration-robustness-v1/02_feasibility_grid_checks.pdf) | [Measured failures](regeneration_robustness.md) |
| Qualifying acceleration prediction | [Validation](../figures/dissertation/session-mix-qualifying-v1/01_qualifying_session_mix.pdf) · [Final evaluation](../figures/dissertation/session-mix-final-v1/qualifying_holdout.pdf) | [Coverage and held-out event scores](session_mix_study.md) |

## Earlier selections

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

## Source access evidence — 10 November 2026

`data-source-audit-v1/01_openf1_sampling` (PNG/PDF) plots timestamp gaps in four 2025 OpenF1 windows. Source: source-access-audit-20261110-002. Spain practice 3 contains a gap above the existing one-second screen. Access probes are not accepted clean laps or model-validation results. Input hashes and plotted statistics checked; PNG visually inspected. Reproduce with scripts/plot_source_audit.py and a new output folder.

## Added11 November2026

- openf1-coverage-v1: acquisition coverage and overlapping exclusion reasons, PNG/PDF, inspected.
- circuit-inputs-v1: development-context acceleration diagnostics and candidate Sakhir geometry, PNG/PDF, inspected. Conditional motion candidates and within-development holdouts; no final test-model results.

## Full-circuit numerical validation — 11 November 2026

Use `circuit-validation-v4/01_curvature_speed_envelope` and `02_refinement_sensitivity_energy` (300 dpi PNG/vector PDF), sourced from circuit-validation-004. Both inspected. Run004 is a verified-case reuse of 003; it changes presentation only. The full reference-model numerical gate passes at 0.625 m, following a preserved coarse-grid failure. Large smoothing sensitivity is shown explicitly. These are assumed-model results, not measured F1 battery or calibrated lap-time claims. Captions and limitations: docs/full_circuit_validation.md. Earlier v1/v3 plots remain historical.

## Observable-motion validation — 11 November 2026

`motion-validation-v2/01_motion_validation` (300 dpi PNG/vector PDF) compares constant acceleration, assumed reference power endpoints and unchanged development-fit predictions on development lap holdouts and two reserved validation events. Source: results/motion-validation-002. Observed speed supplied; matching driver/session/DRS only. Equal lap/DRS-group weighting; no independence or measured battery claim. Visually inspected. Methods and limitations: docs/observable_motion_validation.md. v1 retained as historical presentation.

## Full-circuit controller study — 11 November 2026

- circuit-control-baselines-v1/01_baseline_grid_cadence: five reference-model policies, four numerical grids and 55/110 action decisions; preserved coarse-grid ranking failure.
- circuit-ppo-pilot-v1/01_learning_and_comparison: one 4096-step PPO seed's stochastic training trace and deterministic fine-grid baseline comparison. PPO saves 0.626 s versus zero but trails full request by 0.241 s.
- circuit-ppo-pilot-v1/02_policy_energy_speed: fine replay at action boundaries; requested action, simulated battery and speed. Requested power differs from delivered power during braking/cruise/depletion.

All three figures saved as 300 dpi PNG/vector PDF and visually inspected. Sources: circuit-control-baselines-001 and circuit-ppo-pilot-001. Assumed model; no convergence, optimality or empirical battery claim. Detailed methods and captions: docs/circuit_controller_study.md.

## GPU pilot — 11 November 2026

`circuit-ppo-gpu-v1` contains learning/comparison and policy/energy/speed PNG/PDF pairs, inspected. Source: circuit-ppo-gpu-001, CUDA-required seed0/4096 steps. The deterministic policy underuses battery and trails nonzero baselines; retain as a negative pilot result. This is not a controlled CPU/GPU performance or learning comparison. See docs/gpu_training.md.

## Longer GPU multi-seed study - 12 November 2026

- circuit-multiseed-v1/01_checkpoint_baseline_comparison: deterministic learning checkpoints for all three seeds and final fixed-baseline comparison; mean and sample SD are descriptive, not confidence intervals.
- circuit-multiseed-v1/02_stochastic_deterministic_energy: deterministic and five stochastic evaluations per training seed, with terminal battery reserve. Stochastic rollouts are nested within training seeds.

Source: results/circuit-multiseed-001; three GPU seeds, 16,384 steps each, fixed assumed circuit model and 55 decisions/lap. Final deterministic lap 108.238391 s on average (sample SD 0.049187 s), 0.369715 s faster than the strongest matched fixed baseline. Both 300 dpi PNG/vector PDF pairs are hash checked; both PNGs visually inspected. Methods, captions and limitations: docs/circuit_multiseed_study.md. Cadence/model sensitivity remains outstanding; no real-car or convergence claim.

## Unchanged-policy robustness - 12 November 2026

`circuit-sensitivity-v1/01_model_transfer` and `02_cadence_numerical_gates` are the current 300 dpi PNG/vector PDF sensitivity figures, both visually inspected. Source: results/circuit-sensitivity-001,160 deterministic rollouts,9/10 scenario/cadence cases accepted. The high-drag case fails terminal-speed feasibility and has no valid all-policy comparative mean. At110 decisions unchanged PPO is slower than at55; at20 m smoothing one PPO seed loses to exit boost. Numerical-error ratios alone pass and do not override feasibility. Three-seed SD is descriptive, not a confidence interval. Detailed methods/table/captions: docs/circuit_sensitivity_study.md. verification.json checks all160 saved replays and369 hashes.

## Terminal reserve guard - 13 November 2026

`terminal-guard-v1/01_feasibility_and_comparison` and `02_guard_energy_actions` are300 dpi PNG/vectorPDF, both inspected. Source: results/terminal-guard-001,64/64 feasible deterministic replays, nominal/highdrag x55/110. Identical250kJ protection and forcedterminal deployment apply to allcontrollers; guardedzero is no longer zeroelectricaldeployment. PPO+guard beats matched guardedbaselines; nominal55 has0.140950s cost versus unguardedPPO. Failed unguardedstudy preserved. SampleSD is descriptive; fixed guard has no globalfeasibility/optimality guarantee. Details/captions: docs/terminal_guard_study.md. Independent verification:445 hashes/64 replays.

17 November 2026: `regeneration-v1` contains two visually inspected PNG/PDF figure pairs for matched recovery-on/off fixed policies and full-request battery accounting. Source run: `results/regeneration-validation-001`; captions, assumptions and interpretation: `docs/regeneration_study.md`. These are not regeneration-trained PPO results.


17 November 2026: `regeneration-ppo-pilot-v1` adds two inspected PNG/PDF pairs for the 4,096-step CUDA pilot: learning/matched-baseline comparisons and policy/battery/speed profiles. See `docs/regeneration_study.md` for the small single-seed advantage and grid-sensitivity limitation.


18 November 2026 update. The [completed regeneration multi-seed study](regeneration_multiseed_study.md) reports all three trained policies and links to the comparison plots and independent replay audit.


The [full-circuit DP study](regeneration_dp_study.md) compares all three final PPO policies with two feasible optimized schedules, reports planning and action-selection costs, and links to the dissertation figures.


18 November 2026. The [DP sensitivity study](regeneration_dp_factorial.md) identifies the contribution of retained search width and the interaction between action spacing and state bins. It includes all eight schedules and both dissertation figure pairs.
