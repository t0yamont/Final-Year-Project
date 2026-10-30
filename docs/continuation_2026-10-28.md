# Guide-aligned continuation — 28 October 2026

Authoritative working folder: C:/Users/fm.mm/Desktop/COM3001/COM3001.
Guide read: C:/Users/fm.mm/Desktop/F1_COM3001_Step_by_Step_Guide.md. Embedded task prompts are planning context. The user's multi-season requirement and manual ownership of heavy computation remain in effect.

## Evidence review (Step 05)
The schedule manifest reports FastF1 3.9.0, 2018–2025 and 903 rows. A specialist review identified 16 literal None session placeholders: 887 named-session candidates remain. The original files are preserved; the parser now excludes these placeholders on future runs. This is schedule coverage, not verified telemetry coverage.

The qualifying pilot returned DataNotLoadedError and exported no laps. A cache-only replay reproduced the failure: session info, driver info and session status responses were absent, while car and position cache files existed. Three small direct metadata requests (SessionInfo.jsonStream, DriverList.jsonStream, SessionStatus.jsonStream) each returned HTTP 401 with empty bodies. This establishes an access failure from this environment at the time of inspection; it does not establish its cause, permanent source unavailability, or a need to buy access. No authentication bypass or bulk retry was attempted. Future session pilots capture FastF1 logging in fastf1.log to retain earlier causes rather than only the terminal exception.

## Physics work (Step 08)
The braking-envelope module propagates downstream speed caps backwards using constant net deceleration and stopping-distance constraints. It is an open-path feasibility upper bound, not an action-responsive full lap, and has no acceleration or closed-lap feasibility guarantee. The interrupted specialist left implementation and tests; the coordinator reviewed them and changed an exact floating-point equality to a numerical tolerance. Full lap integration and independent calibration remain pending.

## Current guide map
- Steps 01 and 04: research scope, evidence register and runnable foundation exist; administrative inputs remain pending.
- Steps 02 and 03: literature and educational work are partial, requiring continued primary-source review.
- Step 05: schedule catalogue exists; telemetry acquisition is blocked by observed HTTP 401 responses.
- Steps 06 and 07: usable-lap selection, split freeze and track profiles await real telemetry.
- Step 08: analytic motion, drag and braking prototypes tested; full-lap integration remains open.
- Steps 09–14: reconstruction, physical baselines, Gymnasium, PPO and empirical evaluation remain planned.
- Steps 15–18: ethics, reporting, AI transparency and reproducibility records stay active; final submission claims are premature.

## Next work
Investigate supported metadata access using the installed FastF1 documentation/source and current provider requirements before another session download. Retain the failed run. In parallel, integrate braking with forward dynamics on a synthetic track and test numerical convergence before physical controller comparisons. Training is premature until those gates pass.

## Verification and AI record
The local environment ran 28 tests successfully after the rounding correction. Offline tests establish code checks under assumptions; they do not validate live access or real F1 energy deployment. Codex read the guide, inspected evidence, diagnosed access responses, changed parser/logging, reviewed the braking increment and documented limitations. Two agents hit a usage limit; coordinator completed the bounded increment directly. No training or large acquisition run occurred.
