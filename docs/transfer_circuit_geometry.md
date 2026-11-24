# Silverstone geometry and frozen vehicle transfer

Silverstone's 2025 layout aligned with the official event map. The frozen Bahrain vehicle built and ran on that layout, but the spread baseline missed the required control-line speed on both grids. The separate pace and braking-location checks also failed. The study stopped before comparing deployment schedules or transferring learned controllers.

Silverstone was selected by the exploratory second pass of the braking screen after the strict native-coverage pass found no qualifying circuit. The geometry run used the five laps selected by that existing rule, with UK qualifying session 9943 retaining its validation role. The protocol was fixed before reading those lap outcomes. There was no vehicle fitting, tuning, or deployment selection on Silverstone and no access to final test telemetry. [Braking screen](circuit_braking_screen.md) · [Geometry protocol](../configs/transfer_circuit_geometry.json) · [Frozen selection](../results/circuit-braking-screen-001/selection.json)

## Layout, control line and DRS

A 2D similarity registration projected manually sampled FIA map points onto the TUMFTM closed polyline. The fit excluded the control-line, sector and DRS markers. The source order matched the clockwise sequence of all 18 FIA turn markers. The polyline length was 5,886.8 m against the FIA reference of 5,891 m, a 0.07% difference. Fit RMSE was 2.52 m and the largest marker projection residual was 8.55 m. These residuals measure agreement with the drawn map. The numbering and station annotations are approximate. [FIA event map v2](https://www.fia.com/system/files/decision-document/2025_british_grand_prix_-_event_notes_-_circuit_map_v2.pdf) · [Registration results](../results/transfer-circuit-geometry-001/metrics.json)

Stations are metres along the raw centreline from the projected FIA control line. Sectors 1 and 2 end at 1,820 and 4,280 m. The prescribed DRS zones begin near 1,307 m after T5 and 4,229 m near T14. The FIA map specifies activation points. For simulation, the zones end at 1,890 and 4,965 m, 100 m before the mapped T6 and T15 markers respectively. The midpoint rule on 55 equal source-parameter blocks gives effective simulated openings of approximately 1,285–1,931 m and 4,281–4,927 m on the 5 m diagnostic grid. The same rule and the Bahrain DRS drag multiplier apply in all replays. [Figure and approximate turn locations](../figures/dissertation/transfer-circuit-geometry-v1/01_silverstone_transfer_geometry.pdf) · [Frozen model](../results/transfer-circuit-geometry-001/model.json)

The centreline is reproduced unchanged from the pinned TUMFTM racetrack-database revision. The repository supplies a GNU LGPL v3 license and credits OpenStreetMap GPS points as the source of the centreline. © OpenStreetMap contributors under the ODbL. The FIA document is cited for the event and local marker positions. Only original plots and numerical landmark annotations are distributed here. [Pinned centreline](https://raw.githubusercontent.com/TUMFTM/racetrack-database/e59595d1f3573b30d1ded6a08984935b957688e0/tracks/Silverstone.csv) · [Repository data provenance](https://github.com/TUMFTM/racetrack-database/tree/e59595d1f3573b30d1ded6a08984935b957688e0) · [Supplied license](../results/transfer-circuit-geometry-001/SOURCE_LICENSE.txt) · [OpenStreetMap copyright](https://www.openstreetmap.org/copyright)

## Gates and evidence

The model kept the Bahrain rolling target of 80.65 m/s, vehicle and regeneration coefficients, and battery state. On the 4,400- and 8,800-cell grids, spread finished 20.47 and 20.38 m/s below that target. The fixed 25% request missed by 23.28 and 23.20 m/s. Its elapsed time changed by 0.180 s between grids and met the 0.250 s refinement threshold. Both fixed-request elapsed times are from physically integrated runs that missed the finish condition.

Four of the five selected laps had usable, time-bracketed speed data at the 1.0 s limit. Their speed-integrated lengths were 5,818–5,838 m, within 2% of the model centreline. Their independently aligned XY traces established forward direction with about 5.2 m fit RMSE. The largest timing-line disagreement among the fitted phase and both projected lap edges was 62.3 m against the 65 m bound. Location gaps of 1.08 s on driver 1 lap 5 and 1.04 s on driver 22 lap 9 exceeded the 1.0 s limit. Driver 22 lap 12 had a 1.04 s raw speed interval bracketing the opening timing edge, so no full pace score was computed. The independent native location and distance check passed on driver 1 lap 14 and driver 22 lap 3. [Per-lap evidence](../results/transfer-circuit-geometry-001/metrics.json)

| Driver | Lap | Simulated minus observed lap time (s) | Speed RMSE (m/s) | Independent location and distance |
|---|---:|---:|---:|---|
| 1 | 5 | +5.91 | 12.97 | Fail |
| 1 | 14 | +6.53 | 11.50 | Pass |
| 22 | 3 | +5.14 | 11.27 | Pass |
| 22 | 9 | +5.32 | 11.56 | Fail |
| 22 | 12 | — | — | Failed native speed preparation |

Every scored lap exceeded the 2.0 s lap, 1.0 s per-sector and 5.0 m/s speed tolerances. Sector two was 2.81–3.38 s slow. DRS passed the extent and overlap checks on three scored laps. One missed the 120 m boundary bound by 5 m at the second activation after block quantization. Each scored lap passed the requirement for at least 80% of observed brake onsets to precede a sufficient curvature peak within 200 m. The frozen simulation produced 18 brake intervals versus seven or eight observed per scored lap, and all four comparisons failed the joint onset and minimum-speed criterion. The sharp simulated speed reductions at Abbey and Copse show where a broadly correct layout can still yield inaccurate pace. [Gate definitions and model trace diagnostics](../results/transfer-circuit-geometry-001/metrics.json)

The registered track and model are available to reproduce these checks. The geometry and solver gate, pace gate, and empirical location gate all returned false. Any subsequent vehicle or rolling-boundary change informed by these laps would require independent laps for an empirical transfer claim. [Machine-readable manifest](../results/transfer-circuit-geometry-001/manifest.json)

## Why the inherited finish target is unreachable

A separate diagnostic bounded the best possible finish speed from every interior grid node. With about 94 m left, the simulator’s braking envelope limited the speed to 41.05 m/s. Granting the full 490.57 kW of base and electrical power for the remaining distance, unlimited battery energy and zero aerodynamic drag gave an upper bound of 62.33 m/s on the 160-cell grid and 62.38 m/s on the 320-cell grid. Both are below the inherited 80.65 m/s requirement. Changing when a controller deploys cannot close this gap under the frozen Silverstone model.

The calculation follows from the spatial energy balance, which gives d(v³)/ds ≤ 3P/m. A check on both Bahrain grids put the planner’s achieved finish below the corresponding upper bound. The Silverstone bound diagnoses a model and boundary-condition mismatch. A future circuit-specific fit needs independent corner-exit motion and a justified rolling speed before controller gains can be compared. [Bound and Bahrain checks](../results/silverstone-finish-bound-001/metrics.json) · [Figure](../figures/dissertation/silverstone-finish-bound-v1/01_finish_speed_bound.pdf)

## Reproduction

From the repository root, place the pinned source CSV and license at the paths in the protocol. The archived raw OpenF1 response cache and frozen screen selection are also required. Use fresh run directories for a replay.

```powershell
$env:PYTHONPATH = 'src'
.venv/Scripts/python.exe scripts/prepare_transfer_circuit.py --output work/replay-silverstone --figures work/replay-silverstone-figures
```
