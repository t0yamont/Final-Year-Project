# Research scope and claim boundary

The controller extension asks whether PPO or soft actor-critic can learn a feasible deployment schedule directly on the calibrated Bahrain vehicle and whether widening the actor from 64 to 256 units helps at the same interaction budget. The circuit extension asks whether those schedules transfer to a layout selected for a contrasting braking pattern. All learned policies choose deployment. The model automatically harvests during required braking. [Controller and circuit protocol](../configs/circuit_policy_transfer.json)

The original calibrated vehicle subsequently missed the sector-two tolerance on three laps from the other Red Bull driver at Bahrain. A geometry-only path replacement also failed. The available lap and sector checks support a model-based deployment study with explicit local limits. [Driver transfer](bahrain_driver_transfer.md)

The main question is **where, and at what power, should the car deploy a finite supply of electrical energy to minimise a simulated qualifying lap at Bahrain?** Evidence consists of geographically located wheel work, feasible paired lap times, timing-shift interventions and sensitivity to grip. The 2025 qualifying data constrain the motion model. The estimated gains and energy use apply to that model. One of two same-session laps exceeded the speed-error limit, so exact braking and corner-exit placements remain provisional. [Deployment map](bahrain_deployment_zones.md) · [Calibration evidence](bahrain_qualifying_pace.md)

The [results draft](../report/06_results.md) and [evidence matrix](evidence_matrix.csv) record the implemented scope. The location experiment uses the calibrated centreline model. The earlier Sakhir vehicle supplied neural training and the original controller baselines. RQ1 is limited to selected real development windows, and the final RQ3 prediction estimates acceleration at supplied speed with one covered qualifying test event. RQ4 remains conditional. The earlier prospective aims below are retained for comparison with the executed studies.

Status: proposed research design, prepared 27 October 2026 and clarified 10 November 2026 (Europe/London). Current evidence is recorded in agent_handoff.md and data_sufficiency.md; this design document alone does not establish empirical results. Basis: the supplied F1 COM3001 implementation guide, especially Steps 01 and 06–14. The guide is planning context; subsequent explicit user authorisation of local training and validation supersedes the original manual-execution restriction.

## Aim and intended contribution

This project investigates electrical deployment for a single simulated Formula One qualifying flying lap. It will connect incomplete public telemetry to a declared vehicle model, investigate the ambiguity of reconstructing hidden electrical assistance, and compare proximal policy optimisation (PPO) with dynamic programming (DP) and two practical deployment heuristics. The contribution sought is a reproducible experimental pipeline and a critical assessment of its assumptions. No claim of first use, superior real-world driving, or regulation-complete simulation is made.

The data ambition is broader than the principal optimisation result. Following the student's 27 October 2026 clarification, the historical source plan used FastF1; the accepted 10 November implementation uses OpenF1 historical data with archived-file fallback and the audit will consider every season that can usefully support the project. Usefulness is an inclusion decision, not a presumption that all available seasons are compatible. The audit will record telemetry availability, session coverage, layout continuity, vehicle/regulatory regime, data quality and contribution to a specified research question. Practice, qualifying and race coverage and exclusions will be reported by season, event, session and driver. The main controller comparison will still concern one dry qualifying circuit. The 2025 season and Bahrain remain candidates for that result, not confirmed choices. Incompatible technical regimes, layouts and vehicles must not be silently pooled; 2026 requires a separately justified model before entering physical comparisons. Failed retrievals and unsuitable laps must remain visible in the audit rather than disappearing from a denominator.

## Inputs, outputs and interpretation

| Evidence class | Intended content | Permitted interpretation |
| --- | --- | --- |
| Observed telemetry | Source speed, timestamps, RPM, gear, throttle, binary brake and position where supplied, with original units and provenance | Evidence of available motion and control channels; source interpolation and missingness must be recorded |
| Fitted or reconstructed quantities | Calibration parameters, effective corner constraints and deployment maps inferred under explicit bounds | Conditional estimates; several hidden deployments may fit a trace |
| Assumed quantities | Reference mass, drag, combustion-power model, grip, efficiency, initial energy and terminal conditions where independent evidence is absent | Model inputs with sensitivity ranges; they are not measurements of a team's car |
| Optimised simulation outputs | Executed deployment, speed, battery-energy accounting, lap time and feasibility from the action-responsive simulator | Controller performance within the declared model and information conditions |

The planning guide states that the public source does not provide verified electrical-power and battery-state labels. The ingestion audit must verify the available schema and retain that distinction in every output. Fitting a speed trace does not verify the real battery trajectory. Synthetic action-recovery error is meaningful because synthetic ground truth is known; real-data deployment accuracy is not an available metric without independent labels.

## Model boundary and qualifying objective

The first production model will use one declared reference vehicle, a fixed racing line, automatic feasible braking and deployment-only electrical control. Internal dynamics will use SI units. The action convention must specify whether power is at the battery or wheels; conversion losses must then be accounted for consistently. The original deployment-only scope is superseded by the 17 November 2026 brake-regeneration update. The reference model includes optional automatic MGU-K recovery during required braking, with friction braking reduced to preserve total deceleration. Deployment remains the controller action. Detailed hybrid subsystems, MGU-H and tyre/axle dynamics remain excluded. Assumptions, 2025-era source bounds and validation are recorded in [the regeneration study](regeneration_study.md); these do not establish regulatory compliance.

The objective is minimum simulated elapsed time over a complete lap, conditional on common initial speed, usable energy, terminal reserve and terminal-speed requirements. Deployment must alter acceleration and elapsed time; a simulator replaying a fixed speed trace cannot establish optimisation benefit. Energy depletion must be solved consistently with segment duration. Braking must occur before a restrictive corner, rather than through an instantaneous speed clip. The precise finish condition will be decided before controller tuning and tested for sensitivity.

All controllers must use the same physical transition code and scenario limits. DP is a discretised model-aware reference whose numerical convergence must be investigated; it is not automatically an exact continuous optimum. If a controller receives exact uncertain vehicle or profile parameters unavailable to its comparator, that information advantage must be explicit. Training cost, optimisation cost and inference cost will be reported separately.

## Research questions and tests

**RQ1:** Under declared vehicle assumptions, which deployment patterns are compatible with observed telemetry, and how uncertain is reconstruction? A synthetic recovery experiment will precede a bounded real-lap study. The study will compare trace mismatch, constraint feasibility and variation across plausible parameter sets and optimiser initialisations. Different feasible maps with similar fits would be evidence of ambiguity, not a failed result to suppress.

**RQ2:** How closely does PPO approach a refined DP reference on the selected qualifying circuit, and at what training and inference cost? The nominal comparison will include uniform and tuned deployment heuristics, a zero-deployment diagnostic, and sensitivity to energy budget and vehicle parameters. Paired scenario differences and failure rates will accompany feasible lap times. DP may outperform PPO; no positive outcome is assumed.

**RQ3:** Does adding practice and race telemetry improve held-out qualifying modelling compared with qualifying-only data? The proposed ablation holds the observable model, test sessions and tuning procedure fixed. A matched-sample-size control will distinguish data volume from session diversity. Mixed-session data may increase coverage while adding confounding fuel, tyre and operating conditions. Inverse-fit error will be reported separately from any forward prediction error.

**RQ4:** Does conditioning deployment on an observable driving profile improve simulated performance across profiles? Two PPO variants will share the training profile distribution and evaluation scenarios; one receives profile features and the other does not. Observable braking and throttle patterns are not claims about intrinsic personality or skill. Profile conditioning is contingent on a credible core comparison and sufficient authorised compute budget.

The evidence matrix specifies planned experiments, metrics, figures and completion criteria. None of these questions currently has an empirical answer in this document.

## Proposed evaluation and leakage control

The initial proposal is retrospective, known-circuit, held-out-session evaluation across the compatible audited season subsets. Subject to the audit, the reporting circuit's complete qualifying session will be reserved for final testing, with permitted practice sessions and other events used for development. Using later race observations would make the study retrospective; it must not be described as a pre-qualifying forecast. This proposal does not yet constitute a frozen split.

Whole-event separation is preferred where the available design supports it. Season, technical regime and circuit-layout identifiers must be retained in every split, and a season-transfer claim would require a separately declared held-out-season experiment. When practice and qualifying from one event occupy different groups, shared circuit and conditions weaken independence and must be stated. Smoothing, scaling, vehicle fitting, effective corner envelopes, profile derivation and checkpoint selection must use development data only. A final test speed trace cannot supply corner limits and then serve as independent validation. Test geometry and performance targets require separate declared provenance. A later inverse fit to a held-out lap is a separately labelled diagnostic and cannot feed back into primary tuning.

Independent training seeds, rather than individual timesteps, form the principal replication unit for PPO. Five training seeds are a provisional planning target, subject to measured runtime and the authorised compute budget. Failure records must be retained. Differences smaller than numerical or parameter uncertainty do not support strong performance claims.

## Deliverable boundary and execution ownership

The minimum viable research outcome is a verified simulator, bounded reconstruction study, credible heuristics and converged DP comparison, a reproducible PPO study, and independent analysis with explicit limitations. Brake MGU-K regeneration is now in scope; SAC and unseen-track transfer remain deferred. If profile conditioning cannot be completed, the limitation and any fixed-profile sensitivity will be reported honestly.

The assistant is authorised to execute local training and validation, using bounded pilots, measured runtime, checkpoints and stopping checks before scaling work. The user also authorises MATLAB where it provides a practical benefit. Personal reflection requires the student's input. Official deadlines, ethics status and available weekly hours remain pending at the student's request; this does not prevent independent source audits or synthetic development.

## Scope revision - 17 November 2026

Brake regeneration changes battery accounting and the controller observation from six to eight values. The regeneration study must establish new numerical and matched-controller evidence before fresh CUDA training. Existing deployment-only results remain valid only for their original model; their source-hash gates cannot authorise training with changed physics. Capacity, charge efficiency and rear braking share are assumptions, not verified car parameters. See [the regeneration study](regeneration_study.md) for the current contract.

## Work record for this document

**Action:** translated the guide's project direction into a bounded research design and an evidence matrix. **Discovery:** broad telemetry coverage and one-circuit optimisation answer different questions; missing real energy labels require distinct inverse and forward evaluations. **Problems:** final circuit, useful season subset, reference parameters, usable data, permissions and available compute remain unconfirmed; ethics evidence, deadlines and weekly hours remain explicitly pending. **Next evidence:** source review, runnable offline foundation, a one-event ingestion audit and supervisor review of the proposed questions. This scope is a draft for academic discussion, not a record of supervisor approval.

### Scope revision — 27 October 2026

The initial guide-based single-season data proposal was superseded during setup by the student's request to use FastF1 and every useful season. This revision expands the availability audit; it does not authorise treating incompatible seasons as one physical dataset. No empirical multi-season coverage is claimed here. The older supplied `F1 energy deployment.docx` contains three research questions, while the named implementation guide proposes four. The four-question design is retained provisionally for review; no supervisor agreement is asserted. The guide's named C4 file, `F1_Energy_Deployment_Workplan.docx`, was not found in the inspected source directory.
