"""Bounded synthetic reconstruction under known and uncertain base power."""
import argparse,json,hashlib,platform
from pathlib import Path
import numpy as np
import scipy
from f1energy.inference import forward,reconstruct

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 truth=np.array([40000.,60000.,80000.]);generated=forward(truth);observed=np.array([r['speed_m_per_s'] for r in generated['rows']])
 noisy=observed+np.random.default_rng(2026).normal(0,.1,3)
 runs=[dict(case='exact',**reconstruct(observed,base,seed,truth)) for base in [180000.,200000.,220000.] for seed in range(5)]
 runs.extend(dict(case='noisy_sigma_0.1',**reconstruct(noisy,200000.,seed,truth)) for seed in range(5))
 payload=dict(provenance='synthetic_analytic_straight_ground_truth',truth=dict(deployment_w=truth.tolist(),base_power_w=200000.,mass_kg=800.,lengths_m=[100,150,100],initial_speed_m_per_s=30.,initial_energy_j=2000000.,reserve_j=50000.,efficiency=.9,drag=0.,generated=generated),observed_speed_m_per_s=observed.tolist(),noisy_observed_speed_m_per_s=noisy.tolist(),noise_seed=2026,runs=runs,
 interpretation='Synthetic endpoint inverse fit. Missing battery labels allow different feasible deployment maps under uncertain base power. No real deployment inference.')
 out=a.output/'reconstruction.json';out.write_text(json.dumps(payload,indent=2));root=Path(__file__).resolve().parents[1]
 manifest=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,outputs_sha256={out.name:hashlib.sha256(out.read_bytes()).hexdigest()},source_sha256={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(__file__),root/'src/f1energy/inference/__init__.py']})
 (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2))
 for base in [180000.,200000.,220000.]:
  r=[x for x in runs if x['case']=='exact' and x['assumed_base_power_w']==base];print(base,'max_speed_RMSE',max(x['speed_rmse_m_per_s'] for x in r),'action_RMSE',r[0]['action_rmse_w'],'feasible',all(x['energy_feasible'] for x in r))
 print('noise',runs[-1]['speed_rmse_m_per_s'],runs[-1]['action_rmse_w'])
if __name__=='__main__':main()
