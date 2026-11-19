# How much does a wider DP search improve the Sakhir schedule?

Doubling the number of retained states from 32 to 64 saved 57.2 ms on the primary grid. That exceeds the declared 50 ms stability tolerance. The strongest schedule found so far is feasible, and its gap to the true minimum remains unknown.

The [frozen width protocol](../configs/regeneration_dp_width.json) held the 55 decisions, five deployment levels, 2 m/s speed bins and 200 kJ energy bins fixed. Each independent search started from a full-request incumbent and used 80 integration cells per block. Width 16 came from the verified [factorial experiment](regeneration_dp_factorial.md). Widths 32 and 64 were new local CPU searches. Every schedule was replayed unchanged at both reporting resolutions. The stopping width of 64 was specified before the new runs.

| Maximum retained states | Block transitions | Search wall time (s) | Primary lap, 8,800 cells (s) | Check lap, 17,600 cells (s) |
|---:|---:|---:|---:|---:|
| 16 | 3,460 | 128.2 | 107.143225 | 106.955834 |
| 32 | 6,065 | 223.9 | 107.113956 | 106.926996 |
| 64 | 9,050 | 325.6 | 107.056747 | 106.869681 |

The first doubling saved 29.3 ms on the primary grid and 28.8 ms on the check grid, within 50 ms on both. The second saved 57.2 and 57.3 ms respectively. Both paired improvements changed by less than 0.5 ms on replay refinement, within the 5 ms numerical tolerance. Thus the larger search changed the comparative result even when the integration grid had little effect on the measured improvement. Width 64 gained 170.9 ms against the fastest deterministic PPO seed on the primary grid. This post-sensitivity comparison is exploratory. Use the original 107.265878 s DP schedule for the predeclared comparison and transfer experiments.

All nine search-grid and evaluation-grid replays passed feasibility and work/energy checks. Verification checked 57 file hashes, exact actions, time sums, finish speed and speed caps. The width-16 cost came from the earlier run. New search times reflect machine load during the experiment. [Saved schedules and traces](../results/regeneration-dp-width-001/) · [Independent replay audit](../figures/dissertation/regeneration-dp-width-v1/verification.json) · [Width comparison figure](../figures/dissertation/regeneration-dp-width-v1/width_comparison.pdf)

To reproduce, run `scripts/run_regeneration_dp_width.py --output results/regeneration-dp-width-NEW` followed by `scripts/report_regeneration_dp_width.py --run results/regeneration-dp-width-NEW --figures figures/dissertation/regeneration-dp-width-NEW` with the project Python environment and `PYTHONPATH=src`.
