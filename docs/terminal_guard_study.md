# Fixed terminal-reserve guard — predeclared 13 November 2026

Protocol: `configs/terminal_guard_protocol.json`. Runner: `scripts/evaluate_terminal_guard.py`. Guard: `src/f1energy/terminal_guard.py`.

The unchanged-policy sensitivity study remains failed in its high-drag case, with its original artifacts preserved. This new experiment asks whether one fixed, common terminal-reserve heuristic produces feasible deterministic replays before any further training. It does not solve the minimum terminal-energy requirement or supply a full-circuit optimization reference.

Every policy protects **250,000 J above the physical 100,000 J reserve** before the final one-of-55 action spans. At 55 decisions this is the last block; at 110 decisions it is the last two blocks, sharing the same physical cell boundaries. During this terminal span the guard releases the protected budget and forces full electrical request, subject to the original physical reserve, speed caps, braking and power constraints. The budget is one conservative assumed engineering choice intended to cover the short full-request span, not a calculated minimum or a guarantee. It will not be tuned within this experiment.

The guard subclasses the existing controller environment without changing hash-bound physics or controller sources. Its temporary integration reserve is restored with `try/finally`; returned observations are recomputed with the original reserve. Thus PPO's six observations and spread's remaining-energy calculation retain their original meanings. Requests must still be valid even when terminal deployment will override them. Traces record proposed and issued requests, integration floor, terminal overrides, action changes, depletion events and protected-floor depletion interventions. Battery energy is neither added nor clipped upward.

The four cases are nominal and drag 1.1 kg/m, each at 55 and 110 decisions. Every case evaluates the three original final 16,384-step CUDA PPO checkpoints and zero, half, full, spread and exit-boost request policies on exactly 4,400 and 8,800 physical cells. This is **64 deterministic rollouts**, with no training, checkpoint selection, parameter search or telemetry. All comparators receive the same guard. Guarded zero requests terminal assistance and is therefore no longer a zero-electrical-deployment diagnostic.

The runner verifies the original multi-seed study, each seed, baseline/numerical evidence and unchanged sensitivity manifests before evaluation. It records the new protocol and source hashes, CUDA checkpoint devices and source/input stability at completion. A fresh output directory is mandatory; errors, partial results and any failed fixed-guard experiment remain visible. The original failed sensitivity study is not required to become accepted and is never overwritten.

Original boundary, reserve, cap, mechanical work-energy and battery-accounting requirements remain in force. Every block additionally checks its battery identity and guard floor/action metadata. Coarse/fine relative lap-time discrepancy must be at most 0.005; gain discrepancy against the matching guarded-zero replay must be at most 0.05 s. Guarded-zero block times define the common reward reference. Their assignment after its physical replay only rebases reward bookkeeping: its original integration reward is also retained, without another rollout or action change.

For each case, report the strongest feasible guarded fixed baseline and all three PPO advantages only when all eight fine-grid policies pass the feasibility/accounting audits. Numerical failure still prevents case acceptance. Report mean, sample SD and range across the three training seeds; do not average incomplete seed groups. Preserve losses and failures without changing thresholds. Any successful result supports only this declared assumed-model replay matrix, without universal or recursive feasibility, convergence, optimality, significance or real-car accuracy claims.

## Implementation validation and execution status

Six targeted unit tests pass: exact guard-disabled full/spread replay; event-driven protected depletion and floor release with energy identities; original observations/spread reserve semantics; malformed requests during forced terminal deployment; impossible budget/span rejection; and reserve restoration after a physics exception. These synthetic tests establish wrapper behavior, not the feasibility of the planned circuit cases.

The fixed study was executed after implementation review. The command below reproduces the design; choose a new output directory because run001 is now complete:

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe scripts/evaluate_terminal_guard.py --output results/terminal-guard-NEW
```

Independent saved-artifact verification and dissertation figures follow execution; a failed fixed guard must remain a failed result and requires a separately declared next experiment.

## Completed results - 13 November 2026

`results/terminal-guard-001` completed all **64 deterministic replays**, and all four case-level feasibility/numerical gates passed. Every policy meets the original 70 m/s finish-speed condition and physical battery reserve. This includes both nominal/high-drag models at 55 and 110 decisions. The original unguarded high-drag failure remains unchanged in `results/circuit-sensitivity-001`; the new guard does not retrospectively make that study pass.

| Scenario | Decisions/lap | Mean PPO + guard lap (s) | Sample SD (s) | Strongest guarded fixed lap (s) | Mean advantage (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nominal | 55 | 108.379341 | 0.049578 | 108.606269 | 0.226928 |
| Nominal | 110 | 108.478940 | 0.062745 | 108.571421 | 0.092480 |
| Drag 1.1 kg/m | 55 | 108.891185 | 0.051095 | 109.104791 | 0.213605 |
| Drag 1.1 kg/m | 110 | 108.989280 | 0.060911 | 109.070322 | 0.081042 |

Exit boost plus the same guard is the strongest fixed comparator in all four cases. All three PPO-plus-guard seeds beat that matched comparator in each case. This is a comparison of complete guarded controllers: the terminal strategy was imposed by the guard, not learned in a new training run. Guarded zero also deploys energy at the finish and must never be relabelled as the original zero-deployment diagnostic.

### Feasibility/performance trade-off

At nominal 55, the mean guarded lap is **0.140950 s slower** than the previously feasible unguarded PPO mean 108.238391 s. The guard provides terminal-feasibility evidence under higher drag, at the cost of protecting energy that the original policy would have deployed earlier. It is not a free performance improvement. Fine-grid PPO final energy ranges from **0.175144 to 0.186410 MJ**, leaving about 75-86 kJ above the physical 100 kJ reserve. That unused margin is consistent with the intentionally conservative fixed budget; no reserve sweep or post-result tuning was performed.

The original high-drag 55 PPO policies finished near 69.695743 m/s. With the guard, every tested rollout finishes within 1.0e-13 m/s of 70 in these saved numerical results. This very small residual is numerical closure in the model, not physical measurement precision. The guard only limits available energy before the final span and requests deployment afterward; it does not add energy, reset battery state or directly correct speed.

At 110 decisions, guarded PPO remains faster than the strongest guarded fixed baseline, but the means are slower than the corresponding 55-decision means. The original 55-trained checkpoints and block-relative lookahead are unchanged. These results do not establish how separately trained 110-decision policies would perform or prove action-resolution convergence.

### Verification and provenance

The full integrated suite passes **133 tests**, including the six guard-specific tests. A focused independent code review checked reserve restoration, observation semantics, reward rebasing and comparison labels. The artifact report independently verifies **445 hashes and all 64 replay traces**: complete scenario/policy pairs, CUDA checkpoint records, scheduled floors/issued actions, intervention counts, block/global work-energy and battery identities, reward bookkeeping, terminal constraints, strongest-baseline selection and seed-level summaries.

Maximum coarse/fine gain discrepancy is **0.007412 s** (threshold 0.05 s); maximum relative lap-time discrepancy is **0.356915%** (threshold 0.5%). Maximum global mechanical energy residual is below 5.20e-8 J; global battery/work identity residual is below 1.17e-8 J. These calculations support the declared numerical checks, not empirical car validity. Source/config/checkpoint hashes were stable throughout. No telemetry or protected final-test modelling inputs were read.

Evidence: `logs/agent_tools/2026-11-13/terminal_guard_tests.txt`, `terminal_guard_001.txt`, `terminal_guard_report.txt`; independent arithmetic record in `figures/dissertation/terminal-guard-v1/verification.json`. The diagnosis recorded before the run is `logs/agent_tools/2026-11-13/terminal_failure_diagnosis.json`. Its approximately 18.9 kJ battery-equivalent kinetic deficit is explicitly a lower bound, not the selected 250 kJ guard budget or a solved minimum.

## Dissertation figures

Both figures are saved as 300 dpi PNG and vector PDF in `figures/dissertation/terminal-guard-v1`, visually inspected and hash checked:

- `01_feasibility_and_comparison`: all three PPO-plus-guard seed advantages over matched guarded baselines, with descriptive sample SD; paired original/guarded finish speeds for the high-drag 55 case.
- `02_guard_energy_actions`: high-drag 55 seed0 selected for illustration, showing protected battery energy and proposed/issued/mean-delivered deployment. Delivered power also responds to braking, cruise and depletion; issued request is not delivered electrical power.

Reproduce independent verification and figures with a fresh destination:

```powershell
.venv/Scripts/python.exe scripts/report_terminal_guard.py --input results/terminal-guard-001 --output figures/dissertation/terminal-guard-NEW
```

## Next research gate

This establishes a feasible guarded-controller comparison for the four declared cases. It is not a minimum-energy solution, continuous optimum, recursive guarantee or validation across the remaining mass/grip/smoothing scenarios. The guard has not been evaluated on every earlier sensitivity case. It also introduces a common controller constraint that must remain explicit in future comparisons.

Next establish a bounded, feasible full-circuit optimization reference using the same transition model and clearly matched controller constraints. A guard-constrained reference and an unrestricted terminal-feasible reference have different admissible controls and must be labelled separately. That will support the outstanding PPO-versus-optimization research question and help quantify the cost of the conservative terminal protection. Further robust GPU training should have a separately frozen protocol and retain these unchanged-policy results. No new controller training ran in this study. No jobs remain active.
