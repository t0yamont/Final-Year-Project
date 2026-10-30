# COM3001: F1 energy deployment

A dissertation research pipeline for reconstructing plausible electrical deployment from incomplete Formula One telemetry and comparing PPO, dynamic programming and practical heuristics in a shared simulator.

## Current position — 30 October 2026

The project includes a bounded telemetry audit, an event-based power/drag/braking simulator, diagnostic calibration and inverse-identifiability experiments, finite-action DP/exhaustive baselines, and three independently seeded physical-model PPO pilots. **84 automated tests pass.** There are **13 selected dissertation figures**, each saved as PNG300dpi and vectorPDF with captions and provenance.

These are predominantly **synthetic development results**. Public telemetry contains no verified electrical-power or battery labels. The real-data fit is diagnostic and does not establish a calibrated F1 car. A simulated time reduction is not evidence of improvement over a real driver. Bahrain2025Q and inspected synthetic evaluation cases cannot be reused as untouched final tests.

- [Current status](docs/PROJECT_STATUS.md) and [compact continuation handoff](docs/agent_handoff.md)
- [Dissertation figure index](figures/dissertation/README.md)
- [Latest DP/PPO comparison and limitations](docs/event_baseline_results.md)
- [Event-solver numerical protocol](docs/event_validation_protocol.md) and [PPO pilot record](docs/event_training.md)
- [Research scope](docs/scope.md), [workflow](docs/WORKFLOW.md), [guide-step status](docs/guide_step_status.md)

## Run locally

The tested research environment uses Python3.12 on Windows, with CPU PyTorch for the small pilot networks. Exact installed package versions are in environment-lock.txt; immutable training runs retain their own locks. A fresh-machine installation has not yet been certified.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r environment-lock.txt --extra-index-url https://download.pytorch.org/whl/cpu
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m f1energy.cli --help
```

The original requirements-core.txt describes only the standard-library foundation; environment-lock.txt records the current scientific environment. Use the project virtual environment and set PYTHONPATH=src when running from the checkout. An editable package installation is not required.

## Reproduce bounded experiments

Use a fresh output directory for each run. Original artifacts are immutable, including failed numerical studies. Training checks that its validation report and simulator source hashes still match.

```powershell
.\.venv\Scripts\python.exe scripts/validate_event_solver.py --output results/event-validation-reproduction-001
.\.venv\Scripts\python.exe scripts/benchmark_event_baselines.py --output results/event-baselines-reproduction-001
.\.venv\Scripts\python.exe scripts/benchmark_event_baselines.py --output results/event-baselines-reproduction-002 --refine-stress --reuse-run results/event-baselines-reproduction-001
.\.venv\Scripts\python.exe scripts/plot_event_baselines.py --output figures/dissertation/event-baselines-v2
```

The benchmark defaults to the preserved event-validation-002 report. The plotting script reads canonical event-baselines-001/003 evidence. See the experiment documents for acceptance thresholds, budgets and training commands. Telemetry acquisition requires the user's own permitted access and depends on service availability. No private authentication or FastF1 cache is distributed.

## Repository contents

| Directory | Contents |
|---|---|
| src/f1energy | Data audit, simulator, inverse diagnostics, baselines and RL environments |
| scripts / tests | Reproducible studies, plotting and automated verification |
| configs | Toy configuration and development data roles |
| results | Saved exports, metrics, manifests, source snapshots, pilot checkpoints and logs |
| figures/dissertation | Versioned scientific plots; README selects the current13 figures |
| docs / report / learning | Research record, report drafts and educational exercises |
| logs/agent_tools | Saved command outcomes, integrity checks and concise reviews |

Local virtual environments, bytecode, scratch material, credentials and authenticated HTTP/parsed caches are excluded. Exported research artifacts are included for the requested project snapshot; the existing [ethics/source-permissions register](docs/ethics_status.md) remains the record of unresolved institutional and redistribution questions. Publication asserts no new permission or approval. Original run manifests may reference intentionally omitted caches; see [publication notes](docs/publication.md).

## Remaining work toward the final goal

The target is a defensible, reproducible comparison on one selected qualifying circuit, with conditional deployment reconstruction and uncertainty, plus qualifying-only/mixed-session and optional driving-profile experiments. Next are action-grid convergence and richer validated scenarios, leakage-safe circuit/profile preparation, untouched event-level splits and real forward calibration. Larger PPO experiments and final comparisons follow those gates. Critical literature synthesis, institutional evidence, final report chapters and submission packaging remain in progress.

The coordinator may run authorised local training/validation. Agent cost controls, minimal context and verified cache reuse are in [agent_execution_policy.md](docs/agent_execution_policy.md). This does not schedule unattended work. Student reflection and university approval evidence must come from the student and institution.
