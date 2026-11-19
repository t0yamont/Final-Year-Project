"""Bounded descriptive path check; no fitting, telemetry acquisition or simulation."""
import hashlib
import json
import os
from pathlib import Path
import time

os.environ.setdefault('MPLBACKEND', 'Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bahrain_pace_model import registered_curve

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/bahrain-corner-paths-001'
FIG = ROOT / 'figures/dissertation/bahrain-corner-paths-v1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def arc(xy):
    return np.r_[0., np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]


def interpolate(s, xy, q):
    return np.stack([np.interp(q, s, xy[:, j]) for j in range(2)], axis=-1)


def project(points, xy, s):
    delta = np.diff(xy, axis=0)
    weight = np.clip(np.sum((points[:, None, :] - xy[:-1]) * delta, axis=2) /
                     np.sum(delta**2, axis=1), 0, 1)
    closest = xy[:-1] + weight[:, :, None] * delta
    residual = np.linalg.norm(points[:, None, :] - closest, axis=2)
    index = np.argmin(residual, axis=1)
    w = weight[np.arange(len(points)), index]
    return s[index] + w * np.diff(s)[index], residual[np.arange(len(points)), index]


def curvature(s, xy, q, halfspan):
    a, b, c = [interpolate(s, xy, q + offset) for offset in (-halfspan, 0, halfspan)]
    u, v = b - a, c - a
    cross = u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]
    return 2 * cross / (np.linalg.norm(u, axis=1) * np.linalg.norm(c - b, axis=1) * np.linalg.norm(v, axis=1))


def main():
    started = time.perf_counter()
    assert not (OUT / 'manifest.json').exists(), 'Preserve the existing run; select a new output version.'
    # Exact circumcircle identity is independent of resampling and tested against a known radius.
    theta = np.linspace(0, np.pi, 10001)
    circle = 50 * np.column_stack([np.cos(theta), np.sin(theta)])
    assert np.max(np.abs(curvature(arc(circle), circle, np.array([50., 75.]), 20) - .02)) < 1e-8
    straight = np.column_stack([np.arange(201.), np.zeros(201)])
    assert np.all(curvature(arc(straight), straight, np.array([50., 75.]), 20) == 0)
    paths = {name: ROOT / relative for name, relative in {
        'registration': 'results/bahrain-pace-inputs-001/metrics.json',
        'positions': 'results/openf1-dataset-003/development/1257/10010/driver-1-position.csv.gz',
        'speed': 'results/bahrain-pace-inputs-001/lap-13.csv',
        'geometry': 'results/circuit-input-assessment-001/Sakhir.csv',
        'landmarks': 'configs/bahrain_turn_landmarks.json',
        'calibrated_speed': 'results/bahrain-pace-calibration-001/speed_time.csv',
        'model': 'results/bahrain-pace-calibration-001/model.json',
        'reference_config': 'configs/circuit_reference.json',
        'previous_corner_checks': 'results/bahrain-pace-mechanisms-001/corner_checks.json',
    }.items()}
    meta, config, model = [load(paths[name]) for name in ('registration', 'reference_config', 'model')]
    assert digest(paths['positions']) == meta['provenance']['acquisition_output_sha256']['driver-1-position.csv.gz']
    assert digest(paths['geometry']) == model['geometry_sha256'] == config['geometry_sha256']
    assert digest(paths['speed']) == meta['laps']['13']['csv_sha256']
    reg, lap = meta['alignment'], meta['laps']['13']
    position, speed, simulation = [pd.read_csv(paths[name]) for name in ('positions', 'speed', 'calibrated_speed')]
    native_time = (pd.to_datetime(position.date) - pd.Timestamp(lap['date_start'])).dt.total_seconds().to_numpy()
    inside = (native_time >= 0) & (native_time <= lap['duration_s'])
    times = native_time[inside]
    xy = (position.loc[inside, ['x', 'y']].to_numpy() * .1 @ np.array(reg['rotation_openf1_to_reference']) *
          reg['scale_reference_m_per_openf1_m'] + np.array(reg['translation_to_reference_m']))
    assert np.all(np.diff(times) > 0)
    observed_s = arc(xy)
    source = np.loadtxt(paths['geometry'], delimiter=',')[:, :2]
    source = np.vstack([source, source[0]])
    source_s = arc(source)
    line = registered_curve(str(paths['geometry']), model['geometry_sha256'], model['line_offset_fraction'])
    parameter = np.linspace(0, line.source_length_m, 22001)
    smoothed = line.spline(parameter)
    smoothed_s = arc(smoothed)
    observed_fraction = np.interp(times, speed.time_s, speed.fraction)
    source_projection, residual = project(xy, source, source_s)
    native = pd.DataFrame({'time_s': times, 'x_reference_m': xy[:, 0], 'y_reference_m': xy[:, 1],
                           'path_arclength_m': observed_s, 'speed_integrated_fraction': observed_fraction,
                           'speed_kmh': np.interp(times, speed.time_s, speed.speed_mps) * 3.6,
                           'source_projected_station_m': source_projection, 'source_residual_m': residual})
    marker = {c['turn']: c for c in load(paths['landmarks'])['corners']}
    previous = {c['turn']: c for c in load(paths['previous_corner_checks'])}
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(3, 3, figsize=(12, 11))
    summaries, curves, supports = [], [], []
    colors = {'observed': '#1565a8', 'raw_reference': '#ad7827', 'smoothed_reference': '#aa275b'}
    for row, turn in enumerate((1, 8, 14)):
        mark = marker[turn]
        center_time = mark['fit_lap_time_s']
        center_s = float(np.interp(center_time, times, observed_s))
        center_xy = interpolate(observed_s, xy, np.array([center_s]))
        raw_center = float(project(center_xy, source, source_s)[0][0])
        smooth_center = float(project(center_xy, smoothed, smoothed_s)[0][0])
        local = np.abs(observed_s - center_s) <= 150
        support = native.loc[local].copy()
        support.insert(0, 'turn', turn)
        support['distance_from_marker_m'] = support.path_arclength_m - center_s
        supports.append(support)
        q = np.arange(-100., 101., 1.)
        summary = {'turn': turn, 'native_samples_within_150m': int(local.sum()),
                   'max_local_location_gap_s': float(np.diff(times[local]).max()),
                   'max_local_location_step_m': float(np.diff(observed_s[local]).max()),
                   'rms_projection_residual_m': float(np.sqrt(np.mean(residual[local]**2))),
                   'max_projection_residual_m': float(residual[local].max()),
                   'raw_reference_center_station_m': raw_center,
                   'marker_fit_lap_distance_m': mark['fit_lap_distance_m'],
                   'previous_speed_check': previous[turn], 'curvature': []}
        for name, path_s, path_xy, center in (
            ('observed', observed_s, xy, center_s),
            ('raw_reference', source_s, source, raw_center),
            ('smoothed_reference', smoothed_s, smoothed, smooth_center)):
            local_xy = interpolate(path_s, path_xy, center + np.arange(-150., 151.))
            axes[row, 0].plot(local_xy[:, 0], local_xy[:, 1], label=name.replace('_', ' '), color=colors[name])
            for halfspan in (10, 20, 40):
                k = np.abs(curvature(path_s, path_xy, center + q, halfspan))
                central = np.abs(q) <= 60
                summary['curvature'].append({'path': name, 'chord_halfspan_m': halfspan,
                    'peak_within_60m_per_m': float(k[central].max()),
                    'peak_distance_from_marker_m': float(q[central][np.argmax(k[central])])})
                curves.extend({'turn': turn, 'path': name, 'halfspan_m': halfspan,
                               'distance_from_marker_m': float(d), 'absolute_curvature_per_m': float(v)} for d, v in zip(q, k))
                if name != 'raw_reference':
                    axes[row, 1].plot(q, k, color=colors[name], alpha=.8,
                        ls={10: ':', 20: '-', 40: '--'}[halfspan], label=f'{name.split("_")[0]}, h={halfspan} m')
        axes[row, 0].scatter(xy[local, 0], xy[local, 1], s=10, color=colors['observed'], label='native locations')
        axes[row, 0].scatter(*center_xy[0], marker='x', color='black', s=40)
        axes[row, 0].set_aspect('equal', adjustable='datalim')
        axes[row, 0].set(xlabel='Registered x (m)', ylabel='Registered y (m)', title=f'T{turn}: path, ±150 m')
        axes[row, 1].set(xlabel='Own path distance from marker (m)', ylabel='Absolute curvature (1/m)', title=f'T{turn}: equal chord halfspans')
        station = mark['fraction'] * simulation.distance_m.iloc[-1]
        obs_station = speed.fraction * simulation.distance_m.iloc[-1] - station
        sim_station = simulation.distance_m - station
        axes[row, 2].plot(obs_station, speed.speed_mps * 3.6, color=colors['observed'], label='lap 13 speed')
        axes[row, 2].plot(sim_station, simulation.calibrated_speed_mps * 3.6, color=colors['smoothed_reference'], label='frozen calibrated replay')
        axes[row, 2].set(xlim=(-150, 150), ylim=(40, 220), xlabel='Frozen model progress from marker (m)', ylabel='Speed (km/h)', title=f'T{turn}: existing speed comparison')
        for ax in axes[row]:
            ax.grid(alpha=.2)
            ax.legend(fontsize=6, loc='best')
        summaries.append(summary)
    figure.suptitle('Bahrain qualifying lap 13: registered paths and scale-dependent curvature', fontsize=14)
    figure.text(.5, .008, 'bahrain-corner-paths-001 | native positions are sparse; chords interpolate, not new observations | labels ≈±50 m | no refit', ha='center', fontsize=8)
    figure.tight_layout(rect=(0, .025, 1, .97))
    for suffix in ('png', 'pdf'):
        figure.savefig(FIG / f'corner_paths.{suffix}', dpi=300)
    plt.close(figure)
    pd.concat(supports).to_csv(OUT / 'native_support.csv', index=False)
    pd.DataFrame(curves).to_csv(OUT / 'curvature_chords.csv', index=False)
    native.to_csv(OUT / 'lap13_registered_native_positions.csv', index=False)
    result = {'run_id': OUT.name, 'elapsed_s': time.perf_counter() - started,
        'scope': 'Driver1 development lap13 only. Existing frozen registration, no re-estimation or simulation.',
        'method': 'Absolute three-point circumcircle curvature at own physical arclength offsets h=10,20,40 m; peaks searched ±60 m about projected marker. Both reference paths project the same observed marker point independently.',
        'registration': reg, 'corners': summaries,
        'checks': {'known_circle_and_straight': True, 'input_hashes_match_frozen_records': True,
                   'native_locations_in_lap': len(native), 'source_length_m': float(source_s[-1]),
                   'transformed_observed_interior_length_m': float(observed_s[-1])}}
    (OUT / 'metrics.json').write_text(json.dumps(result, indent=2) + '\n')
    outputs = [OUT / name for name in ('native_support.csv', 'curvature_chords.csv',
        'lap13_registered_native_positions.csv', 'metrics.json')] + list(FIG.glob('corner_paths.*'))
    manifest = {'command': "$env:PYTHONPATH='src'; .venv/Scripts/python.exe scripts/assess_bahrain_corner_paths.py",
        'inputs_sha256': {str(p.relative_to(ROOT)): digest(p) for p in paths.values()},
        'source_sha256': {str(Path(__file__).resolve().relative_to(ROOT)): digest(Path(__file__)),
                         'scripts/bahrain_pace_model.py': digest(ROOT / 'scripts/bahrain_pace_model.py'),
                         'src/f1energy/circuit.py': digest(ROOT / 'src/f1energy/circuit.py')},
        'outputs_sha256': {str(p.relative_to(ROOT)): digest(p) for p in outputs}}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
