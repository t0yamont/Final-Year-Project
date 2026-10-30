"""Synthetic constant-force straights with exact acceleration/braking phases."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Segment:
    length_m: float
    exit_speed_cap_m_per_s: float

@dataclass(frozen=True)
class Scenario:
    segments: tuple
    mass_kg: float = 800.0
    base_force_n: float = 1600.0
    electrical_force_limit_n: float = 1200.0
    braking_deceleration_m_per_s2: float = 8.0
    discharge_efficiency: float = 0.9
    initial_speed_m_per_s: float = 20.0
    initial_energy_j: float = 450000.0
    reserve_j: float = 50000.0

@dataclass(frozen=True)
class LapState:
    index: int
    speed_m_per_s: float
    energy_j: float
    elapsed_s: float = 0.0


def default_scenario():
    return Scenario(tuple(Segment(length, cap) for length, cap in
                          [(180,25),(300,20),(120,30),(260,20)]))


def initial_state(scenario):
    values = [scenario.mass_kg, scenario.base_force_n, scenario.electrical_force_limit_n,
              scenario.braking_deceleration_m_per_s2, scenario.discharge_efficiency,
              scenario.initial_speed_m_per_s, scenario.initial_energy_j, scenario.reserve_j]
    if not all(math.isfinite(x) and x >= 0 for x in values):
        raise ValueError('invalid scenario values')
    if min(scenario.mass_kg, scenario.base_force_n, scenario.braking_deceleration_m_per_s2,
           scenario.discharge_efficiency, scenario.initial_speed_m_per_s) <= 0:
        raise ValueError('mass, base force, braking, efficiency and initial speed must be positive')
    if scenario.discharge_efficiency > 1 or scenario.reserve_j > scenario.initial_energy_j:
        raise ValueError('invalid efficiency or reserve')
    if not scenario.segments or any(not math.isfinite(s.length_m) or s.length_m <= 0 or
        not math.isfinite(s.exit_speed_cap_m_per_s) or s.exit_speed_cap_m_per_s <= 0 for s in scenario.segments):
        raise ValueError('segments require positive finite length and exit cap')
    return LapState(0, scenario.initial_speed_m_per_s, scenario.initial_energy_j)


def _phases(scenario, state, segment, force):
    a = (scenario.base_force_n + force)/scenario.mass_kg
    b = scenario.braking_deceleration_m_per_s2
    length = segment.length_m
    v = state.speed_m_per_s
    cap = segment.exit_speed_cap_m_per_s
    x = (cap*cap - v*v + 2*b*length)/(2*(a+b))
    if x < -1e-10:
        raise ValueError('entry speed cannot brake to exit cap within segment')
    x = min(length, max(0.0, x))
    peak = math.sqrt(v*v + 2*a*x)
    brake_distance = length-x
    exit_speed = math.sqrt(max(0.0, peak*peak-2*b*brake_distance))
    duration = 2*x/(v+peak) + (2*brake_distance/(peak+exit_speed) if brake_distance else 0)
    return x, brake_distance, peak, exit_speed, duration


def transition(scenario, state, action_fraction):
    if isinstance(action_fraction, bool) or not math.isfinite(action_fraction) or not 0 <= action_fraction <= 1:
        raise ValueError('action fraction must be in [0, 1]')
    if not 0 <= state.index < len(scenario.segments):
        raise ValueError('no remaining segment')
    if state.energy_j < scenario.reserve_j or state.speed_m_per_s <= 0:
        raise ValueError('infeasible incoming state')
    segment = scenario.segments[state.index]
    requested = action_fraction*scenario.electrical_force_limit_n
    available = state.energy_j-scenario.reserve_j
    force = requested
    phases = _phases(scenario,state,segment,force)
    if force*phases[0]/scenario.discharge_efficiency > available:
        lo, hi = 0.0, force
        for _ in range(60):
            mid = (lo+hi)/2
            x = _phases(scenario,state,segment,mid)[0]
            if mid*x/scenario.discharge_efficiency <= available:
                lo = mid
            else:
                hi = mid
        force = lo
        phases = _phases(scenario,state,segment,force)
    x, braking, peak, speed, duration = phases
    draw = force*x/scenario.discharge_efficiency
    next_state = LapState(state.index+1, speed, max(scenario.reserve_j,state.energy_j-draw), state.elapsed_s+duration)
    return next_state, dict(duration_s=duration, acceleration_distance_m=x,
        braking_distance_m=braking, peak_speed_m_per_s=peak,
        requested_force_n=requested, executed_force_n=force, battery_draw_j=draw,
        base_work_j=scenario.base_force_n*x, electrical_wheel_work_j=force*x,
        braking_work_j=scenario.mass_kg*scenario.braking_deceleration_m_per_s2*braking,
        provenance='synthetic_constant_force_lap')


def run_policy(scenario, policy):
    state = initial_state(scenario)
    rows = []
    while state.index < len(scenario.segments):
        state, info = transition(scenario,state,policy(state))
        rows.append(info)
    return state, rows
