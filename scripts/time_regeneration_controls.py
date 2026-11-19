"""Time deterministic action selection on the saved PPO lap observations."""
import gzip
import json
import statistics
import time
from pathlib import Path

import torch
from stable_baselines3 import PPO
from benchmark_circuit_control import load_setup, make_env, save, sha
from f1energy.power_lap import PowerState


def measure(call, cuda=True):
    for _ in range(3):
        call()
    if cuda: torch.cuda.synchronize()
    times=[]
    for _ in range(21):
        start=time.perf_counter_ns()
        call()
        if cuda: torch.cuda.synchronize()
        times.append((time.perf_counter_ns()-start)/1e6)
    return statistics.median(times)


def main():
    run=Path('results/regeneration-dp-001')
    output=Path('logs/agent_tools/2026-11-18/regeneration_dp_cost.json')
    if output.exists(): raise FileExistsError(output)
    contract=json.loads((run/'contract.json').read_text()); config=contract['config']
    parent=Path(contract['protocol']['ppo'])
    metrics=json.loads((run/'metrics.json').read_text())
    schedule=next(r['actions'] for r in metrics['cases'] if r['name']=='refined')
    ref,curve,vehicle=load_setup(config)
    env=make_env(config,ref,curve,vehicle,160)
    rows=[]
    torch.set_num_threads(1)
    for seed in (0,1,2):
        folder=parent/f'seed-{seed}'
        checkpoint=folder/'checkpoint_16384.zip'
        model=PPO.load(checkpoint,device='cuda:0')
        with gzip.open(folder/'checkpoint_16384_deterministic_fine.json.gz','rt') as stream:
            trace=json.load(stream)['trace']
        env.reset()
        observations=[]
        for index,b in enumerate(trace):
            env.index=index
            observations.append(env._obs())
            env.state=PowerState(**b['state'])
            env.recovered_j+=b['battery_recovered_j']
            env.discharged_j+=b['battery_discharged_j']
        def predict():
            return [float(model.predict(obs,deterministic=True)[0][0]) for obs in observations]
        assert predict()==[b['action'] for b in trace]
        rows.append(dict(seed=seed,checkpoint_sha256=sha(checkpoint),ppo_ms_per_55_actions=measure(predict),
                         training_seconds=json.loads((folder/'metrics.json').read_text())['training_seconds']))
    save(output,dict(rows=rows,schedule_ms_per_55_lookups=measure(lambda:[schedule[i] for i in range(len(schedule))], cuda=False),
                     source_sha256=sha(__file__),scope='Median of 21 warm repetitions at batch size one; synchronized CUDA. Excludes simulator, loading and offline planning. Schedule lookup depends only on block index.'))
    print(output)


if __name__=='__main__':main()
