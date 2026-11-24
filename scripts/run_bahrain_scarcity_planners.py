"""Replay and replan Bahrain deployment under the frozen energy-scarcity cases."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from shutil import copyfile

from bahrain_pace_model import build_env
from benchmark_circuit_control import gzsave, save, sha, sources
from compare_bahrain_equal_work import MATCH_J, MAX_BISECTIONS, SAMPLES, refinement, work
from f1energy.circuit_control import baseline_policy, rollout
from map_bahrain_deployment import assess_grid, deployment_zones, evaluate, write_profiles
from optimize_regeneration_dp import search
from validate_regeneration import audit_replay
from verify_bahrain_deployment import read, verify_rollout


PARENT = Path('results/bahrain-deployment-zones-001')
EQUAL = Path('results/bahrain-equal-work-001')
MODEL = Path('results/bahrain-pace-calibration-001/model.json')
SETTINGS = Path('configs/bahrain_deployment_zones.json')
GRIDS = (160, 320)
SUFFIX = 3
SCHEDULE_SCALE = [i / 8 for i in range(9)]
SUFFIX_TARGETS = [1., .75, .5, .25, .125, 0.]


def actions(trace):
    return [row['action'] for row in trace['trace']]


def signed_dependencies(manifest, paths):
    signed = {Path(path): digest for group in read(manifest).values() for path, digest in group.items()}
    for path in paths:
        matches = {digest for archived, digest in signed.items()
                   if archived == path or (archived.is_absolute() and archived.parts[-len(path.parts):] == path.parts)}
        if matches != {sha(path)}:
            raise ValueError(f'Archived input hash differs for {path}')


def summarize(trace, path, env, model):
    row = {key: value for key, value in trace.items() if key not in ('trace', 'reward_sum')}
    row.update(audit_replay(trace, model, model, env.vehicle), wheel_assist_j=work(trace), file=path.as_posix())
    if any(b['electrical_work_j'] > b['action'] * env.vehicle.electrical_limit_w * b['duration_s'] + 1e-5
           for b in trace['trace']):
        raise ValueError(f'Delivered work exceeds requested power in {path}')
    verify_rollout(row, model)
    return row


def archive_trace(source, path, env, model):
    copyfile(source, path)
    trace = read(path)
    return trace, summarize(trace, path, env, model)


def raw_case(name, model, protocol, folder, frozen):
    search_folder = folder / 'search'
    search_folder.mkdir()
    envs = {cells: build_env(model, cells) for cells in GRIDS}
    if name == 'nominal':
        found = dict(read(PARENT / 'central/search.json'), reused_archive=True)
        selected = found['actions']
    else:
        env = build_env(model, protocol['search_cells_per_block'])
        probes = {'frozen': frozen, 'spread': None, 'zero': None, 'full': None,
                  'finish_only': [0.] * (env.blocks - SUFFIX) + [1.] * SUFFIX}
        candidates, probe_rows = [], {}
        for label, schedule in probes.items():
            trace, row = evaluate(env, label, search_folder, schedule)
            probe_rows[label] = row
            if row['feasible']:
                candidates.append((row['duration_s'], label, actions(trace)))
        if candidates:
            _, label, incumbent = min(candidates)
            found = search(env, dict(protocol['search'], name=name), incumbent)
            selected = found['actions']
        else:
            # Retain the search attempt even when none of the fixed probes closes the lap.
            label, incumbent = 'finish_only', probes['finish_only']
            try:
                found = search(env, dict(protocol['search'], name=name), incumbent)
                selected = found['actions']
            except ValueError as error:
                if str(error) != 'selected schedule failed exact search-grid replay':
                    raise
                found = dict(name=name, actions=None, failure=str(error))
                selected = None
        found.update(incumbent_name=label, probes=probe_rows, reused_archive=False)
    save(folder / 'search.json', found)
    raw, profiles, zones = {}, {}, {}
    for cells, env in envs.items():
        grid = str(cells)
        raw[grid], profiles[grid] = {}, {}
        for label, schedule in [('frozen', frozen), ('adapted', selected), ('spread', None)]:
            if label == 'adapted' and selected is None:
                continue
            if name == 'nominal':
                source = 'spread' if label == 'spread' else 'selected'
                trace, row = archive_trace(PARENT / 'central' / f'{source}_{cells}.json.gz',
                                           folder / f'{label}_{cells}.json.gz', env, model)
                if label != 'spread' and (actions(trace) != frozen or not row['feasible']):
                    raise ValueError('Archived nominal planner schedule mismatch')
            else:
                trace, row = evaluate(env, label, folder, schedule)
                verify_rollout(row, model)
            raw[grid][label], profiles[grid][label] = row, trace
        write_profiles(folder / f'profile_{cells}.csv', env, profiles[grid])
        zones[grid] = {label: deployment_zones(env, trace, protocol['zone_min_wheel_j'])
                       for label, trace in profiles[grid].items()}
    return envs, raw, zones, selected


def individual_refinement(trajectory, limits):
    a, b = trajectory['160'], trajectory['320']
    differences = dict(relative_lap_change=abs(a['duration_s'] - b['duration_s']) / b['duration_s'],
                       terminal_energy_change_j=abs(a['final_energy_j'] - b['final_energy_j']),
                       recovered_change_j=abs(a['recovered_j'] - b['recovered_j']))
    return dict(differences, passed=a['feasible'] and b['feasible'] and
                all(value <= limits[key] for key, value in differences.items()))


def pair(reference, spread, alpha, limits, **details):
    rows = {}
    for grid in map(str, GRIDS):
        a, b = reference[grid], spread[grid]
        difference = b['wheel_assist_j'] - a['wheel_assist_j']
        both_feasible = a['feasible'] and b['feasible']
        rows[grid] = dict(reference=a, spread=b, difference_j=difference, both_feasible=both_feasible,
                          matched=abs(difference) <= MATCH_J,
                          saving_s=b['duration_s'] - a['duration_s'] if both_feasible else None)
    a, b = (row['saving_s'] for row in rows.values())
    change = abs(a - b) if a is not None and b is not None else None
    individual = {label: individual_refinement(trajectory, limits)
                  for label, trajectory in [('reference', reference), ('spread', spread)]}
    passed = (change is not None and change <= limits['paired_gap_change_s']
              and all(row['matched'] for row in rows.values()) and all(row['passed'] for row in individual.values()))
    direction = ('reference_faster' if a > 0 else 'spread_faster') if passed and a * b > 0 else None
    return dict(alpha=alpha, grids=rows, individual_refinement=individual, paired_gap_change_s=change,
                passed=passed, direction=direction, **details)


def trial_cache(envs, model, folder, name, schedule=None, suffix=0):
    trials = {str(cells): {} for cells in GRIDS}

    def trial(cells, alpha):
        env = envs[cells]
        rows = trials[str(cells)]
        if alpha not in rows:
            ordinary = baseline_policy('spread', env)

            def policy(obs):
                if suffix and env.index >= env.blocks - suffix:
                    return [1.]
                request = ordinary(obs)[0] if schedule is None else schedule[env.index]
                return [min(1., alpha * request)]

            trace = rollout(env, policy)
            path = folder / f'{name}_{cells}_alpha-{alpha}.json.gz'
            gzsave(path, trace)
            rows[alpha] = summarize(trace, path, env, model)
        return rows[alpha]

    return trial, trials


def find_scales(trial, samples, target):
    def error(alpha):
        return trial(GRIDS[0], alpha)['wheel_assist_j'] - target

    initial = [error(alpha) for alpha in samples]
    brackets = [refinement(lo, hi, error) for lo, hi, a, b in zip(samples, samples[1:], initial, initial[1:])
                if a * b < 0]
    candidates = {r['alpha'] for r in brackets} | {a for a, residual in zip(samples, initial) if abs(residual) <= MATCH_J}
    return sorted(candidates or {min(samples, key=lambda a: (abs(error(a)), a))}), brackets


def preferred(candidates):
    return min(candidates, key=lambda row: (not row['passed'],
               -sum(grid['both_feasible'] for grid in row['grids'].values()),
               sum(abs(grid['difference_j']) for grid in row['grids'].values()), row['alpha']))


def ordinary_matches(envs, model, folder, raw, labels, limits):
    trial, trials = trial_cache(envs, model, folder, 'ordinary_spread')
    for cells in GRIDS:
        trials[str(cells)][1.] = raw[str(cells)]['spread']
    result = {}
    for label in labels:
        reference = {grid: rows[label] for grid, rows in raw.items()}
        scales, brackets = find_scales(trial, SAMPLES, reference['160']['wheel_assist_j'])
        candidates = [pair(reference, {str(c): trial(c, alpha) for c in GRIDS}, alpha, limits)
                      for alpha in scales]
        result[label] = dict(ordinary=dict(preferred=preferred(candidates), brackets=brackets, candidates=candidates))
    return result, trials


def suffix_matches(envs, model, folder, schedules, matches, limits):
    spread, spread_trials = trial_cache(envs, model, folder, 'terminal_suffix_spread', suffix=SUFFIX)
    caches = {label: trial_cache(envs, model, folder, 'terminal_suffix_' + label, schedule, SUFFIX)
              for label, schedule in schedules.items()}
    options = {label: [] for label in schedules}
    common_alpha = None
    for alpha in SUFFIX_TARGETS:
        target = {str(c): spread(c, alpha) for c in GRIDS}
        if not all(row['feasible'] for row in target.values()):
            continue
        for label, (trial, _) in caches.items():
            scales, brackets = find_scales(trial, SCHEDULE_SCALE, target['160']['wheel_assist_j'])
            candidates = [pair({str(c): trial(c, beta) for c in GRIDS}, target, alpha, limits, beta=beta)
                          for beta in scales]
            options[label].append(dict(preferred=preferred(candidates), candidates=candidates, brackets=brackets))
        # Pick the first predeclared target with both physically feasible, grid-stable work matches.
        if alpha > 0 and all(rows[-1]['preferred']['passed'] for rows in options.values()):
            common_alpha = alpha
            break
    for label, choices in options.items():
        # Keep separate, feasible work levels if no common target is attained by the evaluated families.
        selected = next((row['preferred'] for row in choices if row['preferred']['passed'] and row['preferred']['alpha'] > 0), None)
        if common_alpha is not None:
            selected = choices[-1]['preferred']
        elif selected is None and choices:
            selected = preferred([row['preferred'] for row in choices])
        matches[label]['terminal_suffix'] = dict(preferred=selected, targets=choices, common_target_alpha=common_alpha)
    return dict(spread=spread_trials, **{label: trials for label, (_, trials) in caches.items()})


def run_case(name, model, protocol, folder, frozen, nominal_matches):
    folder.mkdir()
    envs, raw, zones, selected = raw_case(name, model, protocol, folder, frozen)
    labels = ('frozen', 'adapted') if selected is not None else ('frozen',)
    limits = protocol['refinement']
    if name == 'nominal':
        archives = {}
        for archive in nominal_matches:
            alpha = archive['alpha']
            archives[alpha] = {str(c): archive_trace(Path(archive[str(c)]['file']),
                       folder / f'ordinary_spread_{c}_alpha-{alpha}.json.gz', envs[c], model)[1] for c in GRIDS}
        matches = {}
        for label in labels:
            candidates = [pair({grid: r[label] for grid, r in raw.items()}, spread, alpha, limits)
                          for alpha, spread in archives.items()]
            matches[label] = dict(ordinary=dict(preferred=preferred(candidates), candidates=candidates,
                                               reused_archive=True))
        trials = {}
    else:
        matches, ordinary = ordinary_matches(envs, model, folder, raw, labels, limits)
        trials = dict(ordinary=ordinary)
        if any(not result['ordinary']['preferred']['passed'] for result in matches.values()):
            schedules = {'frozen': frozen}
            if selected is not None:
                schedules['adapted'] = selected
            trials['terminal_suffix'] = suffix_matches(envs, model, folder, schedules, matches, limits)
    raw_grid = {}
    if selected is not None:
        raw_grid = assess_grid({grid: dict(rows, selected=rows['adapted']) for grid, rows in raw.items()},
                               ('frozen', 'spread'), protocol['refinement'])
        del raw_grid['individual']['selected']
    save(folder / 'metrics.json', dict(scenario=name, model=model, raw=raw, zones=zones, raw_grid=raw_grid,
         matched=matches, trials=trials, search=(folder / 'search.json').as_posix()))
    print(f'{name} complete', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('results/bahrain-scarcity-planners-001'))
    parser.add_argument('--protocol', type=Path, default=Path('configs/bahrain_energy_scarcity.json'))
    parser.add_argument('--workers', type=int, choices=(1, 2, 3, 4), default=3)
    args = parser.parse_args()
    study = read(args.protocol)
    if (Path(study['model']) != MODEL or tuple(study['grids']) != GRIDS
            or study['total_work_pair_tolerance_j'] != MATCH_J or study['finish_speed_tolerance_mps'] != 1e-5):
        raise ValueError('Shared protocol differs from archived model or work-matching tolerances')
    for path, digest in study['parent_hashes'].items():
        if sha(path) != digest:
            raise ValueError(f'Shared protocol parent hash differs for {path}')
    model = read(MODEL)
    protocol = read(SETTINGS)
    if protocol['refinement'] != study['refinement']:
        raise ValueError('Shared refinement limits differ from the archived deployment protocol')
    parent_manifest, equal_manifest = PARENT / 'manifest.json', EQUAL / 'manifest.json'
    search_path = PARENT / 'central/search.json'
    base_code = sources()
    for name in ('bahrain_pace_model', 'benchmark_circuit_control', 'map_bahrain_deployment',
                 'optimize_regeneration_dp', 'validate_regeneration', 'verify_bahrain_deployment'):
        path = Path(f'scripts/{name}.py')
        base_code[path.as_posix()] = sha(path)
    historical = [MODEL, SETTINGS, Path(model['geometry']), search_path,
                  *(PARENT / 'central' / f'{name}_{cells}.json.gz' for name in ('selected', 'spread') for cells in GRIDS)]
    signed_dependencies(parent_manifest, historical + [Path(path) for path in base_code])
    equal_metrics = EQUAL / 'metrics.json'
    nominal_matches = [row for row in read(equal_metrics)['comparisons'] if row['matched_primary']]
    nominal_archives = [equal_metrics, *(Path(row[str(c)]['file']) for row in nominal_matches for c in GRIDS)]
    helper = Path('scripts/compare_bahrain_equal_work.py')
    signed_dependencies(equal_manifest, nominal_archives + [helper])
    inputs = {p.as_posix(): sha(p) for p in [args.protocol, *historical, *nominal_archives]}
    inputs.update(study['parent_hashes'])
    code = {Path(p).as_posix(): value for p, value in base_code.items()}
    code.update({p.as_posix(): sha(p) for p in (helper, Path(__file__))})
    frozen = read(search_path)['actions']
    if len(frozen) != 55 or not all(0 <= value <= 1 for value in frozen):
        raise ValueError('Invalid archived deployment schedule')
    models = {name: dict(model, initial_energy_j=case['initial_energy_j'], regeneration=dict(model['regeneration'],
                   braking_fraction=case['braking_fraction'])) for name, case in study['scenarios'].items()}
    if models['nominal'] != model:
        raise ValueError('Nominal scarcity case differs from the archived calibration')
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / 'contract.json', dict(models=models, frozen_actions=frozen, search_grid=protocol['search_cells_per_block'],
         search=protocol['search'], search_incumbents=['frozen', 'spread', 'zero', 'full', 'finish_only'],
         grids=GRIDS, refinement=protocol['refinement'], ordinary_spread_alpha=SAMPLES, matching_tolerance_j=MATCH_J,
         max_bisections=MAX_BISECTIONS, final_blocks_full=SUFFIX, suffix_fixed_request_multipliers=SCHEDULE_SCALE,
         suffix_spread_target_multipliers=SUFFIX_TARGETS, inputs=inputs, sources=code,
         method='Use raw frozen, spread and adapted profiles, with fixed-suffix variants evaluated separately only after a raw work-match gate fails. Replay the same multiplier on the fine grid. Ordinary candidates rank by pass, feasibility count, total residual, then multiplier. Prefer the first predeclared positive suffix spread multiplier with a passing match for both reference profiles. Alpha zero is a terminal-only diagnostic. A directional match requires both individual refinement gates, 500 J work tolerance, 5 ms paired refinement and a common strict direction. Positive savings favor the reference schedule.'))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        jobs = [pool.submit(run_case, name, m, protocol, args.output / name, frozen, nominal_matches)
                for name, m in models.items()]
        for job in jobs:
            job.result()
    if any(sha(path) != digest for path, digest in (inputs | code).items()):
        raise RuntimeError('Input or source changed during the study')
    paths = {name: (args.output / name / 'metrics.json').as_posix() for name in models}
    save(args.output / 'metrics.json', dict(cases={name: read(path) for name, path in paths.items()}, case_files=paths))
    save(args.output / 'manifest.json', dict(inputs=inputs, sources=code,
         outputs={p.as_posix(): sha(p) for p in sorted(args.output.rglob('*')) if p.is_file()}))


if __name__ == '__main__':
    main()
