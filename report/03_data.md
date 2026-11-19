# Data and modelling assumptions

## From eight race weekends to one deployment circuit

The acquisition included standard practice, qualifying and race sessions from eight 2025 Formula One weekends. The study followed the two team entries selected by the frozen acquisition rule and retained driver identities when substitutions occurred. Car-channel data included speed, throttle, brake, gear, engine speed and drag reduction system (DRS) state. Position data were collected for qualifying. Weather, tyre stint, pit and race-control information supported screening. The data source and field definitions were recorded alongside the requests. [Acquisition protocol](../docs/openf1_implementation.md) · [OpenF1 documentation](https://openf1.org/)

| Event role | Weekends | Sessions | Lap records | Screened motion candidates |
|---|---:|---:|---:|---:|
| Development | 4 | 20 | 1,078 | 318 |
| Validation | 2 | 10 | 565 | 124 |
| Final evaluation | 2 | 8 | 458 | 101 |
| Total | 8 | 38 | 2,101 | 543 |

The table counts lap records across all acquired sessions and both driver entries. The archive contains 1,054,001 native car-channel rows. Hundreds of rows from a lap describe one continuous trajectory and share conditions. A candidate passed the stated screening criteria for a particular analysis. Unknown traffic, fuel, setup and incomplete flag histories still limit what can be inferred from it. [Session-level coverage counts](../results/openf1-dataset-003/coverage.json)

The project assigned whole events to roles before modelling. Bahrain, Spain, Monza and Japan supplied development data. The United Kingdom and Hungary supplied validation data. Belgium and Abu Dhabi were reserved for final evaluation of the acceleration predictor. Under that study's driver, qualifying and quality rules, Belgium contributed zero eligible laps and Abu Dhabi contributed three. Of 516 primary Abu Dhabi windows, 515 had a DRS condition supported by the development fit. Reporting both event and lap counts makes the scope of that final result clear. [Final qualifying evaluation](../docs/session_mix_study.md)

## Bahrain timing and position

Bahrain supplied the geometry and qualifying motion used for the deployment model. Driver 1's lap 13, timed at 92.057 s, furnished the calibration trace. Laps 4 and 10 of the same driver were reserved for separate-lap checks before fitting. A subsequent comparison used all three eligible qualifying laps of the second team driver, numbered 2, 5 and 13. The two candidate predictions for that comparison were frozen before opening the second driver's measurements for scoring. All six observations came from the same qualifying session. They test local pace and within-session transfer. They provide little evidence about deployment at another circuit or in another season. [Lap selection](../docs/bahrain_pace_inputs.md) · [Driver-transfer protocol](../configs/bahrain_driver_transfer_protocol.json)

The public centreline had its own coordinate origin. Driver 1's development-lap positions located the timing line approximately 40.65 m along the source geometry. Model distances are measured forward from that registered line on a 5,372.7 m smoothed path. Approximate turn labels have about 50 m display tolerance. Distances and turn names together are more informative than an apparent switch point at a single precisely named apex. [Timing-line alignment](../docs/bahrain_pace_inputs.md) · [Corner landmark provenance](../docs/bahrain_turn_landmarks.md)

## Parameters and measured quantities

The model used an assumed vehicle mass of 800 kg. The calibrated power and drag describe effective straight-line behaviour conditional on the assumed electrical assistance during the development lap. Drag approached the lower boundary of its fitted range. Treating the fitted coefficients as measurements of the actual engine or aerodynamics would obscure this dependence. The centreline, curvature and speed envelope similarly describe an approximation to the driven path. [Pace calibration](../docs/bahrain_qualifying_pace.md)

Wheel power is the rate at which the electric machine helps propel the car in the simulation. Wheel work is that power accumulated over time. Battery discharge is larger than the delivered wheel work because the model assumes 90% conversion efficiency. During required braking, up to 40% of the braking force is eligible for recovery, subject to the motor and energy limits, and 80% of the recovered mechanical work reaches the battery. Each central-model policy starts with 2 MJ stored, must retain at least 0.1 MJ and must meet the common rolling finish speed. The 120 kW machine ceiling, 2 MJ recovery and 4 MJ discharge bounds represent the stated 2025-era energy-transfer limits. Public telemetry supplies no measured state of charge or MGU-K wheel work for validating those trajectories. [Vehicle assumptions and regulatory sources](../docs/regeneration_study.md)
