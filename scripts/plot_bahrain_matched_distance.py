"""Show where the two work-matched deployment comparisons gain or lose time."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from benchmark_circuit_control import save, sha
from verify_bahrain_deployment import read


def curves(path):
    lap = read(path)
    if not lap["feasible"] or len(lap["trace"]) != 55:
        raise ValueError(f"Expected a feasible 55-block replay in {path}")
    states = [block["state"] for block in lap["trace"]]
    distance = np.r_[0., [s["distance_m"] for s in states]]
    time = np.r_[0., [s["elapsed_s"] for s in states]]
    work = np.r_[0., np.cumsum([b["electrical_work_j"] for b in lap["trace"]])] / 1000
    return distance, time, work


def main():
    root = Path("results/bahrain-equal-work-001")
    output = root / "location"
    stem = Path("figures/dissertation/bahrain-equal-work-v1/03_bahrain_matched_by_distance")
    sector_file = Path("results/bahrain-pace-inputs-001/metrics.json")
    sectors = np.asarray(read(sector_file)["sector_boundary_fractions"])
    inputs = {str(sector_file): sha(sector_file)}
    results = {}
    fig, axes = plt.subplots(2, 1, figsize=(9, 5.5), sharex=True)
    for folder, target_key, label, color in [(root, "archived", "Higher work target", "#126179"),
                                             (root / "secondary", "reference", "Lower work target", "#a2531b")]:
        path = folder / "metrics.json"
        manifest = read(folder / "manifest.json")
        inputs[str(path)] = sha(path)
        if inputs[str(path)] != manifest["outputs"][str(path)]:
            raise ValueError(f"Changed work comparison {path}")
        study = read(path)
        matched, = [c for c in study["comparisons"] if c["matched_primary"]]
        for grid in ("160", "320"):
            fixed = study[target_key][grid]["file"]
            varied = matched[grid]["file"]
            selected, spread = (fixed, varied) if target_key == "archived" else (varied, fixed)
            for filename in (selected, spread):
                inputs[filename] = sha(filename)
                if inputs[filename] != (manifest["inputs"] | manifest["outputs"])[filename]:
                    raise ValueError(f"Changed lap {filename}")
            distance, selected_time, selected_work = curves(selected)
            other_distance, spread_time, spread_work = curves(spread)
            np.testing.assert_allclose(distance, other_distance, atol=1e-6, rtol=0)
            gain = spread_time - selected_time
            extra_work = selected_work - spread_work
            np.testing.assert_allclose(gain[-1], matched[grid]["feasible_gain_s"], atol=1e-8)
            if abs(extra_work[-1]) > .5:
                raise ValueError("Work mismatch exceeds 0.5 kJ")
            boundaries = sectors * distance[-1]
            crossing_gain = np.interp(boundaries, distance, gain)
            results[f"{label}, {grid}"] = dict(sector_gain_s=np.diff(crossing_gain).tolist(),
                cumulative_gain_s=crossing_gain.tolist(), end_wheel_work_difference_kj=float(extra_work[-1]),
                maximum_block_end_lead_s=float(max(gain)), station_of_maximum_m=float(distance[gain.argmax()]))
            if grid == "160":
                axes[0].plot(distance / 1000, extra_work, color=color, label=label)
                axes[1].plot(distance / 1000, gain, color=color)
    for ax in axes:
        for boundary in boundaries[1:-1]:
            ax.axvline(boundary / 1000, color="#777", ls=":", lw=1)
        ax.axhline(0, lw=.7, color="#444")
        ax.grid(axis="y", alpha=.2)
    axes[0].legend(fontsize=8)
    axes[0].set(ylabel="Extra wheel work used by\nselected schedule (kJ)", title="Bahrain deployment at matched total wheel work")
    axes[1].set(xlabel="Distance from timing line (km) · dotted lines mark sector boundaries",
                ylabel="Time saved against spread (s)")
    fig.tight_layout()
    output.mkdir(exist_ok=False)
    for ext in (".png", ".pdf"):
        fig.savefig(stem.with_suffix(ext), dpi=300)
    plt.close(fig)
    save(output / "metrics.json", results)
    files = [output / "metrics.json", stem.with_suffix(".png"), stem.with_suffix(".pdf")]
    save(output / "manifest.json", dict(inputs=inputs, sources={str(Path(__file__)): sha(__file__)},
         outputs={str(p): sha(p) for p in files}))
    print(results)


if __name__ == "__main__":
    main()
