"""Replay-verified terminal reserve heuristic; original physics is unchanged."""
import math
import numpy as np
from .circuit_control import CircuitControlEnv


class TerminalGuardEnv(CircuitControlEnv):
    """Protect battery before a fixed terminal span, then force full request.

    The protected budget is an engineering assumption, not a feasibility proof.
    Policy observations and the public reserve retain their original semantics.
    """
    def __init__(self, *args, protected_energy_j=250000., terminal_blocks=1,
                 guard_enabled=True, **kwargs):
        if (isinstance(protected_energy_j, bool) or not isinstance(protected_energy_j, (int, float))
                or not math.isfinite(protected_energy_j) or protected_energy_j < 0):
            raise ValueError('finite nonnegative protected energy required')
        if isinstance(terminal_blocks, bool) or not isinstance(terminal_blocks, int) or terminal_blocks < 1:
            raise ValueError('positive integer terminal block count required')
        if not isinstance(guard_enabled, bool):
            raise ValueError('guard_enabled must be boolean')
        super().__init__(*args, **kwargs)
        if terminal_blocks > self.blocks or self.initial_energy < self.reserve + protected_energy_j:
            raise ValueError('impossible protected budget or terminal span')
        self.protected_energy_j = float(protected_energy_j)
        self.terminal_blocks = terminal_blocks
        self.guard_enabled = guard_enabled

    def step(self, action):
        if self.index >= self.blocks:
            raise RuntimeError('reset required')
        request = np.asarray(action)
        if request.shape != (1,) or not np.isfinite(request).all() or not 0 <= float(request[0]) <= 1:
            raise ValueError('invalid action')
        if not self.guard_enabled:
            return super().step(action)
        proposed = float(request[0])
        terminal = self.index >= self.blocks - self.terminal_blocks
        physical_reserve = self.reserve
        floor = physical_reserve if terminal else physical_reserve + self.protected_energy_j
        issued = 1. if terminal else proposed
        start_energy = self.state.energy_j
        self.reserve = floor
        try:
            _, reward, done, truncated, info = super().step(np.array([issued], dtype=request.dtype))
        finally:
            self.reserve = physical_reserve
        depletion_events = sum(e['kind'] == 'depletion' for e in info['events'])
        info['terminal_guard'] = dict(
            proposed_action=proposed, issued_action=info['action'], reserve_floor_j=floor,
            physical_reserve_j=physical_reserve, protected_floor_active=not terminal,
            terminal_request_override=terminal, action_changed=info['action'] != proposed,
            depletion_events=depletion_events,
            protected_depletion_intervention=bool(not terminal and issued > 0 and
                (depletion_events or start_energy <= floor + 1e-8)))
        return self._obs(), reward, done, truncated, info
