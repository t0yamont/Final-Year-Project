"""Validation-gated synthetic event-model PPO pilot; fixed scenarios, no tuning."""
import argparse,dataclasses,json,hashlib,time,subprocess,sys
from pathlib import Path
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.logger import configure
from f1energy.event_rl import EventLapEnv,EventScenario,validate_training_gate

def rollout(scenario,policy):
 env=EventLapEnv(scenario);obs,_=env.reset(seed=0);done=False;trace=[]
 while not done:
  action=np.asarray(policy(obs),dtype=np.float32).reshape(1);obs,_,done,_,info=env.step(action)
  trace.append(dict(action=float(action[0]),speed_m_per_s=env.state.speed_m_per_s,energy_j=env.state.energy_j,duration_s=info['duration_s'],energy_residual_j=info['energy_residual_j']))
 return dict(elapsed_s=env.state.elapsed_s,terminal_energy_j=env.state.energy_j,terminal_speed_m_per_s=env.state.speed_m_per_s,
             feasible=env.state.energy_j>=scenario.reserve_j-1e-5 and abs(env.state.speed_m_per_s-scenario.exit_caps_m_per_s[-1])<1e-5,trace=trace)

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--validation-report',type=Path,required=True);p.add_argument('--seed',type=int,default=0);p.add_argument('--steps',type=int,default=16384);a=p.parse_args()
 validate_training_gate(a.validation_report,Path(__file__).resolve().parents[1])
 if not 256<=a.steps<=32768:p.error('bounded pilot steps256..32768')
 a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
 nominal=EventScenario();evaluation=dataclasses.replace(nominal,lengths_m=(360.,440.),exit_caps_m_per_s=(28.,20.),initial_energy_j=400000.,vehicle=dataclasses.replace(nominal.vehicle,mass_kg=840.))
 cases={'nominal_development':nominal,'new_predeclared_evaluation':evaluation}
 config=dict(seed=a.seed,steps=a.steps,device='cpu',threads=1,scenarios={k:dataclasses.asdict(v) for k,v in cases.items()},hyperparameters=dict(n_steps=256,batch_size=64,n_epochs=10,gamma=1.,net_arch=[32,32]),validation_sha256=hashlib.sha256(a.validation_report.read_bytes()).hexdigest())
 (a.output/'config.json').write_text(json.dumps(config,indent=2));(a.output/'validation-evidence.json').write_bytes(a.validation_report.read_bytes());(a.output/'validation-manifest.json').write_bytes((a.validation_report.parent/'manifest.json').read_bytes())
 root=Path(__file__).resolve().parents[1]
 source_paths=[Path(__file__),root/'src/f1energy/event_rl.py',root/'src/f1energy/event_power_lap.py',root/'src/f1energy/power_lap.py']
 before_hashes={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in source_paths}
 (a.output/'source-before-training.json').write_text(json.dumps(before_hashes,indent=2))
 env=EventLapEnv(nominal);check_env(env,warn=True)
 model=PPO('MlpPolicy',env,seed=a.seed,device='cpu',n_steps=256,batch_size=64,n_epochs=10,gamma=1.,policy_kwargs={'net_arch':[32,32]},verbose=0);model.set_logger(configure(str(a.output/'logs'),['csv']))
 initial={k:v.detach().clone() for k,v in model.policy.state_dict().items()}
 t=time.perf_counter();model.learn(total_timesteps=a.steps);runtime=time.perf_counter()-t;model.save(a.output/'ppo');loaded=PPO.load(a.output/'ppo.zip',device='cpu')
 changes={k:float((v-model.policy.state_dict()[k]).abs().max()) for k,v in initial.items()}
 results={}
 for name,scenario in cases.items():
  results[name]={label:rollout(scenario,policy) for label,policy in {'zero':lambda o:[0.],'half':lambda o:[.5],'full':lambda o:[1.],'ppo':lambda o:loaded.predict(o,deterministic=True)[0]}.items()}
  assert rollout(scenario,lambda o:model.predict(o,deterministic=True)[0])==results[name]['ppo']
 from itertools import product
 reference=[]
 for sequence in product([0.,.5,1.],repeat=2):
  row=rollout(nominal,lambda obs,sequence=sequence:[sequence[min(1,int(round(float(obs[0])*2)))]]);row['sequence']=sequence;reference.append(row)
 discrete=min(reference,key=lambda r:r['elapsed_s'])
 metrics=dict(nominal_discrete_9_sequence_reference=discrete,training_s=runtime,actual_timesteps=model.num_timesteps,changed_parameter_tensors=sum(x>0 for x in changes.values()),max_parameter_change=max(changes.values()),checkpoint_reload_exact=True,results=results)
 (a.output/'metrics.json').write_text(json.dumps(metrics,indent=2));(a.output/'environment-lock.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
 root=Path(__file__).resolve().parents[1];sources=[Path(__file__),root/'src/f1energy/event_rl.py',root/'src/f1energy/event_power_lap.py',root/'src/f1energy/power_lap.py']
 if any(hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest for name,digest in before_hashes.items()):raise RuntimeError('source changed during training; do not accept run')
 manifest=dict(outputs_sha256={str(f.relative_to(a.output)):hashlib.sha256(f.read_bytes()).hexdigest() for f in a.output.rglob('*') if f.is_file()},source_sha256={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources})
 (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(metrics,indent=2))
if __name__=='__main__':main()
