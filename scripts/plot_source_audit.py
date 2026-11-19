"""Plot timestamp gaps from immutable OpenF1 access probes, without re-fetching."""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    summary = json.loads(args.input.read_text())
    inputs = {str(args.input): hashlib.sha256(args.input.read_bytes()).hexdigest()}
    records = [r for r in summary['requests'] if '/car_data?' in r['url']]
    assert len(records) == len(summary['windows']) == 4
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 6.8), sharey=True)
    for ax, window, record in zip(axes.flat, summary['windows'], records):
        assert record['status'] == 200
        key = hashlib.sha256(record['url'].encode()).hexdigest()
        path = Path('work/source-audit-openf1') / (key + '.json')
        body = path.read_bytes()
        assert hashlib.sha256(body).hexdigest() == record['sha256']
        inputs[str(path)] = record['sha256']
        data = json.loads(body)
        times = sorted(set(datetime.fromisoformat(row['date']) for row in data))
        gaps = [(b-a).total_seconds() for a, b in zip(times, times[1:])]
        elapsed = [(t-times[0]).total_seconds() for t in times[1:]]
        assert len(data) == window['rows'] and abs(max(gaps)-window['max_gap_s']) < 1e-9
        ax.plot(elapsed, gaps, linewidth=.75, color='#176b8a')
        ax.axhline(1, color='#a64723', linestyle='--', linewidth=1)
        ax.set_title(f"{window['country']} | {window['session_name']} | lap {window['lap_number']}", fontsize=10)
        ax.text(.98, .94, f"{len(data)} samples; max gap {max(gaps):.3f} s",
                transform=ax.transAxes, ha='right', va='top', fontsize=9)
        ax.set_xlabel('Elapsed time from first retrieved sample (s)', fontsize=9)
        ax.set_ylabel('Adjacent timestamp gap (s)', fontsize=9)
        ax.set_ylim(0, 1.35)
        ax.grid(axis='y', alpha=.2)
    fig.suptitle('OpenF1 access audit: irregular sampling in four 2025 lap windows', fontsize=13)
    fig.text(.5, .025, 'Driver 1; illustrative access probes, not accepted clean laps. Dashed line: existing 1 s gap-screen reference.',
             ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .05, 1, .95))
    outputs = {}
    for suffix in ('png', 'pdf'):
        path = args.output / ('01_openf1_sampling.' + suffix)
        fig.savefig(path, dpi=300)
        outputs[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    plt.close(fig)
    manifest = {'source_run': str(args.input.parent), 'inputs': inputs, 'outputs': outputs,
                'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'scope': 'Timestamp gaps only; no lap-quality acceptance, battery labels or independent-source validation'}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Verified input hashes and gap statistics; saved PNG/PDF:', args.output)


if __name__ == '__main__':
    main()
