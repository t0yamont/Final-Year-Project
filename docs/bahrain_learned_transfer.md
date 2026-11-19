# Archived controller transfer to the calibrated Bahrain model

**None of the 12 archived policies finished feasibly on either evaluation grid.** All reached the last action span at the 100 kJ battery reserve and delivered zero assist there. On the primary grid they missed the 80.653 m/s target by 0.847–1.009 m/s. Both archived comparators finished feasibly. The transfer supplies evidence about terminal energy allocation on this model, with no feasible learned lap-time comparison. [Run metrics](../results/bahrain-learned-transfer-001/metrics.json)

The experiment evaluates all final archived PPO and supervised imitation controllers on the frozen central Bahrain qualifying model. It uses the 12-model cohort formed by two methods, hidden widths 32 and 64, and all three original training seeds. PPO checkpoints are the final 16,384-step models. Imitators are the final 500-epoch regressors trained to reproduce bounded DP requests on four reference-vehicle cases. No checkpoints, actions or epochs were selected by results in Bahrain. [Frozen protocol](../configs/bahrain_learned_transfer.json) · [PPO width study](ppo_actor_width.md) · [Imitation training study](regeneration_imitation_pilot.md)

## Design

Each checkpoint issued 55 deterministic deployment requests in closed loop. Inference used the unchanged eight-value observation interface and the original PPO deterministic prediction or the imitation regressor's output clipped to [0, 1]. No guard, parameter adjustment, new data or training was used. Each checkpoint was evaluated once at 160 cells per action span and once at 320, for 8,800 and 17,600 cells per lap. The saved central selected schedule and ordinary adaptive spread traces supply the two same-grid references. Their wheel work differs. [Parent deployment study](bahrain_deployment_zones.md)

The original policies used the reference vehicle and its geometry origin. The target used the registered timing line, fitted effective base power, brakes, lateral grip and speed-dependent aero terms, a prescribed DRS drag pattern and a common start and finish speed of 80.653 m/s instead of 70 m/s. The target retained the same MGU-K limits, starting energy of 2 MJ and battery reserve of 0.1 MJ. Shifts in the observed speeds, look-ahead caps and position relative to the timing line can all matter. The test does not isolate their individual effects. [Reference vehicle](../configs/circuit_reference.json) · [Frozen Bahrain model](../results/bahrain-pace-calibration-001/model.json)

Physical feasibility requires a complete lap, an absolute finish-speed error below 10⁻⁵ m/s, and agreement with speed-cap, reserve, battery-capacity, recovery and deployment limits and work balances. The independent audit recomputes mechanical and battery identities and checks delivered work against requested power. Infeasible trajectories remain in the set of reported outcomes. A time saving is defined only when both compared policies finished feasibly on the same grid. The predeclared refinement limits are 0.25% for each lap time, 10 kJ for terminal energy, 5 kJ for recovered energy and 5 ms for the change in a paired time saving. A resolved direction additionally requires the same nonzero sign on both grids. Cross-method seed labels identify archived runs with different training objectives and experience. Their time comparisons are descriptive.

## Results

Every learned replay completed all 55 action spans. The independent checks reproduced its reserve, work and battery balances. The failure was the speed requirement. The deficits below are in m/s, with the 160-cell value followed by the 320-cell value for each seed.

| Archived policy | Seed 0 | Seed 1 | Seed 2 |
|---|---:|---:|---:|
| PPO, width 32 | 0.847 / 0.839 | 0.983 / 0.974 | 0.992 / 0.983 |
| PPO, width 64 | 0.850 / 0.843 | 0.850 / 0.843 | 1.009 / 1.001 |
| Imitation, width 32 | 0.905 / 0.896 | 0.931 / 0.923 | 0.907 / 0.899 |
| Imitation, width 64 | 0.886 / 0.878 | 0.934 / 0.926 | 0.907 / 0.899 |

All 12 individual grid changes fell within the numerical thresholds. The maximum relative lap-time change was 0.1348%, the maximum terminal-energy change was 0 kJ, and the maximum recovered-energy change was 1.755 kJ. Both grids reproduced each finish miss. The 36 pairs involving a learned policy have no feasible time saving on either grid. The selected schedule beat adaptive spread by 0.990 s at 160 cells and 0.988 s at 320, a 1.72 ms change in the gap. [Paired comparisons and grid checks](../results/bahrain-learned-transfer-001/metrics.json)

### Deployment by distance

At 393 m on the timing-line straight, all six imitation policies had delivered 472–515 kJ, compared with 469 kJ for the selected schedule and 123 kJ for spread. PPO ranged from 213 to 530 kJ. At 1,172 m, just beyond the selected T1–T3 deployment window, imitation had used 1.303–1.408 MJ and PPO 0.997–1.574 MJ, compared with 1.295 MJ for the selected schedule and 0.327 MJ for spread. These primary-grid totals track where assist was delivered at unequal work. The separate matched-work study estimates the timing effect for the two reference families. [Distance profiles](../results/bahrain-learned-transfer-001/deployment_by_distance.csv) · [Matched-work study](bahrain_equal_work.md)

Over the full primary-grid lap, learned trajectories delivered 3.058–3.068 MJ, compared with 3.050 MJ for the selected schedule and 2.989 MJ for spread. The final 5,274–5,373 m span shows the scheduling difference. All six imitation policies requested 13.9–56.1 kW. Three PPO policies requested zero and three requested 120 kW. All twelve had only the 100 kJ reserve at entry and delivered zero wheel work on that span. The selected schedule entered with 152.4 kJ, requested 120 kW and delivered 47.1 kJ (37.8 kW mean). Spread entered with 312.1 kJ, requested 120 kW and delivered 123.9 kJ (104.9 kW mean). On the finer grid all twelve policies again entered at the reserve and delivered zero final-span work. [Block-level profiles](../results/bahrain-learned-transfer-001/deployment_by_distance.csv)

The archived policies lost terminal feasibility after the model change despite delivering slightly more total wheel work than both references. Performance after training or adaptation on this model remains unmeasured. The Bahrain pace calibration failed its overall separate-lap gate, so all deployment and terminal-feasibility findings remain conditional on the frozen centreline model. [Calibration results](bahrain_qualifying_pace.md)

**Figure 1.** Finish-speed error by archived seed and grid, with the feasible time comparison left unavailable for every failed transfer. The four lower panels show cumulative delivered wheel work minus the selected schedule at 160 cells per action span. The shared vertical scale allows direct comparison between methods and widths. Turn labels are approximate. [PDF](../figures/dissertation/bahrain-learned-transfer-v1/01_bahrain_learned_transfer.pdf) · [300 dpi PNG](../figures/dissertation/bahrain-learned-transfer-v1/01_bahrain_learned_transfer.png)

## Reproduction and artifacts

From the repository root, use the project environment to generate a fresh run, or verify the saved artifacts with hashes and independent replay checks:

~~~powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe scripts/evaluate_bahrain_learned_transfer.py --output results/bahrain-learned-transfer-NEW --figures figures/dissertation/bahrain-learned-transfer-NEW
.venv/Scripts/python.exe scripts/evaluate_bahrain_learned_transfer.py --verify
~~~

The archives contain 24 policy traces with pre-action observations. The distance CSV includes both references and every learned policy at both grids. Its block endpoints give distance from the timing line, power requested, mean assist delivered, wheel work and time, speed and battery energy. The manifest binds the model, baseline laps, final checkpoint files, code, protocol, metrics and figures. [Run manifest](../results/bahrain-learned-transfer-001/manifest.json) · [Distance profiles](../results/bahrain-learned-transfer-001/deployment_by_distance.csv) · [Evaluation script](../scripts/evaluate_bahrain_learned_transfer.py)

An independent action audit reproduced all 1,320 requests from the saved observations and original CUDA checkpoints, and reconciled all 1,540 distance records. [Independent audit](../logs/agent_tools/2026-11-19/bahrain_policy_action_audit.json)
