# Dissertation figure index

The [matched-work distance plot](bahrain-equal-work-v1/03_bahrain_matched_by_distance.pdf) shows when deploying earlier gains time and how much of the lead is given back. Read it alongside the [three-lap transfer check](bahrain-driver-transfer-v1/01_paired_transfer.pdf).

For the Bahrain deployment question, start with the [wheel-assist map](bahrain-deployment-zones-v1/01_bahrain_wheel_assist.pdf), [power and time comparison](bahrain-deployment-zones-v1/02_bahrain_deployment_profiles.pdf) and [motion error in recurring deployment zones](bahrain-zone-support-v1/zone_motion_support.pdf).

For the 18 November dissertation draft, use the [main figure register](../../docs/figures.md). It links the primary regenerative PPO comparison, DP width and uncertainty checks, partial Bahrain reconstruction and final Abu Dhabi qualifying prediction. The selections below document earlier stages.

## October 2026 selection

The current selection contains **13 figures, each as PNG300dpi and vectorPDF**. Prefer PDF for dissertation insertion. Retain each folder's captions and manifest to preserve units, assumptions, exact source IDs and hashes. These are research evidence, not final empirical F1 performance claims.

| Folder | Figures | Evidence scope |
|---|---:|---|
| [v4](v4/captions.md) |6|Historical numerical failures, accepted event numerical gate, real development identifiability diagnostic, synthetic inverse ambiguity and original force-model comparisons|
| [telemetry-quality-v1](telemetry-quality-v1/caption.md) |1|Real development source speed/time-gap diagnostic for Bahrain2025Q|
| [event-training-v1](event-training-v1/captions.md) |3|Synthetic event-model PPO comparisons, recorded training curves and speed/battery replay|
| [event-baselines-v1](event-baselines-v1/captions.md) |3|Shared event-model DP/PPO references, failed/refined energy grids and action allocations|

Folders v1/v2/v3 are superseded historical drafts; use v4 for their six corresponding figures. Event training and baseline figures extend that selection. Do not compare elapsed times across different physics or scenarios as if they were a single controlled experiment. Do not interpret reconstructed or simulated battery/deployment as measured labels.

The newest result is the distinction between rounded DP objectives and original-state physical replay. The first four-segment finest grid failed; a documented refinement reaches the finite-action reference. This is useful methodology/results evidence even though it does not establish a continuous optimum. The shifted evaluation also shows that a richer finite action set improves the reference beyond all three saved PPO pilot seeds.

Plot scripts: scripts/plot_dissertation_results.py, plot_telemetry_quality.py, plot_event_training.py and plot_event_baselines.py. Full register: docs/figures.md. Experiment interpretation: docs/event_baseline_results.md. Original runs and negative findings are retained.

## Added11 November2026

- openf1-coverage-v1: acquisition coverage and overlapping exclusion reasons, PNG/PDF, inspected.
- circuit-inputs-v1: development-context acceleration diagnostics and candidate Sakhir geometry, PNG/PDF, inspected. Conditional motion candidates and within-development holdouts; no final test-model results.

## Full-circuit numerical validation — 11 November 2026

Use `circuit-validation-v4/01_curvature_speed_envelope` and `02_refinement_sensitivity_energy` (300 dpi PNG/vector PDF), sourced from circuit-validation-004. Both inspected. Run004 is a verified-case reuse of 003; it changes presentation only. The full reference-model numerical gate passes at 0.625 m, following a preserved coarse-grid failure. Large smoothing sensitivity is shown explicitly. These are assumed-model results, not measured F1 battery or calibrated lap-time claims. Captions and limitations: docs/full_circuit_validation.md. Earlier v1/v3 plots remain historical.

## Observable-motion validation — 11 November 2026

`motion-validation-v2/01_motion_validation` (300 dpi PNG/vector PDF) compares constant acceleration, assumed reference power endpoints and unchanged development-fit predictions on development lap holdouts and two reserved validation events. Source: results/motion-validation-002. Observed speed supplied; matching driver/session/DRS only. Equal lap/DRS-group weighting; no independence or measured battery claim. Visually inspected. Methods and limitations: docs/observable_motion_validation.md. v1 retained as historical presentation.

## Full-circuit controller study — 11 November 2026

- circuit-control-baselines-v1/01_baseline_grid_cadence: five reference-model policies, four numerical grids and 55/110 action decisions; preserved coarse-grid ranking failure.
- circuit-ppo-pilot-v1/01_learning_and_comparison: one 4096-step PPO seed's stochastic training trace and deterministic fine-grid baseline comparison. PPO saves 0.626 s versus zero but trails full request by 0.241 s.
- circuit-ppo-pilot-v1/02_policy_energy_speed: fine replay at action boundaries; requested action, simulated battery and speed. Requested power differs from delivered power during braking/cruise/depletion.

All three figures saved as 300 dpi PNG/vector PDF and visually inspected. Sources: circuit-control-baselines-001 and circuit-ppo-pilot-001. Assumed model; no convergence, optimality or empirical battery claim. Detailed methods and captions: docs/circuit_controller_study.md.

## GPU pilot — 11 November 2026

`circuit-ppo-gpu-v1` contains learning/comparison and policy/energy/speed PNG/PDF pairs, inspected. Source: circuit-ppo-gpu-001, CUDA-required seed0/4096 steps. The deterministic policy underuses battery and trails nonzero baselines; retain as a negative pilot result. This is not a controlled CPU/GPU performance or learning comparison. See docs/gpu_training.md.

## Longer GPU multi-seed study - 12 November 2026

- circuit-multiseed-v1/01_checkpoint_baseline_comparison: deterministic learning checkpoints for all three seeds and final fixed-baseline comparison; mean and sample SD are descriptive, not confidence intervals.
- circuit-multiseed-v1/02_stochastic_deterministic_energy: deterministic and five stochastic evaluations per training seed, with terminal battery reserve. Stochastic rollouts are nested within training seeds.

Source: results/circuit-multiseed-001; three GPU seeds, 16,384 steps each, fixed assumed circuit model and 55 decisions/lap. Final deterministic lap 108.238391 s on average (sample SD 0.049187 s), 0.369715 s faster than the strongest matched fixed baseline. Both 300 dpi PNG/vector PDF pairs are hash checked; both PNGs visually inspected. Methods, captions and limitations: docs/circuit_multiseed_study.md. Cadence/model sensitivity remains outstanding; no real-car or convergence claim.

## Unchanged-policy robustness - 12 November 2026

`circuit-sensitivity-v1/01_model_transfer` and `02_cadence_numerical_gates` are the current 300 dpi PNG/vector PDF sensitivity figures, both visually inspected. Source: results/circuit-sensitivity-001,160 deterministic rollouts,9/10 scenario/cadence cases accepted. The high-drag case fails terminal-speed feasibility and has no valid all-policy comparative mean. At110 decisions unchanged PPO is slower than at55; at20 m smoothing one PPO seed loses to exit boost. Numerical-error ratios alone pass and do not override feasibility. Three-seed SD is descriptive, not a confidence interval. Detailed methods/table/captions: docs/circuit_sensitivity_study.md. verification.json checks all160 saved replays and369 hashes.

## Terminal reserve guard - 13 November 2026

`terminal-guard-v1/01_feasibility_and_comparison` and `02_guard_energy_actions` are300 dpi PNG/vectorPDF, both inspected. Source: results/terminal-guard-001,64/64 feasible deterministic replays, nominal/highdrag x55/110. Identical250kJ protection and forcedterminal deployment apply to allcontrollers; guardedzero is no longer zeroelectricaldeployment. PPO+guard beats matched guardedbaselines; nominal55 has0.140950s cost versus unguardedPPO. Failed unguardedstudy preserved. SampleSD is descriptive; fixed guard has no globalfeasibility/optimality guarantee. Details/captions: docs/terminal_guard_study.md. Independent verification:445 hashes/64 replays.

17 November 2026: `regeneration-v1` contains two visually inspected PNG/PDF figure pairs for matched recovery-on/off fixed policies and full-request battery accounting. Source run: `results/regeneration-validation-001`; captions, assumptions and interpretation: `docs/regeneration_study.md`. These are not regeneration-trained PPO results.


17 November 2026: `regeneration-ppo-pilot-v1` adds two inspected PNG/PDF pairs for the 4,096-step CUDA pilot: learning/matched-baseline comparisons and policy/battery/speed profiles. See `docs/regeneration_study.md` for the small single-seed advantage and grid-sensitivity limitation.
