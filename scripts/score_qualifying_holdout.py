"""Score frozen development fits on the declared qualifying holdout once."""
import argparse
import csv
import gzip
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from prepare_openf1_motion import pairs, sha
from study_session_mix import save


def read(path):
    return json.loads(Path(path).read_bytes())


def verified(path, expected):
    if sha(path) != expected:
        raise ValueError(f"Frozen input changed: {path}")


def event_windows(protocol, event, acquisition, digests):
    directory = Path(protocol["source"]) / str(event["meeting"]) / str(event["session"])
    completion = directory / "complete.json"
    verified(completion, acquisition["sha256"])
    record = read(completion)
    if (record["role"], record["meeting_key"], record["session_key"], record["session_name"]) != (
        "test", event["meeting"], event["session"], "Qualifying"
    ):
        raise ValueError(f"Unexpected source identity: {completion}")
    number = protocol["driver_number"]
    driver = next(d for d in record["drivers"] if int(d["driver_number"]) == number)
    digests[str(completion)] = acquisition["sha256"]
    known = next(d for d in acquisition["drivers"] if d["driver_number"] == number)
    if known["conditional_motion_candidates"] != event["candidate_laps"]:
        raise ValueError("Coverage changed")
    if not event["candidate_laps"]:
        return [], {}
    lap_file = directory / f"driver-{number}-laps.json"
    car_file = directory / f"driver-{number}-car.csv.gz"
    for path in (lap_file, car_file):
        digests[str(path)] = driver["outputs"][path.name]
        verified(path, digests[str(path)])
    laps = {str(r["lap_number"]): [] for r in read(lap_file) if r["conditional_motion_candidate"]}
    if len(laps) != event["candidate_laps"]:
        raise ValueError("Candidate lap identities disagree with acquisition")
    with gzip.open(car_file, "rt", newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["lap_number"] in laps:
                laps[row["lap_number"]].append(row)
    windows, audit = [], {}
    for lap, rows in laps.items():
        selected, exclusions = pairs(rows)
        audit[lap] = dict(input_samples=len(rows), selected=len(selected), exclusions=exclusions)
        windows.extend(dict(lap=lap, **r) for r in selected)
    return windows, audit


def in_filter(row, sensitivity):
    if sensitivity == "dt_le_0.3":
        return row["dt_s"] <= .3
    if sensitivity == "speed_ge_30":
        return row["speed_mid_mps"] >= 30
    if sensitivity != "primary":
        raise ValueError(f"Unknown filter: {sensitivity}")
    return True


def plot(scores, events, arms, figures):
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 4), sharey=True)
    for ax, (sensitivity, title) in zip(axes, [
        ("primary", "Primary windows"), ("dt_le_0.3", "Pair gap ≤ 0.3 s"), ("speed_ge_30", "Speed ≥ 30 m/s")
    ]):
        for event in events:
            subset = [r for r in scores if r["event"] == event["event"] and r["filter"] == sensitivity]
            if not subset:
                continue
            for i, arm in enumerate(arms):
                values = [r["rmse"][arm] for r in subset]
                ax.plot([i, i], [min(values), max(values)], color="#306787", linewidth=3)
                ax.plot(i, mean(values), "o", color="#24445b", label=event["event"] if i == 0 else None)
        ax.set_title(title)
        ax.set_xticks(range(len(arms)), ["Q", "QP", "QPR", "QP\nmatched", "QPR\nmatched"], fontsize=8)
        ax.grid(axis="y", alpha=.2)
        if ax.lines:
            ax.legend(fontsize=8)
    axes[0].set_ylabel("Mean lap/DRS-group RMSE (m/s²)")
    fig.suptitle("Held-out qualifying acceleration at observed speed")
    fig.text(.5, .025, "Belgium: zero eligible laps. Points show seed means. Lines span the five matched draws.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .08, 1, .94))
    for extension in ("png", "pdf"):
        fig.savefig(figures / f"qualifying_holdout.{extension}", dpi=300)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/session-mix-final-001"))
    parser.add_argument("--figures", type=Path, default=Path("figures/dissertation/session-mix-final-v1"))
    args = parser.parse_args()
    protocol_path = Path("configs/session_mix_final.json")
    protocol = read(protocol_path)
    digests = dict(protocol["inputs"])
    for path, digest in digests.items():
        verified(path, digest)
    development = read("configs/session_mix_protocol.json")
    arms = development["arms"]
    fits = defaultdict(list)
    for m in read("results/session-mix-validation-002/models.json"):
        fits[m["sensitivity"], m["seed"], m["arm"], str(m["drs"])].append(m)
    acquisition = {r["meeting_key"]: r for r in read("logs/agent_tools/2026-11-18/session_mix_coverage_decision.json")["records"]}
    args.output.mkdir(parents=True, exist_ok=False)
    args.figures.mkdir(parents=True, exist_ok=False)
    sources = {str(p): sha(p) for p in [Path(__file__), Path("scripts/study_session_mix.py")]}
    digests[str(protocol_path)] = sha(protocol_path)
    save(args.output / "contract.json", dict(protocol=protocol, inputs=digests, sources=sources))
    scores, coverage, lap_audits = [], [], {}
    prediction_path = args.output / "predictions.csv.gz"
    with gzip.open(prediction_path, "wt", newline="", encoding="utf-8") as stream:
        fields = ["event", "filter", "seed", "lap", "drs", "start_utc", "speed", "observed", "constant", *arms]
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        for event in protocol["events"]:
            name = event["event"]
            windows, lap_audits[name] = event_windows(protocol, event, acquisition[event["meeting"]], digests)
            for sensitivity in development["sensitivities"]:
                selected = [r for r in windows if in_filter(r, sensitivity)]
                supported = [r for r in selected if (sensitivity, 0, "Q", str(r["drs"])) in fits]
                coverage.append(dict(event=name, filter=sensitivity, candidate_laps=event["candidate_laps"],
                                     selected=len(selected), unsupported_drs=dict(Counter(str(r["drs"]) for r in selected if (sensitivity, 0, "Q", str(r["drs"])) not in fits)),
                                     retained=len(supported), laps=len({r["lap"] for r in supported}),
                                     groups=len({(r["lap"], r["drs"]) for r in supported})))
                if not supported:
                    continue
                for seed in development["seeds"]:
                    errors = defaultdict(list)
                    outside = Counter()
                    for r in supported:
                        speed, observed, drs = r["speed_mid_mps"], r["acceleration_mps2"], str(r["drs"])
                        pred = {"constant": median(m["mean_a"] for m in fits[sensitivity, seed, "Q", drs])}
                        for arm in arms:
                            source = [m["fit"] for m in fits[sensitivity, seed, arm, drs]]
                            pred[arm] = median((f["effective_total_power_w"] / speed - f["drag_coefficient_kg_per_m"] * speed**2) / f["assumed_mass_kg"] for f in source)
                            outside[arm] += not all(f["speed_min_m_per_s"] <= speed <= f["speed_max_m_per_s"] for f in source)
                        writer.writerow(dict(event=name, filter=sensitivity, seed=seed, lap=r["lap"], drs=drs,
                                             start_utc=r["start_utc"], speed=speed, observed=observed, **pred))
                        for arm, value in pred.items():
                            errors[arm, r["lap"], drs].append((value - observed)**2)
                    group_rmse = defaultdict(list)
                    for (arm, lap, drs), squares in errors.items():
                        group_rmse[arm].append(math.sqrt(mean(squares)))
                    scores.append(dict(event=name, filter=sensitivity, seed=seed, rmse={a: mean(v) for a,v in group_rmse.items()},
                                       outside_fraction={a: outside[a] / len(supported) for a in arms}))
    save(args.output / "metrics.json", dict(coverage=coverage, lap_audits=lap_audits, scores=scores))
    plot(scores, protocol["events"], arms, args.figures)
    for path, digest in digests.items():
        verified(path, digest)
    save(args.output / "manifest.json", dict(inputs=digests, sources=sources,
         outputs={str(p): sha(p) for directory in (args.output, args.figures) for p in directory.iterdir() if p.is_file()}))
    print(json.dumps(dict(coverage=coverage, primary=[r for r in scores if r["filter"] == "primary" and r["seed"] == 0])))


if __name__ == "__main__":
    main()
