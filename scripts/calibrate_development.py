"""Development-only effective-power diagnostic; frozen lap roles supplied by data audit."""
import argparse,csv,hashlib,json,platform
from pathlib import Path
import numpy as np
import scipy
from f1energy.identification import fit_effective,evaluate

def read(path):
 with path.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def arrays(rows):return ([float(r['speed_mid_m_per_s']) for r in rows],[float(r['acceleration_m_per_s2']) for r in rows])
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=Path('results/calibration-data-001'));p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 fitrows=read(args.input/'fit.csv');valrows=read(args.input/'validation.csv')
 if {int(float(r['lap_number'])) for r in fitrows}!={4,10}:raise ValueError('expected development fit laps4/10')
 if {int(float(r['lap_number'])) for r in valrows}!={13}:raise ValueError('expected development validation lap13')
 args.output.mkdir(parents=True,exist_ok=False)
 results={}
 for mass in [750.,800.,850.]:
  fit=fit_effective(*arrays(fitrows),mass);results[str(mass)]=dict(fit=fit,fit_diagnostic=evaluate(fit,*arrays(fitrows)),validation_diagnostic=evaluate(fit,*arrays(valrows)))
 strata={}
 for drs in sorted({r['drs'] for r in fitrows}):
  rows=[r for r in fitrows if r['drs']==drs]
  if len(rows)>=5:
   fit=fit_effective(*arrays(rows));strata[drs]=dict(fit=fit,validation_diagnostic=evaluate(fit,*arrays([r for r in valrows if r['drs']==drs])))
 payload=dict(mass_sensitivity=results,drs_strata=strata,fit_laps=[4,10],development_validation_laps=[13],excluded_primary_laps=[16],interpretation='Acceleration-window proxy, not proven straight. Fit-to-derivative residuals are not trajectory prediction or deployment recovery. No final test set evaluated.')
 out=args.output/'metrics.json';out.write_text(json.dumps(payload,indent=2,allow_nan=False));root=Path(__file__).resolve().parents[1]
 inputs=[args.input/'fit.csv',args.input/'validation.csv']
 for name in ['manifest.json','summary.json']:
  if (args.input/name).exists():inputs.append(args.input/name)
 manifest=dict(python=platform.python_version(),scipy=scipy.__version__,numpy=np.__version__,inputs_sha256={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs},outputs_sha256={'metrics.json':hashlib.sha256(out.read_bytes()).hexdigest()},source_sha256={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(__file__),root/'src/f1energy/identification.py']})
 (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:{'power_w':v['fit']['effective_total_power_w'],'drag':v['fit']['drag_coefficient_kg_per_m'],'boundary':v['fit']['parameter_boundary_hits'],'condition':v['fit']['scaled_design_condition_number'],'validation':v['validation_diagnostic']} for k,v in results.items()},indent=2))
if __name__=='__main__':main()
