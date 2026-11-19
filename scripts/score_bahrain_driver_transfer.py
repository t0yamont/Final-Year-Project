"""Score two locked Bahrain predictions on the frozen same-session driver transfer."""
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import numpy as np

from acquire_openf1_dataset import verify_outputs
from benchmark_circuit_control import save, sha
from calibrate_bahrain_pace import PLOT_FRACTION, assess, observed, plt, read
from f1energy.openf1 import OpenF1Client, OpenF1Error
from prepare_bahrain_pace import SOURCE, prepare_lap, stamp

PROTOCOL = Path('configs/bahrain_driver_transfer_protocol.json')
LOCK = Path('results/bahrain-path-candidate-001/locked_predictions.json')
PACE_PROTOCOL = Path('configs/bahrain_pace_protocol.json')
PACE_METADATA = Path('results/bahrain-pace-inputs-001/metrics.json')
ACQUISITION_PLAN = Path('configs/openf1_dataset_plan.json')
OUT = Path('results/bahrain-driver-transfer-001')
FIGURES = Path('figures/dissertation/bahrain-driver-transfer-v1')
COHORT = [2, 5, 13]
COLUMNS = 'fraction,time_s,speed_mps,brake,throttle,drs'


def verify_hashes(hashes):
    for path, expected in hashes.items():
        if sha(path) != expected:
            raise ValueError(f'Frozen input changed: {path}')


def prediction(entry, frozen, rolling_speed):
    for path in ('profile', 'model'):
        if entry[path] not in frozen:
            raise ValueError(f'File missing from prediction lock: {entry[path]}')
    model = read(entry['model'])
    trace = np.genfromtxt(entry['profile'], names=True, delimiter=',')
    fraction, distance, speed, time = (
        trace[column] for column in ('fraction', 'distance_m', 'calibrated_speed_mps', 'calibrated_time_s'))
    if not np.array_equal(fraction, PLOT_FRACTION):
        raise ValueError('Prediction must use the original scoring fractions')
    if (not np.isfinite(distance).all() or not np.isfinite(speed).all() or not np.isfinite(time).all()
            or np.any(np.diff(time) <= 0) or np.any(speed <= 0)
            or distance[-1] <= 0 or not np.allclose(distance, fraction * distance[-1], rtol=0., atol=1e-8)
            or time[0] != 0 or abs(speed[0] - rolling_speed) >= 1e-5
            or model['initial_speed_mps'] != rolling_speed):
        raise ValueError('Invalid time, speed or distance in a frozen prediction')
    grid_error = float(entry['grid_error_s'])
    if not np.isfinite(grid_error) or grid_error < 0:
        raise ValueError('Invalid frozen grid assessment')
    return dict(speed=speed, time=time, length_m=float(distance[-1]), grid_error_s=grid_error)


def transfer_data(driver, cohort):
    complete = read(SOURCE / 'complete.json')
    if (complete['meeting_key'], complete['session_key'], complete['role'], complete['session_name']) != (
            1257, 10010, 'development', 'Qualifying'):
        raise ValueError('Unexpected acquisition session')
    # Verify the driver-scoped normalized products and the receipts before opening traces.
    acquisitions = {name: complete['outputs'][name] for name in (
        f'driver-{driver}-complete.json', f'driver-{driver}-laps.json', f'driver-{driver}-car.csv.gz',
        'requests.json')}
    verify_outputs(SOURCE, {'outputs': acquisitions})
    audit = read(SOURCE / f'driver-{driver}-laps.json')
    accepted = [r['lap_number'] for r in audit if r['conditional_motion_candidate']]
    if accepted != cohort:
        raise ValueError(f'Acquisition screen mismatch: {accepted}')
    server = OpenF1Client(Path('work/source-audit-openf1'), offline=True)
    cached = {'laps': [], 'car_data': []}
    for receipt in read(SOURCE / 'requests.json'):
        url = urlsplit(receipt['url'])
        endpoint = url.path.rsplit('/', 1)[-1]
        params = dict(parse_qsl(url.query))
        if params.get('driver_number') != str(driver) or endpoint not in cached:
            continue
        cached[endpoint].extend(server.fetch(endpoint, **params))
        if server.records[-1]['sha256'] != receipt['sha256']:
            raise ValueError(f'Cached response differs from the acquisition receipt: {receipt["url"]}')
    laps = {record['lap_number']: record for record in cached['laps']}
    if laps != {r['lap_number']: r['lap'] for r in audit}:
        raise ValueError('Cached lap records differ from the acquisition records')
    context = {r['lap_number']: {k: r[k] for k in (
        'screening_exclusions', 'conditional_motion_candidate', 'verified_clean_lap', 'dry_track_verified',
        'quality_flags')} for r in audit}
    return (laps, cached['car_data'], context, server.records,
            {str(SOURCE / path): digest for path, digest in acquisitions.items()})


def repair_first_sample(lap, car):
    start = datetime.fromisoformat(lap['date_start']).astimezone(timezone.utc)
    first_cached = car[0]
    first_time = stamp(first_cached['date'])
    if first_time <= start.timestamp():
        return car, {'status': 'original_bracket_present'}
    patch = OpenF1Client(Path('work/bahrain-driver-transfer-edge-001'), max_attempts=1)
    bounds = {'date>': (start - timedelta(seconds=2)).isoformat(),
              'date<': (start + timedelta(seconds=2)).isoformat()}
    try:
        archive = patch.fetch('car_data', session_key=10010, driver_number=22, **bounds)
    except OpenF1Error as error:
        return car, {'status': 'request_unavailable', 'error': str(error), 'requests': patch.records}
    match = [row for row in archive if stamp(row['date']) == first_time]
    channels = ('speed', 'rpm', 'n_gear', 'throttle', 'brake', 'drs')
    preceding = [row for row in archive if stamp(row['date']) < first_time]
    matched = len(match) == 1 and all(match[0][channel] == first_cached[channel] for channel in channels)
    identity = all((r['meeting_key'], r['session_key'], r['driver_number']) == (1257, 10010, 22) for r in archive)
    repaired = matched and identity and any(stamp(row['date']) <= start.timestamp() for row in preceding)
    info = {'status': 'verified_preceding_rows_added' if repaired else 'archive_overlap_or_bracket_failed',
            'overlap_timestamp': first_cached['date'], 'overlap_channels': list(channels),
            'overlap_verified': matched, 'rows_added': len(preceding) if repaired else 0,
            'requests': patch.records}
    return (preceding + car if repaired else car), info


def score(obs, info, pred, boundaries, rolling_speed, assessment):
    values = assess(obs, info, pred['speed'], pred['time'], boundaries)
    checks = dict(lap=abs(values['lap_error_s']) <= assessment['absolute_lap_error_s'],
                  sectors=max(map(abs, values['sector_error_s'])) <= assessment['absolute_each_sector_error_s'],
                  speed=values['speed_rmse_mps'] <= assessment['speed_rmse_mps'],
                  grid=pred['grid_error_s'] <= assessment['absolute_grid_time_change_s'],
                  finish=bool(abs(pred['speed'][-1] - rolling_speed) < 1e-5))
    return dict(values, checks=checks, passed=all(checks.values()))


def figure(path, laps, predictions, boundaries):
    fig, axes = plt.subplots(len(laps), 2, figsize=(11, 8), sharex=True)
    length = predictions['current']['length_m'] / 1000
    x = PLOT_FRACTION * length
    colors = {'current': '#ab501b', 'candidate': '#11718b'}
    for (n, lap), (speed_ax, time_ax) in zip(laps.items(), axes):
        v, t = observed(lap)
        speed_ax.plot(x, v*3.6, color='#252525', label='Observed', lw=1.3)
        for model, pred in predictions.items():
            speed_ax.plot(x, pred['speed']*3.6, color=colors[model], label=model.title(), lw=1.2)
            time_ax.plot(x, pred['time']-t, color=colors[model], label=model.title(), lw=1.2)
        time_ax.axhline(0, color='#777', lw=.7)
        for ax in (speed_ax, time_ax):
            for boundary in boundaries[1:-1]:
                ax.axvline(boundary*length, color='#777', linestyle=':', lw=1)
            ax.grid(axis='y', alpha=.2)
        speed_ax.set_ylabel(f'Lap {n} speed (km/h)')
        time_ax.set_ylabel(f'Lap {n} time error (s)')
    axes[0, 0].set_title('Speed')
    axes[0, 1].set_title('Simulated minus observed time')
    axes[0, 0].legend(loc='lower right', fontsize=8)
    for ax in axes[-1]:
        ax.set_xlabel('Distance from timing line on current model path (km)')
    fig.suptitle('Bahrain qualifying driver 22 · Dotted lines show inferred sector boundaries')
    fig.tight_layout()
    for ext in ('png', 'pdf'):
        fig.savefig(path.with_suffix(f'.{ext}'), dpi=300)
    plt.close(fig)


def main():
    if OUT.exists() or FIGURES.exists():
        raise FileExistsError('The frozen transfer has already been attempted in these output directories')
    protocol, lock = read(PROTOCOL), read(LOCK)
    if (protocol['meeting_key'], protocol['session_key'], protocol['driver_number'], protocol['laps']) != (
            1257, 10010, 22, COHORT) or Path(protocol['curve_lock']) != LOCK:
        raise ValueError('Unexpected transfer cohort')
    frozen = lock['inputs']
    if not {str(p).replace('\\', '/') for p in (PROTOCOL, PACE_METADATA)}.issubset(
            str(p).replace('\\', '/') for p in frozen):
        raise ValueError('Transfer protocol and original input metadata must be locked')
    verify_hashes(frozen)
    verify_hashes(protocol['inputs'])
    procedure = read(PACE_PROTOCOL)
    if procedure['assessment'] != dict(absolute_lap_error_s=2., absolute_each_sector_error_s=1.,
            speed_rmse_mps=5., absolute_grid_time_change_s=.25):
        raise ValueError('Original pace thresholds changed')
    if protocol['gates'] != dict(procedure['assessment'], absolute_finish_speed_error_mps=1e-5):
        raise ValueError('Transfer gates differ from the original assessment')
    metadata = read(PACE_METADATA)
    rolling_speed, boundaries = metadata['rolling_line_speed_mps'], metadata['sector_boundary_fractions']
    predictions = {name: prediction(lock[name], frozen, rolling_speed) for name in ('current', 'candidate')}

    # Predictions are verified and loaded before any transfer telemetry is read.
    laps, car, screened, receipts, input_hashes = transfer_data(protocol['driver_number'], COHORT)
    repaired_car, edge_repair = repair_first_sample(laps[2], car)
    gap = read(ACQUISITION_PLAN)['maximum_gap_s']
    original = {'protocol': str(PACE_PROTOCOL), 'assessment': procedure['assessment'],
                'boundary_fractions': boundaries, 'rolling_line_speed_mps': rolling_speed,
                'finish_tolerance_mps': 1e-5}
    scores, observations, prepared = {}, {}, {}

    for n in COHORT:
        samples = repaired_car if n == 2 else car
        timestamps = np.array([stamp(r['date']) for r in samples])
        start = stamp(laps[n]['date_start'])
        duration = laps[n]['lap_duration']
        nearby = timestamps[(timestamps >= start-2) & (timestamps <= start+duration+2)] - start
        if not len(nearby) or nearby[0] > 0 or nearby[-1] < duration:
            scores[n] = {'status': 'unscorable_missing_native_edge_bracket',
                         'official_lap_s': duration,
                         'official_sector_s': [laps[n][f'duration_sector_{j}'] for j in (1, 2, 3)],
                         'first_cached_sample_after_start_s': round(float(nearby[0]), 6) if len(nearby) else None,
                         'last_cached_sample_after_finish_s': round(float(nearby[-1]) - duration, 6) if len(nearby) else None}
            continue
        record, values = prepare_lap(laps[n], samples, gap)
        # Match the original pace input's tabulation precision before scoring.
        csv = StringIO()
        np.savetxt(csv, values, fmt=('%.12f', '%.6f', '%.9f', '%d', '%g', '%d'), delimiter=',',
                   header=COLUMNS, comments='')
        prepared[n] = csv.getvalue()
        csv.seek(0)
        observations[n] = np.genfromtxt(csv, names=True, delimiter=',')
        scores[n] = {'status': 'scored', 'observed': record}
        for name, pred in predictions.items():
            scores[n][name] = score(observations[n], record, pred, boundaries, rolling_speed, procedure['assessment'])
    scored = list(observations)
    if not scored:
        raise ValueError('No frozen cohort lap has the required native bracketing coverage')
    unscorable = [n for n in COHORT if n not in scored]
    summary = {name: dict(cases=len(COHORT), scored=len(scored), passing=sum(scores[n][name]['passed'] for n in scored),
        all_cohort_cases_passed=not unscorable and all(scores[n][name]['passed'] for n in scored),
        unscorable_cases=unscorable, failed_cases=[n for n in scored if not scores[n][name]['passed']],
        criterion_passes={k: sum(scores[n][name]['checks'][k] for n in scored)
                         for k in scores[scored[0]][name]['checks']},
        grid_error_s=pred['grid_error_s'], model_path_length_m=pred['length_m'],
        finish_speed_mps=float(pred['speed'][-1])) for name, pred in predictions.items()}
    input_hashes.update(protocol['inputs'])
    input_hashes.update(frozen)
    input_hashes.update({str(path): sha(path) for path in (LOCK, PACE_PROTOCOL, ACQUISITION_PLAN, SOURCE / 'complete.json')})
    sources = {str(path): sha(path) for path in (Path(__file__).resolve(), Path('scripts/prepare_bahrain_pace.py'),
               Path('scripts/calibrate_bahrain_pace.py'), Path('src/f1energy/openf1.py'))}
    verify_hashes(input_hashes)
    OUT.mkdir()
    FIGURES.mkdir()
    for n, content in prepared.items():
        (OUT / f'lap-{n}.csv').write_bytes(content.encode('ascii'))
    save(OUT / 'metrics.json', dict(driver_number=protocol['driver_number'], meeting_key=1257, session_key=10010,
        screening=screened, acquisition_receipts=receipts, lap_2_edge_repair=edge_repair,
        original=original, summary=summary, laps=scores))
    figure(FIGURES / '01_paired_transfer', observations, predictions, boundaries)
    save(OUT / 'manifest.json', dict(inputs=input_hashes, sources=sources,
         outputs={str(p): sha(p) for folder in (OUT, FIGURES) for p in folder.iterdir() if p.is_file()}))
    print(summary)


if __name__ == '__main__':
    main()
