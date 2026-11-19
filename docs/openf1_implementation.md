# OpenF1 implementation and acquisition — 10 November 2026

## Modelling preparation completed — 11 November 2026

results/openf1-motion-001 contains46,051 development windows and15,501 validation windows from318/124 candidate lap groups; each retains event/session/driver/lap labels. Adjacent rows are dependent. Final test modelling inputs were not prepared. Coverage plot PNG/PDF saved and visually inspected at figures/dissertation/openf1-coverage-v1.

results/circuit-input-assessment-001 contains21 separate driver1 development event/session/DRS fits using chronological last-lap-group holdouts. Effective power/drag beats a constant-acceleration baseline in20/21 contexts; no parameter boundary hits. These are observed-speed-conditioned acceleration diagnostics, not full-lap predictions. Assumed mass800kg; electrical power remains unobserved. Independent RMSE recalculation and input/output hashes verified. Figure pair at figures/dissertation/circuit-inputs-v1 was inspected.

Candidate TUM Sakhir centreline downloaded with source licence:1082 points,5405.749m closed length,0.1155% below official5412m. Basic geometry checks pass. Full layout/curvature, speed-envelope, lap-boundary and forward-simulator validation remain next. See docs/model_preparation_2026-11-11.md. Do not rerun the completed acquisition or model-table generation unnecessarily.


## Verified acquisition completion — 11 November 2026

Run results/openf1-dataset-003 completed all38 planned standard sessions across8 weekends, with zero recorded invocation failures and no pending sessions. It contains2,101 lap entries,1,054,001 native car samples and543 conditional motion candidates. All per-session output hashes were checked. The acquisition process has finished. Earlier run002 retains its three failures; run003 recovered them using cached responses and explicit empty-window handling. Do not restart acquisition unnecessarily.

102 automated tests pass. scripts/prepare_openf1_motion.py and scripts/plot_openf1_dataset.py are implemented but their full-cohort outputs have not yet been generated. Next: prepare grouped development/validation model inputs and coverage figures, then empirical motion modelling/full-circuit validation. Test telemetry has been acquired and quality-screened only; no model performance evaluated. These data are not verified battery/deployment labels.


## Contract

The dataset plan is configs/openf1_dataset_plan.json. Source catalogue and plan hashes bind every run. Roles are frozen by meeting ID across all providers, sessions and drivers: development Bahrain/Spain/Monza/Japan, validation UK/Hungary, test Belgium/Abu Dhabi. Standard sessions only in the initial cohort; sprint sessions remain explicit excluded cells. Both entries of driver 1's team are selected per session from source metadata; substitutions retain their real identities. When driver 1 is absent, the predeclared Red Bull Racing identity selects that session's actual entries; primary-driver presence is recorded. Missing team entries fail selection rather than silently borrowing another team.

Acquisition may inspect schema, gaps and context for every role, but calibration and profile extraction must select development explicitly. Test model performance remains untouched. No battery/deployment labels are invented. Preserve native timestamps and distinguish missing, invalid, excluded and candidate records. A screened motion candidate is not a verified clean/dry F1 lap.

## Execution design

One reusable client supports hash-checked caches and offline replay, bounded request timeouts/retries and at least 2.1 seconds between network requests. Queries use `date>` and `date<`. Acquisition runs save their frozen plan/catalogue, implementation hashes, per-session/driver files and manifests. Resume verifies source and output hashes before skipping completed units. Failed units remain recorded and can be retried using cached successful responses. New scientific configurations require new run folders.

Car requests use bounded 15-minute windows, preserving original values. Native position is acquired for qualifying in this cohort; practice/race profiles use car channels. Weather matches cannot use future observations or values older than120 seconds. Stints use declared lap ranges; ambiguous assignments remain unknown. Race-control and pit data are preserved alongside alignment flags. These are engineering safeguards, not proof of physical car identification.

Out-lap metadata are retained but excluded from sample alignment: some source out-lap durations include garage time and would otherwise obscure later timed laps. Ambiguous samples in overlapping timed-lap intervals are excluded, with overlaps up to0.5 seconds permitted under the frozen approximation policy; larger overlaps fail QC. Conditional whole-lap screening requires internal and boundary sample gaps at most1 second, suitable tyre/weather evidence and no reported pit/deletion/caution exclusion. Unknown full flag history, traffic, fuel and setup remain declared limitations. Timing-sector colour2048 is not treated as a race-control yellow flag.

## Commands

Run from the authoritative project root in PowerShell. Fresh studies require fresh output directories. Existing acquisition runs accept `--resume` only if implementation, plan, catalogue and Python versions match their saved contract.

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
# Bounded first development session:
.\.venv\Scripts\python.exe scripts/acquire_openf1_dataset.py --output results/openf1-new-run --session 9967 --max-minutes 10 --max-requests 100
# Continue the same unchanged implementation over the complete frame:
.\.venv\Scripts\python.exe scripts/acquire_openf1_dataset.py --output results/openf1-new-run --resume --max-minutes 45 --max-requests 800
# Verify completed-session resume without network:
.\.venv\Scripts\python.exe scripts/acquire_openf1_dataset.py --output results/openf1-new-run --resume --offline --session 9967
# Prepare grouped model inputs; test role is deliberately unavailable:
.\.venv\Scripts\python.exe scripts/prepare_openf1_motion.py --input results/openf1-new-run --output results/openf1-motion-new --roles development validation
.\.venv\Scripts\python.exe scripts/plot_openf1_dataset.py --input results/openf1-new-run --output figures/dissertation/openf1-new-coverage
```

The motion-preparation step uses adjacent observations only: maximum pair gap0.5 seconds, throttle at least95%, no reported braking, unchanged gear/DRS and positive speed. It retains zero and negative acceleration to avoid the historical positive-acceleration selection bias. Each row retains event/session/driver/lap identity. These are conditional motion proxies; adjacent rows are dependent and full throttle does not prove straight-line driving. Keep per-context fits or justify pooling. Historical fit datasets are unchanged.

## Progress

The previous access audit succeeded on four lap windows and five context endpoints (source-access-audit-20261110-003). The reusable adapter and first complete Spain qualifying session have now been exercised. Two integration bugs were corrected with regression tests: garage-time out-laps masking later laps, and sector colours mistaken for race-control flags. Pilot001 remains preserved; corrected002 was reconstructed from cache and used for broad acquisition. Full acquisition outcomes will be recorded after the batch and empty-window recovery finish.
