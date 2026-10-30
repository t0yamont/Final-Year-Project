"""Reproducible synthetic grid study; no controller fitting or real F1 data."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from f1energy.power_lap import PowerVehicle,PowerState,spatial_step
from f1energy.braking import braking_envelope

GRID_SIZES=(40.,20.,10.,5.,2.5)
PATH_LENGTH=800.
ACTION=0.6
RESERVE=50000.

def physical_cap(position_m):
    # Point constraints at exact shared physical locations; all grids include them.
    if position_m==400.:return 30.
    if position_m==800.:return 20.
    return 100.

def spatial_control(position_m):
    return ACTION

def grid(spacing):
    count=round(PATH_LENGTH/spacing)
    if spacing<=0 or abs(count*spacing-PATH_LENGTH)>1e-9 or abs(400/spacing-round(400/spacing))>1e-9:
        raise ValueError('grid must include path endpoint and corner at 400 m')
    nodes=[i*spacing for i in range(count+1)]
    return nodes,[physical_cap(x) for x in nodes]

def run_grid(spacing):
    vehicle=PowerVehicle()
    nodes,caps=grid(spacing)
    lengths=[b-a for a,b in zip(nodes,nodes[1:])]
    envelope=braking_envelope(lengths,caps,[vehicle.friction_deceleration_m_per_s2]*len(lengths))
    state=PowerState(20.,450000.)
    trajectory=[]
    for i,ds in enumerate(lengths):
        action=spatial_control(nodes[i])
        state,info=spatial_step(vehicle,state,ds,envelope[i+1],action,RESERVE)
        trajectory.append(dict(position_m=nodes[i+1],cap_m_per_s=caps[i+1],
            envelope_m_per_s=envelope[i+1],action_fraction=action,state=asdict(state),info=info))
    summary=dict(spacing_m=spacing,cells=len(lengths),elapsed_s=state.elapsed_s,
        battery_draw_j=450000.-state.energy_j,terminal_speed_m_per_s=state.speed_m_per_s,
        max_abs_energy_residual_j=max(abs(r['info']['energy_residual_j']) for r in trajectory),
        max_envelope_excess_m_per_s=max(r['state']['speed_m_per_s']-r['envelope_m_per_s'] for r in trajectory),
        min_energy_j=min(r['state']['energy_j'] for r in trajectory))
    return summary,trajectory

def assess(summaries):
    differences=[abs(b['elapsed_s']-a['elapsed_s']) for a,b in zip(summaries,summaries[1:])]
    fine,previous=summaries[-1],summaries[-2]
    time_relative=differences[-1]/fine['elapsed_s']
    energy_relative=abs(fine['battery_draw_j']-previous['battery_draw_j'])/max(1.,fine['battery_draw_j'])
    physical=all(s['max_abs_energy_residual_j']<1e-6 and s['max_envelope_excess_m_per_s']<1e-8 and s['min_energy_j']>=RESERVE for s in summaries)
    refinement=all(b<a for a,b in zip(differences,differences[1:]))
    passed=physical and refinement and time_relative<0.001 and energy_relative<0.001
    return dict(gate='passed_for_this_synthetic_case' if passed else 'rejected',
        consecutive_time_differences_s=differences,finest_time_relative_change=time_relative,
        finest_energy_relative_change=energy_relative,physical_checks_passed=physical,
        time_changes_strictly_decreasing=refinement,threshold_relative=0.001,
        interpretation='Successive-grid evidence only, not an exact error bound or general simulator validation.')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    args.output.mkdir(parents=True,exist_ok=False)
    summaries=[];artifacts=[]
    for spacing in GRID_SIZES:
        summary,trajectory=run_grid(spacing);summaries.append(summary)
        p=args.output/f'grid-{spacing:g}.json'
        p.write_text(json.dumps(dict(summary=summary,trajectory=trajectory),indent=2,allow_nan=False)+'\n')
        artifacts.append(p)
    assessment=assess(summaries)
    result=args.output/'summary.json'
    result.write_text(json.dumps(dict(summaries=summaries,assessment=assessment),indent=2,allow_nan=False)+'\n')
    artifacts.append(result)
    source_paths=[Path(__file__),ROOT/'src/f1energy/power_lap.py',ROOT/'src/f1energy/braking.py']
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),
        scenario=dict(length_m=PATH_LENGTH,initial_speed_m_per_s=20,initial_energy_j=450000,
            reserve_j=RESERVE,action_fraction=ACTION,vehicle=asdict(PowerVehicle()),
            corner_caps={'400':30,'800':20},other_node_cap=100,grid_sizes=GRID_SIZES),
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in source_paths},
        outputs={p.name:sha(p) for p in artifacts})
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(assessment,indent=2))
    return 0 if assessment['gate'].startswith('passed') else 1

if __name__=='__main__':raise SystemExit(main())
