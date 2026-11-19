# Bounded reconstruction from real development motion — 18 November 2026

A bounded inverse diagnostic admits several different deployment patterns for the same observed Bahrain development-lap motion under explicitly assumed physics. This answers a restricted part of RQ1: selected real motion windows can constrain feasible *conditional* actions without identifying the actual electrical activity. It does not reconstruct a complete real lap or validate battery state, geometry, or timing-line alignment.

## Frozen design and data

`configs/bounded_real_reconstruction_protocol.json` was written before the first fit. The study uses only existing `results/openf1-motion-001/development.csv` rows for Bahrain meeting 1257, Qualifying, driver 1, lap 13. This is an already used development lap, not an independent test. Its prepared input hash matches the original preparation manifest. No validation/test telemetry, new acquisition, geometry or layout alignment was used. No alternative lap, tolerance revision, or post-fit parameter adjustment was allowed.

The fixed selection yields 159 full-throttle, unbraked, constant-gear/DRS adjacent windows, totalling 41.643 s within a 91.361 s first-to-last timestamp span. These are conditional candidates, not certified clean/dry conditions. Every omitted interval starts a new observed-speed-initialised segment: 36 segments and 39 segment-local nominal two-second action blocks. Segment duration may cross the nominal boundary by the native sample duration. Adjacent rows are dependent; no effective independent sample count or statistical significance is claimed.

The objective minimises endpoint speed mean squared discrepancy, using cumulative work-energy within each segment:

`v_end² = v_segment_start² + (2/m) Σ dt [P_base + P_deploy − k v_observed_mid³]`.

Observed midpoint speed conditions the drag quadrature. Resetting observed initial speeds and retaining observed drag inputs makes this considerably weaker than a free-running prediction. No circuit model or controller-training source is changed.

Nine assumptions were frozen: mass 750/800/850 kg, base power at 800 kg of 355/375/395 kW, and drag coefficient 0.511429 kg/m at 800 kg; base power and drag scale by mass/800. This family is anchored only loosely to the earlier development effective-power/drag diagnostic (453.278 kW total, 0.511429 kg/m at an assumed 800 kg). It is an illustrative confounding family, not an estimated parameter posterior or confidence region. Base power is separate from deployment; fitted total power is never added to it. The 750 kg arm reproduces the historical mass sensitivity but is below the nominal 800 kg reference and is a mathematical sensitivity, not a credible 2025 regulation-compliant car candidate. Interpret the 800/850 kg arms separately.

Each parameter set has three initial action fractions, 0.05/0.50/0.95. SLSQP jointly enforces mechanical deployment between 0 and 120 kW and a linear gross discharge constraint. The fixed acceptance criterion is optimizer success, speed RMSE ≤1.0 m/s, maximum absolute endpoint error ≤3.0 m/s, and partial energy feasibility with 1 J numerical tolerance. These motion tolerances are illustrative engineering criteria, not telemetry-error confidence intervals. Failed cases remain failed.

## Energy and regeneration scope

Initial energy is assumed 2 MJ, reserve 0.1 MJ, capacity 4 MJ and discharge efficiency 0.9, with the existing gross discharge allowance of 4 MJ. These are declared modelling assumptions/interfaces, not measured battery values. Selected unbraked windows have no eligible braking recovery. Their common energy constraint is therefore the tighter 1.9 MJ available above reserve. Each selected interval debits its mechanical deployment work divided by 0.9.

The partial accounting concatenates selected windows and assigns zero deployment and zero recovery to omitted intervals. Omitting recovery is conservative about available harvested energy; omitting deployment is **not** conservative about full-lap consumption. Consequently passing this calculation establishes only selected-window feasibility. It neither proves nor disproves feasibility of a real full-lap schedule. There is no claimed regenerative full-lap reconstruction. The current regeneration-aware reference remains documented in `docs/regeneration_study.md`: assumed 0.8 charging efficiency and 0.4 rear-braking share, with 120 kW mechanical recovery, 2 MJ recovered and 4 MJ discharged bounds at its declared interfaces. Since none of these selected windows brake, these recovery assumptions are inactive here.

## Results

All 27 optimizations terminate successfully and satisfy the partial energy/power constraints. Seven of nine physical-assumption rows pass the frozen motion tolerances, consistently across all three starts (21/27 fits). The two failed rows exceed the 1 m/s RMSE limit. All runs use the entire 1.9 MJ selected-window budget and end at the 0.1 MJ reserve: this is imposed-model budget saturation, not evidence of actual energy use.

| Mass (kg) | Base power (kW) | RMSE (m/s) | Maximum error (m/s) | Frozen motion decision |
|---:|---:|---:|---:|---|
| 750 | 332.813 | 0.980 | 2.351 | Pass; mathematical mass sensitivity |
| 750 | 351.563 | 0.793 | 1.928 | Pass; mathematical mass sensitivity |
| 750 | 370.313 | 0.695 | 2.486 | Pass; mathematical mass sensitivity |
| 800 | 355.000 | 1.023 | 2.496 | Fail |
| 800 | 375.000 | 0.830 | 1.999 | Pass |
| 800 | 395.000 | 0.721 | 2.486 | Pass |
| 850 | 377.188 | 1.061 | 2.643 | Fail |
| 850 | 398.438 | 0.864 | 2.062 | Pass |
| 850 | 419.688 | 0.747 | 2.486 | Pass |

The four passing 800/850 kg candidates have speed RMSE 0.721–0.864 m/s, yet their conditional deployment patterns differ. The largest pairwise row-weighted deployment RMSE is 14.387 kW (800 kg/395 kW versus 850 kg/398.438 kW). Across the complete illustrative grid, the largest passing-pair difference is 22.843 kW, including the 750 kg mathematical arm. Row weighting is explicit; this is not a distance- or duration-weighted action metric. Repeated starts for a given parameter set differ by at most 38.584 W across all action blocks, suggesting numerical consistency of these bounded fits without proving global optimality or identifiability.

This result extends the prior synthetic demonstration (`results/reconstruction-synthetic-002`), where a ±20 kW base-power change produced different feasible actions with essentially identical synthetic speed endpoints. Here the motion is real, the discrepancy is nonzero, and acceptance depends strongly on the declared tolerance and partial-window model. Existing observable-motion evidence (`docs/observable_motion_validation.md`) already shows assumed power-reference discrepancy; the present short-segment conditional fit does not remove that limitation. Multiple parameter/action solutions support nonuniqueness under declared assumptions, not a conclusion that any of these solutions was used by the car.

## Reproduction, verification and figures

Runner: `scripts/reconstruct_bounded_real.py`; accepted artifact: `results/bounded-real-reconstruction-002`; frozen study identifier remains `bounded-real-reconstruction-001`. Run001 retains a path-serialization failure after computation and plotting; Run002 fixes absolute/relative manifest-path serialization only, with unchanged selection, physics, optimizer, thresholds and results. No original source or prior scientific artifact was overwritten.

```
.venv/Scripts/python.exe scripts/reconstruct_bounded_real.py --output results/bounded-real-reconstruction-NEW --figures figures/dissertation/bounded-real-reconstruction-NEW
```

The runner leaves a runnable cumulative-matrix/segment-reset/analytic-energy self-check. Independent scalar work-energy and battery replay recomputed all 4,293 saved endpoints, with maximum matrix/scalar speed difference 2.85e-14 m/s, reproduced RMSE and energy accounting, and checked seven input/source/output hashes plus the prepared table's original manifest hash. Evidence is in `logs/agent_tools/2026-11-18/bounded_real_inverse_verification.json`. CPU linear algebra was limited to one thread; no neural training ran.

The 300 dpi PNG/vector PDF pair is `figures/dissertation/bounded-real-reconstruction-v2/01_bounded_real_inverse`. The PNG was visually inspected: labels, units, legends, reserve and all nine curves are legible without clipping. It displays the first start for every declared parameter row, including failures and mathematical mass sensitivities. Connected curves use cumulative selected-window time with missing intervals removed; speed jumps join separately initialised segments and must not be interpreted as simulated braking. Caption: *Conditional reconstruction of selected Bahrain development lap 13 motion under nine declared assumptions. Similar selected-window speed matches coexist with differing assumed deployment. Energy traces account for selected propulsion windows only; all fits saturate the assumed 1.9 MJ budget. This is not an inferred real battery trace or full-lap validation.*
