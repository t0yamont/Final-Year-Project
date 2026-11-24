"""Run the matched Bahrain terminal-constraint CUDA experiment and its four-arm ablation."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

import gymnasium as gym
import numpy as np
from stable_baselines3 import __version__ as sb3_version
import torch

from bahrain_finish_constraint import build_constrained_env, prepare_constraint
from bahrain_pace_model import build_env
from benchmark_circuit_control import gzsave, save, sha
from evaluate_bahrain_learned_transfer import bind, from_manifest, read_and_check
from f1energy.circuit_control import baseline_policy, rollout
from f1energy.training_device import require_cuda
from train_bahrain_algorithm_width import ALGORITHMS, TerminalReward, cuda_evidence, shape_checks, utc_now, verify_hashes
from validate_regeneration import audit_replay
from verify_bahrain_deployment import read


CONFIG = Path("configs/bahrain_finish_constraint.json")
OUTPUT = Path("results/bahrain-finish-constraint-001")
ARMS = ("penalty_raw", "penalty_guarded", "constrained_raw", "constrained_guarded")


def prefix(method, width, seed):
    return f"{method.lower()}_{width}_seed{seed}"


def grids(protocol):
    return tuple(protocol[f"{grid}_cells_per_block"] for grid in ("training", "primary", "refined"))


def frozen_design():
    config = read(CONFIG)
    parent = config["parent_manifest"]
    manifest_path = Path(parent["path"])
    inputs = {CONFIG.as_posix(): sha(CONFIG)}
    bind(manifest_path, parent["sha256"], inputs)
    manifest = read(manifest_path)
    parent_root = manifest_path.parent
    design = read(from_manifest(parent_root / "contract.json", manifest, "outputs", inputs))
    for name in ("metrics.json", "preflight.json"):
        from_manifest(parent_root / name, manifest, "outputs", inputs)
    if not read(parent_root / "preflight.json")["passed"]:
        raise ValueError("The penalty-only parent preflight did not pass")
    for path, digest in manifest["inputs"].items():
        bind(path, digest, inputs)
    sources = {}
    for path, digest in manifest["sources"].items():
        bind(path, digest, sources)
    for path in (Path(__file__), Path(__file__).with_name("bahrain_finish_constraint.py")):
        relative = path.resolve().relative_to(Path.cwd()).as_posix()
        bind(relative, sha(path), sources)

    original = read(parent_root / "metrics.json")["rows"]
    legacy_rows = []
    for row in original:
        from_manifest(row["file"], manifest, "outputs", inputs)
        if "checkpoint" in row:
            checkpoint = from_manifest(row["checkpoint"], manifest, "outputs", inputs)
            from_manifest(checkpoint.with_suffix(".json"), manifest, "outputs", inputs)
            legacy_rows.append(dict(row, arm="penalty_raw"))
        else:
            name = "planner" if row["policy"] == "selected" else row["policy"]
            legacy_rows.append(dict(row, arm="baseline_raw", policy=name, method=None, width=None, seed=None))
    for cells in grids(design["protocol"]):
        trace_path = from_manifest(parent_root / f"spread_{cells}.json.gz", manifest, "outputs", inputs)
        if [b["duration_s"] for b in read(trace_path)["trace"]] != design["reference_block_times_s"][str(cells)]:
            raise ValueError("The saved reference reward differs from the signed spread replay")
    design.update(experiment=config, inputs=inputs, sources=sources, legacy_rows=legacy_rows)
    return design


def environment(design, cells, guarded):
    model = design["model"]
    if guarded:
        env = build_constrained_env(model, cells, design["certificates"][str(cells)])
    else:
        env = build_env(model, cells)
    env.reference_times = np.array(design["reference_block_times_s"][str(cells)])
    return env


def guard_counts(lap, certificate, max_probes):
    checks = [(block, block["finish_constraint"]) for block in lap["trace"]]
    proposed = np.array([check["proposed_action"] for _, check in checks])
    executed = np.array([block["action"] for block, _ in checks])
    if not (np.isfinite(proposed).all() and np.all((0 <= proposed) & (proposed <= 1))):
        raise ValueError("Invalid proposed action in guard trace")
    probes = []
    for index, (block, check) in enumerate(checks):
        count = check["lookahead_transitions"]
        assert count >= 0 and isinstance(count, int)
        assert check["issued_action"] == block["action"]
        assert check["changed"] == (check["proposed_action"] != check["issued_action"])
        assert check["protected_draw_j"] == certificate["protected_draw_j"]
        if index < certificate["suffix_start_index"]:
            assert check["phase"] == "prefix" and count == 0
            assert check["issued_action"] == min(check["proposed_action"], check["prefix_action_ceiling"])
            assert block["duration_s"] <= certificate["zero_block_durations_s"][index] + 1e-7
            headroom = min(check["available_charge_before_j"] - block["battery_draw_j"],
                           check["discharge_left_before_j"] - block["battery_discharged_j"])
            assert headroom >= certificate["protected_draw_j"] - 1e-5
        else:
            remaining = len(checks) - index
            assert check["phase"] == "terminal"
            assert count == remaining * (1 + check["changed"])
        probes.append(count)
    assert sum(probes) <= max_probes
    return dict(guard_interventions=int(np.count_nonzero(proposed != executed)),
                guard_extra_block_integrations=sum(probes), guard_max_extra_block_integrations=max(probes))


def evaluated(output, design, cells, policy_name, policy, env, arm, file_prefix, **labels):
    path = output / f"{arm}_{file_prefix}_{cells}.json.gz"
    model, protocol = design["model"], design["protocol"]
    observations = []

    def predict(obs):
        observations.append(obs.tolist())
        return policy(obs)

    started = time.perf_counter()
    lap = rollout(env, predict)
    penalty = protocol["reward"]["terminal_shortfall_s_per_mps"]
    lap["reward_sum"] = TerminalReward(env, penalty).reward(lap["reward_sum"])
    row = {key: value for key, value in lap.items() if key != "trace"}
    row.update(audit_replay(lap, model, model, SimpleNamespace(**model["vehicle"])), arm=arm, policy=policy_name,
               cells=cells, file=path.as_posix(), replay_seconds=time.perf_counter() - started,
               wheel_assist_j=sum(block["electrical_work_j"] for block in lap["trace"]), **labels)
    gzsave(path, dict(lap, pre_action_observations=observations))
    read_and_check(row, model, protocol, design["boundaries_m"][str(cells)])
    if arm.endswith("_guarded"):
        max_probes = design["experiment"]["preflight"]["max_lookahead_transitions_per_complete_lap"]
        row.update(guard_counts(lap, design["certificates"][str(cells)], max_probes))
        if not row["feasible"]:
            raise ValueError(f"Constrained replay missed the finish: {path}")
    return row


def preflight(output, design):
    started = time.perf_counter()
    p, config = design["protocol"], design["experiment"]["preflight"]
    training, *evaluation = grids(p)
    assert (training, *evaluation) == tuple(config["grid_cells_per_block"])
    controls = tuple("planner" if name == "selected" else name for name in config["controls"])
    design["certificates"] = {}
    rows = []
    for cells in (training, *evaluation):
        design["certificates"][str(cells)] = prepare_constraint(design["model"], cells)
        env = environment(design, cells, True)
        assert env.observation_space.shape == (p["observations"],) and env.blocks == p["action_blocks"]
        assert env.action_space.shape == (1,) and env.action_space.low.item() == 0 and env.action_space.high.item() == 1
        np.testing.assert_allclose(env.grid.distance_m[::cells], design["boundaries_m"][str(cells)], rtol=0, atol=1e-7)
        for name in (*controls, *(f"random_{s}" for s in config["random_action_seeds"])):
            if name.startswith("random_"):
                actions = np.random.default_rng(int(name.split("_")[-1])).random(env.blocks)
                policy = lambda obs: actions[env.index]
            elif name == "planner":
                policy = lambda obs: design["selected_actions"][env.index]
            else:
                policy = baseline_policy(name, env)
            row = evaluated(output, design, cells, name, policy, env, "baseline_guarded", name,
                            method=None, width=None, seed=None)
            if name in ("zero", "full"):
                assert row["guard_interventions"] > 0
            rows.append(row)
        print(f"Preflight {cells}: all guarded rollouts feasible", flush=True)
    elapsed = time.perf_counter() - started
    save(output / "preflight.json", dict(passed=True, rows=rows, wall_seconds=elapsed, completed_at=utc_now()))
    return [row for row in rows if row["cells"] in evaluation and row["policy"] in ("spread", "planner")]


def verify_predictions(agent, rows):
    for row in rows:
        lap = read(row["file"])
        for obs, block in zip(lap["pre_action_observations"], lap["trace"], strict=True):
            proposal = block.get("finish_constraint", {}).get("proposed_action", block["action"])
            action, _ = agent.predict(np.asarray(obs, dtype=np.float32), deterministic=True)
            if action.item() != proposal:
                raise ValueError(f"Deterministic reload changed a proposal in {row['file']}")


def train(output, design, method, width, seed):
    p = design["protocol"]
    verify_hashes(design["inputs"] | design["sources"])
    if not read(output / "preflight.json")["passed"]:
        raise ValueError("Missing passing guard preflight")
    started, stamp = time.perf_counter(), utc_now()
    hardware = require_cuda()
    torch.set_num_threads(1)
    torch.cuda.reset_peak_memory_stats()
    training, *evaluation = grids(p)
    guarded = environment(design, training, True)
    env = TerminalReward(guarded, p["reward"]["terminal_shortfall_s_per_mps"])
    kwargs = p[method.lower()]
    critic = p["architectures"][method.lower()]["critic"]
    if method == "PPO":
        network = dict(net_arch=dict(pi=[width, width], vf=critic), activation_fn=torch.nn.Tanh)
    else:
        network = dict(net_arch=dict(pi=[width, width], qf=critic), activation_fn=torch.nn.ReLU,
                       n_critics=p["architectures"]["sac"]["critics"])
    algorithm = ALGORITHMS[method]
    agent = algorithm("MlpPolicy", env, policy_kwargs=network, device=hardware["device"], seed=seed, verbose=0, **kwargs)
    shapes = shape_checks(agent, method, width)
    initial = {key: value.detach().clone() for key, value in agent.policy.state_dict().items()}
    tick = time.perf_counter()
    agent.learn(total_timesteps=p["steps_per_seed"])
    torch.cuda.synchronize()
    training_seconds = time.perf_counter() - tick
    if method == "PPO":
        updates = p["steps_per_seed"] // kwargs["n_steps"] * kwargs["n_epochs"]
        minibatches = updates * kwargs["n_steps"] // kwargs["batch_size"]
        prefixes = ("action_net", "value_net")
    else:
        updates = (p["steps_per_seed"] - kwargs["learning_starts"]) // kwargs["train_freq"]
        minibatches = updates
        prefixes = ("actor.mu", "critic.qf0", "critic.qf1")
    stats = guarded.constraint_stats
    max_probes = design["experiment"]["preflight"]["max_lookahead_transitions_per_complete_lap"]
    assert stats["episodes"] == p["steps_per_seed"] // p["action_blocks"]
    assert stats["lookahead_transitions"] <= (stats["episodes"] + 1) * max_probes
    assert stats["max_abs_finish_error_mps"] < design["experiment"]["terminal_tolerance_mps"]
    if agent.num_timesteps != p["steps_per_seed"] or stats["agent_steps"] != agent.num_timesteps or agent._n_updates != updates:
        raise ValueError("Unexpected environment interactions or optimizer schedule")
    cuda = cuda_evidence(agent, method)
    changed = [key for key, value in agent.policy.state_dict().items() if not torch.equal(initial[key], value)]
    if not all(any(key.startswith(start) for key in changed) for start in prefixes):
        raise ValueError("Training failed to change all required networks")
    file_prefix = prefix(method, width, seed)
    checkpoint = output / f"{file_prefix}.zip"
    agent.save(checkpoint)
    restored = algorithm.load(checkpoint, device=agent.device)
    for key, value in agent.policy.state_dict().items():
        if not torch.equal(value, restored.policy.state_dict()[key]):
            raise ValueError(f"Checkpoint tensor changed: {checkpoint}, {key}")

    policy_name = f"{method} {width} seed {seed}"
    old_rows = [row for row in design["legacy_rows"] if row["policy"] == policy_name]
    if len(old_rows) != len(evaluation) or len({row["checkpoint"] for row in old_rows}) != 1:
        raise ValueError(f"Missing signed penalty-only rows for {policy_name}")
    old_checkpoint = old_rows[0]["checkpoint"]
    old_agent = algorithm.load(old_checkpoint, device=agent.device)
    verify_predictions(old_agent, old_rows)
    rows = list(old_rows)
    for cells in evaluation:
        for arm, policy_agent, checkpoint_path in (("penalty_guarded", old_agent, old_checkpoint),
                                                    ("constrained_raw", agent, checkpoint.as_posix()),
                                                    ("constrained_guarded", agent, checkpoint.as_posix())):
            raw = environment(design, cells, arm.endswith("_guarded"))
            rows.append(evaluated(output, design, cells, policy_name,
                                  lambda obs: policy_agent.predict(obs, deterministic=True)[0], raw,
                                  arm, file_prefix, method=method, width=width, seed=seed, checkpoint=checkpoint_path))
    verify_predictions(restored, [row for row in rows if row["arm"].startswith("constrained_")])
    verify_predictions(old_agent, [row for row in rows if row["arm"] == "penalty_guarded"])
    replay_buffer_host_bytes = 0
    if method == "SAC":
        replay_buffer_host_bytes = sum(getattr(agent.replay_buffer, name).nbytes for name in
                                       ("observations", "next_observations", "actions", "rewards", "dones", "timeouts"))
    save(output / f"{file_prefix}.json", dict(
        policy=policy_name, method=method, width=width, seed=seed, checkpoint=checkpoint.as_posix(),
        checkpoint_sha256=sha(checkpoint), checkpoint_reload_exact=True, penalty_checkpoint_reload_exact=True,
        rows=rows, hardware=hardware, architecture=shapes, cuda=cuda, changes=changed,
        actual_steps=stats["agent_steps"], update_count=updates, minibatches=minibatches, training_seconds=training_seconds,
        guard_interventions=stats["interventions"], guard_extra_block_integrations=stats["lookahead_transitions"],
        max_abs_training_finish_error_mps=stats["max_abs_finish_error_mps"],
        completed_training_laps=stats["episodes"], started_at=stamp, completed_at=utc_now(),
        wall_seconds=time.perf_counter() - started, peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        peak_reserved_bytes=torch.cuda.max_memory_reserved(), replay_buffer_host_bytes=replay_buffer_host_bytes))
    print(f"{policy_name}: {training_seconds:.2f}s training, {stats['episodes']} feasible training laps", flush=True)


def numerical(rows, protocol):
    _, primary, refined = grids(protocol)
    limits = protocol["refinement"]
    indexed = {(row["arm"], row["policy"], row["cells"]): row for row in rows}
    individuals, comparisons = [], []
    by_policy = {}
    for arm, name in dict.fromkeys((row["arm"], row["policy"]) for row in rows):
        a, b = (indexed[arm, name, cells] for cells in (primary, refined))
        changes = dict(relative_lap_change=abs(a["duration_s"] - b["duration_s"]) / b["duration_s"],
                       terminal_energy_change_j=abs(a["final_energy_j"] - b["final_energy_j"]),
                       recovered_change_j=abs(a["recovered_j"] - b["recovered_j"]))
        passed = a["feasible"] and b["feasible"] and all(value <= limits[key] for key, value in changes.items())
        by_policy[arm, name] = passed
        individuals.append(dict(arm=arm, policy=name, **changes, both_feasible=a["feasible"] and b["feasible"],
                                passes_refinement=passed))
    for arm, name in by_policy:
        if arm not in ARMS:
            continue
        peers = [("baseline_guarded", baseline) for baseline in ("spread", "planner")]
        if arm == "constrained_guarded":
            peers.append(("penalty_guarded", name))
        for other_arm, other_name in peers:
            savings = {}
            for cells in (primary, refined):
                a, b = indexed[arm, name, cells], indexed[other_arm, other_name, cells]
                savings[str(cells)] = b["duration_s"] - a["duration_s"] if a["feasible"] and b["feasible"] else None
            available = all(value is not None for value in savings.values())
            change = abs(savings[str(primary)] - savings[str(refined)]) if available else None
            passed = (available and change <= limits["paired_gap_change_s"] and by_policy[arm, name]
                      and by_policy[other_arm, other_name])
            comparisons.append(dict(arm=arm, policy=name, other_arm=other_arm, other_policy=other_name,
                                    time_savings_s=savings, gap_change_s=change, grid_pass=passed))
    return individuals, comparisons


def verify(output):
    manifest, design, preflight_record, metrics = (read(output / f"{name}.json") for name in
                                                  ("manifest", "contract", "preflight", "metrics"))
    verify_hashes(manifest["inputs"] | manifest["sources"] | manifest["outputs"])
    p = design["protocol"]
    _, *evaluation = grids(p)
    rows = metrics["rows"]
    expected_runs = {(method, width, seed) for method in ALGORITHMS for width in p["widths"] for seed in p["seeds"]}
    expected_rows = {(arm, method, width, seed, cells)
                     for arm in ARMS for method, width, seed in expected_runs for cells in evaluation}
    ablation_rows = [row for row in rows if row["arm"] in ARMS]
    assert len(ablation_rows) == len(expected_rows)
    assert {(r["arm"], r["method"], r["width"], r["seed"], r["cells"]) for r in ablation_rows} == expected_rows
    assert len(rows) == len(expected_rows) + 8
    assert len(metrics["checkpoints"]) == len(expected_runs)
    assert {(r["method"], r["width"], r["seed"]) for r in metrics["checkpoints"]} == expected_runs
    assert preflight_record["passed"]
    assert all(c["checkpoint_reload_exact"] and c["penalty_checkpoint_reload_exact"]
               and c["actual_steps"] == p["steps_per_seed"] and c["completed_training_laps"] == p["steps_per_seed"] // p["action_blocks"]
               for c in metrics["checkpoints"])
    assert metrics["total_interactions"] == len(expected_runs) * p["steps_per_seed"]
    for row in {r["file"]: r for r in [*preflight_record["rows"], *rows]}.values():
        read_and_check(row, design["model"], p, design["boundaries_m"][str(row["cells"])])
        if row["arm"].endswith("_guarded"):
            assert row["feasible"]
            max_probes = design["experiment"]["preflight"]["max_lookahead_transitions_per_complete_lap"]
            counts = guard_counts(read(row["file"]), design["certificates"][str(row["cells"])], max_probes)
            assert all(row[key] == value for key, value in counts.items())
    assert numerical(rows, p) == (metrics["individual_grid_checks"], metrics["comparisons"])
    print(f"Verified {len(ablation_rows)} factorial rows, {len(expected_runs)} trained checkpoints, and all manifest hashes.",
          flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--worker", nargs=3, metavar=("ALGORITHM", "WIDTH", "SEED"))
    args = parser.parse_args()
    output = args.output
    if args.verify:
        verify(output)
        return
    if args.worker:
        method, width, seed = args.worker
        train(output, read(output / "contract.json"), method, int(width), int(seed))
        return
    started, stamp = time.perf_counter(), utc_now()
    design = frozen_design()
    protocol = design["protocol"]
    runtime = dict(hardware=require_cuda(), sb3=sb3_version, numpy=np.__version__, gymnasium=gym.__version__,
                   python=sys.version, driver=subprocess.check_output(
                       ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"], text=True).strip())
    output.mkdir(parents=True, exist_ok=False)
    rows = preflight(output, design)
    rows.extend(row for row in design["legacy_rows"] if row["arm"] == "baseline_raw")
    save(output / "contract.json", dict(design, runtime=runtime, started_at=stamp, protocol_frozen_at=utc_now()))
    checkpoints, phases = [], []

    def run_worker(job):
        method, width, seed = job
        subprocess.run([sys.executable, __file__, "--output", str(output), "--worker", method, str(width), str(seed)],
                       check=True, env=dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                                            OPENBLAS_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1"))
        return read(output / f"{prefix(*job)}.json")

    for width in protocol["widths"]:
        tick, phase_start = time.perf_counter(), utc_now()
        jobs = [(method, width, seed) for method in ALGORITHMS for seed in protocol["seeds"]]
        workers = min(protocol["parallel_workers"], len(jobs))
        print(f"Starting width {width}: {len(jobs)} CUDA runs, {workers} concurrent", flush=True)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            completed = list(pool.map(run_worker, jobs))
        phases.append(dict(width=width, workers=workers, wall_seconds=time.perf_counter() - tick,
                           started_at=phase_start, completed_at=utc_now()))
        for record in completed:
            rows.extend(record.pop("rows"))
            checkpoints.append(record)
        save(output / "progress.json", dict(phases=phases, completed_policies=len(checkpoints)))
    individual, comparisons = numerical(rows, protocol)
    save(output / "metrics.json", dict(training_performed=True, checkpoints=checkpoints, rows=rows,
                                       individual_grid_checks=individual, comparisons=comparisons, phases=phases,
                                       calibration_heldout_checks_passed=design["calibration_heldout_checks_passed"],
                                       total_interactions=sum(c["actual_steps"] for c in checkpoints),
                                       total_training_worker_seconds=sum(c["training_seconds"] for c in checkpoints),
                                       wall_seconds=time.perf_counter() - started, completed_at=utc_now()))
    verify_hashes(design["inputs"] | design["sources"])
    save(output / "manifest.json", dict(inputs=design["inputs"], sources=design["sources"],
                                        outputs={f.as_posix(): sha(f) for f in sorted(output.iterdir()) if f.is_file()}))
    verify(output)


if __name__ == "__main__":
    main()
