"""Reproduce saved physical trajectories without the finish action filter."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import copy
import json
from pathlib import Path

import numpy as np

from bahrain_pace_model import build_env
from benchmark_circuit_control import sha
from f1energy.circuit_control import rollout, baseline_policy
from verify_bahrain_deployment import close, read, verify_rollout


def finish_error_after(env, action):
    copy_env = copy(env)
    for index in range(env.index, env.blocks):
        copy_env.step([action if index == env.index else 1.])
    return copy_env.state.speed_m_per_s - env.initial_speed


def verify_grid(model, rows, cells, suffix_length):
    env = build_env(model, cells)
    neutral = rollout(env, baseline_policy("zero", env))["trace"]
    suffix = env.blocks - suffix_length
    seconds = [b["duration_s"] for b in neutral]
    draw_w = env.vehicle.electrical_limit_w / env.vehicle.discharge_efficiency
    protected = sum(seconds[suffix:]) * env.vehicle.electrical_limit_w / env.vehicle.discharge_efficiency
    tol = 1e-5
    checked = guarded = interventions = probes = 0
    max_finish = 0.
    for row in rows:
        if row["cells"] != cells:
            continue
        verify_rollout(row, model)
        saved = read(row["file"])
        obs, _ = env.reset()
        guarded_row = row["arm"].endswith("_guarded")
        row_probes = 0
        for i, (block, archived_obs) in enumerate(zip(saved["trace"], saved["pre_action_observations"], strict=True)):
            np.testing.assert_array_equal(obs, np.asarray(archived_obs, dtype=np.float32))
            action = block["action"]
            if guarded_row:
                entry = block["finish_constraint"]
                proposal = entry["proposed_action"]
                assert entry["phase"] == ("prefix" if i < suffix else "terminal")
                assert entry["changed"] == (proposal != action)
                close(protected, entry["protected_draw_j"], 1e-5)
                charge = env.state.energy_j - env.reserve
                allowance = env.regeneration.deployment_limit_j - env.discharged_j
                close(charge, entry["available_charge_before_j"], 1e-5)
                close(allowance, entry["discharge_left_before_j"], 1e-5)
                if i < suffix:
                    ceiling = float(np.clip((min(charge, allowance) - protected) / (draw_w * seconds[i]), 0, 1))
                    close(entry["prefix_action_ceiling"], ceiling, 1e-12)
                    wanted = min(proposal, ceiling)
                    count = 0
                else:
                    error = finish_error_after(env, proposal)
                    close(error, entry["proposed_backup_finish_error_mps"])
                    wanted = proposal if abs(error) < tol else 1.
                    count = env.blocks - i
                    if abs(error) >= tol:
                        assert proposal != wanted and abs(finish_error_after(env, wanted)) < tol
                        count *= 2
                close(action, wanted, 1e-12)
                close(action, entry["issued_action"], 1e-12)
                assert count == entry["lookahead_transitions"]
                row_probes += count
                interventions += int(entry["changed"])
            else:
                assert "finish_constraint" not in block
            obs, _, done, _, bare = env.step([action])
            for key in ("elapsed_s", "distance_m", "speed_m_per_s", "energy_j"):
                close(bare["state"][key], block["state"][key], 1e-8)
            for key in ("electrical_work_j", "battery_discharged_j", "battery_recovered_j", "duration_s"):
                close(bare[key], block[key], 1e-8)
            assert done == (i + 1 == env.blocks)
        finish = env.state.speed_m_per_s - env.initial_speed
        close(finish, row["terminal_speed_error_mps"])
        if guarded_row:
            assert row["feasible"] and abs(finish) < tol and row_probes <= suffix_length * (suffix_length + 1)
            max_finish = max(max_finish, abs(finish))
            guarded += 1
        checked += 1
        probes += row_probes
    return dict(cells=cells, bare_plant_replays=checked, guarded_replays=guarded,
                changed_proposals=interventions, independently_checked_preview_transitions=probes,
                protected_draw_j=protected, max_guarded_finish_error_mps=max_finish)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--record", type=Path)
    args = parser.parse_args()
    contract = read(args.run / "contract.json")
    m = read(args.run / "metrics.json")
    manifest = read(args.run / "manifest.json")
    for group in ("sources", "inputs", "outputs"):
        for path, digest in manifest[group].items():
            if sha(path) != digest:
                raise ValueError(f"Hash mismatch: {path}")
    model = contract["model"]
    totals = ("bare_plant_replays", "guarded_replays", "changed_proposals", "independently_checked_preview_transitions")
    audits = []
    with ProcessPoolExecutor(6) as pool:
        jobs = {}
        for grid in (160, 320):
            rows = [r for r in m["rows"] if r["cells"] == grid]
            jobs[grid] = [pool.submit(verify_grid, model, rows[offset::3], grid, contract["experiment"]["terminal_blocks"])
                          for offset in range(3)]
        for grid, group in jobs.items():
            parts = [job.result() for job in group]
            counts = {key: sum(p[key] for p in parts) for key in totals}
            if counts["guarded_replays"] != 26 or counts["bare_plant_replays"] != 52:
                raise ValueError("Missing evaluation arms")
            audits.append(dict(cells=grid, **counts, protected_draw_j=parts[0]["protected_draw_j"],
                               max_guarded_finish_error_mps=max(p["max_guarded_finish_error_mps"] for p in parts)))
    result = dict(input_manifest_sha256=sha(args.run / "manifest.json"), verifier_sha256=sha(__file__),
                  hash_entries=sum(len(manifest[k]) for k in ("sources", "inputs", "outputs")), per_grid=audits)
    if args.record:
        with args.record.open("x", encoding="utf-8") as out:
            json.dump(result, out, indent=2)
            out.write("\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
