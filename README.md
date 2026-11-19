# COM3001: F1 energy deployment

A model-based dissertation comparing electrical-energy deployment policies for a simulated qualifying lap, supported by public telemetry, numerical validation and reproducible experiments. Simulated battery trajectories are not measured F1 battery data.

**Where should the car deploy its energy at Bahrain?** The calibrated simulation found seven recurring stretches and measured the cost of moving deployment earlier or later. The timing-line straight has the closest local speed agreement with the two separate qualifying laps. [Deployment map and results](docs/bahrain_deployment_zones.md) · [Matching simulated and observed pace](docs/bahrain_qualifying_pace.md) · [Local speed agreement by zone](figures/dissertation/bahrain-zone-support-v1/zone_motion_support.pdf)

The whole-lap check on the second Red Bull driver exposed a persistent sector-two error. Replacing the entire centreline with one lap's recorded positions worsened the prediction. [Driving-line experiment](docs/bahrain_path_candidate.md) · [Cross-driver qualifying check](docs/bahrain_driver_transfer.md)

Holding delivered electrical work equal still gave a **0.871–0.955 s simulated advantage** over spreading it across the lap. Most of the lead accrued in sectors one and two. [Matched-work study](docs/bahrain_equal_work.md) · [Comparison by distance](figures/dissertation/bahrain-equal-work-v1/03_bahrain_matched_by_distance.pdf)

**Start here for writing: [Dissertation guide](docs/DISSERTATION_GUIDE.md).** It maps the research questions, current evidence, figures and code to the essay. [Current status](docs/PROJECT_STATUS.md) records completed work; [agent handoff](docs/agent_handoff.md) is for continuing implementation.

Read the [editable technical dissertation draft](report/Bahrain_deployment_draft.docx) for the complete argument and the [chapter sources](report/outline.md) for editing. A direct transfer check replayed twelve saved neural policies on the same calibrated vehicle as the planner. They all reached the final block at the battery reserve and missed the required finish speed. [Calibrated controller comparison](docs/bahrain_learned_transfer.md)

## Main dissertation results as of 18 November 2026

The [results chapter](report/06_results.md) compares three regenerative PPO policies with fixed controllers and a bounded DP planner on Sakhir. PPO gained 0.193 s on average over full request on the nominal lap. At higher drag, all three PPO policies missed the finish-speed target. The empirical chapters cover [deployment ambiguity on Bahrain speed windows](docs/bounded_real_reconstruction.md) and [the final qualifying prediction in Abu Dhabi](docs/session_mix_study.md). The [figure register](docs/figures.md) links the relevant PNG and PDF directories.

## Regeneration update - 17 November 2026

Brake MGU-K regeneration is now in scope. Read [the regeneration study](docs/regeneration_study.md) for the physical assumptions, sourced bounds, eight-value observation contract and new validation evidence. The earlier studies below retain their original deployment-only conditions. Existing six-value policies and source-hash training gates do not transfer automatically to the changed model; fresh numerical and controller evidence must precede new CUDA training.

## Historical deployment-only position - 13 November 2026

The full-circuit curvature/braking/event model, fixed-policy baselines and three-seed GPU PPO study are complete. Final deterministic PPO laps average **108.238391 s** (sample SD **0.049187 s**, three seeds), improving on the strongest matched fixed baseline by **0.369715 s**. All final replay gates passed. This is a result on the assumed reference model, not a real-driver comparison or proof of optimality. See [the study](docs/circuit_multiseed_study.md).

The [unchanged-policy sensitivity study](docs/circuit_sensitivity_study.md) is also complete: 160 evaluations, nine of ten cases accepted. Higher drag causes a terminal-speed failure; stronger smoothing and changed cadence reduce the advantage. A [common terminal-reserve guard](docs/terminal_guard_study.md) now passes all 64 replays on nominal/high-drag models at 55/110 decisions. At55 decisions, PPO+guard beats matched guarded baselines by 0.227/0.214 s, with a 0.141 s nominal cost versus unguarded PPO. Final-test telemetry remains reserved. Full-circuit DP comparison, remaining research questions and final dissertation writing are not complete.

## Work locally

Use the existing project virtual environment. Neural-network training requires CUDA and fails if CUDA is unavailable; physics simulation remains on the CPU. GPU execution details and installation evidence are in [GPU training](docs/gpu_training.md). `environment-gpu-lock.txt` records the current environment; `environment-lock.txt` preserves the older CPU environment.

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/train_circuit_multiseed.py --help
```

The pre-regeneration integrated suite passed 133 tests; current verification is recorded in the regeneration study. Use new output folders for experiments. Historical results and manifests must remain unchanged. Training validates its input/source hashes before running; commands and design are in each study report.

## What to read

| Folder | Purpose | Reading priority |
| --- | --- | --- |
| `docs` | Methods, decisions, results and limitations | Start with the dissertation guide |
| `src/f1energy` | Physics, control environment, data preparation and diagnostics | Follow the guide's code map |
| `scripts` | Reproducible study entry points and plotting | Read the entry point for the relevant result |
| `configs` | Declared models, protocols and protected data roles | Cite assumptions and frozen designs |
| `figures/dissertation` | PNG/PDF figures and provenance | Use the guide's selected current figure sets |
| `results` | Immutable evidence, traces, checkpoints and manifests | Inspect metrics when substantiating a claim |
| `tests` | Numerical, data and training-gate tests | Evidence of software verification |
| `report` | Essay outline, related-work draft and bibliography | Working drafts, not a completed dissertation |
| `learning` | Small educational exercises | Optional; not production experiments |
| `logs/agent_tools` | Compact execution and verification records | Audit support |
| `work`, `.venv`, `.git` | Local source caches, dependencies and version history | Not an essay reading path |

Older pilots, failed numerical studies and superseded figures are retained as historical evidence. Do not mix their lap times with current results as if conditions were identical. Local raw/authenticated caches and credentials are excluded from publication; see [publication notes](docs/publication.md).

## Remaining research

The terminal guard passed its bounded deployment-only validation. Establish regeneration numerical and matched-controller evidence before new CUDA training, then establish the full-circuit optimisation-reference comparison and the remaining supported research questions, complete protected evaluation where applicable, and write the final methods/results/discussion chapters. Scope and optional extensions are recorded in [research scope](docs/scope.md). Student reflection and institutional evidence must come from the student and institution.
