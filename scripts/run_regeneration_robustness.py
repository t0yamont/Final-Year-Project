"""Frozen one-factor transfer and bounded model-aware replanning; no training."""
import argparse
import copy
import json
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path

from benchmark_circuit_control import gzsave, load_setup, make_env, save, sha, sources
from optimize_regeneration_dp import replay, search
from f1energy.circuit_control import baseline_policy, rollout
from f1energy.circuit_training_gate import validate_control_gate
from validate_regeneration import audit_replay


def read(path):
    return json.loads(Path(path).read_text())


def scenario_setup(config, scenario):
    config = copy.deepcopy(config)
    reference, curve, vehicle = load_setup(config)
    key, value = scenario['parameter'], scenario['value']
    if key == 'initial_energy_j':
        reference[key] = value
    elif key == 'drag_kg_per_m':
        reference['vehicle'][key] = value
        vehicle = replace(vehicle, **{key: value})
    elif key is not None:
        config['regeneration'][key] = value
    return config, reference, curve, vehicle


def run_case(scenario, config, protocol, original, output):
    import torch
    from stable_baselines3 import PPO
    torch.set_num_threads(1)
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA predictions required; CPU fallback forbidden')
    name = scenario['name']
    folder = output / name
    folder.mkdir()
    config, reference, curve, vehicle = scenario_setup(config, scenario)
    save(folder / 'setup.json', dict(config=config, reference=reference))
    models, devices = {}, []
    for seed in protocol['seeds']:
        path = Path(protocol['ppo']) / f'seed-{seed}' / f"checkpoint_{protocol['checkpoint_steps']}.zip"
        model = PPO.load(path, device='cuda:0')
        if model.num_timesteps != protocol['checkpoint_steps'] or any(p.device.type != 'cuda' for p in model.policy.parameters()):
            raise RuntimeError('checkpoint endpoint or device mismatch')
        models[f'ppo_seed{seed}'] = model
        devices.append(dict(seed=seed, checkpoint=str(path), sha256=sha(path), device=str(next(model.policy.parameters()).device)))
    def env(cells):
        return make_env(config, reference, curve, vehicle, cells)
    started = time.perf_counter()
    try:
        candidate = search(env(protocol['search_cells']), protocol['search'], original['basic']['actions'])
        candidate['status'] = 'completed'
    except ValueError as error:
        if str(error) != 'selected schedule failed exact search-grid replay':
            raise
        candidate = dict(status='failed', reason='No terminal-feasible schedule found within the frozen bounded search.',
                         error=str(error), wall_seconds=time.perf_counter()-started, actions=None)
    save(folder / 'search.json', candidate)
    print(name, 'search', candidate['status'], flush=True)
    rows = []
    for cells in protocol['evaluation_cells']:
        instance = env(cells)
        policies = [*protocol['fixed_policies'], *models, 'frozen_dp', 'replanned_dp']
        for policy in policies:
            row = dict(scenario=name, cells=cells, policy=policy)
            if policy == 'replanned_dp' and candidate['actions'] is None:
                rows.append(dict(row, status='unavailable', feasible=False, reason=candidate['reason']))
                continue
            if policy in models:
                action = lambda obs, m=models[policy]: m.predict(obs, deterministic=True)[0]
            elif policy in ('frozen_dp', 'replanned_dp'):
                actions = original['refined']['actions'] if policy == 'frozen_dp' else candidate['actions']
                action = lambda _, a=actions: [a[instance.index]]
            else:
                action = baseline_policy(policy, instance)
            result = rollout(instance, action)
            audit = audit_replay(result, config, reference, vehicle)
            filename = f'{policy}_{cells}.json.gz'
            gzsave(folder / filename, result)
            rows.append(dict(row, status='completed', file=str(folder / filename), duration_s=result['duration_s'],
                             final_energy_j=result['final_energy_j'], feasible=result['feasible'],
                             terminal_speed_error_mps=result['terminal_speed_error_mps'], audit=audit))
            save(folder / 'progress.json', rows)
    result = dict(scenario=name, search=candidate, results=rows, devices=devices)
    save(folder / 'metrics.json', result)
    print(name, 'done', sum(r['feasible'] for r in rows), '/', len(rows), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, default=Path('configs/regeneration_robustness_protocol.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    protocol = read(args.protocol)
    config, _ = validate_control_gate(protocol['baseline'], Path.cwd())
    inputs = {str(args.protocol): sha(args.protocol)}
    for parent in [Path(protocol[key]) for key in ('baseline', 'ppo', 'dp')]:
        for folder in [parent, *([parent / f'seed-{s}' for s in protocol['seeds']] if str(parent) == protocol['ppo'] else [])]:
            manifest = folder / 'manifest.json'
            inputs[str(manifest)] = sha(manifest)
            for group in read(manifest).values():
                if isinstance(group, dict):
                    for path, digest in group.items():
                        if sha(path) != digest:
                            raise ValueError('changed parent evidence: ' + path)
    original = {r['name']: r for r in read(Path(protocol['dp']) / 'metrics.json')['cases']}
    code = sources()
    for path in [__file__, 'scripts/optimize_regeneration_dp.py', 'scripts/benchmark_circuit_control.py', 'scripts/validate_regeneration.py', 'src/f1energy/circuit_training_gate.py']:
        code[str(Path(path))] = sha(path)
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / 'contract.json', dict(protocol=protocol, config=config, inputs=inputs, sources=code, frozen_original_actions=original))
    cases, errors = [], []
    with ProcessPoolExecutor(max_workers=protocol['workers']) as pool:
        jobs = {pool.submit(run_case, s, config, protocol, original, args.output): s['name'] for s in protocol['scenarios']}
        for job in as_completed(jobs):
            try:
                cases.append(job.result())
            except Exception:
                errors.append(dict(scenario=jobs[job], error=traceback.format_exc()))
            save(args.output / 'progress.json', dict(cases=cases, errors=errors))
    if any(sha(p) != digest for p, digest in (inputs | code).items()):
        raise RuntimeError('source/input changed during study')
    save(args.output / 'metrics.json', dict(cases=cases, errors=errors, training_performed=False))
    if errors or any(not r['feasible'] for c in cases for r in c['results']):
        save(args.output / 'failure.json', dict(reason='Predeclared robustness includes failed/unavailable controllers; see complete case metrics.', worker_errors=errors))
    save(args.output / 'manifest.json', dict(inputs=inputs, sources=code, outputs={str(p): sha(p) for p in args.output.rglob('*') if p.is_file() and p.name != 'manifest.json'}))


if __name__ == '__main__':
    main()
