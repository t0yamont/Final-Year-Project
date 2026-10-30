# Shared-physics baseline study — 30 October 2026

The event-based physical-model pipeline now has a bounded dynamic-programming baseline. This completes a useful implementation and validation increment for guide Step10 and RQ2. It does not complete the full qualifying-circuit or empirical evaluation gates. The initial rounded-energy failure and subsequent refinement are retained as evidence about numerical decision sensitivity.

## Method and controls

The finite-horizon Bellman state comprises physical segment index, usable-energy bin and exact reachable speed. Each action invokes the same event-based transition used in the PPO environment. Time is additive cost, distance follows segment index, and energy is floored relative to the reserve. Speed is never interpolated or replaced with a target cap. The selected action sequence is then replayed from the original unrounded state. This distinguishes the rounded optimisation objective from the feasible physical result; neither an upper-bound assertion nor a continuous optimum is assumed.

An exact finite-action enumeration supplies a small independent algorithmic reference. It shares the simulator deliberately, so its agreement validates optimisation over the stated action set, not real-world dynamics. Numerical validity is supported separately by event-validation-002, dense braking-envelope/reserve checks and tighter integration of each selected exhaustive policy. Maximum standard/tighter elapsed-time discrepancy across the three cases was3.57e-9s, below the predeclared1e-5s criterion. Work residuals were below1e-9J in those standard replays. All listed policies satisfy the declared constraints.

The physics reviewer identified two implementation risks before accepted runs: a DP result could be returned with a failed replay flag, and mutable cache settings could misidentify old transitions. Both were repaired and covered by regression tests. Solver errors propagate; only physically infeasible braking entries are pruned explicitly. Failed policies cannot become empty successful optima. Exact speed keys limit merging, so this remains a bounded reachable-state tree rather than a scalable full-circuit DP implementation.

## Results

| Scenario | Reference | Best finite-reference time (s) | Finding |
|---|---|---:|---|
| Nominal two segments | Five actions;25 sequences |20.597676607|All four energy grids select the reference; nine actions do not improve it; PPOseed0 ties|
| Shifted two-segment evaluation | Five actions;25 sequences |21.132915655|5/2.5kJ grids select the reference;20/10kJ do not|
| Shifted evaluation action sensitivity | Nine actions;81 sequences |21.129190409|Improves five-action reference by3.725246ms; continuous-action convergence remains unestablished|
| Four-segment development stress case | Three actions;81 sequences |23.622721769|Initial2.5kJ finest grid fails agreement; documented100J refinement selects[1,0,.5,1] and matches reference|

The shifted evaluation PPO times remain21.137077717/21.214537246/21.192869432s for seeds0/1/2. These are all above the nine-action reference. Policies were loaded from saved action records and replayed under matching source/scenario hashes without retraining, checkpoint selection or tuning. The previously frozen evaluation has now been inspected and must not be described as a future untouched final test. Three short pilot seeds do not establish a population confidence interval.

In the four-segment case,5kJ selected the discrete reference but2.5kJ selected a different policy, losing1.061924ms and failing the unchanged0.1ms threshold. Run001 is therefore rejected overall even though its individual two-segment checks pass. Follow-up grids1/0.5/0.25/0.1kJ were declared after this failure; the100J result agrees. This refinement is an adaptive development study, not independent confirmation. Full deployment took23.705590265s,82.868496ms slower than the finite reference under these synthetic assumptions. No corresponding real-driver improvement is implied.

Run002 contains the successful stress-only numerical refinement. Its generic scope sentence incorrectly referred to three cases; the case payload actually contains one. Run003 corrects that metadata and reproduces the results entirely from verified optimisation transitions, with fresh dense numerical checks. All three runs remain unchanged after creation, with source snapshots and manifests.

## Execution cost, caching and reproducibility

Initial run001 took3.323s for its measured experiment body (excluding startup and final serialization); its nominal/evaluation/stress cases used130/140/321 uncached transitions and222/212/430 cache hits. Run002 loaded321 stress records and computed219 additional transitions. Run003 loaded all540 and used1178 hits with0 new optimisation transitions; dense verification still ran, so this is not a zero-compute run. Timings depend on cache warmth and are not valid independent comparisons of algorithm hardware speed.

Saved caches are scoped to complete scenario and immutable solver settings. Reuse checks current event/power/scenario-definition source hashes and cache-file hashes before loading. Run artifacts also include exact before-run source hashes, source copies, environment versions, validation evidence and input/output hashes. Historical PPO results were hash-checked, their scenarios matched explicitly and recorded action replays reproduced elapsed times within1e-8s. No remote data was fetched this cycle.

Commands, run diagnostics and integrity reports are saved under logs/agent_tools/2026-10-30. The first test invocation lacked PYTHONPATH and failed import; that log was retained. Corrected invocation with PYTHONPATH=src passed the focused tests. After implementation/review/cache changes the integrated suite passed84 tests. All36 outputs across the three new run directories and the three-figure set passed SHA-256 verification. The earlier seven-directory validation/PPO/figure audit also passed.

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
# Choose fresh output directories; never overwrite the preserved run IDs.
.\.venv\Scripts\python.exe scripts/benchmark_event_baselines.py --output results/event-baselines-reproduction-001
.\.venv\Scripts\python.exe scripts/benchmark_event_baselines.py --output results/event-baselines-reproduction-002 --refine-stress --reuse-run results/event-baselines-reproduction-001
.\.venv\Scripts\python.exe scripts/plot_event_baselines.py --output figures/dissertation/event-baselines-v2
```

The plotting command deliberately reads the canonical preserved001/003 evidence, not arbitrary new reproduction runs. Three new figures show shared-physics controller comparisons, energy refinement including the negative result, and selected action schedules. Captions distinguish requested actions from actual power after depletion/braking. PNG300dpi and vectorPDF outputs were visually inspected. The figure register now identifies13 selected figure pairs overall.

## Remaining gates and AI contribution

Action discretisation still changes the shifted reference, so finite energy-grid agreement alone cannot justify a continuous optimum claim. A richer PPO benchmark requires a frozen scenario set, action sensitivity, fair tuned heuristics and stable numerical constraints. Real circuit/profile provenance, independent event-level test roles and defensible forward calibration remain prerequisites to empirical claims. Preserve the earlier mass/base-power ambiguity and telemetry-quality limits.

AI implemented the bounded controller/cache, reviewed numerical design with one specialist, ran local verification and produced plots/documentation. It did not author student reflection or invent ethics approval. The user's new cost preference is recorded in agent_execution_policy.md; agent briefs and saved evidence are intentionally compact.
