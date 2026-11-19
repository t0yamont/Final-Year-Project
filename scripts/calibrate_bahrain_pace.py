"""Fit effective Sakhir physics on one development lap, then score separate laps."""
import argparse
import csv
import gzip
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import least_squares

from bahrain_pace_model import free_lap, geometry, limits
from benchmark_circuit_control import save, sha


PROTOCOL = Path("configs/bahrain_pace_protocol.json")
PLOT_FRACTION = np.linspace(0., 1., 551)


def read(path):
    return json.loads(Path(path).read_bytes())


def load_lap(root, number, metadata):
    path = root/f"lap-{number}.csv"
    if sha(path) != metadata["laps"][str(number)]["csv_sha256"]:
        raise ValueError(f"Changed input {path}")
    return np.genfromtxt(path, names=True, delimiter=",")


def vehicle_defaults(phase, start):
    study = read("configs/regeneration_study.json")
    ref = read(study["reference_config"])
    return dict(geometry=ref["geometry"], geometry_sha256=ref["geometry_sha256"], line_offset_fraction=phase,
        vehicle=ref["vehicle"].copy(), lateral_base_mps2=ref["lateral_acceleration_mps2"], lateral_aero_per_m=0.,
        max_speed_mps=ref["max_speed_mps"], initial_speed_mps=start, initial_energy_j=ref["initial_energy_j"],
        reserve_j=ref["reserve_j"], regeneration=study["regeneration"], drs_blocks=[False]*55, drs_drag_factor=1.)


def fitted_model(start, params):
    lateral, aero, brake, power_kw, drag, drs = map(float, params)
    return dict(start, lateral_base_mps2=lateral, lateral_aero_per_m=aero, drs_drag_factor=drs,
                vehicle=dict(start["vehicle"], friction_deceleration_m_per_s2=brake, base_power_w=power_kw*1000, drag_kg_per_m=drag))


def prediction(model, cells, fraction, action):
    # Exact propagation of v³ at constant wheel power and quadratic drag in distance coordinates.
    # The braking and corner ceilings apply at the same nodes as the subsequent event replay.
    grid, envelope, drag = limits(model, cells)
    k = np.repeat(drag, cells)
    vehicle = model["vehicle"]
    total = vehicle["base_power_w"] + action*vehicle["electrical_limit_w"]
    ds = grid.lengths_m
    weight = -np.expm1(-3*k*ds/vehicle["mass_kg"])
    cube = model["initial_speed_mps"]**3
    v3 = np.empty(len(ds)+1)
    v3[0] = cube
    cap3 = np.minimum(envelope[1:],grid.cell_speed_cap_mps)**3
    for i, (keep, add, limit) in enumerate(zip(1-weight, weight*total/k, cap3)):
        cube = min(keep*cube+add, limit)
        v3[i+1] = cube
    speed = np.cbrt(v3)
    time = np.r_[0.,np.cumsum(2*ds/(speed[:-1]+speed[1:]))]
    x = grid.distance_m/grid.distance_m[-1]
    return np.interp(fraction,x,speed), np.interp(fraction,x,time)


def observed(lap):
    return (np.interp(PLOT_FRACTION,lap["fraction"],lap["speed_mps"]),
            np.interp(PLOT_FRACTION,lap["fraction"],lap["time_s"]))


def assess(lap, info, speed, time, boundaries):
    v, t = observed(lap)
    sectors = np.diff(np.interp(boundaries,PLOT_FRACTION,time))
    error = speed-v
    brake = np.interp(PLOT_FRACTION,lap["fraction"],lap["brake"]) > .5
    throttle = np.interp(PLOT_FRACTION,lap["fraction"],lap["throttle"])
    drs = np.isin(lap["drs"],[10,12,14])
    opened = np.interp(PLOT_FRACTION,lap["fraction"],drs.astype(float))>.5
    masks = {"braking":brake,"slow_observed_under_45_mps":v<45,"full_throttle_drs_open":(throttle>=95)&opened,
             "full_throttle_drs_closed":(throttle>=95)&~opened}
    for name, mask in list(masks.items()):
        if not np.any(mask):
            del masks[name]
    return dict(lap_s=float(time[-1]), observed_s=info["duration_s"], lap_error_s=float(time[-1]-info["duration_s"]),
        sector_prediction_s=sectors.tolist(), sector_error_s=(sectors-info["sector_times_s"]).tolist(),
        speed_rmse_mps=float(np.sqrt(np.mean(error**2))), mean_speed_bias_mps={k:float(error[m].mean()) for k,m in masks.items()},
        cumulative_time_error_s=(time-t).tolist(), measured_boundary_bias_m=np.round(
        (np.asarray(boundaries)-np.array(info["sector_boundary_fractions"]))*info["integrated_distance_m"],1).tolist())


def historic_profile(protocol, metadata):
    folder = Path(protocol["historic"])
    manifest = read(folder/"manifest.json")
    for hashes in manifest.values():
        for p,digest in hashes.items():
            if sha(p)!=digest:
                raise ValueError(f"Changed parent {p}")
    path = folder/"w64_cells160.json.gz"
    with gzip.open(path,"rt") as stream:
        parent = json.load(stream)
    old = vehicle_defaults(0.,70.)
    trace = free_lap(old,160,[b["action"] for b in parent["trace"]])
    if abs(trace[-1,1]-parent["duration_s"])>1e-6:
        raise ValueError("Original 107 s schedule failed exact replay")
    grid = geometry(old["geometry"],old["geometry_sha256"],0.,160)
    line = np.interp(metadata["timing_line_offset_fraction"]*grid.parameter_m[-1],grid.parameter_m,grid.distance_m)/grid.distance_m[-1]
    fraction = trace[:,0]/trace[-1,0]
    query = PLOT_FRACTION+line
    speed = np.interp(query%1,fraction,trace[:,2])
    time = np.interp(query%1,fraction,trace[:,1])+np.floor(query)*trace[-1,1]-np.interp(line,fraction,trace[:,1])
    return speed,time


def profile_figure(path, lap, info, profiles, length, boundaries):
    fig,axes = plt.subplots(2,1,figsize=(10,6),sharex=True)
    v,t = observed(lap)
    x = PLOT_FRACTION*length/1000
    axes[0].plot(x,v*3.6,color="#252525",label="Observed",lw=1.5)
    for label, (speed,time), color in profiles:
        axes[0].plot(x,speed*3.6,color=color,label=label,lw=1.3)
        axes[1].plot(x,time-t,color=color,label=label,lw=1.5)
    for ax in axes:
        for b in boundaries[1:-1]:
            ax.axvline(b*length/1000,ls=":",lw=1,color="#777")
        ax.grid(axis="y",alpha=.2)
        ax.legend(fontsize=8)
    axes[1].axhline(0,color="#555",lw=.7)
    axes[0].set_ylabel("Speed (km/h)")
    axes[1].set(ylabel="Simulated minus observed time (s)",xlabel="Distance from timing line on model path (km)")
    axes[0].set_title(f"Bahrain qualifying, driver 1, lap {info} | dotted lines mark sector boundaries")
    fig.tight_layout()
    for ext in ["png","pdf"]:
        fig.savefig(path.with_suffix("."+ext),dpi=300)
    plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnose",action="store_true")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--figures",type=Path,required=True)
    args=parser.parse_args()
    p=read(PROTOCOL)
    source=Path(p["inputs"]); metadata=read(source/"metrics.json")
    if metadata["calibration_laps"]!=p["fit_laps"] or metadata["holdout_laps"]!=p["check_laps"]:
        raise ValueError("Data roles changed")
    fit_id=p["fit_laps"][0]; lap=load_lap(source,fit_id,metadata)
    info=metadata["laps"][str(fit_id)]; boundaries=metadata["sector_boundary_fractions"]
    args.output.mkdir(parents=True,exist_ok=False); args.figures.mkdir(parents=True,exist_ok=False)
    inputs={str(path):sha(path) for path in [PROTOCOL,source/"metrics.json",source/f"lap-{fit_id}.csv",Path(p["historic"])/"manifest.json",Path("configs/circuit_reference.json"),Path("configs/regeneration_study.json")]}
    code={str(path):sha(path) for path in [Path(__file__),Path("scripts/bahrain_pace_model.py"),Path("scripts/benchmark_circuit_control.py"),
        *[Path("src/f1energy")/f for f in ["circuit_control.py","circuit.py","power_lap.py","event_power_lap.py"]]]}
    save(args.output/"contract.json",dict(protocol=p,inputs=inputs,sources=code))
    start=vehicle_defaults(metadata["timing_line_offset_fraction"],metadata["rolling_line_speed_mps"])
    g=geometry(start["geometry"],start["geometry_sha256"],start["line_offset_fraction"],80)
    length=float(g.distance_m[-1])
    if args.diagnose:
        speed,time=historic_profile(p,metadata)
        save(args.output/"historical.json",dict(speed_mps=speed.tolist(),time_s=time.tolist(),fraction=PLOT_FRACTION.tolist()))
        metric=assess(lap,info,speed,time,boundaries)
        save(args.output/"metrics.json",metric)
        profile_figure(args.figures/"01_historic_gap",lap,fit_id,[("Historical best schedule",(speed,time),"#ab501b")],length,boundaries)
        print({k:v for k,v in metric.items() if k!="cumulative_time_error_s"},flush=True)
    else:
        calibrate(args,p,source,metadata,lap,info,boundaries,start,length,inputs)
    if any(sha(k)!=v for k,v in (inputs|code).items()):
        raise ValueError("Inputs or code changed during study")
    save(args.output/"manifest.json",dict(inputs=inputs,sources=code,outputs={str(f):sha(f) for folder in (args.output,args.figures) for f in folder.iterdir() if f.is_file()}))


def calibrate(args,p,source,metadata,lap,info,boundaries,start,length,inputs):
    history=Path("results/bahrain-pace-diagnosis-001/historical.json")
    inputs[str(history)]=sha(history)
    historical=read(history)
    historic=(np.array(historical["speed_mps"]),np.array(historical["time_s"]))
    # Declare the active drag regime from development DRS status on each fixed block.
    start["drs_blocks"]=[bool(np.isin(lap["drs"][(lap["fraction"]>=i/55)&(lap["fraction"]<(i+1)/55)], [10,12,14]).mean()>.5) for i in range(55)]
    action=p["reference_action"]; cells=p["fit_cells_per_block"]
    x=np.linspace(0,1,221)
    target=np.interp(x,lap["fraction"],lap["speed_mps"])
    initial=np.array([20.,.003,20.,480.,.9,.85])
    scale=np.array([6.,.003,8.,80.,.2,.12])
    lo,hi=np.array(list(p["bounds"].values())).T
    def residual(params):
        speed,time=prediction(fitted_model(start,params),cells,np.r_[x,boundaries],action)
        sectors=np.diff(time[len(x):])
        return np.r_[(speed[:len(x)]-target)/4, (sectors-info["sector_times_s"])*2, .4*(params-initial)/scale]
    fit=least_squares(residual,initial,bounds=(lo,hi),x_scale=scale,loss="soft_l1",max_nfev=90)
    model=fitted_model(start,fit.x)
    save(args.output/"model.json",model)
    save(args.output/"fit.json",dict(success=bool(fit.success),message=fit.message,params=fit.x.tolist(),parameter_names=list(p["bounds"]),
         nfev=fit.nfev,active_bounds=fit.active_mask.tolist(),cost=float(fit.cost),model_sha256=sha(args.output/"model.json")))
    print("Model frozen before separate-lap scoring",fit.x,flush=True)
    profiles={}
    for n in (80,160,320):
        tr=free_lap(model,n,action)
        frac=tr[:,0]/tr[-1,0]
        profiles[n]=(np.interp(PLOT_FRACTION,frac,tr[:,2]),np.interp(PLOT_FRACTION,frac,tr[:,1]))
    speed,time=profiles[160]
    approx_v, approx_t=prediction(model,cells,PLOT_FRACTION,action)
    grid_error=abs(time[-1]-profiles[320][1][-1]); thresholds=p["assessment"]
    fitid=p["fit_laps"][0]; results={}
    for n in [fitid,*p["check_laps"]]:
        obs=load_lap(source,n,metadata); inputs[str(source/f"lap-{n}.csv")]=sha(source/f"lap-{n}.csv")
        measured=metadata["laps"][str(n)]
        old=assess(obs,measured,*historic,boundaries); revised=assess(obs,measured,speed,time,boundaries)
        checks=dict(lap=abs(revised["lap_error_s"])<=thresholds["absolute_lap_error_s"],
            sectors=max(map(abs,revised["sector_error_s"]))<=thresholds["absolute_each_sector_error_s"],
            speed=revised["speed_rmse_mps"]<=thresholds["speed_rmse_mps"],
            grid=bool(grid_error<=thresholds["absolute_grid_time_change_s"]),
            finish=bool(abs(speed[-1]-model["initial_speed_mps"])<1e-5))
        results[n]=dict(role="fit" if n==fitid else "separate_lap",historical=old,revised=revised,checks=checks)
        profile_figure(args.figures/f"lap-{n}",obs,n,[("Historical best",historic,"#ab501b"),("Revised quarter request",(speed,time),"#11718b")],length,boundaries)
    with (args.output/"speed_time.csv").open("w",newline="",encoding="utf-8") as stream:
        writer=csv.writer(stream);writer.writerow(["fraction","distance_m","historical_speed_mps","historical_time_s","calibrated_speed_mps","calibrated_time_s"])
        writer.writerows(zip(PLOT_FRACTION,PLOT_FRACTION*length,*historic,speed,time))
    summary=dict(laps=results,model_length_m=length,fit_surrogate_time_difference_s=float(approx_t[-1]-time[-1]),
        fit_surrogate_speed_difference_rms_mps=float(np.sqrt(np.mean((approx_v-speed)**2))),grid_error_s=float(grid_error),
        all_heldout_checks_passed=all(all(results[n]["checks"].values()) for n in p["check_laps"]))
    save(args.output/"metrics.json",summary)
    print("Held-out gates",summary["all_heldout_checks_passed"],flush=True)


if __name__=="__main__":
    main()
