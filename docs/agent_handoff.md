# Compact continuation handoff — 22 November 2026

## Bahrain energy scarcity complete

Four simulated cases crossed starting charge (2 or 1 MJ) with recoverable braking share (40% or 20%). All four adapted planners finished and beat matched-work spread on both grids. The original schedule missed finish speed in all three stress cases. For a fixed 20 kJ packet, T10 beat every other tested location in every case. T8 versus T11 and T13 versus T15 were unresolved throughout. Retain the local T10 speed-error caveat and the distinction between marginal packet value and total energy assigned to a zone. [Experiment and results](bahrain_energy_scarcity.md) · [Transfer plot](../figures/dissertation/bahrain-energy-scarcity-v1/02_zone_transfers.pdf)

## Bahrain finish-speed comparison complete

Independent physical replay reproduced all 104 evaluation trajectories from the issued actions, including charge, recovery, speed and elapsed time at all 55 decision boundaries. The largest guarded finish error was 4.3 × 10⁻¹⁴ m/s. All 148 unit tests passed. [Physical replay verification](../logs/agent_tools/2026-11-20/bahrain_finish_constraint_bare_replay.json) · [Test record](../logs/agent_tools/2026-11-20/bahrain_finish_constraint_checks.json)

The recorded penalty-only policies and the twelve policies retrained with the physical action filter all met the 80.65294 m/s rolling finish on both grids when the filter was active. All twenty-four policies missed with it disabled. The retraining used the local NVIDIA A16, the original reward, matched seeds and 4,096 interactions per policy. It used 5,411 extra simulated lookahead transitions over 49,152 applied interactions. All 888 completed training laps reached the target. [Training record](../results/bahrain-finish-constraint-001/metrics.json) · [Replay evidence](../results/bahrain-finish-constraint-comparison-001/replays.csv)

Every retrained policy beat the spread reference with the same filter on both grids. PPO improved in all six comparisons with its filtered penalty-only counterpart, while SAC slowed slightly in all six. The original feasible planner remains the fastest benchmark. Its lap increased by 0.462 s on the finer grid when filtered, so keep both planner references when presenting these results. The comparison used the central Bahrain model and allowed delivered wheel work to vary. [Paired timings](../results/bahrain-finish-constraint-comparison-001/paired_comparisons.csv)

On the finer grid all twelve retrained policies delivered zero electrical wheel work over the final three blocks with the filter off. Turning it on raised their median there to 230.6 kJ. Of all the requests the filter changed in these twelve replays, only one was inside the final three blocks. Its main effect was limiting earlier spending so energy remained available at the finish. [Work by block](../results/bahrain-finish-constraint-comparison-001/final_three_blocks.csv) · [Deployment and interventions by distance](../figures/dissertation/bahrain-finish-constraint-v1/03_guard_intervention_distance.pdf)

## Completed controller and second-circuit extensions

Direct GPU training on calibrated Bahrain compared PPO and SAC at actor widths 64 and 256, with three seeds each. All twelve missed the finish on both grids. Most depleted the available battery before the last block, and two retained usable charge but requested no final assist. [Training results](bahrain_algorithm_width.md)

The braking screen selected Silverstone. Its inherited target of 80.65 m/s exceeded the model’s optimistic 62.38 m/s upper bound. A separate model-only case froze a 56 m/s rolling target from zero-assist simulation. All 12 unchanged policies passed both grids there. The planner saved 0.639–0.640 s at equal wheel work. Keep the failed inherited transfer and the model-only result together. A circuit-specific fit would need fresh laps for independent pace validation. [Original Silverstone gate](transfer_circuit_geometry.md) · [Supplementary model study](silverstone_model_only.md)

## Earlier proposals and transfer results before direct training

For controller robustness, compare the existing finish rule with a common terminal-energy safeguard on the calibrated vehicle, then test direct training across declared grip, drag, recovery and initial-charge conditions. Score feasibility first, and use matched wheel work when attributing a saving to deployment timing. For empirical accuracy, target brake onset, minimum speed and exit speed in sector two and evaluate a frozen change on fresh laps. For circuit transfer, the existing acquisition has four screened 2025 Monza qualifying laps (two per driver), six at Silverstone (three per driver) and five in Hungary (four and one). Monza is already a development event. Silverstone is already a validation event for the separate motion study and can be reserved in advance for a new circuit-level control comparison. Each new layout needs independent timing-line, distance, curvature, DRS and braking checks before interpreting its map. [Acquisition coverage](../results/openf1-dataset-003/coverage.json) · [Public circuit geometry catalogue](https://github.com/TUMFTM/racetrack-database)

An architecture ablation could compare two 64-unit layers with two 128-unit layers on the same training scenarios, seeds and interaction budget. The supervised pilot used 220 correlated decisions from four expert trajectories. More whole expert trajectories would test whether additional capacity is worthwhile. A separate PPO versus soft actor-critic comparison would answer an algorithm question using the same observations, objective and budgets. These are proposed extensions. [Width experiment](ppo_actor_width.md) · [Imitation experiment](regeneration_imitation_pilot.md) · [Soft actor-critic paper](https://proceedings.mlr.press/v80/haarnoja18b.html)

The [editable technical draft](../report/Bahrain_deployment_draft.docx) includes the location findings, training evidence and a direct transfer comparison. All 12 frozen PPO and imitation policies were replayed on the calibrated Bahrain vehicle. All missed the finish speed on both grids. Every learned lap entered the final block at the 100 kJ reserve and delivered zero electrical work there. The reported feasible benchmark remains the model-aware planner against spread. The [study](bahrain_learned_transfer.md) and [independent action audit](../logs/agent_tools/2026-11-19/bahrain_policy_action_audit.json) preserve the evidence. Use the [chapter outline](../report/outline.md) for manuscript changes and student-owned submission items. If extending the controller experiment, predeclare a common terminal-energy intervention for every comparator and keep the unassisted transfer failures visible.

## Bahrain qualifying deployment follow-up

The equal-wheel-work follow-up is complete. Both matched comparisons passed the work and feasibility checks at both resolutions. Lead the dissertation's location result with the 0.871–0.955 s gains and the shift on the timing-line straight. Qualify the result using the cross-driver sector errors and grip sensitivity. [Matched-work study](bahrain_equal_work.md) · [Work and time by distance](../figures/dissertation/bahrain-equal-work-v1/03_bahrain_matched_by_distance.pdf)

The T8/T14 investigation below has now been completed. The registered lap-13 path is flatter near T14 at all three chord scales. T8 changes sign across scales. Direct substitution shortened the lap by 59 m and worsened the already-fast simulation. Both traces were frozen before scoring driver 22 laps 2, 5 and 13. Neither passed all criteria on any of the three. Do not reuse this driver as fresh confirmation of future changes. [Corner study](bahrain_corner_paths.md) · [Path candidate](bahrain_path_candidate.md) · [Driver transfer](bahrain_driver_transfer.md)

The calibrated Bahrain model, separate-lap pace checks, deployment search, timing interventions, grip sensitivity and plots are complete. Lap 10 exceeded the 5.0 m/s speed limit at 5.36 m/s. The seven recurring zones have different levels of agreement with real speed. Use the timing-line straight as the clearest example. [Pace evidence](bahrain_qualifying_pace.md) · [Deployment evidence](bahrain_deployment_zones.md) · [Locations and local errors](../results/bahrain-zone-support-001/metrics.json)

## Current handoff for 18 November 2026

The [methods](../report/04_methods.md) and [results](../report/06_results.md) drafts now integrate RQ1–RQ3. Resume dissertation assembly from the [reading guide](DISSERTATION_GUIDE.md). The latest studies are the [bounded Bahrain inverse](bounded_real_reconstruction.md), [width-only search](regeneration_dp_width.md), [controller robustness](regeneration_robustness.md) and [qualifying session-mix test](session_mix_study.md). Width convergence and overall controller robustness failed their declared criteria. Keep those measured outcomes in any summary. The protected qualifying evaluation has been used once with frozen fits. Belgium had zero eligible laps. The final Abu Dhabi score covers three laps. Subsequent method changes informed by that evaluation require fresh independent evidence for a new final claim. Profile conditioning remains an optional, untested question.

## DP search sensitivity completed - 18 November 2026

Retaining 16 instead of eight partial schedules per block was the largest driver of the earlier 208.3 ms improvement. It saved 89.8 to 289.3 ms in all four matched comparisons. Averaged over the six orders of changing settings, retained width contributed +185.0 ms, finer state bins +35.1 ms and finer deployment spacing -11.8 ms. Positive values mean time saved. These contributions describe the tested search on nominal Sakhir. All 24 replays were feasible and all 12 numerical comparisons passed. The fastest exploratory schedule was 107.143225 s. If pursuing search convergence, test wider retained frontiers with the five-action grid and original state bins fixed. [Study report](regeneration_dp_factorial.md).

## Regenerative optimization reference completed - 18 November 2026

The bounded forward DP search produced a feasible 107.265878 s schedule on the primary Sakhir grid. It was 0.228138 s faster than the three-seed PPO mean and 0.421437 s faster than full deployment. PPO seed 0 finished 0.038195 s faster than this schedule. Both DP candidates passed the replay refinement checks. Increasing search resolution improved the scheduled lap by 0.208282 s, exceeding the 0.050 s search-stability tolerance. This result supports comparison with an achievable schedule. The remaining uncertainty is how much further a larger search could improve it. See the [DP study](regeneration_dp_study.md) for costs, per-seed comparisons and the failed search-stability diagnostic. Next: isolate action-spacing and retained-width sensitivity.

## Regeneration multi-seed study completed and verified - 18 November 2026

All three PPO policies completed 16,384 CUDA training steps each (49,152 total) on the regenerative Sakhir model. On the primary 8,800-cell grid, final deterministic laps averaged **107.494016 s** (sample SD 0.235700 s) against **107.687315 s** for full deployment, the fastest fixed baseline. Each seed finished faster, with gains ranging from 0.011612 to 0.459632 s. The mean gain was 0.193299 s. The spread across training seeds limits how precisely this gain can be predicted for another run.

All 18 final comparisons (three deterministic and 15 stochastic) passed the frozen refinement criteria. Doubling the evaluation grid to 17,600 cells changed the paired advantage by at most 4.684 ms against the 5 ms tolerance. Maximum relative lap-time change was 0.177% against 0.25%. Terminal energy differences were zero and recovered-energy differences were below 5e-9 J against the 10 kJ and 5 kJ limits respectively. The verifier checked 327 hashes, 89 saved replays and exact deterministic checkpoint reloads on all three grids. All three final deterministic policies finished at the 0.1 MJ reserve.

[Study report](regeneration_multiseed_study.md). The next comparison is a feasible optimization reference with the same regenerative model and constraints.

## Regeneration GPU pilot completed - 17 November 2026

results/regeneration-ppo-pilot-001 completed seed 0 at 4,096 CUDA training steps in 159.96 s. The eight-observation policy, gradients and Adam moments were verified on cuda:0 (NVIDIA A16-16Q); checkpoint reload was exact. Training-grid and fine-grid replays are feasible and the pilot gate passes. Fine lap: 107.673673 s, versus the matched full-request baseline 107.687315 s. The 0.013642 s advantage is small; it is 0.006883 s on the training grid, giving a paired advantage discrepancy of 0.006759 s. Do not claim established superiority, convergence or significance from this one short seed.

Fine replay recovers 2 MJ, discharges 3.9 MJ and ends at the 0.1 MJ reserve with exact 70 m/s terminal speed. Independent verification checked 22 pilot hashes and three saved replay energy balances; two PNG/PDF plot pairs in figures/dissertation/regeneration-ppo-pilot-v1 were inspected. Physics and baseline sources did not change. The plot reader now uses recorded baseline filenames and rejects mismatched pilot/baseline studies. Details: docs/regeneration_study.md; verification: logs/agent_tools/2026-11-17/regeneration_ppo_verification.json.

Next: freeze a regeneration multi-seed protocol with evaluation isolated from training, include tighter paired grid checks before interpreting small controller differences, then establish the matched feasible optimization reference and recovery-parameter sensitivity. Final-test telemetry untouched. No jobs running. Earlier sections below are historical.

## Braking regeneration implemented and validated - 17 November 2026

The user requires automatic MGU-K braking recovery in the reference model. Optional recovery replaces friction braking at unchanged total deceleration; capacity, power, charging losses and per-lap recovery/deployment budgets are enforced. Eight controller observations expose battery capacity and remaining budgets; old six-observation PPO policies remain no-regeneration evidence. Current protocol: configs/regeneration_study.json. Full assumptions, equations, evidence and continuation command: docs/regeneration_study.md.

141 tests pass, including eight regeneration tests. Six disabled solver cases exactly match archived source. results/regeneration-validation-001 completed 20/20 feasible nominal rollouts (five fixed policies, recovery on/off, 4,400/8,800 cells); independent verification checked 37 hashes and 20 saved traces. Both grid/ranking gates pass; maximum regeneration within-mode gain discrepancy 0.006585 s. Full request improves from 108.608107 to 107.687315 s, recovering 2 MJ; this is a fixed-policy model result, not a PPO improvement. Two PNG/PDF pairs in figures/dissertation/regeneration-v1 were visually inspected. Additional energy/cross-mode grid diagnostics are descriptive; sensitivity remains open.

Original results/checkpoints/plots remain unchanged; pre-change core sources archived under logs/agent_tools/2026-11-17. Old source-bound training gates correctly reject the changed model; the new regeneration gate passes. No training ran and no jobs remain. Next: fresh CUDA PPO pilot with the new eight-observation environment, then a frozen multi-seed comparison and matched feasible optimization reference. Reassess the terminal guard under stressed regenerative scenarios and sensitivity of assumed recovery parameters. Final-test telemetry untouched. Earlier sections below are historical.

## Ponytail audit completed - 17 November 2026

Reviewed 90 Python files (7,534 lines). Removed six unused imports across six files, a net reduction of three lines; executable logic is unchanged. Broader consolidation did not justify adding abstractions or weakening independent scientific checks. Ponytail full is now the standing coding default in AGENTS.md and docs/agent_execution_policy.md. Audit evidence and original source snapshots are in logs/agent_tools/2026-11-17.

All 133 tests pass. Post-cleanup verification confirms the control training gate, 445 terminal-guard hashes/64 feasible replays, and 116 multi-seed hashes/66 replays. Original results, checkpoints and plots remain unchanged. The next research step remains a bounded feasible full-circuit optimization reference with matched constraints, as described below.

## Terminal-feasibility guard validated - 13 November 2026

results/terminal-guard-001 completed 64/64 feasible replays and 4/4 accepted cases: nominal/high drag 1.1 at 55/110 decisions, all three unchanged final CUDA PPO policies plus five fixed policies on 4,400/8,800-cell grids. The common guard protects 250 kJ above the physical 100 kJ reserve until the final one-of-55 action span, then requests full deployment. It preserves original observation semantics and adds no energy. Original physics and failed sensitivity artifacts remain unchanged. No training ran.

At 55 decisions, mean PPO-plus-guard laps are 108.379341 s nominal and 108.891185 s at higher drag; advantages over the strongest guarded baseline (exit boost) are 0.226928/0.213605 s. At 110 decisions, advantages are 0.092480/0.081042 s. Every seed beats its matched guarded baselines. Nominal55 costs 0.140950 s relative to unguarded PPO; final PPO energy of 0.175144-0.186410 MJ shows conservative unused margin. Guarded zero requests terminal assistance. Validation covers only these four cases, not universal feasibility or optimality.

133 integrated tests pass; independent verification checked 445 hashes and 64 replays. Maximum gain error is 0.007412 s and lap error 0.356915%; terminal errors are below 1e-13 m/s. Two PNG/PDF pairs in figures/dissertation/terminal-guard-v1 were visually inspected. Report: docs/terminal_guard_study.md; wrapper: src/f1energy/terminal_guard.py; runner: scripts/evaluate_terminal_guard.py; protocol: configs/terminal_guard_protocol.json. Sources/protocol are bound by the run manifest: use new versions for changes. No jobs running; final-test telemetry untouched.

Next: establish a bounded feasible full-circuit optimization reference for the PPO-versus-optimization question, with matched physical constraints. Distinguish a guard-constrained reference from unrestricted terminal-feasible optimization. Further robust GPU training requires a new protocol; the guard has not been evaluated on the remaining mass/grip/smoothing cases. See docs/DISSERTATION_GUIDE.md for the essay reading path. Older sections below are historical.

## Controller sensitivity completed with a feasibility failure - 12 November 2026

Cleanup: 78 generated bytecode files deleted; 429 obsolete duplicate files (134,207,143 bytes) archived outside the codebase in sibling COM3001-cleanup-archive-2026-11-12. Bulk deletion was blocked by automatic approval review; narrower deletion and reversible archival succeeded. README and docs/DISSERTATION_GUIDE.md now provide the essay reading path. Original research evidence retained; exact cleanup ledgers under logs/agent_tools/2026-11-12.

results/circuit-sensitivity-001 completed all 160 planned deterministic rollouts using the unchanged three final CUDA policies and five fixed baselines. Nine of ten scenario/cadence cases passed. High drag (1.1 kg/m) causes every policy except spread to miss the terminal70 m/s condition by about0.304257 m/s on the fine grid; all three PPO policies are infeasible there. 146/160 replays feasible. The study-wide acceptance flag remains false; no threshold relaxed and failure.json retained. Numerical grid errors alone pass (max0.013063 s gain error;0.440254% lap error), so refinement alone is not an established fix for the physical terminal failure.

Nominal110-decision unchanged transfer is0.081495 s slower on average than55, still0.076456 s faster than its strongest fixed baseline (exit boost). At20 m smoothing, mean advantage shrinks to0.041950 s and one seed loses by0.023783 s. Do not claim universal robustness, convergence, real-car validity or statistical significance. All127 integrated tests pass. Independent verification checked369 hashes and160 replays. Two PNG/PDF figure pairs in figures/dissertation/circuit-sensitivity-v1 were inspected; report: docs/circuit_sensitivity_study.md. No jobs running; final-test telemetry untouched.

Next: establish explicit terminal-feasibility handling and a feasible full-circuit optimization reference before further robustness training. Preserve this failure and apply any guard/interface change consistently to comparison policies. A separately trained110-decision study would need its own protocol; current transfer includes changed physical lookahead. GPU neural training remains required; consider moving physics toGPU only after profiling and numerical parity justify it. Older sections below are historical.

## GPU multi-seed study completed - 12 November 2026

results/circuit-multiseed-001 completed all three CUDA seeds 0/1/2 at 16,384 steps each (49,152 total). The predeclared final deterministic endpoint averages 108.238391 s, sample SD 0.049187 s, range 108.186268-108.283990 s. Every seed beats all five matched 55-decision fixed baselines; the mean advantage against the strongest (full request, 108.608107 s) is 0.369715 s. All deterministic policies reach the 0.1 MJ reserve feasibly. Nested stochastic evaluation has seed-mean average 108.310744 s and sample SD 0.025930 s.

All final deterministic/stochastic coarse-fine gates and exact checkpoint reload checks passed. CUDA parameters, gradients and Adam moments verified. 123 integrated tests passed; independent verification checked 66 replay traces and 116 hashes. Two dissertation PNG/PDF figure pairs in figures/dissertation/circuit-multiseed-v1 were visually inspected and hash checked. Protocol: configs/circuit_multiseed_protocol.json. Report: docs/circuit_multiseed_study.md. Verification logs: logs/agent_tools/2026-11-12. No jobs running.

Next: predeclare and execute 55/110-decision action-cadence and vehicle/geometry sensitivity comparisons, retaining all seeds and matched baselines. Distinguish policy transfer from retraining and maintain physical/numerical constraints. This is a nominal assumed-model result, not convergence, optimality, real-F1 validation or statistical significance. Final-test telemetry remains untouched. Older sections below are historical.

## GPU training enabled and verified — 11 November 2026

User requires GPU neural-network training and sensible use of system/shared memory. Installed torch 2.14.1+cu126, retaining NVIDIA 553.24 driver; CUDA 12.6 operations pass on A16-16Q 16 GB. System RAM is approximately 64 GiB; user-reported 32 GiB shared GPU allowance is host memory, not additional VRAM. SB3 rollout arrays/circuit data use RAM; policy/gradients/Adam use CUDA. All three trainers require_cuda with no CPU fallback; physics remains CPU. See docs/gpu_training.md and environment-gpu-lock.txt.

119 tests pass. results/circuit-ppo-gpu-001 completed 4096 steps in 180.81 s; 13 parameter tensors, 13 gradient tensors and 26 Adam moments verified on cuda:0. Reload exact, fine replay passes. Fine lap 109.415539 s (0.059667 s better than zero; 0.807432 s slower than full). Terminal energy 1.908298 MJ shows underdeployment. Preserve this result; CPU/GPU same seed does not guarantee identical stochastic training. Previous CPU results remain historical.

GPU pilot plots in figures/dissertation/circuit-ppo-gpu-v1 inspected. Memory audit, installation logs and 22 manifest hash checks retained in logs/agent_tools/2026-11-11. PyTorch peak allocated 16.36 MiB for this small pilot; host rollout configuration 13 KiB. Do not inflate allocations to consume advertised capacity. Future larger batches/caches should use RAM/VRAM as required and be profiled.

Next research work remains larger predeclared multi-seed GPU training with deterministic/stochastic evaluation checkpoints, action-cadence and model sensitivity. Final-test telemetry untouched. No jobs running.

## Full-circuit RL pilot completed — 11 November 2026

The Gym controller interface, five deployment baselines and first full-circuit PPO pilot are complete. results/circuit-control-baselines-001 contains 25 rollouts. The coarse 20-cell/block grid changes rankings; 80 cells/block (~1.229 m) passes against 160 (~0.614 m), with maximum gain error 0.00309 s. All policies use 55 decisions, 70 m/s common initial/verified terminal speed, 2 MJ initial energy and 0.1 MJ reserve. 110-decision sensitivity materially improves corner-exit boost, so action-resolution convergence remains open.

results/circuit-ppo-pilot-001: seed 0, 4096 steps, 131.75 s CPU training. Fine deterministic lap 108.849138 s, saving 0.626068 s versus zero but slower than full-request baseline 108.608107 s by 0.241032 s. Terminal battery 0.954526 MJ; policy underuses budget. Fine/train gain discrepancy 0.000576 s; feasibility and reload identity pass. This is a functioning pilot, not convergence or an RL advantage.

113 integrated tests plus 4 separate training-gate tests pass. Nested numerical input/config hashes are now checked before training, in addition to solver/results hashes. Independent verification checked 25 baseline and 3 policy rollouts and saved hashes. Figures in circuit-control-baselines-v1 and circuit-ppo-pilot-v1 are inspected PNG/PDF. See docs/circuit_controller_study.md. Final-test telemetry unused. No jobs running.

Next: predeclared larger multi-seed budget with deterministic/stochastic evaluation checkpoints, followed by 55/110-action cadence and model uncertainty comparisons. Preserve prior results; do not tune on final-test events. Existing benchmark001 reference/script identity is historical; current runner adds nested numerical-input checks, and training already used the stronger gate.

## Observable-motion assessment completed — 11 November 2026

results/motion-validation-002 evaluates unchanged development fits on original development holdouts and reserved validation events. Driver 1 only; exact session/DRS matching; no validation fitting. Included 5,110 development and 8,756 validation windows (65 validation laps); 9 unmatched validation windows recorded. Mean lap/DRS-group acceleration RMSE improves from constant 4.578 to transferred-fit 2.776 m/s² in Hungary and 3.354 to 1.922 in UK. Observed speed is supplied; this is conditional acceleration evidence.

The assumed circuit reference has larger errors and remains explicitly model-based. Straight-motion windows cannot establish grip, geometry smoothing, timing alignment or electrical split. The assessment is complete with limitations; a calibrated digital twin is not required before the accepted model-based controller study. Next: shared-physics full-circuit baselines/controller interface, throughput and action/grid comparisons against 0.625 m replay, then bounded RL. No new training has run.

See docs/observable_motion_validation.md and configs/motion_validation_protocol.json. Figure PNG/PDF: figures/dissertation/motion-validation-v2, inspected. Independent recalculation verified 13,866 predictions/161 group RMSEs and 13 hashes. Final-test modelling inputs untouched. No active jobs.

## Full-circuit numerical gate completed — 11 November 2026

The periodic curvature, cyclic braking envelope and forward event-solver wrapper are implemented in src/f1energy/circuit.py. The integrated suite passes 109 tests. The initial 5-to-2.5 m refinement failed the unchanged 0.5% time criterion; 1.25-to-0.625 m refinement passes at 0.348%/0.353% for zero/full electrical request. Speed, reserve, work-energy, depletion and periodic-speed checks pass. This is numerical validation of an assumed reference vehicle, not empirical F1 lap-time validation.

Current artifacts: results/circuit-validation-004 and figures/dissertation/circuit-validation-v4. Run004 reuses all 15 hash-verified cases from 003 with presentation fixes only; 001 retains its refinement failure and 002 its pre-simulation cache-loader failure. Seven new circuit tests and an independent focused review cover the new implementation. No telemetry or final-test modelling inputs were read by this study; no new training ran.

Geometry smoothing materially changes lap time and spline length; nominal 10 m sigma gives 5373.012 m, versus original 5405.749 m. Separate lateral/longitudinal limits, unmodelled combined grip/grade/regeneration, unverified racing line and source-origin timing alignment remain limitations. Reference base 450 kW plus electrical 120 kW is assumed; do not add telemetry-derived total power to it. Speed periodicity is not battery periodicity.

Next: development/validation observable-motion and model-assumption assessment; then scalable full-circuit baseline/action-grid gates and bounded multi-seed training. See docs/full_circuit_validation.md for methods, quantitative results and reproducible commands. Older dated sections below are historical and do not supersede this section. No jobs remain running.

## Modelling preparation completed — 11 November 2026

results/openf1-motion-001 contains46,051 development windows and15,501 validation windows from318/124 candidate lap groups; each retains event/session/driver/lap labels. Adjacent rows are dependent. Final test modelling inputs were not prepared. Coverage plot PNG/PDF saved and visually inspected at figures/dissertation/openf1-coverage-v1.

results/circuit-input-assessment-001 contains21 separate driver1 development event/session/DRS fits using chronological last-lap-group holdouts. Effective power/drag beats a constant-acceleration baseline in20/21 contexts; no parameter boundary hits. These are observed-speed-conditioned acceleration diagnostics, not full-lap predictions. Assumed mass800kg; electrical power remains unobserved. Independent RMSE recalculation and input/output hashes verified. Figure pair at figures/dissertation/circuit-inputs-v1 was inspected.

Candidate TUM Sakhir centreline downloaded with source licence:1082 points,5405.749m closed length,0.1155% below official5412m. Basic geometry checks pass. Full layout/curvature, speed-envelope, lap-boundary and forward-simulator validation remain next. See docs/model_preparation_2026-11-11.md. Do not rerun the completed acquisition or model-table generation unnecessarily.


## Verified acquisition completion — 11 November 2026

Run results/openf1-dataset-003 completed all38 planned standard sessions across8 weekends, with zero recorded invocation failures and no pending sessions. It contains2,101 lap entries,1,054,001 native car samples and543 conditional motion candidates. All per-session output hashes were checked. The acquisition process has finished. Earlier run002 retains its three failures; run003 recovered them using cached responses and explicit empty-window handling. Do not restart acquisition unnecessarily.

102 automated tests pass. scripts/prepare_openf1_motion.py and scripts/plot_openf1_dataset.py are implemented but their full-cohort outputs have not yet been generated. Next: prepare grouped development/validation model inputs and coverage figures, then empirical motion modelling/full-circuit validation. Test telemetry has been acquired and quality-screened only; no model performance evaluated. These data are not verified battery/deployment labels.


Root: C:/Users/fm.mm/Desktop/COM3001/COM3001. Python .venv/Scripts/python.exe; set PYTHONPATH=src. User authorises local acquisition/training/validation and accepts a defensible model-based dissertation. Use bounded low-cost work, cached evidence, minimal agent context. One Sol specialist implemented the initial adapter but stopped at its usage limit; coordinator reviewed/fixed and tested it. No further agents are needed for the current acquisition.

## Active work

Guidelines AGENTS.md, WORKFLOW.md, scope.md, data_roles.md, README and PROJECT_STATUS now reflect OpenF1 + physics simulation. configs/openf1_dataset_plan.json freezes 8 events: development Bahrain1257/Spain1262/Monza1268/Japan1256; validation UK1277/Hungary1266; test Belgium1265/AbuDhabi1276. 40 catalogue sessions, 38 included after excluding Belgian sprint sessions. Roles apply across providers/drivers. Red Bull Racing entries selected from each session, including substitutes. Test acquisition/QC allowed; no test fitting/profile extraction/model tuning.

Adapter src/f1energy/openf1.py has hash-checked caching, rate limits, bounded retries, offline replay, UTC/unit normalization, approximate-lap boundary handling and conservative context alignment. Tests now cover false timing-colour flags and out-lap garage-duration overlaps. Out-laps retain metadata but cannot mask timed-lap samples. <=0.5s timed-lap overlaps exclude ambiguous samples; larger overlap fails. Whole-lap conditional screening uses1s internal/edge gaps; this is not verified clean/dry status. 99 integrated tests passed, plus2 new motion-window tests passed separately.

scripts/acquire_openf1_dataset.py is acquiring results/openf1-dataset-002, initial full-cohort invocation with45min/800request budgets. A running execution session may exist (root tool session66522). DO NOT edit collector or adapter while this run is active: contract binds both file hashes. Per-session complete.json and per-driver files are checkpoints; coverage.json updates at invocation end. Inspect completed manifests for live counts. Resume requires unchanged source/plan and verifies outputs.

Known pending repair: Spain FP3 session9966 failed on a car_data tail window after actual telemetry; direct probe confirmed HTTP404 body {"detail":"No results found."}. Old runner treats it as failure. Let current batch finish. Then explicitly support this documented empty-window case only for car/location, preserve404 provenance and lap-edge screening; do not convert other404 failures to success. Add regression test. Use a NEW run003 after source changes, rebuilding from existing successful cached responses (no need to re-fetch those);001/002 remain historical artifacts. Do not loosen quality thresholds merely to increase yield.

Pilot001 diagnosed out-lap/timing-colour bugs;002 is corrected. Spain Q was rebuilt entirely offline, then full acquisition started. Real-data gaps still exclude some otherwise timed laps. Native public response cache is ignored work/source-audit-openf1. Documentary sources cached work/source-review-cache. No credentials saved.

New scripts: prepare_openf1_motion.py prepares development/validation grouped adjacent full-throttle unbraked constant-gear/DRS windows, maxpairgap0.5s, signed acceleration retained; final test role is unavailable. Run after accepted acquisition. plot_openf1_dataset.py produces coverage/exclusion PNG/PDF with hashes. Do final integrated tests, output integrity checks, figures/visual inspection, current documentation and concise completion report after acquisition/recovery. No new GitHub push requested in this increment.

## Existing scientific state

Source audit docs/data_source_options_audit.md; literature review six papers docs/literature_review_2026-11-10.md. User supplied local files; no Library UI needed. Current accepted old calibration is287 fit pairs/144 validation pairs from Bahrain2025Q, with mass/power/drag confounding; expanded acquisition is not yet a newly fitted car.

Event solver event-validation-002 passes bounded synthetic checks. event-baselines-003 agrees with finite three-action stress reference at100J; action-grid convergence and full-circuit geometry/physics remain open. Three4096-step event PPO pilots are not convergence or real-world improvement. Do not retrain substantially until relevant gates pass. Previous detailed handoff archived in logs/agent_tools/2026-11-10/handoff_before_implementation.md; use linked result docs rather than transcripts.

MATLAB R2026b starts; optimisation licence is available but fmincon was not installed/on path at last check. MATLAB is optional for independent optimisation, not a data-acquisition blocker. Final reflection/institutional approval remain student-owned.
