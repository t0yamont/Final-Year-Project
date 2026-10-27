# COM3001: F1 energy deployment

This repository starts a reproducible study of plausible electrical deployment inferred from incomplete public telemetry, followed by a controlled simulator comparison of DP, heuristics and PPO. No real telemetry has been collected and no model has been trained by this initial implementation.

The implemented software is a small **synthetic analytic straight-line fixture**, strict JSON configuration, a provenance-writing CLI and a separate discrete DP learning exercise. It is not the eventual racing simulator, and its output does not answer the research questions. Research scope, evidence and task status are maintained in `docs/`.

## Run the offline foundation on Windows

Open PowerShell in the repository root. A normal working Python 3.11+ installation can replace the bundled path below. On this machine the ordinary `python` command resolves to an unusable Windows app alias; the bundled Python was confirmed as 3.12.14.

```powershell
$python = 'C:\Users\monti\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $python -m venv .venv
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
& $python -m f1energy.cli --help
& $python -m unittest discover -s tests -v
& $python -m f1energy.cli verify --config configs/toy.json --output results/manual-smoke-001
& $python learning/energy_allocation.py
```

Use a new output directory for every run. Existing directories are rejected to preserve evidence. The CLI writes the exact configuration, trajectory CSV, summary JSON and manifest with SHA-256 hashes, software versions, seed and source revision where available. `PYTHONPATH` supports running from source without installing any packages or fetching a build backend. The `pyproject.toml` also defines standard packaging metadata; a wheel/editable install is not required for the demonstrated workflow.

The fixture uses SI units in explicit field names. Its values are arbitrary teaching assumptions, not regulatory values or estimates of an F1 car. It has no drag, traction cap, corners, braking, harvesting or depletion projection. It rejects an energy-infeasible request. These omissions are recorded in `docs/implementation.md` and must be resolved before production simulator claims.

## Current and planned capabilities

Only `verify` is implemented in the CLI. Ingestion, track preparation, reconstruction, physical baselines, Gymnasium, PPO training and evaluation remain planned. The guide's proposed commands are not promises that those features already exist. Heavy training and large data acquisition are reserved for manual execution by the student once tested scripts, exact commands, budgets and return artifacts have been prepared.

`requirements-core.txt` records that the foundation has no external runtime dependencies. Compatible scientific/ML versions and their exact lock will be established only when those stages are implemented and imported successfully in a dedicated environment. No speculative dependency versions have been presented as tested.

For the research argument, retain the distinction between measured telemetry, reconstructed hidden quantities and simulated optimised actions. A synthetic time reduction cannot establish a real-driver improvement.
