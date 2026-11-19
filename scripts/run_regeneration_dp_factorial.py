"""Cross three DP settings while reusing verified endpoint searches."""
import argparse
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import product
from pathlib import Path

from benchmark_circuit_control import load_setup, make_env, sha, save, gzsave
from optimize_regeneration_dp import replay, search
from f1energy.circuit_training_gate import validate_control_gate


def run_corner(bits, parent_contract, protocol, output):
    config=parent_contract['config']
    endpoints=parent_contract['protocol']['cases']
    settings={key:endpoints[bits[i]][key] for i,fields in enumerate([
        ['actions'], ['width'], ['speed_bin_mps','energy_bin_j']]) for key in fields}
    name=''.join(map(str,bits))
    reference, curve, vehicle=load_setup(config)
    def env(cells):
        return make_env(config,reference,curve,vehicle,cells)
    result=search(env(protocol['search_cells']),dict(name=name,**settings),[1.]*config['action_blocks'])
    result.update(settings=settings,reused=False,traces={})
    for cells in [protocol['search_cells'],protocol['primary_cells'],protocol['check_cells']]:
        trace=replay(env(cells),result['actions'])
        path=output/f'{name}_{cells}.json.gz'
        gzsave(path,trace)
        result['traces'][str(cells)]=str(path)
    save(output/f'{name}.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol',type=Path,default=Path('configs/regeneration_dp_factorial.json'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();protocol=json.loads(args.protocol.read_text())
    parent=Path(protocol['parent']);manifest=json.loads((parent/'manifest.json').read_text())
    for hashes in manifest.values():
        for path,digest in hashes.items():
            if sha(path)!=digest:raise ValueError('changed parent evidence '+path)
    contract=json.loads((parent/'contract.json').read_text())
    config,_=validate_control_gate(contract['protocol']['baseline'],Path.cwd())
    if config!=contract['config']:raise ValueError('model config changed')
    args.output.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [args.protocol,parent/'manifest.json']}
    sources={**manifest['sources'],str(Path(__file__)):sha(__file__)}
    save(args.output/'contract.json',dict(protocol=protocol,parent_config=contract,inputs=inputs,sources=sources))
    cases={}
    originals=json.loads((parent/'metrics.json').read_text())['cases']
    for name,result,settings in zip(['000','111'],originals,contract['protocol']['cases']):
        if result['name']!=settings['name'] or result['search_time_s']>=result['incumbent_time_s']:
            raise ValueError('endpoint does not qualify for reuse')
        label=result['name']
        cases[name]=dict(result,name=name,settings=settings,reused=True,
            traces={str(c):str(parent/f'{label}_{c}.json.gz') for c in contract['protocol']['evaluation_cells']})
    with ProcessPoolExecutor(max_workers=protocol['workers']) as pool:
        pending=[pool.submit(run_corner,bits,contract,protocol,args.output) for bits in product(range(2),repeat=3)
                 if bits not in [(0,0,0),(1,1,1)]]
        for future in as_completed(pending):
            row=future.result();cases[row['name']]=row
            print(row['name'],row['transitions'],flush=True)
    save(args.output/'metrics.json',dict(cases=dict(sorted(cases.items()))))
    if any(sha(p)!=h for p,h in (inputs|sources).items()):raise RuntimeError('source or input changed')
    save(args.output/'manifest.json',dict(inputs=inputs,sources=sources,outputs={str(p):sha(p) for p in args.output.iterdir() if p.is_file()}))


if __name__=='__main__':main()
