# Data-role record

On 18 November the frozen qualifying holdout was scored once for RQ3. The two test event roles were preserved. Belgium had zero eligible laps and its detailed rows remained unopened. Abu Dhabi contributed 515 primary windows in three laps with exact-DRS support. Neither event was used to fit the stored models. The final qualifying scores are now known and cannot be used to retune a method and claim a fresh independent evaluation on these same sessions. [Frozen final protocol](../configs/session_mix_final.json) · [Results and coverage](session_mix_study.md)

The active event split is frozen in configs/openf1_dataset_plan.json and registered in configs/data_roles.json: development = Bahrain, Spain, Monza and Japan; validation = United Kingdom and Hungary; test = Belgium and Abu Dhabi. These roles apply to every driver, session and provider for the event. Monza is meeting 1268; the separate Italian Imola event is not included. Bahrain pre-season testing is not included. This freeze precedes new calibration/profile/controller tuning; it does not claim circuit geometry or data quality have passed.

Validation may guide model selection. Test acquisition and completeness checks are permitted, but test telemetry cannot fit parameters, define profile distributions or build target-speed envelopes for a claimed independent prediction. If test data later influence model choices, disclose that and revise the experiment rather than silently retaining an untouched-test claim. Missing/unsuitable cells stay in coverage denominators; substitutions require a dated protocol amendment.

The following records describe the earlier state and are superseded by the active freeze above.

The Bahrain 2025 qualifying event has been used for debugging and data-quality development. configs/data_roles.json records its role as development pilot, not a final untouched test. The earlier synthetic mass/energy scenario remains the pilot evaluation case and is not a tuning objective. These classifications prevent later relabelling of inspected evidence as independent final validation.

The final event split remains unfrozen pending useful-data coverage and layout/regime review. Final split selection must happen before calibration, profile extraction and controller selection. No data were discarded or changed by this record. This is a design/provenance decision, not an empirical conclusion.
