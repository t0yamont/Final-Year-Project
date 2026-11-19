"""Independently recalculate saved predictions and group scores; report qualifying."""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    root=Path('results/session-mix-validation-002')
    manifest=json.loads((root/'manifest.json').read_text());checks=0
    for section in ['inputs','sources','outputs']:
        for p,expected in manifest[section].items():
            assert sha(p)==expected,p
            checks+=1
    models=json.loads((root/'models.json').read_text());lookup=defaultdict(list)
    for m in models:lookup[(m['sensitivity'],m['seed'],m['arm'],m['drs'])].append(m)
    with (root/'predictions.csv').open(newline='',encoding='utf-8') as f:pred=list(csv.DictReader(f))
    grouped=defaultdict(list);max_error=0
    arms=['Q','QP','QPR','QP_matched','QPR_matched']
    for r in pred:
        key=(r['sensitivity'],int(r['seed']))
        for arm in arms:
            fits=[m['fit'] for m in lookup[key+(arm,r['drs'])]]
            speed=float(r['speed']);expected=float(np.median([(f['effective_total_power_w']-f['drag_coefficient_kg_per_m']*speed**3)/(f['assumed_mass_kg']*speed) for f in fits]))
            error=abs(float(r[arm])-expected);max_error=max(max_error,error);assert error<1e-12
        grouped[key+(r['event'],r['session_key'],r['lap'],r['drs'])].append(r)
    gm=json.loads((root/'group_metrics.json').read_text())
    for m in gm:
        rr=grouped[(m['sensitivity'],m['seed'],m['event'],m['session_key'],m['lap'],m['drs'])]
        for arm in ['constant']+arms:
            rmse=np.sqrt(sum((float(r[arm])-float(r['observed']))**2 for r in rr)/len(rr))
            assert abs(rmse-m[arm]['rmse'])<1e-12
    metrics=json.loads((root/'metrics.json').read_text())['metrics']
    for m in metrics:
        gg=[g for g in gm if all(g[k]==m[k] for k in ['sensitivity','seed','event']) and (m['session']=='ALL' or g['session']==m['session'])]
        for arm in ['constant']+arms:
            assert abs(sum(g[arm]['rmse'] for g in gg)/len(gg)-m['rmse'][arm])<1e-12
    # Matched row volume and no validation fitting, checked from the saved source identities.
    qcounts={(m['sensitivity'],m['seed'],m['event'],m['drs']):m['fit']['sample_count'] for m in models if m['arm']=='Q'}
    for m in models:
        assert all(row.startswith('development:') for row in m['train_row_ids'])
        assert len(set(m['train_row_ids']))==m['fit']['sample_count']
        if m['arm'].endswith('matched'):assert m['fit']['sample_count']==qcounts[(m['sensitivity'],m['seed'],m['event'],m['drs'])]
    figures=Path('figures/dissertation/session-mix-qualifying-v1');figures.mkdir(parents=True,exist_ok=False)
    fig,axes=plt.subplots(1,2,figsize=(11.5,4.7),sharey=True)
    for ax,sens in zip(axes,['primary','dt_le_0.3']):
        for event,color,label,offset in [('1266','#176b8a','Hungary',-.15),('1277','#b86118','UK',.15)]:
            mm=[m for m in metrics if m['session']=='Qualifying' and m['sensitivity']==sens and m['event']==event]
            for j,arm in enumerate(arms):
                values=[m['rmse'][arm] for m in mm];x=j+offset
                ax.plot([x,x],[min(values),max(values)],color=color,linewidth=2)
                ax.scatter([x],[np.mean(values)],color=color,s=35,label=label if j==0 else None)
        ax.set_xticks(range(5),['Q','Q+P','Q+P+R','Q+P\nmatched','Q+P+R\nmatched']);ax.grid(axis='y',alpha=.2)
        ax.set_title('Qualifying: '+('primary windows' if sens=='primary' else 'pair gap ≤ 0.3 s'));ax.legend(fontsize=8)
    axes[0].set_ylabel('Mean qualifying lap/DRS-group RMSE (m/s²)')
    fig.suptitle('RQ3: practice helps here; added race benefit is not robust | session-mix-validation-002')
    fig.text(.5,.015,'Observed speed supplied; driver 1; two development events. Matched bars span seeds 0–4, not confidence intervals. Protected test telemetry unopened.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.055,1,.94))
    for ext in ['png','pdf']:fig.savefig(figures/f'01_qualifying_session_mix.{ext}',dpi=300)
    plt.close(fig)
    log=Path('logs/agent_tools/2026-11-18/session_mix_verification.json')
    save(log,dict(status='passed',hashes_checked=checks,prediction_rows=len(pred),conditional_predictions_checked=len(pred)*5,group_metrics=len(gm),max_prediction_discrepancy=max_error,model_records=len(models),matched_volume_and_development_only_fitting=True,figures={str(p):sha(p) for p in figures.iterdir()},script_sha256=sha(__file__)))
    print(log.read_text())


if __name__=='__main__':main()
