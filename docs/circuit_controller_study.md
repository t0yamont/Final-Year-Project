# Full-circuit controller study — 11 November 2026

## Interface and controlled comparison

`src/f1energy/circuit_control.py` supplies a Gymnasium environment around the accepted event solver. Each lap has 55 fixed action blocks, with exact shared boundaries in the geometry parameter across numerical grids. Deployment requests lie in [0,1] and are held over a block. The observation contains lap progress, speed, usable battery fraction, local speed cap and braking-envelope minima over the next one/two blocks. No measured battery or deployment labels are used.

All policies start at 70 m/s with 2 MJ battery and a 0.1 MJ reserve. A common 70 m/s terminal cap is propagated backward with the same drag/friction law. Terminal equality is checked after replay; it is not enforced by clipping or by separately adjusting each policy's start speed. The present reported policies all attain that equality. These are single finite-energy rolling laps, not a charge-sustaining race simulation.

For training, each reward is the zero-request reference block duration minus the actual duration. At gamma=1 the sum is exactly the reference lap time minus actual lap time. The reference times are fixed per grid, not recalculated from each policy's state. Feasibility remains enforced by the event solver. Infeasible entry, invalid actions and calls after termination are rejected.

## Baselines and numerical gate

The study protocol in `configs/circuit_controller_study.json` was declared before running. It compares zero, half and full requests; a remaining-energy/estimated-time spreading heuristic; and a corner-exit heuristic that requests power below 55 m/s when the next-block braking envelope permits at least the current speed. These heuristics are simple comparators, not optimization references.

Twenty-five rollouts cover five policies, four integration grids and a doubled action cadence. At 55 blocks/lap, each block contains 20, 40, 80 or 160 cells, giving approximately 4.914, 2.457, 1.229 or 0.614 m parameter spacing. All grids share action locations. For each candidate training grid, the preset checks require feasible replay, at most 0.5% lap-time difference, at most 0.05 s error in gain versus zero request, and preserved pairwise ranking for fine-grid separations above 0.02 s.

| Cells per action block | Maximum relative lap-time error | Maximum time-gain error | Ranking preserved | Accepted |
|---:|---:|---:|---|---|
|20|2.336%|0.21424 s|No|No|
|40|1.022%|0.00913 s|Yes|No|
|80|0.351%|0.00309 s|Yes|Yes|
|160|Reference|Reference|Yes|Yes|

The 80-cell grid is selected for the bounded pilot. Baseline runtime is approximately 1.89–2.27 s per lap on the current CPU setup; this is a local timing observation, not a hardware benchmark. The installed PyTorch build is CPU-only. This small network and CPU event solver run locally without changing dependencies.

Fine-grid results at 55 decisions/lap:

| Policy | Lap time (s) |
|---|---:|
|Zero|109.475206|
|Half|108.643983|
|Full|108.608107|
|Spread|108.679327|
|Corner-exit boost|108.628191|

At 110 decisions on exactly the same fine geometry grid, zero/half/full are unchanged, spread gives 108.661812 s and corner-exit boost 108.396342 s. The latter improves by 0.231849 s. Thus policy decision cadence is material, and this experiment does not claim action-resolution convergence or a continuous optimum. Main pilot comparisons retain 55 decisions for every policy.

Results: `results/circuit-control-baselines-001`. Figure PNG/PDF: `figures/dissertation/circuit-control-baselines-v1`. The figure was visually inspected. Independent arithmetic checks cover all 25 rollouts' kinetic/work balance, battery identity, durations, terminal speed and reserve; 38 artifact/source/input hashes were verified.

## Training authorization and verification

The user has authorized local training and accepts the model-based dissertation scope. The prior telemetry assessment is documented in observable_motion_validation.md; it does not establish real-car lap-time accuracy. Geometry smoothing, independent lateral/longitudinal limits and the assumed power split remain explicit limitations.

The expanded existing suite passes 113 tests, including four controller-interface tests for aligned action boundaries, energy/reward identities, depletion, replay determinism, invalid actions and the Gym API. Four additional training-gate tests pass separately, for 117 passing tests across those runs. A focused review found that nested numerical input hashes also need checking. The benchmark runner was strengthened after Run001, and `circuit_training_gate.py` verifies both numerical and baseline evidence before any training, including reference configuration, geometry, physical sources and saved result hashes. Original baseline experiment bytes remain unchanged.

The pilot contract is one seed, 4096 steps, 55 decisions/lap, PPO with gamma 1, 256-step batches, 64 minibatch size, 10 epochs and two 32-unit hidden layers. Intermediate checkpoints are saved every 1024 steps. Deterministic replay is required after checkpoint reload and at the 160-cell reference grid. The pilot's numerical replay gate requires feasibility and time-gain disagreement no greater than 0.05 s between training and fine grids. A passed gate does not establish learning convergence or held-out generalization.

Reproduce into fresh destinations from the project root:

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe scripts/benchmark_circuit_control.py --output results/circuit-control-baselines-NEW --figures figures/dissertation/circuit-control-baselines-NEW
.venv/Scripts/python.exe scripts/train_circuit_ppo.py --baselines results/circuit-control-baselines-001 --output results/circuit-ppo-pilot-NEW
```

The next experiment should address multiple seeds, training budget and action cadence, with common fine-grid replay and model-parameter/geometry sensitivity. No final-test telemetry has been read during this controller study.

## Completed PPO pilot

Run results/circuit-ppo-pilot-001 completed all 4,096 steps locally in 131.75 seconds of training. This is the first full-circuit RL pilot; earlier event-model pilots covered short synthetic segments. Seed 0 and its initial/final policy and four intermediate checkpoints are retained. Thirteen parameter tensors changed, with maximum absolute change 0.18866. Reloaded deterministic rollout matches the original exactly.

The deterministic training-grid lap improves from 109.855022 s before training to 109.229686 s afterward. Fine-grid replay gives 108.849138 s: a 0.626068 s gain versus zero request, but 0.241032 s slower than the full-request baseline. It also remains slower than the other three nonzero baselines. The policy finishes with 0.954526 MJ, including 0.854526 MJ above reserve; the short run underuses the available budget. Stochastic training episode rewards should not be substituted for the deterministic comparison or treated as independent validation samples.

The trained policy passes the numerical replay gate. Its gain differs by 0.000576 s between training and fine grids, terminal-speed error is below 1e-12 m/s, and independent whole-lap work-energy residual is below 3.2e-8 J. All reserve and boundary checks pass. Independent verification covered three saved policy rollouts, 21 training artifact/input/source hashes, parameter changes, and all four figure-output hashes. No empirical final-test data were accessed.

Dissertation PNG/PDF pairs in figures/dissertation/circuit-ppo-pilot-v1 show the learning trace and fair fine-grid comparison, plus requested deployment, battery and speed at action boundaries. Both figures were visually inspected. Logs and verification are under logs/agent_tools/2026-11-11/circuit_*.

Next: predeclare a larger multi-seed training budget and evaluation/checkpoint schedule, compare deterministic and stochastic policy behaviour without changing the lap-time objective, then test 55 versus 110 decisions and model sensitivity. Keep every failed or negative comparison. The present pilot establishes a functioning training/replay pipeline; it does not establish convergence or an RL advantage.
