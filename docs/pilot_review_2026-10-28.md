# Pilot evidence review — 28 October 2026

Authoritative project: C:/Users/fm.mm/Desktop/COM3001/COM3001. Reviewed existing JSON using this project's .venv Python. No source data or cache was changed.

## Integrity and scope

Both manifest output hashes match the current files: schedule catalogue SHA-256 `9f1d4d2d74d62eed95e7e0806b5d4a676d77ac2ed62d7a260852f81a6b64637a`; telemetry summary SHA-256 `423b38b5116df41b9614d2ad2b02c02bc48494fdaa1b38521937c70f81a8fbdf`. These checks establish agreement with the saved manifests, not independent source authenticity. Both manifests record FastF1 3.9.0 and package hashes, but commit is null.

The schedule run was created at 2026-10-28 00:26:41 UTC and requested 2018–2025 with testing included and the fastf1 backend. It contains 903 rows and zero season failures. Counts by season: 2018 105; 2019 105; 2020 93; 2021 115; 2022 120; 2023 115; 2024 125; 2025 125. The 2026 season was not requested.

Counts by recorded session name: Practice 1 181; Practice 2 162; Practice 3 156; Qualifying 173; Race 173; Sprint 24; Sprint Qualifying 12; Sprint Shootout 6; literal string `None` 16. The 16 placeholders must not count as real sessions. Removing that category leaves 887 candidate session rows, not 887 verified available telemetry sessions. Preserve the original catalogue and produce any corrected catalogue as a new version. Placeholder counts by season: 2020 4; 2021 2; 2022 4; 2023 2; 2024 2; 2025 2.

There are 40 Bahrain Grand Prix rows (five per season across eight seasons) and five separate Sakhir Grand Prix rows. Event identity must remain distinct pending layout verification. The 2025 Bahrain qualifying entry is round 4, session slot 4, scheduled 12 April 2025 16:00 UTC. Its support flag is true; telemetry remains not_checked and inclusion pending in this catalogue.

## Failed telemetry pilot

The telemetry manifest at 00:36:20 UTC requests 2025 round 4, Q, driver 1, at most three laps. Summary status is partial_failure, laps is empty and the recorded error is DataNotLoadedError at session_load_or_selection. This does not establish that the event lacks data. Cache filenames exist, but were not deserialised or treated as validated lap data. No deployment reconstruction, quality eligibility, lap-time comparison or trained model result follows from this pilot.

## Next gates

Correct sentinel session-name handling and test it; retain original evidence. Diagnose the loading/selection failure, then run a bounded retry in a new directory. Validate returned lap identities, channel units, sampling gaps and quality flags before broader collection. Freeze layouts, technical regimes and train/test roles before calibration. Synthetic simulator/controller verification may proceed independently, with its assumptions and outputs labelled explicitly.

AI contribution: local JSON inspection, SHA-256 recomputation, descriptive counts and this evidence review. No empirical causal or model-performance claim is made.
