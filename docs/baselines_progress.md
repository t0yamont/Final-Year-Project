# Physical synthetic baselines — 28 October 2026

Implemented backward dynamic programming over segment index, a downward-rounded usable-energy grid and exact reachable speed. The speed state is essential: nominal segment three may not reach its exit cap under zero assistance. An initial energy-only implementation rejected that case during testing; the final version retains speed without discretisation. Exact reachable speeds can cause exponential state growth, so the implementation rejects action-tree sizes above 100,000 leaves. This is a bounded prototype, not a scalable production solver.

The DP Bellman recursion evaluates the shared lap transition, rounds remaining usable energy down, and stores the best finite-action tail. Initial usable energy is also rounded down. Selected actions are then replayed through the original unrounded physical state. The grid objective and replay time are stored separately: rounding loss is computational conservatism, not actual battery dissipation. No claim of monotonic convergence for every scenario, continuous-action optimality or real F1 validity is made.

## Executed nominal benchmark

Saved results/synthetic-baselines-001/metrics.json and manifest.json. Actions are {0, 0.5, 1}; the independent reference enumerates all 81 four-segment sequences. All runs were feasible under the common transition. Saved PPO checkpoints were read only and their input hashes recorded. The previously held-out scenario was not retuned or evaluated in this benchmark.

| Method | Physical replay seconds | Conservative grid objective seconds |
| --- | ---: | ---: |
| Zero | 28.997142 | — |
| Uniform half | 27.757070 | — |
| Uniform full | 27.761082 | — |
| Exhaustive 81 sequences | 27.651656 | — |
| DP 100,000 J | 27.761082 | 27.810747 |
| DP 50,000 J | 27.732890 | 27.732890 |
| DP 10,000 J | 27.661435 | 27.677454 |
| DP 1,000 J | 27.651656 | 27.652095 |
| DP 100 J | 27.651656 | 27.651780 |
| PPO each of seeds 0, 1, 2 | 27.761082 | — |

At 1,000 J and 100 J, DP selects a sequence matching the finite-action exhaustive optimum on physical replay. PPO is 0.109426 seconds slower on this toy nominal case. This supports the baseline implementation and preserves a negative PPO result; the tiny action grid and four-segment simulator cannot establish dissertation-level controller performance.

Five tests passed before the final safety-bound addition: invalid grids, feasible replay vs exhaustive, one-segment reference, refinement reaching the tiny reference, and variable exit speed support. The coordinator should run combined tests after integration. Run command: set PYTHONPATH=src then `.venv/Scripts/python.exe scripts/benchmark_baselines.py --output results/synthetic-baselines-NEW`. Outputs refuse overwrite.

AI contribution: implementation, failed energy-only assumption discovery, correction, offline tests and bounded nominal benchmark. Next gates: higher-resolution actions, scalable speed/energy discretisation with error checks, proper power-based calibrated dynamics, richer scenarios and matched information comparisons.
