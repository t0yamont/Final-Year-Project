"""Regenerate dissertation figures exclusively from immutable saved results."""
import argparse,hashlib,json
from pathlib import Path
from datetime import datetime,timezone
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FixedFormatter, NullLocator
ROOT=Path(__file__).resolve().parents[1]
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.constrained_layout.use':True,'savefig.facecolor':'white'})

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False);records=[]
    def read(name):return json.loads((ROOT/'results'/name).read_text())
    def save(fig,name,caption,sources):
        paths=[]
        for ext in ('png','pdf'):
            p=output/f'{name}.{ext}';fig.savefig(p,dpi=300);paths.append(p)
        plt.close(fig)
        records.append(dict(figure=name,caption=caption,sources=[{'path':'results/'+x,'sha256':sha(ROOT/'results'/x)} for x in sources],outputs=[{'path':p.name,'sha256':sha(p)} for p in paths]))
    sources=['power-grid-001/summary.json','power-grid-diagnostic-001/summary.json']
    old=read(sources[0]);fine=read(sources[1]);fig,ax=plt.subplots(1,2,figsize=(11,4))
    rows=old['summaries'];ax[0].plot([r['spacing_m'] for r in rows],[r['elapsed_s'] for r in rows],'o-',label='Original fixed-policy path');ax[0].set(xscale='log',xlabel='Cell length (m)',ylabel='Elapsed time (s)',title='Synthetic cell solver: original grids');ax[0].invert_xaxis();ax[0].ticklabel_format(axis='y',useOffset=False)
    for name,case in fine.items():
        r=case['summaries'];reference=r[-1]['elapsed_s']
        ax[1].plot([x['spacing_m'] for x in r],[(x['elapsed_s']-reference)*1000 for x in r],'o-',label=name.replace('_',' '))
    ax[1].set(xscale='log',xlabel='Cell length (m)',ylabel='Time minus finest result (ms)',title='Synthetic diagnostic arms');ax[1].invert_xaxis();ax[1].legend(fontsize=8)
    for axis,ticks in zip(ax,([40,20,10,5,2.5],[2.5,1.25,.625,.3125,.15625])):
        axis.xaxis.set_major_locator(FixedLocator(ticks));axis.xaxis.set_major_formatter(FixedFormatter([f'{x:g}' for x in ticks]));axis.xaxis.set_minor_locator(NullLocator());axis.tick_params(axis='x',labelrotation=30)
    save(fig,'01_grid_studies','Original cell-solver study and four finer-grid diagnostic arms. Different arms have different constraints; offsets are relative to each armÃ¢â‚¬â„¢s own finest result, not true error. Historical rejected gate is retained.',sources)
    source='event-validation-002/summary.json';d=read(source);fig,ax=plt.subplots(1,2,figsize=(10,4));r=d['sampling']
    ax[0].plot([x['spacing_m'] for x in r],[x['elapsed_s']-r[-1]['elapsed_s'] for x in r],'o-');ax[0].set(xscale='log',xlabel='Output sample spacing (m)',ylabel='Time minus finest output spacing (s)',title='Synthetic event solver: output invariance');ax[0].invert_xaxis()
    errors=d['assessment']['integration_errors_vs_reference'];ax[1].loglog([e['rtol'] for e in errors],[e['elapsed_s'] for e in errors],'o-');ax[1].set(xlabel='Requested relative tolerance',ylabel='Absolute time difference (s)',title='Integration refinement vs tighter reference');ax[1].invert_xaxis()
    save(fig,'02_event_validation','Event solver: output sampling is separate from integration refinement. Right panel also varies maximum integration step per saved protocol. Reference is numerical, not exact; analytic checks are recorded separately. Synthetic only.',[source])
    source='calibration-fit-001/metrics.json';d=read(source);m=d['mass_sensitivity'];fig,ax=plt.subplots(1,3,figsize=(12,4));mass=[float(x) for x in m]
    ax[0].plot(mass,[v['fit']['effective_total_power_w']/1000 for v in m.values()],'o-');ax[0].set(xlabel='Assumed mass (kg)',ylabel='Effective total power (kW)',title='Development fit: mass confounding')
    ax[1].plot(mass,[v['fit']['drag_coefficient_kg_per_m'] for v in m.values()],'o-');ax[1].set(xlabel='Assumed mass (kg)',ylabel='Effective drag coefficient (kg/m)',title='Coefficients scale with mass')
    profile=m['800.0']['fit']['profile'];ax[2].plot([p['drag_coefficient_kg_per_m'] for p in profile],[p['rmse_w']/1000 for p in profile]);ax[2].set(xlabel='Fixed effective drag (kg/m)',ylabel='Power-equation RMSE (kW)',title='Power refitted at each drag value')
    save(fig,'03_calibration_identifiability','Bahrain development acceleration-window diagnostic. Coefficients scale with assumed mass while predicted acceleration is unchanged. Right panel is objective sensitivity, not a confidence interval. These are not verified car or electrical parameters.',[source])
    source='reconstruction-synthetic-002/reconstruction.json';d=read(source);runs=d['runs'];fig,ax=plt.subplots(1,2,figsize=(11,4))
    for case,marker in [('exact','o'),('noisy_sigma_0.1','s')]:
        r=[x for x in runs if x['case']==case]
        if r:
            ax[0].scatter([x['assumed_base_power_w']/1000 for x in r],[x['action_rmse_w']/1000 for x in r],marker=marker,label=case,alpha=.6)
            ax[1].scatter([x['assumed_base_power_w']/1000 for x in r],[x['speed_rmse_m_per_s'] for x in r],marker=marker,label=case,alpha=.6)
    for a in ax:a.axvline(d['truth']['base_power_w']/1000,color='gray',ls='--',label='True base power');a.set_xlabel('Assumed base power (kW)');a.legend(fontsize=8)
    ax[0].set(ylabel='Deployment RMSE vs known truth (kW)',title='Synthetic inverse recovery: action ambiguity');ax[1].set(ylabel='Endpoint speed RMSE (m/s)',title='Small trace error can hide action error')
    save(fig,'04_reconstruction_errors','Synthetic analytic straight with known deployment truth. Exact and noisy endpoint observations fitted across assumed base powers and initialisations. Multiple starts are not independent experimental samples. Low speed error does not verify deployment.',[source])
    fig,ax=plt.subplots(figsize=(7,4));truth=d['truth']['deployment_w'];ax.plot([1,2,3],[x/1000 for x in truth],'ko-',lw=2,label='Known truth')
    for base in sorted(set(x['assumed_base_power_w'] for x in runs)):
        r=next(x for x in runs if x['case']=='exact' and x['assumed_base_power_w']==base)
        ax.plot([1,2,3],[x/1000 for x in r['deployment_w']],'o--',label=f'Assumed base {base/1000:g} kW')
    ax.set(xlabel='Synthetic segment index',ylabel='Electrical deployment (kW)',title='Synthetic ambiguity: alternative feasible deployment maps',xticks=[1,2,3]);ax.legend(fontsize=8)
    save(fig,'05_reconstruction_maps','One exact-observation solution per assumed base power, with synthetic truth shown. This figure demonstrates ambiguity under the declared analytic model; it is not an inferred real-team deployment map.',[source])
    sources=['synthetic-baselines-001/metrics.json','synthetic-ppo-001/metrics.json','synthetic-ppo-seed1-001/metrics.json','synthetic-ppo-seed2-001/metrics.json'];b=read(sources[0])['results'];names=[];times=[]
    for name,r in b.items():
        if isinstance(r,dict) and 'elapsed_s' in r and r.get('feasible') and 'ppo' not in name.lower():names.append(name);times.append(r['elapsed_s'])
    for seed,src in enumerate(sources[1:]):
        r=read(src)['results']['training_nominal'];key=next(k for k in r if 'ppo' in k.lower());names.append(f'PPO seed {seed}');times.append(r[key]['elapsed_s'])
    fig,ax=plt.subplots(figsize=(10,5));ax.scatter(times,range(len(names)),s=45);ax.set_yticks(range(len(names)),names);ax.invert_yaxis();ax.set(xlabel='Feasible nominal elapsed time (s)',title='Synthetic constant-force model: baselines and PPO pilots');ax.grid(axis='x',alpha=.25)
    save(fig,'06_synthetic_controller_comparison','All points use the original synthetic constant-force model and nominal scenario. PPO pilots use 16,384 steps per seed. DP uses finite action/energy grids; exhaustive reference covers its discrete action set. Event/power-model times are not mixed into this comparison.',sources)
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(Path(__file__)),'matplotlib_version':matplotlib.__version__,'figures':records}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (output/'captions.md').write_text('\n\n'.join(f"## {r['figure']}\n\n{r['caption']}" for r in records)+'\n',encoding='utf-8')
    print(f'Saved {len(records)} figures as PNG300dpi and vector PDF to {output}')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args();main(a.output)
