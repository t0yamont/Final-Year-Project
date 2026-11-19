"""Independent arithmetic and provenance audit of a completed multi-seed study."""
import argparse,gzip,hashlib,json,math,statistics
from pathlib import Path
from types import SimpleNamespace
from validate_regeneration import audit_replay


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def replay(p):
    with gzip.open(p,'rt') as f:return json.load(f)
def close(a,b,label):
    if not math.isfinite(a) or not math.isfinite(b) or abs(a-b)>1e-8:raise ValueError(label)
def finite(value):
    if isinstance(value,dict):return all(finite(v) for v in value.values())
    if isinstance(value,list):return all(finite(v) for v in value)
    return not isinstance(value,(float,int)) or math.isfinite(value)


def refinement_check(fine,refined,fine_base,refined_base,limits):
    a=fine_base-fine['duration_s'];b=refined_base-refined['duration_s']
    result=dict(refined_time_s=refined['duration_s'],refined_final_energy_j=refined['final_energy_j'],
        fine_advantage_s=a,refined_advantage_s=b,paired_advantage_discrepancy_s=abs(a-b),
        relative_lap_time_error=abs(fine['duration_s']-refined['duration_s'])/refined['duration_s'],
        terminal_energy_discrepancy_j=abs(fine['final_energy_j']-refined['final_energy_j']),
        recovery_discrepancy_j=abs(sum(t.get('battery_recovered_j',0.) for t in fine['trace'])-
                                   sum(t.get('battery_recovered_j',0.) for t in refined['trace'])))
    checks=[('paired_advantage_discrepancy_s','max_paired_advantage_error_s'),
        ('relative_lap_time_error','max_relative_lap_time_error'),('terminal_energy_discrepancy_j','max_terminal_energy_error_j'),
        ('recovery_discrepancy_j','max_recovery_error_j')]
    result['passed']=bool(fine['feasible'] and refined['feasible'] and all(result[k]<=limits[l] for k,l in checks))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    count=0;cases=[];refinement_cases=[]
    def hashes(mapping):
        nonlocal count
        for name,digest in mapping.items():
            if sha(name)!=digest:raise ValueError('hash mismatch: '+name)
            count+=1
    def manifest(folder,groups=('inputs','sources','outputs')):
        data=read(folder/'manifest.json')
        for group in groups:hashes(data[group])
        return data
    parent_manifest=manifest(args.input)
    summary=read(args.input/'metrics.json');contract=read(args.input/'contract.json');protocol=contract['protocol']
    baseline=Path(protocol['baselines']);manifest(baseline,('inputs','outputs'))
    gate=read(baseline/'metrics.json');base_config=read(baseline/'contract.json')['config']
    if base_config.get('regeneration'):
        from f1energy.circuit_training_gate import validate_control_gate
        validate_control_gate(baseline,Path(__file__).resolve().parents[1])
    limits=protocol.get('refinement');root_replays={}
    if limits:
        hashes(contract['refinement_inputs'])
        for label in ['zero','comparator']:
            path=args.input/f'refined_{label}.json.gz'
            for mapping in [contract['refinement_inputs'],parent_manifest['outputs']]:
                if mapping.get(str(path))!=sha(path):raise ValueError('unbound refined baseline: '+str(path))
            root_replays[label]=replay(path)
    def audit(path,result,config,reference):
        trace=result['trace'];end=trace[-1]['state'];v=reference['vehicle'];initial=config['initial_speed_mps']
        if not finite(result):raise ValueError('non-finite replay: '+str(path))
        independent=audit_replay(result,config,reference,SimpleNamespace(**v))
        residual=.5*v['mass_kg']*(end['speed_m_per_s']**2-initial**2)-sum(
            t['base_work_j']+t['electrical_work_j']-t['drag_work_j']-t['friction_braking_work_j']-
            t.get('regenerative_braking_work_j',0.) for t in trace)
        if abs(residual)>1:raise ValueError('global energy failed: '+str(path))
        close(sum(t['duration_s'] for t in trace),result['duration_s'],'duration mismatch')
        close(end['energy_j'],result['final_energy_j'],'final energy mismatch')
        if abs(end['speed_m_per_s']-initial)>1e-5 or end['energy_j']<reference['reserve_j']-1e-5:raise ValueError('terminal constraint failed')
        if len(trace)!=config['action_blocks']:raise ValueError('decision-count mismatch')
        if any(t['max_node_cap_excess_mps']>1e-5 for t in trace):raise ValueError('speed constraint failed')
        if config.get('regeneration'):
            for t in trace:
                draw=t['electrical_work_j']/v['discharge_efficiency']
                close(t['battery_discharged_j'],draw,'block discharge identity')
                close(t['charging_loss_j'],t['regenerative_braking_work_j']-t['battery_recovered_j'],'block charging loss identity')
                if draw>config['regeneration']['max_power_w']*t['duration_s']/v['discharge_efficiency']+1e-5:raise ValueError('deployment power bound')
        cases.append(dict(file=str(path),global_energy_residual_j=residual,duration_s=result['duration_s'],**independent))
    root_checked=False;seed_summaries=[]
    for seed in protocol['training_seeds']:
        folder=args.input/f'seed-{seed}'
        if not (folder/'metrics.json').exists():continue
        manifest(folder);sc=read(folder/'contract.json');config=sc['config'];reference=read(config['reference_config'])
        if config!=base_config or sc['protocol']!=protocol or sc['seed']!=seed:raise ValueError('worker contract mismatch')
        def baseline_row(policy,cells):
            return next(r for r in gate['results'] if r['policy']==policy and r['blocks']==config['action_blocks'] and r['cells']==cells)
        zero={}
        for name,cells in [('training',sc['selected_cells']),('fine',config['fine_cells_per_block'])]:
            row=baseline_row('zero',cells);data=replay(baseline/row['file'])
            close(data['duration_s'],row['duration_s'],'baseline duration mismatch');zero[name]=data['duration_s']
        if limits:
            zero['refined']=root_replays['zero']['duration_s']
            if not root_checked:
                for label,data in root_replays.items():audit(args.input/f'refined_{label}.json.gz',data,config,reference)
                root_checked=True
        saved={}
        for p in sorted(folder.glob('*.json.gz')):
            r=replay(p);audit(p,r,config,reference);saved[p.name]=r
            grid=p.name.removesuffix('.json.gz').rsplit('_',1)[1]
            close(r['reward_sum'],zero[grid]-r['duration_s'],'reward identity mismatch')
        metrics=read(folder/'metrics.json');seed_summaries.append(metrics)
        if metrics['actual_steps']!=protocol['steps_per_seed']:raise ValueError('incomplete training budget')
        if [c['step'] for c in metrics['checkpoints']]!=protocol['checkpoint_steps']:raise ValueError('missing checkpoint')
        if not all(c['gpu_training']['passed'] and c['gpu_training']['policy_device']=='cuda:0' for c in metrics['checkpoints'] if c['step']):raise ValueError('CUDA proof missing')
        if not metrics['checkpoint_reload_exact']:raise ValueError('reload check failed')
        final_label=f'checkpoint_{protocol["steps_per_seed"]}_deterministic'
        if metrics['final_deterministic']!=metrics['checkpoints'][-1]:raise ValueError('final checkpoint selection mismatch')
        if [r['noise_seed'] for r in metrics['final_stochastic']]!=protocol['stochastic_evaluation_seeds']:raise ValueError('stochastic seed mismatch')
        evaluations=[(f'checkpoint_{r["step"]}_deterministic',r) for r in metrics['checkpoints']]
        evaluations += [(f'final_stochastic_{r["noise_seed"]}',r) for r in metrics['final_stochastic']]
        passes=[]
        for label,r in evaluations:
            coarse=saved[label+'_training.json.gz'];fine=saved[label+'_fine.json.gz']
            expected=dict(training_time_s=coarse['duration_s'],fine_time_s=fine['duration_s'],fine_gain_s=zero['fine']-fine['duration_s'],
                fine_final_energy_j=fine['final_energy_j'],gain_discrepancy_s=abs((zero['training']-coarse['duration_s'])-(zero['fine']-fine['duration_s'])))
            for key,value in expected.items():close(r[key],value,key+' arithmetic')
            feasible=bool(coarse['feasible'] and fine['feasible'])
            if r['feasible']!=feasible:raise ValueError('feasibility summary mismatch')
            passed=feasible and expected['gain_discrepancy_s']<=config['gates']['gain_error_s']
            final=label==final_label or label.startswith('final_stochastic_')
            if limits and final:
                refined=saved[label+'_refined.json.gz'];fine_base=baseline_row(limits['baseline_policy'],config['fine_cells_per_block'])['duration_s']
                check=refinement_check(fine,refined,fine_base,root_replays['comparator']['duration_s'],limits)
                for key,value in check.items():
                    if key=='passed':
                        if r['refinement'][key]!=value:raise ValueError('refinement acceptance mismatch')
                    else:close(r['refinement'][key],value,'refinement arithmetic: '+key)
                refinement_cases.append(dict(seed=seed,label=label,**check));passed=passed and check['passed']
            if final:passes.append(passed)
        for grid in ['training','fine']+(['refined'] if limits else []):
            if saved[final_label+'_'+grid+'.json.gz']!=saved['reloaded_final_deterministic_'+grid+'.json.gz']:raise ValueError('reload replay mismatch')
        if metrics['final_replay_gate_passed']!=all(passes):raise ValueError('seed acceptance mismatch')
    if summary['seeds']!=seed_summaries:raise ValueError('aggregate seed records mismatch')
    completed=len(seed_summaries)==len(protocol['training_seeds'])
    accepted=completed and all(summary['worker_exit_codes'].get(str(s))==0 for s in protocol['training_seeds']) and all(s['final_replay_gate_passed'] for s in seed_summaries)
    if summary['all_seeds_completed_and_passed']!=accepted:raise ValueError('study acceptance mismatch')
    def stats(values,reported):
        expected=dict(n=len(values),mean=statistics.mean(values),sample_sd=statistics.stdev(values),minimum=min(values),maximum=max(values))
        for key,value in expected.items():close(reported[key],value,'summary '+key+' arithmetic')
    for s in seed_summaries:stats([r['fine_time_s'] for r in s['final_stochastic']],s['stochastic_within_seed'])
    if completed and (limits or accepted):
        stats([s['final_deterministic']['fine_time_s'] for s in seed_summaries],summary['deterministic_lap_time_s'])
        stats([s['final_deterministic']['fine_gain_s'] for s in seed_summaries],summary['deterministic_gain_s'])
        stats([statistics.mean(r['fine_time_s'] for r in s['final_stochastic']) for s in seed_summaries],summary['stochastic_seed_mean_lap_time_s'])
    record=dict(hash_checks=count,replays_checked=len(cases),max_absolute_energy_residual_j=max((abs(c['global_energy_residual_j']) for c in cases),default=0.),
        all_seeds_completed=completed,all_seeds_passed=accepted,refinement_cases=refinement_cases,cases=cases,script_sha256=sha(__file__),
        dependency_hashes={'scripts/validate_regeneration.py':sha(Path(__file__).with_name('validate_regeneration.py'))})
    args.output.write_bytes((json.dumps(record,indent=2,allow_nan=False)+'\n').encode())
    print(json.dumps({k:v for k,v in record.items() if k not in ['cases','refinement_cases']}))


if __name__=='__main__':main()
