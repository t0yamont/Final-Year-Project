"""Predeclared event integration and output-sampling validation; synthetic only."""
import argparse
from dataclasses import asdict,replace
from datetime import datetime,timezone
import hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from f1energy.power_lap import PowerVehicle,PowerState
from f1energy.event_power_lap import integrate_segment
GRIDS=(40,20,10,5,2.5,1.25,.625,.3125,.15625)
SETTINGS=((1e-6,20),(1e-7,10),(1e-8,5),(1e-9,2),(1e-11,1))

def physical(s):
    return s['max_residual_j']<=.01 and s['min_energy_j']>=50000-1e-6 and s['terminal_speed_m_per_s']<=20+1e-6 and s.get('max_envelope_excess_m_per_s',float('inf'))<=1e-6

def assess(sampling,refinement,analytic):
    changes=[abs(b['elapsed_s']-a['elapsed_s']) for a,b in zip(sampling[:5],sampling[1:5])]
    original=all(b<a for a,b in zip(changes,changes[1:]))
    spreads={key:max(s[key] for s in sampling)-min(s[key] for s in sampling) for key in ('elapsed_s','terminal_speed_m_per_s','battery_draw_j')}
    reference=refinement[-1];fine=refinement[-2]
    errors=[dict(rtol=s['rtol'],**{key:abs(s[key]-reference[key]) for key in spreads}) for s in refinement[:-1]]
    tolerances=dict(elapsed_s=1e-5,terminal_speed_m_per_s=1e-6,battery_draw_j=.01)
    passed=all(physical(s) for s in sampling+refinement) and all(spreads[k]<=v and abs(fine[k]-reference[k])<=v for k,v in tolerances.items()) and analytic['passed']
    return dict(gate='passed_synthetic_numerical_gate' if passed else 'rejected',output_sampling_spreads=spreads,
                integration_errors_vs_reference=errors,physical_checks=all(physical(s) for s in sampling+refinement),
                original_strict_time_trend=original,original_first_five_differences_s=changes,
                original_note='Output-sampling invariance is not integration convergence; original strict trend retained literally.',analytic=analytic)

def run_case(spacing=40,rtol=1e-9,max_step=5):
    state=PowerState(20,450000);infos=[];excess=[];energies=[]
    for cap in (30,20):
        start_distance=state.distance_m
        state,info=integrate_segment(PowerVehicle(),state,400,cap,.6,50000,sample_spacing_m=spacing,rtol=rtol,atol=rtol,max_step_m=max_step)
        infos.append(info)
        vehicle=PowerVehicle();m=vehicle.mass_kg;k=vehicle.drag_kg_per_m;b=vehicle.friction_deceleration_m_per_s2
        for row in info['samples']:
            remaining=max(0.,400-(row['position_m']-start_distance))
            q=cap*cap+2*b*remaining if k==0 else cap*cap*math.exp(2*k*remaining/m)+(m*b/k)*math.expm1(2*k*remaining/m)
            excess.append(row['speed_m_per_s']-min(100.,math.sqrt(q)))
            energies.append(row['energy_j'])
    return dict(spacing_m=spacing,rtol=rtol,max_step_m=max_step,elapsed_s=state.elapsed_s,
                terminal_speed_m_per_s=state.speed_m_per_s,battery_draw_j=450000-state.energy_j,
                max_residual_j=max(abs(i['energy_residual_j']) for i in infos),min_energy_j=min(energies+[state.energy_j]),max_envelope_excess_m_per_s=max(excess)),infos

def analytic_checks():
    v=replace(PowerVehicle(),base_power_w=0,drag_kg_per_m=0)
    initial=PowerState(20,10000);usable=(10000-1000)*v.discharge_efficiency;p=v.electrical_limit_w
    peak=math.sqrt(20**2+2*usable/v.mass_kg);powered_distance=v.mass_kg*(peak**3-20**3)/(3*p)
    expected_time=usable/p+(100-powered_distance)/peak
    end,info=integrate_segment(v,initial,100,100,1,1000)
    reserve_errors=dict(speed=abs(end.speed_m_per_s-peak),time=abs(end.elapsed_s-expected_time),energy=abs(end.energy_j-1000))
    distance=(30**2-20**2)/(2*v.friction_deceleration_m_per_s2)
    end,b=integrate_segment(v,PowerState(30,1000),distance,20,0,1000)
    brake_errors=dict(speed=abs(end.speed_m_per_s-20),time=abs(end.elapsed_s-1.25),work=abs(b['friction_braking_work_j']-.5*v.mass_kg*(30**2-20**2)))
    rejected=False
    try:integrate_segment(v,PowerState(30,1000),distance/2,20,0,1000)
    except ValueError:rejected=True
    passed=reserve_errors['speed']<=1e-6 and reserve_errors['time']<=1e-6 and reserve_errors['energy']<=.01 and brake_errors['speed']<=1e-6 and brake_errors['time']<=1e-6 and brake_errors['work']<=.01 and rejected
    return dict(passed=passed,reserve_errors=reserve_errors,braking_errors=brake_errors,infeasible_braking_rejected=rejected)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    sampling=[];refinement=[];artifacts=[]
    try:
        for spacing in GRIDS:
            s,infos=run_case(spacing);sampling.append(s)
        for tolerance,step in SETTINGS:
            s,infos=run_case(40,tolerance,step);refinement.append(s)
        assessment=assess(sampling,refinement,analytic_checks())
    except Exception as exc:assessment=dict(gate='rejected',exception_type=type(exc).__name__,message=str(exc))
    result=a.output/'summary.json';result.write_text(json.dumps(dict(sampling=sampling,refinement=refinement,assessment=assessment),indent=2)+'\n');artifacts.append(result)
    paths=[Path(__file__),ROOT/'docs/event_validation_protocol.md',ROOT/'src/f1energy/event_power_lap.py',ROOT/'src/f1energy/power_lap.py']
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),source_hashes={str(x.relative_to(ROOT)):sha(x) for x in paths},grids=GRIDS,integration_settings=SETTINGS,vehicle=asdict(PowerVehicle()),outputs={x.name:sha(x) for x in artifacts})
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(assessment,indent=2))
    return 0 if assessment['gate'].startswith('passed') else 1
if __name__=='__main__':raise SystemExit(main())
