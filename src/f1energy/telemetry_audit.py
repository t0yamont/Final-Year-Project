"""Manual one-session pilot. Source car samples are not verified electrical labels."""
import math
import json
from datetime import datetime, timezone
from pathlib import Path

CHANNELS = ('Speed', 'RPM', 'nGear', 'Throttle', 'Brake', 'DRS', 'Time')


def present(value):
    if value is None or str(value) in ('NaT', 'nan', '<NA>'):
        return False
    return not (isinstance(value, float) and math.isnan(value))


def describe_samples(records):
    """Report missingness without interpolation or silently dropping samples."""
    return {'sample_count': len(records),
            'missing_counts': {key: sum(not present(row.get(key)) for row in records) for key in CHANNELS},
            'electrical_deployment_label': 'not_provided_by_this_pipeline',
            'battery_state_label': 'not_provided_by_this_pipeline',
            'evidence_class': 'source_car_data; source processing may apply'}


def lap_flags(lap):
    reasons = []
    if not present(lap.get('IsAccurate')) or not bool(lap['IsAccurate']):
        reasons.append('accuracy_not_confirmed')
    if present(lap.get('PitInTime')) or present(lap.get('PitOutTime')):
        reasons.append('pit_in_or_out')
    if str(lap.get('TrackStatus', '')) != '1':
        reasons.append('track_status_not_confirmed_clear')
    if not present(lap.get('Deleted')) or bool(lap['Deleted']):
        reasons.append('deletion_status_not_confirmed_valid')
    return reasons


def run_session_audit(year, round_number, session_name, driver, output, max_laps=3):
    if not 2018 <= year <= datetime.now(timezone.utc).year or round_number < 1:
        raise ValueError('Use a season from 2018 through current year and positive race round; testing is separate.')
    if session_name not in ('FP1', 'FP2', 'FP3', 'Q', 'SQ', 'SS', 'S', 'R'):
        raise ValueError('Use an explicit FastF1 session code.')
    if not str(driver).isdigit() or not 1 <= max_laps <= 3:
        raise ValueError('Driver must be a numeric race number; max_laps must be 1 to 3.')
    output = Path(output)
    if output.exists():
        raise FileExistsError(f'Output already exists: {output}')
    try:
        import fastf1
    except ImportError as exc:
        raise ValueError('Install requirements-data.txt first') from exc
    from .cli import sha256, source_record
    output.mkdir(parents=True, exist_ok=False)
    cache = output / 'cache'
    cache.mkdir()
    fastf1.Cache.enable_cache(str(cache))
    import logging
    handler = logging.FileHandler(output / 'fastf1.log', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s'))
    logger = logging.getLogger('fastf1')
    logger.addHandler(handler)
    results, failures, files = [], [], [output / 'fastf1.log']
    try:
        session = fastf1.get_session(year, round_number, session_name, backend='fastf1')
        # FastF1 loads session telemetry before lap slicing: max_laps bounds exports, not download size.
        session.load(telemetry=True, weather=False, messages=False)
        laps = session.laps[session.laps['DriverNumber'].astype(str) == str(driver)]
        if laps.empty:
            raise ValueError('No laps found for requested driver')
        laps_path = output / 'driver_laps.csv'
        laps.to_csv(laps_path, index=False)
        files.append(laps_path)
        for _, lap in laps.sort_values('LapNumber').head(max_laps).iterrows():
            item = {'lap_number': int(lap['LapNumber']), 'quality_flags': lap_flags(lap),
                    'selection': 'first chronological laps; diagnostic, not modelling selection'}
            try:
                samples = lap.get_car_data()
                item.update(describe_samples(samples.to_dict('records')))
                if samples.empty:
                    raise ValueError('Empty car data')
                path = output / f"lap-{item['lap_number']}-car.csv"
                samples.to_csv(path, index=False)
                files.append(path)
                item['status'] = 'exported'
            except Exception as exc:
                item.update(status='failed', error_type=type(exc).__name__, message=str(exc))
                failures.append(dict(item))
            results.append(item)
    except Exception as exc:
        failures.append({'stage': 'session_load_or_selection', 'error_type': type(exc).__name__, 'message': str(exc)})
    logger.removeHandler(handler)
    handler.close()
    summary = {'status': 'partial_failure' if failures else 'completed', 'laps': results, 'failures': failures,
               'interpretation': 'Pilot source audit; no deployment reconstruction or dataset eligibility established.'}
    path = output / 'summary.json'
    path.write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    files.append(path)
    manifest = {'schema_version': 1, 'command': 'audit-session', 'created_utc': datetime.now(timezone.utc).isoformat(),
                'request': dict(year=year, round_number=round_number, session=session_name, driver=str(driver), max_laps=max_laps),
                'fastf1_version': fastf1.__version__, 'source': source_record(),
                'outputs': [{'path': p.name, 'sha256': sha256(p)} for p in files]}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return summary
