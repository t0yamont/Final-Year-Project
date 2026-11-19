"""Test whether a scaled spread policy can match the selected Bahrain wheel work."""
import argparse
import json
from pathlib import Path

from bahrain_pace_model import build_env
from benchmark_circuit_control import gzsave, save, sha, sources
from f1energy.circuit_control import baseline_policy, rollout
from validate_regeneration import audit_replay
from verify_bahrain_deployment import read, verify_rollout
import matplotlib.pyplot as plt


PARENT = Path('results/bahrain-deployment-zones-001')
MODEL = Path('results/bahrain-pace-calibration-001/model.json')
SAMPLES = [i / 4 for i in range(17)]
MATCH_J = 500
MAX_BISECTIONS = 16


def work(trace):
    return sum(block['electrical_work_j'] for block in trace['trace'])


def refinement(lo, hi, error):
    """Retain the closest tested point even if the tolerance is unreachable."""
    original = [lo, hi]
    lower, upper = error(lo), error(hi)
    for _ in range(MAX_BISECTIONS):
        best = min((lo, hi), key=lambda alpha: abs(error(alpha)))
        if abs(error(best)) <= MATCH_J:
            break
        mid = (lo + hi) / 2
        value = error(mid)
        if lower * value > 0:
            lo, lower = mid, value
        else:
            hi, upper = mid, value
    best = lo if abs(lower) <= abs(upper) else hi
    return dict(bracket=original, alpha=best, primary_error_j=error(best), matched=abs(error(best)) <= MATCH_J)


def summaries(alpha, grid, env, model, output):
    spread = baseline_policy('spread', env)
    policy = lambda obs: [min(1., alpha * spread(obs)[0])]
    record = rollout(env, policy)
    audit = audit_replay(record, model, model, env.vehicle)
    row = {k: v for k, v in record.items() if k not in ('trace', 'reward_sum')}
    path = output / f'spread_{grid}_alpha-{alpha}.json.gz'
    gzsave(path, record)
    row.update(audit, alpha=alpha, wheel_assist_j=work(record), file=str(path))
    verify_rollout(row, model)
    return row


def plot(path, samples, roots, target):
    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(7.7, 6.2))
    for i, ax in enumerate(axes):
        def ordinate(row):
            return (row['wheel_assist_j'] - target) / 1000 if i == 0 else row['terminal_speed_error_mps']
        ax.plot([r['alpha'] for r in samples], [ordinate(r) for r in samples],
                color='#7d8d96', label='160-cell scan')
        for feasible, label, color, marker in [(True, 'Feasible finish', '#0c607d', 'o'),
                                               (False, 'Finish-speed miss', '#aa471c', 'x')]:
            chosen = [r for r in samples if r['feasible'] == feasible]
            ax.scatter([r['alpha'] for r in chosen], [ordinate(r) for r in chosen], color=color, marker=marker, label=label)
        for j, root in enumerate(roots):
            row = root['160']
            ax.scatter(row['alpha'], ordinate(row), marker='D', facecolor='white', edgecolor='#3f326d',
                       zorder=4, label='Refined point' if j == 0 else None)
        ax.axhline(0, lw=.8, color='#3a3a3a')
        if i == 0:
            ax.axhspan(-MATCH_J / 1000, MATCH_J / 1000, color='#3f326d', alpha=.15, label='Match tolerance')
        ax.grid(alpha=.25)
    axes[0].set_title('Bahrain spread multiplier and wheel work | bahrain-equal-work-001', loc='left')
    axes[0].set_ylabel('Wheel work minus target (kJ)')
    axes[0].legend(fontsize=8, ncols=2)
    axes[1].set(xlabel='Applied multiplier to spread request', ylabel='Finish-speed error (m/s)')
    fig.tight_layout()
    for ext in ('png', 'pdf'):
        fig.savefig(path.with_suffix(f'.{ext}'), dpi=300)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--figures', required=True, type=Path)
    args = parser.parse_args()
    parent_manifest = PARENT / 'manifest.json'
    parent = read(parent_manifest)
    relevant = [MODEL, PARENT / 'central' / 'search.json']
    archives = {grid: {name: PARENT / 'central' / f'{name}_{grid}.json.gz'
                       for name in ('selected', 'spread')} for grid in (160, 320)}
    for pair in archives.values():
        relevant.extend(pair.values())
    code = sources()
    for name in ('bahrain_pace_model', 'benchmark_circuit_control', 'validate_regeneration', 'verify_bahrain_deployment'):
        path = Path(f'scripts/{name}.py')
        code[str(path)] = sha(path)
    previous = {str(Path(k)): v for group in parent.values() for k, v in group.items()}
    for path in (*relevant, *code):
        if sha(path) != previous[str(path)]:
            raise ValueError(f'Parent input differs: {path}')
    code[str(Path(__file__))] = sha(__file__)
    inputs = {str(p): sha(p) for p in [parent_manifest, *relevant]}
    model = read(MODEL)
    inputs[model['geometry']] = sha(model['geometry'])
    selected = {grid: read(pair['selected']) for grid, pair in archives.items()}
    actions = read(PARENT / 'central' / 'search.json')['actions']
    if any(len(actions) != 55 or not r['feasible'] or
           [block['action'] for block in r['trace']] != actions for r in selected.values()):
        raise ValueError('Saved selected schedule differs or is infeasible')
    args.output.mkdir(parents=True, exist_ok=False)
    args.figures.mkdir(parents=True, exist_ok=False)
    target = work(selected[160])
    save(args.output / 'contract.json', dict(alpha_scan=SAMPLES, max_bisections=MAX_BISECTIONS,
         tolerance_j=MATCH_J, grid_primary=160, grid_refined=320, actions=actions, target_wheel_j=target,
         policy='min(1, alpha * ordinary adaptive spread request)', inputs=inputs, sources=code))

    grids = {n: build_env(model, n) for n in archives}
    trials = {n: {} for n in grids}
    def trial(grid, alpha):
        if alpha not in trials[grid]:
            row = summaries(alpha, grid, grids[grid], model, args.output)
            trials[grid][alpha] = row
            if alpha == 1 and read(row['file']) != read(archives[grid]['spread']):
                raise ValueError(f'Alpha = 1 failed exact spread parity at {grid} cells')
        return trials[grid][alpha]

    def error(alpha):
        return trial(160, alpha)['wheel_assist_j'] - target

    initial = [trial(160, alpha) for alpha in SAMPLES]
    brackets = [refinement(lo, hi, error) for lo, hi in zip(SAMPLES, SAMPLES[1:]) if error(lo) * error(hi) < 0]
    matched_alphas = {r['alpha'] for r in brackets if r['matched']}
    matched_alphas.update(alpha for alpha in SAMPLES if abs(error(alpha)) <= MATCH_J)
    replay_alphas = sorted(matched_alphas | {r['alpha'] for r in brackets} | {1.})
    comparisons = []
    for alpha in replay_alphas:
        row = dict(alpha=alpha, matched_primary=alpha in matched_alphas)
        for grid, trace in selected.items():
            candidate = trial(grid, alpha)
            gap = candidate['wheel_assist_j'] - work(trace)
            row[str(grid)] = dict(candidate, target_difference_j=gap,
                feasible_gain_s=candidate['duration_s'] - trace['duration_s'] if candidate['feasible'] else None,
                matched=abs(gap) <= MATCH_J)
        comparisons.append(row)

    records = dict(archived={grid: dict(wheel_assist_j=work(trace), duration_s=trace['duration_s'],
                   file=str(archives[grid]['selected'])) for grid, trace in selected.items()},
                   scan=initial, brackets=brackets, comparisons=comparisons,
                   all_trials={grid: [rows[a] for a in sorted(rows)] for grid, rows in trials.items()},
                   alpha_one_exact_parity=True)
    save(args.output / 'metrics.json', records)
    plot(args.figures / '01_bahrain_spread_work_match', initial, [r for r in comparisons if r['alpha'] != 1], target)
    if any(sha(p) != h for p, h in (inputs | code).items()):
        raise ValueError('A bound input changed during the study')
    manifest = dict(inputs=inputs, sources=code, outputs={str(p): sha(p) for folder in (args.output, args.figures)
                    for p in sorted(folder.iterdir()) if p.is_file()})
    save(args.output / 'manifest.json', manifest)
    print(json.dumps(dict(probes={n: len(rows) for n, rows in trials.items()},
                          hashes=sum(len(x) for x in manifest.values()),
                          roots=brackets, comparison_alphas=replay_alphas)), flush=True)


if __name__ == '__main__':
    main()
