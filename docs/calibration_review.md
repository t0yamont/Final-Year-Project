# Calibration diagnostic review — 28 October 2026

## Decision
Accept results/calibration-fit-001 as a reproducible development identification diagnostic. Do not accept it as a calibrated physical F1 vehicle, verified engine/electrical power, recovered deployment map or a validated forward simulator. This decision is based on metrics.json, manifest.json, identification_progress.md, calibration_data_plan.md and the guide's Step09 requirements. Results remain immutable.

## Evidence and scale
The fitted equation is m*v*a = P_total - k*v^3. At assumed mass 800 kg, effective total power is about 453.278 kW and k about 0.511429 kg/m. The solver reports no bound hit; design condition number is approximately 6.80 in the implemented scaling. Fit acceleration RMSE is approximately 2.238 m/s²; lap13 within-event validation RMSE is 2.308 m/s², with bias -0.327 m/s² and residual extremes approximately -9.259 and +8.062 m/s². The objective minimises power-equation residual, not equally weighted acceleration error. Solver success and moderate algebraic conditioning are not proof of physical identification.

## Structural mass confounding
Dividing by mass gives v*a = P_total/m - (k/m)*v^3. These observations identify ratios within this model. Multiplying mass, P_total and k by the same positive factor preserves predicted acceleration, unless imposed bounds intervene. The saved 750/800/850 kg fits show exactly this: power changes from approximately 424.948 to 453.278 to 481.607 kW and drag coefficient from 0.479464 to 0.511429 to 0.543393, while acceleration predictions and validation errors remain unchanged. Therefore the mass sweep demonstrates non-identifiability, not robustness of physical power estimates or an empirical mass estimate. Assumed mass needs independent justification; parameter intervals cannot be interpreted as measured car uncertainty merely from this sweep.

## Other confounding and statistical limitations
- P_total combines combustion/electrical contribution and other unmodelled effects. No observed battery/deployment labels separate them.
- Rolling resistance, grade, wind, tyre/slip effects, changing effective power and cornering can enter residuals or fitted coefficients. High throttle with no brake does not prove straight-line motion.
- Finite-difference acceleration from quantised speed at irregular source intervals is noisy. Adjacent pairs share observations, so 287 fitting rows are not 287 independent experimental replicates.
- Selecting positive acceleration and high throttle creates a conditional subset; discarding nonpositive derivatives can bias an acceleration fit upward. Gap, throttle and gear/DRS rules need sensitivity review.
- The fits pool operating regimes. DRS-code stratification is exploratory, potentially confounded by speed, gear and power schedules. Its lower error must not be treated as a causal DRS estimate or a prospectively validated model choice.
- Fit laps4/10 and validation lap13 share driver, car, circuit, session and conditions. This diagnoses interpolation/generalisation within this development event; it does not establish transfer or final independent prediction.
- Race-control-derived Deleted=False is source/parser evidence. Sparse Rainfall=False observations do not independently verify a continuously dry track.
- The drag-profile refit is an objective-sensitivity curve, not a confidence interval. Synthetic exact-recovery tests validate regression mechanics only.

## Required promotion gates
1. Define the intended forward quantity and acceptable error before further fitting; compare with declared simple alternatives.
2. Examine residuals by speed, gear/DRS, lap and operating segment, including derivative/selection sensitivity and blocked rather than rowwise replication.
3. Justify independent physical parameter ranges and identify which quantities remain assumed, estimated or structurally ambiguous.
4. Resolve the separate physical solver's convergence gate before using fitted values for controller claims.
5. Prepare track constraints with permitted independent provenance; avoid supplying the full target speed envelope and then calling replay fit independent prediction.
6. Freeze an untouched event-level evaluation protocol before final calibration/tuning. Keep Bahrain as development.
7. Complete known-ground-truth synthetic deployment reconstruction with uncertainty/noise before real conditional inverse fits. Report multiple plausible solutions where warranted.

Review outcome: useful negative/limiting evidence for the dissertation's identifiability argument; insufficient evidence for a production car model. No new source claims, parameter fits, training, downloads or result edits were made by this review.
