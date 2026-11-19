# Full-circuit implementation and numerical validation — 11 November 2026

The full-circuit curvature, braking and forward speed-envelope implementation is complete for the declared Bahrain reference model. The numerical gate passes; empirical vehicle validity and controller-training readiness remain separate questions. No final-test telemetry was used, and no new PPO training was performed.

## Implementation

`src/f1energy/circuit.py` constructs a periodic cubic centreline after uniform polygon-distance resampling and periodic Gaussian smoothing. Signed curvature uses analytic spline derivatives. Each cell's lateral speed cap uses the largest absolute curvature at its boundaries, spline knots and interior stationary points. Interior extrema are found from the polynomial equation `2*C'*D - 3*C*D' = 0`, where `C=x'y''-y'x''` and `D=x'^2+y'^2`. This avoids missing a narrow corner between sampled nodes. Cell distance is the integrated spline arc length, distinct from its approximately distance-based parameter.

The backward braking envelope is cyclic. Each node respects both adjacent cell caps; the backward bound includes constant friction deceleration and quadratic drag, matching `event_power_lap.py`. Forward replay calls that existing event solver without clipping speed or resetting battery at cell boundaries. This supplies acceleration feasibility beneath the upper envelope. Speed-periodic shooting enforces equal start/end speed for a fixed starting battery and per-cell action sequence. It does **not** enforce battery periodicity: each shooting trial is an independent single-lap calculation.

The source order matches the main GP layout and clockwise progression in the [FIA 2025 Bahrain map](https://www.fia.com/system/files/decision-document/2025_bahrain_grand_prix_-_event_notes_-_circuit_map_v4.pdf), whose second page was locally rendered and visually compared. This is a topology/direction check, not a metric survey. The source origin is retained and is not certified to be the official control line. The source remains the approximate [TUM Sakhir centreline](https://github.com/TUMFTM/racetrack-database/blob/master/tracks/Sakhir.csv); its licence and original geometry are preserved in circuit-input-assessment-001.

## Declared assumptions

`configs/circuit_reference.json` records an assumed 800 kg vehicle, 450 kW base power, at most 120 kW electrical power, 0.9 discharge efficiency, drag coefficient 1 kg/m, friction deceleration 12 m/s², lateral acceleration limit 20 m/s² and 95 m/s ceiling. Battery starts at 2 MJ with a 0.1 MJ reserve. These are research reference values, not fitted component specifications or claims about regulations. Effective total-power telemetry fits are **not** added to these powers.

The lateral and longitudinal limits are independent. There is no combined-slip tyre model, downforce map, grade, regeneration, DRS or optimized racing line. Available drive power is not constrained by a combined tyre-force envelope. These limitations affect physical interpretation even when the numerical equations are solved accurately.

Smoothing sigma is nominally 10 m; 5 and 20 m are sensitivity cases. The original polygon is 5,405.749 m; smoothed spline lengths are 5,396.107 m, 5,373.012 m and 5,307.755 m respectively. Smoothing changes length and corner shape together. These lengths are not rescaled to force agreement with the official 5,412 m, and smoothed paths are not certified to remain within track boundaries. A 0.625 m numerical grid does not create new geometric measurement resolution from the approximately 5 m source spacing.

## Evidence and gates

The integrated automated suite passes **109 tests**, including seven new circuit tests: analytic circle turning/closure, dense checks of interior curvature bounds and direction reversal, independent all-downstream cyclic braking constraints with/without drag, rotation invariance, full-lap depletion/energy/caps, power-limited periodic speed, sub-1 m/s shooting, and invalid-input rejection. A compact independent code review found a low-speed shooting-bracket issue; it was repaired with adaptive bracketing and a regression test before the circuit study.

Run001 passed energy, reserve, speed-cap and periodicity checks but **failed** the predeclared 0.5% finest-grid time criterion: 5 to 2.5 m refinement changed full-request lap time by 1.478%. The failure remains preserved. Run002 stopped before simulation because of a Windows path-key mismatch in the new cache loader; its failure log is retained. Run003 added 1.25 and 0.625 m cases without changing the tolerance and passed. Run004 reuses all 15 compatible, hash-verified Run003 cases and improves figure rendering only; it is the current presentation artifact. No simulations were rerun for Run004.

| Nominal geometry grid (m) | No electrical request (s) | Full electrical request (s) |
|---:|---:|---:|
| 20 | 118.647321 | 117.821218 |
| 10 | 114.781875 | 113.941452 |
| 5 | 112.173994 | 111.316705 |
| 2.5 | 110.553918 | 109.695628 |
| 1.25 | 109.820370 | 108.959829 |
| 0.625 | 109.439293 | 108.576470 |

The finest-pair change is **0.348%** without electrical request and **0.353%** with full request, passing the preset 0.5% criterion. This is a bounded refinement result, not a bound on error against an exact solution. At the finest grid the baseline gap is 0.862823 s; neither policy is claimed optimal. The full-request trajectory depletes to reserve once, drawing 1.9 MJ and delivering 1.71 MJ at the wheels. All cases satisfy equal start/end speed within 1e-6 m/s. Tightening the numerical solver changes the finest full-request time by approximately 3.5e-10 s. Independent global kinetic/work-balance recomputation across all 15 cases has a maximum absolute residual below 7.3e-8 J, well inside the 1 J gate.

At a common 5 m grid, changing smoothing sigma from 5 to 10 to 20 m changes full-request duration from **115.961 to 111.317 to 104.788 s**. This large model sensitivity is separate from discretization error. It must be reported rather than selecting smoothing solely to match a real lap time. No observed lap times were used in this study.

Results, complete profiles, configurations, code/input hashes and metrics: `results/circuit-validation-004`. Original case computations: Run001 and Run003. The cache checks all saved output hashes, physical source hashes, model assumptions and runtime versions; only reporting code and the refinement schedule may differ. Logs: `logs/agent_tools/2026-11-11/circuit_*`. Two 300 dpi PNG/vector PDF figure pairs in `figures/dissertation/circuit-validation-v4` show curvature, braking/speed limits, spatial refinement, smoothing sensitivity and battery energy. They were visually inspected.

Reproduce from the project root in PowerShell, using fresh output destinations:

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe scripts/validate_circuit.py --output results/circuit-validation-NEW --figures figures/dissertation/circuit-validation-NEW
```

Use `--reuse results/circuit-validation-003` to reuse compatible cases with their hashes verified. Existing output destinations are rejected. Python/NumPy/SciPy versions are recorded in the run contract.

## Next gates, in order

1. Assess observable motion against development and reserved validation evidence, explicitly handling approximate centreline versus actual racing line, source-origin alignment, smoothing, grip and power assumptions. Keep final test events untouched. Numerical validity alone is not real-car calibration.
2. Establish full-circuit controller interfaces and shared-physics baseline comparisons, with action-grid/optimization refinement and parameter/geometry sensitivity. The present two fixed-action policies only verify replay. Choose a cheaper training grid or acceleration scheme only after measuring its effect on policy ranking against the accepted fine replay.
3. Run bounded multi-seed physical-model training, then a frozen held-out evaluation and dissertation comparisons. Retain negative results and uncertainty; no claim of measured battery/deployment accuracy.
