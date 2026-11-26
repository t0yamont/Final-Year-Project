"""Compare bounded Bahrain planners with fixed and free finish speed."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from math import isclose
from pathlib import Path

from bahrain_free_finish import build_free_env, free_rollout, search_free
from benchmark_circuit_control import gzsave, save, sha, sources
from compare_bahrain_equal_work import MATCH_J, MAX_BISECTIONS, SAMPLES
from f1energy.circuit_control import baseline_policy
from map_bahrain_deployment import assess_grid, write_profiles
from run_bahrain_scarcity_planners import (
    GRIDS, MODEL, SETTINGS, SUFFIX, actions, find_scales, pair, preferred, signed_dependencies,
)
from validate_regeneration import audit_replay
from verify_bahrain_deployment import close, read, verify_rollout


PARENT = Path('results/bahrain-scarcity-planners-001')
FROZEN = Path('results/bahrain-deployment-zones-001/central/search.json')
SCARCITY = Path('configs/bahrain_energy_scarcity.json')
FREE_PROTOCOL = Path('configs/bahrain_free_finish.json')
OUTPUT = Path('results/bahrain-free-planner-001')


def schedule_policy(env, schedule):
    return lambda _: [schedule[env.index]]


def summarize(trace, model, env, path=None, *, fixed_finish=False):
    blocks = trace['trace']
    if len(blocks) != env.blocks:
        raise ValueError('Incomplete Bahrain lap')
    total_distance = float(env.grid.distance_m[-1])
    close(blocks[-1]['state']['distance_m'], total_distance)
    close(sum(block['duration_s'] for block in blocks), trace['duration_s'])
    close(blocks[-1]['state']['energy_j'], trace['final_energy_j'])
    limit = model['vehicle']['electrical_limit_w']
    if any(not 0 <= block['action'] <= 1
           or block['electrical_work_j'] > block['action'] * limit * block['duration_s'] + 1e-5 for block in blocks):
        raise ValueError('Invalid request or wheel work above requested power')
    audit = audit_replay(trace, model, model, env.vehicle)
    recovered = audit['recovered_j']
    usable = model['initial_energy_j'] - model['reserve_j']
    efficiency = model['vehicle']['discharge_efficiency']
    regen = model['regeneration']
    block_work = [block['electrical_work_j'] for block in blocks]
    close(sum(block_work), audit['discharged_j'] * efficiency)
    row = {key: value for key, value in trace.items() if key not in ('trace', 'reward_sum')}
    row.update(audit, block_work_j=block_work, wheel_assist_j=sum(block_work),
               actual_finish_speed_mps=blocks[-1]['state']['speed_m_per_s'],
               final_three_blocks_work_j=sum(block_work[-SUFFIX:]),
               max_node_cap_excess_mps=max(block['max_node_cap_excess_mps'] for block in blocks),
               max_cell_residual_j=max(block['max_cell_residual_j'] for block in blocks),
               max_block_battery_residual_j=max(abs(block['battery_residual_j']) for block in blocks),
               allocated_battery_budget_upper_bound_j=min(regen['deployment_limit_j'], usable + regen['recovery_limit_j']),
               realised_battery_budget_upper_bound_j=min(regen['deployment_limit_j'], usable + recovered))
    if fixed_finish:
        feasible_finish = abs(row['actual_finish_speed_mps'] - model['initial_speed_mps']) < 1e-5
    else:
        feasible_finish = row['actual_finish_speed_mps'] <= env.grid.cell_speed_cap_mps[-1] + 1e-5
    feasible = (feasible_finish and row['max_node_cap_excess_mps'] < 1e-5
                and abs(sum(block['energy_residual_j'] for block in blocks)) < 1
                and row['max_block_battery_residual_j'] < .01)
    if feasible != row['feasible']:
        raise ValueError('Physical feasibility mismatch')
    if path is not None:
        row['file'] = path.as_posix()
    return row


def matched_spread(envs, model, folder, raw, traces, limits):
    trials = {cells: {} for cells in GRIDS}
    for cells in GRIDS:
        trials[cells][1.] = raw[str(cells)]['ordinary_spread']

    def replay(cells, alpha):
        env = envs[cells]
        policy = baseline_policy('spread', env)
        return free_rollout(env, lambda obs: [min(1., alpha * policy(obs)[0])])

    def trial(cells, alpha):
        rows = trials[cells]
        if alpha not in rows:
            rows[alpha] = summarize(replay(cells, alpha), model, envs[cells])
        return rows[alpha]

    reference = {grid: rows['free_winner'] for grid, rows in raw.items()}
    scales, brackets = find_scales(trial, SAMPLES, reference['160']['wheel_assist_j'])
    candidates = [pair(reference, {str(c): trial(c, alpha) for c in GRIDS}, alpha, limits) for alpha in scales]
    chosen = preferred(candidates)
    for cells in GRIDS:
        grid = str(cells)
        record = replay(cells, chosen['alpha'])
        path = folder / f'matched_spread_{cells}.json.gz'
        gzsave(path, record)
        row = summarize(record, model, envs[cells], path)
        if not isclose(row['wheel_assist_j'], chosen['grids'][grid]['spread']['wheel_assist_j'], rel_tol=0, abs_tol=1e-7):
            raise ValueError('Matched spread did not reproduce the chosen trial')
        raw[grid]['matched_spread'], traces[grid]['matched_spread'] = row, record
        chosen['grids'][grid]['spread'] = row
    return dict(preferred=chosen, candidates=candidates, brackets=brackets, trials=trials)


def run_case(name, model, protocol, folder, frozen, fixed):
    folder.mkdir()
    search_env = build_free_env(model, protocol['search_cells_per_block'])
    probes = {label: baseline_policy(label, search_env) for label in ('zero', 'full', 'spread')}
    probes.update(fixed_actions_free=schedule_policy(search_env, fixed),
                  frozen_nominal=schedule_policy(search_env, frozen),
                  finish_only=schedule_policy(search_env, [0.] * (search_env.blocks - SUFFIX) + [1.] * SUFFIX))
    probe_rows, candidates = {}, []
    for label, policy in probes.items():
        record = free_rollout(search_env, policy)
        path = folder / f'probe_{label}_40.json.gz'
        gzsave(path, record)
        probe_rows[label] = summarize(record, model, search_env, path)
        if record['feasible']:
            candidates.append((record['duration_s'], label, actions(record)))
    _, incumbent_label, incumbent = min(candidates)
    result = search_free(search_env, dict(protocol['search'], name=name), incumbent)
    result.update(incumbent_name=incumbent_label, probes=probe_rows)
    save(folder / 'search.json', result)
    print(f'{name}: search complete ({result["transitions"]} transitions)', flush=True)

    envs = {cells: build_free_env(model, cells) for cells in GRIDS}
    raw, traces = {}, {}
    for cells, env in envs.items():
        grid = str(cells)
        raw[grid], traces[grid] = {}, {}
        policies = dict(free_winner=schedule_policy(env, result['actions']),
                        fixed_actions_free=schedule_policy(env, fixed),
                        ordinary_spread=baseline_policy('spread', env))
        for label, policy in policies.items():
            record = free_rollout(env, policy)
            path = folder / f'{label}_{cells}.json.gz'
            gzsave(path, record)
            raw[grid][label], traces[grid][label] = summarize(record, model, env, path), record
        path = PARENT / name / f'adapted_{cells}.json.gz'
        record = read(path)
        if actions(record) != fixed or not record['feasible']:
            raise ValueError('Archived fixed schedule mismatch or infeasible finish')
        row = summarize(record, model, env, path, fixed_finish=True)
        verify_rollout(row, model)
        raw[grid]['fixed_winner_archive'], traces[grid]['fixed_winner_archive'] = row, record
    limits = protocol['refinement']
    match = matched_spread(envs, model, folder, raw, traces, limits)
    comparison_labels = [label for label in raw['160'] if label != 'free_winner']
    raw_grid = assess_grid({grid: dict(selected=rows['free_winner'],
                                      **{label: rows[label] for label in comparison_labels})
                            for grid, rows in raw.items()}, comparison_labels, limits)
    raw_grid['individual']['free_winner'] = raw_grid['individual'].pop('selected')
    for grid, rows in raw.items():
        for label in comparison_labels:
            comparison = raw_grid['paired'][label]
            comparison[f'wheel_assist_delta_{grid}_j'] = rows[label]['wheel_assist_j'] - rows['free_winner']['wheel_assist_j']
            comparison[f'work_matched_{grid}'] = abs(comparison[f'wheel_assist_delta_{grid}_j']) <= MATCH_J
            comparison[f'finish_speed_delta_{grid}_mps'] = rows[label]['actual_finish_speed_mps'] - rows['free_winner']['actual_finish_speed_mps']
        write_profiles(folder / f'profile_{grid}.csv', envs[int(grid)], traces[grid])
    print(f'{name}: evaluation complete', flush=True)
    result = dict(scenario=name, model=model, raw=raw, raw_grid=raw_grid, matched_spread=match,
                  search=(folder / 'search.json').as_posix())
    save(folder / 'metrics.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=4)
    args = parser.parse_args()
    model, study, protocol, free = read(MODEL), read(SCARCITY), read(SETTINGS), read(FREE_PROTOCOL)
    if (free['parent_protocol'] != SCARCITY.as_posix() or free['parent_protocol_sha256'] != sha(SCARCITY)
            or free['scenarios'] != list(study['scenarios']) or free['evaluation_cells_per_block'] != list(GRIDS)
            or free['planner_search']['cells_per_block'] != protocol['search_cells_per_block']
            or free['planner_search']['width'] != protocol['search']['width'] or tuple(study['grids']) != GRIDS
            or study['refinement'] != protocol['refinement'] or study['total_work_pair_tolerance_j'] != MATCH_J):
        raise ValueError('Scarcity and free-finish settings disagree on the scenarios, search or replay gates')
    frozen = read(FROZEN)['actions']
    models = {name: dict(model, initial_energy_j=case['initial_energy_j'], regeneration=dict(
        model['regeneration'], braking_fraction=case['braking_fraction'])) for name, case in study['scenarios'].items()}
    if models['nominal'] != model:
        raise ValueError('Nominal study parameters differ from the frozen calibrated model')
    archived_paths = {name: PARENT / name / 'search.json' for name in models}
    archives = [path for name, search_path in archived_paths.items()
                for path in (search_path, *(PARENT / name / f'adapted_{cells}.json.gz' for cells in GRIDS))]
    stable_sources = {Path(path).as_posix(): digest for path, digest in sources().items()}
    for name in ('bahrain_pace_model', 'benchmark_circuit_control', 'compare_bahrain_equal_work',
                 'map_bahrain_deployment', 'run_bahrain_scarcity_planners', 'validate_regeneration',
                 'verify_bahrain_deployment'):
        path = Path(f'scripts/{name}.py')
        stable_sources[path.as_posix()] = sha(path)
    parent_manifest = PARENT / 'manifest.json'
    dependencies = [MODEL, SCARCITY, SETTINGS, FROZEN, Path(model['geometry']), *archives]
    signed_dependencies(parent_manifest, [*dependencies, *map(Path, stable_sources), Path('scripts/optimize_regeneration_dp.py')])
    fixed = {name: read(path)['actions'] for name, path in archived_paths.items()}
    if frozen != fixed['nominal'] or any(len(schedule) != 55 or not all(0 <= a <= 1 for a in schedule)
                                         for schedule in fixed.values()):
        raise ValueError('Invalid archived search schedule')
    inputs = {path.as_posix(): sha(path) for path in (FREE_PROTOCOL, parent_manifest, *dependencies)}
    code = {**stable_sources, **{path: sha(path) for path in
        ('scripts/bahrain_free_finish.py', 'scripts/optimize_regeneration_dp.py', 'scripts/run_bahrain_free_planner.py')}}
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / 'contract.json', dict(
        models=models, inputs=inputs, sources=code, fixed_actions=fixed, frozen_actions=frozen,
        search_grid=protocol['search_cells_per_block'], search=protocol['search'],
        search_incumbents=['zero', 'full', 'spread', 'fixed_actions_free', 'frozen_nominal', 'finish_only'],
        finish_only_blocks=SUFFIX, grids=GRIDS, refinement=protocol['refinement'], workers=args.workers,
        work_tolerance_j=MATCH_J, spread_multiplier_scan=SAMPLES, max_bisections=MAX_BISECTIONS,
        design=[
            'All comparisons retain calibrated initial speed, physical braking and energy limits. Free finish uses only the physical terminal speed cap.',
            'Choose the fastest feasible exact 40-cell probe by (duration, label) as incumbent. Search the archived finite action grid and width. Lock the winner before 160/320 evaluation.',
            'Replay the winner, fixed planner actions and unchanged spread in the free plant. Read the signed fixed-plant winner as the historical reference.',
            'Fit spread work on the 160-cell grid using all predeclared scan intervals and replay the same multiplier on 320. Prefer a passing pair, then feasible count, aggregate work mismatch and lower multiplier. Preserve failed matches.',
            'Reuse the scarcity work and grid gates. Evaluate physical feasibility first. Positive time differences favor the free winner. Attribute timing only to stable comparisons at matched realised work.',
            'Distinguish allocated and realised path-specific battery budget ceilings from delivered wheel work. Last three blocks use the same one-based blocks 53â€“55 in every replay.'
        ]))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        jobs = {name: pool.submit(run_case, name, m, protocol, args.output / name, frozen, fixed[name])
                for name, m in models.items()}
        cases = {name: job.result() for name, job in jobs.items()}
    if any(sha(path) != digest for path, digest in (inputs | code).items()):
        raise RuntimeError('An input or source changed during execution')
    save(args.output / 'metrics.json', dict(cases=cases))
    save(args.output / 'manifest.json', dict(inputs=inputs, sources=code,
         outputs={path.as_posix(): sha(path) for path in sorted(args.output.rglob('*')) if path.is_file()}))


if __name__ == '__main__':
    main()

