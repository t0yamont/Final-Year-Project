"""Verify frozen Bahrain pace results independently of the calibration metrics reader."""
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from bahrain_pace_model import build_env, limits
from f1energy.circuit_control import terminal_envelope
from f1energy.power_lap import PowerVehicle

RESULTS = Path('results')
INPUTS = RESULTS / 'bahrain-pace-inputs-001'
DIAGNOSIS = RESULTS / 'bahrain-pace-diagnosis-001'
CALIBRATION = RESULTS / 'bahrain-pace-calibration-001'


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_manifest(folder):
    manifest = load(folder / 'manifest.json')
    for section in manifest.values():
        for file, checksum in section.items():
            assert sha(Path(file)) == checksum, file
    return manifest


def audit_metrics(metadata, protocol):
    metrics = load(CALIBRATION / 'metrics.json')
    table = np.genfromtxt(CALIBRATION / 'speed_time.csv', delimiter=',', names=True)
    historic = load(DIAGNOSIS / 'historical.json')
    fraction = table['fraction']
    np.testing.assert_array_equal(fraction, historic['fraction'])
    np.testing.assert_array_equal(table['historical_speed_mps'], historic['speed_mps'])
    np.testing.assert_array_equal(table['historical_time_s'], historic['time_s'])
    reference_length = table['distance_m'][-1]
    np.testing.assert_allclose(table['distance_m'], fraction * reference_length, rtol=0, atol=1e-10)
    np.testing.assert_allclose(reference_length, metrics['model_length_m'], rtol=0, atol=1e-10)
    boundaries = metadata['sector_boundary_fractions']
    gates = protocol['assessment']
    rows = {}
    for n in protocol['check_laps']:
        path = INPUTS / f'lap-{n}.csv'
        obs = np.genfromtxt(path, delimiter=',', names=True)
        observed = metadata['laps'][str(n)]
        assert sha(path) == observed['csv_sha256']
        observed_speed = np.interp(fraction, obs['fraction'], obs['speed_mps'])
        observed_time = np.interp(fraction, obs['fraction'], obs['time_s'])
        assert observed_time[-1] == observed['duration_s']
        stored = metrics['laps'][str(n)]
        assert stored['role'] == 'separate_lap'
        rows[n] = {}
        for columns, label in [('historical', 'historical'), ('calibrated', 'revised')]:
            time, speed = (table[f'{columns}_{channel}'] for channel in ('time_s', 'speed_mps'))
            sector = np.diff(np.interp(boundaries, fraction, time))
            errors = sector - observed['sector_times_s']
            err = time[-1] - observed_time[-1]
            rmse = np.linalg.norm(speed - observed_speed) / np.sqrt(len(fraction))
            independent = dict(lap_s=time[-1], lap_error_s=err, sector_prediction_s=sector.tolist(),
                sector_error_s=errors.tolist(), speed_rmse_mps=rmse,
                cumulative_time_error_s=(time - observed_time).tolist())
            for k, v in independent.items():
                np.testing.assert_allclose(v, stored[label][k], rtol=0, atol=1e-10)
            del independent['cumulative_time_error_s']
            rows[n][label] = independent
        revised = rows[n]['revised']
        checks = dict(lap=bool(abs(revised['lap_error_s']) <= gates['absolute_lap_error_s']),
            sectors=bool(max(map(abs, revised['sector_error_s'])) <= gates['absolute_each_sector_error_s']),
            speed=bool(revised['speed_rmse_mps'] <= gates['speed_rmse_mps']),
            grid=metrics['grid_error_s'] <= gates['absolute_grid_time_change_s'],
            finish=bool(abs(table['calibrated_speed_mps'][-1] - metadata['rolling_line_speed_mps']) < 1e-5))
        assert checks == stored['checks']
        rows[n]['checks'] = checks
    assert metrics['all_heldout_checks_passed'] == all(all(row['checks'].values()) for row in rows.values())
    return rows


def trajectory(env, action):
    env.reset()
    values = []
    for _ in range(env.blocks):
        _, _, _, _, record = env.step([action])
        s = record['state']
        values.append([s[k] for k in ('distance_m', 'elapsed_s', 'speed_m_per_s', 'energy_j')] +
                      [env.recovered_j, env.discharged_j])
    return np.array(values)


def main():
    calibration = checked_manifest(CALIBRATION)
    diagnosis = checked_manifest(DIAGNOSIS)
    protocol = load(Path('configs/bahrain_pace_protocol.json'))
    contract = load(CALIBRATION / 'contract.json')
    split = load(INPUTS / 'split.json')
    metadata = load(INPUTS / 'metrics.json')
    assert protocol == contract['protocol']
    assert protocol['fit_laps'] == split['calibration_laps'] == metadata['calibration_laps'] == [13]
    assert protocol['check_laps'] == split['holdout_laps'] == metadata['holdout_laps'] == [4, 10]
    assert sha(INPUTS / 'split.json') == metadata['provenance']['split_sha256']
    assert {Path(p).name for p in contract['inputs'] if Path(p).suffix == '.csv'} == {'lap-13.csv'}
    assert {Path(p).name for p in calibration['inputs'] if Path(p).suffix == '.csv'} == {
        'lap-13.csv', 'lap-4.csv', 'lap-10.csv'}
    assert sha(CALIBRATION / 'model.json') == load(CALIBRATION / 'fit.json')['model_sha256']
    historic_folder = Path(protocol['historic'])
    historic_manifest = checked_manifest(historic_folder)
    with gzip.open(historic_folder / 'w64_cells160.json.gz', 'rt') as stream:
        old_duration = json.load(stream)['duration_s']
    assert abs(load(DIAGNOSIS / 'historical.json')['time_s'][-1] - old_duration) < 1e-6
    model = load(CALIBRATION / 'model.json')
    assert model['line_offset_fraction'] == metadata['timing_line_offset_fraction']
    assert model['initial_speed_mps'] == metadata['rolling_line_speed_mps']
    lap = np.genfromtxt(INPUTS / 'lap-13.csv', delimiter=',', names=True)
    opens = np.isin(lap['drs'], [10, 12, 14])
    block = lap['fraction']
    expected_drs = []
    for k in range(55):
        states = opens[(block >= k/55) & (block < (k+1)/55)]
        expected_drs.append(bool(2 * states.sum() > len(states)))
    assert model['drs_blocks'] == expected_drs

    reference = load(Path('configs/circuit_reference.json'))
    historical_model = dict(model, line_offset_fraction=0., initial_speed_mps=70.,
        lateral_base_mps2=reference['lateral_acceleration_mps2'], lateral_aero_per_m=0.,
        drs_blocks=[False]*55, drs_drag_factor=1., vehicle=reference['vehicle'])
    grid, regime_envelope, _ = limits(historical_model, 40)
    old_envelope = terminal_envelope(grid, PowerVehicle(**reference['vehicle']), 70.)
    envelope_difference = float(np.max(np.abs(regime_envelope - old_envelope)))
    np.testing.assert_allclose(regime_envelope, old_envelope, rtol=0, atol=1e-10)
    parity = {}
    for name, m in [('historical', historical_model), ('revised', model)]:
        blocked = trajectory(build_env(m, 40), protocol['reference_action'])
        cellwise = trajectory(build_env(m, 40, cellwise=True), protocol['reference_action'])
        np.testing.assert_array_equal(blocked, cellwise[39::40])
        parity[name] = {'max_block_end_difference': (np.abs(blocked-cellwise[39::40]).max(axis=0)).tolist(),
                        'duration_s': float(blocked[-1, 1])}
    record = dict(manifest_hashes_checked=sum(len(section) for manifest in (
        calibration, diagnosis, historic_manifest) for section in manifest.values()),
        split={'fit': [13], 'check': [4, 10]}, historical_archive_duration_s=old_duration,
        lap_metrics=audit_metrics(metadata, protocol), historical_envelope_max_difference_mps=envelope_difference,
        block_cellwise_parity=parity)
    print(json.dumps(record, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
