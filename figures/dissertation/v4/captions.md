## 01_grid_studies

Original cell-solver study and four finer-grid diagnostic arms. Different arms have different constraints; offsets are relative to each armÃ¢â‚¬â„¢s own finest result, not true error. Historical rejected gate is retained.

## 02_event_validation

Event solver: output sampling is separate from integration refinement. Right panel also varies maximum integration step per saved protocol. Reference is numerical, not exact; analytic checks are recorded separately. Synthetic only.

## 03_calibration_identifiability

Bahrain development acceleration-window diagnostic. Coefficients scale with assumed mass while predicted acceleration is unchanged. Right panel is objective sensitivity, not a confidence interval. These are not verified car or electrical parameters.

## 04_reconstruction_errors

Synthetic analytic straight with known deployment truth. Exact and noisy endpoint observations fitted across assumed base powers and initialisations. Multiple starts are not independent experimental samples. Low speed error does not verify deployment.

## 05_reconstruction_maps

One exact-observation solution per assumed base power, with synthetic truth shown. This figure demonstrates ambiguity under the declared analytic model; it is not an inferred real-team deployment map.

## 06_synthetic_controller_comparison

All points use the original synthetic constant-force model and nominal scenario. PPO pilots use 16,384 steps per seed. DP uses finite action/energy grids; exhaustive reference covers its discrete action set. Event/power-model times are not mixed into this comparison.
