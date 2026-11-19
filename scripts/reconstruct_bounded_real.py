"""Frozen partial-window real-motion inverse diagnostic; no full-lap inference."""
import argparse
import csv
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np
from scipy.optimize import minimize
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / 'configs/bounded_real_reconstruction_protocol.json'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def design(rows):
    """Build cumulative time/action matrix, resetting at every missing interval."""
    labels, starts, durations, blocks = [], [], [], []
    previous = None
    segment = -1
    local_time = 0.
    key_to_block = {}
    for row in rows:
        if previous != row['start_utc']:
            segment += 1
            local_time = 0.
            initial = float(row['speed_start_mps'])
        key = (segment, int(local_time / 2.))
        if key not in key_to_block:
            key_to_block[key] = len(key_to_block)
        labels.append(segment)
        starts.append(initial)
        durations.append(float(row['dt_s']))
        blocks.append(key_to_block[key])
        local_time += durations[-1]
        previous = row['end_utc']
    matrix = np.zeros((len(rows), len(key_to_block)))
    for i, (segment, dt, block) in enumerate(zip(labels, durations, blocks)):
        if i and labels[i-1] == segment:
            matrix[i] = matrix[i-1]
        matrix[i, block] += dt
    return np.array(labels), np.array(starts), np.array(durations), np.array(blocks), matrix

def self_check():
    rows = [dict(start_utc='a', end_utc='b', speed_start_mps='30', dt_s='1'),
            dict(start_utc='b', end_utc='c', speed_start_mps='31', dt_s='1'),
            dict(start_utc='d', end_utc='e', speed_start_mps='40', dt_s='1')]
    labels, initial, dt, block, matrix = design(rows)
    assert labels.tolist() == [0, 0, 1]
    assert initial.tolist() == [30, 30, 40]
    assert np.array_equal(matrix, [[1, 0], [2, 0], [0, 1]])
    # Independent drag-free work-energy endpoint and discharge check.
    predicted = np.sqrt(initial**2 + 2 / 800 * (matrix @ np.array([400000., 400000.])))
    assert np.isclose(predicted[1]**2, 30**2 + 2*400000*2/800)
    assert np.isclose(np.bincount(block, weights=dt) @ np.array([60000., 60000.])/.9, 200000.)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--figures', type=Path, required=True)
    args = parser.parse_args()
    self_check()
    protocol_bytes = PROTOCOL.read_bytes()
    protocol = json.loads(protocol_bytes.decode('utf-8-sig'))
    args.output.mkdir(parents=True, exist_ok=False)
    args.figures.mkdir(parents=True, exist_ok=False)
    (args.output/'contract.json').write_bytes(protocol_bytes)
    source = ROOT/protocol['input']
    with source.open(newline='', encoding='utf-8-sig') as handle:
        rows = [r for r in csv.DictReader(handle) if all(r[k] == v for k,v in protocol['selection'].items())]
    if not rows:
        (args.output/'failure.json').write_text(json.dumps({'reason':'Frozen lap selection absent; no replacement'}))
        raise ValueError('Frozen lap absent')
    rows.sort(key=lambda r:r['start_utc'])
    with (args.output/'selected_windows.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    labels, initial, dt, blocks, matrix = design(rows)
    speed = np.array([float(r['speed_end_mps']) for r in rows])
    mid = np.array([float(r['speed_mid_mps']) for r in rows])
    block_dt = np.bincount(blocks, weights=dt)
    cumulative_dt = matrix.sum(axis=1)
    drag_integral = np.zeros(len(rows))
    for i in range(len(rows)):
        drag_integral[i] = dt[i]*mid[i]**3 + (drag_integral[i-1] if i and labels[i]==labels[i-1] else 0)
    runs=[]
    constraints=protocol['constraints']; tolerance=protocol['compatibility']
    for mass in protocol['physical_grid']['mass_kg']:
        drag=protocol['physical_grid']['drag_at_800kg_kg_per_m']*mass/800
        for base800 in protocol['physical_grid']['base_at_800kg_w']:
            base=base800*mass/800
            offset=initial**2+2/mass*(base*cumulative_dt-drag*drag_integral)
            coefficients=2/mass*120000*matrix
            def predict(x):
                return np.sqrt(np.maximum(offset+coefficients@x, 1e-12))
            def objective(x):
                residual=predict(x)-speed
                return np.mean(residual**2)
            def gradient(x):
                predicted=predict(x)
                return ((predicted-speed)/predicted)@coefficients/len(speed)
            energy_coeff=block_dt*120000/.9
            budget=min(constraints['initial_energy_j']-constraints['reserve_j'],constraints['gross_discharge_limit_j'])
            for start in protocol['optimizer']['starts_fraction']:
                result=minimize(objective,np.full(len(block_dt),start),jac=gradient,method='SLSQP',bounds=[(0,1)]*len(block_dt),constraints=[{'type':'ineq','fun':lambda x:1-energy_coeff@x/budget,'jac':lambda x:-energy_coeff/budget}],options={'ftol':1e-10,'maxiter':400})
                predicted=predict(result.x);residual=predicted-speed
                power=result.x*120000;draw=float(energy_coeff@result.x)
                remaining=constraints['initial_energy_j']-np.cumsum(power[blocks]*dt/.9)
                rmse=float(np.sqrt(np.mean(residual**2)));maximum=float(abs(residual).max())
                feasible=bool(min(remaining)>=constraints['reserve_j']-1 and max(remaining)<=constraints['capacity_j']+1 and draw<=constraints['gross_discharge_limit_j']+1 and min(power)>=-1e-5 and max(power)<=120000+1e-5)
                compatible=bool(result.success and feasible and rmse<=tolerance['rmse_mps'] and maximum<=tolerance['maximum_absolute_error_mps'])
                runs.append(dict(mass_kg=mass,base_power_w=base,drag_kg_per_m=drag,start_fraction=start,success=bool(result.success),message=result.message,iterations=result.nit,rmse_mps=rmse,max_abs_error_mps=maximum,draw_j=draw,terminal_energy_j=float(remaining[-1]),partial_energy_feasible=feasible,compatible=compatible,deployment_w=power.tolist(),predicted_speed_mps=predicted.tolist(),partial_energy_j=remaining.tolist()))
    payload=dict(study_id=protocol['study_id'],window_count=len(rows),segment_count=int(labels.max()+1),action_count=len(block_dt),selected_duration_s=float(dt.sum()),elapsed_first_to_last_s=(datetime.fromisoformat(rows[-1]['end_utc'])-datetime.fromisoformat(rows[0]['start_utc'])).total_seconds(),block_duration_s=block_dt.tolist(),block_index=blocks.tolist(),segment_index=labels.tolist(),runs=runs)
    (args.output/'reconstruction.json').write_text(json.dumps(payload,indent=2))
    # First start per physical case; repeated starts are retained in JSON.
    shown=runs[::3]
    fig,axes=plt.subplots(3,1,figsize=(9,9),layout='constrained')
    x=np.cumsum(dt)
    axes[0].plot(x,speed,color='black',linewidth=1.8,label='Observed endpoints')
    for r in shown:
        label=f"{r['mass_kg']} kg / {r['base_power_w']/1000:.0f} kW"
        axes[0].plot(x,r['predicted_speed_mps'],alpha=.7,linewidth=.8)
        axes[1].step(x,np.array(r['deployment_w'])[blocks]/1000,where='post',linewidth=.9,label=label)
        axes[2].plot(x,np.array(r['partial_energy_j'])/1e6,linewidth=.9)
    axes[0].set_ylabel('Speed (m/s)');axes[0].legend(loc='upper left')
    axes[1].set_ylabel('Conditional deployment (kW)');axes[1].set_ylim(-3,123)
    axes[1].legend(ncol=3,fontsize=7,loc='lower center',bbox_to_anchor=(.5,1.01))
    axes[2].set_ylabel('Partial-window energy (MJ)');axes[2].axhline(.1,color='black',linestyle='--',label='Reserve')
    axes[2].set_xlabel('Cumulative selected-window time (s); omitted intervals removed')
    for ax in axes: ax.grid(alpha=.2)
    fig.suptitle('Bahrain development lap 13: conditional inverse diagnostic\nObserved initial speed resets at each segment; no full-lap battery claim',fontsize=11)
    fig.savefig(args.figures/'01_bounded_real_inverse.png',dpi=300)
    fig.savefig(args.figures/'01_bounded_real_inverse.pdf')
    plt.close(fig)
    outputs=list(args.output.glob('*.json'))+list(args.output.glob('*.csv'))+list(args.figures.glob('*'))
    manifest=dict(protocol_sha256=sha(PROTOCOL),inputs_sha256={str(source.relative_to(ROOT)):sha(source)},source_sha256={str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},outputs_sha256={str(f.resolve().relative_to(ROOT)):sha(f) for f in outputs},threads=1)
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({k:v for k,v in payload.items() if k not in ['runs','block_index','segment_index','block_duration_s']},indent=2))
    for r in shown: print(r['mass_kg'],r['base_power_w'],r['rmse_mps'],r['max_abs_error_mps'],r['draw_j'],r['compatible'])

if __name__=='__main__': main()

