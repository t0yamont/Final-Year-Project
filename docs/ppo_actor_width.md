# Bounded PPO actor-width comparison

The two-layer width-64 actor finished faster than width 32 for every one of the three prescribed seeds, nominally and in both frozen transfers. All 36 physical replays and nine paired numerical comparisons passed. This is bounded, model-based descriptive evidence.

The frozen protocol is [regeneration_ppo_actor64.json](../configs/regeneration_ppo_actor64.json). The historical control is `results/regeneration-multiseed-001`; the new training run is `results/regeneration-ppo-actor64-001`. Both use training seeds 0/1/2 and exactly 16,384 CUDA PPO steps per seed. The primary endpoint is every seed's final deterministic policy on the 8,800-cell grid. No checkpoint or seed is selected for its observed outcome.

The actor changes from two 32-unit hidden layers to two 64-unit hidden layers. The critic remains two 32-unit hidden layers; its learned weights are not frozen. All other PPO settings, the eight observations, 55 decisions, physical model and training budget remain fixed. Independent random initialization at each width means matching seed labels does not make initial weights or learning trajectories identical, including the jointly trained critic. This is a descriptive fixed-budget comparison of two prescribed architectures, not a width sweep or evidence of optimal architecture.

The physical model uses automatic brake MGU-K recovery with the existing 120 kW mechanical power bound, 2 MJ gross battery recovery and 4 MJ gross battery discharge limits per lap. Battery capacity 4 MJ, charging efficiency 0.8 and rear braking share 0.4 remain assumptions. The nominal lap starts at 2 MJ and must finish at or above the 0.1 MJ reserve and exactly 70 m/s, with the common initial speed also 70 m/s. Both widths share the same solver and constraints. No telemetry is used to tune this comparison.

Two frozen, deterministic transfer cases change one nominal assumption each: drag coefficient 1.05 kg/m (from 1.0), and initial battery energy 1.5 MJ (from 2.0). There is no transfer retraining or terminal guard. Every saved final policy is evaluated in the nominal model and both transfers on 160 and 320 cells per block, giving 36 planned replays. Primary-grid times use 160 cells per block; 320-cell replays diagnose numerical sensitivity.

`scripts/evaluate_ppo_actor_width.py` validates immutable input/source/output manifests and the frozen historical manifest digest. It checks the actual saved policy tensor shapes, CUDA parameter devices, fixed critic dimensions and restored PPO scalar settings. Every nominal replay must exactly reproduce its saved training-run deterministic replay, including reward. The existing independent multi-seed verifier additionally checks all saved nominal intermediate/final deterministic and stochastic replays, arithmetic, GPU training proofs and checkpoint reload identity.

Transfer verification reuses the existing independent saved-trace auditor. It reconstructs block and global mechanical work, battery recovery and discharge, charging loss, power limits, rear braking share, capacity, reserve and terminal feasibility. An infeasible finish is retained with its measured speed error. Its elapsed time is descriptive and cannot support a feasible-policy speed advantage.

The frozen numerical limits are a 5 ms change in each same-seed width gap, 0.25% relative lap-time change for each policy, 10 kJ terminal energy difference and 5 kJ recovered-energy difference. Physical feasibility and numerical consistency are separate. A combined accepted comparison requires all planned pairs to meet both; thresholds are retained after observing results.

Evaluation evidence is cached separately under `results/ppo-actor-width-evaluation-001/actor-32` and `actor-64`. A precheck failure under `actor-32-failed-precheck` is retained: the first implementation compared nominal reward before restoring the original reference block times. The corrected evaluation sets the original reference times before exact replay comparison; physical predictions were unaffected. The original baseline folder is never modified.

## Observed outcomes

All 36 planned deterministic nominal and transfer replays were feasible. Width 64 was faster in all nine same-seed comparisons on both grids. All nine paired numerical checks passed. The nominal mean gain was **0.202801 s**, with a paired sample SD of **0.243854 s** and range **0.032473 to 0.482145 s**. This describes these three training seeds at the fixed budget; it does not establish a general architecture advantage.

The nominal deterministic mean (sample SD) was 107.494016 (0.235700) s for width 32 and 107.291215 (0.167720) s for width 64. Against the same nominal full-request fixed baseline (107.687315 s), the width-64 mean gain was 0.396099 s. The secondary nominal stochastic endpoint first averages five action-noise seeds within each training seed: the three training-seed means averaged 107.511994 s for width 32 and 107.391042 s for width 64 (between-training-seed sample SDs 0.177609 and 0.156113 s). These nested samples do not supply 15 independent training runs.

| Condition | Seed | Width 32 time (s) | Width 64 time (s) | Gain at 160 cells (ms) | Gain at 320 cells (ms) | Gap change (ms) |
|---|---:|---:|---:|---:|---:|---:|
| nominal | 0 | 107.227682 | 107.195210 | 32.473 | 33.034 | 0.561 |
| nominal | 1 | 107.675703 | 107.193558 | 482.145 | 479.328 | 2.817 |
| nominal | 2 | 107.578663 | 107.484879 | 93.783 | 98.478 | 4.694 |
| drag_1p05 | 0 | 107.471212 | 107.436865 | 34.347 | 34.973 | 0.626 |
| drag_1p05 | 1 | 107.893904 | 107.434791 | 459.113 | 460.621 | 1.508 |
| drag_1p05 | 2 | 107.813264 | 107.719809 | 93.455 | 97.904 | 4.449 |
| energy_1p5MJ | 0 | 107.489322 | 107.436392 | 52.929 | 53.608 | 0.678 |
| energy_1p5MJ | 1 | 107.809175 | 107.451870 | 357.305 | 358.806 | 1.500 |
| energy_1p5MJ | 2 | 107.817181 | 107.650876 | 166.305 | 170.287 | 3.982 |

| Condition | Mean gain (ms) | Paired sample SD (ms) | Gain range (ms) |
|---|---:|---:|---:|
| nominal | 202.801 | 243.854 | 32.473 to 482.145 |
| drag_1p05 | 195.638 | 230.082 | 34.347 to 459.113 |
| energy_1p5MJ | 192.180 | 153.829 | 52.929 to 357.305 |

The largest paired gap change was 4.694 ms (nominal seed 2), close to the frozen 5 ms limit. The largest individual relative lap-time change was 0.176142%, below 0.25%. Terminal battery differences were zero; the largest recovered-energy difference was 5.12e-09 J, below 5 kJ. Grid refinement changes absolute laps by approximately 0.18 to 0.19 s; comparisons rely on paired differences rather than treating the primary absolute times as exact.

Every replay in both widths, all seeds, both grids and all three conditions finished with 0.100000 MJ and zero recorded terminal-speed error. Gross battery recovery was 2.000000 MJ. Gross discharge was 3.900000 MJ nominally and under higher drag, and 3.400000 MJ with 1.5 MJ initial energy. These shared totals do not mean identical deployment schedules. The largest reconstructed block work residual was 2.03e-08 J, battery residual 7.01e-09 J, and global mechanical work residual 5.44e-08 J. All original physical limits and the feasibility condition remained in force.

The original independent verifier passed separately for both training runs: 327 hash checks and 89 saved replay audits per run, all three completed seeds accepted, all 18 final deterministic/stochastic nominal refinement pairs accepted and exact checkpoint reloads. The separate width report rechecked 70 bound cache/input/source/output hashes. Its [verification record](../figures/dissertation/ppo-actor-width-v1/verification.json) contains all 36 rows, per-policy numerical metrics and all nine gap checks. The [300 dpi figure](../figures/dissertation/ppo-actor-width-v1/01_actor_width.png) and [vector PDF](../figures/dissertation/ppo-actor-width-v1/01_actor_width.pdf) show every seed; the PNG was visually inspected.

## Parameters and observed training cost

| Width | Actor parameters, including log standard deviation | Critic parameters | Total | Training seconds by seed 0 / 1 / 2 |
|---|---:|---:|---:|---|
| 32 | 1,378 | 1,377 | 2,755 | 656.01 / 627.52 / 645.62 |
| 64 | 4,802 | 1,377 | 6,179 | 648.11 / 636.12 / 640.13 |

The larger actor has 3.485 times as many actor parameters and the combined policy has 2.243 times as many parameters. The critic architecture and parameter count are unchanged. Training times are observed historical/new-run process times and include differing machine contention; they are not a controlled speed benchmark. Each width used 49,152 training steps total, with three concurrent CUDA workers and CPU physics. Replay verification adds compute but no learning steps. Saved checkpoints and all earlier results are retained.

A separate [cost measurement](../results/ppo-actor-width-cost-001/metrics.json) used the NVIDIA A16-16Q after transfer evaluation finished: three warm-ups, then the median of 21 synchronized batch-one repetitions for each policy, with the same saved nominal observations. It excludes solver integration, loading and observation construction. The [cost figure](../figures/dissertation/ppo-actor-width-cost-v1/actor_width_cost.pdf) records the measured overhead.

| Width | Deterministic actor weights (excluding log standard deviation) | Weight bytes | Warm inference for 55 actions by seed 0 / 1 / 2 (ms) | Per-worker peak allocated training memory (MiB) |
|---|---:|---:|---|---:|
| 32 | 1,377 | 5,508 | 33.7814 / 33.2547 / 32.5845 | 16.36426 |
| 64 | 4,801 | 19,204 | 34.5554 / 33.1522 / 33.8254 | 16.42627 |

The per-seed warm inference medians average 33.2069 ms for width 32 and 33.8443 ms for width 64. These small measured differences include framework/CUDA overhead and do not establish a portable latency ratio. Training memory excludes driver/context reservations. Parameter counts in this table exclude the scalar log standard deviation used by the stochastic Gaussian policy; the architecture table includes it. The critic is excluded from deterministic action inference.

## Retest of the known 10% drag increase

The primary transfer experiment used 5% higher drag. A separate secondary check returned to the historical 10% increase where the original controller had failed. The new check used every final width-64 checkpoint, the same physical constants and finish condition as the published failure, and the same two replay grids. All six distinct PPO policies across the two widths missed the 70 m/s finish on both grids. They finished at 69.6957 m/s on the primary grid and 69.7009 m/s on the refined grid.

The saved traces show where the difference arose. At the end of block 51 on the primary grid, all six PPO policies were travelling at 38.83 m/s and had reached the 100 kJ battery reserve. They delivered zero electrical work in block 52. At the same speed and position, the informed DP schedule still had 251.8 kJ in the battery. It delivered 136.7 kJ of electrical work at the wheels in block 52 and reached the required finish speed. Width improved nominal elapsed time while leaving this particular energy-allocation failure intact. This is a diagnostic on a previously analysed stress case. [Wider policy replays](../results/ppo-actor64-high-drag-001/) · [Earlier DP and PPO replays](../results/regeneration-robustness-001/high_drag/) · [Finish-speed figure](../figures/dissertation/ppo-actor64-high-drag-v1/finish_speed.pdf)

## Reproduction

From the repository root, using PowerShell and fresh output paths if re-running:

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe scripts/verify_circuit_multiseed.py --input results/regeneration-ppo-actor64-001 --output logs/agent_tools/2026-11-18/ppo_actor64_independent_verification.json
.venv/Scripts/python.exe scripts/evaluate_ppo_actor_width.py --width 32
.venv/Scripts/python.exe scripts/evaluate_ppo_actor_width.py --width 64
.venv/Scripts/python.exe scripts/evaluate_ppo_actor_width.py
```

The script refuses to overwrite a completed per-width cache or figure folder. The final report figure is a 300 dpi PNG and vector PDF in `figures/dissertation/ppo-actor-width-v1`, with input/source/output hashes. The verification JSON contains all per-seed rows, architecture counts and grid comparisons. Three training seeds and two synthetic parameter transfers do not establish statistical significance, convergence, universal robustness, real-car validity or optimality. Finite numerical agreement constrains the tested differences only; the assumed vehicle, circuit geometry and simplified electrical system retain their existing modelling limitations.
