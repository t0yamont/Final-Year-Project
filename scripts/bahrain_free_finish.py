"""Single-lap free crossing on the archived Bahrain vehicle and energy model."""
import time

import numpy as np
from bahrain_pace_model import build_env
from f1energy.circuit_control import rollout


def build_free_env(model, cells):
    env = build_env(model, cells)
    cap = env.grid.cell_speed_cap_mps
    # Recompute only the braking tail influenced by the old terminal condition.
    squared = float(cap[-1]) ** 2
    env.envelope[-1] = np.sqrt(squared)
    for i in range(len(cap) - 1, -1, -1):
        vehicle = env.regime_vehicles[i // cells]
        drag = vehicle.drag_kg_per_m
        exponent = 2 * drag * env.grid.lengths_m[i] / vehicle.mass_kg
        braking = vehicle.mass_kg * vehicle.friction_deceleration_m_per_s2 / drag
        squared = min(min(cap[i], cap[i - 1]) ** 2,
                      np.exp(exponent) * squared + braking * np.expm1(exponent))
        bound = np.sqrt(squared)
        if bound == env.envelope[i]:
            break
        env.envelope[i] = bound
    return env


def free_rollout(env, policy):
    record = rollout(env, policy)
    trace = record["trace"]
    p = env.regeneration
    record["feasible"] = bool(
        env.reserve - 1e-5 <= env.state.energy_j <= p.capacity_j + 1e-5
        and env.recovered_j <= p.recovery_limit_j + 1e-5
        and env.discharged_j <= p.deployment_limit_j + 1e-5
        and abs(record["energy_residual_j"]) < 1
        and max(abs(row["battery_residual_j"]) for row in trace) < .01
        and max(row["max_node_cap_excess_mps"] for row in trace) < 1e-5)
    record["finish_speed_mps"] = env.state.speed_m_per_s
    return record


def search_free(env, settings, incumbent):
    """Match the archived scarcity beam and bins, admitting any physical crossing."""
    def replay(actions):
        return free_rollout(env, lambda _: [actions[env.index]])

    started = time.perf_counter()
    original = replay(incumbent)
    best = (original["duration_s"] if original["feasible"] else float("inf"), tuple(incumbent))
    env.reset()
    frontier = [(env.state, env.recovered_j, env.discharged_j, ())]
    layers = []
    for block in range(env.blocks):
        buckets = {}
        expansions = len(frontier) * len(settings["actions"])
        for state, recovered, discharged, prefix in frontier:
            for action in settings["actions"]:
                env.index, env.state = block, state
                env.recovered_j, env.discharged_j = recovered, discharged
                env.step([action])
                path = prefix + (action,)
                if block == env.blocks - 1:
                    best = min(best, (env.state.elapsed_s, path))
                    continue
                energy_bin = settings["energy_bin_j"]
                key = (round(env.state.speed_m_per_s / settings["speed_bin_mps"]),
                       round(env.state.energy_j / energy_bin), round(env.recovered_j / energy_bin),
                       round(env.discharged_j / energy_bin))
                if key not in buckets or env.state.elapsed_s < buckets[key][0].elapsed_s:
                    buckets[key] = (env.state, env.recovered_j, env.discharged_j, path)
        frontier = sorted(buckets.values(), key=lambda row: row[0].energy_j)
        n, width = len(frontier), settings["width"]
        if n > width:
            frontier = [min(frontier[i*n//width:(i+1)*n//width], key=lambda row: row[0].elapsed_s)
                        for i in range(width)]
        layers.append(dict(block=block+1, expansions=expansions, buckets=len(buckets), retained=len(frontier)))
    checked = replay(best[1])
    if not checked["feasible"] or abs(checked["duration_s"] - best[0]) > 1e-8:
        raise ValueError("free planner failed exact search-grid replay")
    return dict(name=settings["name"], actions=list(best[1]), search_time_s=best[0],
                wall_seconds=time.perf_counter()-started, transitions=sum(row["expansions"] for row in layers),
                layers=layers, incumbent_time_s=original["duration_s"])
