"""Fixed-distance deployment decisions on the validated event-based circuit model."""
import math
import numpy as np
import gymnasium as gym
from .circuit import closed_braking_envelope
from .event_power_lap import integrate_segment, Regeneration
from .power_lap import PowerState


def control_grid(curve, blocks, cells_per_block, lateral=20., ceiling=95.):
    if any(isinstance(x,bool) or not isinstance(x,int) or x<1 for x in [blocks,cells_per_block]) or blocks*cells_per_block<3:
        raise ValueError('positive integer block counts with at least three cells required')
    # All grids share exact action boundaries in the geometry parameter.
    return curve.grid(curve.source_length_m/(blocks*cells_per_block-.25), lateral, ceiling)


def terminal_envelope(grid, vehicle, terminal_speed):
    if not np.isfinite(terminal_speed) or terminal_speed<=0:raise ValueError('positive terminal speed required')
    envelope=closed_braking_envelope(grid.lengths_m,grid.cell_speed_cap_mps,vehicle)
    envelope[-1]=min(envelope[-1],terminal_speed)
    m,k,b=vehicle.mass_kg,vehicle.drag_kg_per_m,vehicle.friction_deceleration_m_per_s2
    for i in range(len(grid.lengths_m)-1,-1,-1):
        length=grid.lengths_m[i]
        if k:
            exponent=2*k*length/m
            bound=math.inf if exponent>700 else envelope[i+1]**2*math.exp(exponent)+m*b/k*math.expm1(exponent)
        else:bound=envelope[i+1]**2+2*b*length
        envelope[i]=min(envelope[i],math.sqrt(bound))
    return envelope


class CircuitControlEnv(gym.Env):
    """Single finite-energy rolling lap; common entry speed and terminal speed cap.

    Reward is a fixed reference block time minus actual time; its episode sum
    is exactly reference lap time minus actual lap time (use gamma=1).
    Terminal speed equality is checked in evaluation, not fabricated by clipping.
    """
    metadata={'render_modes':[]}
    def __init__(self,grid,vehicle,blocks=55,initial_speed=70.,initial_energy=2e6,reserve=1e5,reference_times=None,regeneration=None):
        if not isinstance(blocks,int) or blocks<1 or len(grid.lengths_m)%blocks:raise ValueError('grid must divide into action blocks')
        if not all(np.isfinite(x) for x in [initial_speed,initial_energy,reserve]) or initial_speed<=0 or reserve<0 or initial_energy<reserve:
            raise ValueError('invalid initial conditions')
        if regeneration is not None and (not isinstance(regeneration, Regeneration) or initial_energy>regeneration.capacity_j):
            raise ValueError('invalid regeneration parameters or initial battery energy')
        self.regeneration=regeneration
        self.grid,self.vehicle,self.blocks=grid,vehicle,blocks
        self.initial_speed,self.initial_energy,self.reserve=initial_speed,initial_energy,reserve
        self.cells_per_block=len(grid.lengths_m)//blocks
        self.envelope=terminal_envelope(grid,vehicle,initial_speed)
        if initial_speed>self.envelope[0]+1e-8:raise ValueError('infeasible entry')
        self.reference_times=np.zeros(blocks) if reference_times is None else np.asarray(reference_times,dtype=float)
        if self.reference_times.shape!=(blocks,) or not np.isfinite(self.reference_times).all():raise ValueError('invalid reference times')
        self.action_space=gym.spaces.Box(0.,1.,(1,),dtype=np.float32)
        self.observation_space=gym.spaces.Box(0.,np.inf,(8 if regeneration is not None else 6,),dtype=np.float32)
        self.reset()

    def _obs(self):
        i=min(self.index*self.cells_per_block,len(self.grid.lengths_m)-1)
        j=min(len(self.envelope),i+self.cells_per_block+1)
        k=min(len(self.envelope),i+2*self.cells_per_block+1)
        observation=[self.index/self.blocks,self.state.speed_m_per_s/100,
            max(0.,self.state.energy_j-self.reserve)/max(1.,(self.regeneration.capacity_j if self.regeneration is not None else self.initial_energy)-self.reserve),
            self.grid.cell_speed_cap_mps[i]/100,min(self.envelope[i:j])/100,min(self.envelope[i:k])/100]
        if self.regeneration is not None:
            observation.extend(max(0.,1-used/limit) if limit>0 else 0. for used,limit in
                               [(self.recovered_j,self.regeneration.recovery_limit_j),
                                (self.discharged_j,self.regeneration.deployment_limit_j)])
        return np.array(observation,dtype=np.float32)

    def reset(self,*,seed=None,options=None):
        super().reset(seed=seed);self.index=0
        self.state=PowerState(self.initial_speed,self.initial_energy)
        self.recovered_j=0.;self.discharged_j=0.
        return self._obs(),{}

    def step(self,action):
        if self.index>=self.blocks:raise RuntimeError('reset required')
        a=np.asarray(action)
        if a.shape!=(1,) or not np.isfinite(a).all() or not 0<=float(a[0])<=1:raise ValueError('invalid action')
        start=self.state; total_residual=0.; max_residual=0.; max_excess=0.; events=[]
        work=dict.fromkeys(['base_work_j','electrical_work_j','drag_work_j','friction_braking_work_j'],0.)
        if self.regeneration is not None:
            work.update(dict.fromkeys(['regenerative_braking_work_j','battery_recovered_j',
                                      'battery_discharged_j','charging_loss_j','battery_residual_j'],0.))
        for i in range(self.index*self.cells_per_block,(self.index+1)*self.cells_per_block):
            self.state,info=integrate_segment(self.vehicle,self.state,float(self.grid.lengths_m[i]),
                float(self.envelope[i+1]),float(a[0]),reserve_j=self.reserve,
                max_speed_m_per_s=float(self.grid.cell_speed_cap_mps[i]),regeneration=self.regeneration,
                recovered_j=self.recovered_j,discharged_j=self.discharged_j)
            if self.regeneration is not None:
                self.recovered_j+=info['battery_recovered_j'];self.discharged_j+=info['battery_discharged_j']
            total_residual+=info['energy_residual_j'];max_residual=max(max_residual,abs(info['energy_residual_j']))
            max_excess=max(max_excess,self.state.speed_m_per_s-self.envelope[i+1])
            for key in work:work[key]+=info[key]
            events.extend(info['events'])
        duration=self.state.elapsed_s-start.elapsed_s
        reward=float(self.reference_times[self.index]-duration);self.index+=1
        info=dict(action=float(a[0]),duration_s=duration,energy_residual_j=total_residual,max_cell_residual_j=max_residual,
                  max_node_cap_excess_mps=max_excess,battery_draw_j=start.energy_j-self.state.energy_j,
                  state=vars(self.state),events=events,**work)
        return self._obs(),reward,self.index==self.blocks,False,info


def rollout(env,policy):
    obs,_=env.reset(seed=0); trace=[]; reward=0.;done=False
    while not done:
        obs,r,done,_,info=env.step(np.asarray(policy(obs),dtype=np.float32).reshape(1));trace.append(info);reward+=r
    residual=sum(r['energy_residual_j'] for r in trace)
    terminal_error=env.state.speed_m_per_s-env.initial_speed
    feasible=(abs(terminal_error)<1e-5 and env.state.energy_j>=env.reserve-1e-5 and abs(residual)<1.
              and max(r['max_node_cap_excess_mps'] for r in trace)<1e-5)
    if env.regeneration is not None:
        p=env.regeneration
        feasible=feasible and (env.state.energy_j<=p.capacity_j+1e-5 and env.recovered_j<=p.recovery_limit_j+1e-5
                              and env.discharged_j<=p.deployment_limit_j+1e-5
                              and max(abs(r['battery_residual_j']) for r in trace)<.01)
    return dict(duration_s=env.state.elapsed_s,final_energy_j=env.state.energy_j,terminal_speed_error_mps=terminal_error,
                energy_residual_j=residual,feasible=bool(feasible),reward_sum=reward,trace=trace)


def baseline_policy(name,env):
    if name in ['zero','half','full']:
        return lambda obs:[{'zero':0.,'half':.5,'full':1.}[name]]
    if name=='spread':
        # Allocate remaining battery over estimated remaining travel time at current
        # speed. Conservative heuristic, not an optimizer or measured deployment.
        def policy(obs):
            remaining=max(1.,env.grid.distance_m[-1]-env.state.distance_m)
            seconds=remaining/max(1.,env.state.speed_m_per_s)
            return [min(1.,max(0.,env.state.energy_j-env.reserve)*env.vehicle.discharge_efficiency/
                          max(1.,seconds*env.vehicle.electrical_limit_w))]
        return policy
    if name=='exit_boost':
        return lambda obs:[float(obs[1]<.55 and obs[4]>=obs[1])]
    raise ValueError('unknown policy')
