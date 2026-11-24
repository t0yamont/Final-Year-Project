# Bahrain energy scarcity experiment

The experiment asks which of the seven previously identified Bahrain deployment zones gives the largest lap-time benefit for an additional 20 kJ of electrical work at the wheels. A separate full-lap comparison tests whether the original deployment schedule survives a change in starting charge or braking recovery. [Frozen protocol](../configs/bahrain_energy_scarcity.json) · [Original zone map](bahrain_deployment_zones.md)

## Physical settings

The four cases cross starting battery charge of 2 or 1 MJ with a recoverable braking share of 40% or 20%. The share sets the fraction of mechanical braking work eligible for recovery. The model still applies the 120 kW power limit, charging losses and per-lap energy limits, so halving the eligible share need not halve the energy stored. All cases retain the calibrated Bahrain car, geometry, 100 kJ battery reserve and 80.65294 m/s rolling finish. Both inputs and all results are simulated.

## Reading the comparisons

- **Whole-lap schedules.** The frozen schedule contains the original 55 requests. The adapted schedule comes from a bounded search using the scenario’s starting charge and recovery share. Spread chooses its request from the energy and distance remaining. For equal-work comparisons, declare a lap-time saving only if both schedules finish feasibly, their delivered work differs by at most 0.5 kJ on both grids, and their individual and paired numerical checks pass. A separate comparison with three full final requests is explicitly labelled wherever used. It changes both schedules.
- **Local energy transfers.** Each scenario has a common background allocation. Each alternative adds the same 20 kJ to one of seven zones, with identical target work everywhere else. Putting the packet in A instead of B gives a pairwise time difference. There are 21 pairs per scenario. The model solves for actual requests at 160 and 320 integration cells per decision block and also replays the original 160-cell actions on the finer grid. A priority applies to this packet and background allocation. Close pairs can remain unresolved.
- **Motion evidence.** The circuit positions are simulated chainages. Existing separate-lap motion checks are strongest on the timing-line straight and appreciably weaker around T10. The timing experiments do not measure where a real team deployed energy. [Local motion support](../figures/dissertation/bahrain-zone-support-v1/zone_motion_support.pdf)


## Results

T10 and its exit was the fastest of the seven places for the extra 20 kJ in each case. It won all six head-to-head comparisons per case. Moving the packet from the timing-line straight to T10 shortened the fine-grid lap by 14.56 ms at nominal charge and 15.01 ms at low charge, to two decimal places at either recovery setting. All 84 pairings met the work and finish criteria. Of those, 76 had a resolved direction. T8 versus T11 and T13 versus T15 remained unresolved in each case. The largest change in a paired effect on either refinement check was 0.173 ms. [Paired transfer plot](../figures/dissertation/bahrain-energy-scarcity-v1/02_zone_transfers.pdf) · [All 84 transfers](../results/bahrain-scarcity-zones-001/pairs.csv)

| Scenario | Frozen schedule finish shortfall (m/s) | Adapted lap (s) | Adapted saving over spread at matched work (s) |
|---|---:|---:|---:|
| Nominal | 0.00000 | 88.298 | 0.953 |
| Low charge | 0.98243 | 89.114 | 0.633 |
| Low recovery | 0.00436 | 88.355 | 0.895 |
| Low charge and recovery | 0.98293 | 89.012 | 0.745 |

These are the 320-cell results. All four adapted schedules and scaled spread comparators finished feasibly on both grids at those work targets. The unchanged original schedule failed the 0.00001 m/s finish criterion in every stressed case. The low-recovery miss was small. Halving the recoverable share reduced realised recharge in the same frozen high-charge schedule by about 8 kJ, from 1,491 to 1,483 kJ. The bounded search returned a quicker candidate under combined scarcity than under low charge alone. Search coverage limits conclusions about the best physically attainable time. [Matched timing and auxiliary cases](../results/bahrain-energy-scarcity-comparison-001/matched_timing.csv) · [Timing comparison](../figures/dissertation/bahrain-energy-scarcity-v1/01_matched_timing.pdf)

The adapted planner assigned its largest total work among the seven zones to T1–T3 in every case, ranging from 638 to 827 kJ. Those totals cover five blocks and describe a complete schedule. The T10 result answers the narrower marginal question on the frozen experimental background. It can coexist with substantial deployment on the timing-line straight and in T1–T3. At T10 the existing model's speed RMSE on the two separate real laps was 8.08 and 9.94 m/s, so this location priority remains conditional on the simulation. [Planner power by distance](../figures/dissertation/bahrain-energy-scarcity-v1/03_planner_deployment.pdf) · [Zone-level wheel work](../results/bahrain-energy-scarcity-comparison-001/zone_work_and_power.csv)

## Reproduction

Independent replay applied the saved requests directly to the plant for 58 scored whole-lap files and 96 zone-test files. It reproduced blockwise speed, time, energy and finish classification, rechecked transferred work and numerical direction for all 84 pairs, and verified the two run manifests. All 148 project tests passed. [Planner audit](../logs/agent_tools/2026-11-22/bahrain_energy_scarcity_planners.json) · [Packet audit](../logs/agent_tools/2026-11-22/bahrain_energy_scarcity_zones.json) · [Figure and test checks](../logs/agent_tools/2026-11-22/bahrain_energy_scarcity_checks.json)

Run from the project root using the project virtual environment. Both study arms protect existing run directories. Use separate output directories for a new run and pass those paths to the plotting script. A versioned raw labels file contains a Windows encoding artefact in the T1–T3 display name. Its stable ID `t1_t3`, blocks 8–12 and delivered-work data are intact. The shared UTF-8 protocol and figures give the canonical spelling.

```powershell
$env:PYTHONPATH = 'src;scripts'
$env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe scripts/run_bahrain_scarcity_planners.py --output work/scarcity-repeat-planners
.\.venv\Scripts\python.exe scripts/run_bahrain_scarcity_zones.py --output work/scarcity-repeat-zones
.\.venv\Scripts\python.exe scripts/report_bahrain_energy_scarcity.py --planner work/scarcity-repeat-planners --swaps work/scarcity-repeat-zones --output work/scarcity-repeat-tables --figures work/scarcity-repeat-figures
```
