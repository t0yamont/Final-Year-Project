"""Compare signed fixed- and free-finish Bahrain model experiments."""

import argparse
from itertools import product
from math import isclose
from pathlib import Path

from matplotlib.lines import Line2D

from benchmark_circuit_control import plt, save, sha
from map_bahrain_deployment import read_profiles
from report_bahrain_energy_scarcity import (
    CASES, GRIDS, REASONS, ZONES, paired_row, read_swaps, signed_files, zone_summary,
)
from report_bahrain_finish_constraint import save_csv, save_figure
from verify_bahrain_deployment import read


PLANNER = Path("results/bahrain-free-planner-001")
FREE_ZONES = Path("results/bahrain-free-zones-001")
FIXED_ZONES = Path("results/bahrain-scarcity-zones-001")
OUTPUT = Path("results/bahrain-free-finish-comparison-001")
FIGURES = Path("figures/dissertation/bahrain-free-finish-v1")
PROTOCOL = Path("configs/bahrain_free_finish.json")
SCHEDULES = {
    "fixed_winner_archive": ("Fixed-finish planner", "#244a68", "o"),
    "fixed_actions_free": ("Same requests, free finish", "#77727b", "s"),
    "free_winner": ("Free-finish planner", "#b04927", "D"),
}
FIXED = "fixed_winner_archive"
FREE = "free_winner"
METRICS = ("duration_s", "actual_finish_speed_mps", "wheel_assist_j", "final_three_blocks_work_j")
T10 = "t10_exit"


def planner_tables(cases, run, check):
    if set(cases) != set(CASES):
        raise ValueError("Planner cases differ from the four frozen Bahrain scenarios")
    replays, profiles, comparisons, matched = [], {}, [], []
    for case in CASES:
        details = cases[case]
        for grid in GRIDS:
            records = details["raw"][grid]
            profiles[case, grid] = read_profiles(check(run / case / f"profile_{grid}.csv"))
            for policy, replay in records.items():
                if replay is None:
                    continue
                blocks = profiles[case, grid][policy]
                if [row["block"] for row in blocks] != list(range(1, 56)):
                    raise ValueError(f"Incomplete block profile for {case}/{grid}/{policy}")
                work = [1000 * row["wheel_assist_kj"] for row in blocks]
                if not (
                    isclose(sum(work), replay["wheel_assist_j"], rel_tol=0, abs_tol=1e-5)
                    and isclose(sum(work[-3:]), replay["final_three_blocks_work_j"],
                                rel_tol=0, abs_tol=1e-5)
                ):
                    raise ValueError(f"Wheel work differs from the signed profile for {case}/{grid}/{policy}")
                replays.append(dict(case=case, cells_per_block=int(grid), schedule=policy,
                                    feasible=replay["feasible"], **{key: replay[key] for key in METRICS},
                                    recovered_j=replay["recovered_j"], final_energy_j=replay["final_energy_j"],
                                    block_53_wheel_work_j=work[-3], block_54_wheel_work_j=work[-2],
                                    block_55_wheel_work_j=work[-1], file=replay["file"]))
            baseline = records[FIXED]
            for policy in ("fixed_actions_free", FREE):
                alternative = records[policy]
                comparisons.append(dict(
                    case=case, cells_per_block=int(grid), schedule=policy, reference=FIXED,
                    both_feasible=baseline["feasible"] and alternative["feasible"],
                    **{f"fixed_{key}": baseline[key] for key in METRICS},
                    **{f"free_{key}": alternative[key] for key in METRICS},
                    **{f"free_minus_fixed_{key}": alternative[key] - baseline[key] for key in METRICS},
                ))
        selection = details["matched_spread"]
        matched.append(paired_row(case, FREE, "ordinary", selection))
    return replays, profiles, comparisons, matched


def grid_tables(cases):
    individual, paired = [], []
    for case, details in cases.items():
        refinement = details["raw_grid"]
        individual.extend(dict(case=case, schedule=policy, **values)
                          for policy, values in refinement["individual"].items())
        paired.extend(dict(case=case, schedule=policy, reference=FREE, **values)
                      for policy, values in refinement["paired"].items())
    return individual, paired


def spatial_tables(profiles, zones):
    for (case, grid), schedules in profiles.items():
        for policy in SCHEDULES:
            blocks = schedules[policy]
            ranges = {**zones, "final_three": (53, 55)}
            for zone, (start, end) in ranges.items():
                selected = blocks[start - 1:end]
                duration = sum(row["duration_s"] for row in selected)
                work = sum(row["wheel_assist_kj"] for row in selected)
                yield dict(case=case, cells_per_block=int(grid), schedule=policy, zone=zone,
                           first_block=start, last_block=end,
                           from_m=selected[0]["from_m"], to_m=selected[-1]["to_m"],
                           duration_s=duration, delivered_wheel_work_kj=work,
                           mean_requested_kw=sum(row["request_kw"] * row["duration_s"]
                                                 for row in selected) / duration,
                           mean_delivered_wheel_kw=work / duration)


def t10_table(fixed, free):
    zone_order = tuple(ZONES)
    for case, other in product(CASES, (key for key in zone_order if key != T10)):
        t10_donor = zone_order.index(other) > zone_order.index(T10)
        pair = (case, T10, other) if t10_donor else (case, other, T10)
        row = dict(case=case, competitor=other, competitor_label=ZONES[other])
        t10_direction = "donor_faster" if t10_donor else "recipient_faster"
        for mode, data in (("fixed", fixed), ("free", free)):
            packet = data[pair]
            status = packet["status"]
            row[f"{mode}_status"] = status
            outcome = status
            if status == "resolved":
                outcome = "won" if packet["direction"] == t10_direction else "lost"
            row[f"{mode}_t10_outcome"] = outcome
            for grid in GRIDS:
                raw = packet[f"delta_time_{grid}_ms"]
                row[f"{mode}_t10_advantage_{grid}_ms"] = (
                    float(raw) * (1 if t10_donor else -1) if raw else None
                )
        yield row


def t10_wins(rows):
    for case in CASES:
        result = {"case": case}
        for mode in ("fixed", "free"):
            head_to_heads = [row[f"{mode}_t10_outcome"] for row in rows if row["case"] == case]
            won = head_to_heads.count("won")
            lost = head_to_heads.count("lost")
            result.update({f"{mode}_wins": won, f"{mode}_losses": lost, f"{mode}_unresolved": 6 - won - lost,
                           f"{mode}_wins_all_six": won == 6})
        yield result


def paired_packets(fixed, free):
    for key, alternate in free.items():
        baseline = fixed[key]
        names = ("status", "direction", "resolved", "delta_time_320_ms")
        if any(alternate[f"fixed_{name}"] != baseline[name] for name in names):
            raise ValueError(f"Free run refers to a different historical packet comparison for {key}")
        yield {**alternate, **{f"fixed_{name}": value for name, value in baseline.items()
                              if name not in {"scenario", "donor", "recipient", "packet_kj"}}}


def lap_figure(folder, replays):
    fig, axes = plt.subplots(1, 3, sharey=True, figsize=(10, 4.2), layout="constrained")
    rows = {(row["case"], row["schedule"]): row for row in replays if row["cells_per_block"] == 320}
    for ax, metric, label, scale in zip(axes, (METRICS[0], METRICS[1], METRICS[3]),
                                       ("Lap time (s)", "Crossing speed (m/s)",
                                        "Final three blocks (kJ at wheels)"), (1, 1, .001)):
        for y, case in enumerate(CASES):
            values = [rows[case, policy][metric] * scale for policy in SCHEDULES]
            offsets = [y - .16, y, y + .16]
            ax.plot(values, offsets, color="#bbc3c9", lw=1, zorder=1)
            for value, offset, (policy, (_, color, marker)) in zip(values, offsets, SCHEDULES.items()):
                is_feasible = rows[case, policy]["feasible"]
                ax.plot(value, offset, marker=marker if is_feasible else "x", color=color,
                        ms=6.4, linestyle="", zorder=2)
        ax.set_xlabel(label)
        ax.set_yticks(range(len(CASES)), CASES.values())
        ax.grid(axis="x", alpha=.24)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
    axes[0].set_ylim(3.45, -.45)
    fig.suptitle("Bahrain model lap outcomes", fontsize=14, fontweight="bold")
    fig.legend(handles=[Line2D([], [], color=color, marker=marker, ls="", label=label)
                        for label, color, marker in SCHEDULES.values()],
               loc="outside lower center", ncol=3, frameon=False, fontsize=9)
    save_figure(fig, folder, "01_lap_outcomes")


def transfer_figure(folder, rows):
    fig, axes = plt.subplots(2, 2, sharex=True, sharey=True, figsize=(10, 6.4), layout="constrained")
    for ax, (case, label) in zip(axes.flat, CASES.items()):
        relevant = [row for row in rows if row["case"] == case]
        for y, row in enumerate(relevant):
            for finish, (color, marker), sep in zip(("fixed", "free"), (("#244a68", "o"), ("#b04927", "D")),
                                                   (-.13, .13)):
                status = row[f"{finish}_status"]
                if status == "resolved":
                    ax.plot(row[f"{finish}_t10_advantage_320_ms"], y + sep, marker=marker,
                            color=color, ms=5, linestyle="")
                else:
                    ax.text(.98, y + sep, REASONS[status][0], transform=ax.get_yaxis_transform(),
                            color=color, ha="right", va="center", fontsize=8)
        ax.set_yticks(range(len(relevant)), [row["competitor_label"] for row in relevant])
        ax.set_title(label, loc="left", fontsize=10, fontweight="bold")
        ax.axvline(0, color="#a4adb4", lw=.85)
        ax.set_xmargin(.14)
        ax.grid(axis="x", alpha=.22)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
    axes[0, 0].set_ylim(5.5, -.5)
    fig.suptitle("Bahrain model · 20 kJ packet at T10 exit", fontsize=14, fontweight="bold")
    fig.supxlabel("Competitor lap minus T10 lap (ms)")
    handles = [Line2D([], [], color=color, marker=marker, ls="", label=label)
               for label, color, marker in (SCHEDULES[FIXED], SCHEDULES[FREE])]
    statuses = {row[f"{mode}_status"] for row, mode in product(rows, ("fixed", "free"))}
    handles.extend(Line2D([], [], ls="", label=f"{mark}  {reason}") for status, (mark, reason)
                   in REASONS.items() if status in statuses)
    handles[0].set_label("Fixed finish")
    handles[1].set_label("Free finish")
    fig.legend(handles=handles, loc="outside lower center", ncol=len(handles), frameon=False, fontsize=8)
    save_figure(fig, folder, "02_t10_packet")


def deployment_figure(folder, profiles, zones):
    fig, axes = plt.subplots(4, 1, sharex=True, sharey=True, figsize=(10, 7.7), layout="constrained")
    for ax, (case, label) in zip(axes, CASES.items()):
        schedules = profiles[case, "320"]
        ax.set_title(label, loc="left", fontweight="bold", fontsize=9, pad=8)
        blocks = schedules[FIXED]
        for zone, (start, end) in zones.items():
            left = blocks[start - 1]["from_m"] / 1000
            right = blocks[end - 1]["to_m"] / 1000
            ax.axvspan(left, right, color="#dbe6ed", lw=0, zorder=0)
            if ax is axes[0]:
                ax.text((left + right) / 2, 132, ZONES[zone], ha="center", va="center", fontsize=7)
        ax.axvspan(blocks[52]["from_m"] / 1000, blocks[-1]["to_m"] / 1000,
                   color="#efe4da", lw=0, zorder=0)
        for policy, style in ((FIXED, "-"), (FREE, (0, (4, 1.5)))):
            blocks = schedules[policy]
            edges = [0, *(row["to_m"] / 1000 for row in blocks)]
            ax.stairs([row["wheel_assist_kw"] for row in blocks], edges, baseline=None,
                      color=SCHEDULES[policy][1], label=SCHEDULES[policy][0], lw=1.45, linestyle=style)
        ax.set(xlim=(0, edges[-1]), ylim=(-2, 144), yticks=(0, 60, 120))
        ax.grid(axis="y", alpha=.2)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Bahrain model · deployment by distance", fontsize=14, fontweight="bold")
    fig.supylabel("Delivered wheel-assist power (kW)")
    axes[-1].set_xlabel("Distance from timing line (km)")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="outside lower center",
               ncol=2, frameon=False, fontsize=9)
    save_figure(fig, folder, "03_deployment_by_distance")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--planner", type=Path, default=PLANNER)
    parser.add_argument("--free-zones", type=Path, default=FREE_ZONES)
    parser.add_argument("--fixed-zones", type=Path, default=FIXED_ZONES)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--figures", type=Path, default=FIGURES)
    args = parser.parse_args()
    if args.output.exists() or args.figures.exists():
        raise FileExistsError("Choose new output and figure directories")
    inputs = {}
    planner_check = signed_files(args.planner / "manifest.json", inputs)
    free_check = signed_files(args.free_zones / "manifest.json", inputs)
    fixed_check = signed_files(args.fixed_zones / "manifest.json", inputs)
    protocol = read(planner_check(PROTOCOL))
    parent_protocol = fixed_check(Path(protocol["parent_protocol"]))
    if sha(parent_protocol) != protocol["parent_protocol_sha256"]:
        raise ValueError("Fixed packet results use a different parent protocol")
    cases = read(planner_check(args.planner / "metrics.json"))["cases"]
    fixed = read_swaps(fixed_check(args.fixed_zones / "pairs.csv"))
    free = read_swaps(free_check(args.free_zones / "pairs.csv"))
    zone_path = fixed_check(args.fixed_zones / "zones.json")
    if sha(zone_path) != sha(free_check(args.free_zones / "zones.json")):
        raise ValueError("Packet zone definitions changed between end conditions")
    zones = {row["id"]: (row["first_block"], row["last_block"]) for row in read(zone_path)}
    if list(zones) != list(ZONES):
        raise ValueError("Expected the seven signed Bahrain zones in circuit order")
    replays, profiles, comparisons, matched = planner_tables(cases, args.planner, planner_check)
    individual_grid, paired_grid = grid_tables(cases)
    t10 = list(t10_table(fixed, free))
    packets = list(paired_packets(fixed, free))
    summary = [dict(finish_condition=mode, **row) for mode, data in (("fixed", fixed), ("free", free))
               for row in zone_summary(data)]
    tables = {
        "lap_replays": replays,
        "fixed_free_lap_differences": comparisons,
        "matched_spread": matched,
        "individual_grid_checks": individual_grid,
        "paired_grid_checks": paired_grid,
        "zone_work_and_power": list(spatial_tables(profiles, zones)),
        "paired_zone_comparisons": packets,
        "conditional_zone_outcomes": summary,
        "t10_head_to_heads": t10,
        "t10_case_summary": list(t10_wins(t10)),
    }
    args.output.mkdir(parents=True)
    args.figures.mkdir(parents=True)
    for name, rows in tables.items():
        save_csv(args.output / f"{name}.csv", rows)
    plt.rcParams["pdf.fonttype"] = 42
    lap_figure(args.figures, replays)
    transfer_figure(args.figures, t10)
    deployment_figure(args.figures, profiles, zones)
    captions = {
        "01_lap_outcomes": (
            "Model lap outcomes at 320 integration cells per block. The squares replay the archived fixed-finish "
            "requests with a free finish. The diamonds use the free-finish planner's own requests. A cross marks "
            "an infeasible replay. Whole-lap elapsed times are descriptive when delivered wheel work differs."
        ),
        "02_t10_packet": (
            "Each point gives the fine-grid time saved by placing a 20 kJ wheel-work packet at T10 exit "
            "instead of the named alternative. Positive values favor T10. Points are shown only for directions "
            "resolved by the signed work, feasibility and grid criteria. Symbols at right mark unresolved or "
            "failed comparisons. Packet priority is conditional on this frozen allocation and model. "
            "The full pair table retains all 21 comparisons in each case and finish condition. "
            "Earlier local motion checks found speed RMSE of 8.08 and 9.94 m/s around T10 on two separate laps."
        ),
        "03_deployment_by_distance": (
            "Electrical wheel work divided by action-block duration for the two searched schedules, "
            "using 320 cells per block. Blue shading marks the seven packet-test zones, in order "
            "from the timing-line straight, T1–T3, T8 exit, T10 exit, T11 exit, T13 exit and T15. "
            "Tan shading marks the final three blocks. The zone table gives starting and ending chainage, "
            "mean requested power and delivered work for both grids."
        ),
    }
    caption_text = ["# Bahrain fixed- and free-finish figures",
                    "All results describe simulated laps on the frozen Bahrain model.",
                    f"Source runs are {args.planner.as_posix()}, {args.free_zones.as_posix()} and "
                    f"{args.fixed_zones.as_posix()}.", "Each case retains its frozen starting charge and recovery share."]
    for name, caption in captions.items():
        caption_text += [f"## {name.replace('_', ' ')}", caption]
    (args.figures / "captions.md").write_text("\n\n".join(caption_text) + "\n", encoding="utf-8")
    source_names = ("report_bahrain_free_finish.py", "report_bahrain_energy_scarcity.py",
                    "benchmark_circuit_control.py", "map_bahrain_deployment.py",
                    "report_bahrain_finish_constraint.py", "verify_bahrain_deployment.py")
    sources = {path.as_posix(): sha(path) for path in (Path("scripts") / name for name in source_names)}
    outputs = {path.as_posix(): sha(path)
               for folder in (args.output, args.figures) for path in sorted(folder.iterdir())}
    save(args.output / "manifest.json", dict(inputs=inputs, sources=sources, outputs=outputs, captions=captions))


if __name__ == "__main__":
    main()

