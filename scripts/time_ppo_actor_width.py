"""Measure both PPO actor widths on the same 55 observations from one saved lap."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
from stable_baselines3 import PPO

from benchmark_circuit_control import load_setup, make_env, save, sha
from time_regeneration_controls import measure
from verify_circuit_multiseed import replay


def read(path):
    return json.loads(path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/ppo-actor-width-cost-001"))
    parser.add_argument("--figures", type=Path, default=Path("figures/dissertation/ppo-actor-width-cost-v1"))
    args = parser.parse_args()
    torch.set_num_threads(1)
    runs = [Path("results/regeneration-multiseed-001"), Path("results/regeneration-ppo-actor64-001")]
    inputs = {}
    for run in runs:
        manifest = run / "manifest.json"
        for section in read(manifest).values():
            for path, digest in section.items():
                if sha(path) != digest:
                    raise ValueError(f"Changed PPO study input: {path}")
        inputs[str(manifest)] = sha(manifest)
    config = read(runs[0] / "seed-0/contract.json")["config"]
    ref, curve, vehicle = load_setup(config)
    env = make_env(config, ref, curve, vehicle, config["fine_cells_per_block"])
    trace = replay(runs[0] / "seed-0/checkpoint_16384_deterministic_fine.json.gz")["trace"]
    obs, _ = env.reset()
    observations = []
    for block in trace:
        observations.append(obs)
        obs, _, _, _, _ = env.step([block["action"]])

    rows = []
    for seed in range(3):
        # Alternate order across seeds to reduce systematic warm-up/order effects.
        for run in runs[::1 if seed % 2 == 0 else -1]:
            folder = run / f"seed-{seed}"
            model = PPO.load(folder / "checkpoint_16384.zip", device="cuda:0")
            actor = model.policy.mlp_extractor.policy_net
            width = actor[0].out_features
            weights = [*actor.parameters(), *model.policy.action_net.parameters()]
            if any(p.device.type != "cuda" for p in weights):
                raise ValueError("Timing requires a CUDA policy")
            def predict():
                return [float(model.predict(o, deterministic=True)[0][0]) for o in observations]
            if seed == 0 and run == runs[0] and predict() != [b["action"] for b in trace]:
                raise ValueError("Reference observations do not reproduce saved actions")
            metrics = read(folder / "metrics.json")
            checks = [c["gpu_training"] for c in metrics["checkpoints"] if c["gpu_training"]]
            if not checks or not all(c["passed"] for c in checks):
                raise ValueError("Missing CUDA training evidence")
            rows.append(dict(width=width, seed=seed, actor_parameters=sum(p.numel() for p in weights),
                             actor_weight_bytes=sum(p.numel()*p.element_size() for p in weights),
                             training_s=metrics["training_seconds"],
                             peak_torch_allocated_bytes=max(c["peak_allocated_bytes"] for c in checks),
                             warm_ms_per_55_actions=measure(predict)))
    args.output.mkdir(parents=True, exist_ok=False)
    args.figures.mkdir(parents=True, exist_ok=False)
    save(args.output / "metrics.json", dict(rows=rows, gpu=torch.cuda.get_device_name(),
         method="Three warm-ups and median of 21 synchronized batch-one repetitions. All policies receive the original seed-0 nominal fine-grid observations. Wall times exclude environment integration, model loading and observation construction. Peak allocated bytes are per training worker and exclude driver/context reservations."))
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.7))
    for ax, key, ylabel in zip(axes, ["warm_ms_per_55_actions", "training_s"],
                              ["55 sequential decisions (ms)", "Training per seed (s)"]):
        for seed, color in enumerate(["#116b83", "#9f510d", "#724f86"]):
            rr = sorted((r for r in rows if r["seed"] == seed), key=lambda r: r["width"])
            ax.plot([0, 1], [r[key] for r in rr], "o-", color=color, label=f"Seed {seed}")
        ax.set(xticks=[0, 1], xticklabels=["32 × 32", "64 × 64"], ylabel=ylabel, xlabel="Actor hidden layers", xlim=(-.15, 1.15))
        ax.grid(axis="y", alpha=.25)
    axes[0].legend(fontsize=8)
    fig.suptitle("PPO execution costs on the local GPU")
    fig.tight_layout()
    for extension in ("png", "pdf"):
        fig.savefig(args.figures / f"actor_width_cost.{extension}", dpi=300)
    plt.close(fig)
    sources = {str(p): sha(p) for p in [Path(__file__), Path("scripts/time_regeneration_controls.py")]}
    save(args.output / "manifest.json", dict(inputs=inputs, sources=sources,
         outputs={str(p): sha(p) for folder in (args.output, args.figures) for p in folder.iterdir() if p.is_file()}))
    print(json.dumps(rows))


if __name__ == "__main__":
    main()
