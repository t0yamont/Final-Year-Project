# Data sufficiency and acquisition priorities — 10 November 2026

Update after the user's acceptance of a model-based dissertation: the selected acquisition/training route is in [data_source_options_audit.md](data_source_options_audit.md). OpenF1 access and context endpoints now work locally; new access probes are not yet additional accepted calibration data. The counts below remain the accepted modelling dataset, not the size of all cached source responses.

**Decision: enough for an engineering pilot and an identifiability case study; insufficient for the full proposed empirical conclusions.** Sample count alone cannot resolve unobserved electrical deployment or an inadequately validated simulator.

## Current evidence

- One real development event/session/driver: Bahrain 2025 qualifying, driver 1. The audit contains 17 laps; candidates 4/10/13/16 were identified, with lap 16 excluded for a telemetry gap over one second.
- Calibration uses laps 4 and 10: 287 adjacent acceleration pairs. Validation uses lap 13: 144 pairs. These counts were checked against `results/calibration-data-001/{fit,validation}.csv`. Adjacent pairs are dependent; this is two fitting laps and one within-session validation lap, not 431 independent experiments.
- The diagnostic validation acceleration RMSE is about 2.308 m/s². Mass, power and drag are structurally confounded in the fitted model. See [calibration_review.md](calibration_review.md); this is not an identified F1 powertrain.
- Public telemetry has no verified battery-state or electrical-action labels in the audited schema. Synthetic reconstruction demonstrates ambiguity; real deployment accuracy cannot presently be measured.
- Three 4,096-step PPO pilots and synthetic event-solver/DP checks establish bounded software evidence. They do not establish learning convergence or full-circuit empirical validity. DP action-grid convergence remains open.
- Schedule/catalogue entries describe potential coverage, not acquired usable telemetry. Bahrain remains development data and cannot become an untouched final test.

## What can each question currently support?

| Question | Current defensible claim | Evidence still needed |
| --- | --- | --- |
| RQ1: compatible deployment and reconstruction uncertainty | Synthetic ambiguity and a limited real motion-model diagnostic | Bounded real-lap reconstruction across justified parameter ranges, sensitivity to data processing, and independent motion validation; retain conditional claims without deployment labels |
| RQ2: PPO versus DP on a qualifying circuit | Short synthetic pilot comparisons | Full-circuit action-responsive model, converged numerical reference, feasible heuristics, sufficient independent training runs and frozen evaluation scenarios |
| RQ3: mixed practice/race versus qualifying-only data | No supported answer yet | Usable practice/race/qualifying coverage, matched-volume ablation, and qualifying evaluation groups excluded from all tuning |
| RQ4: observable profile conditioning | No supported answer yet | Defined observable profiles, context coverage and held-out profile comparisons; otherwise report as an uncompleted extension |

## Staged acquisition and stopping decisions

1. **Define roles before acquisition and tuning.** Preserve Bahrain qualifying as development. Select one reference circuit/car and justify compatible layouts and technical regimes. Freeze independent evaluation groups and their permitted uses. Cross-year comparisons on one circuit require explicit vehicle/regime shift assumptions; do not silently pool them.
2. **Expand development coverage deliberately.** Audit practice and race from the same reference context, retaining traffic, tyre, fuel, weather, DRS, track-status and gap limitations where known. This enables a bounded mixed-session pilot, not independent event validation. Unknown fuel/tyre effects must not become assumed deployment effects.
3. **Acquire independent compatible groups.** Use additional sessions/weekends/seasons only for a stated question and supported model assumptions. Separate source/parameter validation from final controller evaluation. A speed envelope derived from a target lap must not then be presented as independent prediction of that lap.
4. **Measure marginal value.** Build data-volume curves by complete laps or sessions, with fixed evaluation groups and transformations fitted only on development data. Use group-aware uncertainty; training seed is a separate replication unit. Record exclusions and failed retrievals in coverage denominators.
5. **Freeze adequacy criteria before the final experiment.** Choose a scientifically meaningful lap-time difference and acceptable predictive/constraint errors, then assess whether numerical, parameter and seed uncertainty permit that distinction. Expand data or narrow the claim if they do not. There is no defensible universal minimum lap count from the supplied papers.

More telemetry helps constrain motion and context; it does not directly reveal battery actions. Simulator-generated PPO experience can be abundant while empirical validity remains weak. The core dissertation can still be valuable if it reports a reproducible, conditional comparison and the limits of reconstruction honestly. It cannot currently substantiate real-world optimal F1 deployment, generalisation across seasons, or a benefit from mixing session types.
