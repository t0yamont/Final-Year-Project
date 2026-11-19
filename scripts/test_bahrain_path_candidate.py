"""Replay one geometry-only change using the cached development lap as a path."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bahrain_pace_model import free_lap
from benchmark_circuit_control import save, sha
from calibrate_bahrain_pace import PLOT_FRACTION, assess, load_lap, read


def lap_path(positions, lap):
    times = (pd.to_datetime(positions.date) - pd.Timestamp(lap["date_start"])).dt.total_seconds().to_numpy()
    duration = lap["duration_s"]
    nearby = (times >= -2) & (times <= duration + 2)
    times = times[nearby]
    xy = positions.loc[nearby, ["x", "y"]].to_numpy(dtype=float) * 0.1
    if times[0] > 0 or times[-1] < duration or np.any(np.diff(times) <= 0):
        raise ValueError("Position samples must bracket the lap in chronological order")
    endpoints = np.column_stack([np.interp([0, duration], times, axis) for axis in xy.T])
    path = np.vstack([endpoints.mean(axis=0), xy[(times > 0) & (times < duration)]])
    path = path[np.r_[True, np.linalg.norm(np.diff(path, axis=0), axis=1) > 1e-9]]
    if np.linalg.norm(path[0] - path[-1]) < 1e-9:
        path = path[:-1]
    return path, float(np.linalg.norm(endpoints[0] - endpoints[1]))


def main():
    out = Path("results/bahrain-path-candidate-001")
    figures = Path("figures/dissertation/bahrain-path-candidate-v1")
    source = Path("results/bahrain-pace-inputs-001")
    baseline = Path("results/bahrain-pace-calibration-001")
    protocol = Path("configs/bahrain_driver_transfer_protocol.json")
    locked = read(protocol)
    reference = baseline / "model.json"
    if sha(reference) != locked["inputs"][reference.as_posix()]:
        raise ValueError("Reference model has changed")
    acquisition = Path("results/openf1-dataset-003/development/1257/10010")
    positions = acquisition / "driver-1-position.csv.gz"
    metadata = read(source / "metrics.json")
    if sha(positions) != metadata["provenance"]["acquisition_output_sha256"][positions.name]:
        raise ValueError("Development positions differ from the acquisition record")
    path, closure = lap_path(pd.read_csv(positions), metadata["laps"]["13"])
    out.mkdir(exist_ok=False)
    figures.mkdir(exist_ok=False)
    geometry = out / "driver1_lap13_xy_m.csv"
    np.savetxt(geometry, path, delimiter=",", fmt="%.9f")
    model = dict(read(reference), geometry=geometry.as_posix(), geometry_sha256=sha(geometry), line_offset_fraction=0.)
    save(out / "model.json", model)
    action = read("configs/bahrain_pace_protocol.json")["reference_action"]
    primary = free_lap(model, 160, action)
    refined = free_lap(model, 320, action)
    length = float(primary[-1, 0])
    grid_error = float(abs(primary[-1, 1] - refined[-1, 1]))
    fraction = primary[:, 0] / length
    speed = np.interp(PLOT_FRACTION, fraction, primary[:, 2])
    elapsed = np.interp(PLOT_FRACTION, fraction, primary[:, 1])
    profile = out / "speed_time.csv"
    with profile.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["fraction", "distance_m", "calibrated_speed_mps", "calibrated_time_s"])
        writer.writerows(zip(PLOT_FRACTION, PLOT_FRACTION * length, speed, elapsed))
    inputs = [protocol, reference, positions, source / "metrics.json", baseline / "speed_time.csv",
              baseline / "metrics.json", Path("configs/bahrain_pace_protocol.json")]
    provenance = {p.as_posix(): sha(p) for p in inputs}
    original = read(baseline / "metrics.json")
    save(out / "locked_predictions.json", dict(
        inputs=provenance | {p.as_posix(): sha(p) for p in (profile, out / "model.json", geometry)},
        current=dict(profile=(baseline / "speed_time.csv").as_posix(), model=reference.as_posix(), grid_error_s=original["grid_error_s"]),
        candidate=dict(profile=profile.as_posix(), model=(out / "model.json").as_posix(), grid_error_s=grid_error)))
    gates = locked["gates"]
    finish_error = float(primary[-1, 2] - model["initial_speed_mps"])
    results = {}
    old = np.genfromtxt(baseline / "speed_time.csv", delimiter=",", names=True)
    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(9, 5.2))
    for lap_id in ["13", "4", "10"]:
        lap = load_lap(source, lap_id, metadata)
        provenance[(source / f"lap-{lap_id}.csv").as_posix()] = metadata["laps"][lap_id]["csv_sha256"]
        score = assess(lap, metadata["laps"][lap_id], speed, elapsed, metadata["sector_boundary_fractions"])
        checks = dict(lap=abs(score["lap_error_s"]) <= gates["absolute_lap_error_s"],
                      sectors=max(map(abs, score["sector_error_s"])) <= gates["absolute_each_sector_error_s"],
                      speed=score["speed_rmse_mps"] <= gates["speed_rmse_mps"], grid=grid_error <= gates["absolute_grid_time_change_s"],
                      finish=abs(finish_error) <= gates["absolute_finish_speed_error_mps"])
        results[lap_id] = dict(lap_error_s=score["lap_error_s"], sector_error_s=score["sector_error_s"],
                               speed_rmse_mps=score["speed_rmse_mps"], checks=checks)
        if lap_id == "13":
            continue
        ax = axes[["4", "10"].index(lap_id)]
        observed = np.interp(PLOT_FRACTION, lap["fraction"], lap["speed_mps"])
        ax.plot(100 * PLOT_FRACTION, old["calibrated_speed_mps"] - observed, label="Circuit centreline", color="#346984")
        ax.plot(100 * PLOT_FRACTION, speed - observed, label="Lap 13 position path", color="#ae5b27")
        ax.axhline(0, lw=.6, color="#444")
        ax.set(ylabel="Speed error (m/s)", title=f"Qualifying lap {lap_id}")
        ax.grid(axis="y", alpha=.2)
    axes[0].legend(fontsize=8, ncol=2)
    axes[-1].set_xlabel("Progress from timing line (% of lap distance)")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(figures / f"path_comparison.{ext}", dpi=300)
    plt.close(fig)
    save(out / "metrics.json", dict(length_m=length, vertices=len(path), endpoint_separation_m=closure,
         primary_lap_s=float(primary[-1, 1]), refined_lap_s=float(refined[-1, 1]), grid_error_s=grid_error,
         finish_error_mps=finish_error, laps=results))
    sources = [Path(__file__), Path("scripts/bahrain_pace_model.py"), Path("scripts/calibrate_bahrain_pace.py")]
    save(out / "manifest.json", dict(inputs=provenance, sources={str(p): sha(p) for p in sources},
         outputs={str(p): sha(p) for folder in (out, figures) for p in folder.iterdir()}))
    print((out / "metrics.json").read_text())


if __name__ == "__main__":
    main()
