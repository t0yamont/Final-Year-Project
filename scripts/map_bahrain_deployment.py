"""Experimental Bahrain deployment map using a frozen pace-model calibration."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
from matplotlib.collections import LineCollection
import matplotlib.pyplot as plt
import numpy as np

from bahrain_pace_model import build_env
from benchmark_circuit_control import gzsave, save, sha, sources
from f1energy.circuit_control import baseline_policy, rollout
from optimize_regeneration_dp import replay, search
from validate_regeneration import audit_replay


def evaluate(env, name, output, actions=None):
    """Save exact traces including terminal-speed misses, with independent energy checks."""
    record = rollout(env, baseline_policy(name, env)) if actions is None else replay(env, actions)
    audit = audit_replay(
        record, dict(initial_speed_mps=env.initial_speed, regeneration=vars(env.regeneration)),
        dict(initial_energy_j=env.initial_energy, reserve_j=env.reserve), env.vehicle)
    previous = (0., 0.)
    for block in record['trace']:
        requested_w = block['action'] * env.vehicle.electrical_limit_w
        if block['electrical_work_j'] > requested_w * block['duration_s'] + 1e-5:
            raise ValueError('delivered work exceeds request times duration')
        if abs(block['battery_discharged_j'] - block['electrical_work_j'] / env.vehicle.discharge_efficiency) > .01:
            raise ValueError('recorded discharge disagrees with work')
        if abs(block['charging_loss_j'] - block['regenerative_braking_work_j'] + block['battery_recovered_j']) > .01:
            raise ValueError('recorded charge losses disagree with recovered energy')
        state = block['state']
        if (not np.isclose(state['elapsed_s'] - previous[0], block['duration_s'], rtol=0, atol=1e-8)
                or state['distance_m'] <= previous[1]):
            raise ValueError('inconsistent elapsed time or distance')
        previous = (state['elapsed_s'], state['distance_m'])
    if abs(previous[0] - record['duration_s']) > 1e-8 or abs(previous[1] - env.grid.distance_m[-1]) > 1e-7:
        raise ValueError('inconsistent replay endpoint')
    file = output / f'{name}_{env.cells_per_block}.json.gz'
    gzsave(file, record)
    metrics = {key: value for key, value in record.items() if key not in ('trace', 'reward_sum')}
    metrics.update(audit, file=str(file), wheel_assist_j=sum(r['electrical_work_j'] for r in record['trace']))
    return record, metrics


def search_scenario(model, protocol, name, output):
    settings = dict(protocol['search'], name=name)
    grid = protocol['search_cells_per_block']
    env = build_env(model, grid)
    candidates = []
    search_probes = {}
    for label in ('full', 'spread', 'zero', 'finish_only'):
        actions = [0.] * (env.blocks - 3) + [1.] * 3 if label == 'finish_only' else None
        trace, metadata = evaluate(env, label, output, actions)
        search_probes[label] = metadata
        if trace['feasible']:
            candidates.append((trace['duration_s'], label, [r['action'] for r in trace['trace']]))
    if not candidates:
        save(output / 'search_failure.json', dict(reason='No feasible search incumbent', trials=search_probes))
        raise ValueError(f'{name}: no feasible search incumbent')
    _, incumbent_name, incumbent = min(candidates)
    found = search(env, settings, incumbent)
    found.update(incumbent_name=incumbent_name, probes=search_probes)
    save(output / 'search.json', found)
    print(name, found['search_time_s'], found['transitions'], flush=True)
    return found


def windows(actions, energy, threshold_j):
    """Return maximal contiguous positive requests above a total delivered-work cutoff."""
    groups = []
    start = None
    for block, action in enumerate([*actions, 0.]):
        if action > 0 and start is None:
            start = block
        if action == 0 and start is not None:
            work = sum(energy[start:block])
            if work >= threshold_j:
                groups.append(dict(start_block=start + 1, end_block=block, wheel_assist_j=work))
            start = None
    return groups


def shift_schedule(actions, zone, step):
    a, b = zone['start_block'] - 1, zone['end_block']
    adjacent = a - 1 if step == -1 else b
    if adjacent < 0 or adjacent >= len(actions):
        return None, 'timing-line boundary'
    if actions[adjacent] > 0:
        return None, 'destination occupied'
    shifted = list(actions)
    shifted[a:b] = [0.] * (b - a)
    shifted[a+step:b+step] = actions[a:b]
    return shifted, None


def shift_trials(actions, zones, count):
    selected = sorted(zones, key=lambda r: (-r['wheel_assist_j'], r['start_block']))[:count]
    for zone in selected:
        for direction, step in [('earlier', -1), ('later', 1)]:
            shifted, reason = shift_schedule(actions, zone, step)
            yield f"shift_{zone['start_block']:02d}-{zone['end_block']:02d}_{direction}", shifted, reason


def assess_grid(results, comparisons, limits):
    rows = {name: [grid[name] for grid in results.values()] for name in results['160']}
    records = {}
    for name, (coarse, fine) in rows.items():
        differences = {
            'time_320_minus_160_s': fine['duration_s'] - coarse['duration_s'],
            'relative_lap_change': abs(fine['duration_s'] - coarse['duration_s']) / fine['duration_s'],
            'terminal_energy_change_j': abs(fine['final_energy_j'] - coarse['final_energy_j']),
            'recovered_change_j': abs(fine['recovered_j'] - coarse['recovered_j']),
            'discharged_change_j': abs(fine['discharged_j'] - coarse['discharged_j']),
        }
        records[name] = dict(both_feasible=coarse['feasible'] and fine['feasible'], **differences)
    paired = {}
    for name in comparisons:
        a = results['160'][name]
        b = results['320'][name]
        gap160 = a['duration_s'] - results['160']['selected']['duration_s']
        gap320 = b['duration_s'] - results['320']['selected']['duration_s']
        both_feasible = records['selected']['both_feasible'] and records[name]['both_feasible']
        paired[name] = dict(delta_160_s=gap160, delta_320_s=gap320, gap_change_s=abs(gap160 - gap320),
                            both_feasible=both_feasible,
                            passes_paired_tolerance=both_feasible and abs(gap160 - gap320) <= limits['paired_gap_change_s'])
    for row in records.values():
        row['passes_refinement'] = row['both_feasible'] and all(
            row[key] <= limits[key] for key in ('relative_lap_change', 'terminal_energy_change_j', 'recovered_change_j'))
    return dict(individual=records, paired=paired)


def evaluate_scenario(model, protocol, output, found, central):
    actions = found['actions']
    grids = {str(n): build_env(model, n) for n in protocol['replay_cells_per_block']}
    policies = dict(full=None, spread=None, zero=None, finish_only=[0.] * (len(actions)-3) + [1.] * 3,
                    selected=actions)
    if found['name'] != 'central':
        policies['central_transfer'] = central
    results = {grid: {} for grid in grids}
    traces = {}
    for grid, env in grids.items():
        traces[grid] = {}
        for label, schedule in policies.items():
            traces[grid][label], results[grid][label] = evaluate(env, label, output, schedule)
    zones = {grid: deployment_zones(grids[grid], traces[grid]['selected'], protocol['zone_min_wheel_j'])
             for grid in grids}
    unavailable_shifts = {}
    if found['name'] == 'central':
        for name, moved, reason in shift_trials(actions, zones['160'], protocol['shift_window_count']):
            if moved is None:
                unavailable_shifts[name] = reason
                continue
            for grid, env in grids.items():
                _, results[grid][name] = evaluate(env, name, output, moved)
    comparisons = assess_grid(results, (key for key in results['160'] if key != 'selected'), protocol['refinement'])
    for label, row in comparisons['paired'].items():
        if label.startswith('shift_'):
            for grid in grids:
                row[f'wheel_assist_delta_{grid}_j'] = results[grid][label]['wheel_assist_j'] - results[grid]['selected']['wheel_assist_j']
                row[f'recharge_delta_{grid}_j'] = results[grid][label]['recovered_j'] - results[grid]['selected']['recovered_j']
                row[f'finish_energy_delta_{grid}_j'] = results[grid][label]['final_energy_j'] - results[grid]['selected']['final_energy_j']
    data = dict(results=results, zones=zones, unavailable_shifts=unavailable_shifts, **comparisons)
    save(output / 'evaluation.json', data)
    for grid, env in grids.items():
        write_profiles(output / f'profile_{grid}.csv', env, traces[grid])
    return data


def block_rows(env, record):
    t0, d0 = 0., 0.
    recovered = discharged = 0.
    for i, block in enumerate(record['trace'], start=1):
        state = block['state']
        recovered += block['battery_recovered_j']
        discharged += block['battery_discharged_j']
        yield dict(block=i, from_m=d0, to_m=state['distance_m'], duration_s=state['elapsed_s']-t0,
                   request_fraction=block['action'], request_kw=block['action']*env.vehicle.electrical_limit_w/1000,
                   wheel_assist_kw=block['electrical_work_j']/block['duration_s']/1000,
                   wheel_assist_kj=block['electrical_work_j']/1000,
                   wheel_brake_recovery_kj=block['regenerative_braking_work_j']/1000,
                   battery_charge_kj=block['battery_recovered_j']/1000,
                   battery_kj=state['energy_j']/1000, cumulative_charged_kj=recovered/1000,
                   cumulative_discharged_kj=discharged/1000, cumulative_time_s=state['elapsed_s'])
        t0, d0 = state['elapsed_s'], state['distance_m']


def deployment_zones(env, record, threshold):
    rows = list(block_rows(env, record))
    groups = windows([r['request_fraction'] for r in rows], [r['wheel_assist_kj']*1000 for r in rows], threshold)
    for group in groups:
        blocks = rows[group['start_block']-1:group['end_block']]
        group.update(from_m=blocks[0]['from_m'], to_m=blocks[-1]['to_m'],
                     peak_block_average_wheel_kw=max(r['wheel_assist_kw'] for r in blocks),
                     average_wheel_kw=group['wheel_assist_j']/sum(r['duration_s'] for r in blocks)/1000,
                     battery_charge_j=sum(r['battery_charge_kj'] for r in blocks)*1000)
    return groups


def write_profiles(path, env, traces):
    rows = [dict(policy=name, **row) for name, trace in traces.items() for row in block_rows(env, trace)]
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_profiles(path):
    profiles = {}
    with path.open() as handle:
        for row in csv.DictReader(handle):
            profiles.setdefault(row.pop('policy'), []).append({k: float(v) for k, v in row.items()})
    return profiles


def overlap(a, b, threshold_kj):
    support_a, support_b = a >= threshold_kj, b >= threshold_kj
    union = int(np.sum(support_a | support_b))
    total = float(np.sum(np.maximum(a, b)))
    return dict(active_block_count=[int(np.sum(support_a)), int(np.sum(support_b))],
                shared_active_blocks=[int(i)+1 for i in np.flatnonzero(support_a & support_b)],
                active_block_jaccard=float(np.sum(support_a & support_b)/union) if union else None,
                delivered_energy_overlap=float(np.sum(np.minimum(a, b))/total) if total else None)


def corner_stations(model, grid, landmarks):
    return {c['turn']: float(np.interp(((c['source_geometry_fraction'] - model['line_offset_fraction']) % 1)
                                       * grid.parameter_m[-1], grid.parameter_m, grid.distance_m))
            for c in landmarks['corners']}


def figures(model, landmarks, profiles, target, title, baseline_metrics):
    env = build_env(model, 160)
    xy = env.grid.xy_m
    rows = profiles['central']['selected']
    edges = np.r_[0., [r['to_m']/1000 for r in rows]]
    colors = ['#174f77', '#b0582d', '#588047']
    corners = corner_stations(model, env.grid, landmarks)
    fig, ax = plt.subplots(figsize=(7.1, 7.4))
    edges_xy = np.stack((xy[:-1], xy[1:]), axis=1)
    color_track = LineCollection(edges_xy, cmap='viridis', norm=plt.Normalize(0, env.vehicle.electrical_limit_w/1000),
                                 linewidth=5, capstyle='round')
    color_track.set_array(np.repeat([r['wheel_assist_kw'] for r in rows], env.cells_per_block))
    ax.add_collection(color_track)
    fig.colorbar(color_track, ax=ax, shrink=.72, pad=.04, label='Delivered wheel assist (block-mean kW)')
    for number, station in corners.items():
        pos = np.searchsorted(env.grid.distance_m, station)
        ax.annotate(f'T{number}', xy[pos], xytext=(6, 5), textcoords='offset points', fontsize=8)
    ax.scatter(*xy[0], color='#c0442b', zorder=3)
    ax.annotate('', xy[160], xy[0], arrowprops={'arrowstyle': '-|>', 'color': '#c0442b', 'lw': 1.8})
    ax.annotate('Timing line · 0 km', xy[0], xytext=(-8, 9), ha='right', textcoords='offset points', fontsize=9)
    ax.autoscale()
    ax.margins(.12)
    ax.set_aspect('equal')
    ax.set_axis_off()
    ax.set_title(f'Central Bahrain deployment map | {title}', loc='left')
    fig.text(.08, .04, 'Approximate turn labels. Distance follows the model centreline. Exploratory simulation.', fontsize=8)
    export(fig, target / '01_bahrain_wheel_assist')

    fig, axes = plt.subplots(4, 1, figsize=(10, 9), sharex=True)
    axes[0].stairs([r['request_kw'] for r in rows], edges, label='Central requested', color='#4a4a4a', ls=':')
    for (name, data), color in zip(profiles.items(), colors):
        axes[0].stairs([r['wheel_assist_kw'] for r in data['selected']], edges, label=f'{name.replace("_", " ").capitalize()} delivered', color=color)
    for key, label, color in [('wheel_assist_kj', 'Wheel assist', colors[0]), ('battery_charge_kj', 'Battery charge from brakes', colors[2])]:
        axes[1].stairs([r[key] for r in rows], edges, label=label, color=color)
    for key, label, color, initial in [('battery_kj', 'Battery stored', colors[0], env.initial_energy/1000),
                                             ('cumulative_charged_kj', 'Cumulative charge', colors[2], 0.),
                                             ('cumulative_discharged_kj', 'Cumulative discharge', colors[1], 0.)]:
        axes[2].plot(edges, np.r_[initial, [r[key] for r in rows]]/1000, label=label, color=color)
    for name, color in [('full', colors[1]), ('spread', colors[2])]:
        other = profiles['central'][name]
        delta = [b['cumulative_time_s']-a['cumulative_time_s'] for a,b in zip(rows,other)]
        status = '' if baseline_metrics[name]['feasible'] else ' (terminal-speed miss)'
        axes[3].plot(edges, np.r_[0., delta], color=color, label=f'{name.capitalize()} minus selected{status}')
    axes[3].axhline(0, color='#4a4a4a', lw=.6)
    for ax, label in zip(axes, ['Wheel power (kW)', 'Energy per block (kJ)', 'Battery energy (MJ)', 'Time difference (s)']):
        ax.set_ylabel(label)
        ax.grid(alpha=.24)
        ax.legend(loc='upper left', fontsize=8, ncols=2)
    axes[3].set_xlabel('Distance from timing line (km)')
    axes[0].set_title(f'Bahrain deployment, recovery and time | {title}', loc='left')
    fig.text(.09, .018, 'Full-block averages include braking, speed constraints and depletion. Exploratory simulation.', fontsize=8)
    fig.tight_layout(rect=(0, .04, 1, 1))
    export(fig, target / '02_bahrain_deployment_profiles')
    return corners


def export(fig, path):
    for ext in ('.png', '.pdf'):
        fig.savefig(path.with_suffix(ext), dpi=300, bbox_inches='tight')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, default=Path('configs/bahrain_deployment_zones.json'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--figures', type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text())
    model_path = Path(protocol['model'])
    base = json.loads(model_path.read_text())
    landmarks_path = Path(protocol['landmarks'])
    landmarks = json.loads(landmarks_path.read_text())
    models = {'central': base}
    for name, change in protocol['scenarios'].items():
        variant = deepcopy(base)
        for key in change['keys']:
            variant[key] *= change['multiplier']
        models[name] = variant
    inputs = {str(path): sha(path) for path in (args.protocol, model_path, landmarks_path, Path(base['geometry']))}
    code = sources()
    for name in ('map_bahrain_deployment', 'bahrain_pace_model', 'benchmark_circuit_control',
                 'optimize_regeneration_dp', 'validate_regeneration', 'verify_bahrain_deployment'):
        path = Path(f'scripts/{name}.py')
        code[str(path)] = sha(path)
    args.output.mkdir(parents=True, exist_ok=False)
    args.figures.mkdir(parents=True, exist_ok=False)
    save(args.output / 'contract.json', dict(protocol=protocol, models=models, inputs=inputs, sources=code))
    directories = {name: args.output / name for name in models}
    for folder in directories.values():
        folder.mkdir()
    with ProcessPoolExecutor(max_workers=len(models)) as pool:
        searches = {name: pool.submit(search_scenario, model, protocol, name, directories[name])
                    for name, model in models.items()}
        central = searches['central'].result()['actions']
        futures = {name: pool.submit(evaluate_scenario, model, protocol, directories[name], searches[name].result(), central)
                   for name, model in models.items()}
        evaluations = {name: future.result() for name, future in futures.items()}
    summaries = {}
    for grid in protocol['replay_cells_per_block']:
        profiles = {name: read_profiles(folder / f'profile_{grid}.csv') for name, folder in directories.items()}
        energy = {name: np.array([r['wheel_assist_kj'] for r in data['selected']]) for name,data in profiles.items()}
        summaries[str(grid)] = {name: overlap(energy['central'], values, protocol['active_min_wheel_kj'])
                                for name, values in energy.items() if name != 'central'}
        if grid == 160:
            corners = figures(base, landmarks, profiles, args.figures, args.output.name,
                              evaluations['central']['results']['160'])
    save(args.output / 'metrics.json', dict(evaluations=evaluations, scenario_overlap=summaries,
                                           approximate_corner_stations_m=corners))
    if any(sha(path) != digest for path, digest in (inputs | code).items()):
        raise RuntimeError('study inputs changed during search or replay')
    save(args.output / 'manifest.json', dict(inputs=inputs, sources=code, outputs={
        str(path): sha(path) for folder in (args.output, args.figures)
        for path in sorted(folder.rglob('*')) if path.is_file()}))


if __name__ == '__main__':
    main()
