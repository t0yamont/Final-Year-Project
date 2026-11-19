"""Independent saved-trace guard verification and dissertation figures."""
import argparse
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def trace(p):
    with gzip.open(p,'rt',encoding='utf-8') as f:return json.load(f)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def close(a,b,tol=1e-8):
    if not math.isfinite(a) or not math.isfinite(b) or abs(a-b)>tol:
        raise ValueError(f'arithmetic mismatch: {a}, {b}')


def verify(folder):
    manifest=read(folder/'manifest.json');count=0
    for group in ('inputs','sources','outputs'):
        for p,h in manifest[group].items():
            if sha(p)!=h:raise ValueError('hash mismatch: '+p)
            count+=1
    contract=read(folder/'contract.json');m=read(folder/'metrics.json');protocol=contract['protocol']
    policies=protocol['fixed_policies']+[f'ppo_seed{s}' for s in protocol['training_seeds']]
    expected={(s['name'],c['blocks'],g,p) for s in protocol['scenarios'] for c in protocol['cadences']
              for g in ('coarse','fine') for p in policies}
    keys=[(r['scenario'],r['blocks'],r['grid'],r['policy']) for r in m['results']]
    if len(set(keys))!=len(keys) or set(keys)!=expected:raise ValueError('incomplete/duplicate replay matrix')
    rows=dict(zip(keys,m['results']));saved={};physical={};errors=[]
    initial=protocol['conditions'];ref=contract['reference'];budget=protocol['guard']['protected_energy_j']
    if {p['seed'] for p in contract['policies']}!=set(protocol['training_seeds']):raise ValueError('missing CUDA policy record')
    if any(not p['policy_device'].startswith('cuda') for p in contract['policies']):raise ValueError('non-CUDA policy')
    for key,row in rows.items():
        if row['status']!='completed':raise ValueError('incomplete replay')
        rec=trace(folder/row['file']);saved[key]=rec;steps=rec['trace'];blocks=row['blocks']
        if len(steps)!=blocks:raise ValueError('incorrect action count')
        grid=trace(folder/row['grid_file'])
        if len(grid['cell_speed_cap_mps'])!=blocks*row['cells_per_block']:raise ValueError('incorrect physical grid')
        v,e,t=initial['initial_speed_mps'],initial['initial_energy_j'],0.
        residuals=[];battery=[];overrides=changes=depletions=protected=0
        for i,step in enumerate(steps):
            state=step['state'];guard=step['terminal_guard'];tail=i>=blocks-blocks//55
            floor=initial['reserve_j']+(0. if tail else budget)
            close(guard['reserve_floor_j'],floor);close(guard['physical_reserve_j'],initial['reserve_j'])
            proposed=guard['proposed_action'];issued=1. if tail else proposed
            if not math.isfinite(proposed) or not 0<=proposed<=1:raise ValueError('invalid proposed action')
            close(guard['issued_action'],issued);close(step['action'],issued)
            if guard['protected_floor_active']!= (not tail) or guard['terminal_request_override']!=tail:raise ValueError('wrong guard schedule')
            changed=issued!=proposed
            if guard['action_changed']!=changed:raise ValueError('wrong override classification')
            n=sum(ev['kind']=='depletion' for ev in step['events'])
            intervention=bool(not tail and issued>0 and (n or e<=floor+1e-8))
            if guard['depletion_events']!=n or guard['protected_depletion_intervention']!=intervention:raise ValueError('wrong floor-intervention classification')
            overrides+=tail;changes+=changed;depletions+=n;protected+=intervention
            if state['energy_j']<floor-1e-5 or state['energy_j']>e+1e-5:raise ValueError('protected floor or battery monotonicity violation')
            work=step['base_work_j']+step['electrical_work_j']-step['drag_work_j']-step['friction_braking_work_j']
            residuals.append(.5*ref['vehicle']['mass_kg']*(state['speed_m_per_s']**2-v*v)-work)
            battery.append(step['electrical_work_j']-ref['vehicle']['discharge_efficiency']*(e-state['energy_j']))
            close(step['battery_draw_j'],e-state['energy_j'])
            if step['duration_s']<=0 or step['max_node_cap_excess_mps']>1e-5:raise ValueError('duration/cap violation')
            cell=(i+1)*row['cells_per_block']-1
            if state['speed_m_per_s']>grid['cell_speed_cap_mps'][cell]+1e-5:raise ValueError('boundary cap violation')
            close(state['distance_m'],grid['distance_m'][cell+1],1e-6)
            t+=step['duration_s'];close(t,state['elapsed_s']);v,e=state['speed_m_per_s'],state['energy_j']
        close(t,rec['duration_s']);close(t,row['duration_s']);close(e,row['final_energy_j']);close(e,rec['final_energy_j'])
        terminal=v-initial['terminal_speed_mps'];close(terminal,row['terminal_speed_error_mps'])
        if not all(math.isfinite(x) for x in residuals+battery+[terminal,e]):raise ValueError('non-finite trajectory')
        if max(map(abs,residuals))>1 or abs(sum(residuals))>1 or max(map(abs,battery))>.01 or abs(sum(battery))>.01:raise ValueError('work-energy/battery identity failed')
        feasible=abs(terminal)<1e-5
        if feasible!=row['feasible'] or feasible!=rec['feasible'] or feasible!=row['audit']['passed']:raise ValueError('feasibility classification mismatch')
        physical[key]=feasible
        zero=rows[key[0],blocks,key[2],'zero']['duration_s']
        close(row['reward_reference_time_s'],zero);close(rec['reward_reference_time_s'],zero)
        close(rec['reward_sum'],zero-t)
        if row['policy']=='zero':close(rec['integration_reward_sum_before_reference_assignment'],-t)
        summary=dict(terminal_override_blocks=overrides,action_changed_blocks=changes,protected_depletion_blocks=protected,depletion_events=depletions)
        if row['guard_interventions']!=summary:raise ValueError('intervention summary mismatch')
        errors.append(dict(file=row['file'],terminal_speed_error_mps=terminal,global_work_energy_residual_j=sum(residuals),global_battery_error_j=sum(battery)))
    casekeys=[(c['scenario'],c['blocks']) for c in m['cases']]
    if len(set(casekeys))!=len(casekeys) or set(casekeys)!={(s,b) for s,b,_,_ in expected}:raise ValueError('incomplete cases')
    for c in m['cases']:
        s,b=c['scenario'],c['blocks'];pairs=c['numerical_pairs']
        if len(pairs)!=len(policies) or {p['policy'] for p in pairs}!=set(policies):raise ValueError('incomplete grid pairs')
        for pair in pairs:
            p=pair['policy'];coarse=rows[s,b,'coarse',p]['duration_s'];fine=rows[s,b,'fine',p]['duration_s']
            gap=abs((rows[s,b,'coarse','zero']['duration_s']-coarse)-(rows[s,b,'fine','zero']['duration_s']-fine))
            relative=abs(coarse-fine)/fine;close(gap,pair['gain_discrepancy_s']);close(relative,pair['relative_lap_time_error'])
            passed=gap<=.05 and relative<=.005 and all(physical[s,b,g,n] for g in ('coarse','fine') for n in (p,'zero'))
            if passed!=pair['passed']:raise ValueError('pair gate mismatch')
        if c['passed']!=all(p['passed'] for p in pairs):raise ValueError('case acceptance mismatch')
        if all(physical[s,b,'fine',p] for p in policies):
            best=min(protocol['fixed_policies'],key=lambda p:rows[s,b,'fine',p]['duration_s'])
            if best!=c['strongest_fixed_policy']:raise ValueError('wrong strongest guarded baseline')
            close(c['strongest_fixed_time_s'],rows[s,b,'fine',best]['duration_s'])
            gains=[rows[s,b,'fine',best]['duration_s']-rows[s,b,'fine',f'ppo_seed{i}']['duration_s'] for i in protocol['training_seeds']]
            close(statistics.mean(gains),c['ppo_advantage_over_strongest_fixed_s']['mean']);close(statistics.stdev(gains),c['ppo_advantage_over_strongest_fixed_s']['sample_sd'])
            if set(c['per_seed_advantage_s'])!={f'ppo_seed{i}' for i in protocol['training_seeds']}:raise ValueError('missing seed advantage')
            for seed,gain in zip(protocol['training_seeds'],gains):close(c['per_seed_advantage_s'][f'ppo_seed{seed}'],gain)
            times=[rows[s,b,'fine',f'ppo_seed{i}']['duration_s'] for i in protocol['training_seeds']]
            close(c['ppo_fine_lap_time_s']['mean'],statistics.mean(times));close(c['ppo_fine_lap_time_s']['sample_sd'],statistics.stdev(times))
        elif 'ppo_advantage_over_strongest_fixed_s' in c:raise ValueError('infeasible group aggregated')
    if set(m['nominal_fine_110_minus55_time_s'])!=set(policies):raise ValueError('missing cadence differences')
    for p,delta in m['nominal_fine_110_minus55_time_s'].items():close(delta,rows['nominal',110,'fine',p]['duration_s']-rows['nominal',55,'fine',p]['duration_s'])
    if m['all_cases_completed_and_passed']!=all(c['passed'] for c in m['cases']):raise ValueError('study gate mismatch')
    audit=dict(hash_checks=count,replays_checked=len(rows),physically_feasible_replays=sum(physical.values()),
               all_cases_passed=m['all_cases_completed_and_passed'],max_abs_energy_residual_j=max(abs(r['global_work_energy_residual_j']) for r in errors),
               max_abs_battery_error_j=max(abs(r['global_battery_error_j']) for r in errors),replay_checks=errors)
    return contract,m,saved,audit


def plot(folder,output,contract,m,saved):
    colors=['#176b8a','#b86118','#805080'];markers=['o','s','^'];oldroot=Path(contract['protocol']['sensitivity_run'])
    fig,axes=plt.subplots(1,2,figsize=(12,5.5))
    for i,c in enumerate(m['cases']):
        if 'ppo_advantage_over_strongest_fixed_s' not in c:
            axes[0].text(.03,i,'Infeasible comparison',transform=axes[0].get_yaxis_transform());continue
        stats=c['ppo_advantage_over_strongest_fixed_s']
        axes[0].errorbar(stats['mean'],i,xerr=stats['sample_sd'],fmt='D',color='#444444',capsize=4,label='Mean ± sample SD' if i==0 else None)
        for seed,(color,marker) in enumerate(zip(colors,markers)):
            axes[0].scatter(c['per_seed_advantage_s'][f'ppo_seed{seed}'],i+(seed-1)*.13,color=color,marker=marker,label=f'Seed {seed}' if i==0 else None)
    axes[0].set_yticks(range(len(m['cases'])),[('Nominal' if c['scenario']=='nominal' else 'Higher drag')+f' / {c["blocks"]}' for c in m['cases']]);axes[0].invert_yaxis()
    axes[0].axvline(0,color='#555555',linestyle='--');axes[0].set(title='PPO + guard versus guarded baselines',xlabel='Time saved versus strongest guarded baseline (s)');axes[0].legend(fontsize=8,loc='best');axes[0].grid(axis='x',alpha=.2)
    policies=contract['protocol']['fixed_policies']+[f'ppo_seed{s}' for s in range(3)]
    for i,p in enumerate(policies):
        old=trace(oldroot/f'drag_plus10_blocks-55_fine_{p}.json.gz');new=saved['drag_plus10',55,'fine',p]
        a=old['trace'][-1]['state']['speed_m_per_s'];b=new['trace'][-1]['state']['speed_m_per_s']
        axes[1].plot([a,b],[i,i],color='#999999',linewidth=1)
        axes[1].scatter(a,i,facecolors='none',edgecolors='#555555',marker='o',s=40,label='Original, unguarded' if i==0 else None)
        axes[1].scatter(b,i,color='#176b8a',marker='s',s=30,label='Same policy + guard' if i==0 else None)
    axes[1].set_yticks(range(len(policies)),[p.replace('ppo_seed','PPO seed ').replace('_',' ').capitalize() if not p.startswith('ppo') else p.replace('ppo_seed','PPO seed ') for p in policies]);axes[1].invert_yaxis()
    axes[1].axvline(70,color='#555555',linestyle='--');axes[1].set(title='Higher drag: terminal speed at 55 decisions',xlabel='Final speed (m/s); target = 70');axes[1].legend(fontsize=8,loc='best');axes[1].grid(axis='x',alpha=.2)
    fig.suptitle('Fixed 0.25 MJ terminal protection | '+folder.name)
    fig.text(.5,.025,'All guarded comparisons use the same guard and original 2 MJ initial energy / 0.1 MJ reserve.\nGuarded zero requests terminal assistance. Error bars are descriptive SD across three seeds, not confidence intervals.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.10,1,.94))
    for ext in ('png','pdf'):fig.savefig(output/f'01_feasibility_and_comparison.{ext}',dpi=300)
    plt.close(fig)
    old=trace(oldroot/'drag_plus10_blocks-55_fine_ppo_seed0.json.gz');new=saved['drag_plus10',55,'fine','ppo_seed0'];steps=new['trace']
    fig,axes=plt.subplots(1,2,figsize=(12,4.8))
    for rec,color,label,style in [(old,'#777777','Unguarded seed 0','--'),(new,'#176b8a','Seed 0 + guard','-')]:
        axes[0].plot([0]+[s['state']['distance_m']/1000 for s in rec['trace']],[2]+[s['state']['energy_j']/1e6 for s in rec['trace']],color=color,label=label,linestyle=style)
    start=steps[-2]['state']['distance_m']/1000;end=steps[-1]['state']['distance_m']/1000
    axes[0].step([0,start,end],[.35,.1,.1],where='post',color='#b86118',linestyle=':',label='Guard deployment floor')
    axes[0].set(title='Higher drag, illustrative seed 0: battery',xlabel='Distance (km)',ylabel='Simulated battery energy (MJ)',ylim=(0,2.1));axes[0].legend(fontsize=8);axes[0].grid(alpha=.2)
    x=list(range(1,len(steps)+1))
    axes[1].step(x,[s['terminal_guard']['proposed_action'] for s in steps],where='mid',color='#777777',linestyle='--',label='Policy request')
    axes[1].step(x,[s['action'] for s in steps],where='mid',color='#176b8a',label='Guard-issued request')
    axes[1].plot(x,[s['electrical_work_j']/s['duration_s']/contract['reference']['vehicle']['electrical_limit_w'] for s in steps],color='#b86118',label='Mean delivered power / limit')
    axes[1].set(title='Requested and delivered deployment',xlabel='Action block (55 per lap)',ylabel='Fraction of electrical-power limit',ylim=(-.03,1.08));axes[1].legend(fontsize=8);axes[1].grid(alpha=.2)
    fig.suptitle('Guard intervention trace | '+folder.name)
    fig.text(.5,.02,'Seed 0 selected for illustration, not as the best run. Delivered power also reflects braking, cruise and depletion.\nThe final action block releases protected energy; no battery reset or instantaneous speed correction is applied.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.12,1,.93))
    for ext in ('png','pdf'):fig.savefig(output/f'02_guard_energy_actions.{ext}',dpi=300)
    plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    contract,m,saved,audit=verify(args.input);args.output.mkdir(parents=True,exist_ok=False);plot(args.input,args.output,contract,m,saved)
    (args.output/'verification.json').write_bytes((json.dumps(audit,indent=2)+'\n').encode('utf-8'))
    manifest=dict(inputs={str(args.input/'manifest.json'):sha(args.input/'manifest.json')},source_sha256=sha(__file__),outputs={str(p):sha(p) for p in args.output.iterdir() if p.is_file()})
    (args.output/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({k:v for k,v in audit.items() if k!='replay_checks'}))


if __name__=='__main__':main()
