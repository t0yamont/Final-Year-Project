"""Compare final PPO and SAC checkpoints after physical replay on two resolutions."""
import argparse
import csv
from pathlib import Path
from statistics import mean

import numpy as np

from benchmark_circuit_control import plt, save, sha
from train_bahrain_algorithm_width import numerical
from verify_bahrain_deployment import close, read, verify_rollout


PROTOCOL = Path("configs/circuit_policy_transfer.json")
COLORS = {"PPO 64": "#005f82", "SAC 64": "#bf531b", "PPO 256": "#008672", "SAC 256": "#864595"}


def figures(folder, circuit, rows, profiles, groups):
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 7.5), layout="constrained")
    for group, names in groups.items():
        color = COLORS[group]
        ix = list(groups).index(group)
        for seed, name in enumerate(names):
            x = ix + (seed - 1) * .19
            for cells, dx, marker in ((160, -.025, "o"), (320, .025, "+")):
                row = rows[name, cells]
                axes[0, 0].plot(x + dx, row["terminal_speed_error_mps"], marker,
                                color=color, fillstyle="none", ms=6)
                if row["feasible"] and rows["spread", cells]["feasible"]:
                    axes[0, 1].plot(x + dx, rows["spread", cells]["duration_s"] - row["duration_s"],
                                    marker, color=color, fillstyle="none", ms=6)
            p = profiles[name]
            station = [0., *[v["to_m"] / 1000 for v in p]]
            style = ("-", "--", ":")[seed]
            axes[1, 0].plot(station, np.r_[0, np.cumsum([v["wheel_kj"] for v in p])] / 1000,
                            color=color, ls=style, lw=1.3)
            axes[1, 1].plot(station, [p[0]["start_charge_mj"], *[v["charge_mj"] for v in p]],
                            color=color, ls=style, lw=1.3)
    for axis in axes[0]:
        axis.set_xticks(range(len(groups)), list(groups))
        axis.set_xlim(-.5, len(groups) - .5)
        axis.axhline(0, color="#444444", ls=":", lw=.8)
    axes[0, 0].set(title="Finish-speed constraint", ylabel="Achieved minus target (m/s)")
    axes[0, 1].set(title="Feasible laps against adaptive spread", ylabel="Time saved (s)")
    if len(axes[0, 1].lines) == 1:
        axes[0, 1].text(.5, .55, "No feasible pairs", ha="center", transform=axes[0, 1].transAxes)
    for policy, line in [("selected", "-."), ("spread", "--")]:
        p = profiles[policy]
        station = [0., *[v["to_m"] / 1000 for v in p]]
        axes[1, 0].plot(station, np.r_[0, np.cumsum([v["wheel_kj"] for v in p])] / 1000,
                        line, color="#202020", lw=1.25, label=policy.capitalize())
        axes[1, 1].plot(station, [p[0]["start_charge_mj"], *[v["charge_mj"] for v in p]],
                        line, color="#202020", lw=1.25)
    axes[1, 0].set(xlabel="Distance from timing line (km)", ylabel="Cumulative wheel assist (MJ)",
                   title="Where electrical energy was deployed")
    axes[1, 0].legend(fontsize=8)
    axes[1, 1].set(xlabel="Distance from timing line (km)", ylabel="Battery energy (MJ)",
                   title="Stored energy along the lap")
    for ax in axes.flat:
        ax.grid(alpha=.2)
    fig.suptitle(f"{circuit}  |  Final PPO and SAC policies\n"
                 "Top: seeds 0–2 from left to right in each group, circles at 160 cells and crosses at 320.  "
                 "Bottom: 160 cells per block.", fontsize=12)
    for ext in ("pdf", "png"):
        fig.savefig(folder / f"01_controller_comparison.{ext}", dpi=300)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--circuit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--figures", type=Path, required=True)
    args = parser.parse_args()
    protocol, model = read(PROTOCOL), read(args.model)
    limits = protocol["refinement"]
    manifest_path = args.run / "manifest.json"
    manifest = read(manifest_path)
    expected = {Path(p): h for p, h in manifest["outputs"].items()}
    signed_inputs = {Path(p): h for p, h in manifest["inputs"].items()}
    metrics_path = args.run / "metrics.json"
    records = read(metrics_path)["rows"]
    inputs = {str(p): sha(p) for p in (manifest_path, metrics_path, args.model, PROTOCOL)}
    if inputs[str(metrics_path)] != expected[metrics_path]:
        raise ValueError("Metrics hash differs from run manifest")
    if inputs[str(args.model)] != (expected | signed_inputs).get(args.model):
        raise ValueError("Model hash differs from run manifest")
    rows = {(r["policy"], r["cells"]): r for r in records}
    groups = {f"{method} {width}": [f"{method} {width} seed {s}" for s in protocol["seeds"]]
              for width in protocol["actor_widths"] for method in protocol["methods"]}
    names = ["spread", "selected",
             *(n for group in groups.values() for n in group)]
    if len(rows) != len(records) or set(rows) != {(n, g) for n in names for g in (160, 320)}:
        raise ValueError("Unexpected policy or grid coverage")
    profiles = {}
    for name in names:
        for cells in (160, 320):
            row = rows[name, cells]
            file = Path(row["file"])
            digest = sha(file)
            # Some baseline traces are bound in the producer's input manifest.
            signed = expected.get(file) or signed_inputs.get(file)
            if digest != signed:
                raise ValueError(f"Unsigned trace: {file}")
            inputs[str(file)] = digest
            blocks = verify_rollout(row, model)
            if cells == 160:
                profiles[name] = []
                capacity = model["regeneration"]["capacity_j"]
                previous_m, energy = 0., model["initial_energy_j"]
                for i, b in enumerate(blocks, 1):
                    end = b["state"]["distance_m"]
                    close(b["state"]["energy_j"], energy - b["battery_discharged_j"] + b["battery_recovered_j"], .01)
                    profiles[name].append(dict(policy=name, block=i, feasible=row["feasible"], from_m=previous_m,
                        to_m=end, requested_kw=b["action"] * model["vehicle"]["electrical_limit_w"] / 1000,
                        delivered_kw=b["electrical_work_j"] / b["duration_s"] / 1000, wheel_kj=b["electrical_work_j"] / 1000,
                        recovered_kj=b["battery_recovered_j"] / 1000, start_charge_mj=energy / 1e6,
                        start_headroom_mj=(capacity - energy) / 1e6, charge_mj=b["state"]["energy_j"] / 1e6))
                    previous_m, energy = end, b["state"]["energy_j"]

    checks, paired = numerical(records, dict(primary_cells_per_block=160, refined_cells_per_block=320,
        refinement=limits, baselines=["selected", "spread"], seeds=protocol["seeds"], widths=protocol["actor_widths"]))
    summary = {}
    for group, members in groups.items():
        times = [rows[n, 160]["duration_s"] for n in members if rows[n, 160]["feasible"]]
        summary[group] = dict(feasible_160=len(times), feasible_320=sum(rows[n, 320]["feasible"] for n in members),
            feasible_both=sum(checks[n]["both_feasible"] for n in members),
            refined_feasible=sum(checks[n]["passes_refinement"] for n in members),
            primary_feasible_mean_s=mean(times) if times else None, primary_feasible_times_s=times)
    for path in (args.output, args.figures):
        path.mkdir(parents=True, exist_ok=False)
    save(args.output / "comparison.json", dict(circuit=args.circuit, summary=summary, individual=checks, pairs=paired))
    with (args.output / "distance_profiles.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=profiles["spread"][0])
        writer.writeheader()
        for items in profiles.values():
            writer.writerows(items)
    figures(args.figures, args.circuit, rows, profiles, groups)
    code = {p: sha(p) for p in (str(Path(__file__).relative_to(Path.cwd())), "scripts/verify_bahrain_deployment.py",
                                "scripts/validate_regeneration.py", "scripts/benchmark_circuit_control.py",
                                "scripts/train_bahrain_algorithm_width.py")}
    save(args.output / "manifest.json", dict(inputs=inputs, sources=code,
         outputs={str(p): sha(p) for folder in (args.output, args.figures) for p in folder.iterdir()}))
    for group, values in summary.items():
        print(group, values, flush=True)


if __name__ == "__main__":
    main()
