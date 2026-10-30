# Effective-parameter identification diagnostic — 28 October 2026

Implemented bounded least squares for `m*v*a = P_total - k*v^3`, fitted in MW-scaled coordinates. P_total is constant effective total wheel power over the selected samples; k is an effective drag coefficient in kg/m. Neither is a verified physical vehicle parameter. Bounds of 100–1,200 kW and 0–3 kg/m are deliberately broad diagnostic assumptions, not FIA limits. Mass is fixed by assumption, not estimated. Electrical assistance and battery energy are neither observed nor recovered.

## Inputs and selection

Consumed immutable results/calibration-data-001 tables and recorded their hashes. Fit: lap4 137 pairs plus lap10 150 pairs =287. Development validation: lap13 144 pairs. Lap16 excluded from the primary diagnostic due to gaps. Data preparation requires adjacent endpoints with throttle>=95, no brake, stable gear/DRS, positive speed change and dt<=0.5s. No smoothing, interpolation or bridging. These are acceleration-window proxies; steering/curvature was not verified, so full throttle/no brake does not establish a straight. Positive acceleration selection biases the sample distribution. Adjacent derivative samples can be correlated and are sensitive to speed quantisation and approximately quarter-second sampling.

## Executed fit

Saved results/calibration-fit-001/metrics.json and manifest.json. At assumed 800 kg: effective P_total=453,277.582 W; k=0.511429 kg/m; no boundary hit. Scaled design condition number=6.7963; fit speed range=37.917–89.028 m/s. Fit acceleration residual RMSE=2.23762 m/s²; development-validation RMSE=2.30810 m/s², bias=-0.32679 m/s² (predicted minus observed acceleration). Validation residual range=-9.25866 to 8.06156 m/s². Power-equation residual RMSE=114,563.527 W. The optimisation minimises power-equation residuals, so acceleration RMSE is a different diagnostic weighting.

Mass assumptions 750/800/850 kg produce P_total 424,947.733/453,277.582/481,607.430 W and k 0.479464/0.511429/0.543393 kg/m. Acceleration predictions and validation error are unchanged: both fitted coefficients scale with assumed mass. This exposes structural confounding; the observations determine ratios to mass rather than mass independently. The saved drag profile refits power over 31 fixed k values, providing an objective sensitivity record without claiming confidence intervals.

DRS-code stratification (numeric source codes preserved, no causal interpretation): code12 has98 fit and53 validation pairs, P=542,124.387 W, k=.606615, validation RMSE1.24006 m/s²; code8 has188 fit and91 validation pairs, P=487,915.722 W, k=.698148, validation RMSE2.49837 m/s². One fit pair belongs to another code and is insufficient for a separate fit. Lower stratified error is exploratory, not a selected final model or causal DRS estimate. Operating regimes, gear and correlated power changes confound the comparison.

## Verification and limits

Three tests pass: exact synthetic known-parameter recovery, mass/coefficient scaling and rejection of a rank-deficient constant-speed design. These verify regression behavior, not empirical vehicle fidelity. Parameters were fit only on laps4/10; lap13 was used only for development diagnostics. No final test event or validation-derived track envelope was used. Results are not a trajectory forecast, battery deployment estimate or validated forward simulator. The separate power-model numerical refinement gate remains unresolved, so these coefficients must not be promoted into a validated racing model.

Next: justify a richer model and parameter ranges, review derivative sensitivity and gear/DRS context, establish numerical convergence, then freeze event-level evaluation before making forward-performance claims. Preserve these residuals and negative limitations. AI contribution: regression implementation, synthetic tests, bounded development fit and interpretation. No model training or telemetry files were modified by this increment.
