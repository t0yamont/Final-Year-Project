# Calibration and reconstruction cycle — 28 October 2026

## Completed work
Prepared development-only acceleration windows:287 fit pairs from laps4/10 and144 validation pairs from lap13. Lap16 excluded from primary fitting for sampling gaps. The split, SI conversion, adjacent differencing and selection rules are preserved with hashes. Positive-acceleration selection and within-event validation are explicit limitations.

At assumed mass800kg, effective total power/drag regression returns453277.582W and0.511429kg/m. Acceleration RMSE is2.23762m/s² fit and2.30810m/s² validation. The750/850kg sensitivity scales both coefficients with identical predicted acceleration: this cannot identify true mass, engine/electrical decomposition or vehicle parameters. Treat this as a diagnostic, not calibrated forward validity. See calibration_review.md.

Synthetic reconstruction under a declared exact drag-free straight model recovered known actions for fixed base power. Base power shifted±20kW yields equally fitting speed traces with different deployment and battery use, demonstrating structural nonuniqueness. One0.1m/s endpoint-noise realisation yields5.099kW action RMSE despite essentially zero endpoint fit error. Multiple starts, ground truth, bounds and feasibility are recorded in reconstruction-synthetic-002. Run001 serialization failure retained. Energy feasibility is checked after replay; a budget-constrained optimiser remains required before restrictive inverse problems. See identifiability.md.

## Numerical gate remains open
Original power-grid-001 rejected its prespecified convergence criterion. A separate predeclared diagnostic used20 runs with grids2.5→0.15625m and isolated depletion/corner controls. Smooth arms showed decreasing refinements; combined caps/depletion remained nonmonotone. Finest-pair original timing difference0.000144188s, shared-node energy discrepancy64.4991J; accounting residuals below3.65e-10J and no envelope/reserve violations. Evidence suggests cell-wide switching interacting with depletion, not an accounting leak. These diagnostics do not retroactively pass the original gate.

## Verification and next steps
63 integrated tests passed. Saved outputs for calibration-data, calibration-fit, both power-grid studies and successful synthetic reconstruction verified against their recorded SHA256s. verify_run.py now supports both existing manifest output contracts; tests detect corruption, missing files and escaping paths. Verification concerns saved outputs, not proof of empirical validity or matching current source revisions.

Next: implement and compare event-located propulsion/braking/depletion transitions, rerun original numerical protocols without relaxing criteria; extend inverse optimisation to enforce energy constraints and perform multiple noise realisations; freeze final event roles and independent geometry provenance before real reconstruction or larger physical-model training. No further PPO runs were justified while the forward gate remains open. Guide Steps01–18 status is recorded in guide_step_status.md.

AI work: three specialists and coordinator implemented/audited code, ran local numerical and synthetic experiments and drafted evidence records. No university approval, student reflection or real deployment truth was invented. Local execution remains authorised by the user; no unattended automation is implied.
