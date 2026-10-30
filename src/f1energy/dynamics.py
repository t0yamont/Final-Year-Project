"""First-order implicit straight-line prototype; no calibrated F1 parameters."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Vehicle:
    mass_kg: float
    base_power_w: float
    electrical_limit_w: float
    discharge_efficiency: float
    drag_coefficient_kg_per_m: float

@dataclass(frozen=True)
class State:
    speed_m_per_s: float
    energy_j: float
    distance_m: float = 0.0
    elapsed_s: float = 0.0


def _finite(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be finite numeric data')
    if value < 0 or (positive and value == 0):
        raise ValueError(f'{name} outside allowed range')


def step(state, vehicle, requested_deployment_w, duration_s, reserve_j=0.0):
    """Advance fixed dt with battery-limited wheel power and implicit drag.

    Drag force is k*v^2. Solve K1 + dt*k*v1^3 = K0 + dt*wheel_power.
    Distance uses endpoint velocity (first-order). Battery-limited deployment is
    spread uniformly over the step; this is not a full-power depletion event.
    No braking, corners, traction, harvesting or terminal-speed constraint.
    """
    for name, value in vars(state).items():
        _finite(value, name)
    for name, value in vars(vehicle).items():
        _finite(value, name, name in ('mass_kg', 'discharge_efficiency'))
    if vehicle.discharge_efficiency > 1:
        raise ValueError('discharge_efficiency must be at most one')
    _finite(duration_s, 'duration_s', True)
    _finite(requested_deployment_w, 'requested_deployment_w')
    _finite(reserve_j, 'reserve_j')
    if reserve_j > state.energy_j:
        raise ValueError('reserve exceeds available energy')
    if requested_deployment_w > vehicle.electrical_limit_w:
        raise ValueError('requested deployment exceeds electrical limit')
    usable = state.energy_j - reserve_j
    draw = min(usable, requested_deployment_w * duration_s / vehicle.discharge_efficiency)
    electrical_work = draw * vehicle.discharge_efficiency
    executed = electrical_work / duration_s
    kinetic0 = 0.5 * vehicle.mass_kg * state.speed_m_per_s ** 2
    input_work = vehicle.base_power_w * duration_s + electrical_work
    rhs = kinetic0 + input_work
    if not math.isfinite(rhs):
        raise ValueError('energy arithmetic overflow')
    lo, hi = 0.0, rhs
    for _ in range(100):
        kinetic = (lo + hi) / 2
        speed = math.sqrt(2 * kinetic / vehicle.mass_kg)
        drag_work = duration_s * vehicle.drag_coefficient_kg_per_m * speed ** 3
        if kinetic + drag_work > rhs:
            hi = kinetic
        else:
            lo = kinetic
    kinetic1 = (lo + hi) / 2
    speed = math.sqrt(2 * kinetic1 / vehicle.mass_kg)
    result = State(speed, max(reserve_j, state.energy_j - draw),
                   state.distance_m + speed * duration_s, state.elapsed_s + duration_s)
    if not all(math.isfinite(v) for v in vars(result).values()):
        raise ValueError('state arithmetic overflow')
    return result, dict(requested_deployment_w=requested_deployment_w,
        executed_deployment_w=executed, battery_draw_j=draw,
        electrical_wheel_work_j=electrical_work, total_wheel_work_j=input_work,
        drag_work_j=rhs - kinetic1, kinetic_change_j=kinetic1 - kinetic0,
        provenance='synthetic_implicit_straight_prototype')
