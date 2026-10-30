"""Prepare development-only adjacent-pair acceleration windows with no interpolation."""
import argparse
import csv
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import re
from collections import Counter

FIELDS=['lap_number','start_time_s','end_time_s','dt_s','speed_start_m_per_s','speed_end_m_per_s','speed_mid_m_per_s','acceleration_m_per_s2','gear','drs']

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def seconds(value):
    m=re.fullmatch(r'(\d+) days (\d+):(\d+):(\d+(?:\.\d+)?)',value)
    if not m:raise ValueError('Unrecognised source timedelta')
    days,hours,minutes,secs=map(float,m.groups())
    return days*86400+hours*3600+minutes*60+secs

def windows(rows,lap,max_gap=0.5,throttle=95):
    out=[];reasons=Counter()
    for a,b in zip(rows,rows[1:]):
        try:
            t0,t1=seconds(a['Time']),seconds(b['Time']);dt=t1-t0
            v0,v1=float(a['Speed'])/3.6,float(b['Speed'])/3.6
            values=[v0,v1,float(a['Throttle']),float(b['Throttle']),float(a['nGear']),float(b['nGear']),float(a['DRS']),float(b['DRS'])]
            if not all(math.isfinite(v) for v in values):raise ValueError('nonfinite')
            if dt<=0:reason='nonincreasing_time'
            elif dt>max_gap:reason='gap_above_limit'
            elif a['Brake']!='False' or b['Brake']!='False':reason='brake_or_unknown'
            elif min(float(a['Throttle']),float(b['Throttle']))<throttle:reason='below_throttle_threshold'
            elif float(a['nGear'])!=float(b['nGear']):reason='gear_change'
            elif float(a['DRS'])!=float(b['DRS']):reason='drs_transition'
            elif v1<=v0:reason='not_positive_acceleration'
            else:
                out.append(dict(zip(FIELDS,[lap,t0,t1,dt,v0,v1,(v0+v1)/2,(v1-v0)/dt,float(a['nGear']),float(a['DRS'])])))
                continue
            reasons[reason]+=1
        except (KeyError,ValueError,TypeError):reasons['invalid_or_missing_value']+=1
    return out,dict(reasons)

def run(root,output):
    root,output=Path(root).resolve(),Path(output).resolve()
    config=root/'configs/development_split.json'
    split=json.loads(config.read_text(encoding='utf-8-sig'))
    clean=root/'results/clean-laps-001';context=root/'results/lap-context-001'
    source_paths=[config,clean/'manifest.json',clean/'summary.json',context/'manifest.json',context/'summary.json',Path(__file__).resolve()]
    clean_summary=json.loads((clean/'summary.json').read_text());ctx=json.loads((context/'summary.json').read_text())
    manifest=json.loads((context/'manifest.json').read_text())
    if any(str(manifest['request'][k])!=str(v) for k,v in split['session'].items()):raise ValueError('Context session identity mismatch')
    if set(split['fit_laps']) & set(split['validation_laps']):raise ValueError('Overlapping split')
    all_tables={};counts=[]
    for role in ('fit','validation'):
        table=[]
        for lap in split[role+'_laps']:
            quality=[x for x in clean_summary['laps'] if x['lap_number']==lap]
            contexts=[x for x in ctx['laps'] if x['lap_number']==lap]
            if len(quality)!=1 or len(contexts)!=1:raise ValueError('Ambiguous or absent lap join')
            if not quality[0]['candidate']:raise ValueError('Noncandidate lap requested')
            c=contexts[0]
            if c['deleted_by_fastf1_rcm_parser'] is not False or c['rainfall_summary']!='no_rain_reported_at_samples':raise ValueError('Context gate failed')
            path=clean/f'lap-{lap}-car.csv';source_paths.append(path)
            with path.open(newline='') as stream: rows=list(csv.DictReader(stream))
            selected,reasons=windows(rows,lap,split['max_pair_gap_s'],split['minimum_throttle_percent'])
            table.extend(selected);counts.append(dict(role=role,lap_number=lap,input_pairs=max(0,len(rows)-1),selected_pairs=len(selected),excluded_first_reason=reasons))
        if not table:raise ValueError('Empty development role')
        all_tables[role]=table
    output.mkdir(parents=True,exist_ok=False)
    files=[]
    for role,table in all_tables.items():
        path=output/f'{role}.csv'
        with path.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=FIELDS);writer.writeheader();writer.writerows(table)
        files.append(path)
    report={'role':split['role'],'counts':counts,'final_test':False,'dry_track_verified':False,
            'derivative':'Adjacent source speed difference / observed dt; finite difference of quantised km/h samples, no smoothing.',
            'selection_bias':'Positive-acceleration selection is conditional and can bias fitting; not the complete vehicle dynamics or full lap envelope.'}
    path=output/'summary.json';path.write_text(json.dumps(report,indent=2)+'\n');files.append(path)
    result={'schema_version':1,'created_utc':datetime.now(timezone.utc).isoformat(),'split':split,
            'inputs':[{'path':str(p.relative_to(root)),'sha256':sha(p)} for p in source_paths],
            'outputs':[{'path':p.name,'sha256':sha(p)} for p in files]}
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',default='.');p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(run(a.root,a.output),indent=2))
