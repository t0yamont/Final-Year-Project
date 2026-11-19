# Regenerative controller robustness and model-aware replanning

Study: `results/regeneration-robustness-001`; frozen protocol: `configs/regeneration_robustness_protocol.json`. This is an assumed-model one-factor transfer study, with no retraining and no final-test telemetry. Nominal is retained as the matched control. The three original final regeneration PPO checkpoints (seeds 0/1/2, 16,384 steps) supply deterministic CUDA predictions; vehicle integration remains on CPU. At most three scenario workers run concurrently.

## Frozen comparison

The five scenarios are nominal, 1 MJ initial battery energy (nominal 2 MJ), charging efficiency 0.6 (nominal 0.8), recoverable rear braking share 0.2 (nominal 0.4), and drag coefficient 1.1 kg/m (nominal 1.0). Exactly one assumption changes in each stressed scenario. Values were committed to the protocol and hashed in the run contract before any scenario outcome. They are sensitivity assumptions, not measured uncertainty bounds.

Every case compares five unchanged fixed policies (`zero`, `half`, `full`, `spread`, `exit_boost`), all three frozen final PPO seeds, the unchanged original **refined** DP schedule from `regeneration-dp-001`, and a separately model-aware DP replan. The frozen comparator is not replaced by the later factorial winner or wider-search candidate. No terminal guard is added.

Each model-aware search uses the original refined settings: five requests {0, 0.25, 0.5, 0.75, 1}, retained width 16, 1 m/s speed bins, 100 kJ bins for stored/recovered/discharged energy, 80 cells per block, and 55 decisions. The **same original basic DP schedule** supplies the incumbent in all five scenarios, matching the original refined search's starting schedule. Each case receives one bounded search (at most 4,400 block expansions) with no tuning/retry or PPO incumbent. This is a common computational budget, not a proof of global optimality. The nominal replan must reproduce the original refined schedule and search-grid time.

Primary and check replays use 160 and 320 cells per action block (8,800/17,600 cells). All controllers share each scenario's physical model and constraints: 120 kW electrical deployment/mechanical recovery limits, 4 MJ capacity, 2 MJ gross recovery and 4 MJ gross discharge limits per lap, 0.1 MJ physical reserve and 70 m/s initial/terminal speed. Recovery substitutes for friction braking at unchanged required deceleration. The terminal equality remains a feasibility requirement.

## Checks and failure handling

`report_regeneration_robustness.py` verifies the run/input/source/output hashes, then independently reconstructs saved block work-energy and battery balances, charging loss, deployment/recovery power and budget bounds, rear braking share, capacity/reserve bounds, action identity for both DP schedules, and terminal feasibility. It verifies search layer counts and the bounded retained frontier for completed searches. A focused test exercises every one-factor transformation and rejects a corrupted saved battery trace.

Frozen refinement thresholds are 5 ms paired advantage change, 0.25% relative lap-time change, 10 kJ terminal energy difference and 5 kJ gross recovery difference. Every available controller pair is checked. Physical feasibility and numerical agreement are reported separately: an infeasible trajectory can have small numerical errors. Missing replans fail their planned comparisons. A bounded search that finds no terminal-feasible path is retained as failed, with no invented replacement schedule; it does not prove that the physical scenario has no feasible solution.

## Verified outcomes

All five scenario searches completed and produced a schedule. All 100 planned replays ran. On each grid 43 of 50 controllers met the physical requirements. The seven failures on each grid occurred under higher drag. Times below are from the 8,800-cell primary grid. Each PPO mean uses all three seeds or is left blank when they missed the finish condition.

| Scenario | Feasible controllers (of 10) | Fastest feasible fixed policy (s) | PPO mean (s) | Transferred DP (s) | Replanned DP (s) | Largest change in paired gap on refinement (ms) |
|---|---:|---|---:|---:|---:|---:|
| Nominal | 10 | Full, 107.6873 | 107.4940 | 107.2659 | 107.2659 | 5.952 |
| Initial energy 1 MJ | 10 | Full, 107.9929 | 107.8967 | 107.8418 | 107.7117 | 3.963 |
| Charge efficiency 0.6 | 10 | Half, 107.7203 | 107.5306 | 107.2659 | 107.1522 | 7.356 |
| Recoverable brake share 0.2 | 10 | Half, 107.7203 | 107.5100 | 107.2580 | 107.1481 | 7.390 |
| Drag coefficient 1.1 kg/m | 3 | Spread, 108.4296 | — | 107.7742 | 107.7542 | 4.315 |

In the high-drag case each PPO policy fell about 0.304 m/s short of the 70 m/s target on the primary grid. The spread heuristic and both DP schedules met the finish condition. The informed replan gained about 20 ms over the transferred DP schedule in this case and about 130 ms under reduced initial energy. The nominal replan reproduced the original schedule exactly. An informed planner knew which parameter had changed. That information advantage matters when interpreting these times.

All 50 individual controller/grid comparisons passed the absolute time, final energy and recovery refinement checks. Checking all 45 pairwise time differences per scenario found 5, 0, 6, 5 and 0 violations of the 5 ms tolerance in the table order. The nominal worst pair was half request versus PPO seed 1. The earlier nominal PPO-versus-full comparison retains its own predeclared pass. The robustness study as a whole fails its combined feasibility and numerical criteria. Each failure and its measured size is retained. [100 verified replays and 137 hash checks](../figures/dissertation/regeneration-robustness-v1/verification.json) · [Controller times and feasibility](../figures/dissertation/regeneration-robustness-v1/01_transfer_feasibility.pdf) · [Feasibility and grid checks](../figures/dissertation/regeneration-robustness-v1/02_feasibility_grid_checks.pdf)

## Reproduction

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH='src'
.venv\Scripts\python.exe -m unittest discover -s tests -p test_regeneration_robustness.py -v
.venv\Scripts\python.exe scripts/run_regeneration_robustness.py --output results/regeneration-robustness-NEW
.venv\Scripts\python.exe scripts/report_regeneration_robustness.py --input results/regeneration-robustness-NEW --figures figures/dissertation/regeneration-robustness-NEW
```

Run and figure directories refuse overwrite. Original results and checkpoints are preserved. Execution/test logs are under `logs/agent_tools/2026-11-18/regeneration_robustness_*`. Figure manifests bind the verifier source, run manifest, verification output and 300 dpi PNG/vector PDF exports.
