# Dissertation reading guide

Open the [editable Word draft](../report/Bahrain_deployment_draft.docx) to read the assembled technical chapters and embedded figures. The [chapter outline](../report/outline.md) identifies the Markdown sources, current structure and outstanding student-owned material.

Updated 19 November 2026. Start with the [methods chapter](../report/04_methods.md) and [results and discussion chapter](../report/06_results.md). Both link to the original results, assumptions and validation records.

For continuous reading, begin with the [abstract and introduction](../report/01_introduction.md), [related work](../report/02_related_work.md) and [data chapter](../report/03_data.md). The [conclusion](../report/07_conclusion.md) answers the deployment question and the [professional-practice chapter](../report/08_professional_practice.md) explains data provenance, unresolved permissions and the role of AI assistance. The student's personal reflection is a separate submission component.

Lead with the deployment question. Show where the central schedule delivered power, compare its lap with the feasible spread policy, then show what happened when exactly the same opening requests were moved one block later. Use the real speed traces to explain why confidence varies by location. The three-seed PPO, network-size and imitation experiments used the earlier reference vehicle. Their lap times belong in the controller-method comparison. [Bahrain deployment experiment](bahrain_deployment_zones.md) · [Pace calibration](bahrain_qualifying_pace.md)

## Suggested writing order

1. **Question and scope:** read scope.md, then data_sufficiency.md and data_source_options_audit.md. Explain why public speed/control channels cannot identify true battery deployment uniquely and why controlled simulation is used.
2. **Literature:** use literature_review_2026-11-10.md, literature_matrix.csv and report/references.bib. Distinguish the supplied literature from results produced by this project.
3. **Data:** read openf1_implementation.md and observable_motion_validation.md. Report acquisition, exclusions and conditional motion validation. Keep training/development, validation and final-test roles explicit.
4. **Physical methods:** read full_circuit_validation.md, circuit_controller_study.md and [regeneration_study.md](regeneration_study.md). State geometry, vehicle assumptions, braking/depletion events, speed envelopes, energy accounting and shared initial/terminal conditions.
5. Describe the common energy and finish constraints, all three trained policies and the costs of training, planning and action selection. [Regenerative PPO](regeneration_multiseed_study.md) · [Full-circuit DP](regeneration_dp_study.md)
6. Explain how the answer changes with search width and with assumptions about available energy, braking recovery and drag. [Search settings](regeneration_dp_factorial.md) · [Width check](regeneration_dp_width.md) · [Controller robustness](regeneration_robustness.md)
7. Report motion reconstruction on observed windows and qualifying prediction on held-out events. Include failed fits, missing events and the sensitivity to the window filter. [Bahrain reconstruction](bounded_real_reconstruction.md) · [Session-mix study](session_mix_study.md)
8. Use the [results chapter](../report/06_results.md) and [project status](PROJECT_STATUS.md) for the limits on each research question.

## Main evidence and figures

Paths below are relative to the project root. Figures are supplied as 300 dpi PNG and vector PDF; use PDF for scalable document embedding where supported.

| Essay topic | Authoritative run/report | Current figure folder |
| --- | --- | --- |
| Did the original neural controllers transfer to the calibrated vehicle? | [Twelve frozen checkpoints and two shared-grid benchmarks](bahrain_learned_transfer.md) | [Finish feasibility and delivered assist](../figures/dissertation/bahrain-learned-transfer-v1/01_bahrain_learned_transfer.pdf) |
| Does deployment location still matter at the same total work? | [Two matched work budgets and both grid resolutions](bahrain_equal_work.md) | [Where the time advantage builds and recedes](../figures/dissertation/bahrain-equal-work-v1/03_bahrain_matched_by_distance.pdf) |
| Can public position data improve the simulated racing line? | [Path candidate](bahrain_path_candidate.md) · [Second-driver evaluation](bahrain_driver_transfer.md) | [Corner paths and curvature](../figures/dissertation/bahrain-corner-paths-v1/corner_paths.pdf) · [Paired transfer](../figures/dissertation/bahrain-driver-transfer-v1/01_paired_transfer.pdf) |
| Where to deploy, with what delivered power and time gain | [Locations, shifts and grip sensitivity](bahrain_deployment_zones.md) | [Track map](../figures/dissertation/bahrain-deployment-zones-v1/01_bahrain_wheel_assist.pdf) · [Power, recovery and time](../figures/dissertation/bahrain-deployment-zones-v1/02_bahrain_deployment_profiles.pdf) |
| Why the original Bahrain lap was slow and where speed remains uncertain | [Free-running calibration](bahrain_qualifying_pace.md) | [Original loss](../figures/dissertation/bahrain-pace-diagnosis-v1/01_historic_gap.pdf) · [Separate lap 10](../figures/dissertation/bahrain-pace-calibration-v1/lap-10.pdf) · [Local error in recurring zones](../figures/dissertation/bahrain-zone-support-v1/zone_motion_support.pdf) |
| Brake MGU-K regeneration and changed controller contract | [docs/regeneration_study.md](regeneration_study.md) | See the study for validated run/figure paths |
| Primary regenerative PPO result | [Three-seed study](regeneration_multiseed_study.md) | figures/dissertation/regeneration-multiseed-v1 |
| Follow-up on PPO actor size and compute cost | [Paired 32/64 comparison](ppo_actor_width.md) | figures/dissertation/ppo-actor-width-v1 and ppo-actor-width-cost-v1 |
| Supervised imitation of DP actions | [Pilot design and results](regeneration_imitation_pilot.md) | See the pilot for the demonstration set and full-lap evaluations |
| Primary regenerative DP comparison and cost | [DP study](regeneration_dp_study.md) | figures/dissertation/regeneration-dp-v1 |
| Search settings, width and robustness | [Factorial comparison](regeneration_dp_factorial.md), [width check](regeneration_dp_width.md), [parameter changes](regeneration_robustness.md) | See the studies for their figure directories |
| Empirical reconstruction and qualifying prediction | [Partial-window inverse](bounded_real_reconstruction.md), [session-mix comparison](session_mix_study.md) | See the studies for their figure directories |
| Telemetry coverage and exclusions | results/openf1-dataset-003; docs/openf1_implementation.md | figures/dissertation/openf1-coverage-v1 |
| Observable acceleration validation | results/motion-validation-002; docs/observable_motion_validation.md | figures/dissertation/motion-validation-v2 |
| Circuit geometry, curvature and numerical refinement | results/circuit-validation-004; docs/full_circuit_validation.md | figures/dissertation/circuit-validation-v4 |
| Fixed controller baselines and action/grid sensitivity | results/circuit-control-baselines-001; docs/circuit_controller_study.md | figures/dissertation/circuit-control-baselines-v1 |
| Historical deployment-only full-circuit PPO | results/circuit-multiseed-001; docs/circuit_multiseed_study.md | figures/dissertation/circuit-multiseed-v1 |
| Model/cadence robustness, including terminal failure | results/circuit-sensitivity-001; docs/circuit_sensitivity_study.md | figures/dissertation/circuit-sensitivity-v1 |
| Common terminal guard and performance cost | results/terminal-guard-001; docs/terminal_guard_study.md | figures/dissertation/terminal-guard-v1 |
| Earlier short-scenario DP/exhaustive/PPO comparison | docs/event_baseline_results.md; docs/event_training.md | See docs/figures.md for current event figure selection |

The [figure register](figures.md) includes earlier comparisons for provenance. Use the regenerative experiments for the main argument. The full-circuit DP study gives a feasible reference lap time. Global optimality remains unresolved.

## Minimal code map

| File | What it explains |
| --- | --- |
| src/f1energy/event_power_lap.py | Physical integration, braking/depletion events and work/energy accounting |
| src/f1energy/circuit.py | Circuit geometry, curvature-derived speed limits and braking envelope |
| src/f1energy/circuit_control.py | Gym environment, observations/actions, reward and five fixed policies |
| scripts/benchmark_circuit_control.py | Matched baseline and discretisation study |
| scripts/train_circuit_multiseed.py | Three-seed GPU training, checkpoints and paired evaluation |
| src/f1energy/experiment.py | Evaluation RNG isolation and seed-level statistics |
| src/f1energy/training_device.py | Mandatory CUDA checks for training |
| scripts/verify_circuit_multiseed.py | Independent saved-replay arithmetic and integrity checks |
| scripts/evaluate_circuit_sensitivity.py | Unchanged-policy robustness and cadence study |
| src/f1energy/terminal_guard.py; scripts/evaluate_terminal_guard.py | Common terminal-reserve heuristic and its bounded validation |
| configs/circuit_reference.json | Assumed physics/geometry values and declared limitations |
| configs/regeneration_multiseed_protocol.json | Frozen regenerative learning experiment design |
| configs/openf1_dataset_plan.json; configs/data_roles.json | Data acquisition frame and protected event roles |

Read other scripts only when writing about their associated experiment. Their existence does not imply their outputs are part of the current primary comparison.

## Claims that the completed deployment-only main study supports

Three independently trained GPU PPO policies each outperform all five matched fixed baselines on the nominal assumed model at 55 decisions/lap. Mean deterministic lap time is 108.238391 s, with sample SD 0.049187 s; the mean advantage over full request is 0.369715 s. These are descriptive results from three training seeds. The error bar is not a confidence interval; repeated action-noise rollouts are not independent trained agents.

Sensitivity now limits this result: high drag violates terminal speed; at20 m smoothing one seed loses to exit boost; changing to110 decisions slows the unchanged policies. Read the robustness study before generalizing the nominal result.

The separate terminal-guard study now provides a feasible nominal/high-drag comparison at 55/110 decisions, without erasing the original failure. Its improvement claim is PPO-plus-guard versus fixed-policy-plus-guard; it does not mean PPO learned the new terminal rule.

There is no verified real battery/deployment ground truth, no proof of convergence or continuous optimality, and no demonstrated benefit on a real F1 car. Geometry smoothing, independent lateral/longitudinal limits, missing grade/combined grip (and regeneration in the historical studies) and fixed operating conditions remain limitations. Final-test telemetry has not been used for controller tuning.

## Cleanup record

On 12 November, 78 generated bytecode files (583,030 bytes) were deleted. An obsolete clean verification checkout, a byte-identical diagnostic cache and a temporary figure preview (429 files, 134,207,143 bytes) were moved out of this codebase to the sibling folder COM3001-cleanup-archive-2026-11-12. The archive is reversible and does not reclaim those bytes from disk. The original diagnostic log remains in work/diagnostic; its duplicate cache can be recovered from that archive or the hash-matched original result cache.

Automatic approval review blocked the initial bulk deletion with the generic reason 'blocked by policy'; individual generated-file deletion and reversible archival succeeded. No research result, trained checkpoint, literature source, original telemetry cache or failed-study evidence was removed. Exact paths/counts are recorded in logs/agent_tools/2026-11-12/cleanup_removed_bytecode.json and cleanup_archived_duplicates.json. Bytecode will regenerate during normal Python execution and is already git-ignored.


18 November 2026 update. The [completed regeneration multi-seed study](regeneration_multiseed_study.md) reports all three trained policies and links to the comparison plots and independent replay audit.


The [full-circuit DP study](regeneration_dp_study.md) compares all three final PPO policies with two feasible optimized schedules, reports planning and action-selection costs, and links to the dissertation figures.


18 November 2026. The [DP sensitivity study](regeneration_dp_factorial.md) identifies the contribution of retained search width and the interaction between action spacing and state bins. It includes all eight schedules and both dissertation figure pairs.
