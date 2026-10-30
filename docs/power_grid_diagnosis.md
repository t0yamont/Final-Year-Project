# Predeclared power-grid diagnostic protocol — 28 October 2026

This protocol is written before executing power-grid-diagnostic-001. The original power-grid-001 result and acceptance criteria remain unchanged and rejected. This new study is diagnostic and has no production-readiness pass condition.

Run spacings 2.5, 1.25, 0.625, 0.3125 and 0.15625 m on the same 800 m path with constant 0.6 requested deployment. Use a factorial set of four arms: original corner caps with original 450000 J battery; original caps with 1e9 J battery to avoid depletion; constant 100 m/s caps with original battery; constant 100 m/s caps with 1e9 J battery. Reserve stays 50000 J. Vehicle parameters stay unchanged. All nodes include 400 and 800 m. Changing caps and battery is an explicit control intervention, not an alternative evaluation of the original scenario.

Preserve per-cell trajectories and record elapsed time, energy draw, terminal speed, maximum absolute energy residual, minimum energy, maximum envelope exceedance, onset positions of braking/throttle modes and battery depletion. Quantify consecutive time differences and maximum speed/time/energy discrepancies at shared nodes. These are differences between numerical resolutions, not errors against exact truth. Record relative finest-pair time difference without retrospectively using it as an acceptance criterion.

Hypothesis: cell-wide control switching or averaged depletion causes nonmonotone time increments. Compare the four arms to isolate these effects. If removing depletion improves the trend, that supports depletion involvement; if removing caps does, that supports braking/throttle-switch involvement. A smooth nondepleting arm should show cleaner refinement, but conclusions must follow actual output. No model modifications or new PPO runs occur in this diagnostic. Declare uncertainty if the factorial evidence does not isolate a cause.

## Observed diagnostic results

Executed scripts/diagnose_power_grid.py --output results/power-grid-diagnostic-001. Twenty simulations completed (four arms, five grids). The protocol snapshot was saved before simulation; manifest.json hashes it, source files and all trajectory/summary outputs. Original power-grid-001 files and rejected gate were not altered.

| Arm | Consecutive signed time differences, seconds (coarse to fine) | Finest-pair relative time difference |
| --- | --- | --- |
| Original caps and depletion | -0.000125837, -0.0000295783, +0.000381289, +0.000144188 | 0.000694163% |
| Caps, no depletion | -0.000101316, -0.0000345602, -0.00000714926, -0.00000223673 | 0.0000108698% |
| Smooth caps, depletion | -0.0000394439, -0.00000990960, -0.00000249880, -0.000000635247 | 0.00000370913% |
| Smooth caps, no depletion | -0.0000377886, -0.00000945437, -0.00000236405, -0.000000591040 | 0.00000350573% |

Across all arms/grids the largest cell energy residual was below 3.65e-10 J; envelope exceedance was at most zero and reserve was maintained. These checks support accounting consistency, not a truncation-error bound. At shared nodes the original finest pair differed by at most 0.00187220 m/s in speed, 0.000144254 s in elapsed time and 64.4991 J in battery energy. The corresponding caps/no-depletion energy discrepancy was also 64.4991 J, while its speed discrepancy was only 0.00000690452 m/s. Both smooth arms had a finest shared-node energy difference around 0.04323 J.

The original first braking transition moved from a throttle cell beginning at 300 m and braking at 302.5 m on the coarsest grid to throttle at 302.1875 m and braking at 302.34375 m on the finest. Original depletion endpoints moved through 475, 473.75, 473.125, 472.8125 and 472.65625 m. Smooth-arm depletion remained at the cell endpoint 410 m on every grid. These are cell-resolution observations, not exact continuous switching positions.

Interpretation: removing either the corner caps or depletion restores a cleaner decreasing time-difference trend in this experiment. The matched 64.4991 J discrepancy in both capped arms points to grid-dependent propulsion/throttle energy near braking transitions; in the depleted arm this changes the later reserve event and speed, amplifying the time effect. This supports an interaction between cell-wide throttle/braking switching and depletion rather than an accounting violation or failure of the smooth power/drag integrator. It does not uniquely prove a continuous-time cause, and total-time cancellation can still hide local error.

Proposed next fix (not implemented): locate the powered/coasting-to-braking switching event within a cell, split integration at that event, and locate reserve depletion within the subsequent powered phase. Preserve identical constraints and rerun both original and diagnostic protocols. Prefer this explicit event treatment over retrospectively relaxing the convergence criterion. The original convergence gate stays rejected; no production readiness or real-car claim follows from the small finest-pair difference.

AI contribution: predeclared protocol, diagnostic script, execution, numerical comparison and this interpretation. No model source or training experiment was changed.
