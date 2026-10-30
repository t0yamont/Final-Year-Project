# Synthetic identifiability experiment — 28 October 2026

Step09 begins with an exact analytic constant-power, drag-free straight model. Three segments of100/150/100m, assumed mass800kg and initial speed30m/s generate endpoint observations. Known base wheel power200kW and deployment40/60/80kW produce the ground truth. Initial battery energy2MJ, reserve50kJ and efficiency0.9 are teaching assumptions, not regulatory claims. Deployment bounds0–120kW likewise are experiment bounds, not claimed FIA limits.

The inverse solver fits three bounded deployment powers to three endpoint speeds using SciPy least_squares. Five independent starting seeds are retained for each assumed base power180/200/220kW. Objective is squared endpoint-speed error alone, without regularisation. The generous energy budget makes these bounded candidate runs feasible; energy feasibility is explicitly checked after replay rather than imposed by the optimiser. This solver must not be applied to a restrictive budget as a constrained inverse method without adding actual energy constraints.

## Results

Successful output: results/reconstruction-synthetic-002/reconstruction.json with hashed manifest. The first attempt in reconstruction-synthetic-001 failed JSON serialization of a NumPy boolean; failure.txt records the cause and the successor. Original evidence was preserved.

At known200kW base power, all five initialisations recover the known deployment to numerical precision (example action RMSE2.47e-10W; maximum endpoint-speed RMSE1.50e-13m/s). At180kW, the equally fitting map is60/80/100kW; at220kW it is20/40/60kW. Both alternatives have20,000W action RMSE relative to known truth yet endpoint-speed RMSE below9e-15m/s. All maps remain battery feasible but imply different battery use. Since motion depends on base+deployment, changing base power and subtracting the same amount from deployment preserves the entire synthetic speed trace. Multiple starts cannot remove this structural ambiguity.

A fixed noise-seed2026 adds independent Gaussian endpoint noise with sigma0.1m/s. With known base power, five starts fit the three noisy endpoints essentially exactly; the example deployment RMSE rises to5,099.256W. Three actions fitted to three endpoints give no residual degrees of freedom: zero mismatch is not evidence of correct hidden actions. This is a single noise realisation sensitivity check, not a statistical uncertainty estimate.

## Acceptance and limits

Three tests passed: independent cumulative cubic-speed identity and known recovery, base/deployment confounding with different terminal energies, and infeasible-energy flag/negative-action rejection. Synthetic recovery is established only for this declared model. Uncertain base power alone suffices to exhibit non-uniqueness; drag uncertainty was not added. The model has no corners, braking, tyre limits, aerodynamic drag or real telemetry. No real-driver deployment or battery state has been inferred. Next stages need explicit constrained inverse optimisation, noisy multi-sample uncertainty experiments and validated forward dynamics before bounded real-lap reconstruction.

Run: set PYTHONPATH=src, then `.venv/Scripts/python.exe scripts/reconstruct_synthetic.py --output results/reconstruction-synthetic-NEW`. Existing directories are refused. Run evidence includes truth, observations, bounds, starting guesses, seeds, optimiser status/messages/evaluations, objective, action/speed errors, energy feasibility and software/source/output hashes. AI contribution: model implementation, tests, bounded experiment, serialization repair and conditional interpretation.
