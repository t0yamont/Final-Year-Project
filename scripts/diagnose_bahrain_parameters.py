"""Development-lap mechanisms behind the pace change, with the same requested assistance."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from bahrain_pace_model import build_env, free_lap
from benchmark_circuit_control import save, sha
from calibrate_bahrain_pace import load_lap, read, vehicle_defaults


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=Path("results/bahrain-pace-mechanisms-001"))
    parser.add_argument("--figures",type=Path,default=Path("figures/dissertation/bahrain-pace-mechanisms-v1"))
    args=parser.parse_args()
    source=Path("results/bahrain-pace-inputs-001")
    parent=Path("results/bahrain-pace-calibration-001")
    m=read(parent/"model.json"); meta=read(source/"metrics.json")
    protocol=read("configs/bahrain_pace_protocol.json")
    trn=protocol["fit_laps"][0]; lap=load_lap(source,trn,meta)
    geo=read("configs/bahrain_turn_landmarks.json")
    orig=vehicle_defaults(m["line_offset_fraction"],m["initial_speed_mps"])
    action=protocol["reference_action"]; s=meta["sector_boundary_fractions"]
    base=m["vehicle"]; old=orig["vehicle"]
    models={"Calibrated":m,"Original limits":orig,
            "Original cornering":dict(m,lateral_base_mps2=orig["lateral_base_mps2"],lateral_aero_per_m=0.),
            "Original braking":dict(m,vehicle=dict(base,friction_deceleration_m_per_s2=old["friction_deceleration_m_per_s2"])),
            "Original power and drag":dict(m,vehicle=dict(base,base_power_w=old["base_power_w"],drag_kg_per_m=old["drag_kg_per_m"]),drs_drag_factor=1.),
            "No DRS drag reduction":dict(m,drs_drag_factor=1.)}
    rows=[]
    args.output.mkdir(parents=True,exist_ok=False); args.figures.mkdir(parents=True,exist_ok=False)
    inputs={str(p):sha(p) for p in [source/"metrics.json",source/f"lap-{trn}.csv",parent/"manifest.json",parent/"model.json",
               Path("configs/bahrain_pace_protocol.json"),Path("configs/bahrain_turn_landmarks.json")]}
    for label,mdl in models.items():
        profile=free_lap(mdl,80,action)
        x=profile[:,0]/profile[-1,0]
        rows.append(dict(case=label,lap_s=float(profile[-1,1]),sectors_s=np.diff(np.interp(s,x,profile[:,1])).tolist(),
                    finish_speed_error_mps=float(profile[-1,2]-mdl["initial_speed_mps"])))
    save(args.output/"parameter_replays.json",rows)
    # Compare native brake onset before isolated major turns; a binary telemetry brake signal
    # and required simulated mechanical braking are measurements at different interfaces.
    env=build_env(m,160,cellwise=True)
    env.reset(); v=[env.initial_speed]; braking=[]; energy=[]
    for _ in range(env.blocks):
        _,_,_,_,b=env.step([action]); v.append(env.state.speed_m_per_s)
        braking.append(b["friction_braking_work_j"]+b["regenerative_braking_work_j"]>1.)
        energy.append(b["electrical_work_j"])
    length=env.grid.distance_m[-1]; x=env.grid.distance_m/length
    obs_x=lap["fraction"]; obs_v=lap["speed_mps"]
    diagnostics=[]
    for mark in geo["corners"]:
        if mark["turn"] not in [1,4,8,10,14]:
            continue
        station=mark["fraction"]*length
        measures={}
        for name,axis,speed,br in [("observed",obs_x*length,obs_v,lap["brake"]>0),
                                    ("model",x[:-1]*length,np.array(v[:-1]),np.array(braking))]:
            win=np.flatnonzero(abs(axis-station)<=80)
            if not len(win):
                continue
            apex=win[np.argmin(speed[win])]
            approach=np.flatnonzero((axis>=station-250)&(axis<=axis[apex])&br)
            measures[name]=dict(minimum_speed_mps=float(speed[apex]),minimum_station_m=float(axis[apex]),
                exit_100m_mps=float(np.interp((station+100)%length,axis,speed)),
                first_brake_within_250m_station_m=float(axis[approach[0]]) if len(approach) else None)
        diagnostics.append(dict(turn=mark["turn"],marker_station_m=station,**measures))
    save(args.output/"corner_checks.json",diagnostics)
    fig,axes=plt.subplots(1,2,figsize=(11,4.6))
    differences=[r["lap_s"]-rows[0]["lap_s"] for r in rows[1:]]
    axes[0].barh(range(len(differences)),differences,color="#287286")
    axes[0].set(yticks=range(len(differences)),yticklabels=[r["case"] for r in rows[1:]],xlabel="Change in traversal time (s)",title="Restoring earlier assumptions")
    axes[0].axvline(0,color="#333",lw=.8); axes[0].invert_yaxis()
    for name,marker,color in [("observed","o","#272727"),("model","s","#b35b1c")]:
        axes[1].scatter(range(len(diagnostics)),[r[name]["minimum_speed_mps"]*3.6 for r in diagnostics],marker=marker,color=color,label=name.capitalize())
    axes[1].set(xticks=range(len(diagnostics)),xticklabels=[f"T{r['turn']}" for r in diagnostics],ylabel="Local minimum speed (km/h)",title="Development lap at major braking zones")
    axes[1].legend()
    for ax in axes:ax.grid(axis="x" if ax==axes[0] else "y",alpha=.2)
    fig.text(.5,.015,"Fixed quarter deployment; traversal times include any finish-speed misses. Effects interact and cannot be summed.",ha="center",fontsize=8)
    fig.tight_layout(rect=(0,.05,1,1))
    for ext in ("png","pdf"):fig.savefig(args.figures/f"pace_mechanisms.{ext}",dpi=300)
    plt.close(fig)
    save(args.output/"manifest.json",dict(inputs=inputs,sources={str(Path(__file__)):sha(__file__)},
        outputs={str(f):sha(f) for folder in (args.output,args.figures) for f in folder.iterdir() if f.is_file()}))
    print([(r["case"],round(r["lap_s"],3),round(r["finish_speed_error_mps"],3)) for r in rows])


if __name__=="__main__":
    main()
