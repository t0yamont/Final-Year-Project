# Unchanged-policy sensitivity study — predeclared 12 November 2026

Protocol: `configs/circuit_sensitivity_protocol.json`. Runner: `scripts/evaluate_circuit_sensitivity.py`. The design below was predeclared before execution; completed results and failures follow the protocol description.

Reuse all three final 16,384-step CUDA PPO checkpoints from `results/circuit-multiseed-001`, without learning or selecting a checkpoint. Evaluate deterministic feedback transfer against zero, half, full, spread and exit-boost deployment. Every comparison uses 70 m/s entry and verified terminal speed, 2 MJ initial battery and 0.1 MJ reserve. The source study, nested numerical/controller evidence, checkpoints, geometry and supporting sources must pass their saved hashes before evaluation. No telemetry is read.

Nine cases at the trained 55-decision cadence vary one assumption at a time: nominal, mass 720/880 kg (nominal 800), drag 0.9/1.1 kg/m (nominal 1), lateral acceleration 18/22 m/s² (nominal 20), and Gaussian geometry smoothing 5/20 m (nominal 10). These are declared perturbations rather than calibrated uncertainty bounds. All unvaried assumptions remain fixed. Smoothing changes the reconstructed path and its integrated length; each policy shares its scenario's geometry. This bounded study does not estimate parameter interactions.

Nominal conditions additionally compare 55 with 110 decisions. Use 80/160 cells per block at 55 decisions and 40/80 at 110, giving exactly the same 4,400/8,800 physical cells and boundaries at both cadences. The policy receives the existing six observations at each decision, including normalized progress and one/two-block lookahead. Consequently the 110-decision interface halves the physical lookahead. This measures unchanged feedback-policy transfer under the changed interface; it does not duplicate previously recorded actions or establish how a policy trained at 110 decisions would perform. Any retraining requires a separate protocol.

The complete design has ten scenario/cadence cases, eight policies and two grids: **160 deterministic rollouts**. Keep all seeds and all negative results. The primary endpoint is each seed's fine-grid advantage against that case's strongest matched fixed baseline, summarized with mean, sample SD and range across three training seeds. Also report each unchanged policy's nominal 110-minus-55 lap-time change. These three trained models support descriptive variation, not significance claims; scenarios are not independent trained replicates.

Numerical acceptance requires feasible boundaries/reserve/speed caps, mechanical work-energy and battery identities for every rollout, at most **0.5%** coarse/fine absolute lap-time difference relative to fine time, and no more than **0.05 s** coarse/fine difference in time gain against that case's matching zero-request baseline. Nominal 55-decision checkpoint replays must exactly reproduce saved source lap times, energies and actions. A positive advantage is not an acceptance criterion: a numerically valid loss remains a valid sensitivity result. No ranking-preservation requirement is introduced for the deliberately varied action interface or model.

Use a new output directory. The runner writes its contract before evaluation, then scenario grids, compressed per-policy traces, progress, metrics, failure records when needed, and a manifest binding inputs, sources and outputs. It checks source/input stability at completion. A failed or incomplete rollout makes the study unaccepted and must remain visible; incomplete seed groups are not averaged. Output directories cannot be resumed or overwritten. Existing source-run bytes stay unchanged.

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe scripts/evaluate_circuit_sensitivity.py --output results/circuit-sensitivity-001
```

The implementation requires CUDA and checks loaded policy parameters on the GPU; vehicle integration and geometry remain on CPU. `require_cuda` exercises a separate dummy CUDA optimizer to validate the device; it does not update any transferred policy. The fixed 160-rollout budget is executed sequentially with cached geometry/grid construction rather than new training or an unbounded parameter sweep. Plotting and independent result verification follow execution. Completed verification and the failure-aware result interpretation are recorded below.

## Completed execution and findings

Run `results/circuit-sensitivity-001` completed all **160 planned deterministic rollouts**, with no execution errors. **Nine of ten scenario/cadence cases passed** the predeclared gates. The high-drag case failed terminal-speed feasibility, so `all_cases_completed_and_passed` is correctly false and `failure.json` is preserved. Completion of the experiment is not acceptance of every transferred policy. No threshold was relaxed, failed seed excluded or policy retrained.

| Scenario | Decisions/lap | Strongest matched fixed baseline | Mean PPO advantage (s) | Sample SD (s) | Gate |
| --- | ---: | --- | ---: | ---: | --- |
| Nominal | 55 | full | 0.369715 | 0.049187 | Pass |
| Nominal | 110 | exit_boost | 0.076456 | 0.064817 | Pass |
| Mass 720 kg | 55 | full | 0.332212 | 0.046990 | Pass |
| Mass 880 kg | 55 | exit_boost | 0.273460 | 0.048795 | Pass |
| Drag 0.9 kg/m | 55 | full | 0.385901 | 0.051361 | Pass |
| Drag 1.1 kg/m | 55 | Not comparable | — | — | Terminal-speed failure |
| Lateral limit 18 m/s² | 55 | full | 0.358459 | 0.051322 | Pass |
| Lateral limit 22 m/s² | 55 | full | 0.382592 | 0.045976 | Pass |
| Smoothing 5 m | 55 | exit_boost | 0.175391 | 0.048990 | Pass |
| Smoothing 20 m | 55 | exit_boost | 0.041950 | 0.062623 | Pass |

Positive advantage means a faster feasible PPO lap. Summaries use all three independently trained policies; the same policies recur across scenarios, so the scenarios are not independent training replicates. Do not pool them into a larger training-seed count. Missing high-drag comparison is a recorded failure, not zero improvement or a dropped observation.

### Terminal-speed failure under higher drag

At drag 1.1 kg/m, every policy except spread finishes below 70 m/s on both grids. On the fine grid the deficit is **0.304257 m/s** (approximately **69.695743 m/s** final speed). All three PPO policies finish at the 0.1 MJ reserve. Spread meets the terminal condition and retains **0.113434 MJ**. Thus 14 of the 16 replays in this case are infeasible, and 146 of all 160 study replays are feasible. This includes the zero diagnostic: it also cannot supply a feasible reference lap for this case's accepted performance comparison.

Mechanical/battery accounting remains valid and the deficit persists on both grids; this is a terminal-feasibility limitation of the transferred policies in the changed model. Spread demonstrates that the declared finish condition can be met with the scenario's energy budget. Its retained energy is consistent with the need to allocate assistance differently near the finish, but the minimum required terminal assistance has not yet been solved. Infeasible PPO times are not reported as an advantage over the feasible spread policy.

### Action cadence and geometry sensitivity

At nominal conditions, all three unchanged policies remain faster than the best fixed baseline at 110 decisions, but their mean lap time rises from 108.238391 to **108.319886 s**: **0.081495 s slower**. Exit boost improves by **0.231849 s**, becomes the strongest 110-decision baseline, and reduces the mean PPO advantage to **0.076456 s**. The policy's one/two-block physical lookahead also halves, so this is cadence/interface transfer, not a controlled estimate of what retraining at 110 decisions would achieve. More frequent decisions alone did not improve these saved policies.

At 20 m smoothing the mean advantage is only **0.041950 s**, and seed 2 is **0.023783 s slower** than exit boost. The three-seed mean is positive, but a universal seed-wise advantage is not supported. The different smoothing choices change path length and corner constraints; resulting absolute lap times are not measurements of the same physical racing line. Parameter/smoothing ranges remain illustrative assumptions rather than calibrated probability bounds.

## Verification and dissertation artifacts

The integrated suite passes **127 tests**, including four new checks for the paired physical grids, scenario isolation and failure-sensitive numerical gate. The independent saved-artifact report checks **369 hashes and all 160 replay traces**, all expected scenario/policy combinations, nominal checkpoint replay identity, work/energy, battery accounting, reward telescoping, terminal conditions, matched-baseline arithmetic and paired cadence differences. It verifies that the terminal failures are classified correctly; it does not convert them into passes.

All policy pairs are within the numerical-discrepancy limits considered alone: maximum gain discrepancy **0.013063 s** (limit 0.05 s) and maximum relative lap-time difference **0.440254%** (limit 0.5%). These numerical conditions do not override terminal feasibility. Maximum global work-energy residual is below 5.41e-8 J; maximum per-block battery identity residual is below 5.72e-9 J. Nominal55 replays exactly match the original six coarse/fine saved PPO replays. Final-test telemetry remains untouched.

Two figure pairs in `figures/dissertation/circuit-sensitivity-v1` are saved as 300 dpi PNG/vector PDF and visually inspected:

- `01_model_transfer`: each training seed and mean/sample SD against the strongest matched fixed baseline; high-drag infeasibility is visible with no invalid mean plotted.
- `02_cadence_numerical_gates`: paired time changes at 110 decisions and numerical-error ratios against the fixed tolerances. Terminal failure is marked separately from the grid-error ratios.

The directory also contains `verification.json` and a hash manifest. Reproduce verification and figures with a fresh destination:

```powershell
.venv/Scripts/python.exe scripts/report_circuit_sensitivity.py --input results/circuit-sensitivity-001 --output figures/dissertation/circuit-sensitivity-NEW
```

## Next decision

The nominal learned advantage is supported, but robustness is conditional. Before claiming a controller that handles all these vehicle assumptions, establish explicit terminal-feasibility handling and a feasible optimization reference, then predeclare the next training/evaluation experiment. Apply any controller-interface or feasibility guard consistently to comparators and preserve this unchanged-policy failure as evidence. Separately trained 110-decision policies would be a new comparison with its own budget; these transfer results alone do not establish action-resolution convergence. The full-circuit DP/optimization-reference question remains open.

No training or simulation jobs remain active. GPU inference was required; CPU physics/geometry remains appropriate for this bounded study. A GPU simulator rewrite will be considered only if profiling shows a material benefit and numerical parity can be validated.
