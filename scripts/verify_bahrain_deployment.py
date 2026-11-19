"""Independently check the saved Bahrain deployment replays and paired results."""
import argparse
import csv
import gzip
import json
from math import isclose
from pathlib import Path
from types import SimpleNamespace

from benchmark_circuit_control import sha
from validate_regeneration import audit_replay


def read(path):
    if str(path).endswith('.gz'):
        with gzip.open(path, 'rt') as stream:
            return json.load(stream)
    return json.loads(Path(path).read_text())


def close(a, b, tolerance=1e-7):
    if not isclose(a, b, rel_tol=0, abs_tol=tolerance):
        raise ValueError(f'Check failed: {a} versus {b}')


def verify_rollout(row, model):
    replay = read(row['file'])
    trace = replay['trace']
    if len(trace) != 55:
        raise ValueError(f'Incomplete trace: {row["file"]}')
    audit = audit_replay(replay, model, model, SimpleNamespace(**model['vehicle']))
    for key, value in audit.items():
        close(value, row[key])
    close(sum(b['duration_s'] for b in trace), row['duration_s'])
    close(sum(b['electrical_work_j'] for b in trace), row['wheel_assist_j'])
    close(trace[-1]['state']['energy_j'], row['final_energy_j'])
    close(trace[-1]['state']['speed_m_per_s'] - model['initial_speed_mps'], row['terminal_speed_error_mps'])
    if any(not 0 <= b['action'] <= 1 for b in trace):
        raise ValueError('Action outside [0, 1]')
    max_cap = max(b['max_node_cap_excess_mps'] for b in trace)
    feasible = abs(row['terminal_speed_error_mps']) < 1e-5 and max_cap < 1e-5         and abs(sum(b['energy_residual_j'] for b in trace)) < 1
    if feasible != row['feasible'] or feasible != replay['feasible']:
        raise ValueError('Feasibility mismatch')
    return trace


def verify_profiles(path, replays):
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    for policy in {r['policy'] for r in rows}:
        trace = replays[policy]
        profile = [r for r in rows if r['policy'] == policy]
        if len(profile) != len(trace):
            raise ValueError('Incomplete CSV profile')
        for csv_row, block in zip(profile, trace):
            close(float(csv_row['cumulative_time_s']), block['state']['elapsed_s'])
            close(float(csv_row['wheel_assist_kj']) * 1000, block['electrical_work_j'])
            close(float(csv_row['battery_charge_kj']) * 1000, block['battery_recovered_j'])
            close(float(csv_row['to_m']), block['state']['distance_m'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    manifest = read(args.run / 'manifest.json')
    contract = read(args.run / 'contract.json')
    metrics = read(args.run / 'metrics.json')
    for name in ('inputs', 'sources', 'outputs'):
        for path, digest in manifest[name].items():
            if sha(path) != digest:
                raise ValueError(f'Hash mismatch: {path}')
    n_replays = 0
    for scenario, evaluation in metrics['evaluations'].items():
        search = read(args.run / scenario / 'search.json')
        for name, row in search['probes'].items():
            n_replays += 1
            verify_rollout(row, contract['models'][scenario])
        for grid, rows in evaluation['results'].items():
            traces = {policy: verify_rollout(row, contract['models'][scenario]) for policy, row in rows.items()}
            n_replays += len(rows)
            verify_profiles(args.run / scenario / f'profile_{grid}.csv', traces)
            actual = [block['action'] for block in traces['selected']]
            if actual != search['actions']:
                raise ValueError('Refinement changed selected actions')
            for policy, comparison in evaluation['paired'].items():
                close(rows[policy]['duration_s'] - rows['selected']['duration_s'], comparison[f'delta_{grid}_s'])
                if policy.startswith('shift_'):
                    suffix, direction = policy.split('_')[1:]
                    start, end = map(int, suffix.split('-'))
                    step = {'earlier': -1, 'later': 1}[direction]
                    first, last = start - 1, end - 1
                    original, moved = actual, [block['action'] for block in traces[policy]]
                    if (max(first, first + step) >= len(moved) or min(first, first + step) < 0
                            or max(last, last + step) >= len(moved)
                            or any(moved[i + step] != original[i] for i in range(first, last + 1))
                            or any(a != b for i, (a, b) in enumerate(zip(original, moved))
                                   if i < min(first, first + step) or i > max(last, last + step))
                            or sorted(original) != sorted(moved)):
                        raise ValueError('Shift did not preserve the selected request window')
                    close(rows[policy]['wheel_assist_j']-rows['selected']['wheel_assist_j'],
                          comparison[f'wheel_assist_delta_{grid}_j'])
    print(f'{sum(len(g) for g in manifest.values())} hashes and {n_replays} replays checked')


if __name__ == '__main__':
    main()
