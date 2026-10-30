"""Single-session weather/messages enrichment; does not establish a dry track."""
import argparse
import json
import logging
from pathlib import Path
import shutil
from datetime import datetime, timezone
from .telemetry_audit import present


def run(source_run, output):
    import fastf1
    from .cli import sha256, source_record
    source_run, output=Path(source_run).resolve(),Path(output).resolve()
    request=json.loads((source_run/'manifest.json').read_text())['request']
    output.mkdir(parents=True,exist_ok=False)
    shutil.copytree(source_run/'cache',output/'cache')
    fastf1.Cache.enable_cache(str(output/'cache'))
    handler=logging.FileHandler(output/'fastf1.log',encoding='utf-8')
    handler.setLevel(logging.DEBUG)
    logger=logging.getLogger('fastf1');logger.addHandler(handler)
    files,failures,contexts=[],[],[]
    try:
        session=fastf1.get_session(request['year'],request['round_number'],request['session'],backend='fastf1')
        session.load(telemetry=False,weather=True,messages=True)
        weather=session.weather_data
        messages=session.race_control_messages
        laps=session.laps[session.laps['DriverNumber'].astype(str)==str(request['driver'])]
        for name,frame in [('weather.csv',weather),('race_control_messages.csv',messages),('driver_laps.csv',laps)]:
            path=output/name;frame.to_csv(path,index=False);files.append(path)
        if weather.empty or messages.empty:
            failures.append({'stage':'context','message':'Weather or messages empty; completeness not established'})
        for _,lap in laps.iterrows():
            start,end=lap['LapStartTime'],lap['Time']
            item={'lap_number':int(lap['LapNumber']), 'deleted_by_fastf1_rcm_parser':bool(lap['Deleted']) if present(lap['Deleted']) else None,
                  'deleted_reason':str(lap['DeletedReason']) if present(lap['DeletedReason']) else None,
                  'dry_track_verified':False}
            if present(start) and present(end):
                # Both LapStartTime/Time and weather Time use session-relative timedeltas.
                inside=weather[(weather['Time']>=start)&(weather['Time']<=end)]
                item.update(lap_start_session_s=start.total_seconds(),lap_end_session_s=end.total_seconds(),
                    weather_samples_in_interval=len(inside),
                    weather_sample_session_s=[t.total_seconds() for t in inside['Time']],
                    rainfall_observations=[bool(x) if present(x) else None for x in inside['Rainfall']],
                    air_temperature_c=[float(x) if present(x) else None for x in inside['AirTemp']],
                    track_temperature_c=[float(x) if present(x) else None for x in inside['TrackTemp']])
                observed=item['rainfall_observations']
                item['rainfall_summary']='rain_reported' if True in observed else ('no_rain_reported_at_samples' if observed and None not in observed else 'unknown')
            else:
                item.update(weather_samples_in_interval=0,rainfall_summary='unknown',alignment_error='missing lap interval')
            contexts.append(item)
    except Exception as exc:
        failures.append({'stage':'load_or_alignment','type':type(exc).__name__,'message':str(exc)})
    finally:
        logger.removeHandler(handler);handler.close()
    files.append(output/'fastf1.log')
    summary={'status':'partial_failure' if failures else 'completed','laps':contexts,'failures':failures,
             'data_role':'development_pilot','alignment':'Weather Time inside inclusive [LapStartTime, Time], all session-relative; no nearest sample substituted.',
             'interpretation':'Sparse rain observations do not prove dry track. Deletion flag is FastF1 interpretation of retrieved messages, not independently verified steward record.'}
    path=output/'summary.json';path.write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf-8');files.append(path)
    manifest={'schema_version':1,'created_utc':datetime.now(timezone.utc).isoformat(),'request':request,
              'source_manifest_sha256':sha256(source_run/'manifest.json'),'fastf1_version':fastf1.__version__,
              'source':source_record(),'load':dict(telemetry=False,weather=True,messages=True),
              'outputs':[{'path':p.name,'sha256':sha256(p)} for p in files]}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-run',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();s=run(a.source_run,a.output);print(json.dumps({'status':s['status'],'lap_count':len(s['laps']),'failures':s['failures']},indent=2))
    raise SystemExit(1 if s['failures'] else 0)
