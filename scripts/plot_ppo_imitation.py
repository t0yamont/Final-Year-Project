"""Compare closed-loop outcomes from the two training methods and their teaching planner."""
import argparse
from pathlib import Path
from statistics import mean

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from benchmark_circuit_control import save, sha
from evaluate_ppo_actor_width import verify_manifest
from report_regeneration_robustness import read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("figures/dissertation/ppo-imitation-comparison-v1"))
    args = parser.parse_args()
    ppo = Path("figures/dissertation/ppo-actor-width-v1")
    stress = Path("results/ppo-actor64-high-drag-001")
    imitation = Path("results/regeneration-imitation-pilot-001")
    expert = Path("results/regeneration-robustness-001")
    inputs = {}
    for folder in [ppo, stress, imitation, expert]:
        verify_manifest(folder)
        inputs[str(folder / "manifest.json")] = sha(folder / "manifest.json")
    ppo_rows = read(ppo / "verification.json")["rows"]
    ppo_rows.extend(dict(r, scenario="high_drag") for r in read(stress/"metrics.json")["rows"])
    groups = {"PPO": ppo_rows, "Imitation": read(imitation / "metrics.json")["rows"]}
    titles = {"nominal":"Nominal", "energy_1p5MJ":"1.5 MJ starting energy",
              "drag_1p05":"5% higher drag", "high_drag":"10% higher drag"}
    summary = []
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7))
    for ax, (scenario, title) in zip(axes.flat, titles.items()):
        labels = []
        for method, rows in groups.items():
            for width in [32, 64]:
                rr = sorted((r for r in rows if r["cells"] == 160 and r["width"] == width and r["scenario"] == scenario), key=lambda r:r["seed"])
                if [r["seed"] for r in rr] != [0, 1, 2]:
                    raise ValueError(f"Incomplete seed set for {scenario}/{method}/{width}")
                feasible = [r for r in rr if r["feasible"]]
                index = len(labels)
                labels.append(f"{method} {width}\n{len(feasible)}/3 feasible")
                for r in feasible:
                    ax.scatter(index+(r["seed"]-1)*.075, r["duration_s"], color="#116b83" if method == "PPO" else "#9f510d", s=32)
                summary.append(dict(scenario=scenario, method=method, width=width, feasible=len(feasible), attempted=3,
                                    # Present an all-seed mean only when the whole group qualified.
                                    mean_all_seeds_s=mean(r["duration_s"] for r in rr) if len(feasible)==3 else None))
        if scenario in ("nominal", "high_drag"):
            reference = read(expert/scenario/"replanned_dp_160.json.gz")
            if reference["feasible"]:
                ax.axhline(reference["duration_s"], color="#555555", ls="--", lw=1, label="Model-aware DP")
                ax.legend(fontsize=8, loc="best")
        ax.set(xticks=range(4), xticklabels=labels, xlim=(-.4,3.4), title=title, ylabel="Feasible lap time (s)")
        ax.tick_params(axis="x", labelsize=8)
        ax.ticklabel_format(axis="y", useOffset=False)
        ax.grid(axis="y", alpha=.2)
    fig.suptitle("Regenerative Sakhir deployment policies on the primary grid")
    fig.text(.5,.015,"Points are feasible final policies. PPO trained on nominal laps. Imitation learned from four model-aware DP schedules.",ha="center",fontsize=9)
    fig.tight_layout(rect=(0,.045,1,.96))
    args.output.mkdir(parents=True, exist_ok=False)
    for extension in ("png","pdf"):
        fig.savefig(args.output/f"learned_controllers.{extension}",dpi=300)
    plt.close(fig)
    save(args.output/"summary.json", summary)
    save(args.output/"manifest.json", dict(inputs=inputs, sources={str(Path(__file__)):sha(__file__)},
         outputs={str(p):sha(p) for p in args.output.iterdir() if p.is_file()}))


if __name__ == "__main__":
    main()
