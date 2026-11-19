# Model preparation — 11 November 2026

Completed the next stage after acquisition: grouped motion inputs, coverage figures and initial full-circuit input assessment. Existing physics modules and training checkpoints were unchanged.

## Prepared data

`results/openf1-motion-001` contains 46,051 development and 15,501 validation adjacent-pair windows, drawn from 318 and 124 conditional candidate lap groups respectively. Some lap groups can contribute no windows after pair screening. Event/session/driver/lap identities are retained. Entire-event roles are disjoint, and test-role preparation is unavailable in the script. These are dependent observations, not independent experimental replicates.

The declared screen uses maximum pair spacing 0.5 seconds, throttle at least 95%, no reported braking, positive speed and unchanged gear/DRS. Negative and zero acceleration remain included. Source hashes were verified. No new source data were fetched for table generation or coverage plotting.

## Development diagnostic

`scripts/assess_circuit_inputs.py` fits the existing effective model `m*v*a = P_total - k*v^3` separately for each driver-1 development event/session/DRS context. The assumed mass is 800 kg. Before fitting, the script assigns the chronological last `max(1, floor(number_of_laps/4))` laps to within-development holdout, requiring at least three laps and five windows per side. Insufficient contexts remain recorded as skipped. This does not use the separately reserved validation or test cohorts.

Twenty-one contexts were evaluable. The fitted model's holdout acceleration RMSE is lower than a training-mean constant-acceleration baseline in 20 contexts; one does not improve. No power/drag coefficient hit the inherited fit bounds. All 21 reported RMSEs were independently recomputed. The fitting objective is power-equation residual, while the displayed evaluation metric is acceleration error.

These checks support further model construction. They do not identify the true combustion/electrical split, resolve mass confounding, or validate free-running lap-time prediction. Observed speed is supplied to the acceleration predictor. Contexts and adjacent windows are dependent, so 20/21 is descriptive rather than a statistical significance claim. Fuel, setup, grade and driver controls can enter fitted effective parameters. Do not average these fits into one supposedly measured car without a declared reference-model decision.

## Geometry

The candidate [TUM Sakhir centreline](https://github.com/TUMFTM/racetrack-database/blob/master/tracks/Sakhir.csv) is retained with its source licence and SHA-256 in `results/circuit-input-assessment-001`. Its 1,082 vertices form a 5,405.749 m closed polyline, with positive finite widths and no zero-length edges. It is approximately 0.1155% shorter than the [official 2025 Bahrain length of 5,412 m](https://www.formula1.com/en/racing/2025/bahrain). Length agreement is only a basic consistency check; the geometry is an approximate smoothed centreline rather than a measured racing line.

## Next implementation gate

1. Check layout/version and direction; construct a periodic curvature representation and inspect smoothing sensitivity.
2. Declare a reference vehicle and grip/braking assumptions, retaining effective total power separately from assumed electrical assistance to avoid double counting.
3. Build the full-circuit speed/braking envelope and connect it to the accepted event integrator. Verify periodic boundary conditions, energy accounting and spatial refinement before controller training.
4. Assess observable motion against development/validation evidence with clear permitted inputs. Preserve the final test events for the frozen evaluation.

Coverage and diagnostic plots are saved as 300 dpi PNG and vector PDF in `figures/dissertation/openf1-coverage-v1` and `figures/dissertation/circuit-inputs-v1`; both were visually inspected. This stage performs data/fit diagnostics, not a new PPO training experiment.

Update later on 11 November: full-circuit numerical implementation is now completed; see full_circuit_validation.md. The next implementation gate list above is retained as the original preparation plan.
