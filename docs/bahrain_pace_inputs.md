# Bahrain qualifying pace inputs

The input run uses OpenF1 Bahrain 2025 qualifying (meeting 1257, session 10010), driver 1 only. From 17 lap records, the unchanged acquisition screen admitted laps 4, 10 and 13. The split was written before examining their traces. Lap 13 was reserved for calibration because the bounded inverse study had already used it. Laps 4 and 10 are holdouts for this pace fit within a previously studied development event. The input preparation did not access the final qualifying-test events.

| Use | Lap | Official lap (s) | Official sectors (s) | Integrated speed distance (m) | Native interior car samples | Max native car gap (s) |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| Calibration | 13 | 92.057 | 29.628 / 39.514 / 22.915 | 5,363.03 | 344 | 0.920 |
| Local holdout | 4 | 91.303 | 29.121 / 39.288 / 22.894 | 5,365.71 | 338 | 0.839 |
| Local holdout | 10 | 91.019 | 28.998 / 39.064 / 22.957 | 5,365.56 | 340 | 0.920 |

The session meteorology reported no rain at sampled times. All three laps had assigned soft-tyre stints, with source stint ages at start of 2, 0 and 0 laps respectively. Track temperature at the matched start sample was 30.6, 31.1 and 30.9 °C. The clearance, pit and validity histories are incomplete. Surface conditions, traffic, fuel and setup remain unverified. The full 17-lap acquisition screen and exclusion reasons are recorded in `metrics.json`.

## Timing line and sectors

The estimated timing line lies 0.00752025 of the original Sakhir centreline length after the source origin in the forward direction (40.65 m on the raw geometry). The registration used only lap 13's XY telemetry, with the provider's start/end timestamps and linearly interpolated positions at both edges. Observed open-path and closed reference arclengths were normalized separately. A circular phase search matched 512 equally spaced arclength points after allowing a common scale, rotation and translation. Forward and reverse traversal were tested with and without reflection.

The forward rotation fit had 5.81 m RMS residual, 10.20 m at the 95th percentile and 12.17 m maximum. The closest alternative had 163.16 m RMS residual. The fitted scale was 1.0040 reference metres per nominal OpenF1 metre. Projecting the transformed start and end positions directly onto the centreline yielded fractions 0.006836 and 0.007019, about 3–4 m upstream of the all-track estimate. The observed start/end XY closure error was 1.01 m. The location trace had 342 native interior samples and a 1.140 s maximum gap. These checks support the track layout, direction and approximate phase. Differences between the racing line and public centreline, location sampling and the approximate lap timestamps still affect per-position comparisons.

The lap 13 edge speeds were 82.026 and 79.280 m/s. Their mean of 80.653 m/s is the single periodic rolling-line speed supplied to the simulation. Official sector durations come from the original provider lap response. The calibration sector distance fractions are 0, 0.329881, 0.737310 and 1, obtained by integrating the speed trace to the official cumulative sector times. The model uses these inferred positions for sector timing. Holdout sector times can be compared with those same model positions. Each holdout's integrated sector distances are available as diagnostics.

## Reproduction and use

`split.json` fixes the fit and holdout identifiers. `metrics.json` records source paths, SHA-256 digests, edge brackets, sector positions, registration transform, and screening exclusions. The preparer verifies the acquisition outputs against the completion record and replays driver 1's raw laps, car and location responses through the offline OpenF1 cache. It checks those bytes against the acquisition receipts and checks that the raw lap records equal the embedded acquisition lap records.

Each CSV uses `fraction,time_s,speed_mps,brake,throttle,drs`. Fraction is the trapezoidal integral of native speed divided by that lap's total integral. The two endpoint speeds come from linearly interpolating the native samples bracketing the provider timing bounds. Brake is 0/1, throttle is percent and DRS is the provider's raw state code. Controls stay at their latest native values at interpolated endpoints. Native car selection uses the frozen lap's timestamp bounds, which can retain a sample the original acquisition considered ambiguous between adjacent intervals. The acquisition eligibility decision still governs lap selection. Sector boundaries are integrated within the local piecewise-linear speed interval.

Run from the repository root using the existing Python environment and local cache.

```powershell
$env:PYTHONPATH = 'src'
.venv/Scripts/python.exe scripts/prepare_bahrain_pace.py
```
