"""Dissertation acquisition coverage, without evaluating models on test data."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    coverage=json.loads((args.input/'coverage.json').read_text())
    plan=json.loads((args.input/'plan.json').read_text())
    totals=defaultdict(Counter);reasons=Counter();inputs={}
    for session in coverage['sessions']:
        path=args.input/session['role']/str(session['meeting_key'])/str(session['session_key'])/'complete.json'
        inputs[str(path)]=sha(path)
        for driver in session['drivers']:
            for name,digest in driver['outputs'].items():
                if sha(path.parent/name)!=digest:raise ValueError('Source output hash mismatch')
            totals[session['meeting_key']]['laps']+=driver['lap_count']
            totals[session['meeting_key']]['candidates']+=driver['conditional_motion_candidates']
            reasons.update(driver['exclusion_counts'])
    args.output.mkdir(parents=True,exist_ok=False)
    fig,axes=plt.subplots(1,2,figsize=(13,6.4),gridspec_kw={'width_ratios':[1.25,1]})
    events=plan['events'];x=list(range(len(events)))
    axes[0].bar(x,[totals[e['meeting_key']]['laps'] for e in events],color='#c7d1da',label='Recorded lap entries')
    axes[0].bar(x,[totals[e['meeting_key']]['candidates'] for e in events],color='#176b8a',label='Conditional motion candidates')
    axes[0].set_xticks(x,[e['name']+'\n'+e['role'] for e in events],rotation=40,ha='right',fontsize=8)
    axes[0].set_ylabel('Lap entries across selected driver/session combinations')
    axes[0].set_title('Coverage by frozen event role',fontsize=11)
    axes[0].legend(fontsize=9)
    labels={'gap_missing_or_over_limit':'Missing/large internal gaps','native_motion_qc_failed':'Native-sample / interval QC',
            'lap_edge_coverage_missing_or_over_limit':'Insufficient lap-edge coverage','pit_out_or_unknown':'Out-lap / unknown pit-out',
            'pit_activity_reported':'Reported pit activity','flag_reported':'Reported caution / flag',
            'rain_reported_or_unknown':'Rain / insufficient rain evidence','weather_missing_stale_or_ambiguous':'Missing/stale weather',
            'stint_unknown_or_ambiguous':'Unknown/ambiguous stint','wet_or_unknown_tyre_compound':'Wet/unknown tyre','deletion_reported':'Reported lap deletion'}
    ordered=reasons.most_common()
    axes[1].barh([labels.get(k,k) for k,v in ordered],[v for k,v in ordered],color='#916338')
    axes[1].invert_yaxis();axes[1].tick_params(axis='y',labelsize=8)
    axes[1].set_xlabel('Lap entries carrying this exclusion (reasons can overlap)')
    axes[1].set_title('Screening exclusions, not model errors',fontsize=11)
    for ax in axes:ax.grid(axis='x' if ax==axes[1] else 'y',alpha=.18);ax.set_axisbelow(True)
    fig.suptitle(f"2025 public telemetry: {coverage['completed_sessions']}/{coverage['expected_sessions']} selected sessions acquired",fontsize=13)
    fig.text(.5,.015,'Conditional candidates are not verified clean/dry laps. No battery labels or test-model performance are shown.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.95))
    outputs={}
    for suffix in ('png','pdf'):
        dest=args.output/('01_dataset_coverage.'+suffix);fig.savefig(dest,dpi=300);outputs[dest.name]=sha(dest)
    plt.close(fig)
    manifest={'coverage_sha256':sha(args.input/'coverage.json'),'plan_sha256':sha(args.input/'plan.json'),
              'inputs':inputs,'script_sha256':sha(__file__),'outputs':outputs}
    (args.output/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
    print('Coverage PNG/PDF saved with verified source hashes:',args.output)


if __name__=='__main__':main()
