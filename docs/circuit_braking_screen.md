# Qualifying braking screen for a second circuit

Silverstone is the selected **exploratory** second circuit. Compared with Bahrain, both drivers had lower observed brake-time share and shorter typical braking-onset spacing as a fraction of supported lap distance. The five Silverstone laps are a screened 2025 qualifying cohort from a previously used validation event. Its result supports choosing a distinct modelling case. Any new geometry, timing-line registration, forward-model validation or controller comparison requires its own checks. [Selection](../results/circuit-braking-screen-001/selection.json)

## Protocol and coverage

Only role-checked OpenF1 qualifying car streams for Bahrain, Hungary, Silverstone and Monza were read. The screen reused the acquisition's conditional motion candidates for Red Bull Racing drivers 1 and 22. The original rule required at least two laps per driver with at least 97.5% timed support, a native pair gap of at most 0.50 s and no more than 0.50 s uncovered at either lap edge. Bahrain supplied only one eligible lap for driver 1, so the original rule returned no selection. [Original protocol](../results/circuit-braking-screen-001/protocol_primary.json)

After inspecting coverage and before inspecting braking contrasts, a single exploratory amendment set the requirements to 95% timed support, at most 0.75 s per native pair and at most 1.00 s at either edge. It retained the minimum two laps per driver and the original contrast requirement. A candidate had to show the same direction of change for both drivers against their respective Bahrain medians and reach a threshold in the same indicator for both. The thresholds were a 2 percentage point brake-share difference and a 15% relative difference in typical onset spacing divided by supported lap distance. The frozen priority was Hungary, Silverstone, then Monza. As fallback, Silverstone took precedence over Monza because Monza was a development event. [Protocol with amendment](../configs/circuit_braking_screen.json)

| Circuit and role | Acquisition candidates, 1 / 22 | Original eligible, 1 / 22 | Exploratory eligible, 1 / 22 | Exploratory decision |
| --- | ---: | ---: | ---: | --- |
| Bahrain, development | 3 / 3 | 1 / 2 | 3 / 3 | Reference |
| Hungary, validation | 4 / 1 | 0 / 0 | 4 / 1 | Spacing contrast in both drivers. Driver 22 had one eligible lap. |
| Silverstone, validation | 3 / 3 | 0 / 2 | 2 / 3 | Selected. Passed both contrast indicators. |
| Monza, development | 2 / 2 | 0 / 1 | 2 / 2 | Passed both contrast indicators. Third in priority. |

Silverstone driver 1 lap 11 had 94.15% timed support in the exploratory pass. The selected laps were driver 1 laps 5 and 14 and driver 22 laps 3, 9 and 12, all session 9943. See lap-level records for coverage, leading/trailing gaps, omitted interior intervals, censored bouts and every retained onset spacing. [Lap-level records](../results/circuit-braking-screen-001/metrics.json)

## Observed braking

| Circuit | Driver | Eligible laps | Brake time (s) | Brake share (%) | Summed speed loss (m/s) | Onset spacing (m) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Bahrain | 1 | 3 | 17.32 | 19.03 | 338.5 | 680.0 |
| Bahrain | 22 | 3 | 16.12 | 17.50 | 310.7 | 565.8 |
| Hungary | 1 | 4 | 13.82 | 18.20 | 226.5 | 257.0 |
| Hungary | 22 | 1 | 14.00 | 18.29 | 198.1 | 286.9 |
| Silverstone | 1 | 2 | 10.64 | 12.43 | 137.7 | 603.6 |
| Silverstone | 22 | 3 | 11.86 | 13.69 | 193.2 | 357.0 |
| Monza | 1 | 2 | 10.22 | 12.94 | 212.2 | 901.3 |
| Monza | 22 | 2 | 9.03 | 11.36 | 208.4 | 1055.3 |

The table gives medians across eligible laps for each driver and circuit. Silverstone brake-time shares fell by 6.60 and 3.82 percentage points for drivers 1 and 22, respectively. Their normalized onset spacing fell by 17.6% and 42.5%. Hungary's spacing was shorter by 53.3% and 37.8%, with the latter estimate based on one lap. Monza's spacing was longer by 23.1% and 72.6%. Silverstone within-driver spacing varied substantially. The eligible individual lap medians ranged from 338 to 869 m for driver 1 and 353 to 1,010 m for driver 22. Only two or three onset spacings contributed to some of those individual lap medians. [Figure PDF](../figures/dissertation/circuit-braking-screen-v1/01_qualifying_braking.pdf) · [300 dpi PNG](../figures/dissertation/circuit-braking-screen-v1/01_qualifying_braking.png)

The binary brake flag estimates time under reported braking. State changes use the midpoint of each supported native observation pair, with linear speed interpolation. Brake share divides supported brake-on seconds by the timed-lap duration. Brake bouts touching a lap edge or an excluded interval are censored and contribute supported time only. Summed speed loss adds signed entry-minus-exit speed differences across complete bouts. Onset spacing uses trapezoidal speed integration between successive complete onsets in the same contiguous support, without wrapping across the timing line. These distances describe observed motion along the lap without projecting onto circuit geometry.

Brake duration, loss of speed and spacing describe opportunities under a model that enables recovery during braking. The underlying data leave brake torque, friction/electrical split, battery headroom, recovered energy and delivered wheel assist unknown. Both drivers and laps share a session and laps within each driver are dependent. Fuel, setup, traffic and exact lap edges can affect the comparison.

## Reproduction

From the repository root, use fresh output directories for a replay.

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe scripts/screen_circuit_braking.py --output work/circuit-braking-screen-replay --figures work/circuit-braking-screen-replay-figures
```

The replay reproduced six non-manifest outputs byte for byte, including the figure pair. All 33 recorded hashes matched. An independent calculation re-integrated supported time, brake duration and distance for 21 candidate laps across eight non-test car streams. [Manifest](../results/circuit-braking-screen-001/manifest.json)
