"""Immutable final-checkpoint width comparison, using existing replay/audit helpers."""
import argparse
import json
import statistics
import time
from pathlib import Path
import numpy as np

from benchmark_circuit_control import gzsave, make_env, save, sha, sources
from report_regeneration_robustness import audit, read
from run_regeneration_robustness import scenario_setup
from f1energy.circuit_control import rollout


ROOT = Path('results/ppo-actor-width-evaluation-001')
PROTOCOL = Path('configs/regeneration_ppo_actor64.json')
RUNS = {32: Path('results/regeneration-multiseed-001'), 64: Path('results/regeneration-ppo-actor64-001')}


def verify_manifest(folder):
    manifest = read(folder/'manifest.json')
    count = 0
    for group in ('inputs', 'sources', 'outputs'):
        for path, digest in manifest[group].items():
            if sha(path) != digest:
                raise ValueError('Changed evidence: '+path)
            count += 1
    return count


def evaluate(width):
    import torch
    from stable_baselines3 import PPO
    torch.set_num_threads(1)
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    protocol = read(PROTOCOL)
    run = RUNS[width]
    checks = verify_manifest(run)
    base_contract = read(RUNS[32]/'contract.json')
    contract = read(run/'contract.json')
    matched_keys = ['baselines', 'training_seeds', 'steps_per_seed', 'checkpoint_steps',
                    'stochastic_evaluation_seeds', 'parallel_workers', 'refinement', 'rng_isolation', 'schedule']
    assert all(contract['protocol'][k] == base_contract['protocol'][k] for k in matched_keys)
    hp = contract['protocol']['hyperparameters']
    assert {k:v for k,v in hp.items() if k != 'net_arch'} == {k:v for k,v in base_contract['protocol']['hyperparameters'].items() if k != 'net_arch'}
    config = read(run/'seed-0'/'contract.json')['config']
    assert config == read(RUNS[32]/'seed-0'/'contract.json')['config']
    assert sha(RUNS[32]/'manifest.json') == protocol['width_comparison']['baseline_manifest_sha256']
    output = ROOT/f'actor-{width}'
    output.mkdir(parents=True, exist_ok=False)
    code = sources()
    for path in [__file__, 'scripts/benchmark_circuit_control.py', 'scripts/report_regeneration_robustness.py',
                 'scripts/run_regeneration_robustness.py', 'scripts/validate_regeneration.py']:
        code[str(Path(path))] = sha(path)
    inputs = {str(PROTOCOL): sha(PROTOCOL), str(run/'manifest.json'): sha(run/'manifest.json')}
    save(output/'contract.json', dict(width=width, run=str(run), protocol=protocol, sources=code, inputs=inputs))
    rows, models = [], []
    started = time.perf_counter()
    scenarios = [dict(name='nominal', parameter=None, value=None), *protocol['width_comparison']['transfer']]
    for seed in protocol['training_seeds']:
        folder = run/f'seed-{seed}'
        checks += verify_manifest(folder)
        path = folder/'checkpoint_16384.zip'
        inputs[str(path)] = sha(path)
        model = PPO.load(path, device='cuda:0')
        assert model.num_timesteps == protocol['steps_per_seed']
        tensors = model.policy.state_dict()
        expected = {'mlp_extractor.policy_net.0.weight': [width,8], 'mlp_extractor.policy_net.2.weight': [width,width],
                    'action_net.weight': [1,width], 'mlp_extractor.value_net.0.weight': [32,8],
                    'mlp_extractor.value_net.2.weight': [32,32], 'value_net.weight': [1,32]}
        assert all(list(tensors[k].shape) == shape for k,shape in expected.items())
        assert all(p.device.type == 'cuda' for p in model.policy.parameters())
        # PPO.load restores the actual saved training settings, independently of the JSON contract.
        for key,value in hp.items():
            if key not in ('net_arch', 'clip_range'):
                assert getattr(model,key) == value, key
        assert model.clip_range(1.) == hp['clip_range']
        count = lambda prefix: sum(t.numel() for k,t in tensors.items() if k.startswith(prefix))
        models.append(dict(seed=seed, checkpoint=str(path), sha256=sha(path), shapes={k:list(t.shape) for k,t in tensors.items()},
                           actor_parameters=count('mlp_extractor.policy_net')+count('action_net')+count('log_std'),
                           critic_parameters=count('mlp_extractor.value_net')+count('value_net'),
                           total_parameters=sum(t.numel() for t in tensors.values()), device='cuda:0'))
        for scenario in scenarios:
            case_config, reference, curve, vehicle = scenario_setup(config, scenario)
            for cells in (160,320):
                env = make_env(case_config, reference, curve, vehicle, cells)
                if scenario['name'] == 'nominal':
                    if cells == 320:
                        zero = read(run/'refined_zero.json.gz')
                    else:
                        baseline = Path(protocol['baselines'])
                        row = next(r for r in read(baseline/'metrics.json')['results'] if r['policy']=='zero' and r['cells']==cells)
                        zero = read(baseline/row['file'])
                    env.reference_times = np.array([r['duration_s'] for r in zero['trace']])
                tick = time.perf_counter()
                result = rollout(env, lambda obs: model.predict(obs, deterministic=True)[0])
                elapsed = time.perf_counter()-tick
                independent = audit(result, case_config, reference)
                if scenario['name'] == 'nominal':
                    suffix = 'fine' if cells == 160 else 'refined'
                    original = read(folder/f'checkpoint_16384_deterministic_{suffix}.json.gz')
                    assert result == original, 'nominal saved replay is not exactly reproduced'
                filename = output/f"{scenario['name']}_seed{seed}_{cells}.json.gz"
                gzsave(filename,result)
                rows.append(dict(width=width, seed=seed, scenario=scenario['name'], cells=cells, file=str(filename),
                                 duration_s=result['duration_s'], final_energy_j=result['final_energy_j'],
                                 feasible=result['feasible'], terminal_speed_error_mps=result['terminal_speed_error_mps'],
                                 evaluation_seconds=elapsed, **independent))
                save(output/'progress.json', rows)
                print(width, seed, scenario['name'], cells, result['duration_s'], result['feasible'], flush=True)
    assert all(sha(p)==digest for p,digest in (inputs|code).items())
    save(output/'metrics.json', dict(width=width, rows=rows, models=models, hash_checks=checks,
                                    wall_seconds=time.perf_counter()-started, training_performed=False))
    if any(not r['feasible'] for r in rows):
        save(output/'failure.json', dict(reason='Retained physically infeasible transfer replay(s).'))
    save(output/'manifest.json', dict(inputs=inputs,sources=code,outputs={str(p):sha(p) for p in output.iterdir() if p.is_file()}))


def report():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    protocol = read(PROTOCOL)
    verified = sum(verify_manifest(ROOT/f'actor-{w}') for w in RUNS)
    data = {w: read(ROOT/f'actor-{w}'/'metrics.json') for w in RUNS}
    rows = {(r['scenario'],r['seed'],r['width'],r['cells']):r for d in data.values() for r in d['rows']}
    summaries=[]
    scenarios=['nominal', *[s['name'] for s in protocol['width_comparison']['transfer']]]
    for scenario in scenarios:
        pairs=[]
        for seed in protocol['training_seeds']:
            a,b,c,d=[rows[scenario,seed,w,g] for g in (160,320) for w in (32,64)]
            gap=a['duration_s']-b['duration_s']; refined=c['duration_s']-d['duration_s']
            numerical=[]
            for width in RUNS:
                x,y=rows[scenario,seed,width,160],rows[scenario,seed,width,320]
                numerical.append(dict(width=width,relative_lap_time_error=abs(x['duration_s']-y['duration_s'])/y['duration_s'],
                    terminal_energy_error_j=abs(x['final_energy_j']-y['final_energy_j']),recovery_error_j=abs(x['recovered_j']-y['recovered_j'])))
            limits=protocol['refinement']
            numerical_pass=all(n['relative_lap_time_error']<=limits['max_relative_lap_time_error'] and n['terminal_energy_error_j']<=limits['max_terminal_energy_error_j'] and n['recovery_error_j']<=limits['max_recovery_error_j'] for n in numerical)
            discrepancy=abs(gap-refined)
            pairs.append(dict(seed=seed, gap_s=gap, refined_gap_s=refined, paired_discrepancy_s=discrepancy,
                              feasible=all(r['feasible'] for r in (a,b,c,d)), numerical=numerical,
                              numerical_passed=numerical_pass and discrepancy<=.005))
        gaps=[p['gap_s'] for p in pairs]
        summaries.append(dict(scenario=scenario,pairs=pairs,mean_gap_s=statistics.mean(gaps),sample_sd_gap_s=statistics.stdev(gaps),minimum_gap_s=min(gaps),maximum_gap_s=max(gaps)))
    figures=Path('figures/dissertation/ppo-actor-width-v1')
    figures.mkdir(parents=True,exist_ok=False)
    summary=dict(cases=summaries,hash_checks=verified,rows=list(rows.values()),architectures={str(w):data[w]['models'] for w in RUNS},
                 all_feasible=all(r['feasible'] for r in rows.values()),all_numerical_passed=all(p['numerical_passed'] for s in summaries for p in s['pairs']),training_performed=False)
    save(figures/'verification.json',summary)
    fig,axes=plt.subplots(1,3,figsize=(12,4.5),sharey=True)
    for ax,s in zip(axes,summaries):
        for pair in s['pairs']:
            seed=pair['seed']; marker='o' if pair['feasible'] else 'x'
            ax.plot(seed,pair['gap_s']*1000,marker=marker,color='#146b8a',ms=8)
            ax.plot(seed,pair['refined_gap_s']*1000,marker='_',color='#b86118',ms=12)
        ax.axhline(0,color='grey',lw=1);ax.set_xticks([0,1,2]);ax.set_xlabel('Matched training seed');ax.set_title(s['scenario'].replace('_',' '));ax.grid(alpha=.2)
    axes[0].set_ylabel('Width 32 minus width 64 lap time (ms)')
    fig.suptitle('Final deterministic actor-width comparison | 16,384 CUDA steps per seed')
    fig.text(.5,.015,'Blue: 160 cells/block; orange: 320. Positive favours width 64. Crosses: infeasible pair.\nAssumed Sakhir model; unchanged width-32 critic; no significance or convergence claim. Runs: regeneration-multiseed-001 / regeneration-ppo-actor64-001.',ha='center',fontsize=7)
    fig.tight_layout(rect=(0,.09,1,.93))
    for ext in ('png','pdf'):fig.savefig(figures/f'01_actor_width.{ext}',dpi=300)
    plt.close(fig)
    if not summary['all_feasible'] or not summary['all_numerical_passed']:
        save(figures/'failure.json',dict(reason='At least one frozen physical/numerical width check failed; see verification.json.'))
    save(figures/'manifest.json',dict(inputs={str(ROOT/f'actor-{w}'/'manifest.json'):sha(ROOT/f'actor-{w}'/'manifest.json') for w in RUNS},sources={str(Path(__file__)):sha(__file__)},outputs={str(p):sha(p) for p in figures.iterdir() if p.is_file()}))
    print(json.dumps({k:v for k,v in summary.items() if k not in ('rows','architectures')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--width',type=int,choices=[32,64])
    args=parser.parse_args()
    evaluate(args.width) if args.width else report()
