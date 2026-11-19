# Longer GPU training study — 12 November 2026

## Predeclared design

This study extends the short pilots to three independent training seeds, each trained from scratch for 16,384 steps on CUDA. It retains the same assumed circuit model, 55 deployment decisions per lap, 70 m/s entry and verified terminal speed, 2 MJ initial energy, 0.1 MJ reserve, and lap-time objective. The accepted 80-cell/block grid is used for training; 160 cells/block is the fine evaluation reference.

The protocol is saved before execution in configs/circuit_multiseed_protocol.json. PPO settings remain fixed: 256 rollout steps, 64 minibatch size, 10 epochs, gamma 1, GAE lambda 0.95, constant learning rate 0.0003 and clip range 0.2, entropy coefficient 0, and two 32-unit hidden layers. Chunked learn calls preserve training state; constant schedules avoid redefining a learning-rate/clip decay horizon at each checkpoint. No hyperparameters are changed after examining these runs.

Deterministic policies are evaluated at 0, 4096, 8192, 12288 and 16384 completed steps, using separate environments and restoring Python, NumPy and Torch CPU/all-CUDA RNG states afterward. The primary endpoint is the final deterministic policy from every seed. No best-checkpoint selection is made. The final policy is also evaluated with five fixed action-noise seeds, each paired across coarse/fine grids from the same evaluation seed. These five rollouts are nested within a training seed; they are not fifteen independent training runs.

The primary summary reports mean, sample standard deviation and range across three training seeds. Stochastic evaluations are averaged within a training seed before summarizing across the three seeds. The small seed count supports descriptive variability, not a significance or convergence claim. All failed runs must remain recorded; a successful study requires all three to complete and pass their final replay checks.

The final numerical gate requires feasible boundaries/reserve/energy balance and no more than 0.05 s difference in time gain against each grid's matching zero-request baseline, for both deterministic and all five paired stochastic evaluations. Action cadence, geometry and vehicle-parameter sensitivity remain subsequent experiments; this is nominal reference-model evidence, not empirical final-test performance.

## Execution and reproducibility

The runner is scripts/train_circuit_multiseed.py. It checks the existing numerical and controller evidence, including input/source/output hashes, and requires CUDA. Each worker uses one Torch CPU thread plus its own CUDA context. Up to three independent workers run concurrently; runtime observations are operational telemetry rather than CPU/GPU speed benchmarks. The geometry is cached in each worker's memory; source telemetry is not fetched or read. Final-test events remain protected.

The implementation passes 123 tests, including evaluation RNG restoration after exceptions, identical paired draws, CUDA RNG restoration and correct seed-level descriptive summaries. A focused review identified the schedule/RNG/nested-replication issues; the fixed design addresses them.

Each seed saves checkpoints, separate coarse/fine replay traces, progress, metrics, device evidence and hashes. The coordinator records worker PIDs/status and aggregates all seeds. The original pilot code and experiment outputs remain unchanged.

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe scripts/train_circuit_multiseed.py --output results/circuit-multiseed-NEW
.venv/Scripts/python.exe scripts/plot_circuit_multiseed.py --input results/circuit-multiseed-NEW --output figures/dissertation/circuit-multiseed-NEW
```

Use new output folders. Keep sources/configuration unchanged while workers are active: completed runs reject changed source hashes. A checkpoint contains policy/optimizer state but is not by itself an exact mid-episode training restart, so this runner does not claim bit-exact crash resumption.

## Completed results

All three seeds completed 16,384 GPU training steps (49,152 total). CUDA policy parameters, gradients and Adam moments were verified at each trained checkpoint; all final deterministic and paired stochastic replay gates passed. Final checkpoint reloads reproduced their saved evaluation metrics exactly. No jobs remain active.

| Training seed | Final deterministic lap (s) | Saving versus full request (s) | Mean of five stochastic laps (s) |
| --- | ---: | ---: | ---: |
| 0 | 108.244916 | 0.363191 | 108.340518 |
| 1 | 108.186268 | 0.421838 | 108.293116 |
| 2 | 108.283990 | 0.324116 | 108.298598 |

Across training seeds, final deterministic lap time is **108.238391 s**, sample SD **0.049187 s**, range **108.186268-108.283990 s**. The strongest fixed baseline under the same 55-decision interface is full request at **108.608107 s**; PPO's mean advantage is **0.369715 s**. Every final deterministic seed beats all five fixed baselines. Saving against zero request is **1.236815 s** on average. All final deterministic runs reach the 0.1 MJ battery reserve without violating it.

The mean of the three within-seed stochastic means is **108.310744 s**, with sample SD **0.025930 s** across those three means. This describes action-sampling variability separately from training-seed variability. The fifteen stochastic rollouts are not independent trained models. The maximum final coarse/fine gain discrepancy across deterministic and stochastic evaluations is **0.010118 s**, below the predeclared 0.05 s threshold.

The 4,096-step checkpoint of seed 0 exactly reproduces the earlier GPU pilot's 109.415539 s fine lap, while longer training improves all three seeds. This supports extending the learning budget; it does not isolate a CPU/GPU effect. The checkpoint curves do not establish convergence or optimality.

## Verification and figures

The integrated suite passed 123 tests. Independent artifact verification checked 66 replay traces and 116 hashes, including global mechanical work-energy balance, electrical energy accounting, reward telescoping, final constraints, paired gain discrepancies and seed-level summaries. The largest absolute global work-energy residual was 7.45e-8 J (rounded upward). Evidence: logs/agent_tools/2026-11-12/multiseed_tests.txt and multiseed_independent_verification.json.

Two figure pairs are saved as 300 dpi PNG and vector PDF in figures/dissertation/circuit-multiseed-v1. Both PNGs were visually inspected for labels, scales, legends and clipping; figure input/output and plotting-source hashes were checked.

- 01_checkpoint_baseline_comparison: fine-grid deterministic checkpoint curves and final performance against matched fixed baselines. Error bars show one sample SD across three training seeds, not confidence intervals.
- 02_stochastic_deterministic_energy: five sampled-action rollouts and the deterministic policy per seed, with terminal simulated battery energy and the reserve. The battery axis includes the initial 2 MJ scale.

Run artifacts: results/circuit-multiseed-001. Recheck with `.venv/Scripts/python.exe scripts/verify_circuit_multiseed.py --input results/circuit-multiseed-001 --output logs/agent_tools/2026-11-12/multiseed_recheck_NEW.json`, using a new output filename. Preserve all pilot and completed-run artifacts.

## Interpretation and next gate

This study provides repeatable nominal reference-model evidence that the learned deployment policy improves on the selected fixed baselines. Three seeds support a descriptive finding, not statistical significance, generalization to real F1 cars or a continuous optimum. Geometry, vehicle parameters and the fixed scenario remain assumptions; no final-test telemetry was used.

Next, predeclare the 55/110-decision cadence comparison and vehicle/geometry sensitivity cases before running them. Keep physical resolution, initial energy, entry/terminal conditions and baseline comparisons matched; distinguish unchanged-policy transfer from retraining at a different cadence. Report feasibility, gain against each scenario's strongest fixed baseline, variability across all training seeds and numerical refinement checks. These experiments will determine how robust the nominal advantage is before dissertation conclusions are finalized.
