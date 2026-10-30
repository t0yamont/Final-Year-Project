"""Bounded finite-action DP for the synthetic event solver; no speed interpolation."""
from dataclasses import asdict
from functools import lru_cache
from itertools import product
import math
import time
from types import MappingProxyType
import json

from .event_power_lap import integrate_segment
from .power_lap import PowerState


class InfeasiblePolicyError(ValueError):
    """The supplied action grid has no feasible continuation."""


def _grid(actions):
    values = tuple(actions)
    if not values or any(isinstance(a, bool) or not math.isfinite(a) or not 0 <= a <= 1 for a in values):
        raise ValueError('finite nonempty action grid in [0,1] required')
    return tuple(sorted(set(float(a) for a in values)))


class TransitionCache:
    """Run-local cache scoped to one complete scenario and fixed solver settings.

    Only velocity and energy are dynamic state. Distance follows segment index;
    elapsed time is additive cost. Exported cache records include the scope.
    Unexpected numerical errors propagate; only an infeasible braking entry is
    an explicitly rejected transition. Cache hits do not bypass a wall budget.
    """
    def __init__(self, scenario, *, max_transitions=2000, max_seconds=120, solver=None):
        self._scenario = scenario
        self._solver = MappingProxyType(dict(solver or {}))
        self.max_transitions = max_transitions
        self.max_seconds = max_seconds
        self.started = time.perf_counter()
        self.records = {}
        self.hits = 0
        self.calls = 0
        self.loaded_records = 0
        s = scenario
        if not s.lengths_m or len(s.lengths_m) != len(s.exit_caps_m_per_s):
            raise ValueError('nonempty matching segment lengths and caps required')
        if any(not math.isfinite(v) or v <= 0 for v in (*s.lengths_m, *s.exit_caps_m_per_s)):
            raise ValueError('positive finite lengths and caps required')
        if not all(math.isfinite(v) for v in (s.initial_speed_m_per_s, s.initial_energy_j, s.reserve_j)) or s.initial_speed_m_per_s <= 0 or not 0 <= s.reserve_j <= s.initial_energy_j:
            raise ValueError('invalid initial state or reserve')
        if 'sample_spacing_m' in self.solver:
            raise ValueError('optimisation cache stores event summaries, not dense samples')

    @property
    def scenario(self):
        return self._scenario

    @property
    def solver(self):
        return self._solver

    def step(self, index, speed, energy, action):
        if time.perf_counter() - self.started > self.max_seconds:
            raise RuntimeError('transition wall-time pilot budget exceeded')
        key = (index, float(speed), float(energy), float(action))
        if key in self.records:
            self.hits += 1
            return self.records[key]
        if self.calls >= self.max_transitions:
            raise RuntimeError('transition count pilot budget exceeded')
        self.calls += 1
        s = self.scenario
        state = PowerState(speed, energy, sum(s.lengths_m[:index]), 0.)
        try:
            nxt, info = integrate_segment(s.vehicle, state, s.lengths_m[index], s.exit_caps_m_per_s[index], action, reserve_j=s.reserve_j, **self.solver)
        except ValueError as exc:
            if str(exc) != 'initial speed violates feasible braking envelope':
                raise  # Never hide a solver failure as an optimisation decision.
            record = dict(feasible=False, reason=str(exc))
        else:
            # Correct only sub-microjoule roundoff at a hard reserve boundary.
            if nxt.energy_j < s.reserve_j - 1e-6:
                raise ValueError('reserve violated in physical transition')
            record = dict(feasible=True, speed_m_per_s=nxt.speed_m_per_s,
                          energy_j=max(s.reserve_j, nxt.energy_j),
                          reserve_roundoff_correction_j=max(0., s.reserve_j-nxt.energy_j),
                          **info)
        self.records[key] = record
        return record

    def export(self):
        return dict(scenario=asdict(self.scenario), solver=dict(self.solver), calls=self.calls,
                    hits=self.hits, loaded_records=self.loaded_records,
                    records=[dict(key=list(k), result=v) for k, v in self.records.items()],
                    interpretation='Run-local exact-key transition cache; requires matching dependency hashes before reuse.')

    def load_verified_records(self, payload):
        """Load records AFTER caller verifies file and solver dependency hashes."""
        if self.records:
            raise ValueError('load persisted records only into an empty cache')
        if json.loads(json.dumps(asdict(self.scenario))) != payload['scenario'] or dict(self.solver) != payload['solver']:
            raise ValueError('persisted cache scope mismatch')
        loaded = {}
        for row in payload['records']:
            key = tuple(row['key'])
            if len(key) != 4 or key in loaded or not all(math.isfinite(x) for x in key) or not 0 <= key[0] < len(self.scenario.lengths_m) or int(key[0]) != key[0] or key[1] <= 0 or key[2] < self.scenario.reserve_j or not 0 <= key[3] <= 1:
                raise ValueError('invalid persisted transition key')
            record = row['result']
            if record.get('feasible') is True:
                if not all(math.isfinite(record[k]) for k in ('speed_m_per_s', 'energy_j', 'duration_s', 'energy_residual_j')):
                    raise ValueError('nonfinite persisted transition')
            elif record.get('feasible') is not False or record.get('reason') != 'initial speed violates feasible braking envelope':
                raise ValueError('invalid persisted rejection')
            loaded[key] = record
        self.records.update(loaded)
        self.loaded_records = len(loaded)


def replay(scenario, actions, *, cache=None):
    actions = tuple(actions)
    if len(actions) != len(scenario.lengths_m):
        raise ValueError('one action per physical segment required')
    _grid(actions)
    bank = cache if cache is not None else TransitionCache(scenario)
    if bank.scenario != scenario:
        raise ValueError('cache scenario mismatch')
    speed, energy = scenario.initial_speed_m_per_s, scenario.initial_energy_j
    elapsed, rows = 0., []
    for index, action in enumerate(actions):
        record = bank.step(index, speed, energy, action)
        if not record['feasible']:
            raise InfeasiblePolicyError(record['reason'])
        speed, energy = record['speed_m_per_s'], record['energy_j']
        elapsed += record['duration_s']
        rows.append(dict(index=index, action=float(action), **record))
    feasible = all(r['energy_j'] >= scenario.reserve_j-1e-6 and
                   r['speed_m_per_s'] <= min(scenario.exit_caps_m_per_s[r['index']], bank.solver.get('max_speed_m_per_s', 100.))+1e-6 and
                   abs(r['energy_residual_j']) <= .01 for r in rows)
    return dict(elapsed_s=elapsed, terminal_energy_j=energy, terminal_speed_m_per_s=speed,
                actions=list(actions), feasible=feasible, trace=rows)


def exhaustive(scenario, actions=(0., .5, 1.), *, cache=None, max_sequences=10000):
    actions = _grid(actions)
    count = len(actions)**len(scenario.lengths_m)
    if count > max_sequences:
        raise ValueError('finite-action exhaustive sequence budget exceeded')
    bank = cache if cache is not None else TransitionCache(scenario)
    best, failures = None, 0
    for sequence in product(actions, repeat=len(scenario.lengths_m)):
        try:
            candidate = replay(scenario, sequence, cache=bank)
        except InfeasiblePolicyError:
            failures += 1
            continue
        if not candidate['feasible']:
            raise ValueError('physical replay failed acceptance checks')
        if best is None or candidate['elapsed_s'] < best['elapsed_s']:
            best = candidate
    if best is None:
        raise InfeasiblePolicyError('no feasible sequence on the supplied action grid')
    return dict(best, sequences=count, infeasible_sequences=failures, action_grid=list(actions))


def dynamic_programming(scenario, energy_step_j, actions=(0., .5, 1.), *, cache=None, max_sequences=10000):
    actions = _grid(actions)
    if isinstance(energy_step_j, bool) or not math.isfinite(energy_step_j) or energy_step_j <= 0:
        raise ValueError('positive finite energy step required')
    if len(actions)**len(scenario.lengths_m) > max_sequences:
        raise ValueError('reachable-state tree exceeds pilot sequence budget')
    bank = cache if cache is not None else TransitionCache(scenario)
    if bank.scenario != scenario:
        raise ValueError('cache scenario mismatch')
    bins = math.floor((scenario.initial_energy_j-scenario.reserve_j)/energy_step_j)

    @lru_cache(None)
    def solve(index, energy_bin, speed):
        if index == len(scenario.lengths_m):
            return 0., ()
        energy = scenario.reserve_j+energy_bin*energy_step_j
        best = (math.inf, ())
        for action in actions:
            record = bank.step(index, speed, energy, action)
            if not record['feasible']:
                continue
            next_bin = max(0, min(energy_bin, math.floor((record['energy_j']-scenario.reserve_j)/energy_step_j)))
            cost, tail = solve(index+1, next_bin, record['speed_m_per_s'])
            candidate = (record['duration_s']+cost, (action,)+tail)
            if candidate[0] < best[0]:
                best = candidate
        return best

    rounded_cost, sequence = solve(0, bins, scenario.initial_speed_m_per_s)
    if not math.isfinite(rounded_cost):
        raise InfeasiblePolicyError('no feasible DP continuation on the supplied action grid')
    result = replay(scenario, sequence, cache=bank)
    if not result['feasible']:
        raise ValueError('DP physical replay failed acceptance checks')
    return dict(result, grid_objective_s=rounded_cost, energy_step_j=energy_step_j,
                initial_rounding_loss_j=scenario.initial_energy_j-scenario.reserve_j-bins*energy_step_j,
                states_evaluated=solve.cache_info().currsize, state_cache_hits=solve.cache_info().hits,
                action_grid=list(actions), interpretation='Downward energy grid with exact reachable speed; original-state replay, no conservative-bound assertion.')
