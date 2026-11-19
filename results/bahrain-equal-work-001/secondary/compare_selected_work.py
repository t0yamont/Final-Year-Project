"""Reciprocal match: scale selected Bahrain requests to the ordinary spread wheel work."""
import json
from pathlib import Path

from compare_bahrain_equal_work import MODEL, PARENT, MATCH_J, MAX_BISECTIONS, refinement, work
from bahrain_pace_model import build_env
from benchmark_circuit_control import gzsave, save, sha, sources
from optimize_regeneration_dp import replay
from validate_regeneration import audit_replay
from verify_bahrain_deployment import read, verify_rollout
import matplotlib.pyplot as plt


OUTPUT = Path('results/bahrain-equal-work-001/secondary')
FIGURES = Path('figures/dissertation/bahrain-equal-work-v1')
SAMPLES = [i / 10 for i in range(11)]


def main():
    hashes = read(PARENT / 'manifest.json')
    parent = {Path(k): v for group in hashes.values() for k, v in group.items()}
    spread_paths = {n: PARENT / 'central' / f'spread_{n}.json.gz' for n in (160, 320)}
    selected_paths = {n: PARENT / 'central' / f'selected_{n}.json.gz' for n in spread_paths}
    model = read(MODEL)
    action_path = PARENT / 'central' / 'search.json'
    inputs = {str(p): sha(p) for p in [MODEL, action_path, Path(model['geometry']), *spread_paths.values(), *selected_paths.values()]}
    code = sources()
    for name in ('bahrain_pace_model', 'benchmark_circuit_control', 'optimize_regeneration_dp',
                 'validate_regeneration', 'verify_bahrain_deployment'):
        path = Path(f'scripts/{name}.py')
        code[str(path)] = sha(path)
    if any(parent[Path(p)] != h for p, h in (inputs | code).items()):
        raise ValueError('Parent inputs or simulation code differ')
    inputs[str(PARENT / 'manifest.json')] = sha(PARENT / 'manifest.json')
    code['scripts/compare_bahrain_equal_work.py'] = sha('scripts/compare_bahrain_equal_work.py')
    path = OUTPUT / Path(__file__).name
    code[str(path)] = sha(path)
    spread = {n: read(p) for n, p in spread_paths.items()}
    actions = read(action_path)['actions']
    if len(actions) != 55 or not all(r['feasible'] for r in spread.values()):
        raise ValueError('Spread reference is infeasible or selected request sequence has changed')
    target = work(spread[160])
    contract = OUTPUT / 'contract.json'
    if contract.exists():
        raise FileExistsError('Reciprocal study already started')
    save(contract, dict(beta_scan=SAMPLES, max_bisections=MAX_BISECTIONS, tolerance_j=MATCH_J,
        policy='beta * each of the selected fixed 55 requests', actions=actions, target_wheel_j=target,
        grid_primary=160, grid_refined=320, inputs=inputs, sources=code))
    grids = {n: build_env(model, n) for n in spread}
    trials = {n: {} for n in grids}

    def trial(grid, beta):
        rows = trials[grid]
        if beta not in rows:
            env = grids[grid]
            if beta == 1:
                record = read(selected_paths[grid])
                trace_path = selected_paths[grid]
            else:
                record = replay(env, [beta * a for a in actions])
                trace_path = OUTPUT / f'scaled_selected_{grid}_beta-{beta}.json.gz'
                gzsave(trace_path, record)
            audit = audit_replay(record, model, model, env.vehicle)
            row = {k: v for k, v in record.items() if k not in ('trace', 'reward_sum')}
            row.update(audit, beta=beta, wheel_assist_j=work(record), file=str(trace_path))
            verify_rollout(row, model)
            rows[beta] = row
        return rows[beta]

    def error(beta):
        return trial(160, beta)['wheel_assist_j'] - target

    initial = [trial(160, beta) for beta in SAMPLES]
    brackets = [dict(beta=r['alpha'], **{k: v for k, v in r.items() if k != 'alpha'})
                for lo, hi in zip(SAMPLES, SAMPLES[1:]) if error(lo) * error(hi) < 0
                for r in [refinement(lo, hi, error)]]
    matched_betas = {r['beta'] for r in brackets if r['matched']}
    matched_betas.update(beta for beta in SAMPLES if abs(error(beta)) <= MATCH_J)
    comparisons = []
    for beta in sorted(matched_betas | {r['beta'] for r in brackets} | {1.}):
        comparison = dict(beta=beta, matched_primary=beta in matched_betas)
        for grid, reference in spread.items():
            candidate = trial(grid, beta)
            delta = candidate['wheel_assist_j'] - work(reference)
            comparison[str(grid)] = dict(candidate, target_difference_j=delta, matched=abs(delta) <= MATCH_J,
                feasible_gain_s=reference['duration_s'] - candidate['duration_s'] if candidate['feasible'] else None)
        comparisons.append(comparison)
    save(OUTPUT / 'metrics.json', dict(scan=initial, brackets=brackets, comparisons=comparisons,
        reference={n: dict(wheel_assist_j=work(r), duration_s=r['duration_s'], file=str(spread_paths[n])) for n,r in spread.items()},
        all_trials={n: [rows[b] for b in sorted(rows)] for n, rows in trials.items()}))

    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(7.7, 6.2))
    for i, ax in enumerate(axes):
        def ordinate(row):
            return (row['wheel_assist_j']-target)/1000 if i == 0 else row['terminal_speed_error_mps']
        ax.plot([r['beta'] for r in initial], [ordinate(r) for r in initial], color='#7d8d96', label='160-cell scan')
        for feasible, label, color, marker in [(True, 'Feasible finish', '#0c607d', 'o'),
                                               (False, 'Finish-speed miss', '#aa471c', 'x')]:
            chosen = [r for r in initial if r['feasible']==feasible]
            ax.scatter([r['beta'] for r in chosen], [ordinate(r) for r in chosen], color=color, marker=marker, label=label)
        for j, root in enumerate(r for r in comparisons if r['beta'] != 1.):
            ax.scatter(root['beta'], ordinate(root['160']), marker='D', facecolor='white', edgecolor='#3f326d',
                       zorder=4, label='Refined point' if j == 0 else None)
        ax.axhline(0, lw=.8, color='#3a3a3a')
        ax.grid(alpha=.25)
    axes[0].set_title('Bahrain selected schedule at spread wheel work | bahrain-equal-work-001', loc='left')
    axes[0].set_ylabel('Wheel work minus target (kJ)')
    axes[0].legend(fontsize=8, ncols=2)
    axes[1].set(xlabel='Applied multiplier to selected requests', ylabel='Finish-speed error (m/s)')
    fig.tight_layout()
    figures = [FIGURES / f'02_bahrain_selected_work_match.{ext}' for ext in ('png', 'pdf')]
    for p in figures:
        fig.savefig(p, dpi=300)
    plt.close(fig)
    if any(sha(p) != h for p, h in (inputs | code).items()):
        raise ValueError('A bound input changed during the study')
    manifest = dict(inputs=inputs, sources=code, outputs={str(p): sha(p)
        for p in [*sorted(OUTPUT.iterdir()), *figures] if p.is_file() and p.name != Path(__file__).name})
    save(OUTPUT / 'manifest.json', manifest)
    print(json.dumps(dict(hashes=sum(len(x) for x in manifest.values()), probes={n: len(r) for n,r in trials.items()},
                          roots=brackets)), flush=True)


if __name__ == '__main__':
    main()
