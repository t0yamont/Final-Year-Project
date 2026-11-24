"""Register Silverstone independently of telemetry, then audit the frozen Bahrain transfer."""
import argparse
from pathlib import Path
from shutil import copyfile
from urllib.parse import parse_qsl, urlsplit

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import least_squares
from scipy.signal import find_peaks

from acquire_openf1_dataset import digest, save_json, verify_outputs
from bahrain_pace_model import build_env
from f1energy.circuit_control import baseline_policy, rollout
from f1energy.openf1 import OpenF1Client
from prepare_bahrain_pace import arc_length, load, prepare_lap, timing_alignment


CONFIG = Path("configs/transfer_circuit_geometry.json")


def check(path, expected):
    if digest(path) != expected:
        raise ValueError(f"Changed source: {path}")


def projected(points, closed, arc):
    """Project points onto the nearest full polyline segment."""
    delta = np.diff(closed, axis=0)
    dx = points[:, None] - closed[:-1]
    weights = ((dx * delta).sum(axis=2) / np.sum(delta**2, axis=1)).clip(0, 1)
    residual = dx - weights[..., None] * delta
    idx = np.argmin(np.sum(residual**2, axis=2), axis=1)
    rows = np.arange(len(points))
    return arc[idx] + weights[rows, idx] * np.diff(arc)[idx], residual[rows, idx]


def map_registration(config, xy):
    source = config["fia_map"]
    points = np.asarray(source["registration_pixels"])
    closed = np.vstack([xy, xy[0]])
    arc = arc_length(closed)
    length = arc[-1]

    def project(pixels, state):
        # The official map is north-up; screen y increases southward.
        centered = (np.asarray(pixels) - [349, 955]) * [1, -1]
        scale, angle, x, y = state
        c, s = np.cos(angle), np.sin(angle)
        transformed = scale * centered @ [[c, s], [-s, c]] + [x, y]
        return projected(transformed, closed, arc)

    fit = least_squares(lambda state: project(points, state)[1].ravel(), [2, 0, 0, 0])
    ordered, residual = project(points, fit.x)
    markers = [source["timing_pixel"], *source["sector_pixels"],
               *source["drs_activation_pixels"], *source["turn_pixels"]]
    stations, marker_residual = project(markers, fit.x)
    phase = stations[0]
    registered = (stations[1:] - phase) % length
    sectors, starts, turns = registered[:2], registered[2:4], registered[4:]
    ends = turns[np.asarray(source["drs_braking_turns"]) - 1] - config["conditions"]["drs_closure_margin_m"]
    zones = np.column_stack([starts, ends])
    limits = config["conditions"]
    rmse = np.sqrt(np.mean(np.sum(residual**2, axis=1)))
    max_marker = np.linalg.norm(marker_residual, axis=1).max()
    checks = {
        "clockwise_forward_numbered_route": bool(np.all(np.diff(ordered) > 0) and np.all(np.diff(turns) > 0)),
        "official_length": bool(abs(length / source["official_length_m"] - 1) <= limits["maximum_centreline_length_error_fraction"]),
        "map_registration": bool(fit.success and rmse <= limits["maximum_map_alignment_rmse_m"]
                                 and max_marker <= limits["maximum_map_marker_residual_m"]),
        "sector_and_drs_order": bool(0 < starts[0] < sectors[0] < ends[0] + limits["drs_closure_margin_m"]
                                     < starts[1] < sectors[1] < ends[1] < length
                                     and np.all(ends > starts)),
    }
    return dict(source_length_m=float(length), timing_line_source_m=float(phase), line_offset_fraction=float(phase / length),
                source_direction="original vertex order, clockwise", map_registration_parameters=fit.x.tolist(),
                map_alignment_rmse_m=float(rmse), max_map_marker_residual_m=float(max_marker),
                sector_station_m=sectors.tolist(), drs_zone_station_m=zones.tolist(),
                turn_station_m=turns.tolist(), basic_checks=checks)


def open_fraction(stations, zones):
    starts, ends = np.asarray(zones).T
    return np.any((stations[:, None] >= starts) & (stations[:, None] < ends), axis=1)


def spans(active, stations, minimum):
    """Sampled start and end stations of contiguous intervals, dropping small brake pulses."""
    changes = np.flatnonzero(np.diff(np.r_[False, active, False]))
    result = stations[np.minimum(changes, len(stations) - 1)].reshape(-1, 2)
    return result[np.diff(result, axis=1).ravel() >= minimum]


def trace_braking(sample, stations, speed, limits):
    intervals = spans(sample, stations, limits["minimum_brake_event_distance_m"])
    return [{"onset_m": float(start), "end_m": float(end),
             "minimum_speed_mps": float(speed[(stations >= start) & (stations <= end + 35)].min())}
            for start, end in intervals]


def local_checks(values, info, context):
    x, limits, registration, reference = context
    length = registration["source_length_m"]
    station = values[:, 0] * length
    speed = np.interp(x, station, values[:, 2])
    previous = np.searchsorted(station, x, side="right") - 1
    drs = np.isin(values[previous, 5], [10, 12, 14])
    model_drs = reference["open"]
    observed_zones = spans(drs, x, 0)
    drs_precision = np.count_nonzero(drs & model_drs) / max(1, model_drs.sum())
    drs_recall = np.count_nonzero(drs & model_drs) / max(1, drs.sum())
    edge_error = (observed_zones - reference["drs"]).tolist() if observed_zones.shape == reference["drs"].shape else None
    brake = trace_braking(values[previous, 3].astype(bool), x, speed, limits)
    used = set()
    for item in brake:
        delta = reference["peaks"] - item["onset_m"]
        item["distance_to_next_curvature_peak_m"] = float(delta[delta >= 0].min()) if np.any(delta >= 0) else None
        candidates = {i: m for i, m in enumerate(reference["braking"]) if i not in used}
        if candidates:
            i = min(candidates, key=lambda j: abs(candidates[j]["onset_m"] - item["onset_m"]))
            match = candidates[i]
            onset = match["onset_m"] - item["onset_m"]
            speed_error = match["minimum_speed_mps"] - item["minimum_speed_mps"]
            item.update(simulated_minus_observed_onset_m=onset, simulated_minus_observed_minimum_speed_mps=speed_error)
            if abs(onset) <= limits["max_brake_onset_difference_m"]:
                used.add(i)
    curvature_matches = sum(item["distance_to_next_curvature_peak_m"] is not None
                            and item["distance_to_next_curvature_peak_m"] <= limits["max_brake_to_turn_peak_m"] for item in brake)
    brake_matches = sum(abs(item.get("simulated_minus_observed_onset_m", np.inf)) <= limits["max_brake_onset_difference_m"]
                        and abs(item.get("simulated_minus_observed_minimum_speed_mps", np.inf))
                        <= limits["max_brake_min_speed_difference_mps"] for item in brake)
    model_time = reference["time"]
    sectors = np.diff(np.interp([0, *registration["sector_station_m"], length], x, model_time))
    sector_error = sectors - info["sector_times_s"]
    lap_error = model_time[-1] - info["duration_s"]
    rmse = np.sqrt(np.mean((reference["speed"] - speed)**2))
    pace = limits["pace"]
    checks = {
        "speed_distance": bool(abs(info["integrated_distance_m"] / length - 1) <= limits["maximum_lap_distance_error_fraction"]),
        "drs": bool(min(drs_precision, drs_recall) >= limits["minimum_drs_precision_and_recall"]
                    and edge_error is not None and np.max(np.abs(edge_error)) <= limits["maximum_drs_boundary_error_m"]),
        "brake_before_curvature": bool(curvature_matches / max(1, len(brake)) >= limits["min_brake_to_turn_peak_fraction"]),
        "model_brake_onset_and_minimum_speed": bool(brake_matches / max(1, len(brake), len(reference["braking"]))
                                                   >= limits["min_matched_brake_fraction"]),
        "lap_time": bool(abs(lap_error) <= pace["absolute_lap_error_s"]),
        "sector_time": bool(np.max(np.abs(sector_error)) <= pace["absolute_each_sector_error_s"]),
        "speed_rmse": bool(rmse <= pace["speed_rmse_mps"]),
    }
    return (dict(info, lap_error_s=float(lap_error), sector_errors_s=sector_error.tolist(), speed_rmse_mps=float(rmse),
                 drs_precision=float(drs_precision), drs_recall=float(drs_recall), drs_edge_errors_m=edge_error,
                 observed_drs_zones_m=observed_zones.tolist(), braking_events=brake, checks=checks), speed)


def fixed_replay(model, cells, action, cellwise):
    env = build_env(model, cells, cellwise=cellwise)
    result = rollout(env, lambda _: [action])
    summary = {k: v for k, v in result.items() if k != "trace"}
    return summary, result["trace"]


def read_cached(directory, driver):
    raw = {"laps": [], "car_data": [], "location": []}
    client = OpenF1Client(Path("work/source-audit-openf1"), offline=True)
    for request in load(directory / "requests.json"):
        url = urlsplit(request["url"])
        endpoint = url.path.rsplit("/", 1)[-1]
        params = dict(parse_qsl(url.query))
        if params.get("driver_number") == driver and endpoint in raw:
            raw[endpoint].extend(client.fetch(endpoint, **params))
            if client.records[-1]["sha256"] != request["sha256"]:
                raise ValueError("Cached response hash differs from frozen acquisition")
    return raw, client.records


def figure(path, env, register, x, reference, observed):
    fig, axes = plt.subplot_mosaic([["map", "speed"], ["map", "curvature"]], figsize=(11, 6.3))
    xy = env.grid.xy_m
    fraction = env.grid.distance_m / env.grid.distance_m[-1]
    ax = axes["map"]
    ax.plot(*xy.T, color="#4a6375", lw=1.6)
    ax.scatter(*xy[0], color="#ac3c31", s=36, zorder=3, label="Control line")
    for i, (left, right) in enumerate(register["drs_zone_station_m"]):
        span = xy[(fraction >= left/x[-1]) & (fraction <= right/x[-1])]
        ax.plot(*span.T, color="#218760", lw=3, label="Prescribed DRS" if not i else None)
    for turn, station in enumerate(register["turn_station_m"], 1):
        fx = station / x[-1]
        px, py = (np.interp(fx, fraction, xy[:, i]) for i in range(2))
        ax.annotate(f"T{turn}", (px, py), xytext=(4, 5), textcoords="offset points", fontsize=7)
    ax.set(xlabel="Local x (m)", ylabel="Local y (m)", aspect="equal", title="Registered 2025 layout")
    ax.legend(frameon=False, fontsize=8)
    ax = axes["speed"]
    for i, speed in enumerate(observed):
        ax.plot(x/1000, speed, color="#a4adb5", lw=.8, label="Screened qualifying laps" if not i else None)
    ax.plot(x/1000, reference["speed"], color="#175181", lw=1.25, label="Frozen model · 25% request")
    ax.set(ylabel="Speed (m/s)", title="Unaided vehicle transfer")
    ax.legend(frameon=False, fontsize=8)
    ax = axes["curvature"]
    ax.plot(x/1000, reference["curvature"], color="#4a6375", lw=1)
    for i, item in enumerate(reference["braking"]):
        ax.axvline(item["onset_m"]/1000, color="#ac3c31", alpha=.6, lw=.85,
                   label="Simulated braking onset" if not i else None)
    ax.set(ylabel="Absolute curvature (m⁻¹)", xlabel="Distance from control line (km)")
    ax.legend(frameon=False, fontsize=8)
    for ax in (axes["speed"], axes["curvature"]):
        for left, right in register["drs_zone_station_m"]:
            ax.axvspan(left/1000, right/1000, color="#218760", alpha=.10)
        ax.margins(x=0)
        ax.grid(axis="y", alpha=.2)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(path.with_suffix("." + ext), dpi=300)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/transfer-circuit-geometry-001"))
    parser.add_argument("--figures", type=Path, default=Path("figures/dissertation/transfer-circuit-geometry-v1"))
    args = parser.parse_args()
    config = load(CONFIG)
    selection_path = Path(config["selection"])
    model_path = Path(config["bahrain_model"])
    source = config["geometry"]
    check(source["path"], source["sha256"])
    check(source["license_path"], source["license_sha256"])
    check(model_path, config["bahrain_model_sha256"])
    selection = load(selection_path)
    keys = ("meeting_key", "session_key", "role")
    if selection["selected_circuit"].lower() != config["circuit"].lower() or any(selection[k] != config[k] for k in keys):
        raise ValueError("Frozen selection does not match the registered map")
    split = next(event for event in load(Path("configs/openf1_dataset_plan.json"))["events"]
                 if event["meeting_key"] == config["meeting_key"])
    if config["role"] != split["role"] or split["role"] == "test" or config["session_key"] not in split["session_keys"]:
        raise ValueError("Event role or session differs from original split")
    directory = Path(config["acquisition"]) / config["role"] / str(config["meeting_key"]) / str(config["session_key"])
    complete = load(directory / "complete.json")
    verify_outputs(directory, complete)
    if complete["session_name"] != "Qualifying":
        raise ValueError("Only qualifying geometry was declared")
    bounds = config["conditions"]
    xy = np.loadtxt(source["path"], delimiter=",")[:, :2]
    register = map_registration(config, xy)
    # Freeze the bridge before inspecting qualifying outcomes.
    args.output.mkdir(parents=True, exist_ok=False)
    track_path = args.output / "Silverstone.csv"
    copyfile(source["path"], track_path)
    copyfile(source["license_path"], args.output / "SOURCE_LICENSE.txt")
    length = register["source_length_m"]
    blocks = open_fraction((np.arange(55) + .5) / 55 * length, register["drs_zone_station_m"])
    model = dict(load(model_path), geometry=track_path.as_posix(), geometry_sha256=source["sha256"],
                 line_offset_fraction=register["line_offset_fraction"], drs_blocks=blocks.tolist())
    save_json(args.output / "model.json", model)
    metrics = dict(circuit=config["circuit"], role=config["role"], registration=register, laps={},
                   geometry_passed=False, pace_passed=False, empirical_location_passed=False)
    outputs = []
    if all(register["basic_checks"].values()):
        assess(config, selection, directory, model, metrics, args.figures)
        if args.figures.is_dir():
            outputs.extend(args.figures.iterdir())
    save_json(args.output / "metrics.json", metrics)
    code = ["scripts/prepare_transfer_circuit.py", "scripts/prepare_bahrain_pace.py", "scripts/bahrain_pace_model.py",
            "scripts/acquire_openf1_dataset.py", "scripts/benchmark_circuit_control.py", "src/f1energy/openf1.py",
            "src/f1energy/circuit.py", "src/f1energy/circuit_control.py", "src/f1energy/event_power_lap.py",
            "src/f1energy/power_lap.py"]
    inputs = [CONFIG, selection_path, model_path, directory / "complete.json", Path("configs/openf1_dataset_plan.json")]
    outputs.extend(args.output.iterdir())
    save_json(args.output / "manifest.json", {
        "inputs": {Path(p).as_posix(): digest(p) for p in inputs},
        "code": {p: digest(p) for p in code},
        "external_sources": {"geometry": source, "fia_map_url": config["fia_map"]["url"],
                             "fia_map_sha256": config["fia_map"]["sha256"]},
        "outputs": {p.as_posix(): digest(p) for p in sorted(outputs)},
    })
    print({key: metrics[key] for key in ("circuit", "geometry_passed", "pace_passed", "empirical_location_passed")})


def assess(config, selection, directory, model, metrics, figures):
    limits = config["conditions"]
    register = metrics["registration"]
    length = register["source_length_m"]
    coarse, fine = limits["cells_per_block"]
    checks = metrics["geometry_checks"] = dict(register["basic_checks"])
    try:
        env = build_env(model, fine)
        baseline = [rollout(e, baseline_policy("spread", e))
                    for e in (build_env(model, coarse), env)]
    except (ValueError, RuntimeError) as exc:
        metrics["solver_failure"] = str(exc)
        checks["solver_build_and_run"] = False
        return
    checks["solver_build_and_run"] = True
    checks["spread_feasible_both_grids"] = all(row["feasible"] for row in baseline)
    metrics["spread_replay"] = [{k: v for k, v in row.items() if k != "trace"} for row in baseline]
    co, _ = fixed_replay(model, coarse, limits["reference_action"], False)
    fi, trace = fixed_replay(model, fine, limits["reference_action"], True)
    metrics["pace_reference"] = {"coarse": co, "fine": fi,
                                 "refinement_s": abs(fi["duration_s"] - co["duration_s"])}
    x = np.linspace(0, length, int(length / 5) + 1)
    nodes = np.asarray([[0, 0, model["initial_speed_mps"]]] + [
        [row["state"][key] for key in ("distance_m", "elapsed_s", "speed_m_per_s")] for row in trace])
    stations = nodes[:, 0] / nodes[-1, 0] * length
    speed, time = (np.interp(x, stations, nodes[:, i]) for i in (2, 1))
    midpoint = (stations[1:] + stations[:-1]) / 2
    brake_sample = [row["friction_braking_work_j"] + row["regenerative_braking_work_j"] > 1 for row in trace]
    brakes = trace_braking(np.interp(x, midpoint, brake_sample) > .5, x, speed, limits)
    kappa = np.interp(x, stations, abs(env.grid.curvature_per_m))
    peak_idx = find_peaks(kappa, height=limits["min_turn_peak_abs_curvature_per_m"], distance=8)[0]
    drs = blocks_at(x / length, np.asarray(model["drs_blocks"]))
    reference = dict(speed=speed, time=time, curvature=kappa, braking=brakes, peaks=x[peak_idx],
                     drs=spans(drs, x, 0), open=drs)
    metrics["modeled_brake_events"] = brakes
    metrics["curvature_peak_stations_m"] = reference["peaks"].tolist()
    metrics["modeled_drs_zones_m"] = reference["drs"].tolist()
    metrics["raw_cache_responses"] = []
    observed = []
    for driver, lap_numbers in selection["laps_by_driver"].items():
        raw, records = read_cached(directory, driver)
        metrics["raw_cache_responses"].extend(records)
        screened = {row["lap_number"]: row for row in load(directory / f"driver-{driver}-laps.json")
                    if row["conditional_motion_candidate"]}
        for lap in lap_numbers:
            key = f"driver-{driver}-lap-{lap}"
            entry = screened[lap]
            try:
                info, values = prepare_lap(entry["lap"], raw["car_data"], limits["max_telemetry_gap_s"])
                scores, profile = local_checks(values, info, (x, limits, register, reference))
            except (AssertionError, IndexError, ValueError) as exc:
                metrics["laps"][key] = {"preparation_passed": False, "error": str(exc) or "Invalid native lap edge, gap or sector clock"}
                continue
            observed.append(profile)
            scores["preparation_passed"] = True
            try:
                alignment = timing_alignment(entry["lap"], raw["location"], np.loadtxt(model["geometry"], delimiter=",")[:, :2])
                map_phase = model["line_offset_fraction"]
                differences = [abs((p - map_phase + .5) % 1 - .5) * length for p in
                               [alignment["selected"]["phase_fraction"], *alignment["edge_projection_fractions"]]]
                scores["xy_alignment"] = alignment
                scores["absolute_map_to_xy_timing_line_differences_m"] = differences
                scores["checks"]["location_alignment"] = (
                    max(differences) <= limits["maximum_map_to_xy_timing_line_difference_m"]
                    and alignment["edge_closure_m"] <= limits["maximum_location_closure_m"]
                    and alignment["location_max_gap_s"] <= limits["max_telemetry_gap_s"])
            except (AssertionError, IndexError, ValueError) as exc:
                scores["checks"]["location_alignment"] = False
                scores["location_alignment_error"] = str(exc) or "Failed Bahrain forward-direction, scale, ambiguity or XY bracket check"
            metrics["laps"][key] = scores
    def all_laps(*names):
        return bool(metrics["laps"]) and all(all(lap.get("checks", {}).get(n, False) for n in names)
                                             for lap in metrics["laps"].values())
    checks["independent_openf1_distance_direction_and_timing"] = all_laps("speed_distance", "location_alignment")
    metrics["geometry_passed"] = all(checks.values())
    metrics["pace_passed"] = (fi["feasible"] and co["feasible"]
                              and metrics["pace_reference"]["refinement_s"] <= limits["pace"]["absolute_grid_time_change_s"]
                              and all_laps("lap_time", "sector_time", "speed_rmse"))
    metrics["empirical_location_passed"] = (metrics["geometry_passed"] and metrics["pace_passed"]
                                            and all_laps("drs", "brake_before_curvature", "model_brake_onset_and_minimum_speed"))
    figures.mkdir(parents=True, exist_ok=False)
    figure(figures / "01_silverstone_transfer_geometry", env, register, x, reference, observed)


def blocks_at(fractions, blocks):
    return blocks[np.minimum((fractions * len(blocks)).astype(int), len(blocks)-1)]


if __name__ == "__main__":
    main()
