# Data acquisition increment

## Actions
Added telemetry_audit.py, an optional FastF1 adapter for one explicitly selected season, race round, session code and numeric driver. It preserves all selected-driver lap metadata, exports at most three chronological laps of source car data, reports channel missingness and conservative quality flags, and saves summary and SHA-256 provenance manifests. Existing output directories are rejected. Per-lap and session-level failures remain in the evidence.

## Discoveries and claim limits
A chronological pilot includes in/out laps deliberately to expose quality issues; it is not the modelling dataset selection rule. Source car data can contain upstream processing and is not guaranteed raw sensor measurement. Electrical deployment and battery state remain unavailable labels in this pipeline. Weather is not loaded, so dry-lap eligibility is not established. Sampling-gap analysis and track-position export remain future work.

FastF1 session.load(telemetry=True) may download a full session's telemetry before lap slicing. The three-lap limit bounds exported analysis only, not downloaded bytes or runtime. This pilot therefore remains a manual task. No network download or training was performed by this agent. Current FastF1 API compatibility remains a live-test requirement; installed versions must be frozen for reproducibility.

## Verification
Three offline tests pass: missing channels/NaN and false brake handling; conservative unknown quality and pit flags; request bounds validated before optional imports or network. These do not establish actual session coverage or successful live export.

## Integration contract
Expose audit-session in the existing CLI and call run_session_audit(year, round_number, session_name, driver, output, max_laps=3). The function returns status completed or partial_failure, matching the current CLI exit convention. It raises ValueError for invalid requests/missing FastF1 and FileExistsError for existing destinations. Normal race rounds only; testing retrieval needs its own explicit adapter.

## Next evidence
Run the schedule pilot first. Resolve an exact event round and driver from that evidence, then execute this session pilot manually. Return summary.json, manifest.json, driver_laps.csv, exported car CSVs and the frozen environment. Inspect missingness and failure denominators before expanding acquisition. No inferred energy-map claim is justified by this increment.
