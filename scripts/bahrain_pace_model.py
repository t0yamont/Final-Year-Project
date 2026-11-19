"""Free-running Sakhir reference with timing-line registration and effective aero terms."""
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import numpy as np
from f1energy.circuit import PeriodicCentreline
from f1energy.circuit_control import CircuitControlEnv, control_grid
from f1energy.event_power_lap import Regeneration
from f1energy.power_lap import PowerVehicle
from benchmark_circuit_control import sha


@lru_cache(maxsize=4)
def registered_curve(path, digest, phase):
    if sha(path) != digest:
        raise ValueError("Geometry hash differs from calibration")
    xy = np.loadtxt(Path(path), delimiter=",")[:, :2]
    distance = np.r_[0., np.cumsum(np.linalg.norm(np.roll(xy, -1, axis=0) - xy, axis=1))]
    station = phase % 1 * distance[-1]
    i = int(np.searchsorted(distance, station, side="right")-1)
    fraction = (station-distance[i])/(distance[i+1]-distance[i])
    start = xy[i]+fraction*(xy[(i+1)%len(xy)]-xy[i])
    ordered = np.vstack([start, xy[i+1:], xy[:i+1]])
    if np.linalg.norm(ordered[-1]-start) < 1e-7:
        ordered = ordered[:-1]
    return PeriodicCentreline(ordered, 10., 5.)


@lru_cache(maxsize=16)
def geometry(path, digest, phase, cells):
    return control_grid(registered_curve(path, digest, phase), 55, cells)


def limits(model, cells):
    g = geometry(model["geometry"], model["geometry_sha256"], model["line_offset_fraction"], cells)
    a = model["lateral_base_mps2"]
    # v² |curvature| <= a + beta v². The separate top speed applies on straights.
    cap = np.sqrt(a/np.maximum(g.max_abs_curvature_per_m-model["lateral_aero_per_m"], a/model["max_speed_mps"]**2))
    grid = replace(g, cell_speed_cap_mps=cap)
    drag = model["vehicle"]["drag_kg_per_m"] * np.where(model["drs_blocks"], model["drs_drag_factor"], 1.)
    k = np.repeat(drag, cells)
    mass, brake = (model["vehicle"][n] for n in ("mass_kg", "friction_deceleration_m_per_s2"))
    z = 2*k*grid.lengths_m/mass
    scale, offset = np.exp(z), (mass*brake/k)*np.expm1(z)
    squared = np.minimum(cap, np.roll(cap, 1))**2
    q = min(float(squared[0]), model["initial_speed_mps"]**2)
    envelope = np.empty(len(cap)+1)
    envelope[-1] = q
    for i in range(len(cap)-1, -1, -1):
        q = min(squared[i], scale[i]*q+offset[i])
        envelope[i] = q
    return grid, np.sqrt(envelope), drag


class BahrainPaceEnv(CircuitControlEnv):
    """Use the same event integrator with the drag regime prescribed for each block."""
    def step(self, action):
        self.vehicle = self.regime_vehicles[self.index * 55 // self.blocks]
        return super().step(action)


def build_env(model, cells, *, cellwise=False):
    grid, envelope, drag = limits(model, cells)
    vehicle = PowerVehicle(**model["vehicle"])
    env = BahrainPaceEnv(grid, vehicle, len(grid.lengths_m) if cellwise else 55,
        model["initial_speed_mps"], model["initial_energy_j"], model["reserve_j"],
        regeneration=Regeneration(**model["regeneration"]))
    env.envelope = envelope
    if env.initial_speed > envelope[0]+1e-8:
        raise ValueError("Measured timing-line entry is outside the calibrated braking envelope")
    env.regime_vehicles = [replace(vehicle, drag_kg_per_m=float(k)) for k in drag]
    return env


def free_lap(model, cells, action):
    """Save each cell endpoint for one constant request or a 55-block schedule."""
    env = build_env(model, cells, cellwise=True)
    schedule = np.broadcast_to(np.asarray(action, dtype=float), (55,))
    env.reset()
    trace = [(0., 0., env.initial_speed, env.initial_energy)]
    for i in range(env.blocks):
        env.step([schedule[i//cells]])
        state = env.state
        trace.append((state.distance_m, state.elapsed_s, state.speed_m_per_s, state.energy_j))
    return np.asarray(trace)
