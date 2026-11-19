"""Bounded, hash-gated full-circuit PPO pilot and fine-grid policy replay."""
import argparse,json,time,platform
from pathlib import Path
import numpy as np
import torch
import stable_baselines3
from stable_baselines3 import PPO
from f1energy.training_device import require_cuda,verify_cuda_training
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.logger import configure
from f1energy.circuit_control import rollout,baseline_policy
from f1energy.circuit_training_gate import validate_control_gate
from benchmark_circuit_control import load_setup,make_env,sha,save,gzsave,sources


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baselines',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();gpu=require_cuda();device=gpu['device'];root=Path(__file__).resolve().parents[1]
    config,gate=validate_control_gate(args.baselines,root)
    settings=config['pilot'];cells=gate['selected_cells_per_block']
    if not 256<=settings['steps']<=4096:raise ValueError('initial pilot budget must be256..4096')
    args.output.mkdir(parents=True,exist_ok=False)
    before=sources()
    for p in [Path(__file__),Path('src/f1energy/circuit_training_gate.py'),Path('src/f1energy/training_device.py'),Path('scripts/benchmark_circuit_control.py')]:before[str(p)]=sha(p)
    save(args.output/'contract.json',dict(config=config,baseline_manifest_sha256=sha(args.baselines/'manifest.json'),
        sources=before,selected_cells=cells,device=device,gpu=gpu,threads=1,
        versions=dict(python=platform.python_version(),torch=torch.__version__,sb3=stable_baselines3.__version__,numpy=np.__version__)))
    torch.set_num_threads(1)
    reference,curve,vehicle=load_setup(config)
    raw=make_env(config,reference,curve,vehicle,cells)
    zero=rollout(raw,baseline_policy('zero',raw));raw.reference_times=np.array([r['duration_s'] for r in zero['trace']])
    env=Monitor(raw,str(args.output/'episodes'))
    model=PPO('MlpPolicy',env,seed=settings['seed'],device=device,n_steps=settings['n_steps'],batch_size=settings['batch_size'],
              n_epochs=settings['n_epochs'],gamma=settings['gamma'],policy_kwargs=dict(net_arch=settings['net_arch']),verbose=0)
    model.set_logger(configure(str(args.output/'logs'),['csv']))
    untrained=rollout(raw,lambda obs:model.predict(obs,deterministic=True)[0]);gzsave(args.output/'untrained.json.gz',untrained)
    model.save(args.output/'initial_policy')
    start=time.perf_counter()
    model.learn(total_timesteps=settings['steps'],callback=CheckpointCallback(save_freq=1024,save_path=str(args.output/'checkpoints'),name_prefix='ppo'))
    torch.cuda.synchronize();elapsed=time.perf_counter()-start
    gpu_training=verify_cuda_training(model)
    model.save(args.output/'ppo')
    loaded=PPO.load(args.output/'ppo.zip',device=device)
    trained=rollout(raw,lambda obs:model.predict(obs,deterministic=True)[0])
    reloaded=rollout(raw,lambda obs:loaded.predict(obs,deterministic=True)[0])
    if trained!=reloaded:raise RuntimeError('checkpoint reload differs')
    gzsave(args.output/'trained_training_grid.json.gz',trained)
    fine=make_env(config,reference,curve,vehicle,config['fine_cells_per_block'])
    fine_zero=rollout(fine,baseline_policy('zero',fine));fine.reference_times=np.array([r['duration_s'] for r in fine_zero['trace']])
    evaluated=rollout(fine,lambda obs:loaded.predict(obs,deterministic=True)[0]);gzsave(args.output/'trained_fine_grid.json.gz',evaluated)
    rows={r['policy']:r for r in gate['results'] if r['blocks']==config['action_blocks'] and r['cells']==config['fine_cells_per_block']}
    fine_gain=rows['zero']['duration_s']-evaluated['duration_s'];train_gain=zero['duration_s']-trained['duration_s']
    summary=dict(gpu_training=gpu_training,actual_steps=model.num_timesteps,seed=settings['seed'],training_seconds=elapsed,checkpoint_reload_exact=True,
        untrained_training_grid_s=untrained['duration_s'],trained_training_grid_s=trained['duration_s'],trained_fine_grid_s=evaluated['duration_s'],
        fine_baselines_s={n:r['duration_s'] for n,r in rows.items()},fine_gain_over_zero_s=fine_gain,
        learned_gain_over_untrained_training_grid_s=untrained['duration_s']-trained['duration_s'],
        time_gain_grid_discrepancy_s=abs(fine_gain-train_gain),
        fine_policy_feasible=evaluated['feasible'],terminal_speed_error_mps=evaluated['terminal_speed_error_mps'],
        energy_residual_j=evaluated['energy_residual_j'],final_energy_j=evaluated['final_energy_j'],
        interpretation='One seed,4096-step model-based pilot; not convergence, optimality, or final held-out performance')
    summary['pilot_replay_gate_passed']=bool(trained['feasible'] and evaluated['feasible'] and abs(fine_gain-train_gain)<=config['gates']['gain_error_s'])
    save(args.output/'metrics.json',summary)
    if any(sha(p)!=h for p,h in before.items()):raise RuntimeError('source changed during training')
    save(args.output/'manifest.json',dict(inputs={str(args.baselines/'manifest.json'):sha(args.baselines/'manifest.json')},sources=before,
        outputs={str(p):sha(p) for p in args.output.rglob('*') if p.is_file()}))
    print(json.dumps(summary,indent=2),flush=True)
    if not summary['pilot_replay_gate_passed']:raise SystemExit(2)


if __name__=='__main__':main()
