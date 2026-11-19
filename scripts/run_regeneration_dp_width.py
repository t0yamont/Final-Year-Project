"""Bound the width sensitivity at fixed actions and state bins."""
import argparse
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from benchmark_circuit_control import load_setup, make_env, save, gzsave, sha
from optimize_regeneration_dp import search, replay
from f1energy.circuit_training_gate import validate_control_gate


def run(width, output, settings, protocol, config):
    ref,curve,vehicle=load_setup(config)
    def env(n):
        return make_env(config,ref,curve,vehicle,n)
    settings=dict(settings,width=width,name=f'width_{width}')
    row=search(env(protocol['search_cells']),settings,[1.]*config['action_blocks'])
    row.update(settings=settings,traces={})
    for cells in protocol['replay_cells']:
        r=replay(env(cells),row['actions'])
        path=output/f'w{width}_cells{cells}.json.gz'
        gzsave(path,r)
        row['traces'][str(cells)]=str(path)
    save(output/f'w{width}.json',row)
    return row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol',type=Path,default=Path('configs/regeneration_dp_width.json'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    p=json.loads(args.protocol.read_bytes());parent=Path(p['parent'])
    manifest=json.loads((parent/'manifest.json').read_bytes())
    for group in manifest.values():
        for k,h in group.items():
            if sha(k)!=h: raise ValueError(f'changed parent evidence {k}')
    origin=json.loads((parent/'contract.json').read_bytes())['parent_config']
    config,_=validate_control_gate(origin['protocol']['baseline'],Path.cwd())
    if config!=origin['config']:raise ValueError('model mismatch')
    w0,*widths=p['widths']
    baseline=json.loads((parent/'metrics.json').read_bytes())['cases'][p['corner']]
    if baseline['settings']['width']!=w0:raise ValueError('width mismatch')
    args.output.mkdir(exist_ok=False,parents=True)
    inputs={str(k):sha(k) for k in (args.protocol,parent/'manifest.json')}
    code={str(Path(__file__)):sha(__file__),**manifest['sources']}
    save(args.output/'contract.json',dict(protocol=p,config=config,inputs=inputs,sources=code))
    rows={w0:baseline}
    with ProcessPoolExecutor(max_workers=len(widths)) as pool:
        pending={pool.submit(run,w,args.output,baseline['settings'],p,config):w for w in widths}
        for f in as_completed(pending):
            w=pending[f];rows[w]=f.result()
            print(w,rows[w]['transitions'],rows[w]['search_time_s'],flush=True)
    if any(sha(k)!=h for k,h in (inputs|code).items()):raise ValueError('changed study source')
    save(args.output/'metrics.json',dict(cases={str(w):rows[w] for w in p['widths']}))
    save(args.output/'manifest.json',dict(inputs=inputs,sources=code,outputs={str(k):sha(k) for k in args.output.iterdir() if k.is_file()}))


if __name__=='__main__':main()
