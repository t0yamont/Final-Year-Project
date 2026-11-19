"""Independently check saved transfer replays and export dissertation figures."""
import argparse
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def close(actual, expected, tolerance=1e-8):
    if not math.isfinite(actual) or abs(actual - expected) > tolerance:
        raise ValueError(f'arithmetic mismatch: {actual} versus {expected}')


def verify(folder):
    manifest = read(folder / 'manifest.json')
    checked = 0
    for group in ('inputs', 'sources', 'outputs'):
        for path, expected in manifest[group].items():
            if sha(path) != expected:
                raise ValueError('hash mismatch: ' + path)
            checked += 1
    contract, metrics = read(folder / 'contract.json'), read(folder / 'metrics.json')
    protocol, reference = contract['protocol'], contract['reference']
    scenarios = {s['name']: s for s in protocol['scenarios']}
    policies = protocol['fixed_policies'] + [f'ppo_seed{s}' for s in protocol['training_seeds']]
    expected_keys = {(s, c['blocks'], grid, p) for s in scenarios for c in protocol['cadences']
                     if c['blocks'] == 55 or s == 'nominal'
                     for grid in ('coarse', 'fine') for p in policies}
    rows = metrics['results']
    keys = [(r['scenario'], r['blocks'], r['grid'], r['policy']) for r in rows]
    if len(set(keys)) != len(keys) or set(keys) != expected_keys:
        raise ValueError('missing/duplicate scenario, grid or policy')
    by_key = dict(zip(keys, rows))
    expected_cases = {(s, b) for s, b, _, _ in expected_keys}
    case_keys = [(c['scenario'], c['blocks']) for c in metrics['cases']]
    if len(set(case_keys)) != len(case_keys) or set(case_keys) != expected_cases:
        raise ValueError('missing/duplicate scenario summaries')
    if set(metrics['nominal_fine_110_minus55_time_s']) != set(policies):
        raise ValueError('missing cadence policy comparison')
    grid_cache, audits, independent_pass = {}, [], {}
    for row in rows:
        if row['status'] != 'completed':
            raise ValueError('incomplete rollout; retain failed-run evidence')
        scenario = scenarios[row['scenario']]
        vehicle = dict(reference['vehicle'])
        if scenario['parameter'] in vehicle:
            vehicle[scenario['parameter']] = scenario['value']
        with gzip.open(folder / row['file'], 'rt', encoding='utf-8') as handle:
            replay = json.load(handle)
        trace = replay['trace']
        if len(trace) != row['blocks']:
            raise ValueError('decision count differs')
        grid_file = row['grid_file']
        if grid_file not in grid_cache:
            with gzip.open(folder / grid_file, 'rt', encoding='utf-8') as handle:
                grid_cache[grid_file] = json.load(handle)
        grid = grid_cache[grid_file]
        if len(grid['cell_speed_cap_mps']) != row['blocks'] * row['cells_per_block']:
            raise ValueError('physical cell count differs')
        prior_v = protocol['conditions']['initial_speed_mps']
        prior_e = protocol['conditions']['initial_energy_j']
        elapsed = 0.
        residuals, battery_errors = [], []
        for i, step in enumerate(trace):
            state = step['state']
            net_work = step['base_work_j'] + step['electrical_work_j'] - step['drag_work_j'] - step['friction_braking_work_j']
            residuals.append(.5 * vehicle['mass_kg'] * (state['speed_m_per_s']**2 - prior_v**2) - net_work)
            battery_errors.append(step['electrical_work_j'] - vehicle['discharge_efficiency'] * (prior_e - state['energy_j']))
            close(step['battery_draw_j'], prior_e - state['energy_j'])
            if state['energy_j'] < reference['reserve_j'] - 1e-5 or state['energy_j'] > prior_e + 1e-5:
                raise ValueError('reserve/non-regenerating battery constraint')
            if not 0 <= step['action'] <= 1 or step['duration_s'] <= 0:
                raise ValueError('action/duration constraint')
            if step['max_node_cap_excess_mps'] > protocol['gates']['cap_excess_mps']:
                raise ValueError('reported speed cap violation')
            cell = (i+1) * row['cells_per_block'] - 1
            if state['speed_m_per_s'] > grid['cell_speed_cap_mps'][cell] + 1e-5:
                raise ValueError('saved boundary exceeds physical cell cap')
            close(state['distance_m'], grid['distance_m'][cell+1], 1e-6)
            elapsed += step['duration_s']
            close(elapsed, state['elapsed_s'])
            prior_v, prior_e = state['speed_m_per_s'], state['energy_j']
        close(elapsed, row['duration_s'])
        close(replay['duration_s'], elapsed)
        close(replay['final_energy_j'], prior_e)
        close(row['final_energy_j'], prior_e)
        if not all(math.isfinite(v) for v in [prior_v, prior_e, *residuals, *battery_errors]):
            raise ValueError('non-finite replay values')
        terminal_error = prior_v - protocol['conditions']['terminal_speed_mps']
        close(row['terminal_speed_error_mps'], terminal_error)
        close(replay['terminal_speed_error_mps'], terminal_error)
        zero = by_key[row['scenario'], row['blocks'], row['grid'], 'zero']['duration_s']
        reward_reference = 0. if row['policy'] == 'zero' else zero
        close(row['reward_reference_time_s'], reward_reference)
        close(replay['reward_sum'], reward_reference - elapsed)
        if max(map(abs, residuals)) > 1 or abs(sum(residuals)) > 1 or max(map(abs, battery_errors)) > .01 or abs(sum(battery_errors)) > .01:
            raise ValueError('mechanical/battery identity failure')
        physical_pass = abs(terminal_error) < protocol['gates']['terminal_speed_error_mps']
        if physical_pass != bool(row['audit']['passed']) or physical_pass != bool(row['feasible']):
            raise ValueError('physical feasibility classification mismatch')
        independent_pass[row['scenario'], row['blocks'], row['grid'], row['policy']] = physical_pass
        if row['scenario'] == 'nominal' and row['blocks'] == 55 and row['policy'].startswith('ppo_seed'):
            seed = row['policy'].removeprefix('ppo_seed')
            old_grid = 'training' if row['grid'] == 'coarse' else 'fine'
            old_path = Path(protocol['source_run']) / f'seed-{seed}' / f'checkpoint_16384_deterministic_{old_grid}.json.gz'
            with gzip.open(old_path, 'rt', encoding='utf-8') as handle:
                old = json.load(handle)
            exact = all(replay[k] == old[k] for k in ('duration_s', 'final_energy_j', 'terminal_speed_error_mps'))
            exact = exact and [t['action'] for t in trace] == [t['action'] for t in old['trace']]
            if not exact or row['nominal_source_exact'] is not True:
                raise ValueError('nominal source checkpoint replay differs: ' + row['file'])
        audits.append({'file': row['file'], 'max_block_energy_residual_j': max(map(abs, residuals)),
                       'global_energy_residual_j': sum(residuals), 'max_battery_error_j': max(map(abs, battery_errors)),
                       'physical_pass': physical_pass, 'terminal_speed_error_mps': terminal_error})
    for case in metrics['cases']:
        scenario, blocks = case['scenario'], case['blocks']
        pair_keys = [p['policy'] for p in case['numerical_pairs']]
        if len(set(pair_keys)) != len(pair_keys) or set(pair_keys) != set(policies):
            raise ValueError('missing/duplicate numerical policy pair')
        local = {(g, p): by_key[scenario, blocks, g, p] for g in ('coarse', 'fine') for p in policies}
        for pair in case['numerical_pairs']:
            p = pair['policy']
            c, f = local['coarse', p]['duration_s'], local['fine', p]['duration_s']
            cz, fz = local['coarse', 'zero']['duration_s'], local['fine', 'zero']['duration_s']
            gap = abs((cz-c)-(fz-f))
            relative = abs(c-f)/f
            close(pair['gain_discrepancy_s'], gap)
            close(pair['relative_lap_time_error'], relative)
            passed = gap <= protocol['gates']['gain_error_s'] and relative <= protocol['gates']['relative_lap_time']
            passed = passed and all(independent_pass[scenario, blocks, g, policy]
                                    for g in ('coarse','fine') for policy in (p,'zero'))
            if bool(pair['passed']) != passed:
                raise ValueError('numerical gate classification mismatch')
        fine_feasible = all(independent_pass[scenario,blocks,'fine',p] for p in policies)
        if fine_feasible:
            best = min(protocol['fixed_policies'], key=lambda p: local['fine', p]['duration_s'])
            if best != case['strongest_fixed_policy']:
                raise ValueError('strongest baseline selection mismatch')
            advantage = [local['fine', best]['duration_s'] - local['fine', p]['duration_s'] for p in policies if p.startswith('ppo_seed')]
            close(case['ppo_advantage_over_strongest_fixed_s']['mean'], statistics.mean(advantage))
            close(case['ppo_advantage_over_strongest_fixed_s']['sample_sd'], statistics.stdev(advantage))
            for seed, value in zip(protocol['training_seeds'], advantage):
                close(case['per_seed_advantage_s'][f'ppo_seed{seed}'], value)
        elif 'ppo_advantage_over_strongest_fixed_s' in case:
            raise ValueError('infeasible comparison incorrectly aggregated')
        if bool(case['passed']) != all(p['passed'] for p in case['numerical_pairs']):
            raise ValueError('case gate classification mismatch')
    for policy, delta in metrics['nominal_fine_110_minus55_time_s'].items():
        close(delta, by_key['nominal',110,'fine',policy]['duration_s'] - by_key['nominal',55,'fine',policy]['duration_s'])
    if metrics['all_cases_completed_and_passed'] != all(c['passed'] for c in metrics['cases']):
        raise ValueError('study gate classification mismatch')
    return contract, metrics, dict(hash_checks=checked, replays_checked=len(audits),
        all_cases_completed_and_passed=metrics['all_cases_completed_and_passed'],
        physically_feasible_replays=sum(a['physical_pass'] for a in audits),
        max_block_energy_residual_j=max(a['max_block_energy_residual_j'] for a in audits),
        max_global_energy_residual_j=max(abs(a['global_energy_residual_j']) for a in audits),
        max_battery_error_j=max(a['max_battery_error_j'] for a in audits), replays=audits)


def figures(contract, metrics, output):
    colors, markers = ['#176b8a','#b86118','#805080'], ['o','s','^']
    labels = {'nominal':'Nominal', 'mass_minus10':'Mass 720 kg', 'mass_plus10':'Mass 880 kg',
              'drag_minus10':'Drag 0.9 kg/m', 'drag_plus10':'Drag 1.1 kg/m',
              'lateral_minus10':'Lateral limit 18 m/s²', 'lateral_plus10':'Lateral limit 22 m/s²',
              'smoothing5':'Smoothing 5 m', 'smoothing20':'Smoothing 20 m'}
    cases = [c for c in metrics['cases'] if c['blocks']==55]
    fig, ax = plt.subplots(figsize=(10,6.4))
    for i, case in enumerate(cases):
        if 'ppo_advantage_over_strongest_fixed_s' not in case:
            ax.text(.02,i,'No valid all-policy comparison: terminal constraint failed',
                    transform=ax.get_yaxis_transform(),ha='left',va='center',fontsize=9,color='#555555')
            continue
        stats = case['ppo_advantage_over_strongest_fixed_s']
        ax.errorbar(stats['mean'], i, xerr=stats['sample_sd'], color='#444444', fmt='D',
                    markersize=4, capsize=4, label='Mean ± sample SD (3 seeds)' if i==0 else None)
        for seed, (color, marker) in enumerate(zip(colors,markers)):
            ax.scatter(case['per_seed_advantage_s'][f'ppo_seed{seed}'], i+(seed-1)*.14,
                       color=color,marker=marker,s=35,label=f'Seed {seed}' if i==0 else None,zorder=4)
    ax.set_yticks(range(len(cases)), [labels[c['scenario']]+(' *' if not c['passed'] else '') for c in cases])
    ax.invert_yaxis(); ax.axvline(0,color='#555555',linestyle='--')
    ax.set(xlabel='Time saved versus each scenario’s strongest fixed baseline (s)',
           title='Unchanged PPO policies under model perturbations | 55 decisions/lap\n' + metrics['run_id'])
    ax.grid(axis='x',alpha=.2); ax.legend(loc='best',fontsize=9)
    fig.text(.5,.025,'Positive = PPO faster. One assumption varied at a time; ranges are not calibrated uncertainty.\n* Acceptance gate failed; infeasible comparisons omitted explicitly. Error bars describe seeds, not confidence intervals.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.09,1,1))
    for ext in ('png','pdf'):fig.savefig(output/f'01_model_transfer.{ext}',dpi=300)
    plt.close(fig)
    fig, axes = plt.subplots(1,2,figsize=(12,5.8))
    deltas=metrics['nominal_fine_110_minus55_time_s']; names=list(deltas)
    display={'zero':'Zero','half':'Half','full':'Full','spread':'Spread','exit_boost':'Exit boost',
             **{f'ppo_seed{s}':f'PPO seed {s}' for s in range(3)}}
    gains=[-deltas[n] for n in names]
    axes[0].barh(range(len(names)),gains,color=['#999999' if not n.startswith('ppo') else colors[int(n[-1])] for n in names])
    axes[0].set_yticks(range(len(names)),[display[n] for n in names]);axes[0].invert_yaxis()
    axes[0].axvline(0,color='#555555',linewidth=.8)
    axes[0].set(xlabel='Time saved by changing 55 to 110 decisions (s)',title='Nominal cadence/interface transfer')
    axes[0].grid(axis='x',alpha=.2);axes[0].set_axisbelow(True)
    case_list=metrics['cases'];gates=contract['protocol']['gates']
    for i,c in enumerate(case_list):
        coarse={(r['grid'],r['policy']):r for r in metrics['results'] if r['scenario']==c['scenario'] and r['blocks']==c['blocks']}
        gain_ratio=max(p['gain_discrepancy_s'] for p in c['numerical_pairs'])/gates['gain_error_s']
        time_ratio=max(abs(coarse['coarse',p['policy']]['duration_s']-coarse['fine',p['policy']]['duration_s'])/coarse['fine',p['policy']]['duration_s'] for p in c['numerical_pairs'])/gates['relative_lap_time']
        axes[1].scatter(gain_ratio,i-.1,color='#176b8a',marker='o',label='Gain error / 0.05 s' if i==0 else None)
        axes[1].scatter(time_ratio,i+.1,color='#b86118',marker='s',label='Lap error / 0.5%' if i==0 else None)
    axes[1].set_yticks(range(len(case_list)),[labels[c['scenario']]+f' ({c["blocks"]})'+(' *' if not c['passed'] else '') for c in case_list]);axes[1].invert_yaxis()
    axes[1].axvline(1,color='#555555',linestyle='--');axes[1].set_xlim(left=0)
    axes[1].set(xlabel='Largest policy error / predeclared threshold',title='Coarse/fine numerical checks')
    axes[1].legend(fontsize=8,loc='best');axes[1].grid(axis='x',alpha=.2)
    fig.suptitle('Fixed physical grids: 4,400 and 8,800 cells | '+metrics['run_id'])
    fig.text(.5,.02,'Same checkpoints, no retraining. At 110 decisions the observation lookahead also halves.\nRatios above 1 fail numerical gates. * Acceptance failed; terminal feasibility is checked separately.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.10,1,.94))
    for ext in ('png','pdf'):fig.savefig(output/f'02_cadence_numerical_gates.{ext}',dpi=300)
    plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    contract,metrics,audit=verify(args.input)
    metrics['run_id']=args.input.name
    args.output.mkdir(parents=True,exist_ok=False)
    figures(contract,metrics,args.output)
    (args.output/'verification.json').write_bytes((json.dumps(audit,indent=2)+'\n').encode('utf-8'))
    manifest=dict(inputs={str(args.input/'manifest.json'):sha(args.input/'manifest.json')},source_sha256=sha(__file__),
                  outputs={str(p):sha(p) for p in args.output.iterdir() if p.is_file()})
    (args.output/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({k:v for k,v in audit.items() if k!='replays'}))


if __name__=='__main__':main()
