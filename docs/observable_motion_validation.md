# Observable-motion assessment — 11 November 2026

The pre-controller observable-motion assessment is completed. Existing development fits transfer usefully to the two reserved validation events, while the assumed circuit reference has measurable discrepancy. This supports proceeding to controlled model-based controller experiments with explicit limitations. It does not establish accurate free-running lap prediction, grip, battery state or real electrical deployment.

## Protocol and evidence

`configs/motion_validation_protocol.json` was saved before evaluation. `scripts/assess_motion_validation.py` reads the prepared development/validation motion tables and the 21 existing driver-1 fits in circuit-input-assessment-001. It does not fit any new coefficients. The original development evaluation uses only each context's previously declared holdout laps. Validation transfer matches session name and exact DRS code, then takes the median of predictions from the eligible development context models. This combines predictions without pretending that different event-specific vehicle parameters were measured as one car.

The comparison baseline is each fit's training-lap mean acceleration, with the same median transfer rule. All methods use the same included windows. RMSE is calculated separately within each event/session/driver/lap/DRS group and then averaged with equal group weight per event. A lap containing several DRS codes contributes several groups. Adjacent windows and groups remain dependent; the results are descriptive and carry no independence or significance claim. The prepared full-throttle, unbraked, constant-gear/DRS windows retain signed acceleration and originate from conditional lap candidates, not certified clean laps.

There are 5,110 within-development holdout windows and 8,756 validation windows. The validation windows cover 65 unique session/lap combinations and 115 lap/DRS groups: Hungary 5,196 windows/45 laps/83 groups, UK 3,560 windows/20 laps/32 groups. Nine driver-1 validation windows lack a matched development session/DRS context and are explicitly excluded. Other drivers are outside this declared study. Of the included validation windows, 5.74% in Hungary and 16.07% in the UK lie outside the intersection of their transferred models' training-speed ranges; these remain flagged rather than removed after seeing performance.

## Results

Mean group RMSE, in m/s²:

| Validation event | Constant acceleration | Assumed base-power reference | Assumed full-request reference | Transferred development fits |
|---|---:|---:|---:|---:|
| Hungary | 4.578 | 3.793 | 3.169 | 2.776 |
| UK | 3.354 | 3.821 | 2.527 | 1.922 |

The corresponding mean biases of the transferred predictions are +0.086 and −0.170 m/s². The assumed full-request reference biases are +0.125 and −1.276 m/s². The existing reference therefore needs a clear model-based interpretation, particularly for cross-event transfer. Neither reference endpoint identifies the actual electrical action. Noise, finite-difference acceleration, unobserved controls, fuel, setup and model omissions can contribute to errors.

Only 37.16% of Hungarian and 22.72% of UK observed acceleration windows fall between the reference's base/full-power predictions. This is descriptive band occupancy, not statistical coverage: those endpoints are neither confidence bounds nor a complete physical envelope for real F1 cars.

All these predictions are conditioned on observed speed. Matching the acceleration relationship does not establish a free-running trajectory or validate the centreline's geometry and lateral limits. These straight-motion windows cannot identify cornering grip, smoothing, the official timing-line alignment, the combustion/electrical split, or battery efficiency. The previous circuit smoothing sensitivity remains material.

## Decision for the controller study

Keep configs/circuit_reference.json as an explicitly assumed, numerically checked benchmark. Do not silently replace its parameters or add fitted total power to the electrical contribution. The development/validation assessment is now closed with documented limitations; further pursuit of a calibrated digital twin is not a prerequisite for the user's accepted model-based dissertation scope.

Proceed in this order:

1. Implement shared-physics full-circuit deployment baselines and the controller interface. Use common initial speed/energy and terminal conditions for comparisons; record energy feasibility and elapsed time. Include zero request, full request and a budget-aware heuristic before claiming an RL improvement.
2. Benchmark training throughput and coarser integration/action resolutions against the accepted 0.625 m replay. The 0.5% lap-time numerical gate alone does not guarantee policy-ranking stability. Refine deployment action choices and preserve disagreements before selecting a training configuration.
3. Start a bounded RL pilot, then multiple seeds and sensitivity/evaluation once learning and replay checks pass. Record geometry and power/drag uncertainty separately from random-seed variation. Reserve final-test events for the frozen final evaluation.

## Artifacts and verification

Current run: results/motion-validation-002. The first run is preserved; Run002 improves the plot's legend clearance and uses a shared vertical scale without changing the analysis. Complete row predictions, exclusions, grouped metrics, input/code/output hashes and protocol are saved. No final-test files were read and no new telemetry downloaded.

The predictions for 13,866 rows and RMSEs for 161 lap/DRS groups were independently recalculated, and 13 manifest hashes checked. Verification log: logs/agent_tools/2026-11-11/motion_validation_verification.json. The existing physics implementation is unchanged; its 109-test result remains the prior implementation check, not a new test run. This analysis was checked by execution and independent arithmetic.

The comparison figure is saved as 300 dpi PNG and vector PDF in figures/dissertation/motion-validation-v2 and was visually inspected. Reproduce with fresh destinations:

```powershell
.venv/Scripts/python.exe scripts/assess_motion_validation.py --output results/motion-validation-NEW --figures figures/dissertation/motion-validation-NEW
```
