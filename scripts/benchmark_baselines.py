"""Nominal-only bounded synthetic baseline benchmark; reads saved PPO checkpoints."""
import argparse,json,hashlib,time,dataclasses
from pathlib import Path
from f1energy.lap import default_scenario
from f1energy.baselines import dynamic_programming,exhaustive,replay

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 scenario=default_scenario();results={}
 for label,fn in [('zero',lambda:replay(scenario,[0.]*4)),('half',lambda:replay(scenario,[.5]*4)),('full',lambda:replay(scenario,[1.]*4)),('exhaustive_81',lambda:exhaustive(scenario))]+[(f'dp_{step}J',lambda step=step:dynamic_programming(scenario,step)) for step in [100000,50000,10000,1000,100]]:
  t=time.perf_counter();row=fn();row['solve_and_replay_s']=time.perf_counter()-t;results[label]=row
 import torch
 from stable_baselines3 import PPO
 from f1energy.rl import LapEnv
 torch.set_num_threads(1);checkpoints={}
 for run in ['synthetic-ppo-001','synthetic-ppo-seed1-001','synthetic-ppo-seed2-001']:
  checkpoint=Path('results')/run/'ppo.zip'
  if not checkpoint.exists():raise FileNotFoundError(checkpoint)
  checkpoints[str(checkpoint)]=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
  model=PPO.load(checkpoint,device='cpu');env=LapEnv(scenario);obs,_=env.reset();done=False;actions=[]
  while not done:
   action,_=model.predict(obs,deterministic=True);actions.append(float(action[0]));obs,_,done,_,_=env.step(action)
  results[run]=replay(scenario,actions)
 payload=dict(scenario=dataclasses.asdict(scenario),results=results,interpretation='Nominal synthetic case only. DP energy rounding and finite actions; exhaustive reference covers 81 action sequences, not continuous actions.')
 metrics=a.output/'metrics.json';metrics.write_text(json.dumps(payload,indent=2));root=Path(__file__).resolve().parents[1]
 manifest=dict(inputs_sha256=checkpoints,outputs_sha256={'metrics.json':hashlib.sha256(metrics.read_bytes()).hexdigest()},source_sha256={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(__file__),root/'src/f1energy/baselines.py',root/'src/f1energy/lap.py']})
 (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:dict(elapsed_s=v['elapsed_s'],grid_objective_s=v.get('grid_objective_s'),feasible=v['feasible']) for k,v in results.items()},indent=2))
if __name__=='__main__':main()
