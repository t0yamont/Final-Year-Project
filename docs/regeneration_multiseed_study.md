# Regeneration multi-seed study - protocol frozen 17 November 2026

Protocol: `configs/regeneration_multiseed_protocol.json`. Run: `results/regeneration-multiseed-001`. This study follows the regeneration pilot; all training starts afresh, including seed 0. Final-test telemetry is not used.

Three independent training seeds (0, 1, 2) receive 16,384 steps each. Constant PPO hyperparameters and the 0/4,096/8,192/12,288/16,384 evaluation schedule match the earlier learning-budget study. All workers require CUDA. Three processes share the GPU, with one Torch CPU thread per process; vehicle integration remains CPU work. Neither concurrent execution nor seeding implies bitwise reproducibility across future retraining runs.

The primary endpoint is the final deterministic policy from every training seed on the 8,800-cell grid, with 55 action blocks and eight observations. Five fixed action-noise seeds (101-105) are secondary evaluations nested within each training seed. Every evaluation restores Python, NumPy and Torch CPU/CUDA RNG states; each grid starts from the same action-noise seed. Separate evaluation environments preserve the training environment. Checkpoint reload must reproduce the deterministic paired replay exactly. No best-checkpoint or best-seed selection is permitted.

## Predeclared numerical checks

All final deterministic and stochastic policies must be feasible on their grids. The existing 4,400-to-8,800-cell gain-over-zero tolerance remains 0.05 s. New final evaluations also use 17,600 cells (320 per block):

| Fine-to-refined check | Acceptance threshold |
|---|---:|
| Absolute change in advantage over matched full request | 0.005 s |
| Absolute lap difference divided by refined lap time | 0.0025 |
| Absolute final battery difference | 10,000 J |
| Absolute recovered battery energy difference | 5,000 J |

The matched full-request comparator is preselected from pilot evidence, not selected after seeing the new seeds. Its own fine/refined feasibility, lap-time, terminal-energy and recovery checks must pass before training begins. Refined zero/full traces are computed once, hashed and shared by the workers. Physical recovery/deployment budgets, capacity/reserve, terminal speed and energy balances remain mandatory. All final deterministic and five stochastic pairs must satisfy the checks; a failed pair fails that seed's gate. Intermediate checkpoints are diagnostic and cannot replace the final endpoint.

The coordinator completes all seeds even when one returns a numerical-gate failure. Summaries include every completed seed; missing/crashed seeds are reported as missing, never replaced. All three must finish and pass for study acceptance. Thresholds will not be relaxed after seeing outcomes. Descriptive means, sample SD and ranges are not confidence intervals or evidence of statistical significance. A small positive advantage requires attention to its paired numerical discrepancy; passing a tolerance does not prove optimality or robustness.

## Evidence

The runner reuses the validated regenerative environment and model parameters; no physics change was made. `tests/test_multiseed_refinement.py` checks matched-baseline arithmetic and every new rejection condition; all 142 integrated tests passed before launch. The source versions preceding this extension are archived in `logs/agent_tools/2026-11-17/pre_regeneration_multiseed_sources.zip`. Original result bytes are retained.

## Completed results verified 18 November 2026

All three PPO policies completed 16,384 CUDA training steps each (49,152 total) on the regenerative Sakhir model. On the primary 8,800-cell grid, final deterministic laps averaged **107.494016 s** (sample SD 0.235700 s) against **107.687315 s** for full deployment, the fastest fixed baseline. Each seed finished faster, with gains ranging from 0.011612 to 0.459632 s. The mean gain was 0.193299 s. The spread across training seeds limits how precisely this gain can be predicted for another run.

| Seed | Primary lap (s) | Gain over full (s) | Refined lap (s) | Refined gain (s) |
|---|---:|---:|---:|---:|
| 0 | 107.227682 | 0.459632 | 107.041176 | 0.457617 |
| 1 | 107.675703 | 0.011612 | 107.486375 | 0.012419 |
| 2 | 107.578663 | 0.108652 | 107.394742 | 0.104051 |

All 18 final comparisons (three deterministic and 15 stochastic) passed the frozen refinement criteria. Doubling the evaluation grid to 17,600 cells changed the paired advantage by at most 4.684 ms against the 5 ms tolerance. Maximum relative lap-time change was 0.177% against 0.25%. Terminal energy differences were zero and recovered-energy differences were below 5e-9 J against the 10 kJ and 5 kJ limits respectively. The verifier checked 327 hashes, 89 saved replays and exact deterministic checkpoint reloads on all three grids. All three final deterministic policies finished at the 0.1 MJ reserve.

On the refined grid, full deployment took 107.498794 s and the deterministic PPO mean was 107.307431 s. Averaging the five stochastic evaluations within each seed first gave a primary-grid mean of 107.511994 s across training seeds. All three plotted learning curves, sampled-policy comparisons and refinement comparisons are available as 300 dpi PNG and vector PDF in [the dissertation figure folder](../figures/dissertation/regeneration-multiseed-v1/). See the [independent verification](../logs/agent_tools/2026-11-18/regeneration_multiseed_verification.json) and [training metrics](../results/regeneration-multiseed-001/metrics.json). The outstanding research comparison is a feasible optimization reference under these same braking, battery and finish constraints.


The [full-circuit DP study](regeneration_dp_study.md) compares all three final PPO policies with two feasible optimized schedules, reports planning and action-selection costs, and links to the dissertation figures.
