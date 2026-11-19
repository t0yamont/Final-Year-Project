"""Overlay grip-stable deployment windows with separate-lap motion discrepancies."""
import argparse
import csv
from itertools import groupby
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from benchmark_circuit_control import save, sha
from calibrate_bahrain_pace import read, load_lap


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=Path("results/bahrain-zone-support-001"))
    parser.add_argument("--figures",type=Path,default=Path("figures/dissertation/bahrain-zone-support-v1"))
    args=parser.parse_args()
    root=Path("results/bahrain-deployment-zones-001"); cal=Path("results/bahrain-pace-calibration-001")
    telem=Path("results/bahrain-pace-inputs-001")
    inputs={}
    for folder in (root,cal):
        man=folder/"manifest.json";inputs[str(man)]=sha(man)
        for k,v in read(man)["outputs"].items():
            if sha(k)!=v: raise ValueError(f"Changed input {k}")
    model=np.genfromtxt(cal/"speed_time.csv",delimiter=",",names=True); meta=read(telem/"metrics.json")
    observed={lap:load_lap(telem,lap,meta) for lap in meta["holdout_laps"]}
    protocol=Path("configs/bahrain_deployment_zones.json");inputs[str(protocol)]=sha(protocol)
    minimum=read(protocol)["active_min_wheel_kj"]
    profiles=[]
    for case in ["central","low_grip","high_grip"]:
        for grid in [160,320]:
            with (root/case/f"profile_{grid}.csv").open(newline="") as stream:
                selected=[row for row in csv.DictReader(stream) if row["policy"]=="selected"]
            if [int(r["block"]) for r in selected]!=list(range(1,56)): raise ValueError("Incomplete selected schedule")
            profiles.append(selected)
    active=np.all([[float(r["wheel_assist_kj"])>=minimum for r in pp] for pp in profiles],axis=0)
    fig,ax=plt.subplots(figsize=(10,3.9))
    measured={}
    for lap,obs in observed.items():
        error=model["calibrated_speed_mps"]-np.interp(model["fraction"],obs["fraction"],obs["speed_mps"])
        measured[lap]=error
        ax.plot(model["distance_m"]/1000,error,lw=1.2,label=f"Qualifying lap {lap}")
    zones=[]
    for on, sequence in groupby(enumerate(active),key=lambda item:bool(item[1])):
        blocks=[i for i,_ in sequence]
        if not on:continue
        a,b=blocks[0],blocks[-1]
        low=float(profiles[0][a]["from_m"]);high=float(profiles[0][b]["to_m"])
        select=(model["distance_m"]>=low)&(model["distance_m"]<=high)
        by_lap={str(n):float(np.sqrt(np.mean(e[select]**2))) for n,e in measured.items()}
        energy=[sum(float(prof[i]["wheel_assist_kj"]) for i in blocks) for prof in profiles]
        zones.append(dict(blocks=[a+1,b+1],from_m=low,to_m=high,local_rmse_mps=by_lap,
            min_delivered_kj=min(energy),max_delivered_kj=max(energy)))
        ax.axvspan(low/1000,high/1000,color="#49755b",alpha=.14,label="Active in all six replays" if len(zones)==1 else None)
    ax.axhline(0,color="#555",lw=.6)
    ax.set(xlabel="Distance from timing line on model path (km)",ylabel="Model minus observed speed (m/s)",
           title="Local motion error in recurring simulated deployment zones")
    ax.grid(axis="y",alpha=.2);ax.legend(fontsize=8,ncol=3,loc="upper center")
    fig.tight_layout()
    args.output.mkdir(parents=True,exist_ok=False);args.figures.mkdir(parents=True,exist_ok=False)
    for ext in ("png","pdf"):fig.savefig(args.figures/f"zone_motion_support.{ext}",dpi=300)
    plt.close(fig)
    save(args.output/"metrics.json",dict(zones=zones,recurring_blocks=int(active.sum()),
        method="Each block delivers at least the frozen 10 kJ wheel-work threshold for independently selected schedules at three grip settings and two integration resolutions. Local motion RMSE uses the frozen quarter-request free lap and the two separate real laps. Descriptive post-fit diagnostic; no real energy labels or local acceptance gate."))
    save(args.output/"manifest.json",dict(inputs=inputs,sources={str(Path(__file__)):sha(__file__)},
         outputs={str(p):sha(p) for folder in (args.output,args.figures) for p in folder.iterdir() if p.is_file()}))
    print(zones)


if __name__=="__main__":main()
