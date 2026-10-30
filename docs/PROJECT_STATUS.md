# Project status

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
