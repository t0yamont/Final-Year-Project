# Automatic MGU-K braking recovery - 17 November 2026

The current reference model includes automatic energy recovery during required braking. This supersedes the initial deployment-only scope. Run `regeneration-validation-001` validates the implementation and fixed-policy baselines; a subsequent 4,096-step CUDA PPO pilot is now complete (see below). Existing no-regeneration studies remain historical evidence.

## Model and assumptions

The existing event solver and circuit environment are extended with an optional `Regeneration` parameter object. `regeneration=None` preserves the original dynamics, six observations and output fields. The active study uses `configs/regeneration_study.json`; its regeneration settings augment the unchanged historical `configs/circuit_reference.json`. The older periodic-lap and synthetic runners remain no-regeneration routes; use the circuit control environment for this extension.

| Quantity | Setting | Evidence status |
|---|---:|---|
| Maximum mechanical recovery power | 120 kW | 2025-era MGU-K bound, mapped to wheels with no separate driveline loss model |
| Maximum recovered battery energy per lap | 2 MJ | 2025-era MGU-K-to-store transfer bound |
| Maximum discharged battery energy per lap | 4 MJ | 2025-era store-to-MGU-K transfer bound |
| Model battery upper energy bound | 4 MJ | Assumed model state ceiling, not measured physical battery capacity |
| Charging efficiency | 0.80 | Assumed constant mechanical-to-stored conversion |
| Eligible share of total mechanical brake force | 0.40 | Assumed rear recovery availability proxy, not a measured brake balance |
| Discharge efficiency | 0.90 | Existing assumption, unchanged |
| Initial battery / physical reserve | 2 MJ / 0.1 MJ | Existing experiment boundaries, unchanged |
| Entry / terminal speed | 70 m/s / 70 m/s | Existing experiment boundaries, equality checked |

Sources: [FIA 2025 Technical Regulations, Issue 3, Appendix 4](https://api.fia.com/sites/default/files/documents/fia_2025_formula_1_technical_regulations_-_issue_03_-_2025-04-07.pdf) and [McLaren MCL39 technical specification](https://www.mclaren.com/racing/formula-1/2025/mcl39-technical-specification/). Limits are represented at the declared model interfaces. This is not a regulation-complete car model: no MGU-H flow, shaft-speed/torque map, battery temperature, axle load transfer, combined slip or team-specific calibration is represented. Capacity, efficiency and brake share require sensitivity analysis before broad conclusions.

During required braking, total mechanical brake force remains `m*b`. Recovery force is `min(0.40*m*b, 120000/v)` while battery headroom and the recovery allowance remain. Friction supplies the remainder, so regeneration does not add braking authority or change the braking envelope. Drag remains unrecoverable. When the battery or allowance fills, the solver resolves that event and friction resumes the full braking demand. Recovery is automatic and independent of the deployment request. There is no simultaneous deployment and recovery.

The solver records mechanical recovery work, battery charge, gross battery discharge and charging losses separately. `battery_draw_j` continues to mean net depletion and may be negative. Independent identities are:

- Kinetic energy change = base work + electrical deployment work - drag work - friction work - mechanical recovery work.
- Final battery = initial battery - electrical deployment work / discharge efficiency + charge efficiency * mechanical recovery work.

Cumulative charge/discharge counters persist across cells and action blocks and reset only at episode reset. Recharging never replenishes the cumulative deployment allowance. Capacity saturation is independent of the physical reserve. The existing terminal guard remains optional and was unit-tested with regeneration, but these nominal circuit comparisons do not use it or claim its earlier robustness transfers.

## Controller interface and validation

The action remains one deployment fraction in [0,1]. Enabled observations have eight entries: the original six with available battery normalized against capacity minus reserve, followed by remaining recovery and deployment budget fractions. Zero budgets report zero. Old six-observation policies must not be loaded as regeneration-trained policies.

All 141 integrated tests passed, including eight focused regeneration tests: analytic force- and power-limited braking, capacity/recovery/coincident events, initially full battery, recharge and redeployment, cumulative budget exhaustion, invalid parameters, observations/reset and terminal-guard integration. Six disabled-regeneration segment cases exactly match archived solver output, including events and samples.

Twenty nominal Sakhir rollouts cover five fixed policies, recovery enabled/disabled, and 4,400/8,800 cells with 55 common action blocks. All twenty satisfy terminal speed, reserve and energy constraints. Independent arithmetic recomputed work/battery identities from saved traces; 37 manifest hashes verified. The existing training gate accepts this new evidence and rejects stale no-regeneration evidence after the source change.

Predeclared acceptance checks are relative lap-time difference <=0.005, within-mode gain difference <=0.05 s, and preservation of baseline ordering outside 0.02 s ties. Regeneration's maximum relative lap difference is 0.003552643 (0.355264%); maximum within-mode gain difference is 0.006584843 s. Both modes pass. This is bounded grid evidence, not proof of continuous-model convergence.

Additional descriptive diagnostics, not post-hoc acceptance thresholds: maximum coarse/fine difference in regeneration-versus-disabled gain is 0.008048073 s. All policies reach the 2 MJ recovery cap at both grids (differences below 2e-9 J); this saturation alone does not validate the recovery trajectory. Maximum final battery difference is 9,011.806 J for spread. A small learning gain or a battery-sensitive claim may require finer checks.

## Fixed-policy results

Fine-grid results, same model parameters and initial conditions:

| Policy | No recovery (s) | With recovery (s) | Time saved (s) | Final energy with recovery (MJ) |
|---|---:|---:|---:|---:|
| zero | 109.475206 | 109.475206 | 0.000000 | 4.000000 |
| half | 108.643983 | 107.720281 | 0.923702 | 0.100000 |
| full | 108.608107 | 107.687315 | 0.920792 | 0.100000 |
| spread | 108.679327 | 107.951854 | 0.727473 | 0.418289 |
| exit_boost | 108.628191 | 108.628191 | 0.000000 | 2.612301 |

Full request recovers 2 MJ, discharges 3.9 MJ and ends at the 0.1 MJ reserve. It is about 0.921 s faster with recovery. Zero deployment still harvests energy but never deploys it; exit boost already had enough initial energy for its requests, so these two policies gain no meaningful lap time. These are matched heuristic comparisons, not PPO improvements, statistical significance or optimality claims. All policies saturate the recovery allowance under the assumed nominal parameters; sensitivity to that allowance and efficiency remains important.

## Artifacts and continuation

- Protocol: `configs/regeneration_study.json`.
- Runner: `scripts/validate_regeneration.py`; physics: `src/f1energy/event_power_lap.py`; environment: `src/f1energy/circuit_control.py`.
- Traces, metrics, source/input/output hashes: `results/regeneration-validation-001`.
- Dissertation plots: `figures/dissertation/regeneration-v1/01_regeneration_comparison` and `02_battery_recovery`, each 300 dpi PNG and vector PDF. Both PNGs visually inspected for labels, clipping and data consistency. Lines in the battery figure connect action-block endpoints, not a continuous event-resolution trace.
- Tests, parity checks and independent verification: `logs/agent_tools/2026-11-17/regeneration_*`.
- Archived pre-change solver/environment/helper sources: `logs/agent_tools/2026-11-17/pre_regeneration_sources.zip`, with SHA-256 ledger. Historical run bytes are unchanged. Historical source-bound gates intentionally reject the current checkout; use the archived source in a separate reproduction copy, not by relaxing checks.

Next: a frozen regeneration multi-seed protocol with isolated evaluation and tighter paired grid checks, followed by a feasible optimization reference using the same regenerative constraints. Reassess terminal handling for stressed scenarios. Do not compare old no-recovery PPO directly against new recovery baselines as a learning claim. Test efficiency/recovery-share sensitivity before final conclusions; final-test telemetry remains untouched.

From the repository root in PowerShell, the accepted new baseline evidence is usable by the existing CUDA-only pilot:

```powershell
$env:PYTHONPATH='src'
$env:PYTHONDONTWRITEBYTECODE='1'
.venv/Scripts/python.exe scripts/train_circuit_ppo.py --baselines results/regeneration-validation-001 --output results/regeneration-ppo-pilot-001
```

This command produced the completed pilot below. Use a fresh output directory for another run; existing results cannot be overwritten. To reproduce validation, choose fresh output/figure directories and a matching `numerical_gate` in a new protocol copy; the runner refuses to overwrite existing results.

## Completed CUDA PPO pilot

Run `regeneration-ppo-pilot-001` used the existing frozen seed-0 pilot settings: 4,096 steps, 55 action blocks, 80 cells per block for training and 160 for fine replay. It trained from scratch with eight observations, automatic recovery and the same energy/boundary conditions as the regeneration baselines. No terminal guard was used. Training took 159.96 s; 13 parameter tensors, 13 gradient tensors and 26 Adam moment tensors were verified on cuda:0, NVIDIA A16-16Q. Peak PyTorch allocation was 17,157,632 bytes (about 16.36 MiB); vehicle integration remained on CPU.

| Quantity | Result |
|---|---:|
| Untrained deterministic lap, training grid | 109.850483 s |
| Trained deterministic lap, training grid | 108.060215 s |
| Trained deterministic lap, fine grid | 107.673673 s |
| Strongest fixed baseline, fine grid (full request) | 107.687315 s |
| Fine PPO advantage against full request | 0.013642 s |
| Training-grid PPO advantage against full request | 0.006883 s |
| Paired advantage coarse/fine discrepancy | 0.006759 s |
| Fine gain over zero deployment | 1.801534 s |
| Gain-over-zero coarse/fine discrepancy | 0.006571 s |
| Fine recovered / discharged battery energy | 2.0 / 3.9 MJ |
| Fine final battery / terminal speed | 0.1 MJ / 70 m/s |

Both trained replays are feasible. Exact checkpoint reload and the predeclared 0.05 s gain-over-zero discrepancy gate passed. Independent saved-trace accounting checked the untrained, trained coarse and trained fine replays; maximum block work residual was approximately 1.11e-8 J and battery residual 6.16e-9 J. Verification checked 22 pilot hashes and confirmed the reloaded policy uses eight observations and CUDA. Existing 141-test physics evidence remains applicable because no physics changed in this continuation; the plot change was verified by actual figure generation.

This pilot demonstrates working regeneration-aware GPU training and feasible replay. Its approximately 14 ms advantage is not established superiority: only one short seed was run and the paired grid discrepancy is approximately 7 ms. The absolute lap-time difference between grids also remains approximately 0.387 s. Predeclare multiple seeds and tighter paired numerical checks before attributing small differences to a better policy. These results do not establish robustness, optimality, empirical validity or battery-periodic race operation.

Two visually inspected 300 dpi PNG/vector PDF pairs are saved under `figures/dissertation/regeneration-ppo-pilot-v1`: `01_learning_and_comparison` and `02_policy_energy_speed`. The first shows stochastic training episodes and deterministic matched fine-grid comparisons; the second shows requested actions, battery energy and speed at decision boundaries. Zero request is the common no-deployment reference and can still recover energy. All displayed controllers use the regenerative model.

The existing plotting script now selects baseline trace filenames from their metrics and checks the pilot's recorded baseline-manifest hash, allowing both historical and regenerative studies. Original plot source is archived under `logs/agent_tools/2026-11-17/pre_regeneration_pilot_plot.py.txt`. Training artifacts include initial/final policies, checkpoints every 1,024 steps, episode/training logs, replay traces, metrics and hashes. No jobs remain running.


18 November 2026 update. The [completed regeneration multi-seed study](regeneration_multiseed_study.md) reports all three trained policies and links to the comparison plots and independent replay audit.
