# Development calibration data plan — 28 October 2026

## Fixed development roles
configs/development_split.json assigns driver 1 Bahrain 2025 qualifying laps 4 and 10 to fitting, lap 13 to within-event validation, and excludes lap 16 from primary fitting/validation because its source trace contains two gaps above one second. This is not an event-independent or final test. The event was inspected before this split. The separate final event split remains unfrozen. Never describe lap 13 as an untouched final test.

## Selection and units
The script joins clean-lap metadata and enriched context by unique lap number after checking the context session identity against year, round, session code and driver. Candidates must pass the original accurate/nonpit/clear-track selector, have FastF1 Deleted=False after race-control parsing, and have no rain reported at in-lap weather sample times. This does not prove dry track or independently validate steward decisions.

For each selected lap, preserve original row order and consider only adjacent sample pairs. Require positive dt no greater than 0.5 seconds, throttle at least 95 percent at both endpoints, brake False at both endpoints, stable gear, stable DRS code, finite channels, and positive speed difference. These are declared development heuristics, not validated universal quality thresholds. No smoothing, interpolation, sorting or bridging missing samples is performed. There is no steering input or geometry test: acceleration windows are not verified straights. Corner exits can remain.

Speed is converted from source km/h to m/s by division by 3.6. Time strings are parsed to seconds. Acceleration is the adjacent speed difference divided by dt, in m/s^2, assigned the midpoint speed. Quantised speed and variable sampling amplify derivative noise; adjacent pairs share observations and are not independent replicates. Positive-acceleration filtering induces conditional selection bias. Stable DRS codes are preserved for stratification, not interpreted as identical aerodynamic settings across cars or sessions.

## Executed outputs
results/calibration-data-001 contains fit.csv (287 pairs: 137 from lap 4 and 150 from lap 10), validation.csv (144 pairs from lap 13), summary.json with every exclusion denominator and first-reason counts, and manifest.json with split/config/source/export hashes. Existing output directories are rejected. Three independent fixtures verify SI differentiation, gap/missing-value nonbridging and unsorted-time rejection.

No full speed envelope was constructed or supplied to a simulator. No parameters were fitted in this step. The identification agent may use fit.csv to estimate descriptive acceleration behaviour and validation.csv to assess within-event discrepancy, but must not infer verified electrical deployment, drag, mass or engine power from confounded public traces alone. Selection thresholds were chosen during development; any tuning based on validation must be disclosed.

## Reproduce
Run `.venv/Scripts/python.exe scripts/prepare_calibration_data.py --output results/calibration-data-002` from the project folder. Inputs are the preserved clean-laps-001 and lap-context-001 exports. No API request or training occurs. Review and retain the complete manifest with any later parameter-fit outputs.
