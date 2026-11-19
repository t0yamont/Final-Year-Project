"""Frozen validation-only session-pool intervention using existing effective fits."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from f1energy.identification import fit_effective


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    p.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def category(row):
    return 'Q' if row['session_name']=='Qualifying' else 'R' if row['session_name']=='Race' else 'P'


def matched(rows, count, seed, cats):
    rng=np.random.default_rng(seed)
    pools={c:[r for r in rows if category(r)==c] for c in cats}
    for values in pools.values():
        rng.shuffle(values)
    selected=[]
    while len(selected)<count:
        for c in cats:
            if pools[c] and len(selected)<count:
                selected.append(pools[c].pop())
        if not any(pools.values()) and len(selected)<count:
            raise ValueError('Insufficient matched volume')
    assert len({r['row_id'] for r in selected})==count
    return selected


def main():
    protocol_path=Path('configs/session_mix_protocol.json')
    protocol=json.loads(protocol_path.read_text())
    output=Path('results/session-mix-validation-002')
    figures=Path('figures/dissertation/session-mix-v2')
    output.mkdir(exist_ok=False); figures.mkdir(parents=True,exist_ok=False)
    source=Path(protocol['motion_source']); source_manifest=json.loads((source/'manifest.json').read_text())
    role_path=Path(protocol['roles']); roles=json.loads(role_path.read_text())
    role_events={role:{str(e['meeting_key']) for e in roles['event_roles'] if e['role']==role} for role in ['development','validation']}
    inputs={str(p):sha(p) for p in [protocol_path,role_path,source/'manifest.json']}
    tables={}; coverage=[]
    for role in ['development','validation']:
        path=source/f'{role}.csv'
        assert sha(path)==source_manifest['outputs'][path.name]
        inputs[str(path)]=sha(path)
        with path.open(newline='',encoding='utf-8') as f:
            rows=list(csv.DictReader(f))
        assert all(r['role']==role and r['meeting_key'] in role_events[role] for r in rows)
        tables[role]=[dict(r,row_id=f'{role}:{i}') for i,r in enumerate(rows) if r['driver_number']==protocol['driver_number']]
        for event,session in sorted({(r['meeting_key'],r['session_name']) for r in tables[role]}):
            rr=[r for r in tables[role] if (r['meeting_key'],r['session_name'])==(event,session)]
            coverage.append(dict(role=role,event=event,session=session,windows=len(rr),laps=len({r['lap_number'] for r in rr})))
    save(output/'contract.json',dict(protocol=protocol,inputs=inputs,sources={str(Path(__file__)):sha(__file__),'src/f1energy/identification.py':sha('src/f1energy/identification.py')}))
    save(output/'coverage.json',coverage)
    metrics=[]; models=[]; predictions=[]; skips=[]; group_metrics=[]
    for sensitivity in protocol['sensitivities']:
        def include(r):
            return (sensitivity!='dt_le_0.3' or float(r['dt_s'])<=.3) and (sensitivity!='speed_ge_30' or float(r['speed_mid_mps'])>=30)
        dev=[r for r in tables['development'] if include(r)]
        val=[r for r in tables['validation'] if include(r)]
        contexts=defaultdict(list)
        for r in dev:
            contexts[(r['meeting_key'],r['drs'])].append(r)
        eligible={}
        for key,rows in sorted(contexts.items()):
            q=[r for r in rows if category(r)=='Q']
            if len(q)<30 or len({r['lap_number'] for r in q})<2:
                skips.append(dict(sensitivity=sensitivity,context=key,reason='Q support under 30 windows or 2 laps',q_windows=len(q)))
                continue
            eligible[key]=rows
        assert len({key[0] for key in eligible})>=2
        for seed in protocol['seeds']:
            fitted={arm:defaultdict(list) for arm in protocol['arms']}
            for key,rows in eligible.items():
                q=[r for r in rows if category(r)=='Q']; n=len(q)
                pools={'Q':q,'QP':[r for r in rows if category(r) in 'QP'],'QPR':rows,
                       'QP_matched':matched(rows,n,seed,'QP'),'QPR_matched':matched(rows,n,seed,'QPR')}
                for arm,train in pools.items():
                    v=np.array([float(r['speed_mid_mps']) for r in train]); a=np.array([float(r['acceleration_mps2']) for r in train])
                    fit=fit_effective(v,a,mass_kg=protocol['mass_kg'])
                    assert fit['solver_success']
                    record=dict(sensitivity=sensitivity,seed=seed,arm=arm,event=key[0],drs=key[1],fit=fit,
                                session_counts=dict(Counter(category(r) for r in train)),unique_laps=len({(r['session_key'],r['lap_number']) for r in train}),
                                train_row_ids=[r['row_id'] for r in train],mean_a=float(a.mean()))
                    models.append(record);fitted[arm][key[1]].append(record)
                    if arm.endswith('matched'):assert len(train)==n
            grouped=defaultdict(list); excluded=Counter()
            for r in val:
                drs=r['drs']
                if not fitted['Q'].get(drs):
                    excluded[(r['meeting_key'],r['session_name'],drs)]+=1;continue
                v=float(r['speed_mid_mps']); a=float(r['acceleration_mps2'])
                pred={'constant':float(np.median([m['mean_a'] for m in fitted['Q'][drs]]))}
                for arm in protocol['arms']:
                    ff=[m['fit'] for m in fitted[arm][drs]]
                    pred[arm]=float(np.median([(f['effective_total_power_w']/v-f['drag_coefficient_kg_per_m']*v*v)/800 for f in ff]))
                record=dict(sensitivity=sensitivity,seed=seed,row_id=r['row_id'],event=r['meeting_key'],session=r['session_name'],session_key=r['session_key'],lap=r['lap_number'],drs=drs,speed=v,observed=a,**pred)
                for arm in protocol['arms']:
                    ff=[m['fit'] for m in fitted[arm][drs]]
                    record[arm+'_outside']=not max(f['speed_min_m_per_s'] for f in ff)<=v<=min(f['speed_max_m_per_s'] for f in ff)
                predictions.append(record)
                grouped[(r['meeting_key'],r['session_name'],r['session_key'],r['lap_number'],drs)].append(record)
            skips.extend(dict(sensitivity=sensitivity,seed=seed,validation_context=k,windows=n,reason='unmatched exact DRS') for k,n in sorted(excluded.items()))
            local=[]
            for key,rr in grouped.items():
                item=dict(sensitivity=sensitivity,seed=seed,event=key[0],session=key[1],session_key=key[2],lap=key[3],drs=key[4],windows=len(rr))
                for arm in ['constant']+protocol['arms']:
                    error=np.array([r[arm]-r['observed'] for r in rr]);item[arm]=dict(rmse=float(np.sqrt(np.mean(error**2))),bias=float(error.mean()))
                local.append(item);group_metrics.append(item)
            for event in sorted({r['event'] for r in local}):
                for session in ['ALL']+sorted({r['session'] for r in local if r['event']==event}):
                    ll=[r for r in local if r['event']==event and (session=='ALL' or r['session']==session)]
                    rr=[r for values in grouped.values() for r in values if r['event']==event and (session=='ALL' or r['session']==session)]
                    metrics.append(dict(sensitivity=sensitivity,seed=seed,event=event,session=session,groups=len(ll),windows=sum(r['windows'] for r in ll),
                        rmse={arm:float(np.mean([r[arm]['rmse'] for r in ll])) for arm in ['constant']+protocol['arms']},
                        outside_fraction={arm:float(np.mean([r[arm+'_outside'] for r in rr])) for arm in protocol['arms']}))
    accepted=all(m['rmse']['QPR']<m['rmse']['Q'] and m['rmse']['QPR_matched']<m['rmse']['Q'] for m in metrics if m['session']=='ALL')
    save(output/'metrics.json',dict(status='completed_validation_only',consistent_qpr_benefit=accepted,metrics=metrics,skips=skips))
    save(output/'models.json',models);save(output/'group_metrics.json',group_metrics)
    with (output/'predictions.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(predictions[0]));writer.writeheader();writer.writerows(predictions)
    fig,axes=plt.subplots(1,3,figsize=(13.8,4.9),sharey=True)
    names={'1266':'Hungary','1277':'UK'}
    for ax,sensitivity in zip(axes,protocol['sensitivities']):
        for i,event in enumerate(['1266','1277']):
            mm=[m for m in metrics if m['sensitivity']==sensitivity and m['event']==event and m['session']=='ALL']
            for j,arm in enumerate(protocol['arms']):
                values=[m['rmse'][arm] for m in mm];x=j+(i-.5)*.3
                ax.plot([x,x],[min(values),max(values)],color=['#176b8a','#b86118'][i],linewidth=2)
                ax.scatter([x],[np.mean(values)],color=['#176b8a','#b86118'][i],s=35,label=names[event] if j==0 else None)
        ax.set_xticks(range(5),['Q','Q+P','Q+P+R','Q+P\nmatched','Q+P+R\nmatched'],fontsize=8)
        ax.set_title(sensitivity.replace('_',' '));ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
    axes[0].set_ylabel('Mean lap/DRS-group acceleration RMSE (m/s²)')
    fig.suptitle('Session-mix validation ablation | session-mix-validation-002')
    fig.text(.5,.015,'Driver 1; observed speed supplied; median transfer across development event/DRS fits. Bars span five fixed sampling seeds; no confidence interval.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.055,1,.94))
    for ext in ['png','pdf']:fig.savefig(figures/f'01_session_mix.{ext}',dpi=300)
    plt.close(fig)
    save(output/'manifest.json',dict(inputs=inputs,sources={p:sha(p) for p in ['scripts/study_session_mix.py','src/f1energy/identification.py']},outputs={str(p):sha(p) for folder in [output,figures] for p in folder.iterdir() if p.is_file()}))
    print(json.dumps(dict(status='completed_validation_only',consistent_qpr_benefit=accepted,models=len(models),predictions=len(predictions),primary=[m for m in metrics if m['sensitivity']=='primary' and m['session']=='ALL' and m['seed']==0]),indent=2))


if __name__=='__main__':main()
