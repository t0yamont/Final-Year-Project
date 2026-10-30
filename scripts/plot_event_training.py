"""Plot immutable event-model pilot comparisons, training logs and replay traces."""
import sys,json,hashlib
from pathlib import Path
from dataclasses import replace
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from f1energy.event_rl import EventScenario
from f1energy.power_lap import PowerState
from f1energy.event_power_lap import integrate_segment
out=ROOT/'figures/dissertation/event-training-v1';out.mkdir(parents=True,exist_ok=False)
runs=[ROOT/f'results/event-ppo-seed{s}-001' for s in range(3)]
metrics=[json.loads((r/'metrics.json').read_text()) for r in runs]
inputs=[r/name for r in runs for name in ('metrics.json','config.json','logs/progress.csv')]
files=[]
def save(fig,name):
 for ext in ('png','pdf'):
  p=out/f'{name}.{ext}';fig.savefig(p,dpi=300,bbox_inches='tight');files.append(p)
 plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(11,4),layout='constrained')
for ax,case in zip(axs,('nominal_development','new_predeclared_evaluation')):
 labels=['Zero','Half','Full','PPO seed 0','PPO seed 1','PPO seed 2']
 values=[metrics[0]['results'][case][k]['elapsed_s'] for k in ('zero','half','full')]+[m['results'][case]['ppo']['elapsed_s'] for m in metrics]
 ax.scatter(values,range(6));ax.set_yticks(range(6),labels);ax.invert_yaxis();ax.grid(axis='x',alpha=.2)
 ax.set(xlabel='Feasible elapsed time (s)',title='Development scenario' if case=='nominal_development' else 'Predeclared new evaluation scenario')
fig.suptitle('Synthetic event power/drag/braking model: 4,096-step PPO pilots')
save(fig,'01_event_controller_comparison')
fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
for seed,run in enumerate(runs):
 d=pd.read_csv(run/'logs/progress.csv');ax.plot(d['time/total_timesteps'],-d['rollout/ep_rew_mean'],label=f'Seed {seed}')
ax.set(xlabel='Training timesteps',ylabel='Rolling training episode elapsed time (s)',title='Synthetic event model: PPO learning curves (training episodes)');ax.legend();ax.grid(alpha=.2)
save(fig,'02_event_training_curves')
s=EventScenario();fig,axs=plt.subplots(2,1,figsize=(10,7),layout='constrained')
for label,actions in [('Zero',[0,0]),('Half',[.5,.5]),('Full',[1,1]),('PPO seed 0',[x['action'] for x in metrics[0]['results']['nominal_development']['ppo']['trace']])]:
 state=PowerState(s.initial_speed_m_per_s,s.initial_energy_j);points=[dict(position_m=0,speed_m_per_s=state.speed_m_per_s,energy_j=state.energy_j)]
 for length,cap,action in zip(s.lengths_m,s.exit_caps_m_per_s,actions):
  state,info=integrate_segment(s.vehicle,state,length,cap,action,s.reserve_j,sample_spacing_m=2.)
  points.extend(info['samples'])
 axs[0].plot([p['position_m'] for p in points],[p['speed_m_per_s'] for p in points],label=label)
 axs[1].plot([p['position_m'] for p in points],[p['energy_j']/1000 for p in points],label=label)
axs[1].axhline(s.reserve_j/1000,color='black',ls='--',lw=1,label='Reserve')
axs[0].set(ylabel='Speed (m/s)',title='Synthetic development scenario: dense replay of saved actions')
axs[1].set(xlabel='Distance (m)',ylabel='Usable model battery energy (kJ)')
for ax in axs:ax.legend(fontsize=8,ncol=3);ax.grid(alpha=.2)
save(fig,'03_event_replay_profiles')
caption=out/'captions.md';caption.write_text('''# Event-model pilot figures
01: Shared event dynamics and scenario constraints. Individual PPO seed points; three short runs do not establish convergence or population uncertainty. Scenarios frozen before training; new evaluation not used for tuning. Timings must not be compared directly with prior force-model timings.
02: Rolling training episode returns converted to elapsed seconds; stochastic training actions, not independent deterministic evaluation or confidence intervals. Each seed trained4,096 steps on CPU.
03: Dense replay of saved nominal actions with exact reserve and braking event handling. Synthetic assumed vehicle/geometry, not a real qualifying lap or measured battery trace. Full and PPO may overlap after early reserve depletion. All plots are generated from saved metrics and logs; profiles use the same frozen solver with source hash recorded.
''');files.append(caption)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=dict(inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},source_sha256={str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),ROOT/'src/f1energy/event_power_lap.py',ROOT/'src/f1energy/event_rl.py')},outputs_sha256={p.name:sha(p) for p in files})
(out/'manifest.json').write_text(json.dumps(manifest,indent=2));print(out)
