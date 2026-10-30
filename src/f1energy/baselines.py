"""Conservative energy-grid DP retaining exact reachable speed states."""
from dataclasses import replace
from functools import lru_cache
from itertools import product
import math
from .lap import initial_state, transition, LapState

def replay(scenario, actions):
    state=initial_state(scenario);rows=[]
    if len(actions)!=len(scenario.segments):raise ValueError('one action required per segment')
    for action in actions:
        state,info=transition(scenario,state,action);rows.append(info)
    return dict(elapsed_s=state.elapsed_s,terminal_energy_j=state.energy_j,
                terminal_speed_m_per_s=state.speed_m_per_s,actions=list(actions),
                feasible=state.energy_j>=scenario.reserve_j-1e-7 and all(r['braking_distance_m']>=0 for r in rows))

def _actions(actions):
    actions=tuple(actions)
    if not actions or any(isinstance(a,bool) or not math.isfinite(a) or not 0<=a<=1 for a in actions):
        raise ValueError('nonempty finite action grid in [0,1] required')
    return tuple(sorted(set(actions)))

def exhaustive(scenario, actions=(0.,.5,1.)):
    actions=_actions(actions)
    if len(actions)**len(scenario.segments)>100000:raise ValueError('exhaustive reference bounded to 100000 sequences')
    return min((replay(scenario,seq) for seq in product(actions,repeat=len(scenario.segments))),key=lambda r:r['elapsed_s'])

def dynamic_programming(scenario, energy_step_j, actions=(0.,.5,1.)):
    initial_state(scenario);actions=_actions(actions)
    if len(actions)**len(scenario.segments)>100000:
        raise ValueError("reachable-state tree exceeds 100000 leaf pilot bound")
    if isinstance(energy_step_j,bool) or not math.isfinite(energy_step_j) or energy_step_j<=0:
        raise ValueError('positive finite energy step required')
    bins=math.floor((scenario.initial_energy_j-scenario.reserve_j)/energy_step_j)
    if bins>100000:raise ValueError('energy grid exceeds pilot bound')
    @lru_cache(None)
    def solve(index,energy_bin,speed):
        if index==len(scenario.segments):return 0.,()
        state=LapState(index,speed,scenario.reserve_j+energy_bin*energy_step_j)
        best=(float('inf'),())
        for action in actions:
            nxt,info=transition(scenario,state,action)
            # Round available energy downward: never invent battery energy.
            next_bin=max(0,min(energy_bin,math.floor((nxt.energy_j-scenario.reserve_j)/energy_step_j)))
            cost,tail=solve(index+1,next_bin,nxt.speed_m_per_s)
            candidate=(info['duration_s']+cost,(action,)+tail)
            if candidate[0]<best[0]:best=candidate
        return best
    cost,sequence=solve(0,bins,scenario.initial_speed_m_per_s)
    result=replay(scenario,sequence)
    result.update(grid_objective_s=cost,energy_step_j=energy_step_j,states_evaluated=solve.cache_info().currsize,
                  initial_rounding_loss_j=scenario.initial_energy_j-scenario.reserve_j-bins*energy_step_j,
                  interpretation='Finite action-grid DP with downward energy rounding; replay uses unrounded physical state.')
    return result
