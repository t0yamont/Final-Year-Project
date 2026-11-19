# Regenerative Sakhir DP schedule imitation pilot

This pilot compares two supervised policy widths under one fixed budget on the assumed Sakhir model. [Run metrics](../results/regeneration-imitation-pilot-001/metrics.json) · [Frozen protocol](../configs/regeneration_imitation_pilot.json). It uses no measured telemetry and runs no new optimization search.

## Fit data and training

The robustness archive supplied four model-aware replans for the nominal case and the cases with 1 MJ initial energy, charging efficiency 0.6 and recoverable braking share 0.2. Each archive was replayed at 160 cells per decision block. All 55 unchanged observations were captured immediately before the corresponding requested action, for 220 scenario/block examples with 207 distinct feature vectors. The eight inputs use the existing environment's scaled progress, speed, usable battery energy, local cap, one- and two-block cap lookahead, and remaining recovery and deployment budgets. Request labels are the DP fractions, with no weighting or scaling. Full trace equality verifies the archived actions, timing and state evolution for each fit case. The baseline numerical gate and 137 robustness manifest entries were verified, and the [prefit contract](../results/regeneration-imitation-pilot-001/contract.json) binds protocol, input, source and dataset hashes.

Each model has two Tanh hidden layers of either 32 or 64 units followed by one linear output. Three seeds per width used standard PyTorch initialization and 500 full-batch float32 Adam updates at learning rate 0.003, minimizing MSE against the raw output. Inference clamps the requested fraction to [0, 1]. Final weights were used without selection or tuning. Parameters, gradients, Adam moments and step counters were on the NVIDIA A16-16Q. The plant remained on CPU. Each weight file reloaded exactly, with equality checked for all fit requests and every evaluated closed-loop request.

## Evaluation

Whole-scenario holdouts were initial energy 1.5 MJ, drag 1.05 kg/m and drag 1.10 kg/m. Nominal is an in-sample closed-loop diagnostic. The two intermediate cases match the predeclared PPO width transfers and carry no model-aware labels. The high-drag replan was used only after fitting, as an independent achievable reference. Each learned policy used its own state history, the common 55-decision cadence, automatic braking recovery and unchanged terminal feasibility criteria, at both 160 and 320 cells per action block. No corrective action or terminal guard was applied.

The comparison first checks physical feasibility. Width differences use elapsed time for width 32 minus width 64, with positive values favouring width 64 when both laps are feasible. The paired difference may change by at most 5 ms on refinement. Per-policy limits are 0.25% lap-time change relative to the finer grid, 10 kJ terminal battery-energy change and 5 kJ recovered-energy change. The audits reconstruct work and battery balances from saved block values and enforce power, reserve, recovery and deployment bounds.

## Fitting outcomes

| Hidden width | Parameters | Final raw MSE, seed 0 | Seed 1 | Seed 2 |
|---:|---:|---:|---:|---:|
| 32 | 1,377 | 0.084365 | 0.069598 | 0.081222 |
| 64 | 4,801 | 0.051012 | 0.069552 | 0.055774 |

Each fit took 0.46–0.50 s. The four reused teacher searches previously consumed 576.946 s summed across overlapping workers, excluding the cost of the initial basic incumbent and full archive and replay work. The fit time covers only the new model fitting. Each model had six CUDA gradient tensors, 12 CUDA Adam moment tensors and six CUDA step counters, each at step 500. Peak device memory recorded across these sequential fits ranged from 17.19 MB to 17.53 MB (decimal MB, process allocations). Deployment fractions predicted on the teacher trajectories are saved alongside labels. They summarize fitting to 220 correlated observations from four simulated laps. The closed-loop scores measure a different endpoint because acting changes future states.

## Final closed-loop comparison on the earlier reference vehicle

Both imitation widths finished all three nominal seeds with mean lap times of approximately 107.39 s on the primary grid. The corresponding PPO means were 107.49 s at width 32 and 107.29 s at width 64. All seeds of both methods finished under the 1.5 MJ and +5% drag conditions. At +10% drag all three seeds failed at both widths for both methods. The comparison figure reports the feasible count for each group. These networks were evaluated on the earlier reference vehicle. [Closed-loop figure](../figures/dissertation/ppo-imitation-comparison-v1/learned_controllers.pdf) · [Per-group results](../figures/dissertation/ppo-imitation-comparison-v1/summary.json)

