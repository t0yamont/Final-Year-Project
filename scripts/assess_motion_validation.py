"""Frozen development-fit transfer and assumed-reference observable diagnostics."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, obj): p.write_bytes((json.dumps(obj, indent=2, allow_nan=False)+'\n').encode())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol',type=Path,default=Path('configs/motion_validation_protocol.json'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--figures',type=Path,required=True)
    args=parser.parse_args(); protocol=json.loads(args.protocol.read_text())
    source=Path(protocol['motion_source']); fit_source=Path(protocol['fit_source'])
    manifest=json.loads((source/'manifest.json').read_text())
    fit_manifest=json.loads((fit_source/'manifest.json').read_text())
    fits_path=fit_source/'metrics.json'
    assert sha(fits_path)==fit_manifest['outputs'][str(fits_path)]
    fits=json.loads(fits_path.read_text())['fits']
    config_path=Path(protocol['reference_config']); config=json.loads(config_path.read_text()); vehicle=config['vehicle']
    inputs={str(p):sha(p) for p in [args.protocol,source/'manifest.json',fit_source/'manifest.json',fits_path,config_path]}
    tables={}
    for role in ['development','validation']:
        p=source/f'{role}.csv'; assert sha(p)==manifest['outputs'][p.name]; inputs[str(p)]=sha(p)
        with p.open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
        assert all(r['role']==role for r in rows)
        tables[role]=[r for r in rows if r['driver_number']==protocol['driver_number']]
    assert not {r['meeting_key'] for r in tables['development']} & {r['meeting_key'] for r in tables['validation']}
    args.output.mkdir(parents=True,exist_ok=False); args.figures.mkdir(parents=True,exist_ok=False)
    save(args.output/'contract.json',dict(protocol=protocol,inputs=inputs,source_sha256=sha(__file__)))
    def key(r):return (r['meeting_key'],r['session_name'],r['session_key'],r['drs'])
    grouped=defaultdict(list)
    for r in tables['development']:grouped[key(r)].append(r)
    contexts=[]
    for item in fits:
        group=tuple(item['group']); train=[r for r in grouped[group] if int(r['lap_number']) in item['fit_laps']]
        assert len(train)==item['fit']['sample_count']
        contexts.append(dict(group=group,fit=item['fit'],holdout=item['development_holdout_laps'],
                             mean_acceleration=float(np.mean([float(r['acceleration_mps2']) for r in train]))))
    predictions=[]; skipped=defaultdict(int)
    for role,rows in tables.items():
        for r in rows:
            if role=='development':
                matching=[c for c in contexts if c['group']==key(r) and int(r['lap_number']) in c['holdout']]
            else:
                matching=[c for c in contexts if (c['group'][1],c['group'][3])==(r['session_name'],r['drs'])]
            if not matching:
                skipped[(role,r['meeting_key'],r['session_name'],r['drs'])]+=1; continue
            v=float(r['speed_mid_mps']); a=float(r['acceleration_mps2'])
            pred=[(c['fit']['effective_total_power_w']/v-c['fit']['drag_coefficient_kg_per_m']*v*v)/c['fit']['assumed_mass_kg'] for c in matching]
            base=(vehicle['base_power_w']/v-vehicle['drag_kg_per_m']*v*v)/vehicle['mass_kg']
            full=base+vehicle['electrical_limit_w']/(vehicle['mass_kg']*v)
            low=max(c['fit']['speed_min_m_per_s'] for c in matching); high=min(c['fit']['speed_max_m_per_s'] for c in matching)
            predictions.append(dict(role=role,meeting_key=r['meeting_key'],session_key=r['session_key'],
                session_name=r['session_name'],driver_number=r['driver_number'],lap_number=r['lap_number'],drs=r['drs'],
                start_utc=r['start_utc'],speed_mps=v,observed_acceleration_mps2=a,reference_base=base,reference_full=full,
                development_fit_median=float(np.median(pred)),constant=float(np.median([c['mean_acceleration'] for c in matching])),
                matched_contexts=len(matching),outside_common_speed_range=not low<=v<=high,
                inside_reference_power_band=base<=a<=full))
    with (args.output/'predictions.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(predictions[0]));writer.writeheader();writer.writerows(predictions)
    lapgroups=defaultdict(list)
    for r in predictions:lapgroups[tuple(r[k] for k in ['role','meeting_key','session_key','driver_number','lap_number','drs'])].append(r)
    models=['constant','reference_base','reference_full','development_fit_median']; lap_metrics=[]
    for group,rows in lapgroups.items():
        item=dict(group=group,windows=len(rows))
        for model in models:
            errors=np.array([r[model]-r['observed_acceleration_mps2'] for r in rows])
            item[model]=dict(rmse_mps2=float(np.sqrt(np.mean(errors**2))),bias_mps2=float(np.mean(errors)))
        lap_metrics.append(item)
    event_metrics=[]
    for role,event in sorted({(r['role'],r['meeting_key']) for r in predictions}):
        rows=[r for r in predictions if (r['role'],r['meeting_key'])==(role,event)]
        laps=[r for r in lap_metrics if r['group'][:2]==(role,event)]
        event_metrics.append(dict(role=role,event=event,windows=len(rows),lap_drs_groups=len(laps),
            unique_laps=len({tuple(r[k] for k in ['session_key','lap_number']) for r in rows}),
            rmse_macro={m:float(np.mean([r[m]['rmse_mps2'] for r in laps])) for m in models},
            bias_macro={m:float(np.mean([r[m]['bias_mps2'] for r in laps])) for m in models},
            fraction_outside_common_speed_range=float(np.mean([r['outside_common_speed_range'] for r in rows])),
            fraction_inside_reference_power_band=float(np.mean([r['inside_reference_power_band'] for r in rows]))))
    result=dict(protocol=protocol,event_metrics=event_metrics,lap_metrics=lap_metrics,
                skipped=[dict(group=k,windows=v) for k,v in sorted(skipped.items())],
                fitted_context_parameters=[dict(group=c['group'],power_w=c['fit']['effective_total_power_w'],drag=c['fit']['drag_coefficient_kg_per_m']) for c in contexts])
    save(args.output/'metrics.json',result)
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    colors=['#555555','#b86118','#aa7a21','#176b8a'];labels=['Constant acceleration','Reference: base power','Reference: full request','Development fits']
    for ax,role in zip(axes,['development','validation']):
        items=[r for r in event_metrics if r['role']==role]; x=np.arange(len(items))
        for i,(m,col,label) in enumerate(zip(models,colors,labels)):
            ax.bar(x+(i-1.5)*.19,[r['rmse_macro'][m] for r in items],.19,color=col,label=label,hatch='//' if i==2 else None)
        names={'1256':'Japan','1257':'Bahrain','1262':'Spain','1268':'Monza','1266':'Hungary','1277':'UK'}
        ax.set_xticks(x,[names.get(r['event'],r['event']) for r in items]);ax.set_ylabel('Mean lap/DRS-group acceleration RMSE (m/s²)')
        ax.set_title('Within-development lap holdouts' if role=='development' else 'Transfer to reserved validation events')
        ax.set_ylim(0,1.4*max(v for row in event_metrics for v in row['rmse_macro'].values()))
        ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    axes[0].legend(fontsize=8)
    fig.suptitle('Observable-motion assessment | '+args.output.name)
    fig.text(.5,.015,'Driver 1; matching session/DRS contexts only. Observed speed is supplied. Reference endpoints do not identify actual electrical deployment.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,.94))
    for ext in ['png','pdf']:fig.savefig(args.figures/f'01_motion_validation.{ext}',dpi=300)
    plt.close(fig)
    outputs={str(p):sha(p) for folder in [args.output,args.figures] for p in folder.iterdir() if p.is_file()}
    save(args.output/'manifest.json',dict(inputs=inputs,sources={str(Path(__file__)):sha(__file__)},outputs=outputs))
    print(json.dumps(event_metrics,indent=2))


if __name__=='__main__':main()
