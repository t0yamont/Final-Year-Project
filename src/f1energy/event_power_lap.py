"""Event-resolved synthetic power/drag reference; scipy required at execution."""
import math
from dataclasses import dataclass
from .power_lap import PowerVehicle, PowerState


@dataclass(frozen=True)
class Regeneration:
    """Assumed MGU-K-only model: wheel-side power, battery-side lap budgets."""
    capacity_j: float = 4000000.
    charge_efficiency: float = .8
    max_power_w: float = 120000.
    braking_fraction: float = .4
    recovery_limit_j: float = 2000000.
    deployment_limit_j: float = 4000000.

    def __post_init__(self):
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or
               not math.isfinite(x) or x < 0 for x in vars(self).values()):
            raise ValueError('regeneration parameters must be finite nonnegative numbers')
        if self.capacity_j <= 0 or not 0 < self.charge_efficiency <= 1 or self.braking_fraction > 1:
            raise ValueError('invalid battery capacity, charging efficiency or braking fraction')


def integrate_segment(vehicle,state,length_m,exit_cap_m_per_s,action_fraction,reserve_j=0,
                      max_speed_m_per_s=100,sample_spacing_m=None,
                      rtol=1e-9,atol=1e-9,max_step_m=5,
                      regeneration=None,recovered_j=0.,discharged_j=0.):
    from scipy.integrate import solve_ivp
    values=list(vars(vehicle).values())+list(vars(state).values())+[length_m,exit_cap_m_per_s,action_fraction,reserve_j,max_speed_m_per_s,rtol,atol,max_step_m]
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<0 for x in values):
        raise ValueError('inputs must be finite nonnegative numbers')
    if min(vehicle.mass_kg,vehicle.discharge_efficiency,vehicle.friction_deceleration_m_per_s2,state.speed_m_per_s,length_m,exit_cap_m_per_s,max_speed_m_per_s,rtol,atol,max_step_m)<=0 or vehicle.discharge_efficiency>1 or action_fraction>1 or state.energy_j<reserve_j:
        raise ValueError('invalid positive value, efficiency, action or reserve')
    if sample_spacing_m is not None and (not math.isfinite(sample_spacing_m) or sample_spacing_m<=0):raise ValueError('invalid sample spacing')
    if regeneration is not None:
        if not isinstance(regeneration, Regeneration):raise ValueError('Regeneration parameters required')
        for value, limit in [(recovered_j, regeneration.recovery_limit_j),
                             (discharged_j, regeneration.deployment_limit_j)]:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= limit+1e-5:
                raise ValueError('invalid cumulative battery budget')
        if state.energy_j > regeneration.capacity_j+1e-5 or reserve_j > regeneration.capacity_j:
            raise ValueError('initial energy or reserve exceeds battery capacity')
    m=vehicle.mass_kg;k=vehicle.drag_kg_per_m;b=vehicle.friction_deceleration_m_per_s2
    eta=vehicle.discharge_efficiency;target=min(exit_cap_m_per_s,max_speed_m_per_s)
    def bound(x):
        remaining=max(0.,length_m-x)
        if k==0:return target*target+2*b*remaining
        exponent=2*k*remaining/m
        if exponent>700:return math.inf
        return target*target*math.exp(exponent)+(m*b/k)*math.expm1(exponent)
    if state.speed_m_per_s>max_speed_m_per_s+1e-8 or state.speed_m_per_s**2>bound(0)+1e-7:
        raise ValueError('initial speed violates feasible braking envelope')
    # q, battery, elapsed, electrical work, base work, drag work, friction work
    y=[state.speed_m_per_s**2,state.energy_j,0.,0.,0.,0.,0.]
    if regeneration is not None:y.extend([0.,0.])  # recovered wheel work, battery charge
    x=0.;pieces=[];events=[]
    depleted=state.energy_j<=reserve_j+1e-8
    stage='brake' if abs(y[0]-bound(0))<1e-7 else 'drive'
    for iteration in range(12):
        budget_spent=regeneration is not None and discharged_j+y[3]/eta >= regeneration.deployment_limit_j-1e-8
        pel=0. if depleted or budget_spent else action_fraction*vehicle.electrical_limit_w
        harvesting=(regeneration is not None and stage=='brake' and regeneration.max_power_w>0
                    and regeneration.braking_fraction>0 and y[1]<regeneration.capacity_j-1e-8
                    and recovered_j+y[8]<regeneration.recovery_limit_j-1e-8)
        if stage!='brake' and y[0]>=max_speed_m_per_s**2-1e-7 and vehicle.base_power_w+pel>=k*max_speed_m_per_s**3:
            stage='cruise'
        def rhs(s,z):
            if z[0]<=0:raise ValueError('nonpositive speed; stalled trajectory')
            v=math.sqrt(z[0]);drag=k*z[0]
            pb=vehicle.base_power_w if stage!='brake' else 0.
            pe=pel if stage!='brake' else 0.
            friction=m*b if stage=='brake' else 0.
            if stage=='cruise':
                fraction=(k*v**3)/(pb+pe) if pb+pe else 0.
                pb*=fraction;pe*=fraction
            recovery_force=min(friction*regeneration.braking_fraction,regeneration.max_power_w/v) if harvesting else 0.
            charge_per_m=recovery_force*regeneration.charge_efficiency if harvesting else 0.
            rates=[2*((pb+pe)/v-drag-friction)/m,-pe/(eta*v)+charge_per_m,1/v,pe/v,pb/v,drag,friction-recovery_force]
            return rates+[recovery_force,charge_per_m] if regeneration is not None else rates
        handlers=[];names=[]
        def add(fn,name,direction):
            fn.terminal=True;fn.direction=direction;handlers.append(fn);names.append(name)
        if stage!='brake':
            def braking(s,z):return z[0]-bound(s)
            add(braking,'braking',1)
            if not depleted and pel>0:
                def battery(s,z):return z[1]-reserve_j
                add(battery,'depletion',-1)
                if regeneration is not None:
                    def deployment(s,z):return discharged_j+z[3]/eta-regeneration.deployment_limit_j
                    add(deployment,'deployment_limit',1)
            if stage=='drive' and vehicle.base_power_w+pel>k*max_speed_m_per_s**3:
                def ceiling(s,z):return z[0]-max_speed_m_per_s**2
                add(ceiling,'speed_ceiling',1)
        if harvesting:
            def full(s,z):return z[1]-regeneration.capacity_j
            def recovery(s,z):return recovered_j+z[8]-regeneration.recovery_limit_j
            add(full,'battery_full',1);add(recovery,'recovery_limit',1)
        sol=solve_ivp(rhs,(x,length_m),y,rtol=rtol,atol=atol,max_step=max_step_m,dense_output=True,events=handlers)
        if not sol.success:raise ValueError(sol.message)
        end=float(sol.t[-1]);pieces.append((x,end,sol.sol));x=end;y=sol.y[:,-1].tolist()
        if x>=length_m-1e-10:break
        fired=next((names[i] for i,e in enumerate(sol.t_events) if len(e)),None)
        if fired is None:raise ValueError('solver ended without event')
        events.append(dict(kind=fired,position_m=state.distance_m+x,speed_m_per_s=math.sqrt(y[0]),energy_j=y[1]))
        if fired=='braking':stage='brake'
        elif fired=='depletion':
            depleted=True;y[1]=reserve_j;stage='drive'
        elif fired=='deployment_limit':depleted=True;stage='drive'
        elif fired=='speed_ceiling':stage='cruise'
    else:raise ValueError('event iteration limit reached')
    speed=math.sqrt(y[0]);energy=y[1]
    if speed>target+1e-5 or energy<reserve_j-1e-5:raise ValueError('terminal numerical constraint violation')
    if regeneration is not None and (energy>regeneration.capacity_j+1e-5 or
            recovered_j+y[8]>regeneration.recovery_limit_j+1e-5 or
            discharged_j+y[3]/eta>regeneration.deployment_limit_j+1e-5):
        raise ValueError('terminal regeneration constraint violation')
    result=PowerState(speed,energy,state.distance_m+length_m,state.elapsed_s+y[2])
    samples=[]
    if sample_spacing_m is not None:
        positions=[min(i*sample_spacing_m,length_m) for i in range(1,math.ceil(length_m/sample_spacing_m)+1)]
        for pos in positions:
            z=next(dense(pos) for start,end,dense in pieces if start-1e-10<=pos<=end+1e-10)
            samples.append(dict(position_m=state.distance_m+pos,speed_m_per_s=math.sqrt(z[0]),energy_j=float(z[1]),elapsed_s=state.elapsed_s+float(z[2])))
    change=.5*m*(y[0]-state.speed_m_per_s**2)
    info=dict(duration_s=y[2],battery_draw_j=state.energy_j-energy,electrical_work_j=y[3],base_work_j=y[4],
              drag_work_j=y[5],friction_braking_work_j=y[6],kinetic_change_j=change,
              energy_residual_j=change-y[3]-y[4]+y[5]+y[6],events=events,samples=samples,
              solver=dict(rtol=rtol,atol=atol,max_step_m=max_step_m),provenance='synthetic_event_power_drag')
    if regeneration is not None:
        info.update(regenerative_braking_work_j=y[7],battery_recovered_j=y[8],
                    battery_discharged_j=y[3]/eta,charging_loss_j=y[7]-y[8],
                    battery_residual_j=energy-state.energy_j+y[3]/eta-y[8],
                    provenance='synthetic_event_power_drag_regeneration')
        info['energy_residual_j']+=y[7]
    return result,info
