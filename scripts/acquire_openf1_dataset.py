"""Resumable, role-preserving OpenF1 acquisition; no model fitting or test scoring."""
import argparse
import csv
import gzip
import hashlib
import json
import os
import platform
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from f1energy.openf1 import OpenF1Client, OpenF1Error, align_laps, lap_bounds


class BudgetReached(RuntimeError):
    pass


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_bytes((json.dumps(value, indent=2, allow_nan=False) + '\n').encode())
    os.replace(temp, path)


def verify_outputs(directory, record):
    for name, expected in record['outputs'].items():
        if digest(directory / name) != expected:
            raise ValueError(f'Output integrity failure: {directory / name}')


def write_csv_gz(path, rows):
    fields = sorted(set().union(*(r.keys() for r in rows))) if rows else ['date_utc']
    with gzip.open(path, 'wt', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def screening(item, max_gap):
    """Conservative conditional motion screen; does not certify dry/clear/valid."""
    qc, context, lap = item['qc'], item['context'], item['lap']
    reasons = []
    if not qc.get('passed'):
        reasons.append('native_motion_qc_failed')
    gap = qc.get('maximum_positive_gap_s')
    if gap is None or gap > max_gap:
        reasons.append('gap_missing_or_over_limit')
    if any(qc.get(name) is None or qc[name] > max_gap
           for name in ('leading_gap_s', 'trailing_gap_s')):
        reasons.append('lap_edge_coverage_missing_or_over_limit')
    if lap.get('is_pit_out_lap') is not False:
        reasons.append('pit_out_or_unknown')
    if context.get('pit_status') == 'pit_activity_reported':
        reasons.append('pit_activity_reported')
    if context.get('track_status') == 'flag_reported':
        reasons.append('flag_reported')
    if context.get('validity_status') == 'deletion_reported':
        reasons.append('deletion_reported')
    if context.get('weather_start_status') != 'matched':
        reasons.append('weather_missing_stale_or_ambiguous')
    if context.get('rainfall_summary') != 'no_rain_reported_at_samples':
        reasons.append('rain_reported_or_unknown')
    if context.get('stint_status') != 'assigned':
        reasons.append('stint_unknown_or_ambiguous')
    stint = context.get('stint') or {}
    if stint.get('compound') not in ('SOFT', 'MEDIUM', 'HARD'):
        reasons.append('wet_or_unknown_tyre_compound')
    return {'conditional_motion_candidate': not reasons, 'screening_exclusions': reasons,
            'verified_clean_lap': False, 'dry_track_verified': False,
            'remaining_limitations': ['approximate_lap_boundaries', 'unverified_full_flag_and_pit_history',
                                      'unknown_fuel_setup_traffic', 'no_electrical_labels']}


def run(args):
    root = Path(__file__).resolve().parents[1]
    plan = json.loads(args.plan.read_text())
    catalogue_path = root / plan['session_catalogue_path']
    if digest(catalogue_path) != plan['session_catalogue_sha256']:
        raise ValueError('Frozen catalogue hash mismatch')
    sessions = {s['session_key']: s for s in json.loads(catalogue_path.read_text())}
    contract = {'plan_sha256': digest(args.plan), 'catalogue_sha256': digest(catalogue_path),
                'implementation': {str(p.relative_to(root)): digest(p) for p in
                                   [Path(__file__).resolve(), root/'src/f1energy/openf1.py']},
                'python': platform.python_version()}
    if args.output.exists():
        if not args.resume:
            raise FileExistsError('Use --resume for an existing run')
        if json.loads((args.output/'contract.json').read_text()) != contract:
            raise ValueError('Resume requires unchanged plan, catalogue, implementation and Python')
    else:
        if args.resume:
            raise FileNotFoundError('Resume output does not exist')
        args.output.mkdir(parents=True)
        save_json(args.output/'contract.json', contract)
        save_json(args.output/'plan.json', plan)
    client = OpenF1Client(root/'work/source-audit-openf1', offline=args.offline)
    start = time.monotonic()
    invocation = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    events = [e for e in plan['events'] if not args.meeting or e['meeting_key'] in args.meeting]
    jobs = [(e, sessions[k]) for e in events for k in e['session_keys']
            if sessions[k]['session_name'] not in plan['exclude_session_names']
            and (not args.session or k in args.session)]
    failures, completed_sessions, stop = [], 0, None

    def fetch(endpoint, **params):
        if time.monotonic()-start > args.max_minutes*60:
            raise BudgetReached('wall_time_budget')
        if sum(not r.get('cache_hit') for r in client.records) >= args.max_requests:
            raise BudgetReached('network_request_budget')
        return client.fetch(endpoint, **params)

    try:
        for event, session in jobs:
            if args.max_sessions and completed_sessions >= args.max_sessions:
                stop = 'session_limit'
                break
            key = session['session_key']
            directory = args.output/event['role']/str(event['meeting_key'])/str(key)
            directory.mkdir(parents=True, exist_ok=True)
            completed_file = directory/'complete.json'
            if completed_file.exists():
                done = json.loads(completed_file.read_text())
                verify_outputs(directory, done)
                print(f'SKIP {event["name"]} {session["session_name"]}: verified completed session', flush=True)
                continue
            print(f'START {event["role"]} {event["name"]} {session["session_name"]}', flush=True)
            session_request_start = len(client.records)
            try:
                drivers = fetch('drivers', session_key=key)
                reference = next((d for d in drivers if d.get('driver_number') == plan['primary_driver_number']), None)
                team = reference.get('team_name') if reference else plan.get('reference_team_name')
                if not team:
                    raise ValueError('Reference team cannot be resolved')
                selected = [d for d in drivers if d.get('team_name') == team]
                if not selected:
                    raise ValueError('No entries for reference team')
                context = {endpoint: fetch(endpoint, session_key=key)
                           for endpoint in ['weather', 'race_control', 'stints', 'pit']}
                save_json(directory/'context.json', {'session': session, 'drivers': drivers,
                          'selected_team': team, 'primary_driver_present': reference is not None, **context})
                driver_records = []
                for driver in selected:
                    number = driver['driver_number']
                    driver_file = directory/f'driver-{number}-complete.json'
                    if driver_file.exists():
                        record = json.loads(driver_file.read_text())
                        verify_outputs(directory, record)
                        driver_records.append(record)
                        continue
                    laps = fetch('laps', session_key=key, driver_number=number)
                    bounds = [b for b in (lap_bounds(l) for l in laps) if b]
                    if not bounds:
                        raise ValueError(f'No usable lap intervals for driver {number}')
                    first, last = min(b[0] for b in bounds), max(b[1] for b in bounds)
                    car, position = [], []
                    cursor = first
                    while cursor < last:
                        end = min(last, cursor+timedelta(minutes=plan['time_chunk_minutes']))
                        params = {'session_key': key, 'driver_number': number,
                                  'date>': (cursor-timedelta(microseconds=1)).isoformat(),
                                  'date<': end.isoformat()}
                        car.extend(fetch('car_data', **params))
                        if session['session_name'] == 'Qualifying':
                            position.extend(fetch('location', **params))
                        cursor = end
                    if not car:
                        raise ValueError(f'No car telemetry in resolved windows for driver {number}')
                    aligned = align_laps(laps, car, weather=context['weather'], stints=context['stints'],
                                         pit=context['pit'], race_control=context['race_control'],
                                         max_weather_age_s=plan['weather_max_age_s'],
                                         max_lap_overlap_s=plan['maximum_lap_overlap_s'])
                    output_car, audit = [], []
                    for item in aligned:
                        sample_rows = item.pop('samples')
                        output_car.extend(dict(row, lap_number=item['lap_number']) for row in sample_rows)
                        item.update(screening(item, plan['maximum_gap_s']))
                        audit.append(item)
                    names = [f'driver-{number}-laps.json', f'driver-{number}-car.csv.gz']
                    save_json(directory/names[0], audit)
                    write_csv_gz(directory/names[1], output_car)
                    if session['session_name'] == 'Qualifying':
                        names.append(f'driver-{number}-position.csv.gz')
                        write_csv_gz(directory/names[-1], position)
                    record = {'driver_number': number, 'driver_name': driver.get('full_name'),
                              'team': team, 'lap_count': len(laps), 'native_car_rows': len(car),
                              'aligned_car_rows': len(output_car), 'position_rows': len(position),
                              'motion_qc_pass_laps': sum(i['qc']['passed'] for i in audit),
                              'conditional_motion_candidates': sum(i['conditional_motion_candidate'] for i in audit),
                              'exclusion_counts': dict(Counter(r for i in audit for r in i['screening_exclusions'])),
                              'outputs': {name: digest(directory/name) for name in names}}
                    save_json(driver_file, record)
                    driver_records.append(record)
                    print(f'  driver {number}: {len(laps)} laps, {len(car)} source car samples, '
                          f'{record["conditional_motion_candidates"]} conditional candidates', flush=True)
                save_json(directory/'requests.json', client.records[session_request_start:])
                done = {'session_key': key, 'meeting_key': event['meeting_key'], 'event': event['name'],
                        'role': event['role'], 'session_name': session['session_name'], 'drivers': driver_records,
                        'completed_utc': datetime.now(timezone.utc).isoformat(),
                        'outputs': {p.name:digest(p) for p in directory.iterdir()
                                    if p.is_file() and p.name not in ('complete.json',) and not p.name.endswith('.tmp')}}
                save_json(completed_file, done)
                completed_sessions += 1
                print(f'DONE {event["name"]} {session["session_name"]}', flush=True)
            except (OpenF1Error, ValueError, OSError) as exc:
                error = {'session_key': key, 'event':event['name'], 'type':type(exc).__name__, 'message':str(exc)}
                failures.append(error)
                print('FAILED', json.dumps(error), flush=True)
    except BudgetReached as exc:
        stop = str(exc)
        print('CHECKPOINT', stop, flush=True)
    finally:
        save_json(args.output/f'invocation-{invocation}.json',
                  {'utc': invocation, 'elapsed_s': time.monotonic()-start,
                   'requests': client.records, 'failures': failures, 'stop':stop})
        completed = [json.loads(p.read_text()) for p in args.output.glob('*/*/*/complete.json')]
        all_jobs = [(e,k) for e in plan['events'] for k in e['session_keys']
                    if sessions[k]['session_name'] not in plan['exclude_session_names']]
        expected = {k for _, k in all_jobs}
        present = {s['session_key'] for s in completed}
        save_json(args.output/'coverage.json', {'plan_id':plan['plan_id'], 'expected_sessions':len(expected),
                  'completed_sessions':len(completed), 'pending_session_keys':sorted(expected-present),
                  'scope':'Acquisition and screening only; no model evaluation',
                  'native_car_rows':sum(d['native_car_rows'] for s in completed for d in s['drivers']),
                  'lap_count':sum(d['lap_count'] for s in completed for d in s['drivers']),
                  'conditional_motion_candidates':sum(d['conditional_motion_candidates'] for s in completed for d in s['drivers']),
                  'sessions':completed})
    return 1 if failures else 0


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,default=Path('configs/openf1_dataset_plan.json'))
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--resume',action='store_true')
    p.add_argument('--offline',action='store_true')
    p.add_argument('--meeting',type=int,nargs='*')
    p.add_argument('--session',type=int,nargs='*')
    p.add_argument('--max-sessions',type=int,default=0)
    p.add_argument('--max-minutes',type=float,default=45)
    p.add_argument('--max-requests',type=int,default=800)
    a=p.parse_args()
    if a.max_minutes<=0 or a.max_requests<1 or a.max_sessions<0:
        p.error('Budgets must be positive; max-sessions may be zero for all')
    raise SystemExit(run(a))
