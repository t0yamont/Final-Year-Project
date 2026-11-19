"""Predeclared64-replay fixed terminal-guard evaluation; no training."""
import argparse
import json
import platform
import time
import traceback
from pathlib import Path

import numpy as np
import stable_baselines3
import torch
from stable_baselines3 import PPO

from benchmark_circuit_control import gzsave, save, sha, sources
from evaluate_circuit_sensitivity import scenario_reference, verify_manifest, audit_rollout, numerical_pairs
from f1energy.circuit import PeriodicCentreline
from f1energy.circuit_control import baseline_policy, rollout, control_grid
from f1energy.circuit_training_gate import validate_control_gate
from f1energy.experiment import describe, isolated_rng
from f1energy.power_lap import PowerVehicle
from f1energy.training_device import require_cuda
from f1energy.terminal_guard import TerminalGuardEnv


def planned_cases(protocol):
    return [(s, c) for s in protocol['scenarios'] for c in protocol['cadences']]


def validate_protocol(protocol):
    expected = [('nominal', None, None), ('drag_plus10', 'drag_kg_per_m', 1.1)]
    actual = [(s['name'], s['parameter'], s['value']) for s in protocol['scenarios']]
    if actual != expected or protocol['training_seeds'] != [0, 1, 2] or protocol['checkpoint_steps'] != 16384:
        raise ValueError('this runner requires the predeclared two scenarios and all final three seeds')
    if protocol['guard'] != dict(protected_energy_j=250000., terminal_span_lap_fraction=1/55):
        raise ValueError('fixed guard budget or physical span changed')
    if protocol['fixed_policies'] != ['zero', 'half', 'full', 'spread', 'exit_boost']:
        raise ValueError('matched fixed baseline set changed')
    grids = [(c['blocks'], c['coarse_cells_per_block'], c['fine_cells_per_block']) for c in protocol['cadences']]
    if grids != [(55, 80, 160), (110, 40, 80)]:
        raise ValueError('cadences must share4400/8800 physical cells')
    if protocol['conditions'] != dict(initial_speed_mps=70., terminal_speed_mps=70., initial_energy_j=2e6, reserve_j=1e5):
        raise ValueError('common boundary conditions changed')
    if protocol['gates'] != dict(relative_lap_time=.005, gain_error_s=.05, terminal_speed_error_mps=1e-5,
                                cap_excess_mps=1e-5, energy_balance_j=1., battery_identity_j=.01):
        raise ValueError('predeclared acceptance thresholds changed')


def audit_guard(record, env, gates):
    """Check saved guard decisions/floors and every block's battery identity."""
    valid = True
    max_battery_error = 0.
    previous_energy = env.initial_energy
    for index, row in enumerate(record['trace']):
        guard = row['terminal_guard']
        terminal = index >= env.blocks - env.terminal_blocks
        expected_floor = env.reserve if terminal else env.reserve + env.protected_energy_j
        expected_action = 1. if terminal else guard['proposed_action']
        error = abs(row['electrical_work_j'] - env.vehicle.discharge_efficiency *
                    (previous_energy - row['state']['energy_j']))
        max_battery_error = max(max_battery_error, error)
        valid = valid and (np.isfinite(guard['proposed_action']) and 0 <= guard['proposed_action'] <= 1 and
            guard['issued_action'] == row['action'] == expected_action and
            guard['physical_reserve_j'] == env.reserve and guard['reserve_floor_j'] == expected_floor and
            guard['protected_floor_active'] == (not terminal) and
            guard['terminal_request_override'] == terminal and
            guard['action_changed'] == (expected_action != guard['proposed_action']) and
            guard['depletion_events'] == sum(e['kind'] == 'depletion' for e in row['events']) and
            row['state']['energy_j'] >= expected_floor - 1e-5 and
            abs(row['battery_draw_j'] - (previous_energy - row['state']['energy_j'])) <= gates['battery_identity_j'])
        previous_energy = row['state']['energy_j']
    return dict(passed=bool(valid and max_battery_error <= gates['battery_identity_j']),
                max_block_battery_identity_error_j=max_battery_error)


def source_files():
    result = sources()
    for name in [__file__, 'scripts/benchmark_circuit_control.py', 'src/f1energy/experiment.py',
                 'src/f1energy/training_device.py', 'src/f1energy/circuit_training_gate.py',
                 'scripts/evaluate_circuit_sensitivity.py', 'src/f1energy/terminal_guard.py']:
        result[str(Path(name))] = sha(name)
    return result


def evaluate(args):
    root = Path(__file__).resolve().parents[1]
    if Path.cwd().resolve() != root:
        raise ValueError('run from project root')
    protocol = json.loads(args.protocol.read_text())
    validate_protocol(protocol)
    # Exclusivity is checked before any CUDA work or source-run reads.
    args.output.mkdir(parents=True, exist_ok=False)
    inputs = {str(args.protocol): sha(args.protocol)}
    before = source_files()
    rows, errors, cases, models = [], [], [], {}
    save(args.output / 'contract.json', dict(protocol=protocol, inputs=inputs, sources=before,
         versions=dict(python=platform.python_version(), torch=torch.__version__, sb3=stable_baselines3.__version__, numpy=np.__version__)))
    try:
        config, _ = validate_control_gate(protocol['baselines'], root)
        source = root / protocol['source_run']
        for folder in [source, *(source / f'seed-{s}' for s in protocol['training_seeds']),
                       root / protocol['baselines'], root / config['numerical_gate'],
                       root / protocol['sensitivity_run']]:
            verify_manifest(folder, root, inputs)
        source_metrics = json.loads((source / 'metrics.json').read_text())
        if not source_metrics.get('all_seeds_completed_and_passed'):
            raise ValueError('source multi-seed study is not accepted')
        source_protocol = json.loads((source / 'contract.json').read_text())['protocol']
        if source_protocol['training_seeds'] != protocol['training_seeds'] or source_protocol['steps_per_seed'] != protocol['checkpoint_steps']:
            raise ValueError('source endpoint differs from predeclared transfer')
        reference_path = Path(config['reference_config'])
        reference = json.loads(reference_path.read_text())
        if (config['action_blocks'], config['initial_speed_mps'], reference['initial_energy_j'], reference['reserve_j']) != (55, 70., 2e6, 1e5):
            raise ValueError('source boundary conditions differ')
        if (reference['vehicle']['mass_kg'], reference['vehicle']['drag_kg_per_m'],
            reference['lateral_acceleration_mps2'], reference['smoothing_sigma_m']) != (800., 1., 20., 10.):
            raise ValueError('source nominal assumptions differ')
        if sha(reference['geometry']) != reference['geometry_sha256']:
            raise ValueError('geometry changed')
        inputs[str(reference_path)] = sha(reference_path)
        inputs[reference['geometry']] = sha(reference['geometry'])
        gpu = require_cuda()
        torch.set_num_threads(1)
        device_records = []
        for seed in protocol['training_seeds']:
            checkpoint = source / f'seed-{seed}' / f'checkpoint_{protocol["checkpoint_steps"]}.zip'
            with isolated_rng(9001):
                model = PPO.load(checkpoint, device=gpu['device'])
            parameters = list(model.policy.parameters())
            if not parameters or any(p.device.type != 'cuda' for p in parameters) or model.num_timesteps != protocol['checkpoint_steps']:
                raise RuntimeError('checkpoint budget/device mismatch')
            models[f'ppo_seed{seed}'] = model
            device_records.append(dict(seed=seed, checkpoint=str(checkpoint), sha256=sha(checkpoint),
                                       policy_device=str(parameters[0].device), parameter_tensors=len(parameters)))
        save(args.output / 'contract.json', dict(protocol=protocol, config=config, reference=reference,
             inputs=inputs, sources=before, gpu=gpu, policies=device_records,
             versions=dict(python=platform.python_version(), torch=torch.__version__, sb3=stable_baselines3.__version__, numpy=np.__version__)))
        xy = np.loadtxt(reference['geometry'], delimiter=',')[:, :2]
        curves, grids = {}, {}
        policies = [*protocol['fixed_policies'], *models]
        for scenario, cadence in planned_cases(protocol):
            case_rows = []
            blocks = cadence['blocks']
            ref = scenario_reference(reference, scenario)
            sigma = ref['smoothing_sigma_m']
            try:
                if sigma not in curves:
                    curves[sigma] = PeriodicCentreline(xy, sigma, ref['resample_spacing_m'])
                curve = curves[sigma]
                vehicle = PowerVehicle(**ref['vehicle'])
                for grid_name in ('coarse', 'fine'):
                    cells = cadence[f'{grid_name}_cells_per_block']
                    grid_key = (sigma, ref['lateral_acceleration_mps2'], ref['max_speed_mps'], blocks * cells)
                    if grid_key not in grids:
                        grids[grid_key] = control_grid(curve, blocks, cells, ref['lateral_acceleration_mps2'], ref['max_speed_mps'])
                    env = TerminalGuardEnv(grids[grid_key], vehicle, blocks, config['initial_speed_mps'], ref['initial_energy_j'], ref['reserve_j'],
                                           protected_energy_j=protocol['guard']['protected_energy_j'], terminal_blocks=blocks // 55)
                    # Save each physical grid once; both cadences share identical cell boundaries.
                    grid_path = args.output / f'{scenario["name"]}_{grid_name}_grid.json.gz'
                    if not grid_path.exists():
                        gzsave(grid_path, {key: value.tolist() for key, value in vars(env.grid).items()})
                    zero_times = None
                    for policy in policies:
                        label = f'{scenario["name"]}_blocks-{blocks}_{grid_name}_{policy}'
                        row = dict(scenario=scenario['name'], blocks=blocks, cells_per_block=cells,
                                   physical_cells=len(env.grid.lengths_m), grid=grid_name, policy=policy,
                                   grid_file=grid_path.name, circuit_length_m=float(env.grid.distance_m[-1]))
                        started = time.perf_counter()
                        try:
                            if zero_times is not None:
                                env.reference_times = zero_times
                            reference_time_s = float(sum(env.reference_times))
                            action = (lambda obs, m=models[policy]: m.predict(obs, deterministic=True)[0]) if policy in models else baseline_policy(policy, env)
                            with isolated_rng(9001):
                                record = rollout(env, action)
                            if policy == 'zero':
                                zero_times = np.array([t['duration_s'] for t in record['trace']])
                                # Reference only changes reward bookkeeping, never state/action integration.
                                reference_time_s = float(sum(zero_times))
                                record['integration_reward_sum_before_reference_assignment'] = record['reward_sum']
                                record['reward_sum'] = 0.
                            record['reward_reference_time_s'] = reference_time_s
                            filename = label + '.json.gz'
                            gzsave(args.output / filename, record)
                            audit = audit_rollout(record, ref, config, blocks, protocol['gates'])
                            guard_audit = audit_guard(record, env, protocol['gates'])
                            audit['guard'] = guard_audit
                            audit['passed'] = bool(audit['passed'] and guard_audit['passed'])
                            if abs(record['reward_sum'] - (reference_time_s - record['duration_s'])) > 1e-8:
                                audit['passed'] = False
                                audit['reward_identity_failed'] = True
                            interventions = [t['terminal_guard'] for t in record['trace']]
                            intervention_summary = dict(
                                terminal_override_blocks=sum(t['terminal_request_override'] for t in interventions),
                                action_changed_blocks=sum(t['action_changed'] for t in interventions),
                                protected_depletion_blocks=sum(t['protected_depletion_intervention'] for t in interventions),
                                depletion_events=sum(t['depletion_events'] for t in interventions))
                            row.update(status='completed', duration_s=record['duration_s'], final_energy_j=record['final_energy_j'],
                                       terminal_speed_error_mps=record['terminal_speed_error_mps'], feasible=record['feasible'],
                                       energy_residual_j=record['energy_residual_j'], audit=audit, guard_interventions=intervention_summary,
                                       file=filename, reward_reference_time_s=reference_time_s, wall_seconds=time.perf_counter() - started)
                        except Exception:
                            row.update(status='failed', error=traceback.format_exc(), wall_seconds=time.perf_counter() - started)
                            errors.append(dict(case=label, error=row['error']))
                        rows.append(row)
                        case_rows.append(row)
                        save(args.output / 'progress.json', dict(completed=len(rows), planned=64, results=rows, errors=errors))
            except Exception:
                errors.append(dict(case=f'{scenario["name"]}_blocks-{blocks}', error=traceback.format_exc()))
            pairs = numerical_pairs(case_rows, policies, protocol['gates'])
            fine = {r['policy']: r for r in case_rows if r.get('status') == 'completed' and r['grid'] == 'fine'}
            complete = all(p in fine for p in policies) and all(r['audit']['passed'] for r in fine.values())
            result = dict(scenario=scenario['name'], blocks=blocks, numerical_pairs=pairs,
                          passed=bool(complete and all(p['passed'] for p in pairs)))
            if complete:
                strongest = min(protocol['fixed_policies'], key=lambda p: fine[p]['duration_s'])
                gains = [fine[strongest]['duration_s'] - fine[p]['duration_s'] for p in models]
                result.update(strongest_fixed_policy=strongest, strongest_fixed_time_s=fine[strongest]['duration_s'],
                              ppo_fine_lap_time_s=describe([fine[p]['duration_s'] for p in models]),
                              ppo_advantage_over_strongest_fixed_s=describe(gains),
                              per_seed_advantage_s={p: g for p, g in zip(models, gains)})
            cases.append(result)
            print(json.dumps(dict(scenario=scenario['name'], blocks=blocks, passed=result['passed'], rollouts=len(case_rows))), flush=True)
        nominal = {(r['blocks'], r['policy']): r for r in rows if r.get('status') == 'completed' and r['scenario'] == 'nominal' and r['grid'] == 'fine'}
        changes = {p: nominal[110, p]['duration_s'] - nominal[55, p]['duration_s'] for p in policies if (110, p) in nominal and (55, p) in nominal}
        if any(sha(p) != digest for p, digest in {**inputs, **before}.items()):
            raise RuntimeError('input/source changed during transfer study')
        accepted = len(rows) == 64 and not errors and all(c['passed'] for c in cases)
        save(args.output / 'metrics.json', dict(all_cases_completed_and_passed=bool(accepted), planned_rollouts=64,
             completed_rollouts=sum(r.get('status') == 'completed' for r in rows), cases=cases, results=rows, errors=errors,
             nominal_fine_110_minus55_time_s=changes, interpretation=protocol['interpretation'],
             cuda_memory=dict(allocated_bytes=torch.cuda.memory_allocated(), peak_allocated_bytes=torch.cuda.max_memory_allocated())))
        if not accepted:
            save(args.output / 'failure.json', dict(reason='one or more predeclared cases failed; see metrics and partial traces', errors=errors))
        return accepted
    except Exception:
        save(args.output / 'failure.json', dict(error=traceback.format_exc(), completed_rollouts=len(rows)))
        raise
    finally:
        save(args.output / 'manifest.json', dict(inputs=inputs, sources=before,
             outputs={str(p): sha(p) for p in args.output.rglob('*') if p.is_file() and p.name != 'manifest.json'}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, default=Path('configs/terminal_guard_protocol.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not evaluate(args):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
