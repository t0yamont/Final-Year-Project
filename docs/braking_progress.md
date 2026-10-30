# Braking gate — 28 October 2026

Added braking.py with a backward open-path speed envelope. For each positive segment length ds and constant net deceleration magnitude a, entry speed cannot exceed sqrt(exit_speed^2+2*a*ds). Local speed caps and an optional terminal upper bound are imposed before propagating constraints backwards. This permits braking before a corner and avoids treating a corner cap as an instantaneous speed reduction.

Six synthetic analytic tests pass: stopping-distance identity, multi-segment propagation, local/terminal bounds, subdivision invariance, constraint feasibility and invalid-input rejection. The initial exact floating-point equality assertion was corrected to an approximate numerical comparison; the computed result differed at machine precision.

Assumptions: immediately available constant net deceleration, point-mass longitudinal motion, positive known distances, no jerk or reaction delay, no banking or changing grip. This is an upper bound, not a forward acceleration-feasible trajectory. Closed-lap periodic constraints and equality terminal speeds remain separate requirements. All parameters in tests are synthetic; no empirical F1 validity is claimed.

Next: combine envelope constraints with a consistent forward integrator and verify full-track boundary conditions. AI agent authored implementation and tests; coordinator reviews integration.
