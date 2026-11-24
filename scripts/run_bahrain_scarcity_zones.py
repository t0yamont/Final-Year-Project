"""Move a fixed packet of delivered wheel work between Bahrain deployment zones."""

import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import copy
import csv
from itertools import combinations
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.optimize import brentq

from bahrain_pace_model import build_env
from benchmark_circuit_control import gzsave, save, sha, sources
from f1energy.circuit_control import rollout
from validate_regeneration import audit_replay
from verify_bahrain_deployment import read, verify_rollout


CONFIG = Path('configs/bahrain_energy_scarcity.json')
PARENT = Path('results/bahrain-deployment-zones-001')
HISTORIC_SELECTED = PARENT / 'central/selected_160.json.gz'
HISTORIC_FINISH = PARENT / 'central/finish_only_160.json.gz'
ZONE_SUPPORT = Path('results/bahrain-zone-support-001/metrics.json')
ZONE_IDS = ('timing_line', 't1_t3', 't8_exit', 't10_exit', 't11_exit', 't13_exit', 't15')
PREFIX = 52
PACKET_J = 20_000
SUFFIX_SCALE = .90
BUDGET_SCALE = .85
PREFIX_SCALE_LIMIT = .75
DIRECTION_FLOOR_S = .0005


def work(replay):
    return np.array([block['electrical_work_j'] for block in replay['trace']])


def physical_replay(env, actions):
    return rollout(env, lambda _: [actions[env.index]])


def fit_actions(env, targets):
    """Use the current block's exact dynamics to invert delivered work on [0, 1]."""
    env.reset(seed=0)
    actions = []
    probes = 0
    saturated = []

    def difference(fraction):
        nonlocal probes
        probes += 1
        # The plant replaces its state and counters. Geometry is read-only and shared.
        _, _, _, _, block = copy(env).step([np.float32(fraction)])
        return block['electrical_work_j'] - target

    for index, target in enumerate(targets, 1):
        fraction = 0.
        if target > 0:
            if difference(1.) < 0:
                fraction = 1.
                saturated.append(index)
            else:
                fraction = brentq(difference, 0., 1., xtol=1e-7, maxiter=40)
        issued = float(np.float32(fraction))
        env.step([issued])
        actions.append(issued)
    return actions, probes, saturated


def replay_row(env, actions, path, model, targets, probes=0, saturated=()):
    record = physical_replay(env, actions)
    delivered = work(record)
    gzsave(path, record)
    row = {key: value for key, value in record.items() if key not in ('trace', 'reward_sum')}
    row.update(audit_replay(record, model, model, env.vehicle), file=path.as_posix(),
               wheel_assist_j=float(delivered.sum()), wheel_by_block_j=delivered.tolist(),
               target_l1_error_j=float(np.abs(delivered - targets).sum()), target_by_block_j=targets.tolist(),
               actions=actions, block_probes=probes, saturated_blocks=list(saturated),
               min_energy_j=min(block['state']['energy_j'] for block in record['trace']))
    verify_rollout(row, model)
    return row


def individual_refinement(primary, fine, limits):
    change = dict(relative_lap_change=abs(primary['duration_s'] - fine['duration_s']) / fine['duration_s'],
                  terminal_energy_change_j=abs(primary['final_energy_j'] - fine['final_energy_j']),
                  recovered_change_j=abs(primary['recovered_j'] - fine['recovered_j']))
    return dict(change, passed=all(value <= limits[key] for key, value in change.items()))


def pair_grid(donor, recipient, donor_blocks, recipient_blocks, tolerance):
    diff = np.asarray(recipient['wheel_by_block_j']) - donor['wheel_by_block_j']
    outside = np.ones(len(diff), dtype=bool)
    outside[donor_blocks] = False
    outside[recipient_blocks] = False
    total = float(diff.sum())
    loss = float(-diff[donor_blocks].sum())
    gain = float(diff[recipient_blocks].sum())
    off_zone = float(np.abs(diff[outside]).sum())
    matched = max(abs(total), abs(loss - PACKET_J), abs(gain - PACKET_J), off_zone,
                  donor['target_l1_error_j'], recipient['target_l1_error_j']) <= tolerance
    return dict(raw_delta_s=recipient['duration_s'] - donor['duration_s'],
                feasible=donor['feasible'] and recipient['feasible'], matched=matched,
                total_work_gap_j=total, donor_loss_j=loss, recipient_gain_j=gain, off_zone_l1_j=off_zone)


def pair_row(scenario, a, b, groups, replays, config):
    coarse, fine = config['grids']
    rules = config['refinement']
    tolerance = config['total_work_pair_tolerance_j']
    row = dict(scenario=scenario, donor=a, recipient=b, packet_kj=PACKET_J / 1000)

    def grid(left, right, label):
        pair = pair_grid(left, right, groups[a], groups[b], tolerance)
        for key in ['feasible', 'matched', 'total_work_gap_j', 'donor_loss_j', 'recipient_gain_j', 'off_zone_l1_j']:
            unit = '_j' if key.endswith('_j') else ''
            stem = key.removesuffix(unit) if unit else key
            row[f'{stem}_{label}{unit}'] = pair[key]
        row[f'delta_time_{label}_ms'] = (pair['raw_delta_s'] * 1000 if pair['feasible'] and pair['matched']
                                          else None)
        return pair

    primary = grid(replays[a][coarse], replays[b][coarse], coarse)
    refined = grid(replays[a][fine], replays[b][fine], fine)
    fixed = grid(replays[a]['frozen'], replays[b]['frozen'], 'frozen_320')
    gap = abs(primary['raw_delta_s'] - refined['raw_delta_s'])
    fixed_gap = abs(primary['raw_delta_s'] - fixed['raw_delta_s'])
    row['refinement_delta_ms'] = 1000 * gap
    row['fixed_action_refinement_delta_ms'] = 1000 * fixed_gap
    row['refinement_passed'] = (gap <= rules['paired_gap_change_s'] and fixed_gap <= rules['paired_gap_change_s']
                                and fixed['feasible']
                                and all(replays[z]['refinement']['passed'] and replays[z]['fixed_refinement']['passed']
                                        for z in (a, b)))
    row['resolved'] = False
    row['direction'] = None
    if not (primary['feasible'] and refined['feasible']):
        row['status'] = 'feasibility_failed'
    elif not (primary['matched'] and refined['matched']):
        row['status'] = 'match_failed'
    elif not row['refinement_passed']:
        row['status'] = 'refinement_failed'
    else:
        deltas = [primary['raw_delta_s'], refined['raw_delta_s'], fixed['raw_delta_s']]
        resolved = ((min(deltas) > 0 or max(deltas) < 0)
                    and min(abs(value) for value in deltas) > max(DIRECTION_FLOOR_S, gap, fixed_gap))
        row.update(resolved=resolved, status='resolved' if resolved else 'unresolved',
                   direction=('donor_faster' if deltas[1] > 0 else 'recipient_faster') if resolved else None)
    return row


def run_scenario(output, scenario, run_model, config, zones, historical_prefix, suffix, preflight=None):
    started = perf_counter()
    coarse, fine = config['grids']
    primary = build_env(run_model, coarse)
    refined = build_env(run_model, fine)
    groups = {zone['id']: slice(zone['first_block'] - 1, zone['last_block']) for zone in zones}

    def replay_grids(zone, target):
        records = {}
        for cells, env in ((coarse, primary), (fine, refined)):
            actions, probes, saturated = fit_actions(env, target)
            records[cells] = replay_row(env, actions, output / f'{scenario}_{zone}_{cells}.json.gz',
                                        run_model, target, probes, saturated)
        records['frozen'] = replay_row(refined, records[coarse]['actions'],
                                       output / f'{scenario}_{zone}_320_frozen_160_actions.json.gz', run_model, target)
        records['refinement'] = individual_refinement(records[coarse], records[fine], config['refinement'])
        records['fixed_refinement'] = individual_refinement(records[coarse], records['frozen'], config['refinement'])
        return records

    if preflight is None:
        benchmark = physical_replay(primary, [0.] * PREFIX + [1.] * 3)
        before_suffix_charge = sum(block['battery_recovered_j'] for block in benchmark['trace'][:PREFIX])
        params = run_model['regeneration']
        available_j = primary.vehicle.discharge_efficiency * min(
            params['deployment_limit_j'], primary.initial_energy - primary.reserve + before_suffix_charge)
        prefix_budget_j = max(0., available_j - float(suffix.sum()))
        scale = max(0., min(PREFIX_SCALE_LIMIT, (BUDGET_SCALE * prefix_budget_j - PACKET_J) / historical_prefix.sum()))
        base = np.r_[scale * historical_prefix, suffix]
        records = replay_grids('base', base)
        passed = (benchmark['feasible'] and all(records[g]['feasible'] for g in (coarse, fine, 'frozen'))
                  and records['refinement']['passed'] and records['fixed_refinement']['passed']
                  and all(records[g]['target_l1_error_j'] <= config['total_work_pair_tolerance_j']
                          for g in (coarse, fine)))
        elapsed = perf_counter() - started
        print(f'{scenario}: base preflight {"passed" if passed else "failed"} in {elapsed:.1f} s', flush=True)
        return dict(scenario=scenario, scale=float(scale), budget_j=available_j, prefix_budget_j=prefix_budget_j,
                    zero_prefix_recovered_j=before_suffix_charge, zero_prefix_full_suffix_feasible=benchmark['feasible'],
                    base_target_work_j=float(base.sum()), pulse_target_work_j=float(base.sum()) + PACKET_J,
                    passed=passed, wall_seconds=elapsed, replays={'base': records})

    base = np.r_[preflight['scale'] * historical_prefix, suffix]
    replays = preflight['replays'].copy()
    for zone, zone_blocks in groups.items():
        target = base.copy()
        weights = historical_prefix[zone_blocks]
        target[zone_blocks] += PACKET_J * weights / weights.sum()
        replays[zone] = replay_grids(zone, target)
    pairs = [pair_row(scenario, donor, recipient, groups, replays, config)
             for donor, recipient in combinations(groups, 2)]
    elapsed = perf_counter() - started
    print(f'{scenario}: {sum(row["resolved"] for row in pairs)} of {len(pairs)} resolved in {elapsed:.1f} s', flush=True)
    return dict(preflight, scoring_wall_seconds=elapsed, replays=replays, pairs=pairs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--workers', type=int, choices=(1, 2, 3, 4), default=2)
    args = parser.parse_args()
    config = read(CONFIG)
    model_path = Path(config['model'])
    model = read(model_path)
    prior = read(PARENT / 'manifest.json')
    previous_inputs = {Path(path): digest for group in prior.values() for path, digest in group.items()}
    code_files = [Path(path) for path in sources()]
    code_files.extend(Path('scripts') / f'{script}.py' for script in ('bahrain_pace_model', 'benchmark_circuit_control',
                       'validate_regeneration', 'verify_bahrain_deployment', 'run_bahrain_scarcity_zones'))
    source_hashes = {path.as_posix(): sha(path) for path in code_files}
    for path in [model_path, Path(model['geometry']), HISTORIC_SELECTED, HISTORIC_FINISH, *code_files[:-1]]:
        if sha(path) != previous_inputs[path]:
            raise ValueError(f'Archive input or plant code changed: {path}')
    for path, digest in config['parent_hashes'].items():
        if sha(path) != digest:
            raise ValueError(f'Parent hash mismatch: {path}')
    input_hashes = {path.as_posix(): sha(path) for path in [CONFIG, model_path, Path(model['geometry']),
                                                              HISTORIC_SELECTED, HISTORIC_FINISH, ZONE_SUPPORT]}
    input_hashes.update(config['parent_hashes'])
    selected = read(HISTORIC_SELECTED)
    finish = read(HISTORIC_FINISH)
    historical_prefix = work(selected)[:PREFIX]
    suffix = work(finish)[PREFIX:] * SUFFIX_SCALE
    if (config['grids'] != [160, 320] or config['finish_speed_tolerance_mps'] != 1e-5
            or not selected['feasible'] or not finish['feasible'] or len(historical_prefix) != PREFIX
            or len(suffix) != 3 or len(work(selected)) != PREFIX + 3):
        raise ValueError('Historic replay does not match the declared lap structure and numerical gate')
    coverage = read(ZONE_SUPPORT)['zones']
    zones = []
    for zone_id, zone, support in zip(ZONE_IDS, config['zones'], coverage, strict=True):
        if [zone['first_block'], zone['last_block']] != support['blocks']:
            raise ValueError(f'Zone has changed since the published evidence: {zone}')
        zones.append(dict(zone, id=zone_id, from_m=support['from_m'], to_m=support['to_m']))
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / 'contract.json', dict(
        shared_protocol=config, packet_j=PACKET_J, prefix_blocks=PREFIX, suffix_scale=SUFFIX_SCALE,
        budget_scale=BUDGET_SCALE, prefix_scale_limit=PREFIX_SCALE_LIMIT, direction_floor_s=DIRECTION_FLOOR_S,
        inputs=input_hashes, sources=source_hashes, workers=args.workers, zone_ids=list(ZONE_IDS),
        prefix_targets_reference_j=historical_prefix.tolist(), suffix_targets_j=suffix.tolist(),
        design=("Scale the frozen nominal selected wheel-work target for blocks 1–52. Use the same per-block "
                "suffix target in every lap, at 90% of nominal finish-only delivered work in blocks 53–55. "
                "Run a 160-cell feasibility preflight with zero prefix and full suffix in each scenario. "
                "Budget = discharge efficiency × min(discharge limit, starting charge above reserve + preflight "
                "recovery through block 52). Subtract prescribed suffix work and floor the remainder at zero. "
                "Prefix scale is (85% of this remaining budget minus 20 kJ) / historic prefix work, clamped to "
                "[0, 0.75]. Add the 20 kJ to each one of seven zones in turn, allocated by their nominal "
                "selected per-block work weights. Compare plus-zone variants to each other, all 21 contrasts per scenario. "
                "Before scoring any contrasts, all four zero-packet bases must pass physical feasibility and individual "
                "grid refinement, plus 0.5 kJ L1 target matching on both independently matched grids."),
        solver=("Invert the same ordinary action transition blockwise at the current state via Brent's method "
                "(fraction absolute tolerance 1e-7, maximum 40 iterations) with float32 requests. Use zero "
                "request for zero target. If full request cannot deliver the target, retain the saturated block "
                "and score the actual physics; no alternative search or post-hoc retuning. Rerun each 55-action "
                "schedule through an unmodified rollout and audit mechanical and battery balances."),
        isolation=("Require jointly feasible finishes and max 0.5 kJ each for absolute total work gap, absolute "
                   "donor loss and recipient gain deviations from 20 kJ, summed absolute delivered-work differences "
                   "outside both zones, and summed absolute target error of each entire lap. Repeat across both "
                   "grids with the identical target work, solving its action fractions independently on each grid."),
        refinement=("Also replay the frozen 160-cell fractions at 320 cells. Require legacy absolute paired "
                    "gap and individual time, final battery and recovered charge grid tolerances across both forms "
                    "of fine-grid replay. Report fixed-action work isolation separately. Resolve a sign only if "
                    "both work-isolated gaps agree with the frozen-action direction and all three absolute gaps "
                    "exceed the largest paired grid discrepancy or the 0.5 ms floor, whichever is greater."),
        delta_sign='Recipient-packet lap minus donor-packet lap. Positive means moving the packet slows the lap.'))
    save(args.output / 'zones.json', zones)
    jobs = []
    for name, settings in config['scenarios'].items():
        run_model = dict(model, initial_energy_j=settings['initial_energy_j'],
                         regeneration=dict(model['regeneration'], braking_fraction=settings['braking_fraction']))
        jobs.append((args.output, name, run_model, config, zones, historical_prefix, suffix))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        pending = [pool.submit(run_scenario, *job) for job in jobs]
        preflight = [job.result() for job in pending]
        save(args.output / 'preflight.json', preflight)
        if all(row['passed'] for row in preflight):
            pending = [pool.submit(run_scenario, *job, base) for job, base in zip(jobs, preflight, strict=True)]
            results = [job.result() for job in pending]
            pairs = [row for result in results for row in result['pairs']]
            assert len(pairs) == len(jobs) * 21
            assert len({(r['scenario'], r['donor'], r['recipient']) for r in pairs}) == len(pairs)
            with (args.output / 'pairs.csv').open('w', newline='', encoding='utf-8') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(pairs[0]))
                writer.writeheader()
                writer.writerows(pairs)
            save(args.output / 'metrics.json', results)
    for path, digest in (input_hashes | source_hashes).items():
        if sha(path) != digest:
            raise ValueError(f'Bound file changed during the study: {path}')
    save(args.output / 'manifest.json', dict(inputs=input_hashes, sources=source_hashes,
         outputs={path.as_posix(): sha(path) for path in sorted(args.output.iterdir())}))
    if not all(row['passed'] for row in preflight):
        raise SystemExit('At least one baseline preflight failed. Zone contrasts were not scored.')


if __name__ == '__main__':
    main()
