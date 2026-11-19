# Bahrain qualifying deployment at matched wheel work

**The selected allocation remained faster at both matched work levels.** Its advantage was 0.955 s at approximately 3.050 MJ and 0.871 s at approximately 2.989 MJ on the primary grid. On the finer grid the corresponding savings were 0.953 s and 0.870 s.

The original central-model deployment candidate saved about 0.99 s against ordinary adaptive spread on both grids. On the primary grid it delivered 3.050 MJ to the wheels versus spread's 2.989 MJ. This follow-up tests how much of the time difference remains when those wheel energies are matched. The same frozen model, geometry, 55 action spans and 80.653 m/s finish requirement apply. [Original comparison](bahrain_deployment_zones.md)

At both work targets the selected allocation spent energy earlier. By the end of the T1–T3 window at 1,172 m it had delivered about 939 kJ more wheel work than spread at the higher target and 904 kJ more at the lower target. Its leads were 0.621 and 0.599 s there. For the higher target the primary-grid sector gains were approximately +0.638, +0.527 and −0.210 s, giving a 0.955 s finish advantage. At the lower target the corresponding changes were +0.618, +0.501 and −0.249 s. Sector-crossing times are linearly interpolated between the saved block ends at the development lap's sector fractions. Speed carried into the following blocks affects these times. The work difference at the finish was below 0.25 kJ for both targets and grids. [Wheel work and time saved by distance](../figures/dissertation/bahrain-equal-work-v1/03_bahrain_matched_by_distance.pdf) · [Sector results](../results/bahrain-equal-work-001/location/metrics.json)

## Comparison design

- **Raise spread to the selected schedule's work.** At each decision, compute the ordinary adaptive spread request from the current simulator state. Multiply that request by α and cap it at 100%. Scan α from 0 to 4 in 0.25 increments. Replaying α = 1 must reproduce the archived spread trace exactly on both grids.
- **Reduce the selected schedule to spread's work.** Multiply each of the archived 55 requests by β. Scan β from 0 to 1 in 0.1 increments. The ordinary spread policy supplies the lower work target.

Each direction uses the archived 160-cell-per-block wheel work as its target. Bisect every sampled sign-changing bracket for at most 16 iterations to reach a tolerance of 0.5 kJ. Retain sampled points already within tolerance and the closest point if a bracket cannot attain tolerance. Replay the same multipliers at 320 cells per block and report their wheel-work error relative to that grid's archived reference. The finite scan can detect sampled crossings and near matches. Its resolution limits conclusions about other multipliers.

Each calculated trace is checked against the existing independent mechanical and battery audit and finish-speed tolerance. Positive time saving means the selected schedule or its scaled version was faster than spread. A comparison has a qualifying time saving only if both finish feasibly. The two directions answer the question at different total assist levels. Brake recovery and remaining battery energy can differ even when delivered wheel work is matched. The overall held-out vehicle-pace gate failed, so these are conditional model comparisons.

## Results

Each sampled scan found one sign-changing interval. The two matches finished within 4.3×10⁻¹⁴ m/s of the speed target. Both kept the work difference below the 0.5 kJ tolerance on the finer grid without multiplier retuning.

| Comparison | Cells per block | Spread lap (s) | Selected lap (s) | Scaled schedule work minus reference (kJ) | Time saved (s) |
|---|---:|---:|---:|---:|---:|
| Original spread against original selected | 160 | 89.408202 | 88.418230 | −61.437 | 0.989972 |
| Original spread against original selected | 320 | 89.286322 | 88.298069 | −60.414 | 0.988253 |
| Scaled spread (α = 1.09765625) against original selected | 160 | 89.373032 | 88.418230 | −0.098 | 0.954802 |
| Scaled spread (same α) against original selected | 320 | 89.251391 | 88.298069 | +0.042 | 0.953321 |
| Original spread against scaled selected (β = 0.946875) | 160 | 89.408202 | 88.537167 | +0.002 | 0.871036 |
| Original spread against scaled selected (same β) | 320 | 89.286322 | 88.416800 | −0.243 | 0.869522 |

For the original rows the work difference is ordinary spread minus the original selected schedule. The α root was bracketed by 1.0 and 1.25. The β root was bracketed by 0.9 and 1.0. The α = 1 trace reproduced both archived spread runs exactly. Sampled α = 0 and α ≥ 2.5 missed the terminal speed, as did β ≤ 0.4. All trial outcomes are saved.

Through 1,172 m, just after T3, the selected allocation had already used 939 kJ more wheel work than the work-matched spread at the higher budget and had gained 0.621 s. At the lower budget the corresponding differences were 904 kJ and 0.599 s. At the finish the work differences were within 0.5 kJ. This supports an advantage from the lap-wise allocation of assist within these two policy families. The estimated allocation effect includes the model's speed and recovery response.

At 160 cells, the scaled spread recovered 1.512 MJ and finished with 122.4 kJ. The original selected schedule recovered 1.490 MJ and finished with 100.3 kJ. At the lower budget, the scaled selected schedule recovered 1.491 MJ and finished with 169.6 kJ. Ordinary spread recovered 1.510 MJ and finished with 188.7 kJ.

## Audit and artifacts

Independent checks covered 43 trial traces and 85 manifest entries across the two comparisons. The largest block residuals were 2.65×10⁻⁸ J for work and 9.58×10⁻⁹ J for battery energy. The 160-cell scan plots show the crossing and finish-speed status of each sampled multiplier. The result files contain every test and the signed finer-grid residuals. [Scaled spread results](../results/bahrain-equal-work-001/metrics.json) · [Scaled selected results](../results/bahrain-equal-work-001/secondary/metrics.json)

1. Scaled spread scan and the higher work match. [PNG](../figures/dissertation/bahrain-equal-work-v1/01_bahrain_spread_work_match.png) · [PDF](../figures/dissertation/bahrain-equal-work-v1/01_bahrain_spread_work_match.pdf)
2. Scaled selected scan and the lower work match. [PNG](../figures/dissertation/bahrain-equal-work-v1/02_bahrain_selected_work_match.png) · [PDF](../figures/dissertation/bahrain-equal-work-v1/02_bahrain_selected_work_match.pdf)
3. Matched wheel work and time saved by distance at both budgets. [PDF](../figures/dissertation/bahrain-equal-work-v1/03_bahrain_matched_by_distance.pdf) · [Figure source](../scripts/plot_bahrain_matched_distance.py)

The primary study is generated by [compare_bahrain_equal_work.py](../scripts/compare_bahrain_equal_work.py) and the reciprocal test by [compare_selected_work.py](../results/bahrain-equal-work-001/secondary/compare_selected_work.py). The two input/source manifests bind the parent model, reference traces, simulator and generated artifacts. [Primary manifest](../results/bahrain-equal-work-001/manifest.json) · [Reciprocal manifest](../results/bahrain-equal-work-001/secondary/manifest.json)
