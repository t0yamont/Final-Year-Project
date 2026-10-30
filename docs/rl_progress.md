# Synthetic PPO pilot — 28 October 2026

Implemented `f1energy.rl.LapEnv` and `scripts/train_synthetic_ppo.py` against the shared lap transition. Observation is segment progress, speed/100 and remaining usable-energy fraction; action is requested electrical-force fraction in [0,1]. Reward is negative segment duration. Natural lap finish terminates; no artificial truncation is used. Reset after termination is required. Two wrapper tests passed, and SB3 check_env completed with a recommendation to use a symmetric action range. The current physical fraction contract remains explicit.

## Actual run

`results/synthetic-ppo-001` contains a real 16,384-step seed-0 PPO run on CPU, one Torch thread, a 32x32 MLP, 256-step rollout and batch size 64. Measured training time was 9.435 seconds. Versions: Torch 2.14.1, Gymnasium 1.4.0, Stable-Baselines3 2.9.2. A full environment lock, scenario configuration, checkpoint, metrics and SHA-256 manifest are saved. Checkpoint reload preserved deterministic evaluation actions. A separate weight-update check compared the trained model with recreated same-seed initialization. This is actual training, not a simulated log.

| Scenario | Zero | Uniform 0.5 | Uniform 1.0 | PPO |
| --- | ---: | ---: | ---: | ---: |
| Nominal training scenario, seconds | 28.997142 | 27.757070 | 27.761082 | 27.761082 |
| Held-out mass/energy perturbation, seconds | 29.468907 | 28.362190 | 28.512595 | 28.512595 |

All evaluated trajectories met the simulator's reserve and terminal-speed limits. The held-out scenario was declared before training: mass 880 kg and initial energy 350 kJ, compared with 800 kg and 450 kJ nominal. The scenario was evaluated only after training. It was not used for checkpoint selection.

PPO matches the full-request baseline in elapsed time and loses to the half-request heuristic in both scenarios. Battery feasibility reduces executable force after energy is spent; different later requested actions can therefore produce identical motion. No superiority claim is supported. The nominal scenario is training-domain evaluation; the second case is one synthetic out-of-distribution check, not a statistically general result. The policy does not observe mass directly, so that perturbation also tests behavior under hidden model change.

## Limits and next gate

One seed, four synthetic segments, force-based rather than power-based control, no aerodynamic drag or empirical calibration. This validates training/checkpoint/evaluation plumbing and produces a negative baseline comparison; it does not answer the F1 research questions. Further work requires richer verified dynamics, matched controller information, multiple independent seeds, DP convergence, sensitivity studies and audited telemetry. Tiny evaluation timing values are single measurements, not benchmark-quality inference estimates. CPU handled this pilot in seconds; a GPU upgrade is not justified by this measurement.

Run from the project root with PYTHONPATH=src: `.venv/Scripts/python.exe scripts/train_synthetic_ppo.py --output results/synthetic-ppo-NEW --steps 16384`. Output directories are immutable. Installation used official PyPI; this project's virtual environment was updated, with versions frozen in the run evidence. AI assistance: implementation, test execution, bounded training and interpretation above; no student reflection or real-data claim generated.

## Independent pilot seeds

The coordinator authorised two additional bounded seeds without changing the held-out case or hyperparameters. Seeds 1 and 2 completed 16,384 steps each in 9.215 and 9.260 seconds, respectively, saved separately as synthetic-ppo-seed1-001 and synthetic-ppo-seed2-001. All three seeds produced the same elapsed-time results shown above; this reflects similar saturated deployment behavior, not evidence of global optimality. Each run passed checkpoint-reload action parity. Seed 0 changed all 13 parameter tensors, with maximum absolute change 0.885434 versus recreated initialization; seeds 1 and 2 saved direct before/after weight-change checks. The earlier single-seed limitation is superseded by three small pilot seeds; the simplistic dynamics and tiny evaluation set remain material limitations. No tuning used held-out outcomes. Use --seed to reproduce these independent runs.
