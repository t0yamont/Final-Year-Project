"""Reapply recorded deployment requests to the Bahrain plant and verify scarcity evidence."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from itertools import combinations, repeat
from pathlib import Path

from bahrain_pace_model import build_env
from benchmark_circuit_control import save, sha
from validate_regeneration import audit_replay
from verify_bahrain_deployment import close, read


CONFIG = Path("configs/bahrain_energy_scarcity.json")
ROOTS = {s: Path(f"results/bahrain-scarcity-{s}-001") for s in ("planners", "zones")}


def verify_hashes(mapping):
    for filename, digest in mapping.items():
        if sha(filename) != digest:
            raise ValueError(f"Changed file: {filename}")
    return len(mapping)


def replay_group(protocol, task):
    scenario, cells, files = task
    config = protocol["scenarios"][scenario]
    model = read(protocol["model"])
    model["initial_energy_j"] = config["initial_energy_j"]
    model["regeneration"]["braking_fraction"] = config["braking_fraction"]
    env = build_env(model, cells)
    count = 0
    for file in files:
        lap = read(file)
        trace = lap["trace"]
        if len(trace) != env.blocks:
            raise ValueError(f"Incomplete trajectory: {file}")
        audit_replay(lap, model, model, env.vehicle)
        env.reset()
        for i, expected in enumerate(trace):
            _, _, done, truncated, actual = env.step([expected["action"]])
            for key, value in actual["state"].items():
                close(value, expected["state"][key], 1e-7)
            for field in ("duration_s", "electrical_work_j", "battery_discharged_j", "battery_recovered_j",
                          "friction_braking_work_j", "regenerative_braking_work_j", "max_node_cap_excess_mps"):
                close(actual[field], expected[field], 1e-7)
            if truncated or done != (i + 1 == env.blocks):
                raise ValueError(f"Bad terminal marker: {file}")
        error = env.state.speed_m_per_s - env.initial_speed
        close(env.state.elapsed_s, lap["duration_s"])
        close(error, lap["terminal_speed_error_mps"])
        feasible = (abs(error) < protocol["finish_speed_tolerance_mps"] and
                    env.state.energy_j >= env.reserve - 1e-5 and
                    max(b["max_node_cap_excess_mps"] for b in trace) < 1e-5 and
                    abs(sum(b["energy_residual_j"] for b in trace)) < 1.)
        if feasible != lap["feasible"]:
            raise ValueError(f"Finish classification disagrees: {file}")
        count += feasible
    return dict(scenario=scenario, cells=cells, distinct_scored_files=len(files), feasible=count)


def within_grid_limits(primary, fine, limits):
    recovered = [sum(b["battery_recovered_j"] for b in lap["trace"]) for lap in (primary, fine)]
    return (abs(primary["duration_s"] - fine["duration_s"]) / fine["duration_s"] <= limits["relative_lap_change"]
            and abs(primary["final_energy_j"] - fine["final_energy_j"]) <= limits["terminal_energy_change_j"]
            and abs(recovered[0] - recovered[1]) <= limits["recovered_change_j"])


def planner_records(run, protocol):
    cases = read(run / "metrics.json")["cases"]
    if set(cases) != set(protocol["scenarios"]):
        raise ValueError("Incomplete planner scenarios")
    files = {}
    matched = []
    for scenario, case in cases.items():
        for grid in protocol["grids"]:
            rows = case["raw"][str(grid)]
            files[scenario, grid] = {Path(r["file"]) for r in rows.values()}
        for policy, families in case["matched"].items():
            for family, comparison in families.items():
                selected = comparison.get("preferred")
                if selected is None:
                    continue
                replays = {}
                deltas = []
                work_errors = []
                for grid in protocol["grids"]:
                    pair = selected["grids"][str(grid)]
                    for label in ("reference", "spread"):
                        path = Path(pair[label]["file"])
                        files[scenario, grid].add(path)
                        lap = read(path)
                        close(lap["duration_s"], pair[label]["duration_s"])
                        if lap["feasible"] != pair[label]["feasible"]:
                            raise ValueError(f"Scored feasibility differs for {path}")
                        delivered = sum(b["electrical_work_j"] for b in lap["trace"])
                        close(delivered, pair[label]["wheel_assist_j"])
                        replays[grid, label] = lap
                    work_errors.append(pair["spread"]["wheel_assist_j"] - pair["reference"]["wheel_assist_j"])
                    close(work_errors[-1], pair["difference_j"])
                    deltas.append(replays[grid, "spread"]["duration_s"] - replays[grid, "reference"]["duration_s"])
                    if pair["saving_s"] is not None:
                        close(deltas[-1], pair["saving_s"])
                limits = protocol["refinement"]
                passed = (all(lap["feasible"] for lap in replays.values()) and
                          max(map(abs, work_errors)) <= protocol["total_work_pair_tolerance_j"] and
                          abs(deltas[0] - deltas[1]) <= limits["paired_gap_change_s"])
                for label in ("reference", "spread"):
                    a, b = (replays[g, label] for g in protocol["grids"])
                    passed = passed and within_grid_limits(a, b, limits)
                direction = ("reference_faster" if deltas[-1] > 0 else "spread_faster") if passed and deltas[0] * deltas[1] > 0 else None
                if selected['passed'] != passed or selected['direction'] != direction:
                    raise ValueError(f"Planner attribution mismatch: {scenario}/{policy}/{family}")
                matched.append(dict(scenario=scenario, policy=policy, family=family, physically_matched_and_stable=passed,
                                    resolved=passed and deltas[0] * deltas[1] > 0,
                                    fine_saving_s=deltas[-1] if passed else None))
    return files, matched


def zone_records(run, protocol):
    zones = read(run / "zones.json")
    blocks = {}
    for zone, original in zip(zones, protocol["zones"], strict=True):
        if (zone["first_block"], zone["last_block"]) != (original["first_block"], original["last_block"]):
            raise ValueError("Zone boundaries differ from original protocol")
        blocks[zone["id"]] = range(zone["first_block"] - 1, zone["last_block"])
    files, statuses = {}, {}
    cases = read(run / "metrics.json")
    if {s["scenario"] for s in cases} != set(protocol["scenarios"]):
        raise ValueError("Incomplete packet scenarios")
    for case in cases:
        scenario = case["scenario"]
        results = case["replays"]
        evidence = {}
        for label, policy in results.items():
            for variant, cells in (("160", 160), ("320", 320), ("frozen", 320)):
                row = policy[variant]
                path = Path(row["file"])
                files.setdefault((scenario, cells), set()).add(path)
                lap = read(path)
                curve = [b["electrical_work_j"] for b in lap["trace"]]
                residual = sum(abs(w - t) for w, t in zip(curve, row["target_by_block_j"], strict=True))
                close(row["target_l1_error_j"], residual)
                close(lap["duration_s"], row["duration_s"])
                if variant == "frozen" and row["actions"] != policy["160"]["actions"]:
                    raise ValueError("Fixed-action refinement used different requests")
                evidence[label, variant] = lap, curve, residual
        pairs = case["pairs"]
        if {(row["donor"], row["recipient"]) for row in pairs} != set(combinations(blocks, 2)) or len(pairs) != 21:
            raise ValueError(f"Incomplete packet matrix in {scenario}")
        for row in pairs:
            donor, recipient = row["donor"], row["recipient"]
            phases = ("160", "320", "frozen")
            gaps = []
            checks = []
            for variant in phases:
                a, wa, ea = evidence[donor, variant]
                b, wb, eb = evidence[recipient, variant]
                d = [v - u for u, v in zip(wa, wb, strict=True)]
                outside = sum(abs(value) for i, value in enumerate(d) if i not in blocks[donor] and i not in blocks[recipient])
                gain = sum(d[i] for i in blocks[recipient])
                loss = -sum(d[i] for i in blocks[donor])
                grid = "frozen_320" if variant == "frozen" else variant
                for key, expected in (("off_zone_l1", outside), ("recipient_gain", gain),
                                      ("donor_loss", loss), ("total_work_gap", sum(d))):
                    close(row[f"{key}_{grid}_j"], expected)
                matched = max(abs(sum(d)), outside, abs(gain - 20000.), abs(loss - 20000.), ea, eb) <= protocol["total_work_pair_tolerance_j"]
                feasible = a["feasible"] and b["feasible"]
                if row[f"matched_{grid}"] != matched or row[f"feasible_{grid}"] != feasible:
                    raise ValueError(f"Packet eligibility mismatch in {scenario} {donor} -> {recipient}")
                gaps.append(b["duration_s"] - a["duration_s"])
                checks.append((feasible, matched))
                if feasible and matched:
                    close(row[f"delta_time_{grid}_ms"], gaps[-1] * 1000)
            limits = protocol["refinement"]
            drift = max(abs(gaps[0] - gaps[1]), abs(gaps[0] - gaps[2]))
            stable = (drift <= limits["paired_gap_change_s"] and checks[2][0]
                      and all(within_grid_limits(evidence[z, "160"][0], evidence[z, g][0], limits)
                              for z in (donor, recipient) for g in ("320", "frozen")))
            threshold = max(.0005, drift)
            if not all(f for f, _ in checks[:2]):
                status = "feasibility_failed"
            elif not all(m for _, m in checks[:2]):
                status = "match_failed"
            elif not stable:
                status = "refinement_failed"
            else:
                status = "resolved" if max(gaps) < -threshold or min(gaps) > threshold else "unresolved"
            direction = ("recipient_faster" if gaps[1] < 0 else "donor_faster") if status == "resolved" else None
            if row["refinement_passed"] != stable or row["status"] != status or row["direction"] != direction:
                raise ValueError(f"Zone priority classification disagrees in {scenario} {donor} -> {recipient}")
            statuses[row["status"]] = statuses.get(row["status"], 0) + 1
    return files, statuses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arm", choices=ROOTS)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--workers", choices=range(1, 9), type=int, default=4)
    args = parser.parse_args()
    if args.record.exists():
        raise FileExistsError(args.record)
    root = ROOTS[args.arm]
    manifest = read(root / "manifest.json")
    protocol = read(CONFIG)
    hashes = sum(verify_hashes(manifest[group]) for group in ("sources", "inputs", "outputs"))
    verify_hashes(protocol["parent_hashes"])
    index = planner_records if args.arm == "planners" else zone_records
    groups, comparisons = index(root, protocol)
    tasks = [(scenario, grid, sorted(paths)) for (scenario, grid), paths in groups.items()]
    with ProcessPoolExecutor(args.workers) as pool:
        audit = list(pool.map(replay_group, repeat(protocol), tasks))
    args.record.parent.mkdir(exist_ok=True, parents=True)
    save(args.record, dict(manifest_sha256=sha(root / "manifest.json"), verifier_sha256=sha(__file__),
                           verified_manifest_entries=hashes, replay_groups=audit, comparisons=comparisons))
    print(f"Verified {sum(g['distinct_scored_files'] for g in audit)} replay files and {hashes} bound hashes.", flush=True)


if __name__ == "__main__":
    main()


