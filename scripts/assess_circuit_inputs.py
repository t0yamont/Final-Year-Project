"""Development-only motion diagnostics and independent Bahrain geometry audit."""
import argparse
import csv
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from f1energy.identification import fit_effective, evaluate


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--figures',type=Path,required=True)
    args=parser.parse_args()
    manifest=json.loads((args.input/'manifest.json').read_text())
    table=args.input/'development.csv'
    assert sha(table)==manifest['outputs'][table.name]
    groups=defaultdict(list)
    with table.open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['role']!='development':raise ValueError('Development-only study')
            if row['driver_number']=='1':
                groups[(row['meeting_key'],row['session_name'],row['session_key'],row['drs'])].append(row)
    results=[];skipped=[]
    for key,rows in sorted(groups.items()):
        laps=sorted({int(r['lap_number']) for r in rows})
        if len(laps)<3:
            skipped.append({'group':key,'reason':'fewer_than_three_laps'});continue
        validation_laps=laps[-max(1,len(laps)//4):]
        train=[r for r in rows if int(r['lap_number']) not in validation_laps]
        val=[r for r in rows if int(r['lap_number']) in validation_laps]
        if min(len(train),len(val))<5:
            skipped.append({'group':key,'reason':'too_few_windows'});continue
        v=lambda rr:np.array([float(r['speed_mid_mps']) for r in rr])
        a=lambda rr:np.array([float(r['acceleration_mps2']) for r in rr])
        try:fit=fit_effective(v(train),a(train),mass_kg=800)
        except ValueError as exc:
            skipped.append({'group':key,'reason':str(exc)});continue
        metrics=evaluate(fit,v(val),a(val))
        constant=float(np.mean(a(train)))
        baseline=float(np.sqrt(np.mean((a(val)-constant)**2)))
        results.append({'group':key,'fit_laps':[l for l in laps if l not in validation_laps],
                        'development_holdout_laps':validation_laps,'fit':fit,'holdout':metrics,
                        'constant_acceleration_baseline_rmse':baseline})
    args.output.mkdir(parents=True,exist_ok=False);args.figures.mkdir(parents=True,exist_ok=False)
    source=Path('work/track-source/sakhir.txt');license_path=Path('work/track-source/tracklicense.txt')
    track=np.loadtxt(source,delimiter=',');xy=track[:,:2]
    if track.shape[1]!=4 or not np.isfinite(track).all() or np.any(track[:,2:]<=0):
        raise ValueError('Invalid geometry columns or widths')
    lengths=np.linalg.norm(np.roll(xy,-1,axis=0)-xy,axis=1)
    if np.any(lengths<=0):raise ValueError('Duplicate consecutive vertices')
    geometry={'source':'https://github.com/TUMFTM/racetrack-database/blob/master/tracks/Sakhir.csv',
              'source_sha256':sha(source),'points':len(track),'closed_polyline_length_m':float(lengths.sum()),
              'official_reference_length_m':5412.,'reference':'https://www.formula1.com/en/racing/2025/bahrain',
              'length_difference_percent':float(100*(lengths.sum()/5412-1)),
              'minimum_half_width_m':float(track[:,2:].min()),
              'status':'candidate_geometry_basic_checks_passed; layout visual review and curvature model pending',
              'limitations':'OSM/satellite-derived smoothed centreline; no measured driver racing line, grade or grip. Length agreement alone does not prove layout fidelity.'}
    shutil.copyfile(source,args.output/'Sakhir.csv');shutil.copyfile(license_path,args.output/'SOURCE_LICENSE.txt')
    payload={'scope':'Driver1 development contexts; separate event/session/DRS fits, last laps held out within development only',
             'split_rule':'Chronological last max(1,floor(lap_count/4)) laps; minimum3 laps and5 windows per split; fixed before fits',
             'mass_assumption_kg':800,'model':'m*v*a=P_total-k*v^3; bounded power-equation least squares',
             'limitations':'Conditional acceleration residuals use observed speed; not free-running trajectory validation. Adjacent samples dependent; fuel/setup/grade/energy confounded. No final test inputs read.',
             'fits':results,'skipped':skipped,'geometry':geometry}
    (args.output/'metrics.json').write_bytes((json.dumps(payload,indent=2)+'\n').encode())
    fig,axes=plt.subplots(1,2,figsize=(12,5.4))
    x=[r['constant_acceleration_baseline_rmse'] for r in results]
    y=[r['holdout']['acceleration_rmse_m_per_s2'] for r in results]
    axes[0].scatter(x,y,c='#176b8a',s=35,alpha=.8)
    limit=max(x+y,default=1)*1.1;axes[0].plot([0,limit],[0,limit],'--',color='gray',label='Equal error')
    axes[0].set(xlim=(0,limit),ylim=(0,limit),xlabel='Constant-acceleration baseline RMSE (m/s²)',
                ylabel='Effective power/drag model RMSE (m/s²)',title=f'{len(results)} separate development-context fits')
    axes[0].legend();axes[0].grid(alpha=.2)
    closed=np.vstack([xy,xy[0]])
    axes[1].plot(closed[:,0],closed[:,1],color='#176b8a');axes[1].set_aspect('equal')
    axes[1].set(xlabel='Local x (m)',ylabel='Local y (m)',title=f'Candidate Sakhir centreline: {lengths.sum():.1f} m')
    fig.suptitle('Full-circuit model preparation: observable motion and geometry checks')
    fig.text(.5,.015,'Within-development lap holdouts; assumed 800 kg. Geometry is approximate. Final test data were not used.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,.94))
    for ext in ['png','pdf']:fig.savefig(args.figures/f'01_circuit_inputs.{ext}',dpi=300)
    plt.close(fig)
    record={'inputs':{str(table):sha(table),str(source):sha(source),str(license_path):sha(license_path)},
            'source_sha256':{str(Path(__file__)):sha(__file__),'src/f1energy/identification.py':sha('src/f1energy/identification.py')},
            'outputs':{str(p):sha(p) for folder in [args.output,args.figures] for p in folder.iterdir() if p.is_file()}}
    (args.output/'manifest.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
    print(json.dumps({'context_fits':len(results),'better_than_constant_baseline':sum(b<a for a,b in zip(x,y)),
                      'boundary_hit_fits':sum(bool(r['fit']['parameter_boundary_hits']) for r in results),'geometry':geometry}))


if __name__=='__main__':main()
