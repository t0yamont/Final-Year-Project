"""Bounded, reproducible full-circuit numerical study; no telemetry/test-role reads."""
import argparse
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import platform
import shutil
import time
import numpy as np
import scipy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from f1energy.circuit import PeriodicCentreline, periodic_speed_lap
from f1energy.power_lap import PowerVehicle


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path, payload): path.write_text(json.dumps(payload, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path('configs/circuit_reference.json'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--figures', type=Path, required=True)
    parser.add_argument('--reuse', type=Path, help='Reuse hash-verified compatible case results from an earlier run')
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    geometry = Path(config['geometry'])
    if sha(geometry) != config['geometry_sha256']: raise ValueError('geometry hash mismatch')
    args.output.mkdir(parents=True, exist_ok=False)
    args.figures.mkdir(parents=True, exist_ok=False)
    inputs = {str(p):sha(p) for p in [args.config, geometry]}
    sources = {str(p):sha(p) for p in [Path(__file__), Path('src/f1energy/circuit.py'),
               Path('src/f1energy/event_power_lap.py'), Path('src/f1energy/power_lap.py')]}
    reused = {}
    if args.reuse:
        old_manifest=json.loads((args.reuse/'manifest.json').read_text())
        old_contract=json.loads((args.reuse/'contract.json').read_text())
        # Refinement schedule and reporting code can change; physics, geometry,
        # every model/solver assumption and library versions must match.
        for p, expected in old_manifest['outputs'].items():
            if sha(p) != expected:raise ValueError(f'Corrupt cached output: {p}')
        for p in ['src/f1energy/circuit.py','src/f1energy/event_power_lap.py','src/f1energy/power_lap.py']:
            p=str(Path(p))
            if old_contract['sources'][p] != sources[p]:raise ValueError(f'Changed physics dependency: {p}')
        # Explicit comprehension avoids treating a new grid schedule as a new vehicle.
        old_model={k:v for k,v in old_contract['config'].items() if k!='grid_spacing_m'}
        new_model={k:v for k,v in config.items() if k!='grid_spacing_m'}
        if old_model != new_model or old_contract['versions'] != dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__):
            raise ValueError('Incompatible cached model or runtime')
        inputs[str(args.reuse/'manifest.json')]=sha(args.reuse/'manifest.json')
        reused={r['case']:r for r in json.loads((args.reuse/'metrics.json').read_text())['cases']}
    save(args.output/'contract.json', dict(config=config, inputs=inputs, sources=sources,
         versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__)))
    vehicle = PowerVehicle(**config['vehicle'])
    xy = np.loadtxt(geometry, delimiter=',')[:, :2]
    curves, grids, cases = {}, {}, {}
    started = time.monotonic()

    def run(sigma, spacing, action, tight=False):
        key = f'sigma-{sigma:g}_grid-{spacing:g}_action-{action:g}'+('_tight' if tight else '')
        if key in cases: return cases[key]
        if sigma not in curves:
            curves[sigma] = PeriodicCentreline(xy, sigma, config['resample_spacing_m'])
        if (sigma, spacing) not in grids:
            grids[sigma, spacing] = curves[sigma].grid(spacing, config['lateral_acceleration_mps2'], config['max_speed_mps'])
        grid = grids[sigma, spacing]
        if key in reused:
            shutil.copyfile(args.reuse/f'{key}.json.gz', args.output/f'{key}.json.gz')
            cases[key]=dict(reused[key], reused_from=str(args.reuse), reused_case_sha256=sha(args.reuse/f'{key}.json.gz'))
            save(args.output/'progress.json', list(cases.values()))
            print(json.dumps(dict(case=key, reused_from=str(args.reuse))),flush=True)
            return cases[key]
        options = dict(rtol=1e-11, atol=1e-11, max_step_m=1.) if tight else {}
        before = time.monotonic()
        result = periodic_speed_lap(grid, vehicle, config['initial_energy_j'], action,
                      reserve_j=config['reserve_j'], sample_spacing_m=2., **options)
        payload = dict(sigma_m=sigma, spacing_m=spacing, action=action, tight_solver=tight,
                       grid={k:v.tolist() for k,v in asdict(grid).items()}, result=result)
        with gzip.GzipFile(filename=str(args.output/f'{key}.json.gz'), mode='wb', mtime=0) as stream:
            stream.write(json.dumps(payload, allow_nan=False).encode())
        summary = dict(case=key, sigma_m=sigma, spacing_m=spacing, action=action, tight_solver=tight,
              cells=len(grid.lengths_m), length_m=float(grid.distance_m[-1]), duration_s=result['duration_s'],
              initial_speed_mps=result['initial_speed_mps'], speed_closure_mps=result['speed_closure_error_mps'],
              minimum_speed_mps=min(row['speed_m_per_s'] for row in result['nodes']),
              max_cap_excess_mps=result['max_sample_cap_excess_mps'],
              final_energy_j=result['final_state']['energy_j'], **result['totals'],
              max_cell_energy_residual_j=result['max_cell_energy_residual_j'],
              battery_identity_residual_j=result['totals']['electrical_work_j']-vehicle.discharge_efficiency*result['totals']['battery_draw_j'],
              node_cap_excess_mps=max(row['speed_m_per_s']-cap for row,cap in zip(result['nodes'],result['braking_envelope_mps'])),
              depletion_events=sum(e['kind']=='depletion' for e in result['events']),
              shooting_trials=result['shooting_trials'], wall_seconds=time.monotonic()-before)
        cases[key] = summary
        save(args.output/'progress.json', list(cases.values()))
        print(json.dumps(summary), flush=True)
        return summary

    nominal = config['smoothing_sigma_m']
    spacings = sorted(config['grid_spacing_m'], reverse=True)
    for spacing in spacings:
        for action in [0., 1.]: run(nominal, spacing, action)
    for sigma in config['smoothing_sensitivity_m']: run(sigma, 5., 1.)
    tight = run(nominal, min(spacings), 1., True)
    ordinary = run(nominal, min(spacings), 1.)
    thresholds = config['gates']
    checks = dict(
        periodic_speed=all(abs(r['speed_closure_mps']) <= thresholds['speed_closure_mps'] for r in cases.values()),
        speed_caps=all(max(r['max_cap_excess_mps'], r['node_cap_excess_mps']) <= thresholds['cap_excess_mps'] for r in cases.values()),
        work_energy=all(abs(r['energy_residual_j']) <= thresholds['energy_balance_j'] for r in cases.values()),
        battery_identity=all(abs(r['battery_identity_residual_j']) <= thresholds['battery_identity_j'] for r in cases.values()),
        reserve=all(r['final_energy_j'] >= config['reserve_j']-1e-5 for r in cases.values()),
        tighter_solver=abs(tight['duration_s']-ordinary['duration_s']) <= thresholds['solver_time_absolute_s'])
    refinement = {}
    for action in [0., 1.]:
        fine = run(nominal, spacings[-1], action)
        coarse = run(nominal, spacings[-2], action)
        relative = abs(fine['duration_s']-coarse['duration_s'])/fine['duration_s']
        refinement[str(action)] = dict(finest_pair_relative_time_difference=relative,
             finest_pair_battery_difference_j=abs(fine['battery_draw_j']-coarse['battery_draw_j']))
        checks[f'grid_refinement_action_{action:g}'] = relative <= thresholds['finest_grid_time_relative']
    summary = dict(run_id=args.output.name, evidence='Numerical validation of assumed model; no empirical lap-time validation',
        checks=checks, all_numerical_gates_passed=all(checks.values()), refinement=refinement,
        cases=list(cases.values()), elapsed_s=time.monotonic()-started,
        geometry=dict(source_signed_area_m2=curves[nominal].signed_area_m2,
          direction='source order clockwise in plotted x/y coordinates',
          review='Main GP layout and ordering visually checked against FIA 2025 map; origin not certified timing line',
          map_url='https://www.fia.com/system/files/decision-document/2025_bahrain_grand_prix_-_event_notes_-_circuit_map_v4.pdf'),
        limitations=config['limitations'])
    save(args.output/'metrics.json', summary)

    # Exact plotted data remain in each compressed case artifact.
    nominal_key = ordinary['case']
    with gzip.open(args.output/f'{nominal_key}.json.gz', 'rt') as stream: selected=json.load(stream)
    grid, result = selected['grid'], selected['result']
    s=np.asarray(grid['distance_m']); track=np.asarray(grid['xy_m'])
    fig, axes=plt.subplots(3,1,figsize=(12,10), gridspec_kw={'height_ratios':[1.3,1,1]})
    axes[0].plot(track[:,0],track[:,1],color='#176b8a')
    axes[0].scatter(track[0,0],track[0,1],color='#b86118',label='Source origin (not certified timing line)',zorder=3)
    i=int(np.searchsorted(s,100.)); j=int(np.searchsorted(s,250.))
    axes[0].annotate('',xy=track[j],xytext=track[i],arrowprops=dict(arrowstyle='->',color='#b86118',lw=2))
    axes[0].set(aspect='equal',xlabel='Local x (m)',ylabel='Local y (m)',title='Approximate Bahrain GP centreline; source order retained')
    axes[0].legend(fontsize=9,loc='upper left',bbox_to_anchor=(1.02,1))
    axes[1].plot(s,grid['curvature_per_m'],color='#176b8a',label='Signed curvature')
    axes[1].stairs(grid['max_abs_curvature_per_m'],s,color='#b86118',linestyle='--',label='Cell maximum |curvature|')
    axes[1].set(xlabel='Distance from source origin (m)',ylabel='Curvature (1/m)'); axes[1].legend(fontsize=9)
    axes[2].stairs(np.array(grid['cell_speed_cap_mps'])*3.6,s,baseline=None,color='#b86118',linestyle=':',label='Lateral/speed cap')
    axes[2].plot(s,np.array(result['braking_envelope_mps'])*3.6,color='#555555',linestyle='--',label='Periodic braking envelope')
    axes[2].plot([r['position_m'] for r in result['samples']],[r['speed_m_per_s']*3.6 for r in result['samples']],color='#176b8a',label='Forward trajectory, full request')
    axes[2].set(xlabel='Distance from source origin (m)',ylabel='Speed (km/h)');axes[2].legend(fontsize=9,ncol=3)
    for ax in axes: ax.grid(alpha=.2)
    fig.suptitle('Full-circuit geometry and speed constraints | '+args.output.name)
    fig.text(.5,.01,f'Assumed vehicle/grip; {nominal:g} m Gaussian smoothing; {min(spacings):g} m grid. Separate lateral/longitudinal limits; no real-car accuracy claim.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.035,1,.97))
    for ext in ['png','pdf']:fig.savefig(args.figures/f'01_curvature_speed_envelope.{ext}',dpi=300)
    plt.close(fig)

    fig, axes=plt.subplots(1,3,figsize=(14,4.8))
    for action,label,color,marker in [(0.,'No electrical request','#555555','o'),(1.,'Full electrical request','#176b8a','s')]:
        rows=[run(nominal,h,action) for h in sorted(spacings)]
        axes[0].plot([r['spacing_m'] for r in rows],[r['duration_s'] for r in rows],marker=marker,color=color,label=label)
    axes[0].set(xlabel='Maximum parameter grid spacing (m)',ylabel='Simulated lap duration (s)',title='Spatial refinement');axes[0].legend(fontsize=8)
    sigmas=config['smoothing_sensitivity_m']; rows=[run(x,5.,1.) for x in sigmas]
    axes[1].plot(sigmas,[r['duration_s'] for r in rows],marker='s',color='#b86118')
    axes[1].set(xlabel='Gaussian smoothing sigma (m)',ylabel='Simulated lap duration (s)',title='Geometry sensitivity (5 m grid)')
    samples=result['samples']
    axes[2].plot([r['position_m'] for r in samples],[r['energy_j']/1e6 for r in samples],color='#176b8a')
    axes[2].axhline(config['reserve_j']/1e6,color='#555555',linestyle='--',label='Reserve')
    axes[2].set(xlabel='Distance from source origin (m)',ylabel='Battery energy (MJ)',title=f'Finite-energy lap ({min(spacings):g} m grid)');axes[2].legend(fontsize=8)
    for ax in axes:ax.grid(alpha=.2)
    fig.suptitle('Numerical refinement and model sensitivity | '+args.output.name)
    fig.text(.5,.01,'Single-lap periodic speed; battery is not periodic. Smoothing sensitivity is model uncertainty, not a statistical confidence interval.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.93))
    for ext in ['png','pdf']:fig.savefig(args.figures/f'02_refinement_sensitivity_energy.{ext}',dpi=300)
    plt.close(fig)
    outputs={str(p):sha(p) for folder in [args.output,args.figures] for p in folder.iterdir() if p.is_file()}
    save(args.output/'manifest.json',dict(inputs=inputs,sources=sources,outputs=outputs))
    print(json.dumps(dict(all_numerical_gates_passed=all(checks.values()),checks=checks,refinement=refinement)),flush=True)
    if not all(checks.values()):raise SystemExit(2)


if __name__=='__main__':main()
