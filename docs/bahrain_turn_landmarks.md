# Bahrain approximate corner landmarks

`configs/bahrain_turn_landmarks.json` freezes 15 display landmarks for the Bahrain Grand Prix layout. They are manually annotated corner locations projected onto the previously selected **development** qualifying driver 1 lap 13 (session 10010, 12 April 2025). They are not brake, regeneration or deployment boundaries and must not define scored zones. No holdout lap or final-test event was read for this work.

Source: [MultiViewer circuit metadata](https://api.multiviewer.app/api/v1/circuits/63/2025), fetched 18 November 2026 with the installed FastF1 user-agent convention. **Although the requested path says 2025, the response identifies itself as 2022**, circuit 63, Sakhir, and gives a 2022 FP1 candidate lap. This is reused manual map metadata, not newly measured 2025 telemetry. All 15 labelled bends and their order were checked against the local FIA 2025 circuit map (`work/track-source/bahrain_fia_2025.pdf`, rendered as `bahrain_fia_map.png`); the same Grand Prix layout is evident. FastF1 3.9.0 `mvapi/data.py` explicitly describes these manual marker positions as not highly accurate but adequate for visualisation. Its distance fields require reference-lap projection. Consequently the raw API `length` field is not taken as timing-line distance.

The raw response is retained locally at `work/track-source/bahrain_multiviewer_2025.json`; its SHA-256 and the cached position/lap CSV/registration hashes are in the config. Marker XY values in metres are also preserved in each config row. A mistaken initial circuit-15 request returned HTTP 403; circuit 15 is Catalunya, so it supplied no Bahrain evidence. The one correct circuit-63 request returned HTTP 200 (14,684 bytes).

Projection uses the unrotated shared F1 XY coordinates. Native values are multiplied by 0.1, consistent with installed FastF1 `core.py` documenting position units as 1/10 metre. MultiViewer gives a display rotation of 92 degrees; no rotation is required to compare these native points to OpenF1 positions. Each point is projected continuously onto the closest segment of the lap-13 XY trace. The projected time is interpolated onto the frozen car-speed-integrated distance fraction in `results/bahrain-pace-inputs-001/lap-13.csv`. Its total integrated distance is **5,363.026 m**, which is a measured trace integral, not the official 5,412 m centreline length. `fraction` starts at the timing/control line and increases in driving direction. Scale it by a model lap length only to position an approximate label on the corresponding model progress axis.

For geometry plots, `source_geometry_fraction` instead uses XY arclength progress plus the independently obtained source-origin offset 0.0075202468261320755, modulo one. This respects the distinction between speed-integrated progress and geometry progress. The associated source-to-trace registration uses forward traversal without reflection and has 5.810 m RMS residual. Source TUM geometry has an arbitrary origin; do not subtract the phase again from `fraction`.

All 15 projected positions increase monotonically and residuals are below **2.876 m**. Small perpendicular residuals do not establish precise longitudinal station: manual marker placement, an older source lap and sparse samples remain. The largest bracketing segment among these corners is 66.682 m (T9); T4 has a 1.140 s location gap. Use a deliberately coarse **approximately ±50 m display tolerance**, not a statistical confidence interval or validated survey accuracy. No timing-line claim is inferred from raw MultiViewer lengths.

| Landmark | Lap fraction | Approx. fit-lap distance (m) |
|---|---:|---:|
| T1 | 0.13080 | 701 |
| T2 | 0.14781 | 793 |
| T3 | 0.16916 | 907 |
| T4 | 0.27808 | 1491 |
| T5 | 0.32835 | 1761 |
| T6 | 0.34531 | 1852 |
| T7 | 0.36322 | 1948 |
| T8 | 0.41141 | 2206 |
| T9 | 0.47773 | 2562 |
| T10 | 0.49725 | 2667 |
| T11 | 0.64129 | 3439 |
| T12 | 0.71495 | 3834 |
| T13 | 0.75614 | 4055 |
| T14 | 0.90579 | 4858 |
| T15 | 0.92178 | 4944 |

Reproduction: `.venv/Scripts/python.exe scripts/prepare_bahrain_landmarks.py`, using the retained local inputs. Embedded assertions check all 15 labels, increasing traversal order and the residual ceiling. The command completed successfully; compact projection evidence is `work/track-source/bahrain_landmark_projection.log`. No new telemetry was downloaded and no physics or calibration source was changed.
