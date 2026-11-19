# Which DP search settings changed the Sakhir lap time?

The earlier [full-circuit DP study](regeneration_dp_study.md) found a 208 ms difference between two feasible deployment schedules. Three search settings changed together. This experiment crosses both values of each setting so that every direct comparison changes one setting at a time.

| Search setting | Low | High |
|---|---|---|
| Available deployment fractions | 0, 0.5, 1 | 0, 0.25, 0.5, 0.75, 1 |
| Maximum retained states per decision | 8 | 16 |
| State bins for speed and energy | 2 m/s and 200 kJ | 1 m/s and 100 kJ |

The energy bin applies to stored energy and both cumulative energy counters. These three bin sizes and the speed bin change together as one factor. The bit labels in the figures follow the table order, so 010 denotes three deployment fractions, 16 retained states and the original bins.

**Design.** All eight cases use 55 action blocks, 4,400 search cells, the same regenerative physics, and the same energy and finish constraints. The starting feasible schedule is full deployment. Search schedules are replayed unchanged on the primary 8,800-cell grid and the 17,600-cell check grid. The two diagonal cases come from the hash-verified parent study. The high-setting search previously inherited the basic schedule, but that incumbent affects final selection only. The high-setting winner was strictly faster than the basic incumbent, which was itself faster than full request, so starting it from full request gives the same schedule. The six mixed combinations were run locally on three CPU workers. The parent PPO and DP endpoints remain the predeclared model comparison.

**Interpretation.** A positive contrast means a shorter simulated lap after changing one setting. Each setting has four conditional contrasts, one for each combination of the other settings. The average of those four describes the factor across this design. To allocate the historical endpoint difference, we also start at the all-low corner and change one setting at a time until we reach the all-high corner. We average each setting's contribution across all six possible orders (Shapley allocation). This distributes interaction effects and sums exactly to the observed improvement. It describes this deterministic search and these parameter choices. The order-specific values are available in the verification record.

The [frozen protocol](../configs/regeneration_dp_factorial.json) specifies the 5 ms tolerance for changes in paired contrasts when moving from 8,800 to 17,600 cells. Verification checks exact schedules, search-grid replay times, finish speed, speed caps, energy balances and file hashes. A synthetic three-factor interaction test checks that the attribution and the ordinary factorial averages differ by the expected amounts. All 144 integrated tests passed.


## Results

Retaining 16 instead of eight partial schedules per block was the largest driver of the earlier 208.3 ms improvement. It saved 89.8 to 289.3 ms in all four matched comparisons. Averaged over the six orders of changing settings, retained width contributed +185.0 ms, finer state bins +35.1 ms and finer deployment spacing -11.8 ms. Positive values mean time saved. These contributions describe the tested search on nominal Sakhir.

| Deployment levels | Retained states | State bins | Lap on 8,800 cells (s) | Lap on 17,600 cells (s) | Block transitions |
|---:|---:|---|---:|---:|---:|
| 3 | 8 | Original | 107.474160 | 107.289376 | 1086 |
| 3 | 8 | Finer | 107.326733 | 107.141707 | 1167 |
| 3 | 16 | Original | 107.239229 | 107.053964 | 2133 |
| 3 | 16 | Finer | 107.155213 | 106.969181 | 2280 |
| 5 | 8 | Original | 107.432546 | 107.249348 | 1685 |
| 5 | 8 | Finer | 107.355659 | 107.171054 | 1890 |
| 5 | 16 | Original | 107.143225 | 106.955834 | 3460 |
| 5 | 16 | Finer | 107.265878 | 107.079709 | 3810 |

| Factor changed | Conditional savings range (ms) | Mean of four direct contrasts (ms) | Contribution to endpoint gain (ms) |
|---|---:|---:|---:|
| Three to five actions | -110.7 to +96.0 | -0.5 | -11.8 |
| Eight to 16 retained states | +89.8 to +289.3 | +196.4 | +185.0 |
| Original to finer bins | -122.7 to +147.4 | +46.4 | +35.1 |

The clearest interaction involves deployment spacing and state bins. With the original bins, adding action levels saved 41.6 ms at width eight and 96.0 ms at width 16. With finer bins, the same change cost 28.9 ms and 110.7 ms respectively. The search keeps a bounded frontier. Changing the action set or state grouping changes the prefixes competing for those places, even though all original actions are still available.

The fastest observed setting was five actions, 16 retained states and the original bins at 107.143225 s. This exploratory schedule was 122.7 ms faster than the earlier predeclared DP schedule and 84.5 ms faster than the fastest saved PPO seed on the primary grid. Selection from eight configurations makes this a descriptive sensitivity result. The original DP-versus-PPO endpoint and its failed search-stability diagnostic remain the historical comparison.

All 24 saved replays were feasible. Verification checked 54 hashes and all 12 paired contrasts passed the 5 ms grid tolerance. The largest contrast change was 4.19 ms. The diagonal improvement on the finer grid was 209.7 ms, allocated as +186.6 ms to width, +35.1 ms to finer bins and -12.0 ms to action spacing. Six new searches used 12,615 block transitions. A larger width could change which setting performs best. Search convergence remains open beyond the tested widths.

[Schedules, settings and traces](../results/regeneration-dp-factorial-001/) · [All conditional contrasts, change orders and checks](../figures/dissertation/regeneration-dp-factorial-v1/verification.json) · [Dissertation figures in PNG and PDF](../figures/dissertation/regeneration-dp-factorial-v1/).
