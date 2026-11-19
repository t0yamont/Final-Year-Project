"""Audit the eight schedules and measure conditional effects of DP search settings."""
import argparse
from itertools import permutations, product
from pathlib import Path
from statistics import mean
from types import SimpleNamespace
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from benchmark_circuit_control import sha,save
from validate_regeneration import audit_replay
from verify_regeneration_dp import read,close


def contrasts(times, factors):
    edges = []
    for key, time in sorted(times.items()):
        for i,bit in enumerate(key):
            if bit=='0':
                other=key[:i]+'1'+key[i+1:]
                edges.append(dict(factor=factors[i],low=key,high=other,saving_s=time-times[other]))
    contributions={f:[] for f in factors}
    orders=[]
    total=times['000']-times['111']
    for order in permutations(range(3)):
        key='000';changes={}
        for i in order:
            other=key[:i]+'1'+key[i+1:]
            changes[factors[i]]=times[key]-times[other]
            key=other
        close(sum(changes.values()),total,'order does not recover endpoint difference')
        for f in factors: contributions[f].append(changes[f])
        orders.append(dict(order=[factors[i] for i in order],savings_s=changes))
    allocation={f:mean(v) for f,v in contributions.items()}
    close(sum(allocation.values()),total,'attribution mismatch')
    return dict(total_s=total,edges=edges,orders=orders,allocation_s=allocation,
                marginal_s={f:mean(e['saving_s'] for e in edges if e['factor']==f) for f in factors})


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',type=Path,default=Path('results/regeneration-dp-factorial-001'))
    ap.add_argument('--figures',type=Path,default=Path('figures/dissertation/regeneration-dp-factorial-v1'))
    a=ap.parse_args()
    contract=read(a.input/'contract.json');protocol=contract['protocol']
    parent=Path(protocol['parent']); pc=read(parent/'contract.json')
    checks=0;bound=set()
    for folder in (a.input,parent):
        manifest=read(folder/'manifest.json')
        for group in ('sources','inputs','outputs'):
            for path,digest in manifest[group].items():
                if sha(path)!=digest:raise ValueError('hash mismatch: '+path)
                checks+=1
        bound.update(Path(p).resolve() for p in manifest['outputs'])
    if pc!=contract['parent_config']:raise ValueError('parent mismatch')
    config=pc['config'];ref=read(config['reference_config']);vehicle=SimpleNamespace(**ref['vehicle'])
    cases=read(a.input/'metrics.json')['cases'];factors=protocol['factors']
    keys=[''.join(bits) for bits in product('01',repeat=3)]
    if sorted(cases)!=keys:raise ValueError('incomplete factorial')
    audits={};times={str(n):{} for n in (80,160,320)}
    for key,row in cases.items():
        endpoints=pc['protocol']['cases'];settings=row['settings']
        for i,fields in enumerate([['actions'],['width'],['speed_bin_mps','energy_bin_j']]):
            if any(settings[f]!=endpoints[int(key[i])][f] for f in fields):raise ValueError('factor mismatch')
        if len(row['actions'])!=config['action_blocks'] or not set(row['actions'])<=set(settings['actions']):raise ValueError('bad schedule')
        for cells in times:
            path=Path(row['traces'][cells])
            if path.resolve() not in bound:raise ValueError('unbound replay')
            r=read(path);json.dumps(r,allow_nan=False);trace=r['trace']
            if not r['feasible'] or [b['action'] for b in trace]!=row['actions']:raise ValueError('infeasible or wrong schedule')
            if max(b['max_node_cap_excess_mps'] for b in trace)>1e-5 or abs(trace[-1]['state']['speed_m_per_s']-config['initial_speed_mps'])>1e-5:
                raise ValueError('speed constraint')
            close(sum(b['duration_s'] for b in trace),r['duration_s'],'elapsed time')
            close(trace[-1]['state']['energy_j'],r['final_energy_j'],'final energy')
            audits[f'{key}/{cells}']=audit_replay(r,config,ref,vehicle)
            times[cells][key]=r['duration_s']
        close(times['80'][key],row['search_time_s'],'exact search replay')
    primary=contrasts(times['160'],factors);refined=contrasts(times['320'],factors)
    comparisons=[]
    for e,t in zip(primary['edges'],refined['edges'],strict=True):
        difference=abs(e['saving_s']-t['saving_s'])
        comparisons.append(dict(**e,refined_saving_s=t['saving_s'],grid_change_s=difference,passed=difference<=protocol['paired_gap_tolerance_s']))
    record=dict(hash_checks=checks,replays_checked=len(audits),audits=audits,times_s=times,primary=primary,refined=refined,
                edge_checks=comparisons,all_edges_passed=all(e['passed'] for e in comparisons))
    a.figures.mkdir(parents=True,exist_ok=False);save(a.figures/'verification.json',record)
    labels=['Action levels','Retained states','State bins']
    fig,axes=plt.subplots(1,2,figsize=(12,5),sharey=True)
    for b,ax in enumerate(axes):
        for w,width in enumerate([8,16]):
            y=[times['160'][f'{actions}{w}{b}'] for actions in (0,1)]
            ax.plot([3,5],y,'o-',label=f'{width} retained states')
            for x,v in zip([3,5],y):ax.annotate(f'{v:.3f}',(x,v),xytext=(0,7 if w else -14),textcoords='offset points',ha='center',fontsize=8)
        ax.set(title=['Original state bins','Finer state bins'][b],xlabel='Deployment levels',xticks=[3,5],xlim=(2.7,5.3));ax.margins(y=.15);ax.grid(alpha=.2);ax.legend(fontsize=8)
    axes[0].set_ylabel('Simulated lap time (s)')
    fig.suptitle('Sakhir | all eight DP schedules on 8,800 cells')
    def export(fig,name):
        fig.tight_layout()
        for ext in ['png','pdf']:fig.savefig(a.figures/f'{name}.{ext}',dpi=300)
        plt.close(fig)
    export(fig,'01_search_interactions')
    fig,axes=plt.subplots(1,3,figsize=(12,4.8),sharey=True)
    for f,label,ax in zip(factors,labels,axes):
        subset=[e for e in comparisons if e['factor']==f]
        for i,e in enumerate(subset):
            ax.plot([i-.08,i+.08],[1000*e['saving_s'],1000*e['refined_saving_s']],color='grey')
            ax.scatter(i-.08,1000*e['saving_s'],color='#176b8a',label='8,800 cells' if not i else None)
            ax.scatter(i+.08,1000*e['refined_saving_s'],color='#b86118',marker='x',label='17,600 cells' if not i else None)
        ax.axhline(0,color='black',lw=.8);ax.set(title=label,xticks=range(4),xticklabels=[e['low']+' to '+e['high'] for e in subset])
        ax.tick_params(axis='x',rotation=35,labelsize=8);ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Time saved by changing one setting (ms)');axes[0].legend(fontsize=8)
    fig.suptitle('Conditional effects | bits encode action levels, retained width and bin resolution')
    export(fig,'02_conditional_effects')
    save(a.figures/'manifest.json',dict(inputs={str(a.input/'manifest.json'):sha(a.input/'manifest.json')},
        sources={str(p):sha(p) for p in [Path(__file__),Path('scripts/verify_regeneration_dp.py'),Path('scripts/validate_regeneration.py'),Path('scripts/benchmark_circuit_control.py')]},
        outputs={str(p):sha(p) for p in a.figures.iterdir() if p.is_file()}))
    print(json.dumps(dict(replays=len(audits),passes=sum(e['passed'] for e in comparisons),allocation=primary['allocation_s'])))


if __name__=='__main__':main()
