"""Synthetic endpoint-speed inverse problem with explicit conditional assumptions."""
import numpy as np
from scipy.optimize import least_squares

def forward(deployment_w,base_power_w=200000.,mass_kg=800.,lengths_m=(100.,150.,100.),initial_speed_m_per_s=30.,initial_energy_j=2000000.,reserve_j=50000.,efficiency=.9):
    d=np.asarray(deployment_w,dtype=float);length=np.asarray(lengths_m,dtype=float)
    values=np.array([base_power_w,mass_kg,initial_speed_m_per_s,initial_energy_j,reserve_j,efficiency])
    if d.shape!=length.shape or not np.isfinite(d).all() or np.any(d<0) or not np.isfinite(length).all() or np.any(length<=0) or not np.isfinite(values).all() or base_power_w<0 or min(mass_kg,initial_speed_m_per_s,efficiency)<=0 or efficiency>1 or not 0<=reserve_j<=initial_energy_j:
        raise ValueError('invalid physical inputs')
    speed=initial_speed_m_per_s;energy=initial_energy_j;rows=[]
    for power,dist in zip(d,length):
        nxt=np.cbrt(speed**3+3*(base_power_w+power)*dist/mass_kg)
        duration=3*dist*(nxt+speed)/(2*(nxt*nxt+nxt*speed+speed*speed))
        draw=power*duration/efficiency;energy-=draw
        rows.append(dict(speed_m_per_s=float(nxt),duration_s=float(duration),battery_draw_j=float(draw),energy_j=float(energy)))
        speed=nxt
    return dict(rows=rows,feasible=bool(energy>=reserve_j),terminal_energy_j=float(energy))

def reconstruct(observed_speed,base_power_w,seed,truth=None,limit_w=120000.):
    observed=np.asarray(observed_speed,dtype=float)
    if observed.shape!=(3,) or not np.isfinite(observed).all() or np.any(observed<=0):raise ValueError('three finite positive endpoints required')
    rng=np.random.default_rng(seed);start=rng.uniform(0,limit_w,3)
    def residual(scaled):return np.array([r['speed_m_per_s'] for r in forward(scaled*limit_w,base_power_w)['rows']])-observed
    result=least_squares(residual,start/limit_w,bounds=(0,1),xtol=1e-12,ftol=1e-12,gtol=1e-12,max_nfev=1000)
    actions=result.x*limit_w;sim=forward(actions,base_power_w);error=residual(result.x)
    return dict(seed=seed,assumed_base_power_w=base_power_w,initial_guess_w=start.tolist(),deployment_w=actions.tolist(),
                optimizer_success=bool(result.success),optimizer_message=result.message,nfev=result.nfev,
                objective_speed_squared=float(error@error),speed_rmse_m_per_s=float(np.sqrt(np.mean(error**2))),
                action_rmse_w=None if truth is None else float(np.sqrt(np.mean((actions-truth)**2))),
                energy_feasible=sim['feasible'],terminal_energy_j=sim['terminal_energy_j'],
                lower_bound_w=0.,upper_bound_w=limit_w)
