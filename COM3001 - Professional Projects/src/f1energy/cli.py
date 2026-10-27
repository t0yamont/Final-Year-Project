"""Small offline verification CLI. Future research commands are not implemented."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
from . import __version__
from .config import ConfigError, load_config
from .fixture import run_fixture


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_record():
    package = Path(__file__).resolve().parent
    files = {path.name: sha256(path) for path in sorted(package.glob("*.py"))}
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=package,
                                capture_output=True, text=True, timeout=5, check=False)
        commit = result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        commit = None
    return {"commit": commit, "package_files_sha256": files,
            "note": "File hashes identify executed package contents, including uncommitted edits."}


def verify(config_path, output):
    started = time.perf_counter()
    config_path, output = Path(config_path).resolve(), Path(output).resolve()
    config = load_config(config_path)
    records = run_fixture(config)
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output / "config.json"
    snapshot.write_bytes(config_path.read_bytes())
    trajectory = output / "trajectory.csv"
    with trajectory.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    summary = {"status": "completed", "kind": "synthetic_analytic_straight",
               "segment_count": len(records), "elapsed_s": records[-1]["elapsed_s"],
               "battery_used_j": sum(row["battery_draw_j"] for row in records),
               "terminal_energy_j": records[-1]["remaining_energy_j"],
               "interpretation": "Offline analytic fixture only; not F1 lap-time evidence."}
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    manifest = {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
                "command": "verify", "config_path": str(config_path),
                "config_sha256": sha256(snapshot),
                "inputs": [{"kind": "synthetic_configuration", "path": "config.json", "sha256": sha256(snapshot)}],
                "split_ids": [], "split_note": "No empirical data or fitted parameters.",
                "source": source_record(), "seed": config["seed"],
                "seed_note": "Recorded for interface continuity; fixture is deterministic and uses no RNG.",
                "software": {"python": platform.python_version(), "f1energy": __version__, "runtime_dependencies": []},
                "platform": platform.platform(), "executable": sys.executable,
                "runtime_s": time.perf_counter() - started,
                "outputs": [{"path": p.name, "sha256": sha256(p)} for p in [snapshot, trajectory, summary_path]],
                "verification_scope": "Config validity, analytic trajectory, nonnegative usable energy; independent tests are separate."}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline F1 energy research foundation (synthetic fixtures only).")
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("verify", help="Run the analytic synthetic straight and save a provenance manifest.")
    command.add_argument("--config", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True, help="New output directory; existing directories are never overwritten.")
    args = parser.parse_args(argv)
    try:
        summary = verify(args.config, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(summary, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
