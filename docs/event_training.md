# Event-based physical-model training gate

Prepared 28 October 2026. Training is blocked pending the coordinator's explicit numerical-validation pass for event_power_lap. The rejected spatial solver and previous constant-force environment will not be substituted for this experiment.

Planned protocol: synthetic power, aerodynamic drag and finite braking using the validated shared event transition; three independent PPO seeds with a measured CPU budget. Freeze a development scenario and a new evaluation scenario before training; compare zero, half and full deployment under the exact same initial/terminal constraints. Preserve actual optimizer updates, logs, checkpoints, reload equivalence, source hashes, input configuration and environment versions. Training results will be added only after they exist. No claim of real-circuit calibration is intended.

## Protocol fixed before solver approval

Development scenario: lengths400/400m, exit caps30/20m/s, initial speed20m/s, energy450kJ, reserve50kJ, default PowerVehicle. New evaluation scenario: lengths360/440m, exit caps28/20m/s, mass840kg, initial energy400kJ; all other vehicle values unchanged. It differs from the earlier force-model held-out mass/energy case and is declared before training. The observation is segment progress, speed/100 and fraction of usable battery energy; vehicle mass is not observed, so evaluation includes hidden parameter shift. No training or checkpoint selection uses evaluation outcomes.

PPO: CPU one thread,32x32 MLP, rollout256,batch64,10 epochs,gamma1.0,seed0/1/2. Target16,384 steps each, subject to a predeclared five-minute total initial training budget. Measure transition cost first; reduce to4,096 steps or another rollout-aligned budget if needed and record the reason. No convergence claim follows from a bounded pilot. Script retains actual progress.csv optimizer logs, checkpoint, exact reload verification, weight changes, environment lock, validation evidence and hashes.

## Numerical gate and measured budget — 29 October 2026

Coordinator approved event-validation-002 after numerical, analytic and physical checks. The training script independently checks passed status, summary SHA-256 against its manifest, and both current solver source hashes. Failed status, tampered reports and stale solver sources are rejected before output creation or training. Three wrapper/gate tests pass. Source hashes are frozen before training and checked again afterward.

100 nominal transitions required1.152616s (11.526ms each). Three4,096-step runs are estimated at141.634s for environment stepping before optimizer overhead; therefore the initial protocol uses4,096 steps per seed rather than16,384 to stay within the five-minute aggregate pilot budget. This reduction was based on execution cost before any training outcome. The nominal-only nine-sequence {0,.5,1}² reference is included as a tiny finite-action benchmark, not production DP or a continuous optimum.

## Interpretation rules for completed runs

The environment retains the original action fraction [0,1]; SB3 check_env recommends symmetric actions, but it does not reject this valid contract. Gamma1.0 makes episode return equal negative elapsed time. Every controller uses identical solver settings, initial state, reserve floor and final speed requirement within each scenario. The reserve is a common inequality, not a requirement to consume all energy. Record any infeasible trajectory as failure rather than rewarding an artificially short invalid lap.

The benchmark has only two action decisions per episode and all geometry is synthetic. A full-deployment baseline may equal the finite-action reference by spending usable energy in segment one. Later action changes then have no physical effect after depletion. Training weight changes establish optimizer execution, not intelligent strategy discovery or convergence. Three seeds quantify only this small pilot's variation; no real Formula One performance claim is supported. Evaluation remains fixed without checkpoint selection or hyperparameter tuning.


## Executed training results — 29 October 2026

Three independent runs completed4,096 steps each, with no source changes during training. All13 parameter tensors changed in each run; checkpoint reload produced exactly identical deterministic rollout records. All listed output hashes were independently recomputed and matched, including actual optimizer logs. All baseline/PPO trajectories met the shared energy reserve and terminal speed checks.

| Run | Training seconds | Nominal PPO seconds | New evaluation PPO seconds |
| --- | ---: | ---: | ---: |
| event-ppo-seed0-001 | 24.495 | 20.597676607 | 21.137077717 |
| event-ppo-seed1-001 | 24.458 | 20.713566815 | 21.214537246 |
| event-ppo-seed2-001 | 24.348 | 20.664870549 | 21.192869432 |

Total measured training time was 73.301 seconds, below the300-second initial budget. Nominal zero/half/full times were21.628379146/20.696253649/20.597676607 seconds. New evaluation zero/half/full times were22.046371770/21.193596555/21.137077717 seconds. The nominal nine-sequence reference achieved20.597676607 seconds with actions[1,0]. Seed0 matched the full baseline/reference; seeds1 and2 did not. The result supports a working physical-model training pipeline and documents seed variation, not PPO superiority or convergence.
