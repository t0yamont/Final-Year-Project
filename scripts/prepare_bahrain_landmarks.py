"""Project manually annotated MultiViewer corners onto the frozen fit lap."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    metadata = ROOT / 'work/track-source/bahrain_multiviewer_2025.json'
    position = ROOT / 'results/openf1-dataset-003/development/1257/10010/driver-1-position.csv.gz'
    lap = ROOT / 'results/bahrain-pace-inputs-001/lap-13.csv'
    metrics = json.loads((lap.parent / 'metrics.json').read_text())
    data = json.loads(metadata.read_text())
    fit = metrics['laps']['13']
    trace = pd.read_csv(position)
    times = (pd.to_datetime(trace.date) - pd.Timestamp(fit['date_start'])).dt.total_seconds().to_numpy()
    nearby = (times >= -2) & (times <= fit['duration_s'] + 2)
    times = times[nearby]
    xy = trace.loc[nearby, ['x', 'y']].to_numpy() * .1
    active = np.r_[0., times[(times > 0) & (times < fit['duration_s'])], fit['duration_s']]
    xy = np.column_stack([np.interp(active, times, xy[:, j]) for j in range(2)])
    delta = np.diff(xy, axis=0)
    lengths = np.linalg.norm(delta, axis=1)
    arc = np.r_[0., np.cumsum(lengths)]
    car = pd.read_csv(lap)
    corners = []
    for corner in data['corners']:
        point = np.array([corner['trackPosition'][k] for k in ('x', 'y')]) * .1
        weight = np.clip(np.sum((point - xy[:-1]) * delta, axis=1) / lengths**2, 0, 1)
        residual = np.linalg.norm(xy[:-1] + weight[:, None] * delta - point, axis=1)
        index = int(np.argmin(residual))
        time = float(active[index] + weight[index] * (active[index + 1] - active[index]))
        fraction = float(np.interp(time, car.time_s, car.fraction))
        corners.append({'turn': corner['number'], 'label': f"T{corner['number']}",
                        'marker_native_xy': point.tolist(), 'marker_xy_units': 'm',
                        'fraction': fraction, 'fit_lap_distance_m': fraction * fit['integrated_distance_m'],
                        'fit_lap_time_s': time, 'xy_residual_m': float(residual[index]),
                        'location_segment_length_m': float(lengths[index]),
                        'location_segment_duration_s': float(active[index + 1] - active[index]),
                        'location_arclength_fraction': float((arc[index] + weight[index] * lengths[index]) / arc[-1]),
                        'source_geometry_fraction': float((metrics['timing_line_offset_fraction'] +
                            (arc[index] + weight[index] * lengths[index]) / arc[-1]) % 1)})
    assert len(corners) == 15 and all(a['fraction'] < b['fraction'] for a, b in zip(corners, corners[1:]))
    assert max(c['xy_residual_m'] for c in corners) < 20
    result = {'purpose': 'Approximate visualization landmarks only; never brake/deployment zone boundaries.',
              'fraction_definition': 'Distance integrated from speed on development qualifying lap13, divided by its total; zero at timing line.',
              'distance_length_m': fit['integrated_distance_m'],
              'approximate_station_uncertainty_m': 50,
              'uncertainty_note': 'Conservative display tolerance, not a statistical confidence interval; manual markers and sparse XY samples.',
              'source_url': 'https://api.multiviewer.app/api/v1/circuits/63/2025',
              'returned_source_year': data['year'], 'returned_candidate_lap': data['candidateLap'],
              'source_rotation_degrees': data['rotation'],
              'native_xy_to_m': .1, 'projection': 'Nearest continuous segment in unrotated F1 XY; interpolate time then car-distance fraction.',
              'geometry_phase_fraction': metrics['timing_line_offset_fraction'],
              'input_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (metadata, position, lap, lap.parent / 'metrics.json')},
              'corners': corners}
    target = ROOT / 'configs/bahrain_turn_landmarks.json'
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(corners, indent=2))


if __name__ == '__main__':
    main()
