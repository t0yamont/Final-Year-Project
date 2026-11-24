"""Diagnose a failed circuit transfer gate using a controller-independent speed bound."""
import argparse
from pathlib import Path

import numpy as np

from bahrain_pace_model import build_env
from benchmark_circuit_control import plt, save, sha, sources
from verify_bahrain_deployment import read


def finish_bound(env):
    # At a node the speed is at most its braking envelope. Since all braking and
    # drag forces oppose motion, d(v^3)/ds <= 3 * maximum wheel power / mass.
    # Grant full power with unlimited battery from each interior node to the line.
    end_distance = env.grid.distance_m[-1]
    remaining = end_distance - env.grid.distance_m[:-1]
    power = env.vehicle.base_power_w + env.vehicle.electrical_limit_w
    upper = np.cbrt(env.envelope[:-1] ** 3 + 3 * power * remaining / env.vehicle.mass_kg)
    tightest = int(np.argmin(upper))
    return remaining, upper, dict(cells=env.cells_per_block,
        station_m=float(env.grid.distance_m[tightest]), remaining_m=float(remaining[tightest]),
        speed_envelope_mps=float(env.envelope[tightest]), upper_bound_mps=float(upper[tightest]),
        required_mps=env.initial_speed, target_impossible=bool(upper[tightest] < env.initial_speed - 1e-5))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--figures", type=Path, required=True)
    args = parser.parse_args()
    protocol = Path("configs/circuit_policy_transfer.json")
    p = read(protocol)
    geom, screen = (Path(p[k]) for k in ("model_directory", "screen_directory"))
    inputs = {str(protocol): sha(protocol)}

    def artifact(folder, name):
        manifest = folder / "manifest.json"
        path = folder / name
        digest = {Path(k): v for k, v in read(manifest)["outputs"].items()}[path]
        if sha(path) != digest:
            raise ValueError(f"Unverified source: {path}")
        inputs[str(manifest)] = sha(manifest)
        inputs[str(path)] = digest
        return read(path)

    geometry = artifact(geom, "metrics.json")
    selection = artifact(screen, "selection.json")
    if geometry["geometry_passed"] or selection["selected_circuit"] != geometry["circuit"]:
        raise ValueError("This diagnostic requires a failed geometry gate on the selected circuit")
    model = artifact(geom, "model.json")
    bahrain = Path("results/bahrain-pace-calibration-001")
    reference = artifact(bahrain, "model.json")
    benchmarks = Path("results/bahrain-deployment-zones-001")
    for m in (reference, model):
        inputs[m["geometry"]] = m["geometry_sha256"]
    results = dict(circuit=geometry["circuit"], geometry_checks=geometry["geometry_checks"],
                   geometry_passed=False, pace_passed=geometry["pace_passed"],
                   controller_scores=[], bounds=[], positive_controls=[])
    fig, ax = plt.subplots(figsize=(7.5, 4.2), layout="constrained")
    for g in p["cells_per_block"]:
        env = build_env(model, g)
        distances, bounds, row = finish_bound(env)
        results["bounds"].append(row)
        points = distances <= 350
        ax.plot(distances[points], bounds[points], "-" if g == 160 else "--",
                label=f"{g} cells per block", lw=2 if g == 160 else 1.2)
        ax.plot(row["remaining_m"], row["upper_bound_mps"], "o", color="#252525", ms=4)
        ref_env = build_env(reference, g)
        _, _, positive = finish_bound(ref_env)
        archive = benchmarks / "central" / f"selected_{g}.json.gz"
        expected = {Path(k): v for k, v in read(benchmarks / "manifest.json")["outputs"].items()}
        inputs[str(benchmarks / "manifest.json")] = sha(benchmarks / "manifest.json")
        inputs[str(archive)] = expected[archive]
        lap = read(archive)
        actual = reference["initial_speed_mps"] + lap["terminal_speed_error_mps"]
        if not lap["feasible"] or actual > positive["upper_bound_mps"] + 1e-5:
            raise ValueError("Bound contradicts an achieved Bahrain finish")
        results["positive_controls"].append(dict(**positive, archived_finish_mps=actual))
    ax.axhline(model["initial_speed_mps"], color="#ad4028", ls=":", label="Required finish speed")
    ax.set(xlabel="Distance remaining to the timing line (m)", ylabel="Upper bound on finish speed (m/s)",
           title=f"{geometry['circuit']}  |  Can the car reach the required finish speed?")
    ax.invert_xaxis()
    ax.legend(fontsize=9)
    ax.grid(alpha=.2)
    for folder in (args.output, args.figures):
        folder.mkdir(parents=True, exist_ok=False)
    for ext in ("png", "pdf"):
        fig.savefig(args.figures / f"01_finish_speed_bound.{ext}", dpi=300)
    plt.close(fig)
    save(args.output / "metrics.json", results)
    code = sources()
    for path in ("scripts/evaluate_circuit_policy_transfer.py", "scripts/bahrain_pace_model.py",
                 "scripts/benchmark_circuit_control.py", "scripts/verify_bahrain_deployment.py"):
        code[path] = sha(path)
    if any(sha(path) != digest for path, digest in inputs.items()):
        raise ValueError("Bound input hash mismatch")
    save(args.output / "manifest.json", dict(inputs=inputs, sources=code,
         outputs={str(f): sha(f) for d in (args.output, args.figures) for f in d.iterdir()}))
    print(results["bounds"], flush=True)


if __name__ == "__main__":
    main()
