"""Model-based action filter for the calibrated Bahrain rolling finish."""
from copy import copy
import hashlib
import json
from pathlib import Path

import gymnasium as gym
import numpy as np

from bahrain_pace_model import build_env
from f1energy.circuit_control import baseline_policy, rollout


SETTINGS = Path("configs/bahrain_finish_constraint.json")


def model_digest(model):
    return hashlib.sha256(json.dumps(model, sort_keys=True, allow_nan=False).encode()).hexdigest()


def prepare_constraint(model, cells):
    settings = json.loads(SETTINGS.read_bytes())
    env = build_env(model, cells)
    start = env.blocks - settings["terminal_blocks"]
    zero = rollout(env, baseline_policy("zero", env))
    durations = [block["duration_s"] for block in zero["trace"]]
    full_w = env.vehicle.electrical_limit_w
    protected = sum(durations[start:]) * full_w / env.vehicle.discharge_efficiency
    if protected >= min(env.initial_energy - env.reserve, env.regeneration.deployment_limit_j):
        raise ValueError("The starting charge or discharge allowance cannot cover the backup")
    reference = rollout(env, lambda _: [float(env.index >= start)])
    if not reference["feasible"]:
        raise ValueError("Zero prefix and full-request suffix fail the physical finish test")
    return dict(model_sha256=model_digest(model), cells=cells, suffix_start_index=start,
                terminal_tolerance_mps=settings["terminal_tolerance_mps"], protected_draw_j=protected,
                zero_block_durations_s=durations, zero_handoff_speed_mps=zero["trace"][start-1]["state"]["speed_m_per_s"],
                backup_duration_s=reference["duration_s"], backup_finish_error_mps=reference["terminal_speed_error_mps"])


class FinishConstraint(gym.Wrapper):
    """Preserve a full-request backup and check proposed final actions on a copy of the plant."""

    def __init__(self, env, certificate):
        super().__init__(env)
        self.certificate = certificate
        self.constraint_stats = dict(agent_steps=0, episodes=0, interventions=0, lookahead_transitions=0,
                                     max_abs_finish_error_mps=0.)

    # The existing physics rollout reads the live vehicle, state and counters from its environment.
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self.env, name)

    @property
    def reference_times(self):
        return self.env.reference_times

    @reference_times.setter
    def reference_times(self, times):
        self.env.reference_times = times

    def _terminal_preview(self, first):
        # Blocks replace immutable PowerState objects and scalar counters. Geometry and the
        # read-only vehicle tables can therefore be shared while the copied plant advances.
        probe = copy(self.env)
        remaining = probe.blocks - probe.index
        for i in range(remaining):
            probe.step([first if i == 0 else 1.])
        return probe.state.speed_m_per_s - probe.initial_speed, remaining

    def step(self, action):
        a = np.asarray(action)
        if a.shape != (1,) or not np.isfinite(a).all() or not 0 <= a.item() <= 1:
            raise ValueError("Expected one finite power fraction in [0, 1]")
        proposed = float(a.item())
        env, c = self.env, self.certificate
        idx = env.index
        if idx >= env.blocks:
            raise RuntimeError("Reset required")
        prefix = idx < c["suffix_start_index"]
        allowed = 1.
        error = None
        probes = 0
        charge = env.state.energy_j - env.reserve
        discharge_left = env.regeneration.deployment_limit_j - env.discharged_j
        protected = c["protected_draw_j"]
        if prefix:
            # An action cannot draw more than its requested power times the block duration
            # divided by efficiency. Use the zero-assist duration and allow no future recharge.
            seconds = c["zero_block_durations_s"][idx]
            full_draw = env.vehicle.electrical_limit_w * seconds / env.vehicle.discharge_efficiency
            allowed = float(np.clip((min(charge, discharge_left) - protected) / full_draw, 0., 1.))
            issued = min(proposed, allowed)
        else:
            if idx == c["suffix_start_index"] and (min(charge, discharge_left) < protected - 1e-5
                    or env.state.speed_m_per_s < c["zero_handoff_speed_mps"] - 1e-7):
                raise RuntimeError("Terminal entry falls outside the reserve or speed certificate")
            issued = proposed
            error, probes = self._terminal_preview(issued)
            if abs(error) >= c["terminal_tolerance_mps"]:
                if issued == 1.:
                    raise RuntimeError("Full-request backup failed from the current state")
                issued = 1.
                backup_error, count = self._terminal_preview(issued)
                probes += count
                if abs(backup_error) >= c["terminal_tolerance_mps"]:
                    raise RuntimeError("No verified finish continuation from the current state")
        obs, reward, done, truncated, info = env.step([issued])
        if prefix:
            remaining = min(env.state.energy_j - env.reserve,
                            env.regeneration.deployment_limit_j - env.discharged_j)
            if info["duration_s"] > seconds + 1e-7 or remaining < protected - 1e-5:
                raise RuntimeError("Applied action violated the protected prefix budget")
        stats = self.constraint_stats
        stats["agent_steps"] += 1
        stats["lookahead_transitions"] += probes
        stats["interventions"] += issued != proposed
        if done:
            finish_error = abs(env.state.speed_m_per_s - env.initial_speed)
            stats["episodes"] += 1
            stats["max_abs_finish_error_mps"] = max(stats["max_abs_finish_error_mps"], finish_error)
            if finish_error >= c["terminal_tolerance_mps"]:
                raise RuntimeError("Executed finish violates the speed constraint")
        info["finish_constraint"] = dict(proposed_action=proposed, issued_action=issued, changed=issued != proposed,
            phase="prefix" if prefix else "terminal", prefix_action_ceiling=allowed if prefix else None,
            protected_draw_j=protected, available_charge_before_j=charge, discharge_left_before_j=discharge_left,
            proposed_backup_finish_error_mps=error, lookahead_transitions=probes)
        return obs, reward, done, truncated, info


def build_constrained_env(model, cells, certificate):
    if certificate["cells"] != cells or certificate["model_sha256"] != model_digest(model):
        raise ValueError("Constraint certificate belongs to a different grid or vehicle")
    return FinishConstraint(build_env(model, cells), certificate)
