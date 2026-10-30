"""Plot saved synthetic event DP comparisons, retaining the rejected first grid."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, NullLocator
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    inputs = [ROOT/'results/event-baselines-001/metrics.json', ROOT/'results/event-baselines-003/metrics.json']
    for path in inputs:
        m = json.loads((path.parent/'manifest.json').read_text())
        if sha(path) != m['outputs_sha256'][path.name]:
            raise ValueError('saved result hash mismatch')
    initial, refined = [json.loads(p.read_text()) for p in inputs]
    args.output.mkdir(parents=True, exist_ok=False)
    files = []
    def save(fig, name):
        for ext in ('png', 'pdf'):
            path = args.output/f'{name}.{ext}'
            fig.savefig(path, dpi=300, bbox_inches='tight')
            files.append(path)
        plt.close(fig)

    labels = [('zero', 'Zero'), ('half', 'Half'), ('full', 'Full'),
              ('dp_2500J', 'DP: 2.5 kJ, 5 actions'), ('exhaustive', 'Exhaustive: 5 actions'),
              ('exhaustive_nine_actions', 'Exhaustive: 9 actions'),
              ('ppo_seed0', 'PPO seed 0'), ('ppo_seed1', 'PPO seed 1'), ('ppo_seed2', 'PPO seed 2')]
    fig, axs = plt.subplots(1, 2, figsize=(13, 5.5), layout='constrained')
    for ax, name, title in zip(axs, ['nominal_development', 'new_predeclared_evaluation'], ['Nominal development', 'Previously frozen evaluation']):
        rows = initial['cases'][name]['results']
        times = [rows[k]['elapsed_s'] for k, _ in labels]
        ax.scatter(times, range(len(labels)), c=['#677f96']*3+['#ce7c22']*3+['#3d8e79']*3)
        ax.set_yticks(range(len(labels)), [v for _, v in labels])
        ax.invert_yaxis()
        lo, hi = min(times), max(times)
        ax.set_xlim(lo-.04*(hi-lo), hi+.20*(hi-lo))
        for i, value in enumerate(times):
            ax.annotate(f'{value:.4f}', (value, i), xytext=(5, 0), textcoords='offset points', va='center', fontsize=8)
        ax.set(xlabel='Feasible elapsed time (s)', title=title)
        ax.grid(axis='x', alpha=.2)
    fig.suptitle('Synthetic event model: shared physics, finite-action references and saved PPO pilots')
    save(fig, '01_event_dp_ppo_comparison')

    fig, axs = plt.subplots(1, 3, figsize=(13, 4.8), layout='constrained')
    for ax, name, title in zip(axs, ['nominal_development', 'new_predeclared_evaluation', 'four_segment_development'], ['Nominal: 5 actions', 'Evaluation: 5 actions', 'Four segments: 3 actions']):
        case = refined['cases'][name] if name == 'four_segment_development' else initial['cases'][name]
        rows = case['results']
        reference = rows['exhaustive']['elapsed_s']
        dps = [r for label, r in rows.items() if label.startswith('dp_')]
        x = [r['energy_step_j']/1000 for r in dps]
        ax.plot(x, [(r['elapsed_s']-reference)*1000 for r in dps], 'o-', label='Original-state replay')
        ax.plot(x, [(r['grid_objective_s']-reference)*1000 for r in dps], 's--', label='Rounded DP objective', alpha=.8)
        ax.axhline(0, color='black', linewidth=.8)
        ax.set_xscale('log'); ax.invert_xaxis()
        ax.xaxis.set_major_locator(FixedLocator(x)); ax.xaxis.set_minor_locator(NullLocator())
        ax.set_xticks(x, [f'{v:g}' for v in x], rotation=45)
        ax.set(xlabel='Energy-grid step (kJ), coarse to fine', ylabel='Difference from matching finite-action reference (ms)', title=title)
        ax.grid(alpha=.2)
    axs[0].legend(fontsize=8)
    fig.suptitle('Synthetic DP energy refinement: policy selection need not improve monotonically')
    save(fig, '02_event_dp_refinement')

    rows = refined['cases']['four_segment_development']['results']
    selected = [('full', 'Full'), ('half', 'Half'), ('dp_20000J', 'DP 20 kJ'), ('dp_2500J', 'DP 2.5 kJ'), ('dp_100J', 'DP 0.1 kJ'), ('exhaustive', 'Exhaustive')]
    values = np.array([rows[k]['actions'] for k, _ in selected])
    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 5), width_ratios=(1.3, 1), layout='constrained')
    heat = left.imshow(values, vmin=0, vmax=1, cmap='Blues', aspect='auto')
    left.set_xticks(range(4), ['1: 120 m', '2: 280 m', '3: 160 m', '4: 240 m'])
    left.set_yticks(range(len(selected)), [v for _, v in selected]); left.set_xlabel('Physical segment')
    for y in range(values.shape[0]):
        for x in range(values.shape[1]):
            left.text(x, y, f'{values[y,x]:g}', ha='center', va='center', color='white' if values[y,x]>.5 else 'black')
    fig.colorbar(heat, ax=left, label='Requested electrical deployment fraction')
    ref = rows['exhaustive']['elapsed_s']
    gaps = [(rows[k]['elapsed_s']-ref)*1000 for k, _ in selected]
    right.scatter(gaps, range(len(selected)), color='#b66a24')
    right.set_yticks(range(len(selected)), [v for _, v in selected]); right.invert_yaxis()
    for i, gap in enumerate(gaps):
        right.annotate(f'{gap:.3f}', (gap, i), xytext=(5, 0), textcoords='offset points', va='center', fontsize=8)
    right.set_xlim(-3, max(gaps)*1.22)
    right.set_xlabel('Replay gap to 81-sequence reference (ms)'); right.grid(axis='x', alpha=.2)
    fig.suptitle('Four-segment synthetic development case: allocation and feasible replay')
    save(fig, '03_event_allocation')

    captions = args.output/'captions.md'
    captions.write_text('''# Event-model DP figures — 30 October 2026

01: Two synthetic pilot scenarios, with all methods sharing vehicle, event integration, energy reserve and terminal constraints within each panel. DP uses a 2.5 kJ energy grid and five actions; exhaustive references enumerate 25 or 81 two-segment action sequences. PPO points are the three saved 4,096-step seeds, replayed without retraining or selection. A finite-action reference is not a continuous optimum. The evaluation scenario has been inspected and is not an untouched final test. Dot-plot time axes are intentionally restricted. Do not compare these times with another physical model or real lap.

02: Energy-grid refinement with the action set held fixed. The four-segment run001 failed its finest-grid agreement threshold: replay at 2.5 kJ missed the 81-sequence reference by 1.061924 ms, despite 5 kJ selecting that reference. The documented follow-up adds 1/0.5/0.25/0.1 kJ grids. Rounded objectives are not asserted to be bounds on physical replay; plotted lines connect discrete grid experiments, not confidence intervals. The follow-up was motivated by the failed development result and is not independent confirmation.

03: Requested actions and elapsed-time gaps for the four-segment synthetic case. Electrical power ceases at reserve or during braking, so a requested fraction is not a measured power history. DP at 0.1 kJ and exhaustive search select the same finite-grid policy. No PPO result exists for this scenario. The scene is an open synthetic 800 m path, not a calibrated circuit, and the three-action optimum does not prove continuous-action convergence.

Source runs: event-baselines-001 (original rejected grid study, including valid individual two-segment checks) and event-baselines-003 (stress refinement with corrected evaluated-case metadata). Run002 has identical numerical results to run003 but its generic scope sentence incorrectly referred to three cases; actual payload contains only the stress case. All runs are preserved. Saved transitions were verified and reused; solve timings with different cache warmth are not independent computational-cost rankings.
''', encoding='utf-8')
    files.append(captions)
    (args.output/'manifest.json').write_text(json.dumps(dict(inputs_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in inputs},
        source_sha256={Path(__file__).relative_to(ROOT).as_posix(): sha(Path(__file__))}, matplotlib_version=matplotlib.__version__,
        outputs_sha256={p.name: sha(p) for p in files}), indent=2)+'\n')
    print(args.output)


if __name__ == '__main__':
    main()
