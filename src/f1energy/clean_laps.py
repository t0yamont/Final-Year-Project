"""Offline candidate-lap audit from a preserved FastF1 pilot cache."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import statistics
from .telemetry_audit import present, describe_samples

UNITS = {'Speed': 'km/h', 'RPM': 'rev/min', 'nGear': 'gear index',
         'Throttle': 'percent', 'Brake': 'boolean', 'DRS': 'status code',
         'Time': 'timedelta from slice origin', 'SessionTime': 'timedelta from session origin',
         'Date': 'source timestamp'}


def selection(lap):
    exclusions, flags = [], ['weather_not_checked']
    if not present(lap.get('IsAccurate')) or not bool(lap['IsAccurate']):
        exclusions.append('accuracy_not_confirmed')
    if present(lap.get('PitInTime')) or present(lap.get('PitOutTime')):
        exclusions.append('pit_in_or_out')
    if str(lap.get('TrackStatus', '')) != '1':
        exclusions.append('track_not_confirmed_clear')
    if not present(lap.get('Deleted')):
        flags.append('deletion_unknown')
    elif bool(lap['Deleted']):
        exclusions.append('deleted')
    return {'candidate': not exclusions, 'exclusion_reasons': exclusions, 'unresolved_flags': flags,
            'modelling_eligible': False}


def time_quality(seconds):
    finite = [x for x in seconds if x is not None and math.isfinite(x)]
    # Do not bridge missing samples or sort the observations before checking order.
    gaps = [b-a for a,b in zip(seconds, seconds[1:])
            if a is not None and b is not None and math.isfinite(a) and math.isfinite(b)]
    positive = [x for x in gaps if x > 0]
    return {'missing_time_count': len(seconds)-len(finite),
            'nonincreasing_steps': sum(x <= 0 for x in gaps),
            'median_positive_gap_s': statistics.median(positive) if positive else None,
            'maximum_gap_s': max(positive) if positive else None,
            'gaps_over_1s': sum(x > 1 for x in gaps),
            'span_s': finite[-1]-finite[0] if len(finite)>1 else None,
            'gap_threshold_note': '1 second is a diagnostic threshold, not a validated exclusion rule'}


def run(source_run, output):
    import fastf1
    from .cli import sha256, source_record
    source_run, output = Path(source_run).resolve(), Path(output).resolve()
    request = json.loads((source_run/'manifest.json').read_text())['request']
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    # Work only against a copy; original cache and exports remain immutable.
    shutil.copytree(source_run/'cache', output/'cache')
    fastf1.Cache.enable_cache(str(output/'cache'))
    fastf1.Cache.offline_mode(True)
    failures, rows, files = [], [], []
    try:
        session = fastf1.get_session(request['year'], request['round_number'], request['session'], backend='fastf1')
        session.load(telemetry=True, weather=False, messages=False)
        laps = session.laps[session.laps['DriverNumber'].astype(str) == str(request['driver'])]
        if laps.empty:
            raise ValueError('No driver laps in cached session')
        metadata = output/'driver_laps.csv'
        laps.to_csv(metadata,index=False)
        files.append(metadata)
        for _, lap in laps.sort_values('LapNumber').iterrows():
            item = dict(lap_number=int(lap['LapNumber']), **selection(lap))
            item['lap_time_s'] = lap['LapTime'].total_seconds() if present(lap['LapTime']) else None
            if item['candidate']:
                try:
                    car = lap.get_car_data()
                    if car.empty:
                        raise ValueError('Empty car samples')
                    item['channels'] = describe_samples(car.to_dict('records'))
                    seconds = [x.total_seconds() if present(x) else None for x in car['Time']]
                    item['time_quality'] = time_quality(seconds)
                    path = output/f"lap-{item['lap_number']}-car.csv"
                    car.to_csv(path,index=False)
                    files.append(path)
                    item['export_status']='exported'
                except Exception as exc:
                    item['export_status']='failed'
                    failures.append({'lap_number':item['lap_number'],'error':str(exc),'error_type':type(exc).__name__})
            rows.append(item)
    except Exception as exc:
        failures.append({'stage':'session','error':str(exc),'error_type':type(exc).__name__})
    finally:
        fastf1.Cache.offline_mode(False)
    summary = {'status':'partial_failure' if failures else 'completed', 'laps':rows,'failures':failures,
               'candidate_count':sum(r['candidate'] for r in rows), 'driver_lap_count':len(rows),
               'units':UNITS,'interpretation':'Candidate source audit only. Weather/deletion unknowns prevent modelling eligibility; no electrical labels.'}
    path=output/'summary.json'
    path.write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf-8');files.append(path)
    manifest={'schema_version':1,'created_utc':datetime.now(timezone.utc).isoformat(),
              'source_run':str(source_run),'source_manifest_sha256':sha256(source_run/'manifest.json'),
              'request':request,'fastf1_version':fastf1.__version__,'source':source_record(),
              'mode':'offline copied cache; no network','outputs':[{'path':p.name,'sha256':sha256(p)} for p in files]}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return summary

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    result=run(args.source_run,args.output)
    print(json.dumps({k:result[k] for k in ('status','candidate_count','driver_lap_count','failures')},indent=2))
    raise SystemExit(1 if result['failures'] else 0)
