"""Bounded synthetic CPU PPO pilot with frozen held-out evaluation."""
import argparse, dataclasses, hashlib, json, platform, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import torch
import gymnasium
import stable_baselines3
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from f1energy.rl import LapEnv
from f1energy.lap import default_scenario

def rollout(scenario, policy):
    env=LapEnv(scenario); obs,_=env.reset(seed=0); actions=[]; done=False
    while not done:
        action=np.asarray(policy(obs),dtype=np.float32).reshape(1)
        obs,reward,done,truncated,info=env.step(action); actions.append(float(action[0]))
    s=env.state
    return dict(elapsed_s=s.elapsed_s,terminal_energy_j=s.energy_j,terminal_speed_m_per_s=s.speed_m_per_s,
                feasible=s.energy_j>=scenario.reserve_j-1e-6 and s.speed_m_per_s<=scenario.segments[-1].exit_speed_cap_m_per_s+1e-6,
                actions=actions)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--steps',type=int,default=16384);p.add_argument('--seed',type=int,default=0);a=p.parse_args()
    if not 1024<=a.steps<=30000: p.error('pilot steps must be 1024..30000')
    a.output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    nominal=default_scenario()
    heldout=dataclasses.replace(nominal,initial_energy_j=350000.,mass_kg=880.)
    cases={'training_nominal':nominal,'heldout_mass_energy':heldout}
    config=dict(seed=a.seed,requested_steps=a.steps,device='cpu',torch_threads=1,n_steps=256,batch_size=64,n_epochs=10,
                learning_rate=0.0003,gamma=1.0,net_arch=[32,32],scenarios={k:dataclasses.asdict(v) for k,v in cases.items()},
                interpretation='Fixed synthetic track; held-out perturbation predeclared; single seed pilot, not F1 evidence.')
    (a.output/'config.json').write_text(json.dumps(config,indent=2))
    env=LapEnv(nominal);check_env(env,warn=True)
    model=PPO('MlpPolicy',env,seed=a.seed,device='cpu',n_steps=256,batch_size=64,n_epochs=10,gamma=1.,policy_kwargs={'net_arch':[32,32]},verbose=0)
    initial_weights={k:v.detach().clone() for k,v in model.policy.state_dict().items()}
    t=time.perf_counter();model.learn(total_timesteps=a.steps);runtime=time.perf_counter()-t
    delta={k:float((v-model.policy.state_dict()[k]).abs().max()) for k,v in initial_weights.items()}
    (a.output/'weight_update_check.json').write_text(json.dumps(dict(changed_tensors=sum(v>0 for v in delta.values()),max_absolute_weight_change=max(delta.values())),indent=2))
    model.save(a.output/'ppo')
    loaded=PPO.load(a.output/'ppo.zip',device='cpu')
    results={}
    for name,scenario in cases.items():
        results[name]={}
        policies={'zero':lambda obs:[0.], 'uniform_half':lambda obs:[.5], 'uniform_full':lambda obs:[1.],
                  'ppo':lambda obs:loaded.predict(obs,deterministic=True)[0]}
        for label,policy in policies.items():
            start=time.perf_counter();row=rollout(scenario,policy);row['evaluation_s']=time.perf_counter()-start;results[name][label]=row
        original=rollout(scenario,lambda obs:model.predict(obs,deterministic=True)[0])
        assert original['actions']==results[name]['ppo']['actions'], 'checkpoint reload changed deterministic actions'
    metrics=dict(actual_timesteps=model.num_timesteps,training_s=runtime,results=results)
    (a.output/'metrics.json').write_text(json.dumps(metrics,indent=2))
    (a.output/'environment-lock.txt').write_text(subprocess.check_output([__import__('sys').executable,'-m','pip','freeze'],text=True))
    source=Path(__file__).resolve().parents[1]
    files=list(a.output.glob('*'))
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),torch=torch.__version__,gymnasium=gymnasium.__version__,sb3=stable_baselines3.__version__,
                  outputs={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files if f.is_file()},
                  source_sha256={str(f.relative_to(source)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(__file__),source/'src/f1energy/rl.py',source/'src/f1energy/lap.py']})
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(metrics,indent=2))
if __name__=='__main__': main()
