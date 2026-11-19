"""Shared-physics baseline and training-grid gate for a bounded circuit RL pilot."""
import argparse,gzip,hashlib,json,time
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from f1energy.circuit import PeriodicCentreline
from f1energy.circuit_control import control_grid,CircuitControlEnv,rollout,baseline_policy
from f1energy.power_lap import PowerVehicle
from f1energy.event_power_lap import Regeneration


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):p.write_bytes((json.dumps(obj,indent=2,allow_nan=False)+'\n').encode())
def gzsave(p,obj):
    with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(json.dumps(obj,allow_nan=False).encode())
def sources():return {str(p):sha(p) for p in [Path('src/f1energy')/f for f in ['circuit.py','circuit_control.py','event_power_lap.py','power_lap.py']]}
def load_setup(config):
    reference=json.loads(Path(config['reference_config']).read_text())
    if sha(reference['geometry'])!=reference['geometry_sha256']:raise ValueError('geometry changed')
    curve=PeriodicCentreline(np.loadtxt(reference['geometry'],delimiter=',')[:,:2],reference['smoothing_sigma_m'],reference['resample_spacing_m'])
    return reference,curve,PowerVehicle(**reference['vehicle'])
def make_env(config,reference,curve,vehicle,cells,blocks=None):
    blocks=blocks or config['action_blocks']
    grid=control_grid(curve,blocks,cells,reference['lateral_acceleration_mps2'],reference['max_speed_mps'])
    return CircuitControlEnv(grid,vehicle,blocks,config['initial_speed_mps'],reference['initial_energy_j'],reference['reserve_j'],
                             regeneration=Regeneration(**config['regeneration']) if config.get('regeneration') is not None else None)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--figures',type=Path,required=True)
    parser.add_argument('--config',type=Path,default=Path('configs/circuit_controller_study.json'));args=parser.parse_args()
    config=json.loads(args.config.read_text());gate=Path(config['numerical_gate'])
    manifest=json.loads((gate/'manifest.json').read_text());metrics=json.loads((gate/'metrics.json').read_text())
    if not metrics['all_numerical_gates_passed']:raise ValueError('circuit numerical gate failed')
    for p,h in manifest['inputs'].items():
        if sha(p)!=h:raise ValueError('stale numerical input: '+p)
    for p,h in manifest['outputs'].items():
        if sha(p)!=h:raise ValueError('numerical artifact hash mismatch')
    for p in ['src/f1energy/circuit.py','src/f1energy/event_power_lap.py','src/f1energy/power_lap.py']:
        if manifest['sources'].get(str(Path(p)))!=sha(p):raise ValueError('stale numerical gate')
    ref,curve,vehicle=load_setup(config)
    inputs={str(p):sha(p) for p in [args.config,Path(config['reference_config']),Path(ref['geometry']),gate/'manifest.json']}
    args.output.mkdir(parents=True,exist_ok=False);args.figures.mkdir(parents=True,exist_ok=False)
    save(args.output/'contract.json',dict(config=config,inputs=inputs,sources=sources(),script_sha256=sha(__file__)))
    results=[]
    cases=[(config['action_blocks'],c) for c in config['cells_per_block']]
    cases.append((config['cadence_sensitivity_blocks'],config['action_blocks']*config['fine_cells_per_block']//config['cadence_sensitivity_blocks']))
    for blocks,cells in cases:
        env=make_env(config,ref,curve,vehicle,cells,blocks)
        for name in config['policies']:
            start=time.perf_counter();result=rollout(env,baseline_policy(name,env));elapsed=time.perf_counter()-start
            filename=f'blocks-{blocks}_cells-{cells}_{name}.json.gz';gzsave(args.output/filename,result)
            row=dict(blocks=blocks,cells=cells,policy=name,spacing_m=curve.source_length_m/(blocks*cells),duration_s=result['duration_s'],
                final_energy_j=result['final_energy_j'],feasible=result['feasible'],terminal_speed_error_mps=result['terminal_speed_error_mps'],
                energy_residual_j=result['energy_residual_j'],wall_seconds=elapsed,file=filename)
            results.append(row);save(args.output/'progress.json',results);print(json.dumps(row),flush=True)
    base_blocks=config['action_blocks'];fine=config['fine_cells_per_block']
    reference={r['policy']:r for r in results if r['blocks']==base_blocks and r['cells']==fine}
    assessments=[];gates=config['gates']
    for cells in config['cells_per_block']:
        subset={r['policy']:r for r in results if r['blocks']==base_blocks and r['cells']==cells}
        time_error=max(abs(r['duration_s']-reference[n]['duration_s'])/reference[n]['duration_s'] for n,r in subset.items())
        gain_error=max(abs((subset['zero']['duration_s']-r['duration_s'])-(reference['zero']['duration_s']-reference[n]['duration_s'])) for n,r in subset.items())
        pairs=[(a,b) for a in reference for b in reference if reference[a]['duration_s']+gates['ranking_tie_s']<reference[b]['duration_s']]
        ranking=all(subset[a]['duration_s']<subset[b]['duration_s'] for a,b in pairs)
        passed=all(r['feasible'] for r in subset.values()) and time_error<=gates['relative_lap_time'] and gain_error<=gates['gain_error_s'] and ranking
        assessments.append(dict(cells=cells,max_relative_time_error=time_error,max_gain_error_s=gain_error,ranking_preserved=ranking,passed=bool(passed)))
    accepted=[r['cells'] for r in assessments if r['passed']]
    selected=min(accepted) if accepted else None
    summary=dict(results=results,grid_assessments=assessments,selected_cells_per_block=selected,
        pilot_gate_passed=bool(selected and all(r['feasible'] for r in results)),
        scope=config['interpretation'],boundary='Common70 m/s initial speed and terminal cap; equality verified on every reported policy; single finite-energy lap')
    save(args.output/'metrics.json',summary)
    fig,axes=plt.subplots(1,2,figsize=(12,4.8));colors=['#555555','#b86118','#aa7a21','#176b8a','#805080'];markers=['o','s','^','D','v']
    for name,color,marker in zip(config['policies'],colors,markers):
        rr=sorted([r for r in results if r['blocks']==base_blocks and r['policy']==name],key=lambda r:r['spacing_m'])
        axes[0].plot([r['spacing_m'] for r in rr],[r['duration_s'] for r in rr],color=color,marker=marker,label=name)
    axes[0].set(xlabel='Maximum geometry-parameter spacing (m)',ylabel='Simulated lap time (s)',title='Grid sensitivity; common action boundaries');axes[0].legend(fontsize=8)
    names=config['policies'][1:];x=np.arange(len(names))
    for j,blocks in enumerate([base_blocks,config['cadence_sensitivity_blocks']]):
        rr={r['policy']:r for r in results if r['blocks']==blocks and (blocks!=base_blocks or r['cells']==fine)}
        axes[1].bar(x+(j-.5)*.36,[rr['zero']['duration_s']-rr[n]['duration_s'] for n in names],.36,label=f'{blocks} decisions/lap',color=['#176b8a','#b86118'][j])
    axes[1].set_xticks(x,names);axes[1].set(ylabel='Time saved versus zero request (s)',title='Action-cadence sensitivity; same fine grid');axes[1].legend(fontsize=8)
    for ax in axes:ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('Full-circuit deployment baselines | '+args.output.name)
    fig.text(.5,.01,'Assumed reference vehicle and geometry. Fixed70 m/s entry/terminal speed; 2 MJ initial energy, 0.1 MJ reserve. No optimality claim.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,.94))
    for ext in ['png','pdf']:fig.savefig(args.figures/f'01_baseline_grid_cadence.{ext}',dpi=300)
    plt.close(fig)
    save(args.output/'manifest.json',dict(inputs=inputs,sources=sources(),script_sha256=sha(__file__),outputs={str(p):sha(p) for folder in [args.output,args.figures] for p in folder.iterdir() if p.is_file()}))
    print(json.dumps(dict(pilot_gate_passed=summary['pilot_gate_passed'],selected=selected,assessments=assessments)),flush=True)
    if not summary['pilot_gate_passed']:raise SystemExit(2)


if __name__=='__main__':main()
