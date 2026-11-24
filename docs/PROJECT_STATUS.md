# Project status

## Research evidence as of 22 November 2026

| Question | Current evidence | Boundary |
|---|---|---|
| RQ2, which zones retain priority under scarcity | Across four starting-charge and braking-recovery settings, an extra 20 kJ at T10 and its exit beat all six alternatives in each case. Replanning beat equal-work spread by 0.633–0.953 s. [Scarcity study](bahrain_energy_scarcity.md) | 76 of 84 pair directions resolved. T10 has substantial local real-speed errors. The ranking applies to the tested packet and background allocation. |
| RQ2, enforcing the Bahrain finish speed | The same 12 recorded penalty-only policies and 12 freshly trained PPO/SAC policies each passed 12/12 with the action filter active and 0/12 with it switched off, on both evaluation grids. [Protocol](../configs/bahrain_finish_constraint.json) · [Feasibility plot](../figures/dissertation/bahrain-finish-constraint-v1/01_finish_feasibility.pdf) | Feasibility depends on runtime enforcement at this training budget. The filter protects charge and discharge allowance for the final three of 55 blocks and checks proposed late actions on the frozen simulator. |
| RQ2, lap time under the same finish constraint | On the finer grid, constrained retraining made all six PPO runs 6.5–197.1 ms faster than adding the filter to their recorded counterparts. All six SAC runs became 0.9–5.3 ms slower. All twelve paired differences passed refinement. [Paired timings](../results/bahrain-finish-constraint-comparison-001/paired_comparisons.csv) · [Comparison plot](../figures/dissertation/bahrain-finish-constraint-v1/02_matched_time_comparisons.pdf) | The fastest learned lap was 88.787 s with the filter. The planner achieved 88.760 s with the same filter and 88.298 s on its original feasible schedule. Total wheel work could differ. |
| RQ2, direct learning on the calibrated vehicle | PPO and SAC trained from scratch with two 64- or 256-unit actor layers, three seeds and 4,096 simulator decisions each. All 12 missed the finish on both grids. [CUDA experiment](bahrain_algorithm_width.md) | PPO’s mean speed shortfall decreased from 0.929 to 0.734 m/s with wider layers. Every learned time remained infeasible. |
| RQ2, second circuit | An exploratory qualifying screen selected Silverstone. A controller-independent bound placed the attainable finish speed below 62.38 m/s on both grids against the inherited 80.65 m/s target. [Braking screen](circuit_braking_screen.md) · [Finish diagnosis](transfer_circuit_geometry.md) | Four scored qualifying laps failed the pace criteria. Conditional model experiments require a separately defined rolling boundary. |
| RQ2, deployment and recovery at Silverstone | With a separately derived 56 m/s boundary, all 12 frozen Bahrain policies completed both grids. The planner saved 0.639–0.640 s against spread at matched wheel work. [Study and figures](silverstone_model_only.md) | The zero-assist lap can meet this finish speed. Strict pace and location checks remain failed for the unchanged vehicle. |
| RQ2, learned deployment on the calibrated model | All 12 frozen PPO and imitation policies reached the physical battery reserve before the final block. The model-aware schedule delivered 47.1 kJ there and met the line speed. [Transfer experiment](bahrain_learned_transfer.md) | 0/12 learned policies met the finish requirement on either grid. This is a transfer test of existing weights. |
| RQ2, deployment at matched wheel work | The selected distribution beat spread by 0.955 s and 0.871 s at two total wheel-work targets. Sector three gave back part of the earlier lead. [By-distance evidence](bahrain_equal_work.md) | Both pairs were feasible on both grids and matched within 0.25 kJ. Regeneration and terminal battery charge can differ. Results apply to this model. |
| RQ2, pace and driving-line transfer | A geometry-only substitution using the calibration lap's recorded path worsened predicted lap time by a further 7.405 s in the fast direction. Both models were frozen before scoring three laps from driver 22. [Path test](bahrain_path_candidate.md) · [Transfer check](bahrain_driver_transfer.md) | The centreline passed the total-time criterion on 2/3 and all-sector criterion on 0/3. Preserve the conditional deployment map. |
| RQ2, where to deploy | Seven stretches recur under three grip settings on both replay grids. The central schedule gains 0.990 s over feasible spread. Delaying the opening burst by one block costs 59 ms at equal wheel work. [Map and shift tests](bahrain_deployment_zones.md) | The bounded search gives a candidate. Two separate laps passed lap and sector tolerances, one exceeded the speed RMSE limit. [Pace checks](bahrain_qualifying_pace.md) |
| RQ1, deployment reconstruction | Four passing 800/850 kg cases fit observed Bahrain speed within 0.864 m/s RMSE while their assumed deployments differ by up to 14.387 kW RMS. [Study](bounded_real_reconstruction.md) | 41.643 s of selected propulsion windows with reset segments. Battery energy in gaps is unknown. |
| RQ2, lap control | The three-seed nominal PPO mean beat full request by 193 ms. Width 64 yielded a feasible 107.056747 s DP schedule. [PPO](regeneration_multiseed_study.md) · [DP width](regeneration_dp_width.md) | The last doubling still gained 57.2 ms. The 50 ms search-stability gate failed. |
| RQ2, transfer | 86/100 physically feasible replays. Higher drag caused all PPO seeds to miss finish speed. Both DP schedules and the spread heuristic passed. [Robustness](regeneration_robustness.md) | 16/225 pairwise grid checks exceeded 5 ms. The study's combined robustness criteria failed. |
| RQ2 extension, PPO actor capacity | Two 64-neuron layers gained 203 ms over two 32-neuron layers on average at equal training steps. The width advantage held for all three seeds in two moderate transfer cases. [Observed widths and costs](ppo_actor_width.md) | Both widths missed the finish speed under the known 10% drag increase. Only two widths and one depth were compared. |
| RQ3, qualifying prediction | Practice reduced held-out Abu Dhabi acceleration RMSE from 1.8081 to 1.7638 m/s². [Study and exclusions](session_mix_study.md) | Three qualifying laps, one covered test event, no eligible Belgian laps. Incremental race benefit remains uncertain. |
| RQ4, driving profiles | Optional extension. | No matched profile-conditioned study has run. |

The [editable technical dissertation](../report/Bahrain_deployment_draft.docx) assembles the [chapter sources](../report/outline.md), figures and references. Remaining submission work includes the student's review and personal AI reflection, the actual institutional ethics record, the raw-source redistribution decision and confirmation of the final reference style. The primary finding is a model-specific benefit from timing electrical assistance around the lap. Global optimality and actual team deployment remain open.

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


## Active implementation — 10 November 2026

This section supersedes dated snapshots below. The user accepts a model-based dissertation. OpenF1 historical acquisition is selected and locally accessible, including car/lap and context endpoints. The eight event roles are now frozen before new modelling (configs/openf1_dataset_plan.json). Adapter validation and resumable acquisition are in progress; consult docs/openf1_implementation.md for measured outcomes. Local agent execution is authorised. MATLAB starts, but the independent optimisation benchmark awaits an available fmincon installation/path. Full-circuit physical validation and DP action-grid convergence remain separate gates; existing PPO runs are bounded synthetic pilots.

## Current accepted state — 30 October 2026

This section supersedes the historical snapshots below. Authoritative project: C:/Users/fm.mm/Desktop/COM3001/COM3001. Read agent_handoff.md for compact continuation context and event_baseline_results.md for the newest experiment.

- Event-located braking/depletion solver accepted for the bounded synthetic numerical gate (event-validation-002). Historical cell-solver failures remain preserved. Real-car calibration and full-circuit validation remain open.
- Three 4,096-step event-model PPO pilots completed on 29 October; checkpoints, optimizer logs, exact reloads and hashes verified. Seed0 matches nominal full deployment; this does not demonstrate PPO superiority or convergence.
- Shared-physics DP now implemented with exact reachable speed, conservative energy accounting, explicit unrounded physical replay and verified transition caching. Run001 passed the individual two-segment checks but failed the four-segment finest-grid agreement threshold. Documented stress refinement in run003 reaches the same finite three-action reference at100 J. All84 integrated tests pass.
- Five-to-nine-action refinement improves the shifted evaluation reference from21.132915655 to21.129190409s. All three saved PPO seeds are slower. Finite energy-grid agreement does not establish continuous-action convergence or a production DP solver.
- Thirteen selected dissertation figures (26 PNG/PDF files) are indexed in figures/dissertation/README.md. Original failed results, draft figures and all run manifests remain available. Real-data plots are labelled development diagnostics; synthetic comparisons stay separate.
- Agent execution is locally authorised. New cost policy uses minimal briefs, lowest capable available models, hashed local evidence and saved command outputs. Existing occupied agent slots prevented model replacement this turn; one physics reviewer was used and routine work stayed with the coordinator.
- Next: establish action-grid sensitivity/convergence and richer scenario validation before more substantive PPO training; independently progress geometry/profile provenance, untouched event-level splits and empirical forward calibration. No new download, real-F1 deployment recovery or fresh PPO training occurred in this cycle. A later user request authorised GitHub replacement; Git was initialised locally and publication is described in publication.md and the actual commit history.

Snapshot: 27 October 2026, during the first explicitly requested multi-agent continuation. This is a point-in-time record; the coordinator must reconcile it with specialist reports before closing the cycle.

## Established baseline

- Repository recovered from the user's GitHub URL into the local workspace.
- Synthetic analytic straight fixture, strict configuration and provenance-writing verification CLI exist.
- Educational discrete energy-allocation DP exercise exists; it is not the physical lap benchmark.
- Schedule audit CLI, optional FastF1 dependency range, catalogue and manifest exist locally.
- Previous combined offline verification reported 13 passing tests. This count predates the current specialist changes and must not be presented as their verification.
- Research scope, evidence matrix, source register, decisions and report outline exist.
- No live telemetry collection, calibrated lap simulator, empirical reconstruction, production DP or trained PPO result has been established.

## Current dispatched work

| Agent | Increment | Status at this snapshot |
| --- | --- | --- |
| Data pipeline | Bounded single-session telemetry audit and offline tests, with progress record | In progress; acceptance pending coordinator review |
| Simulator | SI forward-transition prototype with drag, deployment accounting and independent tests | In progress; acceptance pending coordinator review |
| Research workflow | Full-scope multi-agent plan and explicit status | Documentation prepared; awaiting integration |
| Coordinator | Shared CLI integration, combined verification and final handoff | In progress |

## Next queue

1. Review and integrate current specialist increments; record exact test evidence and unresolved limitations.
2. Complete the bounded manual acquisition run pack and inspect a real pilot before expanding collection.
3. Establish forward-model numerical validity, braking and terminal constraints before treating the prototype as a qualifying simulator.
4. Freeze data roles/splits and parameter provenance; begin synthetic reconstruction and physical baseline comparisons.
5. Prepare the environment and manually executed PPO experiments only after physics and baseline gates pass.
6. Analyse RQ1–RQ3, then the conditional profile extension RQ4 where resources permit; maintain dissertation chapters throughout.

See WORKFLOW.md for every gate, responsibility, dependency and completion criterion.

## Unresolved inputs and controls

- Ethics status, official deadlines and weekly time budget: pending by user instruction.
- Original course/guide documents: referenced in inherited audit; not established as available in this checkout.
- Useful seasons, final circuit and reference vehicle: require audit and justified decisions; 2025 Bahrain is provisional.
- Regulatory parameters, layout identifiers and physical uncertainty ranges: require primary-source verification.
- Live FastF1 compatibility, telemetry access and resource costs: not established by offline tests.
- Manual model training and bulk collection: remain student-owned.
- GitHub publication: local changes are not proof of a push or merge; coordinator must report actual publication state.

## Workflow creation record

Action: reviewed scope.md, evidence_matrix.csv and source_audit.md; mapped the entire research scope to agent roles and evidence gates. Discovery: the current project already distinguishes four research questions and conditional extensions, but fixture success does not satisfy production simulator acceptance. Problem: live data and original source documents are unavailable as verified evidence in this increment. AI contribution: workflow and status drafting; no empirical results or student reflection authored.

## Integration update

The coordinator reports the `audit-session` CLI is wired, a dynamics prototype is present, and 21 combined offline tests pass. The telemetry pilot is implemented but live API behavior remains unverified. Dynamics remains a synthetic straight-transition prototype; full qualifying-lap braking, track preparation and calibration are outstanding. These results supersede the pre-integration status above for the current cycle. Research experiments and manual training remain planned.

Delivery for this cycle is a packaged local project. No unattended automation has been scheduled by this workflow, and no GitHub push or merge is implied.

## Guide-aligned update — 28 October 2026

See continuation_2026-10-28.md for the verified local state and Steps 01–18 map. The supplied Markdown guide is now available on the Desktop and has been read. Schedule catalogue has 887 named-session candidates after identifying 16 placeholder rows in the original 903. Telemetry pilot failed; three metadata endpoints returned HTTP 401 during small diagnostics. Parser and logging improved. Braking prototype reviewed; 28 local offline tests pass. Full lap simulation, real-data validation and training remain pending. This update supersedes older in-progress status snapshots above.

## Authoritative local continuation — 28 October 2026

The active project is now C:/Users/fm.mm/Desktop/COM3001/COM3001. The prior statement that no live collection was attempted is superseded: a FastF1 3.9.0 schedule run collected metadata for 2018–2025, with 903 rows including 16 literal None placeholders (887 named candidates), and no season failures. Both saved output hashes were verified. A 2025 Bahrain qualifying driver-1 pilot was attempted and failed with DataNotLoadedError; no laps were exported. See pilot_review_2026-10-28.md. These facts establish neither usable telemetry coverage nor calibrated model results. Original result files remain untouched. Updated implementation/training work is in progress; its outcomes require separate evidence before status is advanced.

## Local execution update — 28 October 2026
User authorised agent-run local training/validation. See local_execution_gates.md. Authenticated access succeeded despite inactive status text; telemetry pilot 002 exported three diagnostic laps. Three 16,384-step synthetic PPO seeds completed with feasible evaluations, but lost to uniform-half baseline. 35 integrated tests passed. Production physical validity, data quality and final experiment gates remain open.

## Data, physics and baseline cycle — 28 October 2026
See validation_cycle_2026-10-28.md. Clean-laps audit exported4 candidates from17 driver laps; context audit supplies no reported rain at sample times and parser-level nondeletion, with lap16 gap warning. New power/drag/braking model has6 analytic tests; all49 integrated tests pass. On the original synthetic model refined discrete DP matches exhaustive action-grid result27.651656s; saved PPO27.761082s. Real calibration, full final split and new-model RL remain open. No new training was justified in this increment.

## Calibration and reconstruction cycle — 28 October 2026
See calibration_reconstruction_cycle.md and guide_step_status.md for the current guide-aligned state.63 tests pass; diagnostic real acceleration fit and synthetic multi-start reconstruction are recorded. Mass/base-power confounding is demonstrated, not resolved. Power-model numerical gate remains open after separate20-run finer-grid diagnosis. Next blocker is event-located switching/depletion plus rerun of unchanged validation protocols. No new physical-model PPO training or real hidden-deployment claim has been made.
