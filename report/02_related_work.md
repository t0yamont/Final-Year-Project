# Related work and design rationale

Status: initial evidence-limited draft, 27 October 2026. This chapter can be transferred into the dissertation, but it is not a completed literature review. Citation keys refer to `references.bib`. Source-specific reading coverage and open questions are recorded in the literature matrix. No experiments from this project are reported here.

## Observations and hidden energy decisions

FastF1 documents speed, engine speed, gear, throttle, binary brake, DRS and position channels, with provenance flags for original and interpolated samples. Its documented channel list supplies neither battery state nor electrical deployment power [@fastf1Telemetry]. Consequently, this project's proposed electrical traces are latent reconstructions conditional on a vehicle model. They cannot be evaluated as measured deployment labels. [Primary source: Telemetry class documentation](https://raw.githubusercontent.com/theOehrly/Fast-F1/master/fastf1/core.py).

The research implication is that prediction and reconstruction require different tests. A forward simulator can be checked against withheld observable motion under declared inputs. An inverse procedure uses observed motion to infer possible hidden inputs; its fit error answers whether the model can explain those observations, not whether the explanation is unique. This distinction is the project's proposed interpretation and must later be supported by a dedicated identifiability review and synthetic recovery experiments.

A useful counterexample for the methodology is a straight on which increased assumed resistance can be offset by increased assumed propulsive power. A good speed fit alone does not decide which assumption is correct. The initial design therefore bounds most vehicle parameters, fits only a small subset, and reports sensitivity across plausible alternatives. This is a plan for RQ1, not an empirical finding.

## Model-based energy control

The institutional abstract of Salazar and colleagues describes qualifying control over an out-lap and flying lap, combining nonlinear programming with convex optimisation and feedback tracking [@salazar2019qualifying]. This is a directly relevant comparator family, but only the abstract and bibliographic record were inspected. Detailed assumptions, numerical results and parameter availability must be assessed from the full text before reproducing or challenging the method. [Institutional record](https://research.tue.nl/en/publications/minimum-lap-time-control-of-hybrid-electric-race-cars-in-qualifyi/).

For the present study, dynamic programming is proposed as a transparent discretised reference on a fixed declared simulator. Its credibility will depend on feasible policy replay and independent refinement of state and action grids. A coarse grid cannot establish a continuous optimum. Comparing a neural policy with that reference is informative only when both use identical physical constraints and the information available to each controller is stated. These are proposed comparison rules, not claims established by the abstract above.

## Policy learning and its evaluation

PPO's clipped surrogate uses a policy-probability ratio and advantage estimate; its algorithm alternates rollouts with minibatch updates. The original evaluation concerns simulated control and Atari tasks, not telemetry-based F1 energy reconstruction [@schulman2017ppo, sections 3, 5 and 6]. [Paper](https://arxiv.org/pdf/1707.06347v2).

The proposed use of PPO is therefore a testable engineering choice. The environment must make speed and time respond to deployment, expose the information needed for its transition model, and enforce energy feasibility independently of the learner. Reusing an observed speed trace as a fixed transition would remove the effect that the policy is intended to optimise. The eventual comparison must report training expense separately from inference expense and must allow DP or heuristics to outperform PPO.

Agarwal and colleagues examine uncertainty from limited independent training runs and recommend interval estimates and distribution-aware reporting. Their stratified bootstrap concerns aggregation across benchmark tasks; they also discuss limitations with few runs [@agarwal2021precipice, sections 2-4]. [Versioned full text](https://arxiv.org/html/2108.13264v4).

The project's planned known-circuit experiment should not mechanically copy a multi-task aggregation procedure. It should preserve seed-level replication, pair controller results on the same scenarios, show feasibility failures, and distinguish uncertainty from training randomness, model assumptions and numerical integration. A few seeds cannot support precise claims simply because the simulator generated many timesteps. The exact interval method remains to be justified when the scenario design is frozen.

## Questions that organise the remaining review

| Research question | Unresolved literature/design issue | Evidence still required |
| --- | --- | --- |
| RQ1 reconstruction | Which combinations of hidden power and vehicle parameters are distinguishable from available observations? | Primary identifiability literature; synthetic recovery under known and uncertain parameters |
| RQ2 PPO versus DP | When do amortised decisions justify learning cost on a known deterministic circuit? | Full energy-control papers; DP refinement; repeated matched controller evaluations |
| RQ3 session coverage | Does broader coverage improve qualifying modelling or introduce confounded operating conditions? | A justified observable modelling target; grouped held-out sessions; sample-size control |
| RQ4 profile information | Does an allowed observed profile improve decisions under the same physical scenario? | Profile construction from development data; identical training distributions and held-out profile comparison |

These questions define the proposed contribution as a transparent comparison under incomplete observations. This first reading establishes no claim of novelty or superiority.

## Student critical-reading prompts

1. Explain which FastF1 channels are direct, derived or interpolated and how that changes the permitted claims.
2. Explain why PPO's probability-ratio clipping is different from clipping physical electrical power.
3. Identify which initial and terminal conditions in the qualifying-control paper differ from a single flying-lap experiment once the full text is available.
4. Specify the independent unit of replication in each planned experiment and explain why individual telemetry samples do not provide independent training runs.

## AI-use disclosure for this draft

An AI source-review agent extracted the supplied course documents, inspected the cited technical passages, drafted this synthesis and created the source matrix. Retrieval limitations are recorded explicitly. The student has not yet supplied critical-reading answers or verified the interpretation personally; these must not be represented as completed student learning. No numerical literature result has been reproduced by this project.
