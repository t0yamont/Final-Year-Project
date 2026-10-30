"""Source telemetry quality figures; no smoothing or modelling eligibility claim."""
from pathlib import Path
import hashlib,json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[1]
out=root/'figures/dissertation/telemetry-quality-v1';out.mkdir(parents=True,exist_ok=False)
source=root/'results/clean-laps-001';sources=[]
fig,axes=plt.subplots(2,1,figsize=(10,7),layout='constrained')
for lap in (4,10,13,16):
 p=source/f'lap-{lap}-car.csv';sources.append(p);d=pd.read_csv(p)
 t=pd.to_timedelta(d['Time']).dt.total_seconds();speed=d['Speed']/3.6
 axes[0].plot(t,speed,label=f'Lap {lap}',lw=1)
 axes[1].plot(t.iloc[1:],t.diff().iloc[1:],label=f'Lap {lap}',lw=.8,alpha=.8)
axes[0].set(title='Bahrain 2025 qualifying: development candidate source traces',ylabel='Speed (m/s)',xlabel='Source lap-slice elapsed time (s)')
axes[1].axhline(1,color='black',ls='--',lw=1,label='1 s diagnostic threshold')
axes[1].set(ylabel='Adjacent source time gap (s)',xlabel='Source lap-slice elapsed time (s)')
for ax in axes: ax.legend(fontsize=8,ncol=3);ax.grid(alpha=.2)
for ext in ('png','pdf'):fig.savefig(out/f'telemetry_quality.{ext}',dpi=300)
plt.close(fig)
(out/'caption.md').write_text('Development-only source telemetry from candidate laps4,10,13,16; speed converted from km/h to m/s. Lines connect original samples without smoothing/interpolation. Sampling gaps are adjacent source-time differences; the1s line is diagnostic, not a validated exclusion threshold. Lap16 is excluded from primary calibration. These traces do not measure electrical deployment or prove clean/dry eligibility.\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=dict(inputs_sha256={str(p.relative_to(root)):sha(p) for p in sources},source_sha256=sha(Path(__file__)),outputs_sha256={p.name:sha(p) for p in out.iterdir() if p.is_file()})
(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(out)
