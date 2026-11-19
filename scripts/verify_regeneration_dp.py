"""Audit saved DP candidates and draw dissertation comparisons; never rerun search."""
import argparse
import gzip
import json
import math
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from benchmark_circuit_control import sha, save
from validate_regeneration import audit_replay


def read(path):
    with (gzip.open(path, 'rt') if str(path).endswith('.gz') else open(path)) as stream:
        return json.load(stream)


def close(a, b, label):
    if not math.isfinite(a) or not math.isfinite(b) or abs(a-b)>1e-8:
        raise ValueError(label)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path('results/regeneration-dp-001'))
    parser.add_argument('--figures',type=Path,default=Path('figures/dissertation/regeneration-dp-v1'))
    args=parser.parse_args()
    checked=0
    def manifest(folder):
        nonlocal checked
        data=read(folder/'manifest.json')
        for group in ('inputs','sources','outputs'):
            if not data[group]:raise ValueError('empty manifest '+group)
            for path,digest in data[group].items():
                if sha(path)!=digest:raise ValueError('hash mismatch: '+path)
                checked+=1
        return data
    run_manifest=manifest(args.input)
    baseline=Path('results/regeneration-validation-001')
    multiseed=Path('results/regeneration-multiseed-001')
    manifest(baseline);manifest(multiseed)
    config=read(baseline/'contract.json')['config']
    contract=read(args.input/'contract.json')
    if 'config' in contract and contract['config']!=config:raise ValueError('DP model differs from comparison model')
    protocol=contract['protocol']
    gates=protocol['comparison_gates']
    limits=dict(max_paired_advantage_error_s=gates['paired_gap_change_s'],max_relative_lap_time_error=gates['relative_lap_change'],max_terminal_energy_error_j=gates['terminal_energy_change_j'],max_recovery_error_j=gates['recovered_change_j'])
    reference=read(config['reference_config']);vehicle=SimpleNamespace(**reference['vehicle'])
    audits=[]
    def audit(path,actions=None):
        result=read(path);trace=result['trace']
        json.dumps(result,allow_nan=False)
        if len(trace)!=55 or not result['feasible']:raise ValueError('infeasible/incomplete replay: '+str(path))
        independent=audit_replay(result,config,reference,vehicle)
        elapsed=0.
        global_work=0.
        for i,block in enumerate(trace):
            if actions is not None and block['action']!=actions[i]:raise ValueError('action mismatch: '+str(path))
            if not 0<=block['action']<=1:raise ValueError('action bounds')
            duration=block['state']['elapsed_s']-elapsed
            if duration<=0:raise ValueError('nonpositive duration')
            close(duration,block['duration_s'],'block duration mismatch')
            elapsed=block['state']['elapsed_s']
            global_work+=block['base_work_j']+block['electrical_work_j']-block['drag_work_j']-block['friction_braking_work_j']-block.get('regenerative_braking_work_j',0.)
            draw=block['electrical_work_j']/vehicle.discharge_efficiency
            close(block['battery_discharged_j'],draw,'discharge identity')
            close(block['charging_loss_j'],block['regenerative_braking_work_j']-block['battery_recovered_j'],'charging loss identity')
            if draw>config['regeneration']['max_power_w']*duration/vehicle.discharge_efficiency+1e-5:raise ValueError('deployment power violation')
            if block['max_node_cap_excess_mps']>1e-5:raise ValueError('speed cap violation')
        close(sum(b['duration_s'] for b in trace),result['duration_s'],'total duration mismatch')
        close(elapsed,result['duration_s'],'terminal duration mismatch')
        close(trace[-1]['state']['energy_j'],result['final_energy_j'],'terminal energy mismatch')
        if abs(trace[-1]['state']['speed_m_per_s']-config['initial_speed_mps'])>1e-5:raise ValueError('terminal speed violation')
        global_residual=.5*vehicle.mass_kg*(trace[-1]['state']['speed_m_per_s']**2-config['initial_speed_mps']**2)-global_work
        if abs(global_residual)>1:raise ValueError('global work balance')
        audits.append(dict(file=str(path),duration_s=elapsed,global_work_residual_j=global_residual,**independent))
        return result
    metrics=read(args.input/'metrics.json');seed_metrics=read(multiseed/'metrics.json')
    fullrow=next(r for r in read(baseline/'metrics.json')['results'] if r['cells']==160 and r['policy']=='full')
    comparators={'full':{160:audit(baseline/fullrow['file']),320:audit(multiseed/'refined_comparator.json.gz')}}
    close(comparators['full'][160]['duration_s'],fullrow['duration_s'],'full metric mismatch')
    if len(seed_metrics['seeds'])!=3:raise ValueError('expected all three PPO seeds')
    for seed in seed_metrics['seeds']:
        folder=multiseed/f"seed-{seed['seed']}";manifest(folder)
        final=seed['final_deterministic'];step=final['step'];name=f"PPO seed {seed['seed']}"
        comparators[name]={cells:audit(folder/f'checkpoint_{step}_deterministic_{grid}.json.gz') for cells,grid in [(160,'fine'),(320,'refined')]}
        close(comparators[name][160]['duration_s'],final['fine_time_s'],'PPO fine metric mismatch')
        close(comparators[name][320]['duration_s'],final['refinement']['refined_time_s'],'PPO refined metric mismatch')
    cases={};summaries=[]
    rows=metrics['cases']
    if {r['name'] for r in rows}!={'basic','refined'} or len(rows)!=2:raise ValueError('expected both fixed candidates')
    for row in rows:
        name=row['name'];actions=row['actions']
        if len(actions)!=55 or not all(math.isfinite(a) and 0<=a<=1 for a in actions):raise ValueError('invalid candidate actions')
        # The rollout interface represents requests as float32; require those exact saved values.
        actions=[float(np.float32(a)) for a in actions]
        replays={}
        for cells in (80,160,320):
            path=args.input/f'{name}_{cells}.json.gz'
            if not any(Path(p).resolve()==path.resolve() for p in run_manifest['outputs']):raise ValueError('unbound candidate replay')
            replays[cells]=audit(path,actions)
        close(replays[80]['duration_s'],row['search_time_s'],'search-grid time mismatch')
        if row['transitions']!=sum(layer['expansions'] for layer in row['layers']):raise ValueError('transition count mismatch')
        cases[name]=replays
        fine,refined=replays[160],replays[320]
        checks=dict(relative_lap_time_error=abs(fine['duration_s']-refined['duration_s'])/refined['duration_s'],
                    terminal_energy_discrepancy_j=abs(fine['final_energy_j']-refined['final_energy_j']),
                    recovery_discrepancy_j=abs(sum(b.get('battery_recovered_j',0) for b in fine['trace'])-sum(b.get('battery_recovered_j',0) for b in refined['trace'])))
        comparisons={}
        for label,pair in comparators.items():
            a=pair[160]['duration_s']-fine['duration_s'];b=pair[320]['duration_s']-refined['duration_s']
            comparisons[label]=dict(advantage_160_s=a,advantage_320_s=b,paired_advantage_discrepancy_s=abs(a-b),passed=abs(a-b)<=limits['max_paired_advantage_error_s'])
        passed=checks['relative_lap_time_error']<=limits['max_relative_lap_time_error'] and checks['terminal_energy_discrepancy_j']<=limits['max_terminal_energy_error_j'] and checks['recovery_discrepancy_j']<=limits['max_recovery_error_j'] and all(c['passed'] for c in comparisons.values())
        summaries.append(dict(name=name,primary=name=='refined',times_s={str(c):r['duration_s'] for c,r in replays.items()},comparisons=comparisons,refinement=checks,refinement_passed=passed,search_time_s=row['search_time_s'],wall_seconds=row['wall_seconds'],transitions=row['transitions']))
    stability=abs(cases['basic'][160]['duration_s']-cases['refined'][160]['duration_s'])
    args.figures.mkdir(parents=True,exist_ok=False)
    record=dict(primary_candidate='refined',primary_cells_per_block=160,cases=summaries,hash_checks=checked,replays_checked=len(audits),audits=audits,
                thresholds=limits,
                search_stability=dict(absolute_primary_grid_time_difference_s=stability,threshold_s=protocol['search_stability_s'],passed=stability<=protocol['search_stability_s'],interpretation='Search stability diagnostic only; no global optimality claim'),
                scope=config['interpretation'],script_sha256=sha(__file__))
    save(args.figures/'verification.json',record)
    figures=[]
    def finish(fig,name):
        fig.tight_layout(rect=(0,.05,1,1))
        fig.text(.5,.012,'Assumed reference model; refined DP candidate designated primary. No global optimum claim.',ha='center',fontsize=8)
        for ext in ('png','pdf'):
            path=args.figures/f'{name}.{ext}';fig.savefig(path,dpi=300);figures.append(path)
        plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    all_series={**comparators,**cases}
    for name,pair in all_series.items():
        axes[0].plot([160,320],[pair[c]['duration_s'] for c in (160,320)],'o-',label=name)
    axes[0].set(xlabel='Cells per action block',ylabel='Simulated lap time (s)',title='All final deterministic PPO seeds and DP candidates');axes[0].legend(fontsize=7)
    for row in summaries:
        axes[1].plot(range(4),[c['advantage_160_s'] for c in row['comparisons'].values()],'o-',label=row['name']+' DP')
    axes[1].axhline(0,color='black',lw=.7);axes[1].set_xticks(range(4),list(comparators),rotation=20)
    axes[1].set(ylabel='Comparator time minus DP time (s)',title='Primary grid paired advantage');axes[1].legend()
    for ax in axes:ax.grid(alpha=.2)
    finish(fig,'01_comparison')
    fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True)
    for name,pair in cases.items():
        trace=pair[160]['trace'];distance=[b['state']['distance_m']/1000 for b in trace]
        axes[0].stairs([b['action'] for b in trace],[0]+distance,label=name+' DP')
        axes[1].plot([0]+distance,[reference['initial_energy_j']/1e6]+[b['state']['energy_j']/1e6 for b in trace],label=name+' DP')
        axes[2].plot([0]+distance,np.r_[0,np.cumsum([b['battery_recovered_j'] for b in trace])]/1e6,label=name+' DP')
    for ax,label in zip(axes,['Deployment request','Battery energy (MJ)','Cumulative recovered energy (MJ)']):ax.set_ylabel(label);ax.grid(alpha=.2);ax.legend()
    axes[0].set_title('Saved 160-cell replay strategies; 55 action blocks');axes[2].set_xlabel('Distance (km)')
    finish(fig,'02_strategy')
    outputs=[args.figures/'verification.json']+figures
    save(args.figures/'manifest.json',dict(inputs={str(args.input/'manifest.json'):sha(args.input/'manifest.json')},sources={str(Path(__file__)):sha(__file__)},outputs={str(p):sha(p) for p in outputs}))
    print(json.dumps(dict(primary_candidate='refined',cases=[dict(name=r['name'],refinement_passed=r['refinement_passed']) for r in summaries],search_stability=record['search_stability'])))


if __name__=='__main__':main()
