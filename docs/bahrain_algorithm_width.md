# Direct PPO and SAC training on calibrated Bahrain

The experiment tests whether learned controllers can retain enough charge and request enough power to meet the rolling finish target while minimising lap time. The original Bahrain calibration, planning search and failed transfer of twelve earlier policies remain separate studies. This experiment trains fresh policies directly on the central vehicle.

## What was held fixed

The two 64-unit actor layers were widened to 256 per layer in a second phase. Each method used seeds 0, 1 and 2, eight inputs, 55 actions per lap, 4,096 simulator decisions per seed, the same battery and brake recovery model, and an unchanged objective. PPO used a 32–32 critic and SAC used two 64–64 critics throughout. The reward added the time saved over the spread heuristic in each block and deducted a second for each m/s of finish-speed shortfall. A policy had to satisfy the original finish and energy constraints for its time to count. The terminal penalty was a training choice. It did not weaken the physical test.

Each PPO run used 256-step rollouts and ten optimisation epochs per rollout. SAC began learning after 256 interactions and sampled one minibatch every four interactions. The common interaction allowance amounts to about 74.5 simulated laps per policy. It makes the result specific to this training budget. The algorithms used different critic structures, updates, exploration and actor activations. Three seeds describe run-to-run variation. They provide little basis for ranking the algorithms across settings. [Frozen protocol](../configs/bahrain_algorithm_width.json) · [Run contract](../results/bahrain-algorithm-width-001/contract.json)

## Numerical and physical checks

Training used 80 integration cells per decision block. The five reference and diagnostic policies retained their finish-feasibility classifications at 160 cells. The planner’s advantage over spread changed by 1.28 ms. Deterministic evaluation used both 160 and 320 cells per block with the same actions available at the same 55 boundaries. Hashes link the frozen model, code, observations, checkpoints and traces. The independent energy check reconstructs battery and mechanical work from every saved block. [Preflight checks](../results/bahrain-algorithm-width-001/preflight.json)

## Finish feasibility and actor width

At both resolutions **0 of 12** policies met the Bahrain finish target. On the primary grid nine began the last 98 m at the 100 kJ reserve. Two PPO policies retained usable charge but requested zero assist. The remaining policy, PPO-256 seed 2, delivered 11.57 kJ in that block and still finished 0.627 m/s below target. The feasible planner delivered 47.15 kJ there and adaptive spread delivered 123.91 kJ. The failure can occur through early spending or through the final power request. Last-block work alone does not specify a feasible schedule because the speed on entering the block also depends on the earlier schedule.

| Actor | Feasible seeds at 160 / 320 cells | Primary-grid finish shortfall across seeds (m/s) | Mean shortfall (m/s) |
|---|---:|---:|---:|
| PPO 64 | 0/3 · 0/3 | 0.545–1.337 | 0.929 |
| SAC 64 | 0/3 · 0/3 | 0.854–0.875 | 0.865 |
| PPO 256 | 0/3 · 0/3 | 0.563–1.012 | 0.734 |
| SAC 256 | 0/3 · 0/3 | 0.841–0.874 | 0.857 |

Widening the actor reduced PPO’s mean finish shortfall by 0.195 m/s, with improvement in two seeds and deterioration in one. SAC’s mean decreased by 0.008 m/s. Neither intervention produced a feasible lap. The two benchmark laps took 88.418 s and 89.408 s at 160 cells, and 88.298 s and 89.286 s at 320 cells. The model-aware planning result therefore continues to supply the feasible Bahrain deployment evidence. [Every seed and both grids](../results/bahrain-algorithm-width-001/metrics.json) · [Paired comparisons](../results/bahrain-algorithm-width-report-001/comparison.json)

The GPU runs consumed 49,152 simulator decisions and 436.7 seconds of elapsed time, with six concurrent workers per width. PPO used 640 optimisation minibatches per seed and SAC used 960. Exact checkpoint reload reproduced all 1,320 recorded final-policy actions on both grids. Values of total and cumulative wheel work in the figure include the policies that missed the finish requirement. [Distance profiles](../results/bahrain-algorithm-width-report-001/distance_profiles.csv) · [Figure PDF](../figures/dissertation/bahrain-algorithm-width-v1/01_controller_comparison.pdf) · [300 dpi PNG](../figures/dissertation/bahrain-algorithm-width-v1/01_controller_comparison.png)

## Reproduction

Run from the project root with the project Python environment and `PYTHONPATH=src;scripts`. The training program requires CUDA. To inspect the existing study, use the verification command below. Use fresh output directories for a new run or report.

```powershell
.\.venv\Scripts\python.exe scripts/train_bahrain_algorithm_width.py --verify --output results/bahrain-algorithm-width-001
.\.venv\Scripts\python.exe scripts/report_algorithm_width.py --run results/bahrain-algorithm-width-001 --model results/bahrain-pace-calibration-001/model.json --circuit Bahrain --output work/bahrain-comparison --figures work/bahrain-comparison-figures
```
