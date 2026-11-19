# Does the recorded driving line improve the Bahrain simulator?

Replacing the circuit centreline with one qualifying lap's recorded positions, while keeping the calibrated dynamics fixed, made the simulated car faster through the lap and worsened its agreement with qualifying pace. The driving-line candidate therefore failed the existing requirements for replacing the vehicle used to produce the deployment map. The candidate and its failure are retained for comparison. [Frozen decision rule](../configs/bahrain_driver_transfer_protocol.json) · [Known-lap speed-error figure](../figures/dissertation/bahrain-path-candidate-v1/path_comparison.pdf)

## Path construction and controls

The new path uses driver 1's native XY samples from development lap 13. Coordinates were converted from decimetres to metres. Linear interpolation provided a location at each timing boundary. These two locations were 1.005 m apart. Their midpoint defines the line on the closed path. After removing duplicate consecutive locations the path had 343 vertices including the midpoint. Both geometries use the same periodic 5 m spatial resampling and 10 m Gaussian smoothing. The candidate keeps the fitted vehicle coefficients, 55-block drag regime, 30 kW reference request, 80.653 m/s initial and required terminal speed, energy and regeneration settings. Neither the candidate path nor the run uses another driver's positions or speed targets. [Candidate implementation](../scripts/test_bahrain_path_candidate.py) · [Geometry and model snapshot](../results/bahrain-path-candidate-001/)

## Same-driver checks at 160 cells per block

| Driver 1 lap | Observed (s) | Centreline time error (s) | Position-path time error (s) | Speed RMSE on centreline / position path (m/s) |
|---|---:|---:|---:|---:|
| 13, development | 92.057 | −2.284 | −9.688 | 4.83 / 5.94 |
| 4, previously scored | 91.303 | −1.530 | −8.934 | 4.53 / 5.65 |
| 10, previously scored | 91.019 | −1.246 | −8.650 | 5.36 / 5.85 |

The position-path replay took 82.369 s, against 89.773 s on the centreline. Its smoothed path length was 5,313.6 m, 59.1 m shorter. If the centreline model kept the same speed as a function of fractional distance, that shortening would explain about 0.987 s of the 7.405 s difference. The remaining 6.418 s reflects how the simulated speed changed along the new path. The precise split depends on using the centreline speeds as the reference. Both candidates met the common finish speed and grid-refinement limit. The position-path replay changed by 0.073 s at double resolution, yet failed every lap, sector-group and speed comparison in the table. [Metrics](../results/bahrain-path-candidate-001/metrics.json)

Public position samples, smoothing and the simulator's curvature-dependent speed limit together determine the new prediction. Substituting sparse XY cannot by itself identify a better racing line or tyre model. Local comparisons at T1, T8 and T14 help distinguish a plausible path difference from a usable whole-lap predictor. The project retains the original calibrated centreline map and its original validation outcome. [Corner path investigation](bahrain_corner_paths.md) · [Deployment map](bahrain_deployment_zones.md)

Both model predictions were frozen before scoring a second Red Bull driver. Driver 22 laps 2, 5 and 13 provide a same-session transfer check. The original centreline missed sector two by 1.118–1.259 s on all three. The candidate missed by 4.292–4.433 s. [Transfer study](bahrain_driver_transfer.md) · [Paired figure](../figures/dissertation/bahrain-driver-transfer-v1/01_paired_transfer.pdf)

## Reproduction

From a clean evidence copy containing the original acquisition and calibrated centreline run, use `PYTHONPATH=src;scripts` and run `.venv/Scripts/python.exe scripts/test_bahrain_path_candidate.py`. It writes the new geometry, unchanged vehicle coefficients, a free-running prediction CSV and a hash lock before computing separate-lap scores. Output directories are versioned and an existing run is preserved. [Locked predictions for paired driver transfer](../results/bahrain-path-candidate-001/locked_predictions.json)
