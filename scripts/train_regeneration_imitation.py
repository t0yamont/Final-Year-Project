"""Bounded CUDA-only imitation of hash-verified regenerative DP schedules."""
import argparse
from pathlib import Path
import time
from types import SimpleNamespace

import matplotlib.pyplot as plt
import numpy as np
import torch

from benchmark_circuit_control import gzsave, make_env, save, sha, sources
from report_regeneration_robustness import audit, read
from run_regeneration_robustness import scenario_setup
from f1energy.circuit_control import rollout
from f1energy.circuit_training_gate import validate_control_gate
from f1energy.training_device import require_cuda, verify_cuda_training


def verify_hashes(hashes):
    for path, digest in hashes.items():
        if sha(path) != digest:
            raise ValueError(f'Changed evidence: {path}')


def teacher_replay(protocol, config, scenario, parent, cells):
    name = scenario['name']
    folder = parent / name
    setup, reference, curve, vehicle = scenario_setup(config, scenario)
    assert read(folder / 'setup.json') == dict(config=setup, reference=reference)
    schedule = read(folder / 'search.json')
    assert schedule['status'] == 'completed'
    actions = schedule['actions']
    assert len(actions) == protocol['action_blocks'] and set(actions) <= {0, .25, .5, .75, 1}
    env = make_env(setup, reference, curve, vehicle, cells)
    rows = []

    def policy(observation):
        index = env.index
        action = actions[index]
        rows.append(dict(scenario=name, block=index, observation=observation.tolist(), action=action))
        return [action]

    replay = rollout(env, policy)
    archived = read(folder / f'replanned_dp_{cells}.json.gz')
    assert replay == archived and replay['feasible'], (name, cells)
    assert [row['block'] for row in rows] == list(range(protocol['action_blocks']))
    assert [row['action'] for row in rows] == [block['action'] for block in archived['trace']]
    observations = np.array([row['observation'] for row in rows])
    assert observations.shape == (protocol['action_blocks'], 8) and np.isfinite(observations).all()
    assert len(np.unique(observations, axis=0)) == protocol['action_blocks']
    return rows, dict(scenario=name, cells=cells, duration_s=replay['duration_s'],
                      final_energy_j=replay['final_energy_j'], feasible=replay['feasible'],
                      **audit(archived, setup, reference))


def network(width, device):
    return torch.nn.Sequential(torch.nn.Linear(8, width), torch.nn.Tanh(),
                               torch.nn.Linear(width, width), torch.nn.Tanh(),
                               torch.nn.Linear(width, 1)).to(device)


def fit(protocol, output, x, y, width, seed):
    device = x.device
    torch.manual_seed(seed)
    torch.cuda.reset_peak_memory_stats(device)
    started = time.perf_counter()
    model = network(width, device)
    optimizer = torch.optim.Adam(model.parameters(), lr=protocol['learning_rate'], capturable=True)
    criterion = torch.nn.MSELoss()
    with torch.no_grad():
        initial_mse = criterion(model(x), y).item()
    for _ in range(protocol['epochs']):
        optimizer.zero_grad(set_to_none=True)
        loss = criterion(model(x), y)
        loss.backward()
        optimizer.step()
    # Adapt the shared PPO-format checker and explicitly require every tensor.
    evidence = verify_cuda_training(SimpleNamespace(policy=SimpleNamespace(parameters=model.parameters, optimizer=optimizer)))
    assert evidence['gradient_tensors'] == evidence['parameter_tensors']
    assert evidence['cuda_optimizer_moment_tensors'] == 2 * evidence['parameter_tensors']
    steps = [state['step'] for state in optimizer.state.values()]
    assert len(steps) == evidence['parameter_tensors']
    assert all(step.device == device and step.item() == protocol['epochs'] for step in steps)
    assert all(parameter.device == device and torch.isfinite(parameter).all() for parameter in model.parameters())
    assert all(torch.isfinite(state[key]).all() for state in optimizer.state.values() for key in ('exp_avg', 'exp_avg_sq'))
    elapsed = time.perf_counter() - started

    checkpoint = output / f'width{width}_seed{seed}.pt'
    torch.save(model.state_dict(), checkpoint)
    reloaded = network(width, device)
    reloaded.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=True))
    model.eval()
    reloaded.eval()
    assert all(torch.equal(a, b) for a, b in zip(model.parameters(), reloaded.parameters()))
    with torch.inference_mode():
        raw = model(x)
        requested = raw.clamp(0, 1)
        assert torch.equal(requested, reloaded(x).clamp(0, 1))
        final_mse = criterion(raw, y).item()
        clamped_mse = criterion(requested, y).item()
        predictions = torch.cat((raw, requested), dim=1).tolist()
    return model, reloaded, dict(width=width, seed=seed, checkpoint=str(checkpoint),
                                parameter_count=sum(p.numel() for p in model.parameters()),
                                input_device=str(x.device), target_device=str(y.device), cuda_adam_step_tensors=len(steps),
                                initial_mse=initial_mse, final_mse=final_mse, clamped_mse=clamped_mse,
                                fit_seconds=elapsed, fit_prediction_reload_exact=True, cuda=evidence), predictions


def evaluate(output, cases, models, grids):
    rows = []
    for (width, seed), (model, reloaded) in models.items():
        device = next(reloaded.parameters()).device
        for scenario, config, reference, curve, vehicle in cases:
            name = scenario['name']
            for cells in grids:
                env = make_env(config, reference, curve, vehicle, cells)
                observations = []

                @torch.inference_mode()
                def policy(observation):
                    observations.append(observation.tolist())
                    x = torch.as_tensor(observation, device=device).unsqueeze(0)
                    action = reloaded(x).clamp(0, 1)
                    assert torch.equal(action, model(x).clamp(0, 1))
                    return [action.item()]

                started = time.perf_counter()
                result = rollout(env, policy)
                elapsed = time.perf_counter() - started
                assert len(observations) == len(result['trace']) == env.blocks
                independent = audit(result, config, reference)
                path = output / f'{name}_width{width}_seed{seed}_{cells}.json.gz'
                gzsave(path, dict(**result, pre_action_observations=observations))
                rows.append(dict(scenario=name, split=scenario['split'], width=width, seed=seed, cells=cells, file=str(path),
                                 duration_s=result['duration_s'], feasible=result['feasible'],
                                 final_energy_j=result['final_energy_j'], terminal_speed_error_mps=result['terminal_speed_error_mps'],
                                 evaluation_seconds=elapsed, reloaded_actions_checked=len(observations), **independent))
                print(f"{name:14} width={width} seed={seed} cells={cells} {result['duration_s']:.9f} s feasible={result['feasible']}", flush=True)
    return rows


def comparisons(protocol, rows):
    index = {(r['scenario'], r['seed'], r['width'], r['cells']): r for r in rows}
    limits = protocol['gates']
    pairs = []
    for scenario in protocol['evaluation']:
        name = scenario['name']
        for seed in protocol['seeds']:
            a, b, c, d = [index[name, seed, w, g] for g in protocol['evaluation_cells'] for w in protocol['widths']]
            numerical = []
            for x, y in ((a, c), (b, d)):
                values = dict(relative_lap_change=abs(x['duration_s']-y['duration_s'])/y['duration_s'],
                              terminal_energy_change_j=abs(x['final_energy_j']-y['final_energy_j']),
                              recovered_change_j=abs(x['recovered_j']-y['recovered_j']))
                numerical.append(dict(width=x['width'], **values, passed=all(v <= limits[k] for k, v in values.items())))
            gap, refined = a['duration_s']-b['duration_s'], c['duration_s']-d['duration_s']
            change = abs(gap-refined)
            pairs.append(dict(scenario=name, split=scenario['split'], seed=seed, gap_160_s=gap, gap_320_s=refined,
                              paired_gap_change_s=change, paired_check_passed=change <= limits['paired_gap_change_s'],
                              feasible_160=a['feasible'] and b['feasible'], feasible_320=c['feasible'] and d['feasible'],
                              numerical=numerical))
    return pairs


def plot(folder, protocol, pairs, run_name):
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.8), sharey=True)
    titles = ['Nominal (in sample)', 'Initial energy 1.5 MJ', 'Drag 1.05 kg/m', 'Drag 1.10 kg/m']
    for ax, title, scenario in zip(axes, titles, protocol['evaluation']):
        for pair in (p for p in pairs if p['scenario'] == scenario['name']):
            for cells, offset, color in ((160, -.1, '#146b8a'), (320, .1, '#bd6219')):
                marker = 'o' if pair[f'feasible_{cells}'] else 'x'
                ax.plot(pair['seed']+offset, pair[f'gap_{cells}_s']*1000, marker=marker, color=color, ms=7)
        ax.axhline(0, color='#666666', lw=1)
        ax.set(title=title, xticks=protocol['seeds'], xlabel='Matched seed')
        ax.grid(axis='y', alpha=.25)
    axes[0].set_ylabel('Width 32 minus width 64 lap time (ms)')
    fig.suptitle('DP schedule imitation on regenerative Sakhir')
    fig.text(.5, .025, 'Blue: 160 cells/block. Orange: 320. Crosses: one or both laps infeasible. Positive favours width 64 if feasible.\n'
             f'{run_name} | 500 CUDA updates per model, assessed at the final epoch.', ha='center', fontsize=8)
    fig.tight_layout(rect=(0, .14, 1, .92))
    for ext in ('png', 'pdf'):
        fig.savefig(folder / f'01_imitation_width.{ext}', dpi=300)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, default=Path('configs/regeneration_imitation_pilot.json'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--figures', type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    protocol = read(args.protocol)
    parent_manifest = Path(protocol['teacher_manifest'])
    width_protocol = Path(protocol['ppo_transfer_protocol'])
    anchored = {str(parent_manifest): protocol['teacher_manifest_sha256'],
                str(width_protocol): protocol['ppo_transfer_protocol_sha256']}
    verify_hashes(anchored)
    parent = parent_manifest.parent
    manifest = read(parent_manifest)
    for group in ('inputs', 'sources', 'outputs'):
        verify_hashes(manifest[group])
    parent_protocol = read(parent / 'contract.json')['protocol']
    config, _ = validate_control_gate(parent_protocol['baseline'], Path.cwd())
    cases = {s['name']: s for s in parent_protocol['scenarios']}
    assert protocol['gates'] == parent_protocol['gates']
    assert protocol['evaluation_cells'] == parent_protocol['evaluation_cells']
    assert protocol['teacher_cells'] == protocol['evaluation_cells'][0]
    assert protocol['action_blocks'] == config['action_blocks'] == 55
    fit_names = protocol['fit_scenarios']
    evaluations = {s['name']: s for s in protocol['evaluation']}
    assert len(set(fit_names)) == len(fit_names) == 4
    assert len(evaluations) == len(protocol['evaluation'])
    assert {name for name, s in evaluations.items() if s['split'] == 'in_sample'} == {'nominal'}
    assert set(fit_names).isdisjoint(name for name, s in evaluations.items() if s['split'] == 'held_out')
    assert {k: v for k, v in evaluations['high_drag'].items() if k != 'split'} == cases['high_drag']
    for transfer in read(width_protocol)['width_comparison']['transfer']:
        assert evaluations[transfer['name']] == dict(transfer, split='held_out')
    expected = [parent / name / file for name in (*fit_names, 'high_drag')
                for file in ('setup.json', 'search.json', 'replanned_dp_160.json.gz')]
    expected.append(parent / 'high_drag' / 'replanned_dp_320.json.gz')
    assert set(map(str, expected)) <= set(manifest['outputs'])

    reference_path = Path(config['reference_config'])
    inputs = {str(p): sha(p) for p in (args.protocol, reference_path, Path(read(reference_path)['geometry']))} | anchored
    code = sources()
    for path in (Path(__file__).resolve().relative_to(Path.cwd()), Path('scripts/benchmark_circuit_control.py'),
                 Path('scripts/report_regeneration_robustness.py'), Path('scripts/run_regeneration_robustness.py'),
                 Path('scripts/optimize_regeneration_dp.py'), Path('scripts/validate_regeneration.py'),
                 Path('src/f1energy/training_device.py'), Path('src/f1energy/circuit_training_gate.py')):
        code[str(path)] = sha(path)

    torch.set_num_threads(1)
    device = require_cuda()
    if args.output.exists() or args.figures.exists():
        raise FileExistsError('Choose fresh experiment and figure directories')
    args.output.mkdir(parents=True, exist_ok=False)
    dataset, teachers = [], []
    for name in fit_names:
        rows, teacher = teacher_replay(protocol, config, cases[name], parent, protocol['teacher_cells'])
        dataset.extend(rows)
        teachers.append(teacher)
    keys = {(row['scenario'], row['block']) for row in dataset}
    assert len(keys) == len(dataset) == len(fit_names) * protocol['action_blocks']
    data = args.output / 'teacher_examples.json'
    save(data, dataset)
    inputs[str(data)] = sha(data)
    parent_checks = sum(len(manifest[g]) for g in ('inputs', 'sources', 'outputs'))
    save(args.output / 'contract.json', dict(protocol=protocol, physical_config=config, inputs=inputs, sources=code,
                                            verified_parent_hashes=parent_checks, fit_teachers=teachers, cuda=device))
    verify_hashes(inputs | code)
    print(f'Frozen contract, {parent_checks} parent hashes, {len(dataset)} pre-action fit examples, {device["gpu_name"]}', flush=True)

    x = torch.tensor([row['observation'] for row in dataset], dtype=torch.float32, device=device['device'])
    y = torch.tensor([[row['action']] for row in dataset], dtype=torch.float32, device=device['device'])
    models, fits = {}, []
    for width in protocol['widths']:
        for seed in protocol['seeds']:
            model, reloaded, evidence, prediction = fit(protocol, args.output, x, y, width, seed)
            models[width, seed] = model, reloaded
            fits.append(evidence)
            path = args.output / f'width{width}_seed{seed}_fit_predictions.json'
            save(path, [dict(scenario=row['scenario'], block=row['block'], teacher_action=row['action'],
                             raw_output=p[0], requested_action=p[1]) for row, p in zip(dataset, prediction)])
            print(f'Fitted width={width}, seed={seed}, final MSE={evidence["final_mse"]:.8f}, {evidence["fit_seconds"]:.2f} s',
                  flush=True)
    assert len(fits) == len(models) == len(protocol['widths']) * len(protocol['seeds'])
    save(args.output / 'fit_metrics.json', fits)

    eval_cases = [(s, *scenario_setup(config, s)) for s in protocol['evaluation']]
    rows = evaluate(args.output, eval_cases, models, protocol['evaluation_cells'])
    assert len(rows) == len(models) * len(eval_cases) * len(protocol['evaluation_cells'])
    pairs = comparisons(protocol, rows)
    high_drag_teacher = [teacher_replay(protocol, config, cases['high_drag'], parent, cells)[1]
                         for cells in protocol['evaluation_cells']]
    physical_pass = all(r['feasible'] for r in rows)
    numerical_pass = all(p['paired_check_passed'] and all(n['passed'] for n in p['numerical']) for p in pairs)
    summary = dict(fits=fits, rows=rows, pairs=pairs, fit_example_count=len(dataset), held_out_reference=high_drag_teacher,
                   all_feasible=physical_pass, all_numerical_passed=numerical_pass,
                   all_checks_passed=physical_pass and numerical_pass, wall_seconds=time.perf_counter()-started)
    save(args.output / 'metrics.json', summary)
    if not summary['all_checks_passed']:
        save(args.output / 'failure.json', dict(
            physical=[r for r in rows if not r['feasible']],
            paired_numerical=[p for p in pairs if not p['paired_check_passed']],
            individual_numerical=[p for p in pairs if any(not n['passed'] for n in p['numerical'])]))
    verify_hashes(inputs | code)
    output_hashes = {str(path): sha(path) for path in sorted(args.output.iterdir()) if path.is_file()}
    run_manifest = args.output / 'manifest.json'
    save(run_manifest, dict(inputs=inputs, sources=code, outputs=output_hashes))
    args.figures.mkdir(parents=True, exist_ok=False)
    plot(args.figures, protocol, pairs, args.output.name)
    save(args.figures / 'manifest.json', dict(inputs={str(run_manifest): sha(run_manifest)}, sources=code,
                                             outputs={str(p): sha(p) for p in args.figures.iterdir()}))
    print(f'Completed {len(rows)} rollouts, {sum(r["feasible"] for r in rows)} feasible, '
          f'{sum(p["paired_check_passed"] for p in pairs)}/{len(pairs)} paired grid checks passed, '
          f'{summary["wall_seconds"]:.2f} s before plotting', flush=True)


if __name__ == '__main__':
    main()
