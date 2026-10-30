# Local execution gates — 28 October 2026

The user authorised local execution of training and validation, superseding manual-only execution. Hardware observed: NVIDIA A16-16Q 16GB, 16 logical processors and approximately 64GB RAM. Initial small MLP training used CPU/one thread; a GPU speed advantage has not been benchmarked or claimed.

## Access and real data
After user-performed FastF1 sign-in, the CLI showed an inactive subscription. Observed access nevertheless succeeded: authenticated FastF1 loaded 277 session timing rows. Do not infer failure solely from account-status text. No credentials or tokens were inspected or recorded by agents.

The subsequent results/bahrain-2025-q-driver1-002 run completed, exporting three chronological laps. All seven checked channels have zero missing entries in those exports. They are pit-related diagnostic laps and do not establish a clean-lap dataset. Driver metadata contains 17 laps, four marked accurate without pit-in/out. Weather, deletion status and sampling gaps still require review before modelling inclusion. Earlier failed run 001 is preserved.

## Synthetic training and validation
35 integrated offline tests passed before final specialist handoff. Synthetic segment transitions model explicit acceleration and braking distance/time, electrical work and protected battery reserve. This force-controlled model omits drag, traction and regulation-specific power limits and has no real-circuit calibration. Its checks do not close the production simulator gate.

Three independent PPO seeds (0, 1, 2) each completed 16,384 steps, taking about 9.2–9.4 seconds on CPU. Each has checkpoint, metrics, configuration, dependency lock and hashed manifest in separate synthetic-ppo result folders. Checkpoint reload action parity is asserted in the run script.

All three yielded the same evaluated times: nominal PPO 27.7611s vs uniform-half 27.7571s; held-out mass/energy PPO 28.5126s vs uniform-half 28.3622s. PPO did not beat this heuristic. The small four-step problem and short budget do not establish convergence or general RL performance. The held-out scenario must not be reused to select hyperparameters for a claimed final test.

A coordinator diagnostic enumerated all 81 action sequences on the {0,0.5,1} grid for the nominal scenario: best 27.6517s. This is a discrete exhaustive reference, not production DP or a continuous optimum. Its record is work/exhaustive-pilot.json.

## Gate decisions
- Local execution infrastructure and synthetic PPO pipeline: pilot exercised successfully.
- Authenticated real-data acquisition: one-session pilot exercised successfully; quality gate remains open.
- Full physical simulator and calibration: open.
- Production DP, reconstruction and real-circuit PPO comparison: open.
- Final research conclusions and submission: open.

Next: audit clean-lap candidates and source gaps; develop a common power/drag/braking full-lap transition and physical DP; measure numerical convergence and calibration uncertainty before larger training budgets. Preserve the negative PPO result and do not describe these synthetic timings as real F1 gains.
