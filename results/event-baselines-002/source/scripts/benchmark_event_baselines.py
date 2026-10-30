"""Execute the predeclared bounded synthetic event-model DP baseline protocol."""
import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from f1energy.event_baselines import TransitionCache, dynamic_programming, exhaustive, replay
from f1energy.event_power_lap import integrate_segment
from f1energy.event_rl import EventScenario, validate_training_gate
from f1energy.power_lap import PowerState


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified_cache(directory, name, expected_sources, inputs):
    manifest_path = directory/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    old_sources = {k.replace('\\', '/'): v for k, v in manifest['source_sha256'].items()}
    for name_source in ('src/f1energy/event_power_lap.py', 'src/f1energy/power_lap.py', 'src/f1energy/event_rl.py'):
        if old_sources.get(name_source) != expected_sources[name_source]:
            raise ValueError('persisted cache has stale solver/scenario sources')
    path = directory/f'{name}-transitions.json'
    if sha(path) != manifest['outputs_sha256'].get(path.name):
        raise ValueError('persisted transition cache hash mismatch')
    for item in (manifest_path, path):
        inputs[item.resolve().relative_to(ROOT).as_posix()] = sha(item)
    return json.loads(path.read_text())


def dense_verification(scenario, actions, *, tight):
    state = PowerState(scenario.initial_speed_m_per_s, scenario.initial_energy_j)
    rows, min_energy, max_excess, max_residual = [], state.energy_j, -math.inf, 0.
    settings = dict(rtol=1e-11, atol=1e-11, max_step_m=1.) if tight else {}
    for index, action in enumerate(actions):
        length, cap = scenario.lengths_m[index], min(100., scenario.exit_caps_m_per_s[index])
        start = state.distance_m
        state, info = integrate_segment(scenario.vehicle, state, length, cap, action,
                                        reserve_j=scenario.reserve_j, sample_spacing_m=2., **settings)
        m, k, b = scenario.vehicle.mass_kg, scenario.vehicle.drag_kg_per_m, scenario.vehicle.friction_deceleration_m_per_s2
        for point in info['samples']:
            remaining = max(0., length-(point['position_m']-start))
            q = cap*cap+2*b*remaining if k == 0 else cap*cap*math.exp(2*k*remaining/m)+(m*b/k)*math.expm1(2*k*remaining/m)
            max_excess = max(max_excess, point['speed_m_per_s']-min(100., math.sqrt(q)))
            min_energy = min(min_energy, point['energy_j'])
        max_residual = max(max_residual, abs(info['energy_residual_j']))
        rows.append(info)
    feasible = min_energy >= scenario.reserve_j-1e-6 and max_excess <= 1e-6 and max_residual <= .01
    return dict(elapsed_s=state.elapsed_s, min_energy_j=min_energy, max_envelope_excess_m_per_s=max_excess,
                max_residual_j=max_residual, feasible=feasible, settings=settings, trace=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--validation-report', type=Path, default=ROOT/'results/event-validation-002/summary.json')
    parser.add_argument('--refine-stress', action='store_true', help='Use the documented stress-only follow-up grids')
    parser.add_argument('--reuse-run', type=Path, help='Hash-verified saved transitions with identical physics and scenario')
    args = parser.parse_args()
    validate_training_gate(args.validation_report, ROOT)
    sources = [Path(__file__), ROOT/'src/f1energy/event_baselines.py', ROOT/'src/f1energy/event_power_lap.py',
               ROOT/'src/f1energy/power_lap.py', ROOT/'src/f1energy/event_rl.py', ROOT/'docs/event_baseline_protocol.md']
    before = {p.relative_to(ROOT).as_posix(): sha(p) for p in sources}
    inputs = {str(args.validation_report.resolve().relative_to(ROOT)): sha(args.validation_report),
              str(args.validation_report.parent.resolve().relative_to(ROOT)/'manifest.json'): sha(args.validation_report.parent/'manifest.json')}
    nominal = EventScenario()
    scenarios = dict(nominal_development=nominal,
        new_predeclared_evaluation=replace(nominal, lengths_m=(360., 440.), exit_caps_m_per_s=(28., 20.),
            initial_energy_j=400000., vehicle=replace(nominal.vehicle, mass_kg=840.)),
        four_segment_development=replace(nominal, lengths_m=(120., 280., 160., 240.), exit_caps_m_per_s=(32., 20., 28., 20.)))
    if args.refine_stress:
        scenarios = {'four_segment_development': scenarios['four_segment_development']}
    energy_steps = (20000., 10000., 5000., 2500., 1000., 500., 250., 100.) if args.refine_stress else (20000., 10000., 5000., 2500.)
    saved_ppo = {}
    for seed in (() if args.refine_stress else range(3)):
        directory = ROOT/f'results/event-ppo-seed{seed}-001'
        manifest = json.loads((directory/'manifest.json').read_text())
        for name in ('config.json', 'metrics.json'):
            file = directory/name
            if sha(file) != manifest['outputs_sha256'][name]:
                raise ValueError('PPO input hash mismatch')
            inputs[file.relative_to(ROOT).as_posix()] = sha(file)
        config = json.loads((directory/'config.json').read_text())
        for name, data in config['scenarios'].items():
            if json.loads(json.dumps(asdict(scenarios[name]))) != data:
                raise ValueError('saved PPO scenario differs from benchmark')
        for path in ('src/f1energy/event_power_lap.py', 'src/f1energy/power_lap.py'):
            recorded = {k.replace('\\', '/'): v for k, v in manifest['source_sha256'].items()}
            if recorded[path] != before[path]:
                raise ValueError('saved PPO physics differ from baseline physics')
        saved_ppo[seed] = json.loads((directory/'metrics.json').read_text())

    args.output.mkdir(parents=True, exist_ok=False)
    payload = dict(created_utc=datetime.now(timezone.utc).isoformat(), cases={}, assessment={'gate': 'running'},
                   environment=dict(python=platform.python_version(), platform=platform.platform(),
                       packages={p: importlib.metadata.version(p) for p in ('numpy', 'scipy', 'gymnasium')}))
    started = time.perf_counter()
    caches = {}
    try:
        for name, scenario in scenarios.items():
            if time.perf_counter()-started > 300:
                raise RuntimeError('aggregate pilot budget exceeded')
            case_started = time.perf_counter()
            bank = TransitionCache(scenario)
            caches[name] = bank
            if args.reuse_run:
                bank.load_verified_records(verified_cache(args.reuse_run, name, before, inputs))
            actions = (0., .5, 1.) if name == 'four_segment_development' else (0., .25, .5, .75, 1.)
            rows = {}
            case = dict(scenario=asdict(scenario), action_grid=actions, results=rows)
            payload['cases'][name] = case
            def measure(label, function):
                tick = time.perf_counter()
                row = function()
                row['solve_and_replay_s'] = time.perf_counter()-tick
                rows[label] = row
                return row
            for label, action in [('zero', 0.), ('half', .5), ('full', 1.)]:
                measure(label, lambda action=action: replay(scenario, (action,)*len(scenario.lengths_m), cache=bank))
            reference = measure('exhaustive', lambda: exhaustive(scenario, actions, cache=bank))
            for step in energy_steps:
                result = measure(f'dp_{int(step)}J', lambda step=step: dynamic_programming(scenario, step, actions, cache=bank))
                result['gap_to_matching_exhaustive_s'] = result['elapsed_s']-reference['elapsed_s']
            if name != 'four_segment_development':
                measure('exhaustive_nine_actions', lambda: exhaustive(scenario, tuple(i/8 for i in range(9)), cache=bank))
                for seed, prior in saved_ppo.items():
                    record = prior['results'][name]['ppo']
                    row = replay(scenario, [x['action'] for x in record['trace']], cache=bank)
                    if abs(row['elapsed_s']-record['elapsed_s']) > 1e-8:
                        raise ValueError('saved PPO action replay does not reproduce the recorded result')
                    rows[f'ppo_seed{seed}'] = dict(row, input_run=f'event-ppo-seed{seed}-001', training_s=prior['training_s'])
            verify_start = time.perf_counter()
            standard = dense_verification(scenario, reference['actions'], tight=False)
            tight = dense_verification(scenario, reference['actions'], tight=True)
            verification = dict(standard=standard, tight=tight, time_difference_s=abs(tight['elapsed_s']-standard['elapsed_s']),
                                elapsed_s=time.perf_counter()-verify_start)
            case['verification'] = verification
            dp_rows = [r for label, r in rows.items() if label.startswith('dp_')]
            case['assessment'] = dict(physical_replays_passed=all(r['feasible'] for r in rows.values()) and standard['feasible'] and tight['feasible'],
                finite_reference_consistent=all(r['gap_to_matching_exhaustive_s'] >= -1e-5 for r in dp_rows),
                finest_energy_grid_agrees=abs(dp_rows[-1]['gap_to_matching_exhaustive_s']) <= 1e-4,
                integration_agrees=verification['time_difference_s'] <= 1e-5)
            case['runtime_s'] = time.perf_counter()-case_started
            case['cache'] = dict(uncached_transitions=bank.calls, hits=bank.hits, loaded_records=bank.loaded_records,
                                 timing_note='Sequential warm-cache timings; not an independent hardware speed ranking.')
            if case['runtime_s'] > 120 or time.perf_counter()-started > 300:
                raise RuntimeError('declared wall-time pilot budget exceeded')
            print(json.dumps(dict(case=name, elapsed_s=reference['elapsed_s'], dp_gap_s=dp_rows[-1]['gap_to_matching_exhaustive_s'],
                                  runtime_s=case['runtime_s'], cache=case['cache'], assessment=case['assessment'])), flush=True)
        unchanged = before == {p.relative_to(ROOT).as_posix(): sha(p) for p in sources}
        passed = unchanged and all(all(c['assessment'].values()) for c in payload['cases'].values())
        payload['assessment'] = dict(gate='passed_bounded_synthetic_baseline_gate' if passed else 'rejected', sources_unchanged=unchanged,
            scope='Finite grids on three synthetic development/pilot scenarios; not a continuous optimum or empirical F1 validation.')
    except Exception as exc:
        payload['assessment'] = dict(gate='rejected', exception_type=type(exc).__name__, message=str(exc))
    finally:
        payload['runtime_s'] = time.perf_counter()-started
        (args.output/'metrics.json').write_text(json.dumps(payload, indent=2)+'\n')
        for name, bank in caches.items():
            (args.output/f'{name}-transitions.json').write_text(json.dumps(bank.export(), indent=2)+'\n')
        snapshot = args.output/'source'
        for path in sources:
            target = snapshot/path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
        (args.output/'validation-evidence.json').write_bytes(args.validation_report.read_bytes())
        outputs = {p.relative_to(args.output).as_posix(): sha(p) for p in args.output.rglob('*') if p.is_file()}
        (args.output/'manifest.json').write_text(json.dumps(dict(source_sha256=before, inputs_sha256=inputs, outputs_sha256=outputs), indent=2)+'\n')
    print(json.dumps(payload['assessment'], indent=2))
    return 0 if payload['assessment']['gate'].startswith('passed') else 1


if __name__ == '__main__':
    raise SystemExit(main())
