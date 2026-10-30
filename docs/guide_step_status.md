# Guide step status — 28 October 2026

## Superseding update — 30 October 2026

The table below is the preserved28October snapshot. Current evidence is summarised here and in PROJECT_STATUS.md:

- Step08: event-based braking/depletion/ceiling handling passed a new explicitly scoped synthetic numerical gate in event-validation-002. The original cell-solver rejection is preserved; empirical/full-circuit acceptance remains open.
- Step09: synthetic known-truth reconstruction and ambiguity experiments now exist (reconstruction-synthetic-002). Real forward calibration and identifiability remain unresolved.
- Step10: shared event-model heuristics, exhaustive finite-action references and energy-grid DP implemented. Initial stress-grid failure preserved in event-baselines-001; documented finer-grid agreement reached in003. Action-grid convergence and production scale remain open.
- Steps11–12: event-model environment and three4096-step PPO pilots completed with source-bound validation, logs and exact checkpoint reload. These are synthetic pilots, not accepted real-circuit training or final convergence evidence.
- Steps13/16–17:13 selected dissertation figures, explicit negative findings, paired within-scenario comparisons and provenance logs exist. Final independent evaluation and student reflection remain open.84 integrated tests pass.

The immediate numerical priority is action-grid sensitivity and a richer validated scenario benchmark, alongside independent data-split/track-profile work. The historical final sentence below refers only to the earlier review, not these later executed experiments.

Basis: the actual Desktop/F1_COM3001_Step_by_Step_Guide.md step headings and requirements, checked against current source, configs, documentation and immutable results. This is a review snapshot, not a claim that the dissertation is complete. Implemented means an artifact exists; validated is restricted to stated checks and data. Open identifies the guide's remaining acceptance work. Older status snapshots are historical and may be superseded here. Local execution is now authorised by the user; earlier manual-only run ownership is superseded where recorded in local_execution_gates.md.

| Guide step | Implemented evidence | Validation reached | Open acceptance work |
|---|---|---|---|
| 01 Define the claim and evidence plan | docs/scope.md; evidence_matrix.csv; decisions.md | Explicit reconstruction/measurement/simulation boundaries documented | Supervisor agreement, reference vehicle, final circuit and official dates |
| 02 Build the critical literature review | report/02_related_work.md; references.bib; literature_matrix.csv | Initial source audit exists | Complete critical synthesis, verify each substantive source and derive research gap |
| 03 Learn RL and deep learning through small exercises | learning/energy_allocation.py; synthetic RL pilot | DP teaching exercise checked; three small PPO runs executed | Student learning evidence, DL/DRL explanations and exercises beyond execution |
| 04 Establish repository and working contract | Package, CLI, tests, manifests, WORKFLOW.md | Local commands and repeated test runs work | Fresh-environment reproduction and final dependency/source release records |
| 05 Collect and catalogue available laps | Schedule catalogue; authenticated Bahrain Q pilot; clean/context exports | 887 named session candidates identified; 17 driver laps audited; four candidates exported | Cross-session/circuit acquisition and quality/coverage reporting; schedule support is not achieved telemetry coverage |
| 06 Freeze splits and label usable laps | configs/data_roles.json and development_split.json | Fit laps4/10, within-event validation13, primary exclusion16; hashes retained | Freeze untouched event-level final split and formal inclusion policy; dry-track evidence remains conditional |
| 07 Prepare circuit and driving profiles | Synthetic track scenarios and observed car samples | Synthetic inputs exercised only | Empirical geometry/layout identity, leakage-safe physical corner constraints, braking/throttle profiles and profile uncertainty |
| 08 Build and verify physical simulator | dynamics/braking/lap/power_lap modules; analytic tests | Synthetic physics/accounting checks passed; power-grid001 preserved | Power-grid001 failed its declared convergence gate; resolve numerical switching/convergence and empirical plausibility before physical controller claims |
| 09 Calibrate and reconstruct plausible deployment | identification.py; calibration-data001; calibration-fit001 | Bounded descriptive fit and within-event residual diagnostics executed; mass confounding exposed | Validated forward calibration, synthetic deployment recovery, real conditional inverse maps and uncertainty; no calibrated car established |
| 10 Implement heuristics and DP | baselines.py; synthetic-baselines001 | Original synthetic-model DP checked against exhaustive discrete action grid | Numerical state/action convergence and matched baselines on accepted physical model; distinguish toy/exhaustive grid optimum from continuous optimum |
| 11 Expose simulator as RL environment | rl.py and environment checks | Synthetic environment exercised by saved training runs | Wrap accepted production physical model; information, failure, terminal-condition and look-ahead acceptance checks |
| 12 Train PPO and expand across circuits | Three 16,384-step synthetic PPO pilots | Saved policies evaluated; pilot underperformed uniform-half heuristic | Accepted physical model/circuit training, budget/convergence study, broader circuits, final seed protocol; toy training is not empirical deployment optimisation |
| 13 Freeze and execute main evaluation | Pilot comparisons and data-role registry | Synthetic pilot comparisons only | Freeze E1–E5 protocol, unseen scenarios/events, paired performance and uncertainty; no final evaluation complete |
| 14 Test session coverage and driver information | Research design and evidence plan | No completed ablation established | Qualifying-only vs mixed-session, sample-size control, profile-conditioned vs unconditioned PPO |
| 15 Complete LSEP evidence | ethics_status.md; source/claim safeguards | Status tracked, not approval | Actual ethics evidence, source conditions and redistribution review, sustainability/accessibility/professional analysis |
| 16 Write report and plan video | Report outline and related-work draft; detailed progress notes | Notes linked to actual outputs | Full methods/results/discussion, student review, final report figures, rendered PDF and video |
| 17 Maintain AI transparency and steady progress | Decisions/progress/validation logs; preserved negative findings | AI assistance and test/run evidence recorded across increments | Student-authored reflection, regular supervisor records, complete longitudinal time/task record |
| 18 Reproduce and package submission | Local source and result manifests; earlier archive | Some local reruns and hash checks | Fresh-machine demo, lawful minimal artifact pack, figure/table reconstruction, final PDF/video size/playback and actual submission checks |

## Next gate checklist

- Preserve power-grid001 rejection; define and execute a new numerical protocol without retroactively changing its acceptance criteria.
- Accept calibration-fit001 only as a descriptive development diagnostic; do not install its coefficients as a validated F1 car.
- Review acceleration derivative/selection sensitivity and operating regimes before richer fitting; retain same-event validation limitations.
- Establish permitted geometry and corner-profile provenance independently of final target speed traces.
- Freeze untouched event-level final roles before production parameter/controller tuning.
- Advance controller comparisons and PPO only on an explicitly accepted model, with common dynamics, feasibility and information.
- Keep empirical inverse reconstruction, forward prediction and simulator optimisation as separately evaluated claims.
- Progress literature, LSEP, report and student reflection in parallel; preserve pending ethics/dates without inventing decisions.

No training, download or existing-result modification was performed during this review.
