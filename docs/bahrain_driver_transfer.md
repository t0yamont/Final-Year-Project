# Bahrain qualifying cross-driver pace check

The current model and the fixed path-replacement candidate each passed **0 of 3** cross-driver cases. The current model missed the second-sector limit on all three laps. The candidate underestimated every lap by 9.268–9.727 s, and all three speed errors exceeded 5 m/s. The frozen transfer promotion criterion was unmet. The existing Bahrain deployment map remains conditional. [Transfer protocol](../configs/bahrain_driver_transfer_protocol.json) · [Metrics](../results/bahrain-driver-transfer-001/metrics.json)

## Scoring design

Driver 22 laps 2, 5 and 13 were all the conditional motion candidates among 17 records from Bahrain 2025 qualifying, meeting 1257 and session 10010. The paired comparison applied one prediction per model to all three laps. Both predictions were frozen before opening transfer observations for scoring. The geometry candidate used only the driver 1 lap 13 XY path and retained the vehicle parameters, DRS schedule, quarter request and battery constraints. Both models used the driver 1 rolling speed of 80.653 m/s and sector fractions 0.329881 and 0.737310. The original car preparation and 551-point normalized-distance comparison were used. [Prediction lock](../results/bahrain-path-candidate-001/locked_predictions.json) · [Original pace inputs](bahrain_pace_inputs.md)

Lap 2's earliest originally cached car sample was 7 ms after the timing start. One four-second OpenF1 archival request returned 17 native rows. The first originally cached timestamp matched one returned row on all six car channels. The scorer added the nine rows preceding that match to lap 2's working input, giving it a native start bracket of −0.273 to +0.007 s. The remaining observed data came from the original cache. The request URL, response SHA-256 and match details are recorded alongside the acquisition receipts. The original bracketing requirement applied to all three laps. [Acquisition provenance](../results/bahrain-driver-transfer-001/metrics.json) · [Scorer](../scripts/score_bahrain_driver_transfer.py)

## Paired scores

Time errors are simulated minus official time. Negative values indicate an early prediction. The current model predicted 89.773 s and sector times 28.727 / 38.292 / 22.754 s. The candidate predicted 82.369 s and sector times 26.524 / 35.118 / 20.727 s.

| Driver 22 lap | Official lap (s) | Model | Lap error (s) | S1 / S2 / S3 error (s) | Speed RMSE (m/s) | Failed criteria |
| ---: | ---: | --- | ---: | --- | ---: | --- |
| 2 | 92.096 | Current | −2.323 | −0.644 / −1.259 / −0.420 | 4.938 | Lap, sector |
| 2 | 92.096 | Candidate | −9.727 | −2.847 / −4.433 / −2.447 | 6.029 | Lap, sector, speed |
| 5 | 91.751 | Current | −1.978 | −0.537 / −1.239 / −0.202 | 4.578 | Sector |
| 5 | 91.751 | Candidate | −9.382 | −2.740 / −4.413 / −2.229 | 5.841 | Lap, sector, speed |
| 13 | 91.637 | Current | −1.864 | −0.490 / −1.118 / −0.256 | 5.014 | Sector, speed |
| 13 | 91.637 | Candidate | −9.268 | −2.693 / −4.292 / −2.283 | 5.810 | Lap, sector, speed |

Both models passed the 0.25 s refinement and rolling-finish criteria on all three cases. The current and candidate grid differences were 0.120 s and 0.073 s. The candidate was earlier and had greater speed RMSE on all three laps. This comparison covers one driver within an existing development event and a geometry change under fixed vehicle assumptions. Track clearance, surface, fuel, setup and actual deployment remain unverified.

The paired figure shows speed in km/h and accumulated time error in seconds on a common normalized-distance axis scaled to the current model's path length. Dotted lines mark the inferred sector stations from driver 1. All six cases and 30 manifest hashes were independently verified from saved inputs and curves. The supplemental response hash was checked separately. [Paired figure PNG](../figures/dissertation/bahrain-driver-transfer-v1/01_paired_transfer.png) · [Paired figure PDF](../figures/dissertation/bahrain-driver-transfer-v1/01_paired_transfer.pdf) · [Manifest](../results/bahrain-driver-transfer-001/manifest.json)
