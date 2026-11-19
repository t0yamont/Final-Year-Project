# Bahrain qualifying pace and the missing 15 seconds

The previous 107.057 s Sakhir result was the fastest schedule found on an assumed reference vehicle. Against the cached qualifying lap selected for diagnosis, it was 15.000 s slow. After calibrating effective cornering, braking and straight-line response on that lap, the free-running model traversed the circuit in **89.773 s** under a constant quarter deployment request. On the two other qualifying laps it was **1.530 and 1.246 s fast**. Both passed the lap and sector time criteria. The second missed the speed-profile criterion, so deployment recommendations from this model are conditional.

## What the timing comparison measures

The 2025 qualifying classification lists Oscar Piastri's 89.841 s pole lap and Oliver Bearman's 92.373 s Q1 time. Neither was a fitting target. The calibration uses one car, driver 1, in the cached Bahrain qualifying session. The acquisition screen admitted laps 4, 10 and 13. Lap 13 had already been used in earlier development work. Its 92.057 s flying lap was used for calibration. Laps 4 and 10 were reserved before the new fit as same-driver, same-session checks. These are three usable observations from one development event. Track clearance and surface condition are uncertain. [Official qualifying classification](https://www.formula1.com/en/results/2025/races/1257/bahrain/qualifying) · [Lap selection, data provenance and timing-line registration](bahrain_pace_inputs.md)

The timing line was located by matching position data from lap 13 to the circuit geometry, yielding a forward offset of approximately 40.65 m from the file origin and a 5.81 m RMS registration residual. The comparison uses fractional distance from this line. Each observed lap uses integrated native speed and timestamp information. The smoothed simulation path is 5,372.7 m. It remains an approximation to the racing line. A common 80.653 m/s rolling start and finish came from the average of the calibration lap's two line crossings. The held-out laps contributed neither the line position nor this speed. The model always generates its own speed and elapsed time during evaluation.

Replaying and then rotating the original 55-action schedule reproduced its archived 107.056747 s. Its time losses on lap 13 were **4.612, 7.230 and 3.158 s** by sector. Across the distance grid, speed RMSE was 13.24 m/s. The original model averaged 17.37 m/s below the real car in the portions where the brake signal was active. The corresponding shortfalls at full throttle were 8.24 m/s with DRS open and 6.75 m/s with DRS closed. Those values are pointwise speed discrepancies, not measured decelerations. [Original speed and cumulative time loss](../figures/dissertation/bahrain-pace-diagnosis-v1/01_historic_gap.pdf)

## What changed in the model

The existing event solver supplies the physical transition, finite battery, brake recovery and terminal constraints. The calibration permits lateral acceleration to increase with speed using the effective relation `a_lateral = a_base + beta × speed²`. An allowed cell speed must satisfy the curvature constraint throughout the cell. DRS availability for each of the 55 blocks is fixed by majority status on lap 13. Sixteen blocks receive reduced drag. The braking envelope is built backwards with the drag regime for each cell. Every controller uses the same line, regimes, friction law, 800 kg mass, 120 kW electrical limit, 2 MJ initial battery, 0.1 MJ reserve and regenerative budgets.

| Effective quantity | Earlier reference | Calibrated estimate |
|---|---:|---:|
| Lateral acceleration intercept (m/s²) | 20.00 | 31.13 |
| Speed-squared lateral coefficient (1/m) | 0 | 0.004697 |
| Friction braking deceleration (m/s²), before drag | 12.00 | 27.96 |
| Base wheel power (kW) | 450.0 | 370.6 |
| Closed-DRS drag coefficient in the force law (kg/m) | 1.000 | 0.450003 |
| Open-DRS drag multiplier | 1.000 | 0.825 |

The free-running fit used 221 equally spaced speed comparisons, the three official sector durations and weak parameter regularisation. The fixed quarter request (30 kW requested) gives a reproducible assumption for unobserved real deployment. The fast fitting calculation uses constant propulsive power and the geometric/braking envelopes; the reported results use exact event integration and finite electrical energy. The fit approximation differed from the primary exact replay by 0.247 s and 0.139 m/s speed RMS. The primary-to-refined event replay difference was 0.120 s, inside the 0.25 s numerical limit. Drag lies within 0.000003 kg/m of its lower estimation bound. Power, drag, lateral grip and unknown actual deployment are confounded. These values describe the effective model and cannot be read as engine or aerodynamic measurements for the car. [Frozen protocol](../configs/bahrain_pace_protocol.json) · [Fitted model and run data](../results/bahrain-pace-calibration-001/)

## Checks on separate laps

Positive signed errors indicate a slower simulated traversal. Sector endpoints use the fixed development-lap distance fractions. Their observed positions on the separate laps differ by up to about 2.6 m from those fractions.

| Driver 1 lap | Role | Measured lap (s) | Historical error (s) | Revised error (s) | Revised sector errors S1 / S2 / S3 (s) | Speed RMSE, historical → revised (m/s) |
|---|---|---:|---:|---:|---|---|
| 13 | Fit | 92.057 | +15.000 | −2.284 | −0.901 / −1.222 / −0.161 | 13.24 → 4.83 |
| 4 | Separate lap | 91.303 | +15.754 | −1.530 | −0.394 / −0.996 / −0.140 | 12.86 → 4.53 |
| 10 | Separate lap | 91.019 | +16.038 | −1.246 | −0.271 / −0.772 / −0.203 | 14.24 → 5.36 |

The predeclared limits were 2.0 s per lap, 1.0 s per sector and 5.0 m/s distance-weighted speed RMSE, plus numerical refinement and physical rolling-finish checks. Lap 4 passed all criteria, marginally in sector two. Lap 10 failed speed RMSE. Even the fit lap exceeded the lap and sector-two time thresholds because fitting minimised a compromise between the full speed profile, sector errors and parameter penalties. The fit was frozen before scoring the other laps and was retained after scoring. [Lap 4 figure](../figures/dissertation/bahrain-pace-calibration-v1/lap-4.pdf) · [Lap 10 figure](../figures/dissertation/bahrain-pace-calibration-v1/lap-10.pdf) · [Independent audit](../logs/agent_tools/2026-11-18/bahrain_pace_independent_audit.json)

## Which assumptions explain the change?

Subsequent checks used the known development lap's XY path and a separate three-lap cohort from driver 22. The XY substitution worsened the lap and all three driver-22 sector-two checks failed even for the original centreline. [Path comparison](bahrain_path_candidate.md) · [Driver-transfer results](bahrain_driver_transfer.md)

Separate replays kept the same timing line, quarter request and 80 cells per block and restored one group of old assumptions at a time. Relative to the calibrated 90.002 s traversal **on that grid**, restoring the old cornering limit added **12.767 s**, restoring old friction braking added **5.151 s**, and restoring both old base power and drag added **1.725 s**. Removing only the DRS drag reduction added **0.288 s**. Restoring all old physical limits together added **18.409 s**. These effects interact. The original-cornering, original-power/drag and no-DRS cases also missed finish speed; those figures describe traversals under changed physics and cannot be ranked as feasible deployment policies. Mass stayed fixed throughout. This isolates why the simulator changed pace without assigning a measured number of seconds to any real car component. [Mechanism experiment](../results/bahrain-pace-mechanisms-001/) · [Parameter and corner figure](../figures/dissertation/bahrain-pace-mechanisms-v1/pace_mechanisms.pdf)

Matching total time still leaves location-specific discrepancies. In an 80 m window either side of each approximate turn marker on lap 13, turn 1's minimum was 67.0 km/h observed and 67.8 km/h simulated. At turn 8 it was 70.0 versus 93.6 km/h, and at turn 14 it was 120.0 versus 91.7 km/h. Opposing errors can cancel in a sector total. The accompanying corner checks also record the first braking sample within the 250 m approach window and speed 100 m beyond each marker. Turn locations have roughly 50 m display tolerance and those distances are relative to annotations. These particular corner exits are important qualifications on the [deployment map](bahrain_deployment_zones.md). [Turn provenance](bahrain_turn_landmarks.md) · [Corner diagnostics](../results/bahrain-pace-mechanisms-001/corner_checks.json)

The first 295 m received electrical assist in every grip/grid comparison and had 1.12 and 0.66 m/s local speed RMSE on laps 4 and 10. Near T10, the same test gives 8.08 and 9.94 m/s. These descriptive errors come from the frozen quarter-request replay. They indicate how well the local motion is represented and leave true electrical deployment unknown. [Zone-level errors and delivered work](../results/bahrain-zone-support-001/metrics.json) · [Motion overlay](../figures/dissertation/bahrain-zone-support-v1/zone_motion_support.pdf)

The historical replay and the fit use the two modes of [the calibration script](../scripts/calibrate_bahrain_pace.py). Run the historical mode first with `--diagnose` and pass separate `--output` and `--figures` directories for each stage. The fit reads the historical profile under `results/bahrain-pace-diagnosis-001`. The checked-in [physics diagnostics](../scripts/diagnose_bahrain_parameters.py), [independent pace audit](../scripts/audit_bahrain_pace.py) and [zone overlay](../scripts/assess_bahrain_zone_support.py) consume the corresponding archived runs. The reproducible data selection is documented with the [qualifying inputs](bahrain_pace_inputs.md).
