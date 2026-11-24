"""Train PPO and SAC directly on the frozen regenerative Bahrain model."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

import gymnasium as gym
import numpy as np
from stable_baselines3 import PPO, SAC, __version__ as sb3_version
import torch

from bahrain_pace_model import build_env, geometry, registered_curve
from benchmark_circuit_control import gzsave, save, sha, sources
from evaluate_bahrain_learned_transfer import OBSERVATIONS, bind, from_manifest, read_and_check
from f1energy.circuit_control import baseline_policy, rollout
from f1energy.training_device import require_cuda, verify_cuda_training
from validate_regeneration import audit_replay
from verify_bahrain_deployment import read


PROTOCOL = Path("configs/bahrain_algorithm_width.json")
OUTPUT = Path("results/bahrain-algorithm-width-001")
ALGORITHMS = {"PPO": PPO, "SAC": SAC}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def frozen_inputs(protocol):
    inputs = {PROTOCOL.as_posix(): sha(PROTOCOL)}
    code = {Path(path).as_posix(): digest for path, digest in sources().items()}
    for path in (Path(__file__), Path("src/f1energy/training_device.py"),
                 *(Path("scripts", name) for name in (
                     "bahrain_pace_model.py", "benchmark_circuit_control.py",
                     "evaluate_bahrain_learned_transfer.py", "train_regeneration_imitation.py",
                     "validate_regeneration.py", "verify_bahrain_deployment.py"))):
        path = path.resolve().relative_to(Path.cwd()).as_posix()
        code[path] = sha(path)
    parents = {}
    for name, evidence in protocol["parents"].items():
        path = Path(evidence["path"])
        bind(path, evidence["sha256"], inputs)
        parents[name] = path.parent, read(path)
    root, deployment = parents["bahrain_deployment"]
    calibration, manifest = parents["bahrain_calibration"]
    for path, digest in deployment["sources"].items():
        if Path(path).as_posix() in code:
            bind(path, digest, code)
    model_path = from_manifest(protocol["model"], deployment, "inputs", inputs)
    model = read(from_manifest(model_path, manifest, "outputs", inputs))
    from_manifest(model["geometry"], deployment, "inputs", inputs)
    bind(model["geometry"], model["geometry_sha256"], inputs)
    condition = protocol["scenario"]
    parent_contract = read(from_manifest(root / "contract.json", deployment, "outputs", inputs))
    if model != parent_contract["models"][condition] or protocol["refinement"] != parent_contract["protocol"]["refinement"]:
        raise ValueError("Central model or refinement criteria differ from the frozen parent")
    metrics = read(from_manifest(root / "metrics.json", deployment, "outputs", inputs))
    calibration_metrics = read(from_manifest(calibration / "metrics.json", manifest, "outputs", inputs))
    search = read(from_manifest(root / condition / "search.json", deployment, "outputs", inputs))
    return dict(protocol=protocol, model=model, observations=OBSERVATIONS, inputs=inputs, sources=code,
                selected_actions=search["actions"],
                approximate_corner_stations_m=metrics["approximate_corner_stations_m"],
                calibration_heldout_checks_passed=calibration_metrics["all_heldout_checks_passed"])


def replay(path, env, policy, design, cells, name, **labels):
    observations = []

    def predict(obs):
        observations.append(obs.tolist())
        return policy(obs)

    tick = time.perf_counter()
    lap = rollout(env.unwrapped, predict)
    if isinstance(env, TerminalReward):
        lap['reward_sum'] = env.reward(lap['reward_sum'])
    row = {key: value for key, value in lap.items() if key != "trace"}
    row.update(audit_replay(lap, design["model"], design["model"], SimpleNamespace(**design["model"]["vehicle"])),
               policy=name, cells=cells, file=path.as_posix(), replay_seconds=time.perf_counter() - tick,
               wheel_assist_j=sum(block["electrical_work_j"] for block in lap["trace"]), **labels)
    gzsave(path, dict(lap, pre_action_observations=observations))
    read_and_check(row, design["model"], design["protocol"], design["boundaries_m"][str(cells)])
    return row


def preflight(output, design):
    p, model = design["protocol"], design["model"]
    train, fine, refined = (p[f"{grid}_cells_per_block"] for grid in ("training", "primary", "refined"))
    rows, block_times = {}, {}
    envs = {cells: build_env(model, cells) for cells in (train, fine, refined)}
    design["boundaries_m"] = {str(cells): e.grid.distance_m[::cells].tolist() for cells, e in envs.items()}
    for cells, env in envs.items():
        if (env.observation_space.shape != (p["observations"],) or env.blocks != p["action_blocks"]
                or env.action_space.shape != (1,) or env.action_space.low.item() != 0
                or env.action_space.high.item() != 1):
            raise ValueError("Environment interface differs from the declared design")
        np.testing.assert_allclose(design["boundaries_m"][str(cells)], design["boundaries_m"][str(train)],
                                   rtol=0, atol=1e-7)
        for name in p["preflight"]["policies"] if cells != refined else p["baselines"]:
            policy = (lambda obs: design["selected_actions"][env.index]) if name == "selected" else baseline_policy(name, env)
            rows[name, cells] = replay(output / f"{name}_{cells}.json.gz", env, policy, design, cells, name)
        block_times[str(cells)] = [b["duration_s"] for b in read(rows["spread", cells]["file"])["trace"]]
    limits = p["preflight"]
    checks = {}
    for name in limits["policies"]:
        a, b = rows[name, train], rows[name, fine]
        changes = dict(relative_time_change=abs(a["duration_s"] - b["duration_s"]) / b["duration_s"],
                       wheel_assist_change_j=abs(a["wheel_assist_j"] - b["wheel_assist_j"]),
                       terminal_energy_change_j=abs(a["final_energy_j"] - b["final_energy_j"]),
                       recovery_change_j=abs(a["recovered_j"] - b["recovered_j"]),
                       finish_error_change_mps=abs(a["terminal_speed_error_mps"] - b["terminal_speed_error_mps"]))
        checks[name] = dict(changes, consistent_feasibility=a["feasible"] == b["feasible"],
                            passed=(a["feasible"] == b["feasible"]
                                    and all(value <= limits[f"max_{key}"] for key, value in changes.items())))
    gap = abs((rows["spread", train]["duration_s"] - rows["selected", train]["duration_s"])
              - (rows["spread", fine]["duration_s"] - rows["selected", fine]["duration_s"]))
    baselines = [r for (name, _), r in rows.items() if name in p["baselines"]]
    passed = (all(r["feasible"] for r in baselines) and all(c["passed"] for c in checks.values())
              and gap <= limits["max_selected_spread_gap_change_s"])
    save(output / "preflight.json", dict(rows=list(rows.values()), checks=checks, passed=passed,
                                         selected_spread_gap_change_s=gap, completed_at=utc_now()))
    if not passed:
        raise ValueError(f"Training-grid preflight failed: {output / 'preflight.json'}")
    design["reference_block_times_s"] = block_times
    return [r for r in baselines if r["cells"] != train]


class TerminalReward(gym.RewardWrapper):
    def __init__(self, env, seconds_per_mps):
        super().__init__(env)
        self.seconds_per_mps = seconds_per_mps

    def reward(self, reward):
        if self.env.index == self.env.blocks:
            return reward - self.seconds_per_mps * max(0., self.env.initial_speed - self.env.state.speed_m_per_s)
        return reward


def environment(design, cells):
    env = build_env(design["model"], cells)
    env.reference_times = np.array(design["reference_block_times_s"][str(cells)])
    return TerminalReward(env, design["protocol"]["reward"]["terminal_shortfall_s_per_mps"])


def numerical(rows, protocol):
    fine, refined = (protocol[f"{g}_cells_per_block"] for g in ("primary", "refined"))
    limits = protocol["refinement"]
    individual, comparisons = {}, []
    grouped = {(r["policy"], r["cells"]): r for r in rows}
    names = list(dict.fromkeys(name for name, _ in grouped))
    for name in names:
        a, b = grouped[name, fine], grouped[name, refined]
        changes = dict(relative_lap_change=abs(a["duration_s"] - b["duration_s"]) / b["duration_s"],
                       terminal_energy_change_j=abs(a["final_energy_j"] - b["final_energy_j"]),
                       recovered_change_j=abs(a["recovered_j"] - b["recovered_j"]))
        both = a["feasible"] and b["feasible"]
        passes = all(value <= limits[key] for key, value in changes.items())
        individual[name] = dict(changes, both_feasible=both, passes_limits=passes, passes_refinement=both and passes)
    pairs = [("selected", "spread")]
    for name in names:
        if name not in protocol["baselines"]:
            pairs.extend((name, baseline) for baseline in protocol["baselines"])
    for seed in protocol["seeds"]:
        pairs.extend((f"PPO {width} seed {seed}", f"SAC {width} seed {seed}") for width in protocol["widths"])
        pairs.extend((f"{method} 256 seed {seed}", f"{method} 64 seed {seed}") for method in ALGORITHMS)
    for first, second in pairs:
        gaps = {}
        for cells in (fine, refined):
            a, b = grouped[first, cells], grouped[second, cells]
            gaps[str(cells)] = b["duration_s"] - a["duration_s"] if a["feasible"] and b["feasible"] else None
        available = all(value is not None for value in gaps.values())
        change = abs(gaps[str(fine)] - gaps[str(refined)]) if available else None
        passed = (available and change <= limits["paired_gap_change_s"]
                  and all(individual[name]["passes_refinement"] for name in (first, second)))
        comparisons.append(dict(first=first, second=second, time_savings_s=gaps, gap_change_s=change, grid_pass=passed,
                                resolved_direction=bool(passed and gaps[str(fine)] * gaps[str(refined)] > 0)))
    return individual, comparisons


def shape_checks(agent, method, width):
    p = agent.policy
    if method == "PPO":
        actor = [*p.mlp_extractor.policy_net, p.action_net]
        critics = [[*p.mlp_extractor.value_net, p.value_net]]
        actor_dimensions, critic_dimensions = [8, width, width, 1], [8, 32, 32, 1]
    else:
        actor = [*p.actor.latent_pi, p.actor.mu]
        critics = [*p.critic.q_networks, *p.critic_target.q_networks]
        actor_dimensions, critic_dimensions = [8, width, width, 1], [9, 64, 64, 1]
        if tuple(p.actor.log_std.weight.shape) != (1, width) or len(critics) != 4:
            raise ValueError("Unexpected SAC action log-std or number of Q networks")
    for layers, dims in [(actor, actor_dimensions), *((c, critic_dimensions) for c in critics)]:
        actual = [(m.in_features, m.out_features) for m in layers if isinstance(m, torch.nn.Linear)]
        if actual != list(zip(dims, dims[1:])):
            raise ValueError(f"Unexpected {method} network shapes: {actual}")
    parameters = sum(value.numel() for value in p.parameters())
    return dict(actor_dimensions=actor_dimensions, critic_dimensions=critic_dimensions,
                critic_networks_in_checkpoint=len(critics), policy_parameter_count=parameters,
                shapes={key: list(value.shape) for key, value in p.state_dict().items()})


def cuda_evidence(agent, method):
    if method == "PPO":
        verified = verify_cuda_training(agent)
    else:
        # The shared CUDA audit also works with the separate SAC actor and Q optimizers.
        verified = {"actor": verify_cuda_training(SimpleNamespace(policy=agent.actor)),
                    "critics": verify_cuda_training(SimpleNamespace(policy=agent.critic))}
        for i, q in enumerate(agent.critic.q_networks, start=1):
            probe = SimpleNamespace(parameters=q.parameters, optimizer=agent.critic.optimizer)
            verified[f"critic_{i}"] = verify_cuda_training(SimpleNamespace(policy=probe))
        temperature = SimpleNamespace(parameters=lambda: [agent.log_ent_coef], optimizer=agent.ent_coef_optimizer)
        verified["entropy_temperature"] = verify_cuda_training(SimpleNamespace(policy=temperature))
        target = list(agent.critic_target.parameters())
        if not target or any(p.device.type != "cuda" or not torch.isfinite(p).all() for p in target):
            raise RuntimeError("Invalid SAC target critics")
        verified["target_critic_parameter_tensors"] = len(target)
        verified["target_critic_device"] = str(target[0].device)
    return verified


def exact_policy(agent, method, checkpoint, rows):
    restored = ALGORITHMS[method].load(checkpoint, device=agent.device)
    for key, value in agent.policy.state_dict().items():
        if not torch.equal(value, restored.policy.state_dict()[key]):
            raise ValueError(f"Policy checkpoint tensor mismatch: {checkpoint}, {key}")
    for row in rows:
        lap = read(row["file"])
        for obs, block in zip(lap["pre_action_observations"], lap["trace"], strict=True):
            action, _ = restored.predict(np.asarray(obs, dtype=np.float32), deterministic=True)
            if action.item() != block["action"]:
                raise ValueError(f"Deterministic reload changed an action: {checkpoint}")
    return True


def train(output, design, method, width, seed):
    p = design["protocol"]
    verify_hashes(design["inputs"] | design["sources"])
    if not read(output / "preflight.json")["passed"]:
        raise ValueError("Missing passing preflight")
    started, stamp = time.perf_counter(), utc_now()
    hardware = require_cuda()
    torch.set_num_threads(1)
    torch.cuda.reset_peak_memory_stats()
    env = environment(design, p["training_cells_per_block"])
    kwargs = p[method.lower()]
    critic = p["architectures"][method.lower()]["critic"]
    if method == "PPO":
        network = dict(net_arch=dict(pi=[width, width], vf=critic), activation_fn=torch.nn.Tanh)
    else:
        network = dict(net_arch=dict(pi=[width, width], qf=critic), activation_fn=torch.nn.ReLU,
                       n_critics=p["architectures"]["sac"]["critics"])
    agent = ALGORITHMS[method]("MlpPolicy", env, policy_kwargs=network, device=hardware["device"],
                               seed=seed, verbose=0, **kwargs)
    shapes = shape_checks(agent, method, width)
    initial = {key: value.detach().clone() for key, value in agent.policy.state_dict().items()}
    tick = time.perf_counter()
    agent.learn(total_timesteps=p["steps_per_seed"])
    torch.cuda.synchronize()
    training_seconds = time.perf_counter() - tick
    update_count = agent._n_updates
    if method == "PPO":
        updates = p["steps_per_seed"] // kwargs["n_steps"] * kwargs["n_epochs"]
        minibatches = update_count * kwargs["n_steps"] // kwargs["batch_size"]
    else:
        updates = (p["steps_per_seed"] - kwargs["learning_starts"]) // kwargs["train_freq"]
        minibatches = update_count
    if agent.num_timesteps != p["steps_per_seed"] or update_count != updates:
        raise ValueError("Unexpected environment interactions or optimizer schedule")
    cuda = cuda_evidence(agent, method)
    changed = [key for key, value in agent.policy.state_dict().items() if not torch.equal(initial[key], value)]
    prefixes = ("action_net", "value_net") if method == "PPO" else ("actor.mu", "critic.qf0", "critic.qf1")
    if not all(any(key.startswith(prefix) for key in changed) for prefix in prefixes):
        raise ValueError("Training failed to change all required networks")
    file_prefix = f"{method.lower()}_{width}_seed{seed}"
    checkpoint = output / f"{file_prefix}.zip"
    agent.save(checkpoint)

    def predict(obs):
        return agent.predict(obs, deterministic=True)[0]

    name = f"{method} {width} seed {seed}"
    rows = []
    for grid in ("primary", "refined"):
        cells = p[f"{grid}_cells_per_block"]
        rows.append(replay(output / f"{file_prefix}_{cells}.json.gz", environment(design, cells), predict,
                           design, cells, name, method=method, width=width, seed=seed, checkpoint=checkpoint.as_posix()))
    exact = exact_policy(agent, method, checkpoint, rows)
    cache = dict(registered_curve=registered_curve.cache_info()._asdict(), geometry=geometry.cache_info()._asdict())
    save(output / f"{file_prefix}.json", dict(
        policy=name, method=method, width=width, seed=seed, checkpoint=checkpoint.as_posix(),
        checkpoint_sha256=sha(checkpoint), checkpoint_reload_exact=exact, rows=rows, cuda=cuda, hardware=hardware,
        actual_steps=agent.num_timesteps, update_count=update_count, minibatches=minibatches,
        training_seconds=training_seconds, wall_seconds=time.perf_counter() - started, started_at=stamp,
        completed_at=utc_now(), peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        peak_reserved_bytes=torch.cuda.max_memory_reserved(), changes=changed, architecture=shapes, geometry_cache=cache,
        replay_buffer_host_bytes=(sum(getattr(agent.replay_buffer, v).nbytes for v in
                                     ("observations", "next_observations", "actions", "rewards", "dones", "timeouts"))
                                  if method == "SAC" else 0)))
    print(f"{name}: {training_seconds:.2f}s training, " + ", ".join(
        f'{r["cells"]} cells {"feasible" if r["feasible"] else "FAILED"} ({r["terminal_speed_error_mps"]:+.6f} m/s)'
        for r in rows), flush=True)


def verify_hashes(entries):
    for path, digest in entries.items():
        if sha(path) != digest:
            raise ValueError(f"Hash mismatch: {path}")


def verify(output):
    manifest, design, metrics = (read(output / f"{name}.json") for name in ("manifest", "contract", "metrics"))
    verify_hashes(manifest["inputs"] | manifest["sources"] | manifest["outputs"])
    protocol = design["protocol"]
    rows = metrics["rows"]
    expected_runs = len(protocol["seeds"]) * len(protocol["widths"]) * len(ALGORITHMS)
    assert len(metrics["checkpoints"]) == expected_runs
    assert len(rows) == len({(r["policy"], r["cells"]) for r in rows}) == (expected_runs + 2) * 2
    for row in rows:
        read_and_check(row, design["model"], protocol, design["boundaries_m"][str(row["cells"])])
    assert all(r["checkpoint_reload_exact"] and r["actual_steps"] == protocol["steps_per_seed"]
               for r in metrics["checkpoints"])
    assert metrics["individual_grid_checks"], metrics["comparisons"]
    assert numerical(rows, protocol) == (metrics["individual_grid_checks"], metrics["comparisons"])
    print(f"Verified {sum(len(v) for v in manifest.values())} hashes, {expected_runs} reload records, "
          f"and {len(rows)} independent physical replay audits.", flush=True)


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
    protocol = read(PROTOCOL)
    design = frozen_inputs(protocol)
    runtime = dict(hardware=require_cuda(), sb3=sb3_version, numpy=np.__version__, gymnasium=gym.__version__,
                   python=sys.version, driver=subprocess.check_output(
                       ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"], text=True).strip())
    output.mkdir(parents=True, exist_ok=False)
    rows = preflight(output, design)
    save(output / "contract.json", dict(design, runtime=runtime, started_at=stamp, protocol_frozen_at=utc_now(),
                                       cache="Provenance is frozen geometry plus phase and grid registered in each worker. "
                                             "Every physics transition is freshly integrated. Each SAC worker has a "
                                             "private host NumPy replay buffer. No cache or policy data crosses workers."))
    checkpoints, phases = [], []

    def run_worker(job):
        method, width, seed = job
        subprocess.run([sys.executable, __file__, "--output", str(output), "--worker", method, str(width), str(seed)],
                       check=True, env=dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                                            OPENBLAS_NUM_THREADS="1"))
        return read(output / f"{method.lower()}_{width}_seed{seed}.json")

    for width in protocol["widths"]:
        tick, phase_start = time.perf_counter(), utc_now()
        jobs = [(method, width, seed) for method in ALGORITHMS for seed in protocol["seeds"]]
        print(f"Starting width {width}: {len(jobs)} CUDA runs", flush=True)
        with ThreadPoolExecutor(max_workers=protocol["parallel_workers"]) as pool:
            completed = list(pool.map(run_worker, jobs))
        phases.append(dict(width=width, workers=len(completed), wall_seconds=time.perf_counter() - tick,
                           started_at=phase_start, completed_at=utc_now()))
        for checkpoint in completed:
            rows.extend(checkpoint.pop("rows"))
            checkpoints.append(checkpoint)
        save(output / "progress.json", dict(phases=phases, completed_policies=len(checkpoints)))
    individual, comparisons = numerical(rows, protocol)
    save(output / "metrics.json", dict(
        training_performed=True, calibration_heldout_checks_passed=design["calibration_heldout_checks_passed"],
        checkpoints=checkpoints, rows=rows, individual_grid_checks=individual, comparisons=comparisons, phases=phases,
        total_interactions=sum(c["actual_steps"] for c in checkpoints),
        total_training_worker_seconds=sum(c["training_seconds"] for c in checkpoints),
        wall_seconds=time.perf_counter() - started, completed_at=utc_now()))
    verify_hashes(design["inputs"] | design["sources"])
    save(output / "manifest.json", dict(inputs=design["inputs"], sources=design["sources"],
                                        outputs={f.as_posix(): sha(f) for f in sorted(output.iterdir()) if f.is_file()}))
    verify(output)


if __name__ == "__main__":
    main()
