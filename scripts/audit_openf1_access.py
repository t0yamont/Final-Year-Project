"""Bounded public-source audit, not production ingestion or a clean-lap selector."""
import argparse
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--context', action='store_true', help='Also probe Spain qualifying context endpoints')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cache = Path('work/source-audit-openf1')
    cache.mkdir(parents=True, exist_ok=True)
    records, windows, context = [], [], []
    last_request = 0.0

    def fetch(endpoint, **params):
        nonlocal last_request
        url = requests.Request('GET', 'https://api.openf1.org/v1/' + endpoint,
                               params=params).prepare().url
        key = hashlib.sha256(url.encode()).hexdigest()
        body_path, meta_path = cache / (key + '.json'), cache / (key + '.meta.json')
        if body_path.exists() and meta_path.exists():
            body = body_path.read_bytes()
            meta = json.loads(meta_path.read_text())
            if hashlib.sha256(body).hexdigest() != meta['sha256']:
                raise ValueError('Cache hash mismatch: ' + key)
            record = dict(meta, cache_hit=True)
        else:
            time.sleep(max(0, 2.1 - (time.monotonic() - last_request)))
            last_request = time.monotonic()
            try:
                response = requests.get(url, timeout=(10, 25))
                body = response.content
                record = {'url': url, 'status': response.status_code,
                          'retrieved_utc': datetime.now(timezone.utc).isoformat(),
                          'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
                          'cache_hit': False}
                if response.status_code == 200:
                    body_path.write_bytes(body)
                    meta_path.write_text(json.dumps(record, indent=2))
            except requests.RequestException as exc:
                records.append({'url': url, 'status': 'request_failed',
                                'error_type': type(exc).__name__})
                return []
        records.append(record)
        if record['status'] != 200:
            return []
        try:
            data = json.loads(body)
        except ValueError:
            record['parse_error'] = True
            return []
        if not isinstance(data, list):
            record['unexpected_type'] = type(data).__name__
            return []
        record['rows'] = len(data)
        return data

    sessions = fetch('sessions', year=2025)
    selected = [s for s in sessions if (
        s.get('country_name') == 'Bahrain' and s.get('session_name') == 'Qualifying'
    ) or (
        s.get('country_name') == 'Spain' and
        s.get('session_name') in ('Qualifying', 'Practice 3', 'Race')
    )]
    for session in selected[:4]:
        key = session['session_key']
        laps = fetch('laps', session_key=key, driver_number=1)
        candidates = [lap for lap in laps if lap.get('date_start')
                      and isinstance(lap.get('lap_duration'), (int, float))
                      and 30 < lap['lap_duration'] < 180
                      and lap.get('lap_number', 0) > 1
                      and lap.get('is_pit_out_lap') is False]
        if not candidates:
            windows.append({'session_key': key, 'status': 'no_probe_candidate'})
            continue
        lap = candidates[0]  # Access/schema probe only; not quality acceptance.
        start = datetime.fromisoformat(lap['date_start'])
        end = start + timedelta(seconds=lap['lap_duration'])
        data = fetch('car_data', session_key=key, driver_number=1,
                     **{'date>': (start - timedelta(microseconds=1)).isoformat(),
                        'date<': end.isoformat()})
        dates = [datetime.fromisoformat(d['date']) for d in data if d.get('date')]
        ordered = sorted(set(dates))
        gaps = [(b-a).total_seconds() for a, b in zip(ordered, ordered[1:])]
        windows.append({'session_key': key, 'country': session['country_name'],
                        'session_name': session['session_name'], 'driver_number': 1,
                        'lap_number': lap['lap_number'], 'lap_duration_s': lap['lap_duration'],
                        'rows': len(data), 'duplicate_timestamps': len(dates)-len(ordered),
                        'max_gap_s': max(gaps) if gaps else None,
                        'columns': sorted(set().union(*(d.keys() for d in data))) if data else [],
                        'missing_required_values': {
                            c: sum(d.get(c) is None for d in data)
                            for c in ('date', 'speed', 'rpm', 'n_gear', 'throttle', 'brake', 'drs')},
                        'status': 'access_probe_not_clean_lap_acceptance'})
        print(session['country_name'], session['session_name'], 'rows', len(data), flush=True)
        if args.context and session['country_name'] == 'Spain' and session['session_name'] == 'Qualifying':
            queries = [('drivers', {'session_key': key}),
                       ('stints', {'session_key': key, 'driver_number': 1}),
                       ('weather', {'session_key': key}),
                       ('race_control', {'session_key': key}),
                       ('location', {'session_key': key, 'driver_number': 1,
                                     'date>': (start-timedelta(microseconds=1)).isoformat(),
                                     'date<': end.isoformat()})]
            for endpoint, params in queries:
                rows = fetch(endpoint, **params)
                context.append({'endpoint': endpoint, 'session_key': key, 'rows': len(rows),
                                'columns': sorted(set().union(*(r.keys() for r in rows))) if rows else []})
                print('Context', endpoint, 'rows', len(rows), flush=True)
    summary = {'scope': 'public access and schema probes; no battery labels or clean-lap acceptance',
               'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'session_metadata_rows': len(sessions),
               'meeting_keys': sorted({s['meeting_key'] for s in sessions}),
               'selected_sessions': selected, 'windows': windows, 'context': context, 'requests': records}
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (args.output / 'sessions.json').write_text(json.dumps(sessions, indent=2) + '\n')
    print('Saved audit:', args.output, 'metadata rows:', len(sessions), flush=True)


if __name__ == '__main__':
    main()
