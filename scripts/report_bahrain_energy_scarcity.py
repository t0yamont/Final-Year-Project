"""Render the signed Bahrain energy-scarcity comparisons and preserve their gates."""

import argparse
import csv
from itertools import combinations, product
from math import isclose
from pathlib import Path

import numpy as np
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.lines import Line2D

from benchmark_circuit_control import plt, save, sha
from map_bahrain_deployment import read_profiles
from report_bahrain_finish_constraint import save_csv, save_figure
from verify_bahrain_deployment import read


CASES = {
    "nominal": "Nominal",
    "low_charge": "Low starting charge",
    "low_recovery": "Low recovery",
    "combined": "Low charge and recovery",
}
GRIDS = ("160", "320")
POLICIES = ("frozen", "adapted", "spread")
REFERENCES = {
    "frozen": "Frozen schedule",
    "adapted": "Scenario planner",
}
MATCHES = {"ordinary": "Ordinary spread", "terminal_suffix": "Spread with fixed finish"}
ZONES = dict(zip(
    ("timing_line", "t1_t3", "t8_exit", "t10_exit", "t11_exit", "t13_exit", "t15"),
    ("Timing line", "T1–T3", "T8 exit", "T10 exit", "T11 exit", "T13 exit", "T15"),
))
COLORS = ("#233c54", "#116d74", "#a74f30", "#694e90")
REASONS = {
    "unresolved": ("~", "direction inconclusive"),
    "feasibility_failed": ("F", "feasibility failed"),
    "match_failed": ("W", "work match failed"),
    "refinement_failed": ("G", "grid check failed"),
}
PLANNER = Path("results/bahrain-scarcity-planners-001")
SWAPS = Path("results/bahrain-scarcity-zones-001")
OUTPUT = Path("results/bahrain-energy-scarcity-comparison-001")
FIGURES = Path("figures/dissertation/bahrain-energy-scarcity-v1")
PROTOCOL = Path("configs/bahrain_energy_scarcity.json")


def signed_files(manifest_path, inputs):
    manifest = read(manifest_path)
    entries = {Path(path).resolve(): digest for section in ("inputs", "outputs")
               for path, digest in manifest.get(section, {}).items()}
    inputs[manifest_path.as_posix()] = sha(manifest_path)

    def check(path):
        digest = sha(path)
        if entries.get(path.resolve()) != digest:
            raise ValueError(f"Missing signature or mismatched hash: {path}")
        inputs[path.as_posix()] = digest
        return path

    return check


def planner_inputs(run, check):
    replays, profiles, comparisons = {}, {}, []
    for case in CASES:
        path = run / case
        metrics = read(check(path / "metrics.json"))
        for grid in GRIDS:
            profiles[case, grid] = read_profiles(check(path / f"profile_{grid}.csv"))
            for policy in POLICIES:
                replays[case, grid, policy] = metrics["raw"][grid].get(policy)
        for ref, match in product(REFERENCES, MATCHES):
            row = metrics["matched"].get(ref, {}).get(match)
            if row is not None:
                comparisons.append(paired_row(case, ref, match, row))
            elif match == "ordinary":
                comparisons.append(dict(case=case, schedule=ref, spread_comparator=match,
                                        passed=False, status="no_schedule"))
    return replays, profiles, comparisons


def paired_row(case, reference, match, result):
    selected = result.get("preferred")
    values = dict(case=case, schedule=reference, spread_comparator=match,
                  passed=False, status="no_candidate")
    if selected is None:
        return values
    grid_results = selected["grids"]
    for grid in GRIDS:
        outcome = grid_results[grid]
        values.update({
            f"spread_feasible_{grid}": outcome["spread"]["feasible"],
            f"schedule_feasible_{grid}": outcome["reference"]["feasible"],
            f"work_matched_{grid}": outcome["matched"],
            f"spread_time_{grid}_s": outcome["spread"]["duration_s"],
            f"schedule_time_{grid}_s": outcome["reference"]["duration_s"],
            f"spread_work_{grid}_j": outcome["spread"]["wheel_assist_j"],
            f"schedule_work_{grid}_j": outcome["reference"]["wheel_assist_j"],
            f"work_difference_{grid}_j": outcome["difference_j"],
            f"saving_{grid}_s": outcome["saving_s"],
        })
    if selected["passed"] and match == "terminal_suffix" and selected["alpha"] == 0:
        status = "terminal_only"
    elif selected["passed"]:
        status = "resolved" if selected["direction"] else "unresolved"
    elif not all(values[f"{arm}_feasible_{grid}"] for arm, grid in product(("spread", "schedule"), GRIDS)):
        status = "feasibility_failed"
    elif not all(values[f"work_matched_{grid}"] for grid in GRIDS):
        status = "match_failed"
    else:
        status = "refinement_failed"
    return dict(values, passed=selected["passed"], status=status, direction=selected["direction"],
                alpha=selected["alpha"], beta=selected.get("beta"), common_suffix_target_alpha=result.get("common_target_alpha"),
                schedule_refinement_pass=selected["individual_refinement"]["reference"]["passed"],
                spread_refinement_pass=selected["individual_refinement"]["spread"]["passed"],
                paired_gap_change_s=selected["paired_gap_change_s"])


def replay_rows(replays):
    metrics = ("feasible", "duration_s", "terminal_speed_error_mps", "final_energy_j", "recovered_j",
               "discharged_j", "wheel_assist_j", "file")
    for (case, grid, policy), replay in replays.items():
        yield dict(case=case, grid=grid, schedule=policy, schedule_found=replay is not None,
                   **{name: replay[name] for name in metrics} if replay is not None else {})


def matched_figure(folder, replays, comparisons):
    figure, (raw, paired, status) = plt.subplots(
        1, 3, sharey=True, figsize=(10.1, 7), layout="constrained",
        gridspec_kw={"width_ratios": (2.9, 4.5, 2.2)},
    )
    position = 0
    for (case, name), color in zip(CASES.items(), COLORS):
        rows = [row for row in comparisons if row["case"] == case]
        raw.text(-.42, position - .7, name, va="center", ha="left", fontsize=10, fontweight="bold")
        for column, policy in enumerate(POLICIES):
            for grid, marker, offset in zip(GRIDS, ("o", "D"), (-.15, .15)):
                replay = replays[case, grid, policy]
                feasible = replay is not None and replay["feasible"]
                raw.plot(column + offset, position + (len(rows) - 1) / 2,
                         marker=marker if feasible else "x" if replay else "_", ls="", ms=5.5,
                         mfc="white" if grid == "160" else "#276d65",
                         mec="#276d65" if feasible else "#ab4e34", mew=1.25)
        for index, row in enumerate(rows):
            y = position + index
            label = f"{REFERENCES[row['schedule']]} vs {MATCHES[row['spread_comparator']]}"
            paired.text(.01, y - .24, label, transform=paired.get_yaxis_transform(),
                        fontsize=8, ha="left", va="center", color="#24384a",
                        bbox=dict(fc="white", ec="none", alpha=.94, pad=.45))
            reason = row["status"]
            if reason in {"resolved", "unresolved"}:
                first, last = (1000 * row[f"saving_{grid}_s"] for grid in GRIDS)
                point_color = color if row["status"] == "resolved" else "#7d8590"
                paired.plot([first, last], [y + .06, y + .27], color=point_color, lw=.85)
                paired.plot(first, y + .06, "o", mfc="white", mec=point_color, ms=4.5)
                paired.plot(last, y + .27, "D", mfc=point_color, mec=point_color, ms=4)
            if reason in {"resolved", "unresolved"}:
                label = f"≈ {row['schedule_work_320_j'] / 1000:,.0f} kJ"
                if reason == "unresolved":
                    label += " · inconclusive"
                status.text(0, y + .16, label, ha="left", va="center", fontsize=8, color="#24384a")
            else:
                labels = dict(no_candidate="No candidate", no_schedule="No schedule",
                              terminal_only="Terminal-only diagnostic")
                label = labels[reason] if reason in labels else REASONS[reason][1].capitalize()
                status.text(0, y + .13, label, ha="left", va="center", fontsize=8, color="#6d514c")
        position += len(rows) + .85
    for ax in (raw, paired, status):
        ax.set_ylim(position - .98, -1.18)
        ax.tick_params(axis="y", left=False, labelleft=False)
        ax.spines[["top", "left", "right"]].set_visible(False)
    raw.set_xlim(-.48, 2.48)
    raw.set_title("Unmatched lap feasibility", fontsize=10)
    raw.set_xticks(range(3), ("Frozen", "Planner", "Spread"), fontsize=8)
    paired.set_title("Equal work at the wheels", fontsize=10)
    paired.set_xlabel("Spread lap minus schedule lap (ms)", fontsize=10)
    paired.axvline(0, color="#a6afb7", lw=.8, zorder=0)
    status.set_title("Wheel work or outcome", loc="left", fontsize=10)
    status.set_axis_off()
    legend = [
        Line2D([], [], marker=marker, ls="", mfc=face, mec="#276d65", label=f"{grid} cells per block")
        for grid, marker, face in zip(GRIDS, ("o", "D"), ("white", "#276d65"))
    ]
    legend.append(Line2D([], [], marker="x", ls="", mec="#ab4e34", label="Infeasible replay"))
    figure.legend(handles=legend, loc="outside lower center", ncol=3, frameon=False, fontsize=8)
    save_figure(figure, folder, "01_matched_timing")


def spatial_tables(profiles, replays, zones):
    for case, grid, policy in product(CASES, GRIDS, POLICIES):
        replay = replays[case, grid, policy]
        if replay is None:
            continue
        rows = profiles[case, grid][policy]
        if [row["block"] for row in rows] != list(range(1, 56)):
            raise ValueError(f"Expected an entire 55-block profile for {case}, {grid}, {policy}")
        overall_work = sum(row["wheel_assist_kj"] for row in rows)
        if not isclose(1000 * overall_work, replay["wheel_assist_j"], rel_tol=0, abs_tol=1e-5):
            raise ValueError(f"Profile and replay disagree in wheel work for {case}, {grid}, {policy}")
        selections = {name: [row for row in rows if first <= row["block"] <= last]
                      for name, (first, last) in zones.items()}
        named_blocks = {row["block"] for selection in selections.values() for row in selection}
        selections["outside_zones"] = [row for row in rows if row["block"] not in named_blocks]
        for zone, selected in selections.items():
            duration = sum(row["duration_s"] for row in selected)
            requested = sum(row["request_kw"] * row["duration_s"] for row in selected)
            delivered = sum(row["wheel_assist_kj"] for row in selected)
            recovered = sum(row["battery_charge_kj"] for row in selected)
            zone_range = dict(from_m=selected[0]["from_m"], to_m=selected[-1]["to_m"]) if zone in zones else {}
            yield dict(case=case, grid=grid, schedule=policy, feasible=replay["feasible"], zone=zone,
                       zone_label=ZONES.get(zone, "Outside the seven zones"), **zone_range,
                       duration_s=duration, requested_work_kj=requested, delivered_wheel_work_kj=delivered,
                       mean_request_kw=requested / duration, mean_delivered_wheel_kw=delivered / duration,
                       peak_block_mean_delivered_wheel_kw=max(row["wheel_assist_kw"] for row in selected),
                       share_of_lap_wheel_work=delivered / overall_work if overall_work else None,
                       battery_recovered_kj=recovered)


def deployment_figure(folder, profiles, replays, zones):
    figure, axes = plt.subplots(4, 1, figsize=(8.6, 6.9), sharex=True, sharey=True, layout="constrained")
    for (case, label), color, ax in zip(CASES.items(), COLORS, axes):
        rows = profiles[case, "320"].get("adapted")
        replay = replays[case, "320", "adapted"]
        if rows is None:
            ax.text(.5, .5, f"{label} · no scenario planner schedule", transform=ax.transAxes, ha="center")
            continue
        edges = np.array([rows[0]["from_m"], *(row["to_m"] for row in rows)]) / 1000
        for zone, (first, last) in zones.items():
            lo, hi = edges[first - 1], edges[last]
            ax.axvspan(lo, hi, color="#dce6ea", lw=0, zorder=0)
            if ax is axes[0]:
                ax.text((lo + hi) / 2, 1.055, f"{tuple(zones).index(zone) + 1}", ha="center",
                        va="bottom", fontsize=8, transform=ax.get_xaxis_transform(), color="#2f4656")
        ax.stairs([row["request_kw"] for row in rows], edges, fill=False, baseline=None,
                  lw=1.15, linestyle=(0, (4, 2)), color="#34485a", label="Requested")
        ax.stairs([row["wheel_assist_kw"] for row in rows], edges, fill=True, alpha=.30, lw=.7,
                  color=color, label="Delivered (block mean)")
        label += f"  |  {replay['wheel_assist_j'] / 1000:,.0f} kJ at wheels"
        if not replay["feasible"]:
            label += "  |  infeasible at this grid"
        ax.text(.012, .94, label, transform=ax.transAxes, ha="left", va="top",
                fontsize=9, color="#24384a", bbox=dict(facecolor="white", alpha=.86, edgecolor="none", pad=2))
        ax.set_yticks((0, 60, 120))
        ax.set(ylim=(0, 152), xlim=(0, edges[-1]))
        ax.grid(axis="y", alpha=.22)
        ax.spines[["top", "right"]].set_visible(False)
    figure.legend(*axes[0].get_legend_handles_labels(), loc="outside upper center",
                  ncol=2, frameon=False, fontsize=9)
    figure.supylabel("Wheel-assist power (kW)", fontsize=10)
    axes[-1].set_xlabel("Distance from timing line (km)", fontsize=10)
    save_figure(figure, folder, "03_planner_deployment")


def read_swaps(path):
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    expected = {(case, *pair) for case in CASES for pair in combinations(ZONES, 2)}
    outcomes = {(row["scenario"], row["donor"], row["recipient"]): row for row in rows}
    if len(rows) != len(outcomes) or outcomes.keys() != expected:
        raise ValueError(f"Unexpected zone transfer matrix: {path}")
    if {float(row["packet_kj"]) for row in rows} != {20.0}:
        raise ValueError(f"Expected the fixed 20 kJ packet: {path}")
    for row in rows:
        if row["status"] not in {*REASONS, "resolved"}:
            raise ValueError(f"Unknown packet outcome: {row['status']}")
        if row["status"] == "resolved" and float(row["delta_time_160_ms"]) * float(row["delta_time_320_ms"]) <= 0:
            raise ValueError(f"Resolved transfer lacks a consistent direction: {row}")
    return outcomes


def zone_summary(outcomes):
    for case, zone in product(CASES, ZONES):
        relevant = [row for (c, donor, recipient), row in outcomes.items() if c == case and zone in (donor, recipient)]
        counts = dict(faster=0, slower=0, inconclusive=0)
        for row in relevant:
            status = row["status"]
            if status != "resolved":
                counts["inconclusive"] += 1
                continue
            change = float(row["delta_time_320_ms"])
            recipient_faster = change < 0
            zone_faster = (zone == row["recipient"]) == recipient_faster
            counts["faster" if zone_faster else "slower"] += 1
        yield dict(case=case, zone=zone, zone_label=ZONES[zone], conditional_comparisons=len(relevant), **counts)


def swap_figure(folder, outcomes):
    figure, axes = plt.subplots(2, 2, sharex=True, sharey=True, figsize=(8.6, 7.5), layout="constrained")
    names = list(ZONES)
    magnitudes = [abs(float(row["delta_time_320_ms"])) for row in outcomes.values() if row["status"] == "resolved"]
    limit = max(magnitudes, default=1)
    palette = LinearSegmentedColormap.from_list("packet_time", ["#156678", "#f8fafb", "#a04322"])
    norm = Normalize(-limit, limit)
    for (case, label), ax in zip(CASES.items(), axes.flat):
        values = np.full((len(names), len(names)), np.nan)
        for i, j in combinations(range(len(names)), 2):
            row = outcomes[case, names[i], names[j]]
            status = row["status"]
            if status == "resolved":
                value = float(row["delta_time_320_ms"])
                values[i, j] = value
                ax.text(j, i, f"{value:+.1f}", ha="center", va="center", fontsize=8,
                        color="white" if abs(value) > limit * .65 else "#172c3b")
            else:
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fc="#e7ebef", ec="white", lw=.6))
                ax.text(j, i, REASONS[status][0], ha="center", va="center", fontsize=8, color="#364d61")
        edges = np.arange(len(names) + 1) - .5
        artist = ax.pcolormesh(edges, edges, values, cmap=palette, norm=norm, shading="flat", zorder=0)
        ax.set_aspect("equal")
        ax.set_title(label, loc="left", fontsize=10, fontweight="bold")
        ax.set_xticks(range(1, len(names)), list(ZONES.values())[1:], rotation=35, ha="right", fontsize=8)
        ax.set_yticks(range(len(names) - 1), list(ZONES.values())[:-1], fontsize=8)
        ax.set(xlim=(.5, len(names) - .5), ylim=(len(names) - 1.5, -.5))
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
    figure.supylabel("Donor zone", fontsize=10)
    figure.supxlabel("Recipient zone · 20 kJ transferred", fontsize=10)
    if magnitudes:
        bar = figure.colorbar(artist, ax=axes, shrink=.69, pad=.025, aspect=24)
        bar.set_label("Recipient lap minus donor lap (ms)", fontsize=9)
        bar.solids.set_rasterized(False)
    figure.legend(handles=[Line2D([], [], ls="", label=f"{mark}  {label}") for mark, label in REASONS.values()],
                  loc="outside upper center", ncol=4, frameon=False, fontsize=8, handlelength=0, handletextpad=0)
    save_figure(figure, folder, "02_zone_transfers")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--planner", type=Path, default=PLANNER)
    parser.add_argument("--swaps", type=Path, default=SWAPS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--figures", type=Path, default=FIGURES)
    args = parser.parse_args()
    if args.output.exists() or args.figures.exists():
        raise FileExistsError("Choose new output and figure directories")
    inputs = {}
    planner_check = signed_files(args.planner / "manifest.json", inputs)
    swap_check = signed_files(args.swaps / "manifest.json", inputs)
    planner_check(PROTOCOL)
    swap_check(PROTOCOL)
    replays, profiles, comparisons = planner_inputs(args.planner, planner_check)
    outcomes = read_swaps(swap_check(args.swaps / "pairs.csv"))
    zone_rows = read(swap_check(args.swaps / "zones.json"))
    zones = {row["id"]: (row["first_block"], row["last_block"]) for row in zone_rows}
    if list(zones) != list(ZONES):
        raise ValueError("The zone IDs or circuit order differ from the fixed packet-transfer matrix")
    zoning = list(spatial_tables(profiles, replays, zones))
    args.output.mkdir(parents=True)
    args.figures.mkdir(parents=True)
    save_csv(args.output / "raw_replays.csv", list(replay_rows(replays)))
    save_csv(args.output / "matched_timing.csv", comparisons)
    save_csv(args.output / "zone_work_and_power.csv", zoning)
    save_csv(args.output / "conditional_zone_outcomes.csv", list(zone_summary(outcomes)))
    plt.rcParams["pdf.fonttype"] = 42
    matched_figure(args.figures, replays, comparisons)
    swap_figure(args.figures, outcomes)
    deployment_figure(args.figures, profiles, replays, zones)
    captions = {
        "01_matched_timing": (
            "Unmatched feasibility appears at left in coarse-to-fine order within each schedule. "
            "The time difference is spread minus the named schedule at the same delivered wheel work, so "
            "positive values favor the named schedule. Paired values appear only after feasibility, "
            "work matching and numerical refinement pass. Open circles and filled diamonds show the two "
            "deterministic integration grids. The horizontal separation shows grid sensitivity. Wheel work "
            "at right is the matched total at 320 cells per block. Nominal frozen and scenario-planner rows "
            "reuse the same archived schedule. Fixed-finish comparisons scale the earlier requests and use "
            "full request in the last three blocks of both schedules."
        ),
        "02_zone_transfers": (
            "Each cell compares allocating a 20 kJ wheel-work packet to the recipient (column) with placing it "
            "at the donor (row), under the same scenario and work target. Negative values favor the recipient. "
            "Numbers give the 320-cell difference where both grids resolve its sign. The codes retain every "
            "inconclusive and failed comparison. Each pair applies to its own baseline and work target. "
            "The table of conditional outcomes counts faster, slower and inconclusive comparisons per zone."
        ),
        "03_planner_deployment": (
            "Requested and delivered wheel-assist power for each scenario-specific finite-search schedule at "
            "320 cells per block. Delivered power is work divided by the full action-block duration. Shading "
            "marks the seven predeclared packet-test zones in lap order. The accompanying table gives exact "
            "distances and work for each schedule at both grids."
        ),
    }
    caption_text = ["# Bahrain energy-scarcity figures",
                    f"Source runs {args.planner.as_posix()} and {args.swaps.as_posix()}.",
                    "All results describe simulated laps on the frozen Bahrain model."]
    for name, caption in captions.items():
        caption_text += [f"## {name.replace('_', ' ')}", caption]
    caption_text.append("Zone labels in order are " + ", ".join(ZONES.values()) + ".")
    (args.figures / "captions.md").write_text("\n\n".join(caption_text) + "\n", encoding="utf-8")
    sources = ["report_bahrain_energy_scarcity.py", "benchmark_circuit_control.py",
               "map_bahrain_deployment.py", "report_bahrain_finish_constraint.py", "verify_bahrain_deployment.py"]
    source_hashes = {path.as_posix(): sha(path) for path in (Path("scripts") / name for name in sources)}
    outputs = {path.as_posix(): sha(path) for folder in (args.output, args.figures) for path in sorted(folder.iterdir())}
    save(args.output / "manifest.json", dict(inputs=inputs, sources=source_hashes, outputs=outputs, captions=captions))


if __name__ == "__main__":
    main()
