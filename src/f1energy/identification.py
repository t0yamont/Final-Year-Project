"""Effective total wheel-power/drag diagnostic; cannot identify hybrid deployment."""
import numpy as np
from scipy.optimize import lsq_linear

def fit_effective(speed,acceleration,mass_kg=800.):
    v=np.asarray(speed,dtype=float);a=np.asarray(acceleration,dtype=float)
    if v.ndim!=1 or a.shape!=v.shape or len(v)<5 or not np.isfinite(v).all() or not np.isfinite(a).all() or np.any(v<=0) or not np.isfinite(mass_kg) or mass_kg<=0:
        raise ValueError('at least five finite positive-speed samples and positive assumed mass required')
    # Scaled response in MW keeps conditioning interpretable and optimisation stable.
    x=np.column_stack([np.ones(len(v)),-v**3/1e6]);y=mass_kg*v*a/1e6
    rank=int(np.linalg.matrix_rank(x))
    if rank<2:raise ValueError('speed variation insufficient to identify both coefficients')
    result=lsq_linear(x,y,bounds=([.1,0.],[1.2,3.]),tol=1e-12)
    p,k=result.x;pred=x@result.x
    profile=[]
    for drag in np.linspace(0,3,31):
        power=float(np.clip(np.mean(y+drag*v**3/1e6),.1,1.2))
        profile.append(dict(drag_coefficient_kg_per_m=float(drag),effective_total_power_w=power*1e6,rmse_w=float(np.sqrt(np.mean((x@np.array([power,drag])-y)**2))*1e6)))
    return dict(assumed_mass_kg=mass_kg,effective_total_power_w=float(p*1e6),drag_coefficient_kg_per_m=float(k),
                sample_count=len(v),speed_min_m_per_s=float(v.min()),speed_max_m_per_s=float(v.max()),
                rmse_w=float(np.sqrt(np.mean((pred-y)**2))*1e6),scaled_design_condition_number=float(np.linalg.cond(x)),
                parameter_boundary_hits=[name for name,value,lo,hi in [('power',p,.1,1.2),('drag',k,0,3)] if abs(value-lo)<1e-6 or abs(value-hi)<1e-6],
                solver_success=bool(result.success),profile=profile,
                interpretation='Conditional effective total power and drag fit. Mass assumed. Electrical power and battery energy are unobserved and not recovered.')

def evaluate(fit,speed,acceleration):
    v=np.asarray(speed,dtype=float);a=np.asarray(acceleration,dtype=float)
    if len(v)==0:return dict(sample_count=0,status='no_eligible_samples')
    predicted=(fit['effective_total_power_w']-fit['drag_coefficient_kg_per_m']*v**3)/(fit['assumed_mass_kg']*v)
    residual=predicted-a
    return dict(sample_count=len(v),acceleration_rmse_m_per_s2=float(np.sqrt(np.mean(residual**2))),acceleration_bias_m_per_s2=float(np.mean(residual)),
                residual_quantiles_m_per_s2=[float(x) for x in np.quantile(residual,[0,.25,.5,.75,1])])
