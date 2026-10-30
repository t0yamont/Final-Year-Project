"""Diagnostic factorial refinement; does not supersede original failed gate."""
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib,json,platform,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from f1energy.power_lap import PowerVehicle,PowerState,spatial_step
from f1energy.braking import braking_envelope
GRIDS=(2.5,1.25,.625,.3125,.15625)
ARMS={'original':(True,450000.),'caps_no_depletion':(True,1e9),
      'smooth_depletion':(False,450000.),'smooth_no_depletion':(False,1e9)}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(spacing,with_caps,energy):
    vehicle=PowerVehicle();count=round(800/spacing)
    nodes=[i*spacing for i in range(count+1)]
    caps=[(30. if x==400 else 20. if x==800 else 100.) if with_caps else 100. for x in nodes]
    envelope=braking_envelope([spacing]*count,caps,[vehicle.friction_deceleration_m_per_s2]*count)
    state=PowerState(20.,energy);rows=[];modes=[];previous='power';depletion=None
    for i in range(count):
        state,info=spatial_step(vehicle,state,spacing,envelope[i+1],.6,50000.)
        mode='brake' if info['friction_braking_work_j']>1e-6 else 'throttle' if info['throttle_fraction']<1-1e-9 else 'power'
        if mode!=previous:modes.append(dict(position_m=nodes[i],mode=mode));previous=mode
        if depletion is None and state.energy_j<=50000.+1e-6:depletion=nodes[i+1]
        rows.append(dict(position_m=nodes[i+1],state=asdict(state),info=info,envelope_m_per_s=envelope[i+1]))
    summary=dict(spacing_m=spacing,elapsed_s=state.elapsed_s,energy_draw_j=energy-state.energy_j,
        terminal_speed_m_per_s=state.speed_m_per_s,depletion_position_m=depletion,mode_transitions=modes,
        max_abs_energy_residual_j=max(abs(r['info']['energy_residual_j']) for r in rows),
        min_energy_j=min(r['state']['energy_j'] for r in rows),
        max_envelope_excess_m_per_s=max(r['state']['speed_m_per_s']-r['envelope_m_per_s'] for r in rows))
    return summary,rows

def shared_differences(coarse,fine):
    lookup={r['position_m']:r for r in fine}
    return {key:max(abs(r['state'][key]-lookup[r['position_m']]['state'][key]) for r in coarse)
            for key in ('speed_m_per_s','elapsed_s','energy_j')}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    protocol=ROOT/'docs/power_grid_diagnosis.md'
    (a.output/'protocol.md').write_bytes(protocol.read_bytes())
    files=[a.output/'protocol.md'];all_results={}
    for name,(caps,energy) in ARMS.items():
        summaries=[];comparisons=[];previous=None
        for spacing in GRIDS:
            summary,rows=run(spacing,caps,energy);summaries.append(summary)
            if previous is not None:comparisons.append(shared_differences(previous,rows))
            previous=rows
            dest=a.output/f'{name}-{spacing:g}.json'
            dest.write_text(json.dumps(dict(summary=summary,trajectory=rows),allow_nan=False)+'\n');files.append(dest)
        deltas=[b['elapsed_s']-x['elapsed_s'] for x,b in zip(summaries,summaries[1:])]
        all_results[name]=dict(summaries=summaries,consecutive_signed_time_differences_s=deltas,
            finest_time_relative_difference=abs(deltas[-1])/summaries[-1]['elapsed_s'],shared_node_max_differences=comparisons)
    dest=a.output/'summary.json';dest.write_text(json.dumps(all_results,indent=2,allow_nan=False)+'\n');files.append(dest)
    source=[Path(__file__),ROOT/'src/f1energy/power_lap.py',ROOT/'src/f1energy/braking.py']
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),
        study='diagnostic_only_original_gate_unchanged',vehicle=asdict(PowerVehicle()),grids=GRIDS,arms=ARMS,
        initial_speed_m_per_s=20,reserve_j=50000,requested_deployment_fraction=.6,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in source},outputs={p.name:sha(p) for p in files})
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for name,r in all_results.items():
        print(name,json.dumps(dict(deltas=r['consecutive_signed_time_differences_s'],finest_relative=r['finest_time_relative_difference'],last_shared_difference=r['shared_node_max_differences'][-1])))
if __name__=='__main__':main()
