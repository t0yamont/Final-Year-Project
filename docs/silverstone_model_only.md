# Silverstone deployment and braking recovery in the simulator

The bounded planner completed the modelled lap **0.639 s faster than adaptive spread at matched wheel work** on the primary grid. The finer grid gave 0.640 s. The same twelve learned policies that missed the original Bahrain finish target all completed this Silverstone case. Its rolling start and finish speed was 56 m/s, which the vehicle could maintain even with electrical assist switched off. This makes finish feasibility substantially easier than in the Bahrain experiment. [Protocol](../configs/silverstone_model_only.json) · [Results](../results/silverstone-model-only-001/metrics.json)

## Why the rolling speed changed

Silverstone was selected from the qualifying braking screen. The official layout registered successfully, but the inherited Bahrain model missed the observed pace and its 80.65 m/s finish target was physically unreachable under its own corner speed and power constraints. Those failures remain the outcome of the original transfer. For this separate simulation the experiment kept the circuit, DRS assumptions, grip, mass, power, brake recovery, starting charge and reserve. It tested integer speeds in descending order and selected the highest at which a zero-assist lap met the finish test on all three integration grids. This rule used the simulator alone and was fixed before searching schedules or scoring learned policies. [Original diagnosis](transfer_circuit_geometry.md) · [Rolling-speed trials](../results/silverstone-model-only-001/rolling_speed.json)

## Where the benefit arose

On the 320-cell grid the planner supplied **380 kJ** in the opening 214 m at an average **120 kW**. Its largest deployment window, 855–1,489 m from the registered line, delivered **861 kJ** at a mean 65.3 kW. The battery recovered **271 kJ** within that same window as the car alternated between braking and propulsion. The strongest single recovery block returned 131 kJ between 5,440 and 5,544 m. These are simulated distance intervals and wheel-side deployment values. Only the battery-side recovery values include charging losses. [Distance profiles](../results/silverstone-model-only-001/distance_profiles_320.csv) · [Requested and delivered power, recovery and stored energy](../figures/dissertation/silverstone-model-only-v1/01_silverstone_dp_energy.pdf)

| Cells per block | Planner lap (s) | Matched spread lap (s) | Spread minus planner wheel work (kJ) | Time saved (s) |
|---:|---:|---:|---:|---:|
| 160 | 91.7890 | 92.4276 | −0.025 | 0.6387 |
| 320 | 91.6991 | 92.3396 | +0.466 | 0.6405 |

The spread multiplier of 1.3984375 was chosen on the primary grid and carried unchanged to the fine grid. The work difference stayed below 500 J and the time advantage changed by 1.82 ms against a 5 ms tolerance. At the fine resolution the planner recovered 1.359 MJ and matched spread recovered 1.371 MJ. The faster schedule thus recovered slightly less energy while delivering almost identical total wheel work. Ordinary, unscaled spread used less wheel work and took 92.525 s on the primary grid. [Multiplier scan and all trials](../results/silverstone-model-only-001/work_match/metrics.json)

## Transfer of the Bahrain policies

| Controller | Feasible on both grids | Mean primary lap (s) | Primary range across seeds (s) |
|---|---:|---:|---:|
| PPO 64 | 3/3 | 92.171 | 92.106–92.233 |
| SAC 64 | 3/3 | 92.262 | 92.256–92.265 |
| PPO 256 | 3/3 | 92.161 | 92.136–92.178 |
| SAC 256 | 3/3 | 92.257 | 92.246–92.265 |

All twelve final checkpoints used the same eight observations and received no training on Silverstone. Every learned policy beat ordinary spread and finished behind the circuit-specific planner. PPO was faster than SAC in all six same-width, same-seed comparisons on both grids. Widening PPO saved 9 ms on average, but two of three seeds became slower on the primary grid. Widening SAC saved about 6 ms on average. These are descriptive outcomes for three seeds and a single assumed vehicle. Methods can use different amounts of wheel work. The controlled allocation result is the planner comparison in the table above. [All paired checks](../results/silverstone-model-only-report-001/comparison.json) · [Learned and baseline traces by distance](../figures/dissertation/silverstone-controller-comparison-v1/01_controller_comparison.pdf)

## Reproduction

Independent checks verified 105 source, input and output hashes and audited both matched-spread traces. Repeating all 24 learned laps with CUDA inference preserved every feasibility decision. The largest lap-time change relative to CPU inference was 0.0000000242 s. Final speed differences of order 10⁻¹⁴ m/s in the plot are floating-point rounding. [Verification record](../logs/agent_tools/2026-11-20/silverstone_controller_verification.json)

The primary study used GPU-trained Bahrain checkpoints and deterministic CPU inference on Silverstone. The independent verifier loads the checkpoints on CUDA, compares predictions against saved actions, and reruns the 24 learned laps on the same physical model. From the repository root use the project environment and `PYTHONPATH=src;scripts`.

```powershell
.\.venv\Scripts\python.exe scripts/verify_silverstone_model_only.py results/silverstone-model-only-001
```

The transfer results support a comparison of modelled strategies at the declared rolling speed. An empirical claim about British qualifying requires a separately supported final-corner and timing-line speed profile, followed by a test on fresh laps. [Silverstone geometry and pace checks](transfer_circuit_geometry.md)
