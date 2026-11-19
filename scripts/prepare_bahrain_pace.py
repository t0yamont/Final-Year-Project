"""Prepare frozen Bahrain pace-calibration inputs from checked offline acquisition."""
from datetime import datetime
import json
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import numpy as np
from scipy.optimize import minimize_scalar

from acquire_openf1_dataset import digest, save_json, verify_outputs
from f1energy.openf1 import OpenF1Client, normalise_car_data

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'results/bahrain-pace-inputs-001'
SOURCE = ROOT / 'results/openf1-dataset-003/development/1257/10010'
REFERENCE = ROOT / 'results/circuit-input-assessment-001/Sakhir.csv'


def load(path):
    return json.loads(path.read_text())


def stamp(value):
    return datetime.fromisoformat(value).timestamp()


def arc_length(xy):
    return np.r_[0., np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]


def resample(times, values, query):
    return np.stack([np.interp(query, times, channel) for channel in values.T], axis=-1)


def timing_alignment(lap, positions, geometry):
    start = stamp(lap['date_start'])
    duration = lap['lap_duration']
    nearby = [(stamp(row['date']) - start, [float(row[k]) * .1 for k in ('x', 'y')])
              for row in positions if start - 2 <= stamp(row['date']) <= start + duration + 2]
    times, xy = np.array([row[0] for row in nearby]), np.array([row[1] for row in nearby])
    assert np.all(np.diff(times) > 0) and times[0] <= 0 and times[-1] >= duration
    active = np.r_[0., times[(times > 0) & (times < duration)], duration]
    observed = resample(times, xy, active)
    distance = arc_length(observed)
    closed = np.vstack([geometry, geometry[0]])
    source_distance = arc_length(closed)
    grid = np.arange(512) / 512
    trace = resample(distance / distance[-1], observed, grid)
    centered_trace = trace - trace.mean(axis=0)
    trace_norm_sq = np.sum(centered_trace ** 2)

    def fit(offset, direction, handedness):
        query = (offset + direction * grid) % 1.
        target = resample(source_distance / source_distance[-1], closed, query)
        centered = target - target.mean(axis=0)
        u, _, vt = np.linalg.svd(centered_trace.T @ centered)
        rotation = u @ np.diag([1., handedness * np.linalg.det(u @ vt)]) @ vt
        rotated = centered_trace @ rotation
        scale = np.sum(rotated * centered) / trace_norm_sq
        residual = np.linalg.norm(scale * rotated - centered, axis=1)
        translation = target.mean(axis=0) - scale * trace.mean(axis=0) @ rotation
        return float(np.sqrt(np.mean(residual ** 2))), scale, rotation, translation, residual

    alternatives = []
    for direction in (1, -1):
        for handedness in (1, -1):
            rms = lambda phase: fit(phase, direction, handedness)[0]
            guess = min(np.arange(256) / 256., key=rms)
            result = minimize_scalar(rms, bounds=(guess - 1/256, guess + 1/256),
                                     method='bounded', options={'xatol': 1e-10})
            alternatives.append({'phase_fraction': result.x % 1., 'rmse_m': result.fun,
                                 'direction': direction, 'handedness': handedness})
    best, runner_up, *_ = sorted(alternatives, key=lambda result: result['rmse_m'])
    offset = best['phase_fraction']
    rms, scale, rotation, translation, residual = fit(offset, best['direction'], best['handedness'])
    # Project both transformed edges onto the dense raw centreline as a phase check.
    check_grid = np.arange(16384) / 16384
    support = resample(source_distance / source_distance[-1], closed, check_grid)
    endpoints = scale * observed[[0, -1]] @ rotation + translation
    projected = [float(check_grid[np.argmin(np.linalg.norm(support - p, axis=1))]) for p in endpoints]
    assert best['direction'] == 1 and .9 < scale < 1.1 and rms < 30 and runner_up['rmse_m'] > 2 * rms
    return {'method': 'XY arclength phase search with fitted rotation, translation and common scale',
            'selected': best, 'alternatives': alternatives,
            'scale_reference_m_per_openf1_m': scale, 'rotation_openf1_to_reference': rotation.tolist(),
            'translation_to_reference_m': translation.tolist(),
            'p95_residual_m': float(np.quantile(residual, .95)),
            'max_residual_m': float(residual.max()), 'edge_closure_m': float(np.linalg.norm(observed[-1] - observed[0])),
            'edge_projection_fractions': projected, 'source_length_m': float(source_distance[-1]),
            'location_length_m': float(distance[-1]), 'location_max_gap_s': float(np.diff(active).max()),
            'location_native_samples': len(active) - 2,
            'location_edge_brackets_s': [times[np.searchsorted(times, value) - 1:np.searchsorted(times, value) + 1].tolist()
                                        for value in (0., duration)]}


def prepare_lap(lap, car, max_gap):
    t0 = stamp(lap['date_start'])
    duration = lap['lap_duration']
    raw = [row for row in car if t0 - 2 <= stamp(row['date']) <= t0 + duration + 2]
    samples, qc = normalise_car_data(raw)
    assert qc['passed']
    native = np.array([round(stamp(row['date_utc']) - t0, 6) for row in samples])
    first = np.searchsorted(native, 0., side='right') - 1
    last = np.searchsorted(native, duration)
    assert first >= 0 and last < len(native)
    gap = np.diff(native[first:last+1]).max()
    assert gap <= max_gap
    interior = native[(native > 0) & (native < duration)]
    times = np.r_[0., interior, duration]
    source_speed = [row['speed_mps'] for row in samples]
    speeds = np.interp(times, native, source_speed)
    previous = np.searchsorted(native, times, side='right') - 1
    controls = np.array([[int(row['brake']), row['throttle_pct'], row['drs']] for row in samples])[previous]
    distance = np.r_[0., np.cumsum(np.diff(times) * (speeds[:-1] + speeds[1:]) / 2)]
    sector_times = [lap[f'duration_sector_{j}'] for j in range(1, 4)]
    assert all(s > 0 for s in sector_times) and abs(sum(sector_times) - duration) <= .002
    boundaries = np.r_[0., np.cumsum(sector_times)[:2], duration]
    i = np.searchsorted(times, boundaries, side='right').clip(1, len(times) - 1) - 1
    v = np.interp(boundaries, times, speeds)
    sector_dist = distance[i] + (boundaries - times[i]) * (speeds[i] + v) / 2
    fraction = distance / distance[-1]
    assert np.all(np.diff(fraction) > 0) and fraction[0] == 0 and fraction[-1] == 1
    values = np.column_stack([fraction, times, speeds, controls])
    record = {'date_start': lap['date_start'], 'duration_s': duration, 'sector_times_s': sector_times,
              'sector_boundary_distances_m': sector_dist.tolist(), 'sector_distances_m': np.diff(sector_dist).tolist(),
              'sector_boundary_fractions': (sector_dist / distance[-1]).tolist(),
              'integrated_distance_m': float(distance[-1]), 'native_interior_samples': len(interior),
              'max_bracketing_native_gap_s': float(gap), 'edge_speeds_mps': speeds[[0, -1]].tolist(),
              'edge_brackets_s': [native[first:first+2].tolist(), native[last-1:last+1].tolist()]}
    return record, values


def main():
    split = load(OUTPUT / 'split.json')
    complete = load(SOURCE / 'complete.json')
    verify_outputs(SOURCE, complete)
    reference_config = load(ROOT / 'configs/circuit_reference.json')
    assert digest(REFERENCE) == reference_config['geometry_sha256']
    audit = load(SOURCE / 'driver-1-laps.json')
    assert sorted(n for n in split['calibration_laps'] + split['holdout_laps']) == sorted(
        row['lap_number'] for row in audit if row['conditional_motion_candidate'])
    requests = load(SOURCE / 'requests.json')
    client = OpenF1Client(ROOT / 'work/source-audit-openf1', offline=True)
    cached = {'laps': [], 'car_data': [], 'location': []}
    for request in requests:
        url = urlsplit(request['url'])
        endpoint = url.path.rsplit('/', 1)[-1]
        params = dict(parse_qsl(url.query))
        if params.get('driver_number') == '1' and endpoint in cached:
            cached[endpoint].extend(client.fetch(endpoint, **params))
            assert client.records[-1]['sha256'] == request['sha256']
    laps = {row['lap_number']: row for row in cached['laps']}
    assert laps == {row['lap_number']: row['lap'] for row in audit}
    # Fix the alignment and boundary conditions exclusively from the calibration lap.
    geometry = np.loadtxt(REFERENCE, delimiter=',')[:, :2]
    calibration = split['calibration_laps'][0]
    alignment = timing_alignment(laps[calibration], cached['location'], geometry)
    max_gap = load(ROOT / 'configs/openf1_dataset_plan.json')['maximum_gap_s']
    metrics = dict(split, alignment=alignment,
                   timing_line_offset_fraction=alignment['selected']['phase_fraction'],
                   provenance={'directory': str(SOURCE.relative_to(ROOT)).replace('\\', '/'),
                               'acquisition_output_sha256': complete['outputs'],
                               'acquisition_completion_sha256': digest(SOURCE / 'complete.json'),
                               'raw_cache_responses': client.records,
                               'split_sha256': digest(OUTPUT / 'split.json'),
                               'script_sha256': digest(Path(__file__)),
                               'reference_geometry_sha256': digest(REFERENCE)},
                   acquisition_screening=[{k: row[k] for k in ('lap_number', 'conditional_motion_candidate',
                                           'screening_exclusions', 'quality_flags', 'verified_clean_lap',
                                           'dry_track_verified')} for row in audit], laps={})
    for lap_number in split['calibration_laps'] + split['holdout_laps']:
        record, values = prepare_lap(laps[lap_number], cached['car_data'], max_gap)
        path = OUTPUT / f'lap-{lap_number}.csv'
        np.savetxt(path, values, fmt=('%.12f', '%.6f', '%.9f', '%d', '%g', '%d'), delimiter=',',
                   header='fraction,time_s,speed_mps,brake,throttle,drs', comments='')
        metrics['laps'][str(lap_number)] = dict(record, csv_sha256=digest(path))
        if lap_number == calibration:
            metrics['rolling_line_speed_mps'] = float(np.mean(record['edge_speeds_mps']))
            metrics['sector_boundary_fractions'] = record['sector_boundary_fractions']
    save_json(OUTPUT / 'metrics.json', metrics)
    print('Timing-line phase:', metrics['timing_line_offset_fraction'])
    print('Rolling-line speed (m/s):', metrics['rolling_line_speed_mps'])


if __name__ == '__main__':
    main()
