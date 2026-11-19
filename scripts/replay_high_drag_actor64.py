"""Retest the previously observed PPO finish-speed failure at 1.1 kg/m drag."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
from stable_baselines3 import PPO

from benchmark_circuit_control import gzsave, make_env, save, sha
from evaluate_ppo_actor_width import verify_manifest
from f1energy.circuit_control import rollout
from report_regeneration_robustness import audit, read
from run_regeneration_robustness import scenario_setup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/ppo-actor64-high-drag-001"))
    parser.add_argument("--figures", type=Path, default=Path("figures/dissertation/ppo-actor64-high-drag-v1"))
    args = parser.parse_args()
    torch.set_num_threads(1)
    original = Path("results/regeneration-robustness-001")
    wide = Path("results/regeneration-ppo-actor64-001")
    inputs = {}
    for run in (original, wide):
        verify_manifest(run)
        inputs[str(run/"manifest.json")] = sha(run/"manifest.json")
    scenario = next(s for s in read(original/"contract.json")["protocol"]["scenarios"] if s["name"] == "high_drag")
    config, reference, curve, vehicle = scenario_setup(read(wide/"seed-0/contract.json")["config"], scenario)
    if read(original/"high_drag/setup.json") != dict(config=config, reference=reference):
        raise ValueError("Mismatch with the published high-drag replay")
    args.output.mkdir(parents=True, exist_ok=False)
    args.figures.mkdir(parents=True, exist_ok=False)
    save(args.output/"contract.json", dict(inputs=inputs, scenario=scenario, seeds=[0,1,2], grids=[160,320],
         question="Secondary diagnostic using the known historical 1.1 kg/m failure. Report finish success before elapsed time on both grids for every final policy. No retraining or selection."))
    rows = []
    for seed in range(3):
        model = PPO.load(wide/f"seed-{seed}/checkpoint_16384.zip", device="cuda:0")
        if next(model.policy.parameters()).device.type != "cuda":
            raise ValueError("CUDA policy required")
        for cells in (160, 320):
            env = make_env(config, reference, curve, vehicle, cells)
            result = rollout(env, lambda obs: model.predict(obs, deterministic=True)[0])
            wide_path = args.output/f"seed-{seed}_{cells}.json.gz"
            gzsave(wide_path, result)
            for width, path in ((32, original/f"high_drag/ppo_seed{seed}_{cells}.json.gz"), (64, wide_path)):
                saved = read(path)
                audit(saved, config, reference)
                rows.append(dict(width=width, seed=seed, cells=cells, file=str(path),
                                 duration_s=saved["duration_s"], feasible=saved["feasible"],
                                 terminal_speed_error_mps=saved["terminal_speed_error_mps"]))
    save(args.output/"metrics.json", dict(rows=rows, finish_target_mps=config["initial_speed_mps"]))
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for i, (width, cells) in enumerate([(32,160),(32,320),(64,160),(64,320)]):
        subset = [r for r in rows if r["width"] == width and r["cells"] == cells]
        ax.scatter([r["seed"]+(i-1.5)*.12 for r in subset], [r["terminal_speed_error_mps"] for r in subset],
                   marker="o" if width == 32 else "s", color="#116b83" if cells == 160 else "#a45412",
                   label=f"Width {width}, {55*cells:,} cells")
    ax.axhline(0, color="black", lw=.8)
    ax.set(xlabel="Training seed", ylabel="Finish speed minus target (m/s)", xticks=[0,1,2],
           title="Finish-speed error at 10% higher drag")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(.5,-.21), ncol=2)
    fig.tight_layout()
    for extension in ("png","pdf"):
        fig.savefig(args.figures/f"finish_speed.{extension}", dpi=300)
    plt.close(fig)
    sources = {str(p):sha(p) for p in [Path(__file__), Path("scripts/evaluate_ppo_actor_width.py"),
               Path("scripts/run_regeneration_robustness.py"), Path("scripts/report_regeneration_robustness.py")]}
    save(args.output/"manifest.json", dict(inputs=inputs,sources=sources,
         outputs={str(p):sha(p) for folder in (args.output,args.figures) for p in folder.iterdir() if p.is_file()}))
    print([(w, sum(r["feasible"] for r in rows if r["width"] == w)) for w in (32,64)])


if __name__ == "__main__":
    main()
