# Bahrain T8 and T14 path check

The cached driver-1 lap-13 path is consistently flatter than the reference at T14. That agrees with the direction of the frozen model's local speed error: its minimum is too low. T8 provides weaker evidence: its observed path is tighter at short chord scales but flatter at the broadest scale. Geometry is a plausible contributor, especially at T14, but this check does not establish a cause or explain both discrepancies by itself. T1 remains a useful control: reference curvature is higher there too, although minimum speeds nearly agree.

## Frozen scope and method

Run `bahrain-corner-paths-001` reads only cached development driver-1 qualifying lap 13 (session 10010), its saved speed trace, frozen global registration, original TUM Sakhir reference and existing calibrated replay. No driver-22 file, new telemetry, fitting, holdout score or simulator change is involved. The interpretation is diagnostic evidence informed by the existing model errors, not an independent validation cohort.

The unchanged registration converts native F1 coordinates to metres (factor 0.1), then applies the frozen proper rotation, translation and common scale 1.0040133661. The complete register is copied into `metrics.json`; registered XY and time for all **342 native interior locations** are in `lap13_registered_native_positions.csv`. Native means actual rows in the cached provider export, not proof of raw sensor measurements. The first and last timing-edge interpolations are excluded from this location count.

Paths compared are the observed piecewise-linear native locations, the original centreline polyline, and the simulator's exact existing timing-line-registered 10 m Gaussian-smoothed periodic spline (5 m resampling parameter), obtained with the unchanged `bahrain_pace_model.registered_curve` helper. Curvature is compared by the same three-point circumcircle formula on all paths: sample at physical arclength `s-h`, `s`, `s+h`, with halfspans **10, 20 and 40 m**. These are 20, 40 and 80 m total support extents, not fitted circle radii. Each path is parameterised by its own physical arclength in the registered metre frame; this avoids a derivative of irregularly spaced time samples. The 0.4% frozen common scale therefore also applies to observed lengths. Chord points are interpolations and do not add independent data.

The observed landmark location is interpolated at the frozen marker time. That same XY point is projected to each reference path to set its local zero. This permits a comparison of corner shape without treating the existing phase/arclength mismatch as curvature; it changes no XY coordinates and is not a local geometric fit. Positive distance follows traversal. Full profiles are saved over ±100 m, with peak summaries searched within ±60 m to tolerate approximate marker placement. Native sample support and perpendicular projection residuals to the original reference are saved within ±150 m. Turn annotations retain approximately ±50 m display tolerance.

## Results

Peak absolute curvature within ±60 m, in **1/m**. Each cell lists observed / smoothed reference; the raw reference results are also saved in the metrics and chord CSV.

| Turn | h = 10 m | h = 20 m | h = 40 m |
|---|---:|---:|---:|
| T1 control | 0.05880 / 0.08207 | 0.05316 / 0.06548 | 0.03687 / 0.04151 |
| T8 | 0.06192 / 0.04751 | 0.04685 / 0.04214 | 0.03453 / 0.03700 |
| T14 | 0.03308 / 0.05036 | 0.02693 / 0.04395 | 0.02056 / 0.03030 |

At T14, the observed peak is **32–39% below** the smoothed reference across all three scales. The original polyline is tighter still, so this direction is not introduced by the existing smoothing. The XY overlay shows a broader observed entry and bottom of the turn. The frozen local minima are 120.0 km/h observed and 91.7 km/h simulated. A reference path that is too tight could reduce a curvature-limited model's speed in this direction. The check does not assign how much of the 28.3 km/h difference it causes.

At T8, the observed peak is 30% above reference at h=10 m and 11% above at h=20 m, but **7% below** at h=40 m. The existing smoothed spline reduces the raw reference's h=10 m peak from 0.06120 to 0.04751 1/m, whereas the observed value is 0.06192. This makes local smoothing a plausible contributor at a short scale, not a scale-stable explanation. Frozen minimum speeds are 70.0 versus 93.6 km/h. The reference peak is also approximately 14–16 m later along its own locally centred path at the short scales. Sparse sampling, path shape, local timing/progress alignment and the effective grip/braking model remain competing explanations.

At T1, observed peak curvature is 11–28% below the smoothed reference, yet the previously measured minimum speeds are 67.0 and 67.8 km/h. Agreement in one minimum therefore does not validate the local path or lateral model; compensating effective parameters and different corner-exit behaviour remain possible. This control is a reason to avoid claiming curvature alone explains speed errors.

| Turn | Native rows ±150 m | Maximum local time gap (s) | Maximum native XY step (m) | Projection RMS / maximum (m) |
|---|---:|---:|---:|---:|
| T1 | 27 | 0.819 | 31.33 | 4.87 / 10.47 |
| T8 | 32 | 0.460 | 25.16 | 3.34 / 6.22 |
| T14 | 25 | 0.421 | 30.90 | 6.37 / 10.99 |

These projection distances include driving-line displacement, source-map error and residual global-registration error; they are not measurement-error estimates or confidence intervals. In particular h=10 m can be shorter than a native location step. The visible short-scale wiggles should not be interpreted as resolved tyre-level curvature. The h=20/40 m results give the more defensible scale check. No road-width, kerb, elevation, tyre or downforce data have been inferred.

## Inspectable evidence and checks

- [Nine-panel figure, vector PDF](../figures/dissertation/bahrain-corner-paths-v1/corner_paths.pdf) and [300 dpi PNG](../figures/dissertation/bahrain-corner-paths-v1/corner_paths.png): registered XY with native points, equal-scale chord curvature, and the existing frozen speed comparison. The speed panels use the frozen model progress axis, not the independently centred path-arclength axis used for curvature.
- [Local native register](../results/bahrain-corner-paths-001/native_support.csv): times, registered positions, interpolated car speed, path station, speed-integrated progress, closest source station and residual. Interpolated speeds are not additional car samples.
- [Curvature profiles](../results/bahrain-corner-paths-001/curvature_chords.csv), [metrics and complete registration](../results/bahrain-corner-paths-001/metrics.json), [all native lap positions](../results/bahrain-corner-paths-001/lap13_registered_native_positions.csv), [manifest](../results/bahrain-corner-paths-001/manifest.json) and [verification](../results/bahrain-corner-paths-001/verification.json).

Executed in PowerShell with `$env:PYTHONPATH='src'` followed by `.venv/Scripts/python.exe scripts/assess_bahrain_corner_paths.py`. An initial invocation without the repository's `src` import path failed before writing output. The successful run took **2.20 s** inside the analysis, excluding interpreter startup. An existing completed manifest is protected against rerunning over the run. QA caught that the first draft spline was resampled from the source origin rather than the exact simulator timing-line origin; the final run reuses the exact frozen helper. The superseded draft outputs are retained under `_draft_origin_qa` in the owned result/figure folders. The correction changed the quoted curvature values slightly, without changing their directions or conclusions. An intermediate manifest writer also encountered the draft subdirectory; its file list was corrected before the completed final manifest was verified.

Assertions check exact three-point curvature against a known 50 m circle and a straight line, increasing native timestamps, and frozen hashes of the driver-1 position trace, lap-speed trace and geometry. Independent post-run verification checked **18 manifest hashes**, the existing replay/model/corner-check hashes against their original manifests, PNG dimensions 3600×3300 and approximately 300 dpi, and the PDF header. The complete nine-panel PNG was visually inspected for readable axes, legends and native support. Figure SHA-256: PNG `0734a0ebe5229a4ddf0bfc4bda9590869c703577544abeb7a63eece55da84a51`; PDF `a16974dcacfed585fee343b0c549594fb6839a8db77f0bfdc2bdfbfb7dfc2b45`.

This descriptive comparison supports prioritising path fidelity near T14 and a smoothing/alignment investigation near T8 before interpreting the conditional deployment map more strongly. It supplies no replacement fit or new independent performance claim. The original lap-10 pace-gate failure and existing model results remain unchanged.
