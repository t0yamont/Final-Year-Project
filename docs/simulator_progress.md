# Simulator increment — 27 October 2026

Action: added dynamics.py, a fixed-time straight-line transition with wheel deployment power, discharge losses, a protected battery reserve and quadratic aerodynamic drag. Added five independent validation tests. All five pass in the bundled Python runtime. No empirical data or training was used.

Method: kinetic energy is advanced by backward Euler. The scalar monotone balance K_next + dt*k*v_next^3 = K_previous + wheel_work is solved by bisection. The model reports battery draw, wheel work, drag work and kinetic change separately. Endpoint velocity integrates distance with first-order accuracy. Deployment is uniformly reduced over the step when insufficient usable energy exists; it does not model full-power running followed by an exact switch-off event. Oversized requested power is rejected. These conventions must remain common to all future controllers.

Discovery: implicit energy dynamics remain nonnegative under large drag steps, but stability does not establish accuracy. A coasting drag test compares refinement against the independent exact solution v(t)=v0/(1+k*v0*t/m); tenfold timestep refinement reduces error by more than a factor of five. Lossless constant-power speed and battery energy also match independent analytic identities.

Problems and boundaries: this is an uncalibrated prototype. No braking, corners, tyre/traction cap, harvesting, terminal-speed condition, regulatory limits or real-car parameters are implemented. Constant base power at zero speed is an idealisation and must not support launch claims. No lap-time performance result is established. Existing analytic fixture and CLI remain unchanged.

Next gates: implement physically feasible anticipatory braking and track constraints; establish timestep and spatial-resolution convergence; calibrate declared parameter ranges on development telemetry; test energy and terminal constraints across full laps; only then implement common-transition heuristic/DP comparisons and Gymnasium/PPO. Heavy training remains manual.

Integration: import Vehicle, State and step from f1energy.dynamics. step returns a new immutable state and a dictionary of accounting evidence. It is intentionally not exposed as a production lap-simulation command yet.

AI disclosure: the simulator agent authored this prototype, validation tests and record. The student should review the numerical convention and interpret future empirical evidence independently.
