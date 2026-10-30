"""Synthetic spatial power/drag integrator with explicit braking work."""
from dataclasses import dataclass
import math
from .braking import braking_envelope

@dataclass(frozen=True)
class PowerVehicle:
    mass_kg: float = 800.0
    base_power_w: float = 100000.0
    electrical_limit_w: float = 60000.0
    discharge_efficiency: float = 0.9
    drag_kg_per_m: float = 0.5
    friction_deceleration_m_per_s2: float = 8.0

@dataclass(frozen=True)
class PowerState:
    speed_m_per_s: float
    energy_j: float
    distance_m: float = 0.0
    elapsed_s: float = 0.0


def _valid(value, positive=False):
    return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value) and (value>0 if positive else value>=0)


def spatial_step(vehicle, state, distance_m, exit_cap_m_per_s, deployment_fraction, reserve_j=0):
    """Solve a spatial cell, then integrate finite braking/throttle adjustment.

    Linear v^2 across distance gives dt=2*ds/(v0+v1) and drag work
    k*ds*(v0^2+v1^2)/2. Power work uses this dt. Battery-limited
    power is uniformly reduced across the cell. This is a numerical model,
    requiring spatial refinement; no calibrated F1 claim is supported.
    """
    if not all(_valid(x) for x in vars(vehicle).values()) or not _valid(vehicle.mass_kg,True) or not 0<vehicle.discharge_efficiency<=1:
        raise ValueError('invalid vehicle')
    if not all(_valid(x) for x in vars(state).values()) or not _valid(state.speed_m_per_s,True):
        raise ValueError('invalid state')
    if not _valid(distance_m,True) or not _valid(exit_cap_m_per_s,True) or not _valid(reserve_j) or reserve_j>state.energy_j or not _valid(deployment_fraction) or deployment_fraction>1:
        raise ValueError('invalid cell/action/reserve')
    m=vehicle.mass_kg; v0=state.speed_m_per_s; ds=distance_m
    usable=(state.energy_j-reserve_j)*vehicle.discharge_efficiency
    p=deployment_fraction*vehicle.electrical_limit_w
    def terms(v, throttle):
        dt=2*ds/(v0+v)
        electrical=min(usable,throttle*p*dt)
        base=throttle*vehicle.base_power_w*dt
        drag=vehicle.drag_kg_per_m*ds*(v0*v0+v*v)/2
        kinetic=.5*m*(v*v-v0*v0)
        return kinetic+drag-base-electrical,dt,electrical,base,drag,kinetic
    def root(throttle):
        if terms(0,throttle)[0]>=0:
            raise ValueError('cell stalls; refine spatial grid')
        lo=0.; hi=max(v0,exit_cap_m_per_s,1.)
        while terms(hi,throttle)[0]<0:
            hi*=2
            if not math.isfinite(hi):raise ValueError('numeric overflow')
        for _ in range(70):
            mid=(lo+hi)/2
            if terms(mid,throttle)[0]>0:hi=mid
            else:lo=mid
        return (lo+hi)/2
    powered=root(1.)
    throttle=1.; brake=0.; speed=powered
    if powered>exit_cap_m_per_s:
        speed=exit_cap_m_per_s
        coast_balance=terms(speed,0.)[0]
        if coast_balance<0:
            throttle=0.; brake=-coast_balance
            if brake>m*vehicle.friction_deceleration_m_per_s2*ds+1e-7:
                raise ValueError('infeasible entry: insufficient braking distance')
        else:
            lo=0.;hi=1.
            for _ in range(70):
                mid=(lo+hi)/2
                if terms(speed,mid)[0]>0:lo=mid
                else:hi=mid
            throttle=(lo+hi)/2
    residual,dt,electrical,base,drag,kinetic=terms(speed,throttle)
    draw=electrical/vehicle.discharge_efficiency
    result=PowerState(speed,max(reserve_j,state.energy_j-draw),state.distance_m+ds,state.elapsed_s+dt)
    return result,dict(duration_s=dt,battery_draw_j=draw,electrical_work_j=electrical,
        base_work_j=base,drag_work_j=drag,friction_braking_work_j=brake,
        kinetic_change_j=kinetic,energy_residual_j=residual+brake,
        throttle_fraction=throttle,net_acceleration_m_per_s2=(speed*speed-v0*v0)/(2*ds),
        provenance='synthetic_spatial_power_drag')


def simulate(vehicle, lengths_m, node_caps_m_per_s, initial, policy, reserve_j=0):
    """Open path with precomputed backward braking envelope; policy(i,state)."""
    lengths=tuple(lengths_m)
    envelope=braking_envelope(lengths,node_caps_m_per_s,
                             [vehicle.friction_deceleration_m_per_s2]*len(lengths))
    if initial.speed_m_per_s>envelope[0]+1e-9:
        raise ValueError('initial speed exceeds braking envelope')
    state=initial;rows=[]
    for i,ds in enumerate(lengths):
        state,info=spatial_step(vehicle,state,ds,envelope[i+1],policy(i,state),reserve_j)
        rows.append(info)
    return state,rows
