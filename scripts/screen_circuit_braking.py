"""Compare braking opportunity from cached, screened 2025 OpenF1 qualifying laps."""
import argparse
from collections import defaultdict
import csv
from datetime import datetime
import gzip
import json
from math import isclose, isfinite
from pathlib import Path
import platform
import shutil
from statistics import median

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from acquire_openf1_dataset import digest, save_json


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def known_brake_intervals(samples, max_gap):
    """Each input sample is (seconds from lap start, m/s, bool or None)."""
    bouts, segment, distance, supported_s, skipped = [], 0, 0.0, 0.0, []
    active = None
    for (t0, v0, b0), (t1, v1, b1) in zip(samples, samples[1:]):
        dt = round(t1 - t0, 9)
        if (not 0 < dt <= max_gap or b0 is None or b1 is None
                or not all(isfinite(v) and v > 0 for v in (v0, v1))):
            skipped.append({'start_s': t0, 'end_s': t1, 'gap_s': dt})
            if active is not None:
                active['right_censored'] = True
                active = None
            segment += 1
            continue
        supported_s += dt
        halfway = (v0 + v1) / 2
        pair_distance = dt * halfway
        if b0 or b1:
            if active is None:
                active = {'segment': segment, 'left_censored': b0, 'right_censored': False,
                          'start_s': t0 if b0 else (t0 + t1) / 2,
                          'start_m': distance if b0 else distance + dt * (v0 + halfway) / 4,
                          'entry_mps': v0 if b0 else halfway}
                bouts.append(active)
            active.update(end_s=t1 if b1 else (t0 + t1) / 2,
                          end_m=distance + (pair_distance if b1 else dt * (v0 + halfway) / 4),
                          exit_mps=v1 if b1 else halfway)
            if not b1:
                active = None
        distance += pair_distance
    if active is not None:
        active['right_censored'] = True
    return bouts, distance, supported_s, skipped


def median_or_none(values):
    return median(values) if values else None


def measure(samples, duration, criteria):
    if (not samples or not isfinite(duration) or duration <= 0
            or not 0 <= samples[0][0] <= samples[-1][0] <= duration
            or any(a[0] >= b[0] for a, b in zip(samples, samples[1:]))):
        raise ValueError('Native lap timestamps missing, out of order, or outside timing boundaries')
    bouts, distance, support, skipped = known_brake_intervals(samples, criteria['maximum_native_pair_gap_s'])
    complete = [b for b in bouts if not b['left_censored'] and not b['right_censored']]
    spacing = [b['start_m'] - a['start_m'] for a, b in zip(complete, complete[1:])
               if a['segment'] == b['segment']]
    brake_s = sum(b['end_s'] - b['start_s'] for b in bouts)
    start_gap, end_gap = samples[0][0], duration - samples[-1][0]
    coverage = support / duration
    missing_s = sum(gap['gap_s'] for gap in skipped)
    if not isclose(support + missing_s + start_gap + end_gap, duration, abs_tol=1e-6):
        raise ValueError('Timed-lap coverage identity failed')
    if not 0 <= brake_s <= support + 1e-6:
        raise ValueError('Brake duration exceeds interval support')
    return {'timed_lap_s': duration, 'native_samples': len(samples), 'leading_gap_s': start_gap,
            'trailing_gap_s': end_gap, 'maximum_native_gap_s': max(
                (round(b[0] - a[0], 9) for a, b in zip(samples, samples[1:])), default=0),
            'excluded_intervals': skipped, 'supported_s': support, 'timed_coverage_fraction': coverage,
            'supported_distance_m': distance, 'eligible': (
                coverage >= criteria['minimum_timed_lap_coverage_fraction']
                and max(start_gap, end_gap) <= criteria['maximum_lap_edge_gap_s'] + 1e-9),
            'brake_duration_s': brake_s, 'brake_share': brake_s / duration, 'complete_bouts': len(complete),
            'censored_bouts': len(bouts) - len(complete), 'complete_bout_speed_loss_mps': sum(
                b['entry_mps'] - b['exit_mps'] for b in complete),
            'onset_spacings_m': spacing, 'median_onset_spacing_m': median_or_none(spacing),
            'median_onset_spacing_fraction': median_or_none([s / distance for s in spacing]), 'bouts': bouts}


def screen_circuit(dataset, spec, role, config, inputs):
    meeting, session_key = spec['meeting_key'], spec['session_key']
    if (role['role'] != spec['role'] or role['role'] not in ('development', 'validation')
            or session_key not in role['session_keys'] or role['season'] != config['season']):
        raise ValueError(f'Frozen role mismatch for {spec}')
    directory = dataset / role['role'] / str(meeting) / str(session_key)
    manifest = directory / 'complete.json'
    session = read(manifest)
    if (session['meeting_key'], session['session_key'], session['role'], session['session_name']) != (
            meeting, session_key, role['role'], config['session_name']):
        raise ValueError(f'Session manifest mismatch in {manifest}')
    inputs[manifest.as_posix()] = digest(manifest)
    if {d['driver_number'] for d in session['drivers']} != set(config['drivers']):
        raise ValueError(f'Qualifying driver roster mismatch in {manifest}')
    laps, counts = [], {}
    for driver in session['drivers']:
        number = driver['driver_number']
        car, audit = (directory / f'driver-{number}-{channel}' for channel in ('car.csv.gz', 'laps.json'))
        for path in (car, audit):
            verified = digest(path)
            if verified != driver['outputs'][path.name]:
                raise ValueError(f'Acquisition integrity failure for {path}')
            inputs[path.as_posix()] = verified
        all_laps = read(audit)
        accepted = {r['lap_number']: r for r in all_laps if r['conditional_motion_candidate']}
        starts = {lap: datetime.fromisoformat(row['lap_start_utc']) for lap, row in accepted.items()}
        samples = defaultdict(list)
        with gzip.open(car, 'rt', encoding='utf-8', newline='') as handle:
            for row in csv.DictReader(handle):
                lap = int(row['lap_number']) if row['lap_number'] else None
                if lap in accepted:
                    if tuple(map(int, (row['meeting_key'], row['session_key'], row['driver_number']))) != (
                            meeting, session_key, number):
                        raise ValueError(f'Native stream mismatch in {car}')
                    elapsed = (datetime.fromisoformat(row['date_utc']) - starts[lap]).total_seconds()
                    speed = float(row['speed_mps']) if row['speed_mps'] else float('nan')
                    brake = {'True': True, 'False': False}.get(row['brake'])
                    samples[lap].append((elapsed, speed, brake))
        counts[str(number)] = {'acquisition_lap_entries': len(all_laps), 'conditional_candidates': len(accepted)}
        for lap, audit_row in sorted(accepted.items()):
            duration = (datetime.fromisoformat(audit_row['lap_end_utc']) - starts[lap]).total_seconds()
            laps.append(dict(spec, driver_number=number, lap_number=lap,
                             **measure(samples[lap], duration, config['selection'])))
    return laps, counts


def summarise(laps, counts, minimum):
    summary = {}
    for driver, count in counts.items():
        eligible = [lap for lap in laps if lap['driver_number'] == int(driver) and lap['eligible']]
        stats = {}
        for key in ('brake_duration_s', 'brake_share', 'complete_bouts', 'complete_bout_speed_loss_mps',
                    'median_onset_spacing_m', 'median_onset_spacing_fraction', 'timed_coverage_fraction'):
            stats[key] = median_or_none([lap[key] for lap in eligible if lap[key] is not None])
        summary[driver] = dict(count, eligible_laps=[lap['lap_number'] for lap in eligible],
                               coverage_pass=len(eligible) >= minimum, medians=stats)
    return summary


def assess(candidate, reference, criteria):
    differences = {}
    for driver, lap_stats in candidate.items():
        a, b = lap_stats['medians'], reference[driver]['medians']
        share = a['brake_share'] - b['brake_share'] if a['brake_share'] is not None else None
        x, y = a['median_onset_spacing_fraction'], b['median_onset_spacing_fraction']
        differences[driver] = {'brake_share_difference': share,
                               'relative_spacing_difference': x / y - 1 if x is not None and y else None}
    passes = {}
    for key, threshold in [('brake_share_difference', criteria['minimum_brake_share_difference_fraction']),
                           ('relative_spacing_difference', criteria['minimum_spacing_relative_difference_fraction'])]:
        deltas = [driver[key] for driver in differences.values()]
        passes[key] = None not in deltas and (min(deltas) >= threshold or max(deltas) <= -threshold)
    coverage_pass = all(stats['coverage_pass'] for stats in candidate.values())
    return {'differences_from_bahrain': differences, 'contrast_pass_by_metric': passes,
            'coverage_pass': coverage_pass, 'passes_selection_rule': coverage_pass and any(passes.values())}


def check_interval_math():
    samples = [(0, 20, True), (.5, 16, False), (1, 14, True), (1.5, 12, False),
               (2, 10, True), (3, 8, True), (3.5, 6, False)]
    bouts, distance, support, skipped = known_brake_intervals(samples, .5)
    assert [b['left_censored'] for b in bouts] == [True, False, False, True]
    assert [b['right_censored'] for b in bouts] == [False, False, True, False]
    assert [b['segment'] for b in bouts] == [0, 0, 0, 1] and len(skipped) == 1
    assert isclose(distance, 32) and isclose(support, 2.5)
    assert bouts[1]['entry_mps'] - bouts[1]['exit_mps'] == 2
    assert bouts[1]['end_s'] - bouts[1]['start_s'] == .5


def evaluate(config, inputs):
    criteria = config['selection']
    role_path, dataset = Path(config['roles']), Path(config['dataset'])
    role_contract = read(role_path)
    roles = {e['meeting_key']: e for e in role_contract['event_roles']}
    inputs[role_path.as_posix()] = digest(role_path)
    contract, plan = dataset / 'contract.json', dataset / 'plan.json'
    inputs.update({p.as_posix(): digest(p) for p in (contract, plan)})
    if (role_contract['frozen_plan_sha256'] != inputs[plan.as_posix()]
            or read(contract)['plan_sha256'] != inputs[plan.as_posix()]):
        raise ValueError('Cached acquisition plan differs from the frozen roles')
    reference = config['reference']['circuit']
    all_laps, summaries, decisions = [], {}, {}
    for spec in [config['reference'], *config['candidates_in_order']]:
        laps, counts = screen_circuit(dataset, spec, roles[spec['meeting_key']], config, inputs)
        all_laps.extend(laps)
        summaries[spec['circuit']] = summarise(laps, counts, criteria['minimum_laps_per_driver'])
    reference_pass = all(d['coverage_pass'] for d in summaries[reference].values())
    if reference_pass:
        for spec in config['candidates_in_order']:
            decisions[spec['circuit']] = assess(summaries[spec['circuit']], summaries[reference], criteria)
    coverage = {name: {driver: row['eligible_laps'] for driver, row in rows.items()}
                for name, rows in summaries.items()}
    chosen = next((spec for spec in config['candidates_in_order']
                   if decisions.get(spec['circuit'], {}).get('passes_selection_rule')), None)
    return chosen, decisions, reference_pass, coverage, summaries, all_laps


def plot_laps(laps, summaries, stage, figure_directory):
    figure_directory.mkdir(parents=True, exist_ok=False)
    figure, axes = plt.subplots(1, 3, figsize=(12, 4.6))
    axes_data = [('brake_duration_s', 'Brake-on time (s)'),
                 ('complete_bout_speed_loss_mps', 'Summed speed loss (m/s)'),
                 ('median_onset_spacing_m', 'Median onset spacing (m)')]
    driver_styles = {1: (-.14, '#185c83', 'o'), 22: (.14, '#965018', 's')}
    for axis, (key, label) in zip(axes, axes_data):
        for location, (circuit, drivers) in enumerate(summaries.items()):
            for number, (offset, color, marker) in driver_styles.items():
                values = [lap[key] for lap in laps if lap['circuit'] == circuit and lap['eligible']
                          and lap['driver_number'] == number and lap[key] is not None]
                xs = [location + offset + .036 * (i - (len(values) - 1) / 2) for i in range(len(values))]
                axis.scatter(xs, values, marker=marker, s=30, color=color, alpha=.68, zorder=3)
                middle = drivers[str(number)]['medians'][key]
                if middle is not None:
                    axis.hlines(middle, location + offset - .10, location + offset + .10, color=color, lw=1.8)
        axis.set_ylabel(label)
        axis.set_xticks(range(len(summaries)), list(summaries), rotation=20, ha='right')
        axis.set_xlim(-.42, len(summaries) - .58)
        axis.set_axisbelow(True)
        axis.grid(axis='y', color='#e4e8ec')
        axis.spines[['top', 'right']].set_visible(False)
    drivers = [Line2D([], [], color=color, marker=marker, label=f'Driver {number}', markersize=5)
               for number, (_, color, marker) in driver_styles.items()]
    figure.legend(handles=drivers, loc='upper right', bbox_to_anchor=(.98, .975), ncol=2, frameon=False)
    figure.text(.07, .92, 'Observed braking in 2025 qualifying', fontsize=15, weight='bold')
    figure.text(.07, .065, 'Markers show eligible native laps and lines show driver medians. '
                           'Speed loss and onset spacing use complete bouts only.', fontsize=9)
    if stage != 'primary':
        figure.text(.07, .028, 'Exploratory coverage rule. Hungary driver 22 has one eligible lap.', fontsize=9)
    figure.subplots_adjust(left=.075, right=.98, bottom=.23, top=.81, wspace=.35)
    stem = figure_directory / '01_qualifying_braking'
    figure.savefig(stem.with_suffix('.png'), dpi=300)
    figure.savefig(stem.with_suffix('.pdf'), metadata={'CreationDate': None, 'ModDate': None})
    plt.close(figure)
    metadata = {'run_id': 'circuit-braking-screen-001', 'stage': stage, 'png_dpi': 300,
                'title': 'Observed braking in 2025 qualifying',
                'caption': ('Native OpenF1 qualifying car observations for Red Bull Racing drivers 1 and 22. '
                            'Each point represents one eligible lap. Horizontal lines mark driver medians. '
                            'Summed entry-minus-exit speed loss and median onset-to-onset distance use complete '
                            'bouts only. Spacing excludes transitions across gaps and the timing line. '
                            'Binary brake observations describe braking opportunity. Electrical delivery and '
                            'battery recovery are unobserved.')}
    save_json(figure_directory / 'metadata.json', metadata)
    return sorted(figure_directory.iterdir())


def main(args):
    check_interval_math()
    config = read(args.config)
    primary_archive = read(args.primary_config)
    if primary_archive != {k: v for k, v in config.items() if k != 'exploratory_coverage_after_primary_failure'}:
        raise ValueError('Primary protocol changed when introducing the exploratory coverage rule')
    inputs = {args.config.as_posix(): digest(args.config)}
    chosen, decisions, reference_pass, coverage, summaries, all_laps = evaluate(config, inputs)
    primary = {'original_protocol_sha256': digest(args.primary_config), 'reference_pass': reference_pass,
               'eligible_laps_by_driver': coverage, 'decisions': decisions,
               'selected_circuit': chosen['circuit'] if chosen else None}
    stage = 'primary'
    if not reference_pass:
        stage = 'exploratory_after_primary_coverage_failure'
        updated = config['selection'] | config['exploratory_coverage_after_primary_failure']
        chosen, decisions, reference_pass, coverage, summaries, all_laps = evaluate(
            dict(config, selection=updated), inputs)
    selection = {'selected_circuit': None, 'protocol': config['protocol_id'],
                 'protocol_sha256': digest(args.config), 'stage': stage, 'primary': primary,
                 'reference_pass': reference_pass, 'decisions': decisions}
    if chosen is not None:
        selection.update(selected_circuit=chosen['circuit'], role=chosen['role'], meeting_key=chosen['meeting_key'],
                         session_key=chosen['session_key'], laps_by_driver={d: a['eligible_laps'] for d, a in
                                                                          summaries[chosen['circuit']].items()})
    args.output.mkdir(parents=True, exist_ok=False)
    archive = args.output / 'protocol_primary.json'
    shutil.copyfile(args.primary_config, archive)
    save_json(args.output / 'selection.json', selection)
    save_json(args.output / 'metrics.json', {'stage': stage, 'drivers_by_circuit': summaries, 'lap_metrics': all_laps})
    figure_files = plot_laps(all_laps, summaries, stage, args.figures)
    sources = ['scripts/screen_circuit_braking.py', 'scripts/acquire_openf1_dataset.py', 'src/f1energy/openf1.py']
    generated = [*sorted(args.output.iterdir()), *figure_files]
    save_json(args.output / 'manifest.json', {'run_id': 'circuit-braking-screen-001', 'inputs': inputs,
              'sources': {p: digest(p) for p in sources}, 'outputs': {p.as_posix(): digest(p) for p in generated},
              'environment': {'python': platform.python_version(), 'matplotlib': matplotlib.__version__},
              'checks': ['synthetic midpoint, speed-loss, multi-segment and edge-censor arithmetic',
                         'frozen roles and plan matches', 'acquisition output hashes, session and driver identities',
                         'native timestamp ordering and lap bounds, timed-lap coverage and brake-time identities']})
    print(json.dumps(selection, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path('configs/circuit_braking_screen.json'))
    parser.add_argument('--primary-config', type=Path,
                        default=Path('results/circuit-braking-screen-001/protocol_primary.json'))
    parser.add_argument('--output', type=Path, default=Path('results/circuit-braking-screen-001'))
    parser.add_argument('--figures', type=Path, default=Path('figures/dissertation/circuit-braking-screen-v1'))
    main(parser.parse_args())
