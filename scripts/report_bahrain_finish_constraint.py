"""Compare trained Bahrain policies with and without the common finish guard."""
import argparse
import csv
from itertools import product
from pathlib import Path

import numpy as np
from matplotlib.colors import TwoSlopeNorm
from matplotlib.lines import Line2D

from benchmark_circuit_control import plt, save, sha
from verify_bahrain_deployment import close, read, verify_rollout


ARMS = ("penalty_raw", "penalty_guarded", "constrained_raw", "constrained_guarded")
BASELINES = ("spread", "planner")
LABELS = {
    "penalty_raw": "Penalty / raw",
    "penalty_guarded": "Penalty / guarded",
    "constrained_raw": "Constrained / raw",
    "constrained_guarded": "Constrained / guarded",
}
COLORS = dict(zip(ARMS, ("#586573", "#246494", "#974a21", "#007a68")))
GRIDS = (160, 320)
MODEL = Path("results/bahrain-pace-calibration-001/model.json")


def signed(path, entries):
    digest = sha(path)
    if entries.get(path.as_posix()) != digest:
        raise ValueError(f"Missing signature or mismatched hash: {path}")
    return digest


def sample(row):
    return row["method"], row["width"], row["seed"]


def identity(row):
    return (row["arm"], row["policy"]) if row["arm"].startswith("baseline_") else (row["arm"], *sample(row))


def comparison_name(key):
    return f"{key[1]} {key[0].split('_')[1]}" if len(key) == 2 else LABELS[key[0]]


def comparison_inputs(run):
    manifest_path = run / "manifest.json"
    manifest = read(manifest_path)
    entries = {Path(p).as_posix(): h for p, h in (manifest["inputs"] | manifest["outputs"]).items()}
    inputs = {manifest_path.as_posix(): sha(manifest_path)}
    for path in (run / "contract.json", run / "metrics.json", MODEL):
        inputs[path.as_posix()] = signed(path, entries)
    protocol = read(run / "contract.json")["protocol"]
    model = read(MODEL)
    records = read(run / "metrics.json")["rows"]
    samples = list(product(("PPO", "SAC"), protocol["widths"], protocol["seeds"]))
    keys = [(arm, *s) for s in samples for arm in ARMS]
    keys += list(product(("baseline_raw", "baseline_guarded"), BASELINES))
    rows = {(identity(r), r["cells"]): r for r in records}
    declared_grids = tuple(protocol[f"{g}_cells_per_block"] for g in ("primary", "refined"))
    if declared_grids != GRIDS or len(rows) != len(records) or set(rows) != set(product(keys, GRIDS)):
        raise ValueError("Replay matrix differs from the declared sample, arm, baseline or grid coverage")
    for row in records:
        path = Path(row["file"])
        inputs[path.as_posix()] = signed(path, entries)
    return protocol, model, samples, keys, rows, inputs


def grid_check(coarse, fine, limits):
    changes = dict(
        relative_lap_change=abs(coarse["duration_s"] - fine["duration_s"]) / fine["duration_s"],
        terminal_energy_change_j=abs(coarse["final_energy_j"] - fine["final_energy_j"]),
        recovered_change_j=abs(coarse["recovered_j"] - fine["recovered_j"]),
    )
    both_feasible = bool(coarse["feasible"] and fine["feasible"])
    within_limits = all(value <= limits[key] for key, value in changes.items())
    return dict(changes, both_feasible=both_feasible, within_limits=within_limits,
                grid_pass=both_feasible and within_limits)


def pair(rows, checks, limits, contrast, reference, candidate, method=None, width=None, seed=None):
    """A positive gap favours the candidate; both grids must qualify before publication."""
    present = all(checks[key]["both_feasible"] for key in (reference, candidate))
    gaps = [rows[reference, g]["duration_s"] - rows[candidate, g]["duration_s"] for g in GRIDS] if present else [None, None]
    drift = abs(gaps[0] - gaps[1]) if present else None
    individual_limits_pass = all(checks[key]["within_limits"] for key in (reference, candidate))
    grid_pass = bool(present and individual_limits_pass and drift <= limits["paired_gap_change_s"])
    resolved = bool(grid_pass and gaps[0] * gaps[1] > 0)
    return dict(
        method=method, width=width, seed=seed, contrast=contrast,
        reference=comparison_name(reference), candidate=comparison_name(candidate),
        reference_feasible_both=checks[reference]["both_feasible"],
        candidate_feasible_both=checks[candidate]["both_feasible"],
        individual_limits_pass=individual_limits_pass,
        time_saving_160_s=gaps[0] if grid_pass else None,
        time_saving_320_s=gaps[1] if grid_pass else None,
        gap_change_s=drift, grid_pass=grid_pass, resolved_direction=resolved,
    )


def contrasts(rows, checks, limits, samples):
    training = (("raw_training", "penalty_raw", "constrained_raw"),
                ("guarded_training", "penalty_guarded", "constrained_guarded"),
                ("penalty_guard_effect", "penalty_raw", "penalty_guarded"),
                ("constrained_guard_effect", "constrained_raw", "constrained_guarded"))
    out, attribution = [], []
    for s in samples:
        matched = {name: pair(rows, checks, limits, name, (ref, *s), (cand, *s), *s)
                   for name, ref, cand in training}
        out.extend(matched.values())
        comparisons = {}
        for arm in ARMS:
            baseline_arm = "baseline_" + arm.rsplit("_", 1)[1]
            for policy in BASELINES:
                name = f"{arm}_versus_{policy}"
                comparisons[name] = pair(rows, checks, limits, name, (baseline_arm, policy), (arm, *s), *s)
        out.extend(comparisons.values())
        raw = matched["raw_training"]
        guarded = matched["guarded_training"]
        raw_check, penalty_check = checks[("constrained_raw", *s)], checks[("penalty_raw", *s)]
        attribution.append(dict(
            method=s[0], width=s[1], seed=s[2],
            raw_constrained_grid_pass=raw_check["grid_pass"],
            raw_constrained_feasibility_gain=raw_check["grid_pass"] and not penalty_check["both_feasible"],
            raw_constrained_time_gain=raw["resolved_direction"] and raw["time_saving_320_s"] > 0,
            guarded_constrained_time_gain=guarded["resolved_direction"] and guarded["time_saving_320_s"] > 0,
            constrained_guard_rescue=checks[("constrained_guarded", *s)]["grid_pass"] and not raw_check["both_feasible"],
            penalty_guard_rescue=checks[("penalty_guarded", *s)]["grid_pass"] and not penalty_check["both_feasible"],
        ))
    for mode in ("raw", "guarded"):
        out.append(pair(rows, checks, limits, f"{mode}_planner_versus_spread",
                        (f"baseline_{mode}", "spread"), (f"baseline_{mode}", "planner")))
    for policy in BASELINES:
        out.append(pair(rows, checks, limits, f"{policy}_guard_effect",
                        ("baseline_raw", policy), ("baseline_guarded", policy)))
    return out, attribution


def distance_profile(row, model, num_blocks):
    blocks = verify_rollout(row, model)
    if len(blocks) != num_blocks:
        raise ValueError(f"Incorrect block count: {row['file']}")
    power = model["vehicle"]["electrical_limit_w"]
    start, charge = 0., model["initial_energy_j"]
    for i, b in enumerate(blocks, 1):
        state, dt = b["state"], b["duration_s"]
        applied = b["action"]
        guard = b.get("finish_constraint")
        if (guard is not None) != row["arm"].endswith("_guarded"):
            raise ValueError(f"Guard presence differs from replay mode: {row['file']}")
        proposed, probes = applied, 0
        if guard is not None:
            proposed, probes = guard["proposed_action"], guard["lookahead_transitions"]
            phase = "terminal" if i > num_blocks - 3 else "prefix"
            close(guard["issued_action"], applied)
            if guard["changed"] != (applied != proposed) or guard["phase"] != phase:
                raise ValueError(f"Guard metadata differs from executed action: {row['file']}")
        end = state["distance_m"]
        actual = b["electrical_work_j"]
        if (not 0 <= proposed <= 1 or dt <= 0 or end <= start
                or not 0 <= actual <= applied * power * dt + 1e-5
                or not isinstance(probes, int) or probes < 0):
            raise ValueError(f"Invalid request, duration or distance: {row['file']}")
        yield dict(
            arm=row["arm"], policy=row["policy"], method=row["method"], width=row["width"], seed=row["seed"],
            cells=row["cells"], feasible=row["feasible"], block=i, from_m=start, to_m=end,
            final_three=i > num_blocks - 3, duration_s=dt, proposed_action=proposed, applied_action=applied,
            proposed_power_kw=proposed * power / 1000, applied_power_kw=applied * power / 1000,
            delivered_mean_power_kw=actual / dt / 1000,
            proposed_requested_work_j=proposed * power * dt, applied_requested_work_j=applied * power * dt,
            delivered_wheel_work_j=actual, recovered_j=b["battery_recovered_j"],
            start_energy_j=charge, end_energy_j=state["energy_j"],
            starting_headroom_j=model["regeneration"]["capacity_j"] - charge,
            action_changed=applied != proposed, action_reduced=applied < proposed,
            action_increased=applied > proposed, lookahead_transitions=probes,
        )
        start, charge = end, state["energy_j"]


def lap_summary(row, profile, model):
    target = model["initial_speed_mps"]
    out = dict(row, target_finish_speed_mps=target,
               achieved_finish_speed_mps=target + row["terminal_speed_error_mps"])
    for zone, blocks in (("lap", profile), ("final_three", [b for b in profile if b["final_three"]])):
        for field in ("proposed_requested_work_j", "applied_requested_work_j", "delivered_wheel_work_j",
                      "recovered_j", "action_changed", "action_reduced", "action_increased", "lookahead_transitions"):
            out[f"{zone}_{field}"] = sum(b[field] for b in blocks)
    close(out["lap_delivered_wheel_work_j"], row["wheel_assist_j"])
    for recorded, computed in (("guard_interventions", "lap_action_changed"),
                               ("guard_extra_block_integrations", "lap_lookahead_transitions")):
        if recorded in row:
            close(row[recorded], out[computed])
    return out


def save_csv(file, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with file.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save_figure(fig, folder, name):
    for ext in ("png", "pdf"):
        fig.savefig(folder / f"{name}.{ext}", dpi=300)
    plt.close(fig)


def feasibility_figure(folder, rows, samples, model):
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 5.3), layout="constrained",
                            gridspec_kw={"width_ratios": [2.35, 1]}, sharey=True)
    ax, refs = axes
    group = list(dict.fromkeys((m, w) for m, w, _ in samples))
    seeds = list(dict.fromkeys(seed for _, _, seed in samples))
    markers = {160: "o", 320: "+"}
    for m, w, seed in samples:
        x = group.index((m, w))
        for u, arm in enumerate(ARMS):
            for grid in GRIDS:
                shift = -.015 if grid == 160 else .015
                y = rows[(arm, m, w, seed), grid]["terminal_speed_error_mps"]
                values = (.2 * (u - 1.5), .04 * (seeds.index(seed) - (len(seeds) - 1) / 2), shift)
                ax.plot(x + sum(values), y, markers[grid], color=COLORS[arm], ms=6, mfc="none")
    ref_keys = [(mode, policy) for policy in BASELINES for mode in ("baseline_raw", "baseline_guarded")]
    for i, k in enumerate(ref_keys):
        for grid in GRIDS:
            shift = -.11 if grid == 160 else .11
            row = rows[k, grid]
            refs.plot(i + shift, row["terminal_speed_error_mps"], markers[grid], color="#344d5b", ms=6, mfc="none")
    for axis in axes:
        axis.axhline(0, color="#30353b", lw=.9, ls=":")
        axis.grid(axis="y", alpha=.22)
    ax.set(title="Learned policies", ylabel="Achieved minus target finish speed (m/s)")
    ax.set_xticks(range(len(group)), [f"{m} {w}" for m, w in group])
    refs.set(title="Model-based benchmarks")
    refs.set_xticks(range(len(ref_keys)), [f"{k[1].title()}\n{k[0].split('_')[1]}" for k in ref_keys])
    legend = [Line2D([], [], color=COLORS[a], marker="o", ls="", label=LABELS[a]) for a in ARMS]
    legend += [Line2D([], [], color="0.25", marker=mark, ls="", label=f"{g} cells", mfc="none")
               for g, mark in markers.items()]
    fig.legend(handles=legend, loc="outside lower center", ncol=3, fontsize=9)
    fig.suptitle(f"Bahrain simulator finish-speed errors across all replays\n"
                 f"Rolling target {model['initial_speed_mps']:.3f} m/s • seeds {seeds[0]}–{seeds[-1]} left to right within each arm")
    save_figure(fig, folder, "01_finish_feasibility")


def paired_figure(folder, pairs, samples):
    wanted = [
        ("raw_training", "Training effect\nRaw"),
        ("guarded_training", "Training effect\nGuarded"),
        ("penalty_guard_effect", "Guard effect\nPenalty"),
        ("constrained_guard_effect", "Guard effect\nConstrained"),
        ("penalty_guarded_versus_spread", "Penalty + guard\nvs guarded spread"),
        ("constrained_guarded_versus_spread", "Constrained + guard\nvs guarded spread"),
        ("penalty_guarded_versus_planner", "Penalty + guard\nvs guarded planner"),
        ("constrained_guarded_versus_planner", "Constrained + guard\nvs guarded planner"),
    ]
    index = {(sample(p), p["contrast"]): p for p in pairs}
    table = [[index[s, name] for name, _ in wanted] for s in samples]
    values = np.array([[1000 * r["time_saving_320_s"] if r["resolved_direction"] else np.nan
                        for r in entries] for entries in table])
    finite = values[np.isfinite(values)]
    scale = max(1., np.abs(finite).max()) if finite.size else 1.
    cmap = plt.get_cmap("RdBu").copy()
    cmap.set_bad("#e9edf0")
    fig, ax = plt.subplots(figsize=(13, 7.2), layout="constrained")
    image = ax.pcolormesh(np.arange(len(wanted) + 1) - .5, np.arange(len(samples) + 1) - .5, values,
                          cmap=cmap, norm=TwoSlopeNorm(vmin=-scale, vcenter=0, vmax=scale))
    ax.invert_yaxis()
    ax.set_xticks(range(len(wanted)), [title for _, title in wanted], fontsize=9)
    ax.set_yticks(range(len(samples)), [f"{m} {w} · seed {s}" for m, w, s in samples])
    ax.tick_params(length=0)
    for i, entries in enumerate(table):
        if i > 0 and samples[i][:2] != samples[i - 1][:2]:
            ax.axhline(i - .5, color="white", lw=2)
        for j, row in enumerate(entries):
            v = values[i, j]
            if np.isfinite(v):
                label, color = f"{v:+.1f}", ("white" if abs(v) > .64 * scale else "#17252e")
            elif not (row["candidate_feasible_both"] and row["reference_feasible_both"]):
                label, color = "Infeasible", "#4c5760"
            else:
                label, color = ("Unresolved" if row["grid_pass"] else "Grid check"), "#4c5760"
            ax.text(j, i, label, color=color, ha="center", va="center", fontsize=8.5)
    if finite.size:
        bar = fig.colorbar(image, ax=ax, location="right", shrink=.75, label="Time saved at 320 cells per block (ms)")
        bar.solids.set_rasterized(False)
    ax.set_title("Matched Bahrain finish-constraint comparisons\n"
                 "Signed gaps require physical feasibility, individual grid checks and paired drift ≤ 5 ms")
    save_figure(fig, folder, "02_matched_time_comparisons")


def distance_figure(folder, profiles, samples):
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.1), layout="constrained")
    full, frequency, tail_penalty, tail_constrained = axes.flat
    styles = (("proposed_requested_work_j", "Proposed request", "#6c7884"),
              ("applied_requested_work_j", "Applied request", "#ad4b21"),
              ("delivered_wheel_work_j", "Delivered at wheels", "#1e708c"))
    tails = {"penalty_guarded": tail_penalty, "constrained_guarded": tail_constrained}
    for arm in ARMS:
        profiles_arm = [profiles[(arm, *s), 320] for s in samples]
        distances = np.array([p["to_m"] for p in profiles_arm[0]]) / 1000
        work = np.array([[p["delivered_wheel_work_j"] for p in lap] for lap in profiles_arm])
        cumulative = np.cumsum(work, axis=1) / 1e6
        full.plot(np.r_[0, distances], np.r_[0, np.median(cumulative, axis=0)],
                  color=COLORS[arm], label=LABELS[arm], ls="--" if arm.endswith("_raw") else "-")
        full.fill_between(np.r_[0, distances], np.r_[0, cumulative.min(axis=0)], np.r_[0, cumulative.max(axis=0)],
                          color=COLORS[arm], alpha=.12)
        if arm not in tails:
            continue
        tail = tails[arm]
        changed = np.array([[p["action_changed"] for p in lap] for lap in profiles_arm])
        frequency.step(np.r_[0, distances], np.r_[changed.sum(axis=0), changed[:, -1].sum()],
                       where="post", color=COLORS[arm], label=LABELS[arm])
        for j, (field, label, color) in enumerate(styles):
            values = np.array([[p[field] for p in lap[-3:]] for lap in profiles_arm]) / 1000
            bar = np.median(values, axis=0)
            deviations = [bar - values.min(axis=0), values.max(axis=0) - bar]
            tail.bar(np.arange(3) + .24 * (j - 1), bar, width=.22, yerr=deviations,
                     color=color, alpha=.86, label=label, error_kw={"lw": 1, "capsize": 2})
        labels = [f"{p['block']}\n{p['from_m']/1000:.2f}–{p['to_m']/1000:.2f} km" for p in profiles_arm[0][-3:]]
        tail.set_xticks(range(3), labels)
        tail.set(title=f"{LABELS[arm]} · final three blocks", ylabel="Energy per block (kJ)")
    tail_penalty.sharey(tail_constrained)
    suffix_start = profiles_arm[0][-3]["from_m"] / 1000
    for axis in (full, frequency):
        axis.axvspan(suffix_start, distances[-1], color="#657487", alpha=.12, zorder=0)
    full.set(title="Cumulative delivered wheel work", ylabel="Wheel work (MJ)", xlabel="Distance from timing line (km)")
    frequency.set(title="Where the guard changed the action", ylabel="Number of affected policies",
                  xlabel="Distance from timing line (km)", ylim=(-.3, len(samples) + .7))
    full.legend(fontsize=8, ncol=2)
    tail_penalty.legend(fontsize=8)
    for ax in axes.flat:
        ax.grid(axis="y", alpha=.2)
        ax.set_axisbelow(True)
    fig.suptitle("Finish guard work and intervention at 320 cells per block\n"
                 "Medians and full ranges across policies • requested work uses the actual block duration")
    save_figure(fig, folder, "03_guard_intervention_distance")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path("results/bahrain-finish-constraint-001"))
    parser.add_argument("--output", type=Path, default=Path("results/bahrain-finish-constraint-comparison-001"))
    parser.add_argument("--figures", type=Path, default=Path("figures/dissertation/bahrain-finish-constraint-v1"))
    args = parser.parse_args()
    protocol, model, samples, keys, rows, inputs = comparison_inputs(args.run)
    limits = protocol["refinement"]
    profiles = {key: list(distance_profile(row, model, protocol["action_blocks"])) for key, row in rows.items()}
    laprows = {key: lap_summary(rows[key], profile, model) for key, profile in profiles.items()}
    checks = {key: grid_check(rows[key, 160], rows[key, 320], limits) for key in keys}
    pairs, attribution = contrasts(rows, checks, limits, samples)
    summary = {}
    for arm in ARMS:
        for method, width in dict.fromkeys((m, w) for m, w, _ in samples):
            group = [(arm, m, w, seed) for m, w, seed in samples if (m, w) == (method, width)]
            member_pairs = [p for p in pairs if (p["method"], p["width"]) == (method, width)
                            and p["contrast"].startswith(f"{arm}_versus_")]
            summary[f"{arm} {method} {width}"] = dict(
                samples=len(group), feasible_160=sum(rows[k, 160]["feasible"] for k in group),
                feasible_320=sum(rows[k, 320]["feasible"] for k in group),
                feasible_both=sum(checks[k]["both_feasible"] for k in group),
                passes_individual_grid_gate=sum(checks[k]["grid_pass"] for k in group),
                beats_like_for_like_spread=sum(p["resolved_direction"] and p["time_saving_320_s"] > 0
                                              for p in member_pairs if p["contrast"].endswith("_spread")),
                beats_like_for_like_planner=sum(p["resolved_direction"] and p["time_saving_320_s"] > 0
                                               for p in member_pairs if p["contrast"].endswith("_planner")),
            )
    baseline = [laprows[(mode, name), g] for mode, name, g in product(("baseline_raw", "baseline_guarded"), BASELINES, GRIDS)]
    if args.output.exists() or args.figures.exists():
        raise FileExistsError("Choose new output and figure directories")
    args.output.mkdir(parents=True)
    args.figures.mkdir(parents=True)
    save_csv(args.output / "replays.csv", [laprows[k, g] for k in keys for g in GRIDS])
    save_csv(args.output / "grid_checks.csv", [
        dict(arm=k[0], policy=rows[k, 160]["policy"], method=rows[k, 160]["method"],
             width=rows[k, 160]["width"], seed=rows[k, 160]["seed"], **checks[k]) for k in keys])
    save_csv(args.output / "paired_comparisons.csv", pairs)
    save_csv(args.output / "distance_profiles.csv", [b for p in profiles.values() for b in p])
    save_csv(args.output / "final_three_blocks.csv", [b for p in profiles.values() for b in p if b["final_three"]])
    save_csv(args.output / "training_attribution.csv", attribution)
    captions = {
        "01_finish_feasibility": "Actual signed finish error for every Bahrain replay and both numerical grids.",
        "02_matched_time_comparisons": "Signed fine-grid paired time differences with feasible and numerically stable direction.",
        "03_guard_intervention_distance": "Delivered wheel assist, request equivalents and action changes by distance at 320 cells per block. The shaded distance interval covers the final three blocks. Lines and bars show medians across all twelve policy seeds per training arm, with full ranges.",
    }
    save(args.output / "comparison.json", dict(run=args.run.as_posix(), refinement=limits, summary=summary,
         paired_time_sign="Reference minus candidate; positive means candidate faster.",
         work_columns="Proposed and applied requested work use their power requests and the actual block duration. "
         "Delivered wheel work is integrated by the physical model.",
         comparisons=pairs, training_attribution=attribution, baselines=baseline,
         attribution_rule="A raw feasibility gain requires stable constrained raw and an infeasible penalty raw. "
         "A raw or guarded time gain requires positive gaps at both grids within every acceptance limit. "
         "A guard rescue requires stable guarded evaluation and infeasibility in the same training arm without the guard."))
    feasibility_figure(args.figures, rows, samples, model)
    paired_figure(args.figures, pairs, samples)
    distance_figure(args.figures, profiles, samples)
    code_paths = (Path(__file__), Path("scripts/benchmark_circuit_control.py"),
                  Path("scripts/verify_bahrain_deployment.py"), Path("scripts/validate_regeneration.py"))
    code = {p.resolve().relative_to(Path.cwd()).as_posix(): sha(p) for p in code_paths}
    outputs = {p.as_posix(): sha(p) for folder in (args.output, args.figures) for p in sorted(folder.iterdir())}
    save(args.output / "manifest.json", dict(run=args.run.as_posix(), inputs=inputs, sources=code, outputs=outputs,
         captions=captions))
    print(f"{len(rows)} replays, {len(pairs)} paired comparisons, "
          f"{sum(p['resolved_direction'] for p in pairs)} resolved directions. Outputs at {args.output}.")


if __name__ == "__main__":
    main()
