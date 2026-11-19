"""Prepare grouped observable motion windows; never read the final test cohort."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pairs(rows, *, max_gap_s=.5, min_throttle=95):
    selected, exclusions = [], Counter()
    for a,b in zip(rows,rows[1:]):
        try:
            t0,t1 = datetime.fromisoformat(a['date_utc']),datetime.fromisoformat(b['date_utc'])
            dt = (t1-t0).total_seconds()
            v0,v1 = float(a['speed_mps']),float(b['speed_mps'])
            values = [v0,v1,float(a['throttle_pct']),float(b['throttle_pct'])]
            if not all(math.isfinite(x) for x in values):
                raise ValueError('Nonfinite sample')
            if dt<=0:reason='nonincreasing_time'
            elif dt>max_gap_s:reason='pair_gap_over_limit'
            elif min(v0,v1)<=0:reason='nonpositive_speed'
            elif a['brake']!='False' or b['brake']!='False':reason='braking_or_unknown'
            elif min(values[2:])<min_throttle:reason='below_throttle_threshold'
            elif not a['gear'] or a['gear']!=b['gear']:reason='gear_change_or_unknown'
            elif not a['drs'] or a['drs']!=b['drs']:reason='drs_change_or_unknown'
            else:
                selected.append({'start_utc':a['date_utc'],'end_utc':b['date_utc'],'dt_s':dt,
                                 'speed_start_mps':v0,'speed_end_mps':v1,'speed_mid_mps':(v0+v1)/2,
                                 'acceleration_mps2':(v1-v0)/dt,'gear':int(a['gear']),'drs':int(a['drs'])})
                continue
            exclusions[reason]+=1
        except (KeyError,ValueError,TypeError):
            exclusions['invalid_sample']+=1
    return selected,dict(exclusions)


def run(args):
    plan=json.loads((args.input/'plan.json').read_text())
    roles={e['meeting_key']:e['role'] for e in plan['events']}
    tables,counts,inputs=defaultdict(list),[],{}
    for role in args.roles:
        # This filesystem scope is deliberate: final-test files are never read.
        for path in sorted((args.input/role).glob('*/*/complete.json')):
            session=json.loads(path.read_text())
            if session['role']!=role or roles.get(session['meeting_key'])!=role:
                raise ValueError('Frozen role mismatch')
            inputs[str(path)]=sha(path)
            for driver in session['drivers']:
                number=driver['driver_number'];directory=path.parent
                lap_file=directory/f'driver-{number}-laps.json'
                car_file=directory/f'driver-{number}-car.csv.gz'
                for file in (lap_file,car_file):
                    actual=sha(file)
                    if actual!=driver['outputs'][file.name]:raise ValueError('Input hash mismatch')
                    inputs[str(file)]=actual
                audit=json.loads(lap_file.read_text())
                accepted={str(r['lap_number']):r for r in audit if r['conditional_motion_candidate']}
                grouped=defaultdict(list)
                with gzip.open(car_file,'rt',encoding='utf-8',newline='') as f:
                    for row in csv.DictReader(f):
                        if row['lap_number'] in accepted:grouped[row['lap_number']].append(row)
                for lap,rows in grouped.items():
                    selected,excluded=pairs(rows)
                    metadata={'role':role,'meeting_key':session['meeting_key'],'session_key':session['session_key'],
                              'session_name':session['session_name'],'driver_number':number,'team':driver['team'],
                              'lap_number':int(lap),'compound':accepted[lap]['context']['stint'].get('compound')}
                    tables[role].extend(dict(metadata,**row) for row in selected)
                    counts.append(dict(metadata,input_pairs=max(0,len(rows)-1),selected_pairs=len(selected),
                                       excluded_first_reason=excluded))
    args.output.mkdir(parents=True,exist_ok=False)
    for role in args.roles:
        rows=tables[role]
        fields=list(rows[0]) if rows else ['role','meeting_key','session_key','driver_number','lap_number']
        with (args.output/f'{role}.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    summary={'status':'prepared_not_fitted','rows_by_role':{r:len(tables[r]) for r in args.roles},
             'lap_groups_by_role':{r:sum(c['role']==r for c in counts) for r in args.roles},
             'selection':{'whole_lap':'declared conditional_motion_candidate','max_pair_gap_s':.5,
                          'min_throttle_pct':95,'signed_acceleration_retained':True},
             'interpretation':'Adjacent dependent observations, grouped by event/session/driver/lap. Effective motion model inputs, not ERS labels. No final test data read. Do not pool car/context fits silently.',
             'groups':counts}
    (args.output/'summary.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
    manifest={'inputs':inputs,'plan_sha256':sha(args.input/'plan.json'),'script_sha256':sha(__file__),
              'outputs':{p.name:sha(p) for p in args.output.iterdir() if p.is_file()}}
    (args.output/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
    print(json.dumps({k:summary[k] for k in ['status','rows_by_role','lap_groups_by_role']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--roles',nargs='+',choices=['development','validation'],default=['development'])
    run(p.parse_args())
