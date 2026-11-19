# Multi-agent project workflow

## Bahrain deployment study

The additional same-session transfer cohort has since been scored on driver 22 laps 2, 5 and 13. Both compared paths failed the cross-driver gate. Record these laps as used in any future evaluation design. [Predeclared comparison](../configs/bahrain_driver_transfer_protocol.json) · [Results](bahrain_driver_transfer.md)

Follow the archived sequence from timing-line registration through a free-running fit on lap 13, scoring on separate laps 4 and 10, constrained deployment search, and local timing shifts. Keep the same starting charge, finish speed and physical constraints within a policy comparison. For each reported zone, inspect its wheel work under grip changes and the local speed errors on both separate laps. Before any new fit, freeze the next independent evaluation cohort and the acceptance criteria. The original Bahrain split has been scored. [Calibration and gates](bahrain_qualifying_pace.md) · [Deployment results and replay commands](bahrain_deployment_zones.md)

## Dissertation integration as of 18 November 2026

The simulator, GPU training and controller evaluation have been run. Use the [evidence register](PROJECT_STATUS.md) and the latest study reports for the numerical and physical gate outcomes. The RQ3 final qualifying prediction was scored with frozen development fits. Treat the Abu Dhabi results as known in future method changes and retain the Belgian exclusion. The remaining writing starts from the [dissertation guide](DISSERTATION_GUIDE.md).

## Current regeneration plan - 17 November 2026

Brake MGU-K regeneration now supersedes the earlier harvesting deferral. Implement optional automatic recovery during required braking, preserving total braking deceleration and common controller constraints. Record sourced 2025-era bounds separately from assumed capacity, charging efficiency and rear braking share. MGU-H, detailed tyre/axle dynamics and regulatory-compliance claims remain excluded. The implementation, sources and evidence belong in [regeneration_study.md](regeneration_study.md).

Preserve old result/checkpoint/figure bytes and the pre-change source archive. First verify independent energy/braking cases, capacity and lap-budget boundaries, and numerical refinement; then establish matched-controller evidence on the changed model. The regeneration-aware environment has eight observations rather than the legacy six. Old source-hash training gates must reject the changed sources until a new validation run and protocol bind them. Only then consider fresh CUDA training. This update does not claim new training or invalidate the historical model-specific results.

## Current source and execution policy — 10 November 2026

The accepted deliverable is a defensible model-based study. OpenF1 plus controlled simulator data is the selected route (docs/data_source_options_audit.md). The eight event IDs and 4/2/2 development/validation/test roles are frozen in configs/openf1_dataset_plan.json before new modelling. Bahrain and Spain remain development. Belgium's sprint sessions stay separately labelled and are excluded from the initial standard-session ablation. Test acquisition/schema checks are permitted; test model scores and profile extraction remain withheld until final evaluation. Metadata counts are not usable-data counts.

Use one bounded specialist when useful, rather than automatic agent fan-out. The coordinator is authorised to execute local runs. Retain historical evidence and do not demand perfect car identification before a conditional model-based experiment; require numerical reliability, declared assumptions, sensible empirical checks and honest uncertainty.

Created 27 October 2026. This workflow implements the user's request to continue the whole project with multiple agents. It is a durable execution plan, not a claim that the experiments are complete. Research questions and claim boundaries remain in `scope.md`; experiment acceptance criteria remain in `evidence_matrix.csv`.

## Coordination model

Use one coordinator and at most three concurrent specialists. Rotate specialist roles as gates are reached. The coordinator owns shared interfaces, CLI integration, dependency decisions, final review, status updates and combined verification. Each specialist receives an explicit file ownership list, required inputs, a bounded deliverable and acceptance criteria. Specialists must not edit another agent's files without coordination. Shared files such as the CLI and configuration contract stay with the coordinator.

At each cycle the coordinator reads PROJECT_STATUS.md and the working tree, chooses the next unblocked gate, dispatches independent tasks, reviews the resulting code and evidence, runs appropriate integration tests and records the handoff. A specialist report must state files changed, commands run, observed outcomes, limitations and next dependencies. Passing tests do not imply empirical validity. No agent may silently mark a live experiment complete from fixture evidence.

## Roles and ownership

| Role | Primary responsibility | Typical owned artifacts | Review requirement |
| --- | --- | --- | --- |
| Coordinator | Priorities, interfaces, integration, scope and evidence gates | CLI, shared contracts, PROJECT_STATUS.md | Inspect specialist outputs and integrated tests |
| Data agent | Schedules, bounded telemetry retrieval, quality and split provenance | Data modules, data tests, data audit documentation | Check missingness, failures, source identity and leakage |
| Physics agent | Action-responsive dynamics, braking, energy and numerical validity | Simulator modules, independent physics tests | Analytic checks and refinement error bounds |
| Research/evidence agent | Source audit, decision logs, report traceability | Workflow, literature and dissertation drafts | Verify cited claims and distinguish plans from results |
| Reconstruction agent | Conditional inverse inference and ambiguity | Inverse models, synthetic recovery experiments | Independent truth and multiple feasible solutions |
| Baselines agent | Common heuristics and DP | Controller modules, convergence tests | Tiny exhaustive reference and physical replay |
| RL agent | Gymnasium contract, PPO scripts and bounded local run pack | Environment, configuration, training/evaluation scripts | Environment checks and bounded smoke checks |
| Evaluation agent | Frozen comparisons, uncertainty and figures | Analysis scripts, result tables and plots | Reproduce results from immutable run evidence |

Only three specialist roles run simultaneously. Later roles reuse available slots; this plan does not require eight active agents.

## Full-scope gates and dependencies

| Gate | Work and owner | Dependencies | Acceptance evidence |
| --- | --- | --- | --- |
| G0: reproducible foundation | Coordinator and research | Existing repository | Offline tests, source hashes, runnable instructions, explicit assumptions; original source-document availability recorded |
| G1: metadata and pilot acquisition | Data | G0 | Live pilot manifest, provider/client version and cached response hashes, session identity, failures and resource measurements; support flags never presented as verified telemetry |
| G2: useful dataset and split freeze | Data and research | G1 | Coverage by season/event/session/driver; lap exclusion reasons; exact layout and technical regime; frozen event/session split IDs; train-only preprocessing; measured download budget |
| G3: forward simulator | Physics | G0; real calibration also needs G2 | SI and action conventions; nonnegative usable energy; terminal requirements; deployment changes motion; pre-corner braking; independent analytic tests; numerical refinement error below claimed effects |
| G4: reconstruction (RQ1) | Reconstruction | G3, then G2 for real laps | Synthetic known-truth recovery; parameter bounds; multiple starts and sensitivity; feasible map families; observed-fit error distinct from real hidden-action accuracy |
| G5: physical baselines | Baselines | G3 | Zero-deployment diagnostic, uniform and tuned heuristics, DP sharing transitions/constraints; tiny exhaustive match; grid convergence; feasible continuous replay; solve-time records |
| G6: qualifying/mixed data ablation (RQ3) | Data and evaluation | G2–G3 | Same model/test set/tuning rules; matched-volume control; forward error separate from inverse fitting; no hidden test actions fitted into primary score |
| G7: RL preparation | RL | G3 and G5 | Environment contract, termination vs truncation, scaling fitted on training only, common terminal conditions, seed records, reproducible checkpoint/evaluation path |
| G8: local PPO experiment (RQ2) | Coordinator and RL agent | G7 | Reviewed run pack; measured pilot budget; independently seeded runs; checkpoints, logs, versions and failures preserved; held-out test untouched during selection |
| G9: profile extension (RQ4) | RL and evaluation | Credible G8 core; enough compute | Observable profiles with permissible provenance; same training distributions and tuning budgets with/without inputs; held-out profile comparisons; no driver-skill claims |
| G10: final evaluation | Evaluation | G4–G8; G9 if completed | Frozen paired scenarios; feasible lap-time differences and failure rates; energy/drag/grip/power sensitivity; seed-level uncertainty; separate training, solve and inference costs |
| G11: dissertation and delivery | Research and student | Evidence from all completed gates | Every result traceable to run/figure IDs; critical negative findings; limitations; AI-use chapter disclosures and student reflection; course-format and submission artifact checks |

Literature review, source verification, decision records and dissertation Methods drafts continue across gates. Ethics status, deadlines and weekly hours remain pending as requested; do not invent them or repeatedly block independent code work. Student/supervisor institutional actions remain explicit unresolved dependencies for final submission.

## Scientific controls

Keep observations, assumed parameters, reconstructed quantities and simulated outputs visibly labelled. A telemetry fit cannot verify real battery energy or deployment. Future sessions in a schedule catalogue remain candidates and must be excluded from completed-session acquisition denominators. A season cohort is a preliminary classification; do not pool layouts, cars or regulations by year alone. Freeze permitted test information before calibration. Using later race data makes an analysis retrospective, not a pre-qualifying forecast.

PPO, DP and heuristics must share scenario constraints and transition code. Disclose any oracle information. Numerical and parameter uncertainty must accompany small gains. Report all failures and negative results. Brake MGU-K regeneration is now in scope under the 17 November update; SAC and unseen-circuit transfer remain deferred extensions.

## Authorised local execution

Before any large acquisition or training run, produce a run pack containing exact commands, environment lock, input/output paths and hashes, seeds, resource limits, checkpoint/resume behavior, stopping conditions, expected files and a small verified pilot. Runtime estimates must be measured or labelled unknown. The coordinator executes authorised local acquisition, training and validation, monitors bounded runs, and verifies saved artifacts. Ask the user only for genuinely missing access or institutional input. MATLAB is optional where a measured benefit warrants it; no routine manual handoff is required.

## Dissertation-ready work record

For each increment record date, gate/RQ, action, files/source revision, assumptions, discoveries, problems, verification commands and outcomes, interpretation limits, AI contribution and next dependency. Associate each empirical run with configuration/input/output hashes, environment, split IDs and seed. Write Methods from implemented behavior and Results only from validated artifacts. Student reflection and claimed learning require student input.

The inherited `source_audit.md` records a previous inspection of course documents. Those original documents are not established as present in this checkout. Exact source revalidation and current university requirements remain outstanding; the inherited register must not be described as a fresh inspection.

## Execution cadence

For each active work cycle, use only the specialists justified by independent bounded work; at most three specialists. The coordinator acts as integration reviewer, checks the actual diff and evidence, resolves interface conflicts and runs the relevant combined tests before advancing a dependent gate. Return a compact progress handoff with remaining manual inputs. Resume the next unblocked gate in a subsequent active cycle. This workflow defines collaboration; it does not schedule unattended or recurring execution. Packaging and GitHub publication must be reported according to what actually occurred.

## Execution ownership update — 28 October 2026
The student has authorised local agent execution of training and validation, superseding the manual handoff requirement above. Agents will execute bounded pilots, measure runtime and resource use, preserve seeds/checkpoints/results, and scale only after validation. The validation gates and evidence boundaries remain applicable.
