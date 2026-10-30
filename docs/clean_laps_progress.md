# Candidate lap audit — 28 October 2026

## Action and method
Implemented f1energy.clean_laps and ran it against a copy of the completed Bahrain 2025 qualifying driver-1 pilot cache. FastF1 offline mode was enabled for loading. Original pilot results were preserved. Results are at results/clean-laps-001 with SHA-256 output manifest. Three offline tests passed for missing quality, pit/deleted exclusions, and time ordering/gaps. No new network download occurred.

The selector requires confirmed IsAccurate, no pit-in/out timestamp and clear TrackStatus. Known deleted laps are excluded. Unknown deletion and weather are retained as unresolved flags; every lap remains modelling_eligible=false. This is a development pilot under configs/data_roles.json, not an untouched test event. No final event split is frozen.

## Observations
Seventeen driver laps were inspected. Four candidates were exported, without smoothing, sorting source samples, resampling or interpolation:

| Lap | Lap time (s) | Samples | Median positive gap (s) | Maximum gap (s) | Gaps above 1 s |
|---|---:|---:|---:|---:|---:|
| 4 | 91.303 | 337 | 0.240 | 0.840 | 0 |
| 10 | 91.019 | 340 | 0.240 | 0.920 | 0 |
| 13 | 92.057 | 344 | 0.240 | 0.920 | 0 |
| 16 | 90.423 | 326 | 0.240 | 1.240 | 2 |

All four had zero missing Time values and zero nonincreasing time steps. The one-second diagnostic threshold is not a validated eligibility cutoff. All four retain weather_not_checked and deletion_unknown. Source sample spans are shorter than full lap durations because no boundary interpolation was added; export duration must not be treated as a complete lap-time integral.

## Meaning and limits
The completed run establishes that the copied cached source can produce candidate car traces. It does not verify electrical power, battery state, track geometry, dry conditions, lap deletion status or calibrated physics. FastF1 source processing may already have occurred. CSV speed is km/h; time fields are timedeltas, brake is boolean, DRS is a code. Units are recorded in summary.json. Modelling code must explicitly convert to SI units. Source gaps, particularly lap 16, need a declared handling rule before fitting.

## Reproduction
From the project folder, set PYTHONPATH to src and run the module with a new output directory:

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m f1energy.clean_laps --source-run results/bahrain-2025-q-driver1-002 --output results/clean-laps-002
```

The command copies the source cache and uses offline mode. It rejects an existing output directory. Next work is a separately logged metadata enrichment for weather/race-control messages, then explicit selection and preprocessing policy, while keeping this event in development only.

## Bounded context enrichment — 28 October 2026
Added f1energy.lap_context and completed results/lap-context-001. The run copied pilot002's cache, loaded existing timing metadata, and fetched only weather and race-control messages for the same session; telemetry=False. Original pilot and clean-laps-001 remain unchanged. Raw context tables, driver lap metadata, log, summary and hashed manifest are saved.

Weather Time was aligned directly to each lap's inclusive [LapStartTime, Time] interval; all are session-relative timedeltas. No nearest sample was substituted for an empty interval. Candidate laps 4, 10 and 13 each contain two weather samples; lap 16 contains one. Every such sample reports Rainfall=False. This supports only no rain reported at those sample times, not proof of a dry track throughout a lap. Air temperature spans 26.3–26.5 C across those samples; track temperature spans 30.4–31.2 C.

FastF1's parser marks all four candidate laps Deleted=False after processing the retrieved race-control messages. This resolves the earlier unknown flag at the library/source level, not through independent steward-record verification. Original unknown flags in clean-laps-001 intentionally remain intact as historical evidence; downstream consumers should join the new context by session, driver and lap number and retain the two manifests. All data remain development-pilot data. Sampling gaps and boundary coverage issues identified earlier still apply.

The single live context run completed with 17 aligned lap records and no recorded failures. Source code was exercised by this run; an independent automated alignment fixture is still desirable before using the method across events.
