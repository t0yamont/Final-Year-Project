"""Replay signed Bahrain 20 kJ zone targets with terminal speed free."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import copy
import csv
from itertools import combinations
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.optimize import brentq

from bahrain_free_finish import build_free_env, free_rollout
from bahrain_pace_model import build_env
from benchmark_circuit_control import gzsave, save, sha
from run_bahrain_scarcity_zones import PACKET_J, PREFIX, individual_refinement, pair_row, work
from validate_regeneration import audit_replay
from verify_bahrain_deployment import close, read

PARENT = Path('results/bahrain-scarcity-zones-001')
PARENT_DIGEST = '8d072c7984a232d1000f97e42115fe27dc1eee0dca1607d7289e75f1c7f3f226'
BLOCK_TOLERANCE_J = .01
BLOCKS = 55
PROTOCOL = Path('configs/bahrain_free_finish.json')


def matching_policy(env, targets, warm, unchanged_blocks):
    """Reuse proven prefix requests, then invert on the actual live arrival state."""
    actions = warm['actions'].copy()
    stats = dict(probes=0, saturated=[])

    def policy(_):
        i = env.index
        target = targets[i]
        request = actions[i]
        if i < unchanged_blocks and abs(warm['wheel_by_block_j'][i] - target) <= BLOCK_TOLERANCE_J:
            return [request]
        if not target:
            actions[i] = 0.
            return [0.]

        def difference(action):
            stats['probes'] += 1
            _, _, _, _, block = copy(env).step([np.float32(action)])
            return block['electrical_work_j'] - target

        error = difference(request)
        if abs(error) > BLOCK_TOLERANCE_J:
            if (error if request == 1. else difference(1.)) < 0.:
                request = 1.
                stats['saturated'].append(i + 1)
            else:
                request = float(np.float32(brentq(difference, 0., 1., xtol=1e-7, maxiter=40)))
        actions[i] = request
        return [request]

    return policy, actions, stats


def replay_row(env, actions, output, model, targets, issued_grid, policy=None, fit=None):
    record = free_rollout(env, policy if policy is not None else lambda _: [actions[env.index]])
    fit = fit if fit is not None else dict(probes=0, saturated=[])
    trace = record['trace']
    delivered = work(record)
    finish = trace[-1]['state']['speed_m_per_s']
    if len(trace) != BLOCKS or actions != [block['action'] for block in trace]:
        raise ValueError('Incomplete trace or issued action mismatch')
    close(sum(block['duration_s'] for block in trace), record['duration_s'])
    close(trace[-1]['state']['distance_m'], float(env.grid.distance_m[-1]))
    close(trace[-1]['state']['energy_j'], record['final_energy_j'])
    close(finish - model['initial_speed_mps'], record['terminal_speed_error_mps'])
    for block in trace:
        if not 0. <= block['action'] <= 1.:
            raise ValueError('Request outside [0, 1]')
        if block['electrical_work_j'] > block['action'] * env.vehicle.electrical_limit_w * block['duration_s'] + 1e-5:
            raise ValueError('Independent deployment power check failed')
    audit = audit_replay(record, model, model, env.vehicle)
    residual = sum(block['energy_residual_j'] for block in trace)
    close(residual, record['energy_residual_j'])
    max_cap = max(block['max_node_cap_excess_mps'] for block in trace)
    peak_battery_residual = max(abs(block['battery_residual_j']) for block in trace)
    feasible = max_cap < 1e-5 and abs(residual) < 1. and peak_battery_residual < .01
    if feasible != record['feasible']:
        raise ValueError('Physical feasibility mismatch')
    gzsave(output, record)
    row = {key: value for key, value in record.items() if key not in ('trace', 'reward_sum')}
    row.update(audit, file=output.as_posix(), cells_per_block=env.cells_per_block, issued_cells_per_block=issued_grid,
               finish_speed_mps=finish, max_node_cap_excess_mps=max_cap,
               wheel_assist_j=float(delivered.sum()), wheel_by_block_j=delivered.tolist(),
               target_by_block_j=targets.tolist(), target_l1_error_j=float(np.abs(delivered - targets).sum()),
               actions=actions, block_probes=fit['probes'], saturated_blocks=fit['saturated'],
               min_energy_j=min(block['state']['energy_j'] for block in trace),
               last_three_wheel_by_block_j=delivered[PREFIX:].tolist(),
               last_three_wheel_work_j=float(delivered[PREFIX:].sum()))
    return row


def run_case(output, history, model, config, groups):
    start = perf_counter()
    scenario = history['scenario']
    coarse, fine = config['grids']
    envs = {cells: build_free_env(model, cells) for cells in (coarse, fine)}
    unchanged_blocks = {}
    for cells, env in envs.items():
        differences = np.flatnonzero(env.envelope[1:] != build_env(model, cells).envelope[1:])
        unchanged_blocks[cells] = int(differences[0] // cells) if len(differences) else BLOCKS
    replays = {}
    for zone, historical in history['replays'].items():
        target = np.asarray(historical[str(coarse)]['target_by_block_j'])
        records = {}
        for cells, env in envs.items():
            past = historical[str(cells)]
            # If a signed warm block missed by more than the skip tolerance, all later arrival states may differ.
            warm_error = np.flatnonzero(np.abs(np.asarray(past['wheel_by_block_j']) - target) > BLOCK_TOLERANCE_J)
            prefix = min(unchanged_blocks[cells], int(warm_error[0])) if len(warm_error) else unchanged_blocks[cells]
            policy, actions, fit = matching_policy(env, target, past, prefix)
            records[cells] = replay_row(env, actions, output / f'{scenario}_{zone}_{cells}.json.gz',
                                        model, target, cells, policy, fit)
            if not np.allclose(records[cells]['wheel_by_block_j'][:prefix], past['wheel_by_block_j'][:prefix],
                               rtol=0., atol=1e-7):
                raise ValueError('Free replay disagrees with signed unchanged prefix')
        records['frozen'] = replay_row(envs[fine], records[coarse]['actions'],
                                       output / f'{scenario}_{zone}_{fine}_frozen_{coarse}_actions.json.gz',
                                       model, target, coarse)
        records['refinement'] = individual_refinement(records[coarse], records[fine], config['refinement'])
        records['fixed_refinement'] = individual_refinement(records[coarse], records['frozen'], config['refinement'])
        replays[zone] = records
    base = replays['base']
    passed = (all(base[grid]['feasible'] for grid in (coarse, fine, 'frozen'))
              and base['refinement']['passed'] and base['fixed_refinement']['passed']
              and all(base[g]['target_l1_error_j'] <= config['total_work_pair_tolerance_j'] for g in (coarse, fine)))
    pairs = []
    fixed_pairs = {(row['donor'], row['recipient']): row for row in history['pairs']}
    for donor, recipient in combinations(groups, 2):
        row = pair_row(scenario, donor, recipient, groups, replays, config)
        fixed = fixed_pairs[donor, recipient]
        row.update({f'fixed_{key}': fixed[key] for key in ('status', 'direction', 'resolved', f'delta_time_{fine}_ms')})
        for grid, label in ((coarse, coarse), (fine, fine), ('frozen', f'frozen_{fine}')):
            a, b = replays[donor][grid], replays[recipient][grid]
            row[f'raw_delta_time_{label}_ms'] = 1000 * (b['duration_s'] - a['duration_s'])
        pairs.append(row)
    elapsed = perf_counter() - start
    print(f'{scenario}: {sum(row["resolved"] for row in pairs)}/{len(pairs)} resolved, '
          f'baseline passed={passed}, {elapsed:.1f} s', flush=True)
    return dict(scenario=scenario, passed=passed, unchanged_prefix_blocks=unchanged_blocks,
                replays=replays, pairs=pairs, wall_seconds=elapsed)


def checked_hashes(hashes):
    for path, digest in hashes.items():
        if sha(path) != digest:
            raise ValueError(f'Hash mismatch: {path}')


def check_history(history, scenario_names, groups, grids):
    if [case['scenario'] for case in history] != list(scenario_names):
        raise ValueError('Scenarios differ from the signed protocol')
    for case in history:
        records = case['replays']
        if set(records) != {'base', *groups}:
            raise ValueError('Incorrect zone coverage')
        base = np.asarray(records['base'][str(grids[0])]['target_by_block_j'])
        for zone, past in records.items():
            target = np.asarray(past[str(grids[0])]['target_by_block_j'])
            if target.shape != (BLOCKS,) or not np.isfinite(target).all() or np.any(target < 0):
                raise ValueError('Invalid signed target work vector')
            for cells in grids:
                signed = past[str(cells)]
                trace = read(signed['file'])['trace']
                if (target.tolist() != signed['target_by_block_j'] or len(trace) != BLOCKS
                        or signed['actions'] != [block['action'] for block in trace]
                        or signed['wheel_by_block_j'] != [block['electrical_work_j'] for block in trace]):
                    raise ValueError('Signed replay disagrees with its action, work or target record')
            if zone != 'base':
                packet = target - base
                expected = np.zeros(BLOCKS)
                expected[groups[zone]] = packet[groups[zone]]
                if np.any(packet < 0) or not np.array_equal(packet, expected):
                    raise ValueError('Signed packet spills beyond its zone')
                close(float(packet.sum()), PACKET_J)


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, choices=(1, 2, 3, 4), default=4)
    args = parser.parse_args()
    manifest_path = PARENT / 'manifest.json'
    anchor = {manifest_path.as_posix(): PARENT_DIGEST}
    checked_hashes(anchor)
    parent = read(manifest_path)
    input_hashes = anchor | parent['inputs'] | parent['outputs'] | {PROTOCOL.as_posix(): sha(PROTOCOL)}
    checked_hashes(input_hashes | parent['sources'])
    source_hashes = parent['sources'].copy()
    for path in (Path(__file__), Path(__file__).with_name('bahrain_free_finish.py')):
        relative = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        source_hashes[relative] = sha(path)
    config = read(PARENT / 'contract.json')['shared_protocol']
    protocol = read(PROTOCOL)
    if (protocol['evaluation_cells_per_block'] != config['grids']
            or protocol['scenarios'] != list(config['scenarios'])
            or input_hashes[protocol['parent_protocol']] != protocol['parent_protocol_sha256']):
        raise ValueError('Free-finish protocol disagrees with the signed parent')
    zones = read(PARENT / 'zones.json')
    groups = {zone['id']: slice(zone['first_block'] - 1, zone['last_block']) for zone in zones}
    history = read(PARENT / 'metrics.json')
    check_history(history, config['scenarios'], groups, config['grids'])
    model = read(config['model'])
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'zones.json').write_bytes((PARENT / 'zones.json').read_bytes())
    save(args.output / 'contract.json', dict(
        protocol=protocol, shared_protocol=config, inputs=input_hashes, sources=source_hashes, blocks=BLOCKS, packet_j=PACKET_J,
        workers=args.workers, warm_request_tolerance_j=BLOCK_TOLERANCE_J,
        finish_rule='Free crossing speed with the physical endpoint cap and no prescribed-speed backward dependency.',
        design='Replay the signed base and seven signed zone targets in each case without reallocating target work.',
        solver=('Fit free-finish request sequentially on each grid at the physical arrival state. Reuse the signed '
                'same-grid warm request when its work is within 0.01 J. Reuse the unchanged envelope prefix '
                'and verify its delivered work against the signed trace. Otherwise use the historical Brent root '
                'precision and float32 requests. Retain saturated blocks. Replay the new 160 requests unchanged '
                'at 320 cells. Independently check work, battery flow and power on every complete lap.'),
        scoring=('Use the historical pair gate and sign floor. Report all raw gaps and fixed-finish outcomes. '
                 'A base gate failure is retained separately from the measured pair gates. Preserve both '
                 'matched-grid target isolation and unchanged-action refinement.')))
    jobs = []
    for case in history:
        settings = config['scenarios'][case['scenario']]
        run_model = dict(model, initial_energy_j=settings['initial_energy_j'],
                         regeneration=dict(model['regeneration'], braking_fraction=settings['braking_fraction']))
        jobs.append((args.output, case, run_model, config, groups))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        pending = [pool.submit(run_case, *job) for job in jobs]
        metrics = [job.result() for job in pending]
    pairs = [row for case in metrics for row in case['pairs']]
    assert len(pairs) == len({(r['scenario'], r['donor'], r['recipient']) for r in pairs}) == 84
    write_csv(args.output / 'pairs.csv', pairs)
    columns = ('cells_per_block', 'issued_cells_per_block', 'feasible', 'duration_s', 'finish_speed_mps',
               'wheel_assist_j', 'target_l1_error_j', 'last_three_wheel_work_j', 'final_energy_j', 'recovered_j')
    rows = []
    for case in metrics:
        for zone, replay in case['replays'].items():
            for grid in (*config['grids'], 'frozen'):
                values = replay[grid]
                row = dict(scenario=case['scenario'], finish_condition='free', zone=zone, replay=grid)
                row.update({key: values[key] for key in columns})
                for block, value in enumerate(values['last_three_wheel_by_block_j'], PREFIX + 1):
                    row[f'block_{block}_wheel_work_j'] = value
                rows.append(row)
    write_csv(args.output / 'replays.csv', rows)
    save(args.output / 'metrics.json', metrics)
    checked_hashes(input_hashes | source_hashes)
    save(args.output / 'manifest.json', dict(inputs=input_hashes, sources=source_hashes,
         outputs={p.as_posix(): sha(p) for p in sorted(args.output.iterdir())}))


if __name__ == '__main__':
    main()

