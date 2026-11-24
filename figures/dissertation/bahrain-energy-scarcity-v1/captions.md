# Bahrain energy-scarcity figures

Source runs results/bahrain-scarcity-planners-001 and results/bahrain-scarcity-zones-001.

All results describe simulated laps on the frozen Bahrain model.

## 01 matched timing

Unmatched feasibility appears at left in coarse-to-fine order within each schedule. The time difference is spread minus the named schedule at the same delivered wheel work, so positive values favor the named schedule. Paired values appear only after feasibility, work matching and numerical refinement pass. Open circles and filled diamonds show the two deterministic integration grids. The horizontal separation shows grid sensitivity. Wheel work at right is the matched total at 320 cells per block. Nominal frozen and scenario-planner rows reuse the same archived schedule. Fixed-finish comparisons scale the earlier requests and use full request in the last three blocks of both schedules.

## 02 zone transfers

Each cell compares allocating a 20 kJ wheel-work packet to the recipient (column) with placing it at the donor (row), under the same scenario and work target. Negative values favor the recipient. Numbers give the 320-cell difference where both grids resolve its sign. The codes retain every inconclusive and failed comparison. Each pair applies to its own baseline and work target. The table of conditional outcomes counts faster, slower and inconclusive comparisons per zone.

## 03 planner deployment

Requested and delivered wheel-assist power for each scenario-specific finite-search schedule at 320 cells per block. Delivered power is work divided by the full action-block duration. Shading marks the seven predeclared packet-test zones in lap order. The accompanying table gives exact distances and work for each schedule at both grids.

Zone labels in order are Timing line, T1–T3, T8 exit, T10 exit, T11 exit, T13 exit, T15.
