# Full-circuit regenerative optimization reference

The comparison uses the nominal Sakhir circuit, the common 70 m/s entry and required exit speed, 2 MJ initial energy, a 0.1 MJ reserve and automatic MGU-K braking recovery. All controllers issue one deployment fraction per block for 55 blocks. DP plans an open-loop schedule for a known lap. PPO uses its learned feedback policy on the same simulator. Both comparisons use the final deterministic endpoints established in the [regeneration multi-seed study](regeneration_multiseed_study.md).

At each block, forward dynamic programming branches the retained prefixes over a fixed action set. It advances each branch through the existing circuit environment with its exact speed, battery energy and cumulative charge and discharge. To bound cost, it groups successors by rounded state and keeps the quickest exact prefix in each group. If the remaining count exceeds the width budget, it orders the states by stored energy, divides them into equal-count groups and keeps the quickest prefix from each. Different prefixes in the same group can have different future values. Pruning therefore gives a feasible candidate and an upper bound on minimum lap time, without a certified gap to the global optimum.

The basic search used three action levels and retained up to eight states per block. The primary search used five levels and up to 16 states, halved the state bin sizes, and could retain the basic candidate if it was faster. Both planned on 4,400 cells. Each selected schedule was then replayed unchanged at 4,400, 8,800 and 17,600 cells. Selection used only search-grid time and feasibility. The frozen [protocol](../configs/regeneration_dp_protocol.json) defines the bounds and diagnostics. The primary comparison is the richer candidate on 8,800 cells. The separate 50 ms search-stability diagnostic measures the effect of the two search settings. Spatial validation measures paired time-gap changes against full deployment and each PPO seed (5 ms tolerance), absolute relative lap change (0.25%), terminal battery difference (10 kJ) and recovery difference (5 kJ).

On a four-block regenerative test circuit the unpruned implementation agreed with exhaustive enumeration over all 81 possible schedules. The test also checks bounded search width and retention of the incumbent. All 143 integrated tests passed. The circuit search uses CPU simulation. The PPO training cost comparison uses the previously recorded local GPU training times.

## Results on 18 November 2026

The bounded forward DP search produced a feasible 107.265878 s schedule on the primary Sakhir grid. It was 0.228138 s faster than the three-seed PPO mean and 0.421437 s faster than full deployment. PPO seed 0 finished 0.038195 s faster than this schedule. Both DP candidates passed the replay refinement checks. Increasing search resolution improved the scheduled lap by 0.208282 s, exceeding the 0.050 s search-stability tolerance. This result supports comparison with an achievable schedule. The remaining uncertainty is how much further a larger search could improve it.

| Controller | 8,800-cell lap (s) | 17,600-cell lap (s) |
|---|---:|---:|
| Full request | 107.687315 | 107.498794 |
| Basic DP | 107.474160 | 107.289376 |
| Refined DP (primary) | 107.265878 | 107.079709 |
| PPO seed 0 | 107.227682 | 107.041176 |
| PPO seed 1 | 107.675703 | 107.486375 |
| PPO seed 2 | 107.578663 | 107.394742 |

Against the primary DP schedule, PPO seeds 1 and 2 were slower by 0.410 s and 0.313 s. Doubling the replay grid changed the primary candidate's gap to any comparator by at most 3.16 ms (5 ms tolerance). The largest such change across both candidates was 4.55 ms. For the primary candidate, terminal energy agreed between grids and recovered energy differed by less than 3e-9 J. Independent checks covered 14 saved replays and 350 hash comparisons, including the action sequences, duration, energy balances and finish constraints. Both figure pairs were inspected and their file hashes verified.

The basic search expanded 1,086 block transitions in 41.23 s. The refined search expanded another 3,810 in 137.52 s. Producing both candidates took 178.75 s of CPU planning including the incumbent and exact search-grid replays. Separate fine-grid validation time is excluded. Previously recorded PPO training took 628 to 656 s per seed, with three concurrent GPU workers and CPU simulation. These are observed wall times on this machine.

For execution cost, the 55 CPU schedule lookups took 0.0013 ms per lap. The three CUDA PPO checkpoints took 33.1 to 40.1 ms per lap for 55 sequential deterministic predictions. Medians use 21 warmed repetitions and exclude observation construction, physics, loading and search. The timed predictions reproduced the saved actions. Schedule lookup is cheap because all actions are precomputed for one scenario. PPO evaluates a feedback policy on each observation. The timing experiment does not assess how either approach transfers to a different car or circuit.

[Saved schedules and traces](../results/regeneration-dp-001/) · [Verification and figures (PNG and PDF)](../figures/dissertation/regeneration-dp-v1/) · [Timing measurements](../logs/agent_tools/2026-11-18/regeneration_dp_cost.json)

The next bounded experiment should vary action spacing and retained-state width independently, keeping the primary PPO comparison fixed. This will test which approximation drove the 208 ms improvement. The present comparison alone cannot quantify PPO's distance from the true fastest feasible lap.


18 November 2026. The [DP sensitivity study](regeneration_dp_factorial.md) identifies the contribution of retained search width and the interaction between action spacing and state bins. It includes all eight schedules and both dissertation figure pairs.
