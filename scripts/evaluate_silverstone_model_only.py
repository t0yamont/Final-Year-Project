"""Run a model-only Silverstone comparison at a zero-assist-supported rolling speed."""
import argparse
from itertools import product
import math
from pathlib import Path

import numpy as np
import torch

from bahrain_pace_model import build_env
from benchmark_circuit_control import plt, save, sha, sources
from compare_bahrain_equal_work import MATCH_J, MAX_BISECTIONS, SAMPLES, refinement, summaries
from evaluate_bahrain_learned_transfer import bind, from_manifest, read_and_check
from f1energy.circuit_control import baseline_policy, rollout
from map_bahrain_deployment import block_rows, deployment_zones, evaluate, export, search_scenario, write_profiles
from train_bahrain_algorithm_width import ALGORITHMS, numerical, replay, shape_checks, utc_now, verify_hashes
from verify_bahrain_deployment import read


CONFIG = Path("configs/silverstone_model_only.json")
OUTPUT = Path("results/silverstone-model-only-001")
FIGURES = Path("figures/dissertation/silverstone-model-only-v1")
STAGES = ("search", "primary", "refined")


def code_hashes():
    script_names = ("evaluate_silverstone_model_only", "compare_bahrain_equal_work",
                    "evaluate_bahrain_learned_transfer", "map_bahrain_deployment",
                    "train_bahrain_algorithm_width", "verify_bahrain_deployment", "bahrain_pace_model",
                    "benchmark_circuit_control", "optimize_regeneration_dp", "validate_regeneration")
    return {Path(p).as_posix(): h for p, h in sources().items()} | {
        f"scripts/{name}.py": sha(f"scripts/{name}.py") for name in script_names}


def bridge(protocol, inputs, code):
    root = Path(protocol["geometry_manifest"])
    finish = Path(protocol["finish_bound_manifest"])
    for name, path in (("geometry", root), ("finish_bound", finish)):
        bind(path, protocol[f"{name}_manifest_sha256"], inputs)
    geometry = read(root)
    unaffected = set(geometry["code"]) & code.keys()
    for path in unaffected:
        bind(path, geometry["code"][path], code)
    position = read(from_manifest(root.parent / "metrics.json", geometry, "outputs", inputs))
    bound = read(from_manifest(finish.parent / "metrics.json", read(finish), "outputs", inputs))
    if position["geometry_passed"] or position["pace_passed"] or not all(
            item["target_impossible"] for item in bound["bounds"]):
        raise ValueError("Missing original Silverstone failure or physical finish bound")
    model = read(from_manifest(protocol["model"], geometry, "outputs", inputs))
    from_manifest(model["geometry"], geometry, "outputs", inputs)
    bind(model["geometry"], model["geometry_sha256"], inputs)
    return model, position["registration"]


def choose_boundary(model, grids):
    """Sweep down to certify the highest integer without a monotonicity assumption."""
    trials = []
    for speed in range(math.floor(model["initial_speed_mps"]), 0, -1):
        candidate = dict(model, initial_speed_mps=float(speed))
        checks = {}
        for cells in grids:
            try:
                env = build_env(candidate, cells)
            except ValueError as exc:
                if not any(message in str(exc) for message in ("infeasible entry", "timing-line entry")):
                    raise
                checks[str(cells)] = {"feasible": False, "error": str(exc)}
                break
            result = rollout(env, baseline_policy("zero", env))
            checks[str(cells)] = {k: result[k] for k in
                                 ("feasible", "duration_s", "terminal_speed_error_mps", "final_energy_j")}
            if not result["feasible"]:
                break
        trials.append(dict(speed_mps=speed, checks=checks))
        if len(checks) == len(grids) and all(row["feasible"] for row in checks.values()):
            return candidate, trials
    return None, trials


def match_work(model, protocol, folder, envs, fixed, primary, fine):
    bounds = protocol["work_match"]
    scan = np.arange(bounds["alpha_scan_start"], bounds["alpha_scan_stop"] + bounds["alpha_scan_step"]/2,
                     bounds["alpha_scan_step"]).tolist()
    if scan != SAMPLES or bounds["absolute_wheel_work_tolerance_j"] != MATCH_J or bounds["max_bisections"] != MAX_BISECTIONS:
        raise ValueError("Work matching criteria differ from the frozen helper")
    folder.mkdir()
    target = {cells: fixed["selected", cells]["wheel_assist_j"] for cells in (primary, fine)}
    trials = {cells: {} for cells in target}

    def trial(cells, alpha):
        if alpha not in trials[cells]:
            trials[cells][alpha] = summaries(alpha, cells, envs[cells], model, folder)
        return trials[cells][alpha]

    def error(alpha):
        return trial(primary, alpha)["wheel_assist_j"] - target[primary]

    initial = [trial(primary, alpha) for alpha in scan]
    brackets = [refinement(low, high, error) for low, high in zip(scan, scan[1:]) if error(low) * error(high) < 0]
    candidates = {r["alpha"] for r in brackets} | {a for a in scan if abs(error(a)) <= MATCH_J}
    results = []
    for alpha in sorted(candidates or {min(scan, key=lambda a: (abs(error(a)), a))}):
        per_grid = {}
        for cells in target:
            other, selected = trial(cells, alpha), fixed["selected", cells]
            per_grid[str(cells)] = dict(
                other, difference_j=other["wheel_assist_j"] - target[cells],
                saving_s=other["duration_s"] - selected["duration_s"] if other["feasible"] and selected["feasible"] else None)
        a, b = per_grid.values()
        gap = abs(a["saving_s"] - b["saving_s"]) if a["saving_s"] is not None and b["saving_s"] is not None else None
        passes = (gap is not None and gap <= protocol["refinement"]["paired_gap_change_s"]
                  and all(abs(row["difference_j"]) <= MATCH_J for row in per_grid.values()))
        results.append(dict(alpha=alpha, grids=per_grid, paired_gap_change_s=gap, passed=passes))
    for cells in target:
        if read(trial(cells, 1.0)["file"]) != read(fixed["spread", cells]["file"]):
            raise ValueError("Alpha one and adaptive spread differ")
    preferred = min(results, key=lambda r: (not r["passed"], abs(r["grids"][str(primary)]["difference_j"]), r["alpha"]))
    save(folder / "metrics.json", dict(scan=initial, brackets=brackets, candidates=results, preferred=preferred,
                                      target_j=target, all_trials=trials))
    return preferred


def draw(path, env, traces, registration, rolling, match):
    fig, axes = plt.subplots(3, 1, figsize=(10.5, 7.7), sharex=True, layout="constrained")
    colors = ("#105c83", "#b55b22")
    for (name, trace), color in zip(traces.items(), colors):
        rows = list(block_rows(env, trace))
        edges = np.r_[0., [r["to_m"]/1000 for r in rows]]
        axes[0].stairs([r["wheel_assist_kw"] for r in rows], edges, label=name, color=color, lw=1.6)
        axes[0].stairs([r["request_kw"] for r in rows], edges, color=color, ls=":", lw=.9, alpha=.65)
        axes[1].stairs([r["battery_charge_kj"] for r in rows], edges, label=name, color=color, lw=1.4)
        axes[2].plot(edges, np.r_[env.initial_energy/1000, [r["battery_kj"] for r in rows]]/1000,
                     label=name, color=color, lw=1.4)
    axes[2].axhline(env.reserve / 1e6, color="#687077", ls=":", lw=.9, label="Battery reserve")
    turns = [1, 3, 6, 7, 9, 11, 14, 15, 16, 18]
    raw = np.array(registration["turn_station_m"])[np.array(turns) - 1]
    converted = np.interp(raw/registration["source_length_m"] * env.grid.parameter_m[-1],
                          env.grid.parameter_m, env.grid.distance_m)/1000
    for ax in axes:
        for mark in converted:
            ax.axvline(mark, color="#78909c", alpha=.18, lw=.8, zorder=0)
        ax.grid(axis="y", alpha=.2)
        ax.margins(x=0)
    top = axes[0].secondary_xaxis("top")
    top.set_xticks(converted, [f"T{n}" for n in turns], fontsize=8)
    status = "500 J work match and 5 ms refinement passed" if match["passed"] else "Work-match or refinement gate failed"
    fig.suptitle(f"Silverstone model only | {rolling:g} m/s rolling boundary\n{status}", fontsize=12)
    axes[0].set_ylabel("Wheel assist (kW)")
    axes[0].legend(fontsize=8, ncols=2, title="Solid delivered · dotted requested", title_fontsize=8)
    axes[1].set_ylabel("Battery recovery (kJ/block)")
    axes[2].set(ylabel="Stored energy (MJ)", xlabel="Distance from the control line (km)")
    axes[2].legend(fontsize=8)
    export(fig, path)


def load_checkpoints(protocol, inputs):
    root = Path(protocol["bahrain_run"])
    upstream_path = root / "manifest.json"
    upstream = read(upstream_path)
    bind(upstream_path, sha(upstream_path), inputs)
    results = read(from_manifest(root / "metrics.json", upstream, "outputs", inputs))
    design = read(from_manifest(root / "contract.json", upstream, "outputs", inputs))
    training = design["protocol"]
    expected = set(product(ALGORITHMS, protocol["widths"], protocol["seeds"]))
    observed = {(r["method"], r["width"], r["seed"]) for r in results["checkpoints"]}
    if (len(results["checkpoints"]) != len(expected) or observed != expected
            or any(training[key] != protocol[key] for key in ("widths", "seeds", "steps_per_seed", "action_blocks", "observations"))
            or not results["training_performed"]):
        raise ValueError("Incomplete or inconsistent Bahrain source study")
    paths = {}
    for row in results["checkpoints"]:
        key = (row["method"], row["width"], row["seed"])
        path = Path(row["checkpoint"])
        if not row["checkpoint_reload_exact"] or row["actual_steps"] != protocol["steps_per_seed"]:
            raise ValueError(f"Invalid Bahrain training endpoint {path}")
        from_manifest(path, upstream, "outputs", inputs)
        bind(path, row["checkpoint_sha256"], inputs)
        paths[key] = path
    return paths


def learned_replays(model, protocol, envs, paths, output):
    design = dict(model=model, protocol=protocol, boundaries_m={
        str(cells): env.grid.distance_m[::cells].tolist() for cells, env in envs.items()})
    torch.set_num_threads(1)
    rows = []
    for (method, width, seed), path in paths.items():
        agent = ALGORITHMS[method].load(path, device=protocol["inference_device"])
        agent.policy.set_training_mode(False)
        if agent.num_timesteps != protocol["steps_per_seed"] or agent.seed != seed:
            raise ValueError(f"Training endpoint changed: {path}")
        shape_checks(agent, method, width)
        for cells, env in envs.items():
            if agent.observation_space != env.observation_space or agent.action_space != env.action_space:
                raise ValueError(f"Policy interface changed: {path}")
            def predict(obs):
                return agent.predict(obs, deterministic=True)[0]
            rows.append(replay(output / f"{path.stem}_{cells}.json.gz", env, predict, design, cells,
                               f"{method} {width} seed {seed}", method=method, width=width, seed=seed,
                               checkpoint=path.as_posix(), checkpoint_sha256=sha(path)))
        print(f"{method} {width} seed {seed}: 2 unchanged deterministic replays", flush=True)
    return rows


def signed_manifest(output, figures, inputs, code):
    verify_hashes(inputs | code)
    save(output / "manifest.json", dict(inputs=inputs, sources=code, outputs={
        p.as_posix(): sha(p)
        for root in (output, figures) for p in sorted(root.rglob("*"))
        if p.is_file() and p.name != "manifest.json"}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--figures", type=Path, default=FIGURES)
    args = parser.parse_args()
    p = read(CONFIG)
    inputs, code = {CONFIG.as_posix(): sha(CONFIG)}, code_hashes()
    inherited, registration = bridge(p, inputs, code)
    checkpoints = load_checkpoints(p, inputs)
    search, primary, fine = grids = [p[f"{stage}_cells_per_block"] for stage in STAGES]
    args.output.mkdir(parents=True, exist_ok=False)
    args.figures.mkdir(parents=True, exist_ok=False)
    save(args.output / "contract.json", dict(protocol=p, inputs=inputs, sources=code, frozen_at=utc_now(),
                                            inherited_model=inherited))
    model, speed_trials = choose_boundary(inherited, grids)
    save(args.output / "rolling_speed.json", dict(speed_mps=model["initial_speed_mps"] if model else None,
                                                 inherited_mps=inherited["initial_speed_mps"], trials=speed_trials))
    metrics = dict(circuit="Silverstone", model_only=True, geometry_passed=False, pace_passed=False,
                   empirical_location_passed=False, rows=[])
    if model is None:
        save(args.output / "metrics.json", dict(metrics, failure="No zero-assist integer rolling boundary closed."))
        signed_manifest(args.output, args.figures, inputs, code)
        return

    save(args.output / "model.json", model)
    print(f"Zero-assist rolling boundary {model['initial_speed_mps']:g} m/s across {grids}", flush=True)
    calibrations = args.output / "zero_assist"
    calibrations.mkdir()
    for cells in grids:
        _, row = evaluate(build_env(model, cells), "zero", calibrations)
        if not row["feasible"]:
            raise ValueError(f"Saved zero-assist control disagrees with determination: {cells}")
    dp = args.output / "search"
    dp.mkdir()
    found = search_scenario(model, p, "silverstone_model_only", dp)

    envs = {cells: build_env(model, cells) for cells in (primary, fine)}
    np.testing.assert_allclose(envs[primary].grid.distance_m[::primary], envs[fine].grid.distance_m[::fine],
                               atol=1e-7, rtol=0)
    fixed = {}
    trace = {}
    for cells, env in envs.items():
        for name, actions in (("selected", found["actions"]), ("spread", None)):
            record, row = evaluate(env, name, args.output, actions)
            row.update(policy=name, cells=cells, file=Path(row["file"]).as_posix())
            read_and_check(row, model, p, env.grid.distance_m[::cells])
            fixed[name, cells], trace[name, cells] = row, record
    preferred = match_work(model, p, args.output / "work_match", envs, fixed, primary, fine)
    main_trace = trace["selected", fine]
    ref_trace, name = trace["spread", fine], "Adaptive spread"
    if preferred["passed"]:
        ref_trace = read(preferred["grids"][str(fine)]["file"])
        name = "Work-matched spread"
    plot_traces = {"Bounded DP schedule": main_trace, name: ref_trace}
    draw(args.figures / "01_silverstone_dp_energy", envs[fine], plot_traces, registration, model["initial_speed_mps"], preferred)
    write_profiles(args.output / "distance_profiles_320.csv", envs[fine], plot_traces)
    metrics["work_match"] = preferred
    metrics["rolling_speed_mps"] = model["initial_speed_mps"]
    metrics["deployment_zones_320"] = deployment_zones(envs[fine], main_trace, 20000)
    metrics["top_recovery_blocks_320"] = {
        name: sorted(block_rows(envs[fine], record), key=lambda r: -r["battery_charge_kj"])[:5]
        for name, record in plot_traces.items()}
    metrics["rows"] = list(fixed.values())
    save(args.output / "reference_metrics.json", metrics)
    print("Silverstone baselines and work match complete", flush=True)

    rows = metrics["rows"] + learned_replays(model, p, envs, checkpoints, args.output)
    checks, pairs = numerical(rows, p)
    save(args.output / "metrics.json", dict(metrics, rows=rows, individual_grid_checks=checks, comparisons=pairs))
    signed_manifest(args.output, args.figures, inputs, code)


if __name__ == "__main__":
    main()
