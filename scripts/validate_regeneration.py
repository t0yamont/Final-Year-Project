"""Validate automatic braking recovery against matched no-recovery circuit baselines."""
import argparse
import json
import time
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from f1energy.circuit_control import rollout, baseline_policy
from benchmark_circuit_control import load_setup, make_env, sources, save, sha, gzsave


def audit_replay(result, config, reference, vehicle):
    """Recompute work/battery identities from saved block values, not solver residuals."""
    energy=reference['initial_energy_j']; speed=config['initial_speed_mps']
    recovered=discharged=0.; max_work=max_battery=0.
    params=config.get('regeneration')
    for block in result['trace']:
        state=block['state']; charge=block.get('battery_recovered_j',0.)
        draw=block['electrical_work_j']/vehicle.discharge_efficiency
        mechanical=block.get('regenerative_braking_work_j',0.)
        residual=.5*vehicle.mass_kg*(state['speed_m_per_s']**2-speed**2)-block['base_work_j']-block['electrical_work_j']+block['drag_work_j']+block['friction_braking_work_j']+mechanical
        max_work=max(max_work,abs(residual))
        max_battery=max(max_battery,abs(state['energy_j']-energy+draw-charge))
        if min(charge,draw,mechanical,block['friction_braking_work_j']) < -1e-5:
            raise ValueError('negative energy flow')
        recovered+=charge;discharged+=draw
        if params:
            if abs(charge-params['charge_efficiency']*mechanical)>.01:raise ValueError('charging efficiency identity')
            if state['energy_j']>params['capacity_j']+1e-5 or recovered>params['recovery_limit_j']+1e-5 or discharged>params['deployment_limit_j']+1e-5:
                raise ValueError('regeneration bounds')
            if mechanical>params['max_power_w']*block['duration_s']+1e-5:raise ValueError('recovery power bound')
            if mechanical>params['braking_fraction']*(mechanical+block['friction_braking_work_j'])+1e-5:raise ValueError('rear braking share')
        if state['energy_j']<reference['reserve_j']-1e-5:raise ValueError('reserve violation')
        energy=state['energy_j'];speed=state['speed_m_per_s']
    if max_work>1. or max_battery>.01:raise ValueError('independent energy balance failed')
    return dict(recovered_j=recovered,discharged_j=discharged,max_work_residual_j=max_work,max_battery_residual_j=max_battery)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('configs/regeneration_study.json'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--figures',type=Path,required=True)
    args=parser.parse_args();config=json.loads(args.config.read_text())
    if Path(config['numerical_gate']).resolve()!=args.output.resolve():raise ValueError('protocol numerical gate must name output directory')
    reference,curve,vehicle=load_setup(config)
    args.output.mkdir(parents=True,exist_ok=False);args.figures.mkdir(parents=True,exist_ok=False)
    bound_sources=sources()
    for path in [Path(__file__),Path('scripts/benchmark_circuit_control.py'),Path('tests/test_regeneration.py')]:bound_sources[str(path)]=sha(path)
    inputs={str(path):sha(path) for path in [args.config,Path(config['reference_config']),Path(reference['geometry'])]}
    save(args.output/'contract.json',dict(config=config,inputs=inputs,sources=bound_sources))
    rows=[];replays={}
    for enabled in [False,True]:
        mode='regeneration' if enabled else 'no_regeneration'
        setup=dict(config,regeneration=config['regeneration'] if enabled else None)
        for cells in config['cells_per_block']:
            env=make_env(setup,reference,curve,vehicle,cells)
            for name in config['policies']:
                started=time.perf_counter();result=rollout(env,baseline_policy(name,env))
                independent=audit_replay(result,setup,reference,vehicle)
                filename=f'{mode}_cells-{cells}_{name}.json.gz';gzsave(args.output/filename,result)
                row=dict(mode=mode,cells=cells,blocks=config['action_blocks'],policy=name,file=filename,
                         duration_s=result['duration_s'],final_energy_j=result['final_energy_j'],
                         terminal_speed_error_mps=result['terminal_speed_error_mps'],feasible=result['feasible'],
                         wall_seconds=time.perf_counter()-started,**independent)
                rows.append(row);replays[(mode,cells,name)]=result
                save(args.output/'progress.json',rows);print(json.dumps(row),flush=True)
    fine=config['fine_cells_per_block'];coarse=min(config['cells_per_block']);assessments=[]
    for mode in ['no_regeneration','regeneration']:
        selected={r['policy']:r for r in rows if r['mode']==mode and r['cells']==coarse}
        refined={r['policy']:r for r in rows if r['mode']==mode and r['cells']==fine}
        time_error=max(abs(selected[n]['duration_s']-refined[n]['duration_s'])/refined[n]['duration_s'] for n in selected)
        gain_error=max(abs((selected['zero']['duration_s']-selected[n]['duration_s'])-(refined['zero']['duration_s']-refined[n]['duration_s'])) for n in selected)
        ranking=all(selected[a]['duration_s']<selected[b]['duration_s'] for a in refined for b in refined
                    if refined[a]['duration_s']+config['gates']['ranking_tie_s']<refined[b]['duration_s'])
        passed=all(r['feasible'] for r in rows if r['mode']==mode) and time_error<=config['gates']['relative_lap_time'] and gain_error<=config['gates']['gain_error_s'] and ranking
        assessments.append(dict(mode=mode,max_relative_time_error=time_error,max_gain_error_s=gain_error,ranking_preserved=ranking,passed=passed))
    accepted=all(a['passed'] for a in assessments)
    metrics=dict(results=[r for r in rows if r['mode']=='regeneration'],comparison=rows,grid_assessments=assessments,
                 all_numerical_gates_passed=accepted,pilot_gate_passed=accepted,selected_cells_per_block=coarse if accepted else None,
                 scope=config['interpretation'],training_performed=False,independently_checked_replays=len(rows))
    save(args.output/'metrics.json',metrics)
    fig,axes=plt.subplots(1,2,figsize=(12,5));names=config['policies'];x=np.arange(len(names))
    for index,mode in enumerate(['no_regeneration','regeneration']):
        selected={r['policy']:r for r in rows if r['mode']==mode and r['cells']==fine}
        axes[0].plot(x,[selected[n]['duration_s'] for n in names],'o-',label=mode.replace('_',' '))
        axes[1].bar(x+(index-.5)*.36,[selected[n]['final_energy_j']/1e6 for n in names],.36,label=mode.replace('_',' '))
    for ax in axes:ax.set_xticks(x,names,rotation=15);ax.grid(axis='y',alpha=.25);ax.legend(fontsize=8)
    axes[0].set(ylabel='Simulated lap time (s)',title='Matched fixed policies; 8,800 cells')
    axes[1].set(ylabel='Final battery energy (MJ)',title='Identical 2 MJ initial battery energy')
    fig.suptitle('Automatic MGU-K recovery | '+args.output.name)
    fig.text(.5,.01,'Assumed reference model; 55 decisions, 70 m/s entry/exit. Fixed-policy comparison, not retrained PPO or an optimum.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,.94))
    for ext in ['png','pdf']:fig.savefig(args.figures/f'01_regeneration_comparison.{ext}',dpi=300)
    plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(10,7),sharex=True)
    for mode in ['no_regeneration','regeneration']:
        trace=replays[(mode,fine,'full')]['trace'];distance=[0.]+[b['state']['distance_m']/1000 for b in trace]
        axes[0].plot(distance,[reference['initial_energy_j']/1e6]+[b['state']['energy_j']/1e6 for b in trace],label=mode.replace('_',' '))
    trace=replays[('regeneration',fine,'full')]['trace']
    axes[1].plot(distance,np.r_[0.,np.cumsum([b['battery_recovered_j'] for b in trace])]/1e6,label='Recovered into battery')
    axes[1].plot(distance,np.r_[0.,np.cumsum([b['battery_discharged_j'] for b in trace])]/1e6,label='Discharged from battery')
    axes[0].axhline(reference['reserve_j']/1e6,color='grey',linestyle=':',label='Physical reserve')
    axes[0].set(ylabel='Battery energy (MJ)',title='Full-request fixed policy; block-boundary samples')
    axes[1].set(xlabel='Distance along circuit (km)',ylabel='Cumulative energy (MJ)')
    for ax in axes:ax.legend();ax.grid(alpha=.25)
    fig.suptitle('Battery accounting | '+args.output.name)
    fig.tight_layout(rect=(0,0,1,.95))
    for ext in ['png','pdf']:fig.savefig(args.figures/f'02_battery_recovery.{ext}',dpi=300)
    plt.close(fig)
    if any(sha(path)!=digest for path,digest in bound_sources.items()):raise RuntimeError('source changed during validation')
    save(args.output/'manifest.json',dict(inputs=inputs,sources=bound_sources,
        outputs={str(p):sha(p) for folder in [args.output,args.figures] for p in folder.iterdir() if p.is_file()}))
    print(json.dumps(dict(accepted=accepted,replays=len(rows),assessments=assessments)),flush=True)
    if not accepted:raise SystemExit(2)


if __name__=='__main__':main()
