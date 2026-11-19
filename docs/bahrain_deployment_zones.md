# Bahrain deployment zones

The deployment map is a single-lap experiment for the timing-line-registered Bahrain pace model. Each scenario has the same entry and terminal speed, a 2 MJ initial battery charge, a 0.1 MJ reserve and the same regeneration limits. The prescribed drag-regime pattern is shared by all policies in a scenario. Lap time, assist and battery work are conditional simulations. Both separate qualifying laps met the declared lap and sector timing tolerances, but lap 10's speed RMSE was 5.36 m/s against the 5.0 m/s limit. The overall held-out pace gate failed. [Calibration scores](../results/bahrain-pace-calibration-001/metrics.json)

## Search and replay

The study uses the existing bounded forward dynamic-programming search. The controller requests one of 0%, 25%, 50%, 75% or 100% of the model's maximum wheel-assist power in each of 55 fixed geometry-parameter spans. A 40-cell search grid gives 2,200 spatial cells. At each decision the search retains at most 16 exact simulator states. It bins speed at 1 m/s and each of stored, gross recovered and gross discharged energy at 100 kJ. Outcomes characterize this finite search and model.

The quickest feasible search-grid schedule among full request, spread request, zero request and full request in only the final three blocks supplies the starting incumbent. The search then chooses the fastest feasible schedule on its own grid. Every selected schedule and baseline is replayed on independent 160- and 320-cell grids, with identical action boundaries. The full and spread baselines use their usual controllers at each grid resolution. Each alternative changes a single grip multiplier, scaling both the base and speed-dependent lateral acceleration terms by 0.95 or 1.05. Each receives an independent search and a transfer of the central scenario's selected schedule. The search reads the frozen model and has no access to lap telemetry.

Energy and work identities are recomputed from the saved replays. The reported feasibility checks cover the battery reserve and capacity, recovered and discharged lap budgets, energy balance, speed caps and equality of entry and finish speed. Individual grid diagnostics use the prior study's limits of 0.25% for lap time, 10 kJ for terminal charge and 5 kJ for recovered charge. Paired comparisons additionally track whether relative lap time moves by more than 5 ms across grids.

## Reading the map

The equal-wheel-work follow-up tests whether the gain persists when both schedules deliver the same total electrical work at the wheels to within 0.5 kJ. The location-based schedule gained 0.871–0.955 s on the primary grid across the two tested work budgets. Energy was used earlier through T1–T3, and some of the earlier lead was given back in sector three. [Matched-work results](bahrain_equal_work.md) · [Gain by distance](../figures/dissertation/bahrain-equal-work-v1/03_bahrain_matched_by_distance.pdf)

The model timing line is 0 m. Distances follow the reconstructed, smoothed centreline. Corner numbers are approximate visual landmarks from manual public markers checked against the 2025 FIA Grand Prix layout. Their display tolerance is approximately ±50 m. Each request window still follows the fixed simulation blocks. [Landmark provenance](bahrain_turn_landmarks.md)

The colour scale shows wheel work delivered divided by the full block duration. The second figure also shows requested wheel power, actual wheel assist and battery charge recovered in each block, cumulative gross battery flows and cumulative elapsed-time difference to the full and spread requests. Braking, speed caps and depleted battery can separate average delivered power from the controller's requested power. The CSV profiles retain values for each action span and policy.

Each mapped window is a maximal contiguous sequence of positive requests with at least 20 kJ of delivered wheel work on the stated replay grid. The four highest-energy central windows on the 160-cell replay were designated for one-block shift tests. A shift moves the original sequence of requests over one action boundary and needs a zero-request destination block on that side. Interventions stop at the timing line. The effect includes all resulting changes to actual wheel work, battery recovery and finish charge. Positive shifted-minus-selected time is a penalty. Feasible shifts with material grid-stable differences provide local evidence about timing.

Scenario overlap is calculated from block-level wheel work. A block counts as active at 10 kJ or more. The Jaccard score divides the number of shared active blocks by the number active in either case. The delivery overlap divides the sum of per-block minimum delivered work by the sum of per-block maximum delivered work. These checks assess sensitivity to the two declared perturbations.

## Feasible lap times and energy

The central search candidate finished in **88.418 s** at 160 cells per block and **88.298 s** at 320 cells. It saved **0.990 s** and **0.988 s** versus spread, the fastest feasible simple baseline on both grids. At 160 cells, the common 80.653 m/s finish was reached to floating-point precision by spread, the last-three-block rule and the selected schedule. Full request reached the battery reserve and missed the finish target by 1.010 m/s. Zero request missed by 1.558 m/s despite substantial stored energy.

| Central policy | 160 cells (s) | 320 cells (s) | Finish-speed error at 160 (m/s) | Wheel assist at 160 (MJ) | Recovered at 160 (MJ) | Discharged at 160 (MJ) | Final battery at 160 (MJ) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Selected | 88.418 | 88.298 | 0.000 | 3.050 | 1.490 | 3.389 | 0.1003 |
| Spread | 89.408 | 89.286 | 0.000 | 2.989 | 1.510 | 3.321 | 0.1887 |
| Final three blocks only | 90.947 | 90.830 | 0.000 | 0.458 | 1.442 | 0.509 | 2.9335 |
| Full request, infeasible | 88.917 | 88.796 | −1.010 | 3.058 | 1.498 | 3.398 | 0.1000 |
| Zero request, infeasible | 91.111 | 90.993 | −1.558 | 0.000 | 1.432 | 0.000 | 3.4317 |

Across the three search candidates, refinement changed absolute time by 112–129 ms (0.129–0.144%), final battery by at most 0.102 kJ and recovered energy by at most 1.839 kJ. The gains over spread shifted by at most 3.32 ms, and those over the final-three-block rule shifted by at most 4.22 ms. These feasible baseline comparisons met both grid criteria. The independent saved-replay audit checked 92 hashes and 60 rollouts. Across the 160/320-cell runs, the largest block-level residuals in the independent mechanical and battery balances were 2.65×10⁻⁸ J and 8.56×10⁻⁹ J, respectively.

## Central deployment windows

These are model-arc chainages from the timing line on the 160-cell replay. The reported power averages include each window's complete duration. Peak power is the largest block mean inside each window.

| Blocks | Chainage (m) | Approximate location | Wheel assist (kJ) | Mean / peak wheel power (kW) | Battery charge (kJ) |
|---|---:|---|---:|---:|---:|
| 1–4 | 0–393 | Timing-line straight | 469 | 106 / 120 | 0 |
| 7–12 | 590–1,172 | T1 approach through T3 exit | 826 | 74 / 120 | 259 |
| 20–21 | 1,855–2,051 | T6–T7 | 179 | 52 / 56 | 15 |
| 24–25 | 2,243–2,439 | T8 exit | 239 | 64 / 90 | 0 |
| 28–30 | 2,635–2,925 | T10 and exit | 398 | 65 / 120 | 92 |
| 35–37 | 3,318–3,610 | T11 and exit | 374 | 65 / 120 | 122 |
| 43–44 | 4,099–4,295 | T13 exit | 265 | 80 / 120 | 0 |
| 50–51 | 4,786–4,980 | T14–T15 | 253 | 57 / 90 | 136 |
| 55 | 5,274–5,373 | Approach to the timing line | 47 | 38 / 38 | <1 |

The T1–T3 window contained the most delivered energy. Its first block requested 30 kW, delivered no wheel assist and recovered 183 kJ to the battery. Subsequent blocks in the same window accelerated through T1–T3 and reached 120 kW block-average assist. The selected schedule gained 0.634 s over spread by 1,172 m and 1.224 s by 3,610 m, finishing 0.990 s ahead.

## One-block timing interventions

Differences are shifted minus selected. Positive time indicates a slower lap. Energy differences are on the 160-cell grid.

| Original blocks | Shift | Δ time at 160 (ms) | Δ time at 320 (ms) | Δ wheel assist (kJ) | Δ battery charge (kJ) | Δ finish battery (kJ) | Finish |
|---|---|---:|---:|---:|---:|---:|---|
| 1–4 | Earlier | — | — | — | — | — | Blocked at timing line |
| 1–4 | Later | +58.94 | +58.91 | 0.00 | +0.70 | +0.70 | Feasible |
| 7–12 | Earlier | +89.24 | +89.09 | −49.96 | +0.21 | +55.72 | Feasible |
| 7–12 | Later | +18.37 | +18.73 | −2.49 | −2.62 | +0.14 | Feasible |
| 28–30 | Earlier | +139.94 | +139.13 | −14.16 | +3.61 | +19.35 | Feasible |
| 28–30 | Later | +120.50 | +121.03 | +1.57 | +2.29 | +0.55 | Feasible |
| 35–37 | Earlier | +145.55 | +145.07 | −43.48 | +1.07 | +49.38 | Feasible |
| 35–37 | Later | +97.34 | +98.35 | +4.27 | +4.48 | −0.26 | Infeasible, −0.651 m/s at 160 |

All six feasible shifts cost time, with paired differences stable to 0.82 ms or better. Moving the initial straight window from 0–393 m to 98–491 m cost 59 ms with equal delivered wheel energy. Moving the T10 window from 2,635–2,925 m to 2,728–3,023 m cost 121 ms while delivering about 1.6 kJ more. Those comparisons show a timing effect at similar total wheel work. Moving the T11 window from 3,318–3,610 m to 3,414–3,708 m missed the finish-speed requirement on both grids.

## Grip sensitivity and transfer

| Grip multiplier | Selected 160 / 320 (s) | Spread 160 / 320 (s) | Full 160 / 320 (s) | Spread advantage 160 / 320 (s) | Active overlap with central | Energy overlap with central |
|---|---:|---:|---:|---:|---:|---:|
| 0.95 | 89.390 / 89.261 | 90.289 / 90.161 | 89.802 / 89.676 | 0.899 / 0.900 | 0.543 | 0.511 |
| 1.00 | 88.418 / 88.298 | 89.408 / 89.286 | 88.917 / 88.796 | 0.990 / 0.988 | — | — |
| 1.05 | 87.577 / 87.464 | 88.578 / 88.462 | 88.087 / 87.972 | 1.001 / 0.998 | 0.500 | 0.533 |

All full-request laps in this table missed the finish target on both grids. All spread laps and independently selected schedules were feasible. Sixteen blocks met the 10 kJ threshold in the independently selected schedule for every scenario on **both** replay grids. The ranges below come from the intersection of all six CSV profiles. Wheel work gives the minimum and maximum for the complete range across those profiles. Exact requests and delivered block energies shifted materially. The active-block counts and Jaccard overlaps agreed on both replay grids.

| Shared blocks | Model chainage (m) | Approximate location | Wheel work across scenarios and grids (kJ) |
|---|---:|---|---:|
| 1–3 | 0–295 | Timing-line straight | 309–406 |
| 8–12 | 687–1,172 | T1 through T3 exit | 690–827 |
| 24–25 | 2,243–2,439 | T8 exit | 239–389 |
| 28–29 | 2,635–2,826 | T10 and exit | 237–354 |
| 35–36 | 3,318–3,512 | T11 and initial exit | 171–329 |
| 43 | 4,099–4,197 | T13 exit | 167–220 |
| 51 | 4,882–4,980 | T15 approach and exit | 124–182 |

Under lower grip, the unchanged central schedule was feasible and beat the independently selected candidate by 92.0 ms at 160 cells and 89.4 ms at 320. This is a direct limit on the bounded search's performance. Under higher grip, the unchanged central schedule missed the terminal speed by 0.099 m/s and 0.101 m/s at the two resolutions. Transferring the actions across vehicles can change both timing and feasibility.

Across the seven recurring ranges, the timing-line straight has the smallest local speed discrepancy on each separate lap. Over the first 295 m the frozen quarter-request speed RMSE was 1.12 m/s on lap 4 and 0.66 m/s on lap 10. The shared T10 range scored 8.08 and 9.94 m/s and the T11 range scored 7.78 and 11.73 m/s. These are descriptive follow-up measurements in the full-lap fixed-request simulation. There are no observed assist labels at any of these locations. [Speed-error overlay](../figures/dissertation/bahrain-zone-support-v1/zone_motion_support.pdf) · [Local RMSE and delivered-work ranges](../results/bahrain-zone-support-001/metrics.json)

## Reproduction and figures

Run from the repository root. The versioned run contains the protocol, confirmed actions, saved traces including infeasible runs, block-level CSV profiles, chainages, audit metrics and hashes.

```powershell
$env:PYTHONPATH = 'src;scripts'
.venv/Scripts/python.exe scripts/map_bahrain_deployment.py --output results/bahrain-deployment-zones-001 --figures figures/dissertation/bahrain-deployment-zones-v1
.venv/Scripts/python.exe scripts/verify_bahrain_deployment.py results/bahrain-deployment-zones-001
```

Use new versioned output directories for a repeat. [Protocol](../configs/bahrain_deployment_zones.json) · [Metrics](../results/bahrain-deployment-zones-001/metrics.json) · [Manifest](../results/bahrain-deployment-zones-001/manifest.json)

1. Central model schematic coloured by delivered block-average wheel assist. The arrow shows travel direction across the approximate timing line. [PNG](../figures/dissertation/bahrain-deployment-zones-v1/01_bahrain_wheel_assist.png) · [PDF](../figures/dissertation/bahrain-deployment-zones-v1/01_bahrain_wheel_assist.pdf)
2. Requested and delivered power, recovery, cumulative battery flows and time differences on the 160-cell grid. [PNG](../figures/dissertation/bahrain-deployment-zones-v1/02_bahrain_deployment_profiles.png) · [PDF](../figures/dissertation/bahrain-deployment-zones-v1/02_bahrain_deployment_profiles.pdf)
