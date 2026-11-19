"""Inspectably sourced descriptive figures for the completed three-seed study."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();manifest=json.loads((args.input/'manifest.json').read_text())
    for p,h in manifest['outputs'].items():
        if sha(p)!=h:raise ValueError('corrupt study output: '+p)
    metrics=json.loads((args.input/'metrics.json').read_text())
    if len(metrics['seeds'])!=3:raise ValueError('all three training seeds are required for this figure')
    seeds=sorted(metrics['seeds'],key=lambda s:s['seed']);colors=['#176b8a','#b86118','#805080'];markers=['o','s','^']
    args.output.mkdir(parents=True,exist_ok=False)
    fig,axes=plt.subplots(1,2,figsize=(13,5.2))
    for seed,color,marker in zip(seeds,colors,markers):
        rows=seed['checkpoints']
        axes[0].plot([r['step'] for r in rows],[r['fine_time_s'] for r in rows],color=color,marker=marker,label=f'Seed {seed["seed"]}')
    axes[0].axhline(metrics['fine_baselines_s']['full'],color='#555555',linestyle='--',label='Full request')
    axes[0].set(xlabel='Training steps per seed',ylabel='Deterministic fine-grid lap time (s)',title='Fixed checkpoint evaluations');axes[0].legend(fontsize=8)
    names=['half','full','spread','exit_boost'];zero=metrics['fine_baselines_s']['zero']
    gains=[zero-metrics['fine_baselines_s'][n] for n in names]
    finals=[s['final_deterministic']['fine_gain_s'] for s in seeds]
    axes[1].bar(np.arange(4),gains,color='#999999',width=.65,label='Fixed baselines')
    axes[1].bar(4,np.mean(finals),color='#d5e6ed',edgecolor='#176b8a',width=.65,label='PPO seed mean')
    axes[1].errorbar(4,np.mean(finals),yerr=np.std(finals,ddof=1),fmt='none',color='#176b8a',capsize=5,label='Â±1 sample SD (3 seeds)')
    for i,(value,color,marker) in enumerate(zip(finals,colors,markers)):
        axes[1].scatter(4+(i-1)*.13,value,color=color,marker=marker,s=42,zorder=4)
    axes[1].set_xticks(range(5),['Half','Full','Spread','Exit boost','PPO'])
    axes[1].axhline(0,color='#555555',linewidth=.8)
    axes[1].set(ylabel='Time saved versus zero request (s)',title='Final deterministic policy; all seeds');axes[1].legend(fontsize=8,loc='best')
    for ax in axes:ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('Longer GPU training on the fixed reference model | '+args.input.name)
    fig.text(.5,.015,'Three independent training seeds; final checkpoint predeclared. Error bar is descriptive SD, not a confidence interval.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.94))
    for ext in ['png','pdf']:fig.savefig(args.output/f'01_checkpoint_baseline_comparison.{ext}',dpi=300)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for i,(seed,color) in enumerate(zip(seeds,colors)):
        stochastic=seed['final_stochastic'];x=i+np.linspace(-.16,.16,len(stochastic))
        axes[0].scatter(x,[r['fine_time_s'] for r in stochastic],facecolors='none',edgecolors=color,s=45,label='Stochastic rollouts' if i==0 else None)
        axes[0].scatter(i,seed['final_deterministic']['fine_time_s'],color=color,marker='D',s=55,label='Deterministic policy' if i==0 else None)
        axes[1].scatter(x,[r['fine_final_energy_j']/1e6 for r in stochastic],facecolors='none',edgecolors=color,s=45)
        axes[1].scatter(i,seed['final_deterministic']['fine_final_energy_j']/1e6,color=color,marker='D',s=55)
    axes[0].axhline(metrics['fine_baselines_s']['full'],color='#555555',linestyle='--',label='Full-request baseline')
    axes[0].set(ylabel='Fine-grid lap time (s)',title='Action sampling versus deterministic action');axes[0].legend(fontsize=8)
    axes[1].axhline(.1,color='#555555',linestyle='--',label='Reserve');axes[1].set(ylabel='Terminal battery energy (MJ)',title='Battery use by evaluation mode',ylim=(0,2.1));axes[1].legend(fontsize=8)
    for ax in axes:ax.set_xticks(range(3),[f'Seed {s["seed"]}' for s in seeds]);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle('Final GPU policies: five fixed action-noise seeds per training seed')
    fig.text(.5,.015,'Stochastic rollouts are nested within each training seed. Same55 decisions, physics, initial energy and terminal constraints.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.94))
    for ext in ['png','pdf']:fig.savefig(args.output/f'02_stochastic_deterministic_energy.{ext}',dpi=300)
    plt.close(fig)
    if 'refinement' in seeds[0]['final_deterministic']:
        protocol=json.loads((args.input/'contract.json').read_text())['protocol']
        limit=protocol['refinement']['max_paired_advantage_error_s']*1000
        fig,axes=plt.subplots(1,2,figsize=(12,5))
        for i,(seed,color) in enumerate(zip(seeds,colors)):
            r=seed['final_deterministic']['refinement']
            axes[0].plot([i-.12,i+.12],[1000*r['fine_advantage_s'],1000*r['refined_advantage_s']],color=color)
            axes[0].scatter(i-.12,1000*r['fine_advantage_s'],color=color,marker='o',label='8,800 cells' if i==0 else None)
            axes[0].scatter(i+.12,1000*r['refined_advantage_s'],color=color,marker='D',label='17,600 cells' if i==0 else None)
            stochastic=seed['final_stochastic'];x=i+np.linspace(-.16,.16,len(stochastic))
            axes[1].scatter(x,[1000*r['refinement']['paired_advantage_discrepancy_s'] for r in stochastic],facecolors='none',edgecolors=color,label='Stochastic pairs' if i==0 else None)
            axes[1].scatter(i,1000*r['paired_advantage_discrepancy_s'],color=color,marker='D',label='Deterministic pair' if i==0 else None)
        axes[0].axhline(0,color='#555555',linewidth=.8)
        axes[0].set(ylabel='Advantage over matched full request (ms)',title='Final deterministic policies; both grids')
        axes[1].axhline(limit,color='#aa3333',linestyle='--',label=f'Predeclared {limit:g} ms tolerance')
        axes[1].set(ylabel='Absolute change in paired advantage (ms)',title='Fine-to-refined comparison uncertainty',ylim=(0,None))
        for ax in axes:ax.set_xticks(range(3),[f'Seed {s["seed"]}' for s in seeds]);ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
        status='PASS' if metrics['all_seeds_completed_and_passed'] else 'FAIL (all completed seeds retained)'
        fig.suptitle('Regeneration numerical comparison | study gate: '+status)
        fig.text(.5,.015,'Primary endpoint remains 8,800 cells. Refinement is a validation check; no checkpoint or seed selection.',ha='center',fontsize=9)
        fig.tight_layout(rect=(0,.06,1,.94))
        for ext in ['png','pdf']:fig.savefig(args.output/f'03_paired_grid_checks.{ext}',dpi=300)
        plt.close(fig)
    record=dict(inputs={str(args.input/'manifest.json'):sha(args.input/'manifest.json')},source_sha256=sha(__file__),
                outputs={str(p):sha(p) for p in args.output.iterdir() if p.is_file()})
    (args.output/'manifest.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())


if __name__=='__main__':main()
