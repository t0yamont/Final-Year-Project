# Session-mix ablation — 18 November 2026

Adding practice observations improves conditional qualifying acceleration prediction in the two validation events, including every declared matched-volume seed and the shorter-gap sensitivity. Adding available race observations provides no robust additional benefit. These are descriptive validation findings, not final-test evidence or real electrical-deployment identification.

## Qualifying result for RQ3

Mean qualifying lap/DRS-group acceleration RMSE (m/s²); lower is better. Q means qualifying development observations, P practice, R race. Matched pools contain exactly the qualifying observation count separately within each development event/DRS, with ranges across seeds 0–4.

| Validation event | Q | Q+P | Q+P+R | Q+P matched | Q+P+R matched |
|---|---:|---:|---:|---:|---:|
| Hungary, primary | 2.2204 | 2.0506 | 2.0619 | 2.0247–2.1597 | 2.0353–2.1715 |
| UK, primary | 1.8770 | 1.8504 | 1.8696 | 1.8317–1.8648 | 1.8289–1.8724 |
| Hungary, pair gap ≤0.3 s | 2.3971 | 2.2417 | 2.2591 | 2.2513–2.3010 | 2.2693–2.3249 |
| UK, pair gap ≤0.3 s | 1.9697 | 1.9570 | 1.9802 | 1.9246–1.9509 | 1.9412–1.9789 |

Primary qualifying evaluation includes 519 Hungarian and 550 UK windows; the shorter-gap filter leaves 381/377. The ≥30 m/s sensitivity retains all the eligible development and validation windows, so it reproduces the primary result and adds no distinct robustness evidence. UK qualifying Q+P+R becomes worse than Q under the shorter-gap filter; several matched Q+P+R seeds also lose. The broad all-session acceptance flag must therefore not be interpreted as acceptance of a robust qualifying Q+P+R advantage. Qualifying-only results are a separately reported, descriptive subset of the frozen per-session reporting, not a retroactively substituted primary acceptance criterion.

## Frozen method

`configs/session_mix_protocol.json` was written before fitting, SHA256 `de791867834170c5dae9026a7e4ddc1ebe218f8ec908ebbeccc58478afffc1b6`. The 800 kg mass assumption, existing effective-model bounds, filters, five arms, five seeds, exact-DRS transfer, group weighting, sensitivities and validation-only protection were fixed there. The study reuses `f1energy.identification.fit_effective` unchanged: bounded least squares of `m*v*a=P-k*v³`, with total effective power 0.1–1.2 MW and drag 0–3 kg/m. The target is signed finite-difference acceleration at supplied observed speed. These coefficients cannot separate combustion/electrical power or identify battery state.

Prepared tables from `results/openf1-motion-001` retain existing conditional lap candidates: throttle ≥95%, no brake, unchanged known gear/DRS, positive speed and pair gap ≤0.5 s. No interpolation, additional downloads, neural training or physics changes were needed. Development event/DRS fits remain separate. Pooling session types within an event is the explicit intervention; cross-event prediction takes the median of same-DRS models without fitting validation data. All arms evaluate exactly the same included validation windows. Equal-weight RMSE is computed within event/session/driver/lap/DRS groups and then averaged across groups within each event. The matched design controls window volume, but not speed distribution, unique laps, fuel, setup or observed operating conditions; it cannot identify a causal effect of session type.

Only driver 1 is studied. Qualifying support ≥30 windows and two laps per exact DRS leaves Bahrain and Monza, DRS codes 8 and 12: 864 qualifying windows across five unique session/lap combinations. Spain has only one qualifying candidate lap and Japan no qualifying candidate rows. Monza race observations have DRS 0, absent from its qualifying support, so its Q+P+R models equal Q+P. Added race information comes only from Bahrain's matching DRS contexts. This materially limits conclusions about race data; none of the 300 fitted model records hit coefficient bounds.

## Supporting all-session diagnostics

Primary all-session group RMSE is Hungary 3.0171/2.8600/2.8600 and UK 1.9734/1.8662/1.8835 for Q/Q+P/Q+P+R. All five matched Q+P+R seeds improve over Q in both events under every frozen filter, satisfying the protocol's descriptive **all-session** criterion. This is not a qualifying-wide or statistically significant result.

There are 5,081 unique included primary windows, 80 lap/DRS groups: Hungary 2,307/53 and UK 2,774/27. The table has 69,060 prediction rows because the same source observations recur across seeds and filters; these are not independent new samples. Most race windows use DRS codes absent from qualifying training. Only 493 Hungarian and 31 UK race windows remain eligible. Unmatched observations are recorded in `metrics.json`. Primary extrapolation outside the intersection of source speed ranges is 18.64%/21.23% for Q and 15.00%/16.87% for Q+P+R in Hungary/UK. Dependent windows, finite-difference noise, conditional lap quality, two events and unobserved vehicle context limit interpretation.

## Coverage decision before final scoring

Only acquisition `complete.json` metadata were inspected for protected events. Belgium qualifying session 9935 records **zero conditional-motion candidates for both drivers**, although driver 1 has nine motion-QC-pass laps. Abu Dhabi qualifying 9835 has three driver-1 conditional candidates. These counts are different quality stages; passing native motion QC alone does not authorise treating laps as clean conditional candidates.

The metadata ruled out a two-event final score under the existing quality rules. At that stage, only the acquisition counts had been inspected. The follow-on protocol retained Belgium in the denominator and froze the one-event scoring procedure before opening detailed Abu Dhabi rows. [Initial coverage decision](../logs/agent_tools/2026-11-18/session_mix_coverage_decision.json) · [Final scoring protocol and development-model hashes](../configs/session_mix_final.json)

## Held-out qualifying result

The one-look evaluation used driver 1, the saved development coefficients, all five sampling seeds, unchanged eligibility, exact DRS matching and the validation study's lap/DRS-group weighting. The prediction target was signed acceleration conditional on observed midpoint speed. Abu Dhabi contributed three laps and six lap/DRS groups. Of 516 primary windows, 515 had development support. One window had unsupported DRS code 14. Belgium contributed zero eligible laps and has no error score. No alternative driver, thresholds or events were introduced.

| Abu Dhabi filter | Retained windows | Q | Q+P | Q+P+R | Q+P matched range | Q+P+R matched range |
|---|---:|---:|---:|---:|---:|---:|
| Primary | 515 | 1.8081 | 1.7638 | 1.7695 | 1.7638–1.7846 | 1.7685–1.7849 |
| Gap ≤0.3 s | 365 | 1.9649 | 1.9383 | 1.9456 | 1.9213–1.9432 | 1.9256–1.9676 |
| Speed ≥30 m/s | 515 | 1.8081 | 1.7638 | 1.7695 | 1.7638–1.7846 | 1.7685–1.7849 |

All values are mean group RMSE in m/s². The qualifying-only constant-acceleration reference scored 3.0984 on primary windows. Adding practice reduced primary error by 0.0443 m/s² (2.45%). All five volume-matched practice draws improved on qualifying alone under every filter. Adding race rows increased full-volume error relative to Q+P in both distinct window selections. Only two of five matched race additions beat matched Q+P on the primary windows and one of five on the shorter-gap windows. The ≥30 m/s filter retained the same primary windows. The practice finding transfers to this one covered event. The study provides limited evidence about the incremental value of race sessions or transfer across circuits.

The independent arithmetic check recomputed 41,850 forecasts and 90 event/filter/seed/arm scores from saved rows and verified 17 hashes. Repeated windows across seeds and filters do not increase the number of independent laps. This scoring consumes the qualifying holdout for this question. Any later choices informed by these results must be described accordingly. [Final run and scored rows](../results/session-mix-final-001/) · [Forecast verification](../logs/agent_tools/2026-11-18/session_mix_final_verification.json) · [Final qualifying comparison](../figures/dissertation/session-mix-final-v1/qualifying_holdout.pdf)

## Artifacts and verification

Current study: `results/session-mix-validation-002`. It contains contract, coverage, fitted coefficients and selected source row identities, full predictions, group metrics, exclusions and input/source/output hashes. Run001 preserves an initial support-guard failure; an implementation-only requirement for Q/P/R in every source context was removed to match the frozen available-row arm definition before saving any evaluated results. The protocol did not change.

Independent saved-coefficient arithmetic checked 345,300 conditional predictions (maximum discrepancy 3.56e-15 m/s²), 1,200 group records, all event/session macro values, matched row volume, development-only fitting and 15 manifest hashes. Verification: `logs/agent_tools/2026-11-18/session_mix_verification.json`. Executable check: `scripts/verify_session_mix.py`. The study and verifier create immutable destinations and require fresh versioned paths for reruns.

Two 300 dpi PNG/vector-PDF figure pairs were visually inspected:

- `figures/dissertation/session-mix-qualifying-v1/01_qualifying_session_mix`: qualifying comparison and informative shorter-gap sensitivity. Dots are seed means; vertical lines span five matched sampling seeds, not confidence intervals.
- `figures/dissertation/session-mix-v2/01_session_mix`: supporting all-session comparison, including the ineffective ≥30 m/s filter for transparency.

Execution with the project environment:

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe scripts/study_session_mix.py
.venv/Scripts/python.exe scripts/verify_session_mix.py
```

The destinations already exist; preserve their original bytes and use new versioned scripts/destinations if recomputing. No claim of free-running lap prediction, digital-twin fidelity, grip identification, true electrical action accuracy or final-test generalisation follows from this study.
