"""Replay archived regenerative controllers on the frozen Bahrain qualifying model."""
import argparse
import csv
from pathlib import Path
import time
from types import SimpleNamespace

import numpy as np
import torch
from stable_baselines3 import PPO, __version__ as sb3_version

from bahrain_pace_model import build_env
from benchmark_circuit_control import gzsave, plt, save, sha, sources
from f1energy.circuit_control import rollout
from train_regeneration_imitation import network
from validate_regeneration import audit_replay
from verify_bahrain_deployment import close, read, verify_rollout


PROTOCOL = Path("configs/bahrain_learned_transfer.json")
OUTPUT = Path("results/bahrain-learned-transfer-001")
FIGURES = Path("figures/dissertation/bahrain-learned-transfer-v1")
OBSERVATIONS = (
    "lap progress", "speed / 100", "battery energy above reserve / usable capacity",
    "current cell speed cap / 100", "minimum one-block envelope / 100",
    "minimum two-block envelope / 100", "remaining recovery fraction",
    "remaining battery discharge fraction",
)
GROUPS = ("PPO 32", "PPO 64", "Imitation 32", "Imitation 64")


def bind(path, digest, bindings):
    key = Path(path).as_posix()
    if key not in bindings:
        if sha(path) != digest:
            raise ValueError(f"Hash mismatch: {path}")
        bindings[key] = digest
    elif bindings[key] != digest:
        raise ValueError(f"Conflicting digests for {path}")


def from_manifest(path, manifest, group, bindings):
    expected = {Path(p).as_posix(): h for p, h in manifest[group].items()}
    bind(path, expected[Path(path).as_posix()], bindings)
    return Path(path)


def provenance(protocol, inputs, code):
    parents = {}
    for name, evidence in protocol["parents"].items():
        path = Path(evidence["path"])
        bind(path, evidence["sha256"], inputs)
        parents[name] = path.parent, read(path)
    base, parent = parents["bahrain_deployment"]
    for source in code:
        if Path(source).as_posix() in {Path(p).as_posix() for p in parent["sources"]}:
            from_manifest(source, parent, "sources", code)
    model_path = from_manifest(protocol["model"], parent, "inputs", inputs)
    model = read(from_manifest(model_path, parents["bahrain_calibration"][1], "outputs", inputs))
    calibration = parents["bahrain_calibration"]
    pace = read(from_manifest(calibration[0] / "metrics.json", calibration[1], "outputs", inputs))
    from_manifest(model["geometry"], parent, "inputs", inputs)
    bind(model["geometry"], model["geometry_sha256"], inputs)
    contract = read(from_manifest(base / "contract.json", parent, "outputs", inputs))
    central = protocol["scenario"]
    if model != contract["models"][central] or protocol["refinement"] != contract["protocol"]["refinement"]:
        raise ValueError("Bahrain model or refinement differs from parent deployment")
    deployment = read(from_manifest(base / "metrics.json", parent, "outputs", inputs))
    comparison = deployment["evaluations"][central]
    baselines = {}
    for cells in (protocol["primary_cells_per_block"], protocol["refined_cells_per_block"]):
        for policy in protocol["baselines"]:
            row = comparison["results"][str(cells)][policy]
            path = from_manifest(row["file"], parent, "outputs", inputs)
            baselines[policy, cells] = dict(row, file=path.as_posix(), policy=policy, cells=cells)

    checkpoints = {}
    for width in protocol["widths"]:
        folder, manifest = parents[f"ppo{width}"]
        old = read(from_manifest(folder / "contract.json", manifest, "outputs", inputs))["protocol"]
        baseline, _ = parents["ppo_training_baselines"]
        from_manifest(baseline / "manifest.json", manifest, "inputs", inputs)
        if old["training_seeds"] != protocol["seeds"] or old["steps_per_seed"] != protocol["ppo_final_steps"]:
            raise ValueError(f"PPO endpoint mismatch: {folder}")
        if width == 64:
            bind(parents["ppo32"][0] / "manifest.json", old["width_comparison"]["baseline_manifest_sha256"], inputs)
        for seed in protocol["seeds"]:
            worker = folder / f"seed-{seed}"
            sub = read(from_manifest(worker / "manifest.json", manifest, "outputs", inputs))
            training = read(from_manifest(worker / "contract.json", sub, "outputs", inputs))
            progress = read(from_manifest(worker / "metrics.json", sub, "outputs", inputs))
            if (training["seed"] != seed or training["protocol"] != old or progress["seed"] != seed
                    or progress["actual_steps"] != protocol["ppo_final_steps"] or not progress["checkpoint_reload_exact"]):
                raise ValueError(f"PPO archived endpoint mismatch: {worker}")
            checkpoint = worker / f'checkpoint_{protocol["ppo_final_steps"]}.zip'
            from_manifest(checkpoint, sub, "outputs", inputs)
            checkpoints["PPO", width, seed] = from_manifest(checkpoint, manifest, "outputs", inputs)

    folder, manifest = parents["imitation"]
    old = read(from_manifest(folder / "contract.json", manifest, "outputs", inputs))["protocol"]
    teachers, _ = parents["imitation_teachers"]
    from_manifest(teachers / "manifest.json", manifest, "inputs", inputs)
    bind(teachers / "manifest.json", old["teacher_manifest_sha256"], inputs)
    if (old["epochs"] != protocol["imitation_final_epoch"] or old["seeds"] != protocol["seeds"]
            or old["widths"] != protocol["widths"] or old["action_blocks"] != protocol["action_blocks"]):
        raise ValueError("Imitation archived endpoint mismatch")
    fit = read(from_manifest(folder / "fit_metrics.json", manifest, "outputs", inputs))
    for width in protocol["widths"]:
        for seed in protocol["seeds"]:
            row, = [r for r in fit if (r["width"], r["seed"]) == (width, seed)]
            checkpoint = folder / f"width{width}_seed{seed}.pt"
            if Path(row["checkpoint"]) != checkpoint or not row["fit_prediction_reload_exact"] or not row["cuda"]["passed"]:
                raise ValueError(f"Imitation checkpoint mismatch: {checkpoint}")
            checkpoints["Imitation", width, seed] = from_manifest(checkpoint, manifest, "outputs", inputs)
    return model, pace["all_heldout_checks_passed"], deployment["approximate_corner_stations_m"], baselines, checkpoints


def load_policy(protocol, env, path, method, width, seed):
    device = torch.device(protocol["inference_device"])
    if method == "PPO":
        model = PPO.load(path, device=device)
        shapes = {
            "mlp_extractor.policy_net.0.weight": (width, 8),
            "mlp_extractor.policy_net.2.weight": (width, width),
            "action_net.weight": (1, width),
            "mlp_extractor.value_net.0.weight": (32, 8),
            "mlp_extractor.value_net.2.weight": (32, 32),
            "value_net.weight": (1, 32),
        }
        if (model.num_timesteps != protocol["ppo_final_steps"] or model.seed != seed
                or model.observation_space != env.observation_space or model.action_space != env.action_space
                or not isinstance(model.policy.activation_fn(), torch.nn.Tanh)
                or any(model.policy.state_dict()[name].shape != shape for name, shape in shapes.items())):
            raise ValueError(f"Unexpected PPO checkpoint contract: {path}")
        model.policy.set_training_mode(False)
        return model.policy, lambda obs: model.predict(obs, deterministic=True)[0]

    model = network(width, device)
    model.load_state_dict(torch.load(path, map_location=device, weights_only=True))
    model.eval()
    return model, lambda obs: model(torch.as_tensor(obs, device=device).unsqueeze(0)).clamp(0, 1).item()


def read_and_check(row, model, protocol, boundaries):
    lap = read(row["file"])
    trace = verify_rollout(row, model)
    close(lap["duration_s"], row["duration_s"])
    close(lap["final_energy_j"], trace[-1]["state"]["energy_j"])
    close(lap["terminal_speed_error_mps"], row["terminal_speed_error_mps"])
    for end, block in enumerate(trace):
        state = block["state"]
        close(state["distance_m"], boundaries[end + 1], 1e-7)
        previous_elapsed_s = trace[end - 1]["state"]["elapsed_s"] if end else 0
        close(state["elapsed_s"] - previous_elapsed_s, block["duration_s"])
        efficiency = model["vehicle"]["discharge_efficiency"]
        requested_w = block["action"] * model["vehicle"]["electrical_limit_w"]
        if block["electrical_work_j"] > requested_w * block["duration_s"] + 1e-5:
            raise ValueError(f'Calculated work exceeds request: {row["file"]}')
        close(block["battery_discharged_j"], block["electrical_work_j"] / efficiency, .01)
        close(block["charging_loss_j"], block["regenerative_braking_work_j"] - block["battery_recovered_j"], .01)
    if "checkpoint" in row:
        observations = np.asarray(lap["pre_action_observations"])
        if observations.shape != (protocol["action_blocks"], protocol["observations"]) or not np.isfinite(observations).all():
            raise ValueError(f'Missing observations: {row["file"]}')
        np.testing.assert_allclose(observations[:, 0], np.arange(protocol["action_blocks"]) / protocol["action_blocks"],
                                   rtol=0, atol=3e-8)
        expected_speeds = [model["initial_speed_mps"], *[b["state"]["speed_m_per_s"] for b in trace[:-1]]]
        np.testing.assert_allclose(observations[:, 1], np.asarray(expected_speeds) / 100, rtol=0, atol=3e-8)
    return trace


def numerical(rows, protocol):
    primary = protocol["primary_cells_per_block"]
    refined = protocol["refined_cells_per_block"]
    limits = protocol["refinement"]
    individual = {}
    for name in dict.fromkeys(name for name, _ in rows):
        a, b = rows[name, primary], rows[name, refined]
        changes = dict(
            relative_lap_change=abs(a["duration_s"] - b["duration_s"]) / b["duration_s"],
            terminal_energy_change_j=abs(a["final_energy_j"] - b["final_energy_j"]),
            recovered_change_j=abs(a["recovered_j"] - b["recovered_j"]),
        )
        both = a["feasible"] and b["feasible"]
        individual[name] = dict(**changes, both_feasible=both,
                                passes_limits=all(value <= limits[key] for key, value in changes.items()),
                                passes_refinement=both and all(value <= limits[key] for key, value in changes.items()))
    pairs = [("selected", "spread")]
    for name in individual:
        if name not in protocol["baselines"]:
            pairs.extend((name, baseline) for baseline in protocol["baselines"])
    for seed in protocol["seeds"]:
        pairs.extend((f"{method} 64 seed {seed}", f"{method} 32 seed {seed}") for method in ("PPO", "Imitation"))
        pairs.extend((f"PPO {width} seed {seed}", f"Imitation {width} seed {seed}") for width in protocol["widths"])
    comparisons = []
    for first, second in pairs:
        gaps = {}
        for cells in (primary, refined):
            a, b = rows[first, cells], rows[second, cells]
            gaps[cells] = b["duration_s"] - a["duration_s"] if a["feasible"] and b["feasible"] else None
        available = all(gap is not None for gap in gaps.values())
        change = abs(gaps[primary] - gaps[refined]) if available else None
        grid_pass = (available and change <= limits["paired_gap_change_s"]
                     and all(individual[name]["passes_refinement"] for name in (first, second)))
        comparisons.append(dict(first=first, second=second, time_savings_s=gaps, gap_change_s=change,
                                grid_pass=grid_pass, resolved_direction=bool(grid_pass and gaps[primary] * gaps[refined] > 0)))
    return individual, comparisons


def distance_profiles(model, rows, traces, output):
    profiles = []
    for (policy, cells), trace in traces.items():
        previous_m = cumulative = 0.
        selected = traces["selected", cells]
        selected_cumulative = 0.
        for i, (block, plan) in enumerate(zip(trace, selected, strict=True), start=1):
            distance = block["state"]["distance_m"]
            close(distance, plan["state"]["distance_m"], 1e-7)
            wheel = block["electrical_work_j"] / 1000
            cumulative += wheel
            selected_cumulative += plan["electrical_work_j"] / 1000
            profiles.append(dict(
                policy=policy, cells=cells, feasible=rows[policy, cells]["feasible"], block=i, from_m=previous_m,
                to_m=distance, requested_fraction=block["action"],
                requested_kw=block["action"] * model["vehicle"]["electrical_limit_w"] / 1000,
                mean_wheel_kw=wheel / block["duration_s"], wheel_work_kj=wheel,
                cumulative_wheel_work_kj=cumulative, cumulative_minus_selected_kj=cumulative - selected_cumulative,
                elapsed_s=block["state"]["elapsed_s"], speed_mps=block["state"]["speed_m_per_s"],
                battery_energy_kj=block["state"]["energy_j"] / 1000,
            ))
            previous_m = distance
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=profiles[0].keys())
        writer.writeheader()
        writer.writerows(profiles)
    return profiles


def plot(figure_folder, profiles, rows, primary, refined, corners, comparisons):
    fig, axes = plt.subplots(3, 2, figsize=(10, 9), layout="constrained")
    speeds, gaps = axes[0]
    colors = ("#235c8a", "#19816c", "#94512e", "#794782")
    left_labels = []
    for group_index, (group, color) in enumerate(zip(GROUPS, colors)):
        names = [name for name, cells in rows if cells == primary and name.startswith(group + " ")]
        for pos, name in enumerate(names):
            y = group_index * 3 + pos
            left_labels.append(f"{group} · s{pos}")
            for cells, marker, offset in ((primary, "o", -.13), (refined, "D", .13)):
                row = rows[name, cells]
                speeds.plot(row["terminal_speed_error_mps"], y + offset, marker=marker,
                            color=color, ms=5, mfc=color if row["feasible"] else "white", mew=1.2)
                gap, = [p["time_savings_s"][cells] for p in comparisons
                        if p["first"] == name and p["second"] == "selected"]
                if gap is not None:
                    gaps.plot(gap, y + offset, marker=marker, color=color, ms=5)
            if not any(rows[name, cells]["feasible"] for cells in (primary, refined)):
                gaps.text(.96, y, "Finish missed", transform=gaps.get_yaxis_transform(), ha="right", va="center",
                          fontsize=8, color="#555555")
    for axis in (speeds, gaps):
        axis.axvline(0, lw=.8, color="#555555")
        axis.set_yticks(range(len(left_labels)), left_labels if axis is speeds else [])
        axis.set_ylim(len(left_labels) - .45, -.55)
        axis.grid(axis="y", alpha=.17)
    speeds.set(xlabel="Finish speed minus target (m/s)", title="Finish constraint by archived seed")
    gaps.set(xlabel="Time saved versus selected schedule (s)", title="Feasible time comparisons")
    speeds.plot([], [], "o", color="#555555", label=f"{primary} cells per span", ms=5)
    speeds.plot([], [], "D", color="#555555", label=f"{refined} cells per span", ms=5)
    speeds.legend(loc="upper left", bbox_to_anchor=(0, -.25), ncols=2, frameon=False, fontsize=8)

    for axis, group, color in zip(axes[1:].flat, GROUPS, colors):
        axis.axhline(0, lw=.9, color="#222222", label="Selected schedule")
        for index, style in enumerate(("-", "--", ":")):
            name = f"{group} seed {index}"
            profile = [p for p in profiles if p["policy"] == name and p["cells"] == primary]
            axis.plot([0., *[p["to_m"] / 1000 for p in profile]],
                      [0., *[p["cumulative_minus_selected_kj"] for p in profile]],
                      ls=style, lw=1.8, color=color, label=f"Seed {index}")
        spread = [p for p in profiles if p["policy"] == "spread" and p["cells"] == primary]
        axis.plot([0., *[p["to_m"] / 1000 for p in spread]],
                  [0., *[p["cumulative_minus_selected_kj"] for p in spread]],
                  lw=1, color="#858585", ls="-.", label="Adaptive spread")
        for turn in ("1", "8", "10", "14"):
            km = corners[turn] / 1000
            axis.axvline(km, color="#c6c6c6", lw=.7, zorder=-1)
            axis.text(km, .98, f"T{turn}", transform=axis.get_xaxis_transform(), color="#666", fontsize=7,
                      ha="center", va="top")
        axis.set_title(group, loc="left", fontsize=10, fontweight="semibold")
        axis.grid(axis="y", alpha=.18)
        axis.margins(y=.18)
    lower = list(axes[1:].flat)
    low = min(ax.get_ylim()[0] for ax in lower)
    high = max(ax.get_ylim()[1] for ax in lower)
    for ax in lower:
        ax.set_ylim(low, high)
    for ax in axes[1:, 0]:
        ax.set_ylabel("Extra wheel work versus\nselected schedule (kJ)")
    for ax in axes[-1]:
        ax.set_xlabel("Distance from timing line (km)")
    lower[-1].legend(loc="upper center", bbox_to_anchor=(.5, -.22), ncols=3, frameon=False, fontsize=8)
    fig.suptitle("Archived controllers on the calibrated Bahrain model", fontsize=14, fontweight="semibold")
    for ext in ("png", "pdf"):
        fig.savefig(figure_folder / f"01_bahrain_learned_transfer.{ext}", dpi=300)
    plt.close(fig)


def verify(output):
    manifest = read(output / "manifest.json")
    bindings = {}
    for group in ("inputs", "sources", "outputs"):
        for path, digest in manifest[group].items():
            bind(path, digest, bindings)
    contract = read(output / "contract.json")
    metrics = read(output / "metrics.json")
    protocol = contract["protocol"]
    rows = {(row["policy"], row["cells"]): row for row in metrics["rows"]}
    assert len(rows) == len(metrics["rows"]) == 28
    for row in rows.values():
        read_and_check(row, contract["model"], protocol, contract["boundaries_m"][str(row["cells"])])
    individual, pairs = numerical(rows, protocol)
    assert individual == metrics["individual_grid_checks"]
    assert pairs == [dict(p, time_savings_s={int(k): v for k, v in p["time_savings_s"].items()})
                     for p in metrics["comparisons"]]
    print(f"Verified {len(bindings)} hashes and {len(rows)} independent replay audits.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--figures", type=Path, default=FIGURES)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        verify(args.output)
        return
    protocol = read(PROTOCOL)
    inputs = {PROTOCOL.as_posix(): sha(PROTOCOL)}
    code = {Path(p).as_posix(): h for p, h in sources().items()}
    for script in (Path(__file__).name, "bahrain_pace_model.py", "benchmark_circuit_control.py",
                   "train_regeneration_imitation.py", "validate_regeneration.py", "verify_bahrain_deployment.py"):
        path = Path("scripts", script)
        code[path.as_posix()] = sha(path)
    model, heldout, corners, rows, checkpoints = provenance(protocol, inputs, code)
    torch.set_num_threads(1)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA checkpoint inference is unavailable in this environment")
    primary = protocol["primary_cells_per_block"]
    refined = protocol["refined_cells_per_block"]
    envs = {cells: build_env(model, cells) for cells in (primary, refined)}
    boundaries = {cells: env.grid.distance_m[::cells].tolist() for cells, env in envs.items()}
    for env in envs.values():
        if env.observation_space.shape != (protocol["observations"],) or env.blocks != protocol["action_blocks"]:
            raise ValueError("Bahrain environment observation or action-block mismatch")
    np.testing.assert_allclose(boundaries[primary], boundaries[refined], rtol=0, atol=1e-7)
    traces = {key: read_and_check(row, model, protocol, boundaries[key[1]]) for key, row in rows.items()}
    if any(not row["feasible"] for row in rows.values()):
        raise ValueError("An archived comparator failed feasibility")
    args.output.mkdir(parents=True, exist_ok=False)
    args.figures.mkdir(parents=True, exist_ok=False)
    save(args.output / "contract.json",
         dict(protocol=protocol, model=model, observations=OBSERVATIONS, inputs=inputs, sources=code,
              boundaries_m=boundaries, calibration_heldout_checks_passed=heldout,
              runtime=dict(torch=torch.__version__, sb3=sb3_version, cuda=torch.version.cuda,
                           device=torch.cuda.get_device_name(protocol["inference_device"]))))
    started = time.perf_counter()
    checkpoint_rows = []
    for (method, width, seed), path in checkpoints.items():
        name = f"{method} {width} seed {seed}"
        module, predict = load_policy(protocol, envs[primary], path, method, width, seed)
        if any(str(p.device) != protocol["inference_device"] or not torch.isfinite(p).all()
               for p in module.parameters()):
            raise ValueError(f"Unexpected parameter device or nonfinite weights: {path}")
        checkpoint_rows.append(dict(policy=name, path=path.as_posix(), sha256=inputs[path.as_posix()],
                                    shapes={k: list(v.shape) for k, v in module.state_dict().items()}))
        for cells, env in envs.items():
            observations = []

            def policy(obs):
                observations.append(obs.tolist())
                return predict(obs)

            tick = time.perf_counter()
            with torch.inference_mode():
                lap = rollout(env, policy)
            replay_seconds = time.perf_counter() - tick
            file = args.output / f"{method.lower()}_{width}_seed{seed}_{cells}.json.gz"
            gzsave(file, dict(lap, pre_action_observations=observations))
            audit = audit_replay(lap, model, model, SimpleNamespace(**model["vehicle"]))
            row = {key: value for key, value in lap.items() if key not in ("trace", "reward_sum")}
            row.update(audit, policy=name, method=method, width=width, seed=seed, cells=cells,
                       replay_seconds=replay_seconds, file=file.as_posix(), checkpoint=path.as_posix(),
                       wheel_assist_j=sum(b["electrical_work_j"] for b in lap["trace"]))
            rows[name, cells] = row
            traces[name, cells] = read_and_check(row, model, protocol, boundaries[cells])
            print(f"{name}, {cells}: {row['duration_s']:.9f} s, feasible={row['feasible']}, "
                  f"finish error={row['terminal_speed_error_mps']:.6f} m/s", flush=True)
    individual, comparisons = numerical(rows, protocol)
    profiles = distance_profiles(model, rows, traces, args.output / "deployment_by_distance.csv")
    plot(args.figures, profiles, rows, primary, refined, corners, comparisons)
    save(args.output / "metrics.json", dict(
        training_performed=False, calibration_heldout_checks_passed=heldout, checkpoints=checkpoint_rows,
        rows=list(rows.values()), individual_grid_checks=individual, comparisons=comparisons,
        wall_seconds=time.perf_counter() - started))
    if any(sha(path) != digest for path, digest in (inputs | code).items()):
        raise ValueError("Inputs or sources changed during evaluation")
    outputs = [path for folder in (args.output, args.figures) for path in sorted(folder.iterdir()) if path.is_file()]
    save(args.output / "manifest.json", dict(inputs=inputs, sources=code, outputs={p.as_posix(): sha(p) for p in outputs}))
    verify(args.output)


if __name__ == "__main__":
    main()
