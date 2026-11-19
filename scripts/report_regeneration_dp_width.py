"""Verify width-only DP trials and plot adjacent-width differences on both grids."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from benchmark_circuit_control import sha, save
from validate_regeneration import audit_replay
from verify_regeneration_dp import read, close


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,default=Path('results/regeneration-dp-width-001'))
    parser.add_argument('--figures',type=Path,default=Path('figures/dissertation/regeneration-dp-width-v1'))
    args=parser.parse_args(); contract=read(args.run/'contract.json');p=contract['protocol']
    hashes=0;outputs=set()
    for folder in [args.run,Path(p['parent'])]:
        manifest=read(folder/'manifest.json')
        for group,mapping in manifest.items():
            for path,digest in mapping.items():
                if sha(path)!=digest:raise ValueError('hash mismatch '+path)
                hashes+=1
                if group=='outputs':outputs.add(Path(path).resolve())
    config=contract['config'];reference=read(config['reference_config']);vehicle=SimpleNamespace(**reference['vehicle'])
    cases=read(args.run/'metrics.json')['cases']
    base=cases[str(p['widths'][0])]['settings'];audits={};times={}
    for width in p['widths']:
        row=cases[str(width)];settings=row['settings']
        if width!=settings['width'] or any(settings[k]!=base[k] for k in ('actions','speed_bin_mps','energy_bin_j')):
            raise ValueError('factor mismatch')
        if (len(row['actions'])!=config['action_blocks'] or not set(row['actions'])<=set(base['actions']) or
            len(row['layers'])!=config['action_blocks'] or max(layer['retained'] for layer in row['layers'])>width or
            sum(layer['expansions'] for layer in row['layers'])!=row['transitions']):
            raise ValueError('invalid search budget or action set')
        times[width]={}
        for cells in p['replay_cells']:
            path=Path(row['traces'][str(cells)])
            if path.resolve() not in outputs:raise ValueError('trace missing from manifests')
            trace=read(path);json.dumps(trace,allow_nan=False)
            if [b['action'] for b in trace['trace']]!=row['actions'] or not trace['feasible']:raise ValueError('invalid replay')
            end=trace['trace'][-1]['state']
            if abs(end['speed_m_per_s']-config['initial_speed_mps'])>1e-5 or max(b['max_node_cap_excess_mps'] for b in trace['trace'])>1e-5:
                raise ValueError('invalid speed')
            elapsed=sum(b['duration_s'] for b in trace['trace'])
            close(elapsed,trace['duration_s'],'trace duration')
            close(end['energy_j'],trace['final_energy_j'],'trace battery')
            times[width][cells]=elapsed
            audits[f'{width}/{cells}']=audit_replay(trace,config,reference,vehicle)
        close(times[width][p['search_cells']],row['search_time_s'],'selected replay')
    rows=[]
    for low,high in zip(p['widths'],p['widths'][1:]):
        a=times[low][p['primary_cells']]-times[high][p['primary_cells']]
        b=times[low][320]-times[high][320]
        rows.append(dict(low=low,high=high,primary_gain_s=a,refined_gain_s=b,change_s=abs(a-b),
                         grid_pass=abs(a-b)<=p['gap_change_s'],width_stable=max(abs(a),abs(b))<=p['stability_s']))
    summary=dict(times=times,pairs=rows,hash_checks=hashes,audits=audits)
    args.figures.mkdir(parents=True,exist_ok=False);save(args.figures/'verification.json',summary)
    fig,(a,b)=plt.subplots(1,2,figsize=(10.5,4.4))
    for cells,color in [(160,'#176b8a'),(320,'#a14f13')]:
        a.plot(p['widths'],[times[w][cells] for w in p['widths']],marker='o',label=f'{cells*55:,} cells',color=color)
    a.set(xlabel='Maximum retained states per block',xticks=p['widths'],ylabel='Lap time (s)',title='Fixed five-action search on Sakhir')
    a.legend()
    for index,(key,label) in enumerate([('primary_gain_s','8,800 cells'),('refined_gain_s','17,600 cells')]):
        b.scatter([i+(index-.5)*.08 for i in range(len(rows))],[1000*r[key] for r in rows],label=label)
    b.axhspan(-50,50,color='#e5eadf',label='Within 50 ms');b.axhline(0,color='grey',lw=.8)
    b.set(xlim=(-.45,1.45),xticks=[0,1],xticklabels=['16 to 32','32 to 64'],xlabel='Change in width',
          ylabel='Lap time saved (ms)',title='Adjacent-width comparison')
    b.legend(fontsize=8)
    for ax in (a,b):ax.grid(axis='y',alpha=.25)
    fig.tight_layout()
    for ext in ('png','pdf'):fig.savefig(args.figures/f'width_comparison.{ext}',dpi=300)
    plt.close(fig)
    save(args.figures/'manifest.json',dict(inputs={str(args.run/'manifest.json'):sha(args.run/'manifest.json')},
         sources={str(k):sha(k) for k in [Path(__file__),Path('scripts/validate_regeneration.py'),Path('scripts/verify_regeneration_dp.py')]},
         outputs={str(k):sha(k) for k in args.figures.iterdir() if k.is_file()}))
    print(json.dumps(dict(times=times,pairs=rows)))


if __name__=='__main__':main()
