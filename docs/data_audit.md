# FastF1 schedule audit

## Purpose and evidence boundary
The `audit-schedules` command catalogues candidate sessions before lap acquisition. It requests only schedules, including testing. It pins the FastF1 schedule backend so fallback does not silently change metadata semantics. Session support is stored as true, false or unknown. Neither support nor a scheduled date verifies telemetry availability. Future and cancelled sessions may remain in the catalogue. Season cohorts are provisional partitions, not certifications of compatible physics or circuit layouts.

## Manual execution in PowerShell
Open this project directory with Python 3.11+ available:

```powershell
py -3.12 -m venv .venv
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
& $python -m pip install -r requirements-data.txt
& $python -m pip freeze > environment-lock.txt
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
& $python -m unittest discover -s tests -v
& $python -m f1energy.cli audit-schedules --start 2025 --end 2025 --output results/schedules-pilot-001
```

Inspect `catalogue.json` and `manifest.json` before broadening the range:

```powershell
& $python -m f1energy.cli audit-schedules --start 2018 --end 2026 --output results/schedules-all-001
```

Use a new output directory each time. The manifest records the requested years, source-code hashes, FastF1 version and catalogue hash. Preserve environment-lock.txt alongside returned evidence. The local cache is under the run directory. Exit 0 means schedule enumeration completed; exit 1 means one or more season failures were retained; exit 2 means an invalid request or setup/file error. A schedule error does not establish that the season has no data. Empty schedules are failures, not successful zero coverage. No empirically measured runtime estimate is available yet; begin with one season and record elapsed time before expanding. This command does not train a model or request lap telemetry.

## Next evidence gate
Return the catalogue, manifest, environment lock and console output. Review session dates, technical eras, event identity and exact circuit layout. Then implement a separately bounded one-session telemetry audit, initially considering 2025 Bahrain qualifying. Record lap-quality exclusions and missing channels; freeze whole-event splits before fitting. Earlier than 2018 seasons may provide historical context but are outside this telemetry-oriented backend audit.

## Verification and limitations
Offline tests exercise session enumeration, unknown support, empty/error seasons, era boundaries and continuation after failure. The inherited fixture tests also pass. Live API compatibility and coverage have not been tested in this increment. Dependency bounds are an optional installation range, not a tested lock.

Interface checked against the official FastF1 events source on 27 October 2026:
https://github.com/theOehrly/Fast-F1/blob/master/fastf1/events.py
