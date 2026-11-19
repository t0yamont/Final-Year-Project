"""Independently audit retained robustness traces, including physical failures."""
import argparse
import gzip
import json
from itertools import combinations
from pathlib import Path
from types import SimpleNamespace

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from benchmark_circuit_control import save, sha
from validate_regeneration import audit_replay


def read(path):
    with (gzip.open(path, 'rt') if str(path).endswith('.gz') else open(path)) as stream:
        return json.load(stream)


def audit(record, config, reference):
    vehicle = SimpleNamespace(**reference['vehicle'])
    result = audit_replay(record, config, reference, vehicle)
    trace = record['trace']
    assert len(trace) == config['action_blocks'] == 55
    assert all(0 <= b['action'] <= 1 and b['duration_s'] > 0 for b in trace)
    assert abs(sum(b['duration_s'] for b in trace)-record['duration_s']) < 1e-8
    assert abs(trace[-1]['state']['energy_j']-record['final_energy_j']) < 1e-8
    terminal = trace[-1]['state']['speed_m_per_s']-config['initial_speed_mps']
    assert abs(terminal-record['terminal_speed_error_mps']) < 1e-10
    work = sum(b['base_work_j']+b['electrical_work_j']-b['drag_work_j']-b['friction_braking_work_j']-b['regenerative_braking_work_j'] for b in trace)
    global_residual = .5*vehicle.mass_kg*((terminal+config['initial_speed_mps'])**2-config['initial_speed_mps']**2)-work
    assert abs(global_residual) < 1
    assert abs(reference['initial_energy_j']+result['recovered_j']-result['discharged_j']-record['final_energy_j']) < .01
    feasible = abs(terminal) < 1e-5 and record['final_energy_j'] >= reference['reserve_j']-1e-5 and max(b['max_node_cap_excess_mps'] for b in trace) < 1e-5
    assert feasible == record['feasible']
    for b in trace:
        assert abs(b['charging_loss_j']-b['regenerative_braking_work_j']+b['battery_recovered_j']) < 1e-8
        assert abs(b['battery_discharged_j']-b['electrical_work_j']/vehicle.discharge_efficiency) < 1e-8
        assert b['battery_discharged_j'] <= vehicle.electrical_limit_w*b['duration_s']/vehicle.discharge_efficiency+1e-5
    return dict(**result, global_work_residual_j=global_residual)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('results/regeneration-robustness-001'))
    parser.add_argument('--figures', type=Path, default=Path('figures/dissertation/regeneration-robustness-v1'))
    args = parser.parse_args()
    checked = 0
    manifest = read(args.input/'manifest.json')
    for group in manifest.values():
        for path, digest in group.items():
            assert sha(path) == digest, path
            checked += 1
    contract = read(args.input/'contract.json')
    protocol = contract['protocol']
    metrics = read(args.input/'metrics.json')
    assert not metrics['errors'], metrics['errors']
    cases = {c['scenario']: c for c in metrics['cases']}
    assert set(cases) == {s['name'] for s in protocol['scenarios']}
    gates = protocol['gates']
    policies = [*protocol['fixed_policies'], *[f'ppo_seed{s}' for s in protocol['seeds']], 'frozen_dp', 'replanned_dp']
    summaries, audits = [], []
    for scenario in protocol['scenarios']:
        name = scenario['name']; case = cases[name]
        setup = read(args.input/name/'setup.json')
        rows = {(r['cells'], r['policy']): r for r in case['results']}
        assert set(rows) == {(c, p) for c in protocol['evaluation_cells'] for p in policies}
        if case['search']['status'] == 'completed':
            search = case['search']
            assert search['transitions'] == sum(layer['expansions'] for layer in search['layers'])
            assert search['transitions'] <= 55*16*5
            assert all(layer['retained'] <= 16 for layer in search['layers'])
        for row in rows.values():
            if row['status'] != 'completed':
                assert row['policy'] == 'replanned_dp' and case['search']['status'] == 'failed' and case['search']['actions'] is None
                continue
            record = read(row['file'])
            result = audit(record, setup['config'], setup['reference'])
            assert all(abs(result[key]-value) < 1e-8 for key,value in row['audit'].items())
            assert record['feasible'] == row['feasible']
            assert abs(record['duration_s']-row['duration_s']) < 1e-8
            if row['policy'] in ('frozen_dp', 'replanned_dp'):
                expected = contract['frozen_original_actions']['refined']['actions'] if row['policy'] == 'frozen_dp' else case['search']['actions']
                assert [b['action'] for b in record['trace']] == [float(np.float32(a)) for a in expected]
            audits.append(dict(file=row['file'], **result))
        numerical = []
        for policy in policies:
            a, b = rows[160, policy], rows[320, policy]
            if a['status'] != 'completed' or b['status'] != 'completed':
                numerical.append(dict(policy=policy, status='unavailable', passed=False)); continue
            check = dict(relative_lap_change=abs(a['duration_s']-b['duration_s'])/b['duration_s'],
                         terminal_energy_change_j=abs(a['final_energy_j']-b['final_energy_j']),
                         recovered_change_j=abs(a['audit']['recovered_j']-b['audit']['recovered_j']))
            numerical.append(dict(policy=policy, status='completed', **check, passed=all(check[k] <= gates[k] for k in check)))
        pairs = []
        for a, b in combinations(policies, 2):
            rr = [rows[c, p] for c in (160, 320) for p in (a,b)]
            if any(r['status'] != 'completed' for r in rr):
                pairs.append(dict(a=a,b=b,status='unavailable',passed=False)); continue
            change = abs((rr[0]['duration_s']-rr[1]['duration_s'])-(rr[2]['duration_s']-rr[3]['duration_s']))
            pairs.append(dict(a=a,b=b,status='completed',paired_gap_change_s=change,passed=change <= gates['paired_gap_change_s']))
        feasible_fixed = [p for p in protocol['fixed_policies'] if rows[160,p]['feasible']]
        strongest = min(feasible_fixed, key=lambda p: rows[160,p]['duration_s']) if feasible_fixed else None
        primary = {p: rows[160,p] for p in policies}
        ppo = [primary[f'ppo_seed{s}'] for s in protocol['seeds']]
        all_physical = all(r['status'] == 'completed' and r['feasible'] for r in rows.values())
        summary = dict(scenario=name, primary=primary, strongest_feasible_fixed=strongest,
                       all_controllers_feasible=all_physical, numerical=numerical, pairs=pairs,
                       all_numerical_checks_passed=all(r['passed'] for r in numerical+pairs),
                       ppo_feasible_seeds=sum(r['feasible'] for r in ppo), search=case['search'])
        if strongest and all(r['feasible'] for r in ppo):
            summary['ppo_mean_s'] = float(np.mean([r['duration_s'] for r in ppo]))
            summary['ppo_sample_sd_s'] = float(np.std([r['duration_s'] for r in ppo],ddof=1))
            summary['ppo_mean_advantage_s'] = primary[strongest]['duration_s']-summary['ppo_mean_s']
        summaries.append(summary)
    # Nominal is a matched control for the changed cases, not a new selected schedule.
    nominal = cases['nominal']['search']
    original = contract['frozen_original_actions']['refined']
    assert nominal['actions'] == original['actions']
    assert abs(nominal['search_time_s']-original['search_time_s']) < 1e-8
    args.figures.mkdir(parents=True,exist_ok=False)
    record = dict(cases=summaries, hashes_checked=checked, saved_replays_checked=len(audits), audits=audits,
                  all_cases_passed=all(s['all_controllers_feasible'] and s['all_numerical_checks_passed'] for s in summaries),
                  thresholds=gates, nominal_replan_reproduces_original=True, training_performed=False)
    save(args.figures/'verification.json',record)
    paths = [args.figures/'verification.json']
    def finish(fig, name):
        fig.tight_layout(rect=(0,.06,1,.96))
        fig.text(.5,.012,'regeneration-robustness-001 | Assumed model; crosses mark infeasible laps. No training or optimality claim.',ha='center',fontsize=8)
        for ext in ('png','pdf'):
            path=args.figures/f'{name}.{ext}';fig.savefig(path,dpi=300);paths.append(path)
        plt.close(fig)
    fig, axes = plt.subplots(2,3,figsize=(13,7.5))
    colors=['#999999']*5+['#146b8a']*3+['#b86118','#6a4c93']
    for ax,summary in zip(axes.flat,summaries):
        for i,p in enumerate(policies):
            row=summary['primary'][p]
            if row['status'] != 'completed':
                ax.text(i,.98,'N/A',ha='center',va='top',rotation=90,transform=ax.get_xaxis_transform(),fontsize=7);continue
            ax.plot(i,row['duration_s'],marker='o' if row['feasible'] else 'x',color=colors[i],ms=6)
        ax.set_title(summary['scenario'].replace('_',' '));ax.set_xticks(range(10),policies,rotation=60,fontsize=7)
        ax.set_ylabel('Simulated lap time (s)');ax.grid(alpha=.2)
    axes.flat[-1].axis('off')
    axes.flat[-1].text(0,.8,'160 cells per action block\n55 fixed action boundaries\nBlue: unchanged PPO seeds\nOrange: frozen original DP\nPurple: model-aware DP replan\nN/A: bounded search failed',va='top')
    finish(fig,'01_transfer_feasibility')
    fig,axes=plt.subplots(1,2,figsize=(12,4.8))
    for i,summary in enumerate(summaries):
        rows=list(summary['primary'].values());available=[r for r in rows if r['status']=='completed']
        axes[0].bar(i,sum(r['feasible'] for r in available),color='#146b8a')
        axes[0].text(i,10.2,f"{sum(r['feasible'] for r in available)}/10",ha='center',fontsize=8)
        values=[r['paired_gap_change_s']*1000 for r in summary['pairs'] if r['status']=='completed']
        axes[1].plot(i,max(values),'o',color='#b86118')
    labels=[s['scenario'].replace('_','\n') for s in summaries]
    for ax in axes:ax.set_xticks(range(5),labels,fontsize=8);ax.grid(axis='y',alpha=.2)
    axes[0].set(ylabel='Feasible controllers on primary grid',ylim=(0,11),title='Physical feasibility and search availability')
    axes[1].axhline(5,color='black',ls=':',label='Frozen 5 ms gate');axes[1].legend()
    axes[1].set(ylabel='Maximum paired gap change (ms)',title='All available controller pairs: 160 versus 320 cells')
    finish(fig,'02_feasibility_grid_checks')
    save(args.figures/'manifest.json',dict(inputs={str(args.input/'manifest.json'):sha(args.input/'manifest.json')},sources={str(Path(__file__)):sha(__file__)},outputs={str(p):sha(p) for p in paths}))
    print(json.dumps(dict(replays=len(audits),hashes=checked,all_cases_passed=record['all_cases_passed'],cases=[dict(scenario=s['scenario'],feasible=s['all_controllers_feasible'],numerical=s['all_numerical_checks_passed']) for s in summaries])))


if __name__ == '__main__':
    main()
