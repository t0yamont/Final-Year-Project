# Full-project dataset expansion proposal — 10 November 2026

Source-selection update: docs/data_source_options_audit.md selects OpenF1 plus simulation after successful local probes. Eight weekends remain the target frame; no whole-season coverage is claimed. Bahrain and Spain are now explicitly development. The historical authentication obstacle applies to the direct FastF1 archive path, not the successfully tested public OpenF1 route.

Status: recommended acquisition design, not a frozen split or evidence that the data have been obtained. Extends data_sufficiency.md. Preserve the one-circuit principal controller comparison; a broader telemetry dataset supports model validation, reconstruction, session-mixing and observable-profile experiments. More circuits do not require full PPO training on every circuit.

## Recommended sampling frame

Start with eight 2025 weekends, selected for operating-condition diversity and usable coverage rather than favourable model results. Candidate pool: Bahrain, Barcelona, Silverstone, Monza, Spa, Suzuka, Hungary and Abu Dhabi. Audit availability, wet running, weekend format, provenance and quality before assigning roles; a named candidate is not a promise of clean data. Preserve the broad all-useful-seasons catalogue separately. Keep the main physical study within 2025 initially.

For standard weekends, seek FP1, FP2, FP3, qualifying and race. Eight complete standard weekends give a maximum of 40 event-session combinations. Keep sprint sessions separately labelled if included. Cache session acquisition and retain all exclusion counts; do not repeatedly download the same session per driver.

Begin analysis with the existing reference team and both car entries, retaining actual driver identity and substitutions. Expand to two additional constructors as explicit strata. With three teams and two car entries, the proposed frame has up to 240 car-session combinations before missingness and quality filtering. This is a coverage target, not a statistical sample-size justification or a count of independent observations.

Choose additional constructors for model/context coverage, not because their standings or lap times look similar. Same-year cars still differ in powertrain, aerodynamics, setup and upgrades. Even teammates need context labels. Do not pool raw traces into one fixed-parameter car fit. Use separate team/context fits initially; consider partial pooling only with an explicit model and validation. Other years remain a later domain-shift study if required.

## Splits and questions

Provisional allocation: four development weekends (including Bahrain), two model-selection/validation weekends and two untouched test weekends. Freeze named assignments after coverage-only checks and before examining model performance. Every session, car and lap from a test weekend stays out of fitting, normalisation, feature selection and tuning. Two test weekends support a bounded study, not universal cross-circuit generalisation. Expand if uncertainty remains too large. If a test set is used to revise methods, it becomes development and must be replaced.

- RQ1: reconstruct feasible deployment families under declared assumptions; validate observable motion separately. More circuits constrain model behaviour but do not supply real electrical ground truth.
- RQ2: compare PPO, refined DP and heuristics on the principal circuit, with common physical parameters, boundary conditions and information. Distinguish independently sourced geometry from target telemetry-derived constraints. Additional circuits can provide separately labelled transfer checks; they are not necessary to multiply full training cost.
- RQ3: compare qualifying-only and mixed-session fitting with the same fitting budget (including matched laps/distance as appropriate), tuning budget and held-out qualifying groups. Also report a larger mixed-data arm to distinguish volume from diversity. Race/practice fuel, tyres, traffic and weather are possible confounders, not measured deployment effects.
- RQ4: derive observable braking/throttle profiles from development data and test conditioning on held-out groups. Compare conditioned/unconditioned PPO using identical scenario distributions, training budgets and independent seeds. Driver identities are contextual labels, not proof of intrinsic driving styles. Preserve variation within drivers and control track/car/session effects where observable.

## Adequacy and cost controls

Use clean laps for each question's defined operating conditions; keep excluded/wet/traffic-affected records labelled rather than silently deleting them from the audit. Quality criteria include gaps, source interpolation, pit laps, flags, tyre context, DRS and plausible channel values. Unknown fuel/setup remains a limitation.

Audit one additional weekend first to measure access success, clean yield, runtime and storage, then acquire the frozen frame in resumable batches. Current archive access must be verified; the previous authentication/subscription obstacle is not assumed resolved by installing MATLAB. Do not start a blind season-wide download.

Assess sufficiency using whole-lap/session learning curves, grouped predictive errors, physical constraint failures and sensitivity to assumptions. Predeclare practical error/precision targets before final testing. Add weekends when independent coverage is weak, rather than treating more adjacent rows as independent replication. Keep independent PPO seed uncertainty separate from telemetry sample uncertainty. Save meaningful new comparisons as versioned dissertation PNG/PDF figures.

No public-data expansion alone establishes true battery trajectories or real-world optimal electrical deployment. The full achievable contribution is a validated, reproducible conditional study with all four questions evaluated within explicit evidence limits. Verified electrical labels would require another authorised source.

## MATLAB role

MATLAB R2026b Update 1 starts successfully at C:/Program Files/MATLAB/R2026b. The licence availability test returned true for Optimization Toolbox, but `which('fmincon')` returned empty: the solver installation/path still needs resolving. Evidence: logs/agent_tools/2026-11-10/matlab_availability.txt. Keep acquisition and existing RL in Python. Use MATLAB for a bounded independent optimal-control benchmark once the solver check passes. Assess local solver reliability, constraint residuals, agreement with small exhaustive/DP cases and runtime before scaling. Do not claim a global optimum from a local nonlinear solve or assume MATLAB is faster without measurement.
