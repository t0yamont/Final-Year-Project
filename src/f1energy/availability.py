"""Schedule catalogue only: never treats source support as verified telemetry."""
from datetime import datetime, timezone
import json
from pathlib import Path


def cohort(year):
    return 'pre_2022' if year < 2022 else ('2022_2025' if year < 2026 else '2026_onward')


def collect(years, fetch):
    records, failures = [], []
    for year in years:
        try:
            # Pin the backend so silent fallback cannot change source semantics.
            events = fetch(year, include_testing=True, backend='fastf1').to_dict('records')
            if not events:
                raise ValueError('empty schedule')
            season = []
            for index, event in enumerate(events):
                for number in range(1, 6):
                    name = event.get(f'Session{number}')
                    if not isinstance(name, str) or name.strip().lower() in ('', 'none', 'nat', 'nan'):
                        continue
                    flag = event.get('F1ApiSupport')
                    # Missing/unknown must not become True through bool(NaN).
                    support = bool(flag) if type(flag).__name__ in ('bool', 'bool_') else None
                    date = event.get(f'Session{number}DateUtc')
                    date = None if date is None or str(date) in ('NaT', 'nan', '') else str(date)
                    season.append(dict(season=year, cohort=cohort(year),
                        event_index=index, round=int(event['RoundNumber']),
                        event=str(event['EventName']), event_format=str(event.get('EventFormat', '')),
                        location=str(event.get('Location', '')), session_number=number,
                        session=name, session_date_utc=date, source_support=support,
                        telemetry_status='not_checked', layout_status='unverified',
                        inclusion_status='pending'))
            if not season:
                raise ValueError('schedule contains no named sessions')
            records.extend(season)
        except Exception as exc:
            failures.append(dict(season=year, status='schedule_error',
                                 error_type=type(exc).__name__, message=str(exc)))
    return records, failures


def run_audit(start, end, output):
    if not 2018 <= start <= end <= datetime.now(timezone.utc).year:
        raise ValueError('season range must be chronological, from 2018 through the current year')
    output = Path(output)
    if output.exists():
        raise FileExistsError(f'output already exists: {output}')
    try:
        import fastf1
    except ImportError as exc:
        raise ValueError('Install requirements-data.txt in the project virtual environment first') from exc
    from .cli import sha256, source_record
    output.mkdir(parents=True, exist_ok=False)
    cache = output / 'cache'
    cache.mkdir()
    fastf1.Cache.enable_cache(str(cache))
    records, failures = collect(range(start, end + 1), fastf1.get_event_schedule)
    catalogue = output / 'catalogue.json'
    catalogue.write_text(json.dumps(dict(records=records, failures=failures), indent=2,
                                   allow_nan=False) + '\n', encoding='utf-8')
    summary = dict(status='partial_failure' if failures else 'completed',
                   sessions_catalogued=len(records), failed_seasons=len(failures),
                   interpretation='Schedule metadata only; no telemetry collected or availability verified.')
    manifest = dict(schema_version=1, created_utc=datetime.now(timezone.utc).isoformat(),
                    command='audit-schedules', requested_seasons=list(range(start, end + 1)),
                    backend='fastf1', include_testing=True, source=source_record(),
                    fastf1_version=fastf1.__version__, summary=summary,
                    outputs=[dict(path=catalogue.name, sha256=sha256(catalogue))])
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return summary
