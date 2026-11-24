"""Independently check Silverstone work matching and replay CPU-scored checkpoints on CUDA."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from bahrain_pace_model import build_env
from benchmark_circuit_control import sha
from f1energy.circuit_control import rollout
from train_bahrain_algorithm_width import ALGORITHMS, verify_hashes
from verify_bahrain_deployment import close, read, verify_rollout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--record", type=Path)
    args = parser.parse_args()
    manifest = read(args.run / "manifest.json")
    for group in ("inputs", "sources", "outputs"):
        verify_hashes(manifest[group])
    model, m, p = (read(args.run / n) for n in ("model.json", "metrics.json", "contract.json"))
    protocol = p["protocol"]
    assert [key for key in model if model[key] != p["inherited_model"][key]] == ["initial_speed_mps"]
    assert m["model_only"] and not m["geometry_passed"] and not m["pace_passed"]
    rows = {(r["policy"], r["cells"]): r for r in m["rows"]}
    assert len(rows) == len(m["rows"]) == 28
    for r in rows.values():
        verify_rollout(r, model)
    matched = m["work_match"]
    for grid in (160, 320):
        pair, baseline = matched["grids"][str(grid)], rows["selected", grid]
        verify_rollout(pair, model)
        close(pair["wheel_assist_j"] - baseline["wheel_assist_j"], pair["difference_j"])
        close(pair["duration_s"] - baseline["duration_s"], pair["saving_s"])
        assert pair["feasible"] and baseline["feasible"] and abs(pair["difference_j"]) <= 500
    limits = protocol["refinement"]
    gaps = matched["grids"]
    close(abs(gaps["160"]["saving_s"] - gaps["320"]["saving_s"]), matched["paired_gap_change_s"])
    for a, b in [(gaps["160"], gaps["320"]), (rows["selected", 160], rows["selected", 320])]:
        assert abs(a["duration_s"] - b["duration_s"]) / b["duration_s"] <= limits["relative_lap_change"]
        assert abs(a["recovered_j"] - b["recovered_j"]) <= limits["recovered_change_j"]
        assert abs(a["final_energy_j"] - b["final_energy_j"]) <= limits["terminal_energy_change_j"]
    assert matched["passed"] and matched["paired_gap_change_s"] <= limits["paired_gap_change_s"]

    torch.set_num_threads(1)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for the cross-device check")
    envs = {g: build_env(model, g) for g in (160, 320)}
    maximum_action_error = maximum_time_error = 0.
    replays = actions = 0
    for row in m["rows"]:
        if row["cells"] != 160 or "checkpoint" not in row:
            continue
        agent = ALGORITHMS[row["method"]].load(row["checkpoint"], device="cuda:0")
        assert agent.device.type == "cuda" and sha(row["checkpoint"]) == row["checkpoint_sha256"]
        for g, env in envs.items():
            archived = rows[row["policy"], g]
            lap = read(archived["file"])
            observations = lap["pre_action_observations"]
            for obs, step in zip(observations, lap["trace"], strict=True):
                x = float(agent.predict(np.array(obs, dtype=np.float32), deterministic=True)[0].item())
                maximum_action_error = max(maximum_action_error, abs(x - step["action"]))
                actions += 1
            gpu_lap = rollout(env, lambda obs: agent.predict(obs, deterministic=True)[0])
            assert gpu_lap["feasible"] == archived["feasible"]
            maximum_time_error = max(maximum_time_error, abs(gpu_lap["duration_s"] - archived["duration_s"]))
            replays += 1
    assert (actions, replays) == (1320, 24)
    report = dict(hashes=sum(len(group) for group in manifest.values()), physical_rows=len(rows),
                  matched_trace_audits=2, cuda_actions_compared=actions, cuda_closed_loop_replays=replays,
                  max_action_fraction_difference=maximum_action_error, max_elapsed_difference_s=maximum_time_error,
                  same_finish_classifications=True, input_manifest_sha256=sha(args.run / "manifest.json"),
                  verifier_sha256=sha(__file__))
    if args.record:
        with args.record.open("x", encoding="utf-8") as out:
            json.dump(report, out, indent=2)
            out.write("\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
