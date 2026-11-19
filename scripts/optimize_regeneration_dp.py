"""Bounded forward dynamic programming on the existing regenerative circuit environment."""
import argparse
import json
import time
from pathlib import Path

from benchmark_circuit_control import gzsave, load_setup, make_env, save, sha, sources
from f1energy.circuit_control import rollout
from f1energy.circuit_training_gate import validate_control_gate


def replay(env, actions):
    return rollout(env, lambda _: [actions[env.index]])


def search(env, settings, incumbent):
    """Advance exact simulator states; approximate only the set of retained prefixes."""
    env.reset()
    frontier = [(env.state, env.recovered_j, env.discharged_j, ())]
    counts = []
    start = time.perf_counter()
    original = replay(env, incumbent)
    best = (original['duration_s'] if original['feasible'] else float('inf'), tuple(incumbent))
    for block in range(env.blocks):
        buckets = {}
        expansions = 0
        for state, recovered, discharged, prefix in frontier:
            for action in settings['actions']:
                env.index, env.state = block, state
                env.recovered_j, env.discharged_j = recovered, discharged
                env.step([action])
                expansions += 1
                path = prefix + (action,)
                if block == env.blocks-1:
                    if abs(env.state.speed_m_per_s-env.initial_speed)<1e-5:
                        best = min(best, (env.state.elapsed_s, path))
                    continue
                e = settings['energy_bin_j']
                key = (round(env.state.speed_m_per_s/settings['speed_bin_mps']),
                       round(env.state.energy_j/e), round(env.recovered_j/e), round(env.discharged_j/e))
                candidate = (env.state, env.recovered_j, env.discharged_j, path)
                if key not in buckets or env.state.elapsed_s < buckets[key][0].elapsed_s:
                    buckets[key] = candidate
        frontier = sorted(buckets.values(), key=lambda x: x[0].energy_j)
        width = settings['width']
        if len(frontier) > width:
            n = len(frontier)
            frontier = [min(frontier[i*n//width:(i+1)*n//width], key=lambda x: x[0].elapsed_s)
                        for i in range(width)]
        counts.append(dict(block=block+1, expansions=expansions, buckets=len(buckets), retained=len(frontier)))
    checked = replay(env, best[1])
    if not checked['feasible'] or abs(checked['duration_s']-best[0])>1e-8:
        raise ValueError('selected schedule failed exact search-grid replay')
    return dict(name=settings['name'], actions=list(best[1]), search_time_s=best[0],
                wall_seconds=time.perf_counter()-start, transitions=sum(x['expansions'] for x in counts),
                layers=counts, incumbent_time_s=original['duration_s'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol',type=Path,default=Path('configs/regeneration_dp_protocol.json'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    protocol=json.loads(args.protocol.read_text())
    config,_=validate_control_gate(protocol['baseline'],Path.cwd())
    parent=Path(protocol['ppo'])
    manifest=json.loads((parent/'manifest.json').read_text())
    for group in ('inputs','sources','outputs'):
        for path,digest in manifest[group].items():
            if sha(path)!=digest: raise ValueError('stale PPO evidence: '+path)
    if not json.loads((parent/'metrics.json').read_text())['all_seeds_completed_and_passed']:
        raise ValueError('PPO comparison study incomplete')
    inputs={str(p):sha(p) for p in (args.protocol,parent/'manifest.json',Path(protocol['baseline'])/'manifest.json')}
    code=sources()
    for p in (Path(__file__),Path('scripts/benchmark_circuit_control.py'),Path('src/f1energy/circuit_training_gate.py')):
        code[str(p)]=sha(p)
    args.output.mkdir(parents=True,exist_ok=False)
    save(args.output/'contract.json',dict(protocol=protocol,config=config,inputs=inputs,sources=code))
    ref,curve,vehicle=load_setup(config)
    grids={n:make_env(config,ref,curve,vehicle,n) for n in protocol['evaluation_cells']}
    incumbent=[1.]*config['action_blocks']
    cases=[]
    for settings in protocol['cases']:
        result=search(grids[protocol['search_cells']],settings,incumbent)
        incumbent=result['actions']
        for cells,env in grids.items():
            record=replay(env,incumbent)
            gzsave(args.output/f"{result['name']}_{cells}.json.gz",record)
        cases.append(result)
        save(args.output/'metrics.json',dict(cases=cases))
        print(result['name'],result['search_time_s'],result['transitions'],flush=True)
    if any(sha(path)!=digest for path,digest in (inputs|code).items()):
        raise RuntimeError('study inputs changed during search')
    save(args.output/'manifest.json',dict(inputs=inputs,sources=code,
        outputs={str(p):sha(p) for p in args.output.iterdir() if p.is_file()}))


if __name__=='__main__':main()
