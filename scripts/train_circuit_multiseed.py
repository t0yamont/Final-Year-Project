"""Fixed-budget GPU multi-seed study with isolated, paired policy evaluation."""
import argparse,gzip,json,os,platform,subprocess,sys,time,traceback
from pathlib import Path
import numpy as np
import torch
import stable_baselines3
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.logger import configure
from f1energy.experiment import isolated_rng,describe,gain_discrepancy
from f1energy.training_device import require_cuda,verify_cuda_training
from f1energy.circuit_training_gate import validate_control_gate
from f1energy.circuit_control import rollout,baseline_policy
from benchmark_circuit_control import load_setup,make_env,sha,save,gzsave,sources


def study_sources():
    result=sources()
    for name in [__file__,'scripts/benchmark_circuit_control.py','src/f1energy/experiment.py',
                 'src/f1energy/training_device.py','src/f1energy/circuit_training_gate.py']:
        result[str(Path(name))]=sha(name)
    return result


def refinement_assessment(fine,refined,fine_baseline,refined_baseline,limits):
    fine_gain=fine_baseline-fine['duration_s'];refined_gain=refined_baseline-refined['duration_s']
    recovery=lambda r:sum(b.get('battery_recovered_j',0.) for b in r['trace'])
    result=dict(refined_time_s=refined['duration_s'],refined_final_energy_j=refined['final_energy_j'],
        fine_advantage_s=fine_gain,refined_advantage_s=refined_gain,
        paired_advantage_discrepancy_s=abs(fine_gain-refined_gain),
        relative_lap_time_error=abs(fine['duration_s']-refined['duration_s'])/refined['duration_s'],
        terminal_energy_discrepancy_j=abs(fine['final_energy_j']-refined['final_energy_j']),
        recovery_discrepancy_j=abs(recovery(fine)-recovery(refined)))
    result['passed']=bool(all(np.isfinite(x) for x in result.values()) and fine['feasible'] and refined['feasible'] and
        result['paired_advantage_discrepancy_s']<=limits['max_paired_advantage_error_s'] and
        result['relative_lap_time_error']<=limits['max_relative_lap_time_error'] and
        result['terminal_energy_discrepancy_j']<=limits['max_terminal_energy_error_j'] and
        result['recovery_discrepancy_j']<=limits['max_recovery_error_j'])
    return result


def worker(args,protocol):
    if args.seed not in protocol['training_seeds']:raise ValueError('seed not predeclared')
    root=Path(__file__).resolve().parents[1];gpu=require_cuda();torch.set_num_threads(1)
    config,gate=validate_control_gate(protocol['baselines'],root)
    args.output.mkdir(parents=True,exist_ok=False)
    before=study_sources();inputs={str(args.protocol):sha(args.protocol),str(Path(protocol['baselines'])/'manifest.json'):sha(Path(protocol['baselines'])/'manifest.json')}
    refinement=protocol.get('refinement')
    if refinement:
        parent=json.loads((args.output.parent/'contract.json').read_text())
        for name,digest in parent['refinement_inputs'].items():
            if sha(name)!=digest:raise ValueError('refinement baseline changed')
            inputs[name]=digest
    save(args.output/'contract.json',dict(protocol=protocol,config=config,seed=args.seed,gpu=gpu,sources=before,inputs=inputs,
        selected_cells=gate['selected_cells_per_block'],versions=dict(python=platform.python_version(),torch=torch.__version__,sb3=stable_baselines3.__version__,numpy=np.__version__)))
    ref,curve,vehicle=load_setup(config);cells=gate['selected_cells_per_block'];fine_cells=config['fine_cells_per_block']
    def environment(count):
        env=make_env(config,ref,curve,vehicle,count)
        if refinement and count==refinement['cells_per_block']:
            path=args.output.parent/'refined_zero.json.gz'
        else:
            row=next(r for r in gate['results'] if r['policy']=='zero' and r['blocks']==config['action_blocks'] and r['cells']==count)
            path=Path(protocol['baselines'])/row['file']
        with gzip.open(path,'rt') as f:zero=json.load(f)
        env.reference_times=np.array([r['duration_s'] for r in zero['trace']]);return env,zero['duration_s']
    training,_=environment(cells);coarse,coarse_zero=environment(cells);fine,fine_zero=environment(fine_cells)
    if refinement:
        refined,_=environment(refinement['cells_per_block'])
        with gzip.open(args.output.parent/'refined_comparator.json.gz','rt') as f:refined_baseline=json.load(f)['duration_s']
        fine_baseline=next(r['duration_s'] for r in gate['results'] if r['policy']==refinement['baseline_policy'] and r['cells']==fine_cells and r['blocks']==config['action_blocks'])
    hp=protocol['hyperparameters'];kwargs={k:v for k,v in hp.items() if k!='net_arch'}
    model=PPO('MlpPolicy',Monitor(training,str(args.output/'episodes')),seed=args.seed,device=gpu['device'],
              policy_kwargs=dict(net_arch=hp['net_arch']),verbose=0,**kwargs)
    model.set_logger(configure(str(args.output/'logs'),['csv']))
    checkpoints=[];training_seconds=0.;start=time.perf_counter()
    def pair(policy,deterministic,noise_seed,label,check_refinement=False):
        records=[]
        grids=[('training',coarse),('fine',fine)]+([('refined',refined)] if check_refinement and refinement else [])
        for grid,env in grids:
            with isolated_rng(noise_seed):
                record=rollout(env,lambda obs:policy.predict(obs,deterministic=deterministic)[0])
            gzsave(args.output/f'{label}_{grid}.json.gz',record);records.append(record)
        c,f=records[:2]
        result=dict(training_time_s=c['duration_s'],fine_time_s=f['duration_s'],
            fine_gain_s=fine_zero-f['duration_s'],fine_final_energy_j=f['final_energy_j'],
            gain_discrepancy_s=gain_discrepancy(c['duration_s'],f['duration_s'],coarse_zero,fine_zero),
            feasible=bool(c['feasible'] and f['feasible']),noise_seed=noise_seed,
            fine_energy_residual_j=f['energy_residual_j'],fine_terminal_speed_error_mps=f['terminal_speed_error_mps'])
        if check_refinement and refinement:
            result['refinement']=refinement_assessment(f,records[2],fine_baseline,refined_baseline,refinement)
        return result
    for target in protocol['checkpoint_steps']:
        if target:
            before_train=time.perf_counter()
            model.learn(total_timesteps=target-model.num_timesteps,reset_num_timesteps=False)
            torch.cuda.synchronize();training_seconds+=time.perf_counter()-before_train
            device_check=verify_cuda_training(model)
        else:device_check=None
        if model.num_timesteps!=target:raise RuntimeError('unexpected training budget')
        model.save(args.output/f'checkpoint_{target}')
        record=pair(model,True,9001,f'checkpoint_{target}_deterministic',target==protocol['steps_per_seed'])
        row=dict(step=target,gpu_training=device_check,**record);checkpoints.append(row)
        save(args.output/'progress.json',dict(seed=args.seed,completed_steps=target,checkpoints=checkpoints,training_seconds=training_seconds))
        print(json.dumps(dict(seed=args.seed,step=target,fine_time_s=record['fine_time_s'],feasible=record['feasible'])),flush=True)
    # Model construction/loading must not alter RNG state used by later checks.
    with isolated_rng(9001):loaded=PPO.load(args.output/f'checkpoint_{protocol["steps_per_seed"]}.zip',device=gpu['device'])
    reloaded=pair(loaded,True,9001,'reloaded_final_deterministic',True)
    if reloaded!={k:v for k,v in checkpoints[-1].items() if k not in ['step','gpu_training']}:
        raise RuntimeError('checkpoint reload changed replay')
    stochastic=[pair(loaded,False,s,f'final_stochastic_{s}',True) for s in protocol['stochastic_evaluation_seeds']]
    evaluated=[checkpoints[-1],*stochastic]
    passed=all(r['feasible'] and r['gain_discrepancy_s']<=config['gates']['gain_error_s'] and r.get('refinement',{}).get('passed',True) for r in evaluated)
    summary=dict(seed=args.seed,actual_steps=model.num_timesteps,training_seconds=training_seconds,elapsed_seconds=time.perf_counter()-start,
        checkpoints=checkpoints,final_deterministic=checkpoints[-1],final_stochastic=stochastic,
        stochastic_within_seed=describe([r['fine_time_s'] for r in stochastic]),
        final_replay_gate_passed=bool(passed),checkpoint_reload_exact=True,
        limitation='Nominal assumed-model learning study; five stochastic rollouts are nested within one training seed')
    save(args.output/'metrics.json',summary)
    if any(sha(name)!=digest for name,digest in before.items()):raise RuntimeError('source changed during training')
    save(args.output/'manifest.json',dict(inputs=inputs,sources=before,outputs={str(p):sha(p) for p in args.output.rglob('*') if p.is_file()}))
    if not passed:raise SystemExit(2)


def coordinator(args,protocol):
    config,gate=validate_control_gate(protocol['baselines'],Path(__file__).resolve().parents[1]);gpu=require_cuda()
    args.output.mkdir(parents=True,exist_ok=False)
    before=study_sources();inputs={str(args.protocol):sha(args.protocol),str(Path(protocol['baselines'])/'manifest.json'):sha(Path(protocol['baselines'])/'manifest.json')}
    refinement_inputs={};refinement_baseline_check=None
    if protocol.get('refinement'):
        ref,curve,vehicle=load_setup(config);limits=protocol['refinement']
        for label,name in [('zero','zero'),('comparator',limits['baseline_policy'])]:
            env=make_env(config,ref,curve,vehicle,limits['cells_per_block'])
            replay=rollout(env,baseline_policy(name,env))
            if not replay['feasible']:raise ValueError('refined baseline infeasible')
            path=args.output/f'refined_{label}.json.gz';gzsave(path,replay);refinement_inputs[str(path)]=sha(path)
            if label=='comparator':
                row=next(r for r in gate['results'] if r['policy']==name and r['cells']==config['fine_cells_per_block'] and r['blocks']==config['action_blocks'])
                with gzip.open(Path(protocol['baselines'])/row['file'],'rt') as f:fine_baseline=json.load(f)
                refinement_baseline_check=refinement_assessment(fine_baseline,replay,fine_baseline['duration_s'],replay['duration_s'],limits)
                if not refinement_baseline_check['passed']:raise ValueError('refined comparator grid gate failed')
    save(args.output/'contract.json',dict(protocol=protocol,gpu=gpu,inputs=inputs,sources=before,
        refinement_inputs=refinement_inputs,refinement_baseline_check=refinement_baseline_check,logical_cpu_count=os.cpu_count()))
    pending=list(protocol['training_seeds']);running={};finished={};handles=[]
    workers=min(protocol['parallel_workers'],max(1,(os.cpu_count() or 2)-1))
    try:
        while pending or running:
            while pending and len(running)<workers:
                seed=pending.pop(0);log=(args.output/f'seed-{seed}.log').open('w',encoding='utf-8');handles.append(log)
                cmd=[sys.executable,str(Path(__file__).resolve()),'--protocol',str(args.protocol),'--output',str(args.output/f'seed-{seed}'),'--seed',str(seed)]
                running[seed]=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            for seed,process in list(running.items()):
                if process.poll() is not None:finished[str(seed)]=process.returncode;del running[seed]
            save(args.output/'workers.json',dict(running={str(s):p.pid for s,p in running.items()},finished=finished,pending=pending))
            if running:time.sleep(2)
    finally:
        for p in running.values():
            if p.poll() is None:p.terminate();p.wait()
        for log in handles:log.close()
    summaries=[]
    for seed in protocol['training_seeds']:
        p=args.output/f'seed-{seed}'/'metrics.json'
        if p.exists():summaries.append(json.loads(p.read_text()))
    accepted=len(summaries)==len(protocol['training_seeds']) and all(code==0 for code in finished.values()) and all(s['final_replay_gate_passed'] for s in summaries)
    result=dict(all_seeds_completed=len(summaries)==len(protocol['training_seeds']),all_seeds_completed_and_passed=bool(accepted),worker_exit_codes=finished,seeds=summaries,
                scope=protocol['study'],primary_endpoint=protocol['primary_endpoint'],parallel_workers_used=workers)
    if len(summaries)==len(protocol['training_seeds']):
        result['deterministic_lap_time_s']=describe([s['final_deterministic']['fine_time_s'] for s in summaries])
        result['deterministic_gain_s']=describe([s['final_deterministic']['fine_gain_s'] for s in summaries])
        result['stochastic_seed_mean_lap_time_s']=describe([s['stochastic_within_seed']['mean'] for s in summaries])
        if protocol.get('refinement'):
            result['refined_deterministic_lap_time_s']=describe([s['final_deterministic']['refinement']['refined_time_s'] for s in summaries])
    fine_rows=[r for r in gate['results'] if r['blocks']==config['action_blocks'] and r['cells']==config['fine_cells_per_block']]
    result['fine_baselines_s']={r['policy']:r['duration_s'] for r in fine_rows}
    save(args.output/'metrics.json',result)
    if any(sha(p)!=h for p,h in before.items()):raise RuntimeError('source changed during study')
    save(args.output/'manifest.json',dict(inputs=inputs,sources=before,outputs={str(p):sha(p) for p in args.output.rglob('*') if p.is_file()}))
    print(json.dumps({k:v for k,v in result.items() if k!='seeds'},indent=2),flush=True)
    if not accepted:raise SystemExit(2)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--protocol',type=Path,default=Path('configs/circuit_multiseed_protocol.json'));parser.add_argument('--seed',type=int)
    args=parser.parse_args();protocol=json.loads(args.protocol.read_text())
    steps=protocol['steps_per_seed'];points=protocol['checkpoint_steps']
    if steps!=16384 or points!=[0,4096,8192,12288,16384] or len(set(protocol['training_seeds']))!=3:raise ValueError('bounded study requires three unique seeds and fixed16384-step schedule')
    try:
        if args.seed is None:coordinator(args,protocol)
        else:worker(args,protocol)
    except Exception:
        if args.output.exists():save(args.output/'failure.json',dict(error=traceback.format_exc()))
        raise


if __name__=='__main__':main()
