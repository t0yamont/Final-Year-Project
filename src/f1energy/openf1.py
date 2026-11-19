"""Cached public OpenF1 telemetry and conservative lap-alignment diagnostics."""

from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from threading import Lock
import time
from urllib.parse import parse_qs, urlsplit

try:
    import requests
except ImportError:
    requests = None


BASE_URL = "https://api.openf1.org/v1"
UNITS = {
    "date_utc": "ISO 8601 UTC", "lap_elapsed_s": "s", "speed_kmh": "km/h",
    "speed_mps": "m/s", "rpm": "rev/min", "gear": "gear index",
    "throttle_pct": "percent", "brake": "boolean", "drs": "OpenF1 status code",
}
CHANNELS = ("speed", "rpm", "n_gear", "throttle", "brake", "drs")
DRS_CODES = frozenset((0, 1, 2, 3, 8, 9, 10, 12, 14))


class OpenF1Error(RuntimeError):
    """A cache, transport, HTTP, or response validation failure."""


def _sha256(body):
    return hashlib.sha256(body).hexdigest()


def _utc(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def _now():
    return datetime.now(timezone.utc)


def _atomic_write(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temp:
        name = temp.name
        try:
            temp.write(data)
            temp.close()
            os.replace(name, path)
        finally:
            Path(name).unlink(missing_ok=True)


def _reject_constant(value):
    raise ValueError(f"Non-JSON numeric constant {value}")


def _parse_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"JSON number is non-finite: {value}")
    return number


def _decode_rows(body):
    data = json.loads(body, parse_constant=_reject_constant, parse_float=_parse_float)
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ValueError("Expected a JSON array of objects")
    return data


def _empty_window(url, status, body):
    """Recognise the observed provider's no-results response, not arbitrary404s."""
    if status != 404:
        return False
    parsed = urlsplit(url)
    query = parse_qs(parsed.query)
    if parsed.path.rsplit('/', 1)[-1] not in ('car_data', 'location') or not {
        'session_key', 'driver_number', 'date>', 'date<'
    } <= query.keys():
        return False
    try:
        return json.loads(body) == {'detail': 'No results found.'}
    except (ValueError, TypeError):
        return False


class OpenF1Client:
    """Fetch public data with a URL-keyed cache and per-attempt provenance.

    Reuse one client for all requests in a runner to share its pacing budget.
    Optional HTTP, time and sleep callables allow network-free tests.
    """

    def __init__(
        self, cache_dir, *, offline=False, min_interval_s=2.1, timeout=(10, 25),
        max_attempts=3, max_backoff_s=30, get=None, monotonic=time.monotonic,
        sleep=time.sleep, now=_now,
    ):
        if requests is None:
            raise OpenF1Error("Install requirements-data.txt to use the OpenF1 HTTP client")
        if not math.isfinite(min_interval_s) or min_interval_s < 2.1:
            raise ValueError("OpenF1 request interval must be at least 2.1 seconds")
        if type(max_attempts) is not int or max_attempts < 1:
            raise ValueError("max_attempts must be a positive integer")
        if not math.isfinite(max_backoff_s) or max_backoff_s < 0:
            raise ValueError("max_backoff_s must be finite and nonnegative")
        if len(timeout) != 2 or any(not math.isfinite(t) or t <= 0 for t in timeout):
            raise ValueError("timeout must contain positive, finite connect and read timeouts")
        self.cache_dir = Path(cache_dir)
        self.offline = offline
        self.records = []
        self._min_interval = min_interval_s
        self._timeout = timeout
        self._max_attempts = max_attempts
        self._max_backoff = max_backoff_s
        self._get = get or requests.get
        self._monotonic = monotonic
        self._sleep = sleep
        self._now = now
        self._last_request = None
        self._lock = Lock()

    def fetch(self, endpoint, **params):
        """Return decoded rows, or raise OpenF1Error with a recorded failure."""
        if not re.fullmatch(r"[a-z][a-z0-9_]*", endpoint):
            raise ValueError("Expected an OpenF1 endpoint name")
        url = requests.Request("GET", f"{BASE_URL}/{endpoint}", params=params).prepare().url
        key = _sha256(url.encode())
        body_path = self.cache_dir / f"{key}.json"
        meta_path = self.cache_dir / f"{key}.meta.json"
        with self._lock:
            return self._fetch(url, key, body_path, meta_path)

    def _fetch(self, url, key, body_path, meta_path):
        record = {"url": url, "cache_key": key, "cache_hit": False}
        if body_path.exists() or meta_path.exists():
            record["cache_hit"] = True
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                body = body_path.read_bytes()
                empty_result = isinstance(meta, dict) and _empty_window(url, meta.get('status'), body)
                if not isinstance(meta, dict) or (
                    meta.get("url") != url or (meta.get("status") != 200 and not empty_result)
                    or meta.get("sha256") != _sha256(body)
                    or meta.get("bytes") != len(body)
                    or _utc(meta.get("retrieved_utc")) is None
                ):
                    raise ValueError("Cache metadata or body failed integrity validation")
                rows = [] if empty_result else _decode_rows(body)
            except (OSError, ValueError) as exc:
                self.records.append(dict(record, status="cache_corrupt", error=str(exc)))
                raise OpenF1Error(f"Invalid OpenF1 cache entry {key}: {exc}") from exc
            self.records.append(dict(meta, **record, rows=len(rows)))
            return rows
        if self.offline:
            self.records.append(dict(record, status="cache_miss"))
            raise OpenF1Error(f"Offline OpenF1 cache miss: {url}")

        backoff = min(self._min_interval, self._max_backoff)
        for attempt in range(1, self._max_attempts + 1):
            if self._last_request is not None:
                pause = self._min_interval - (self._monotonic() - self._last_request)
                if pause > 0:
                    self._sleep(pause)
            self._last_request = self._monotonic()
            event = dict(record, attempt=attempt)
            retry_after = None
            try:
                # Explicit no-op authentication avoids ambient netrc credentials.
                response = self._get(
                    url, timeout=self._timeout, allow_redirects=False, auth=lambda request: request,
                )
            except requests.RequestException as exc:
                event.update(status="request_failed", error_type=type(exc).__name__)
                retryable = isinstance(exc, (requests.Timeout, requests.ConnectionError))
                failure = str(exc)
            else:
                body = response.content
                status = response.status_code
                event.update(
                    status=status, retrieved_utc=self._now().isoformat(),
                    bytes=len(body), sha256=_sha256(body),
                )
                if status == 200 or _empty_window(url, status, body):
                    event['empty_result'] = status == 404
                    return self._save_response(event, body, body_path, meta_path)
                retryable = status == 429 or 500 <= status <= 599
                retry_after = response.headers.get("Retry-After")
                failure = f"HTTP {status}"

            self.records.append(event)
            if not retryable or attempt == self._max_attempts:
                raise OpenF1Error(f"OpenF1 request failed: {failure} ({url})")
            pause = max(backoff, self._retry_after_seconds(retry_after))
            if pause > self._max_backoff:
                raise OpenF1Error(f"OpenF1 Retry-After exceeds retry budget ({url})")
            event["retry_backoff_s"] = pause
            if pause > 0:
                self._sleep(pause)
            backoff = min(backoff * 2, self._max_backoff)
        raise AssertionError("No terminal OpenF1 response")

    def _retry_after_seconds(self, value):
        if value is None:
            return 0
        try:
            seconds = float(value)
        except ValueError:
            try:
                stamp = parsedate_to_datetime(value)
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=timezone.utc)
                seconds = (stamp - self._now()).total_seconds()
            except (TypeError, ValueError, OverflowError):
                return 0
        return max(0, seconds)

    def _save_response(self, event, body, body_path, meta_path):
        self.records.append(event)
        try:
            rows = [] if _empty_window(event['url'], event['status'], body) else _decode_rows(body)
        except ValueError as exc:
            event["error"] = str(exc)
            raise OpenF1Error(f"Invalid OpenF1 response ({event['url']}): {exc}") from exc
        event["rows"] = len(rows)
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            _atomic_write(body_path, body)
            _atomic_write(meta_path, json.dumps(event, indent=2).encode())
        except OSError as exc:
            event["cache_write_error"] = str(exc)
            raise OpenF1Error(f"Could not write OpenF1 cache ({event['url']}): {exc}") from exc
        return rows


def _number(value):
    return (
        type(value) is int and value.bit_length() <= 1023
        or type(value) is float and math.isfinite(value)
    )


def _integer(value):
    return _number(value) and value == int(value)


def _positive_int(value):
    return _integer(value) and value > 0


def lap_bounds(lap):
    """Return the approximate source interval [start, start + duration) in UTC."""
    start = _utc(lap.get("date_start"))
    duration = lap.get("lap_duration")
    if start is None or not _number(duration) or duration <= 0:
        return None
    try:
        end = start + timedelta(seconds=duration)
    except OverflowError:
        return None
    return (start, end) if start < end else None


def normalise_car_data(rows):
    """Return native UTC samples in source order and channel/timestamp QC.

    Invalid values become None in the normalised view. The cache holds the source
    payload. Any missing, invalid, duplicate or out-of-order sample fails QC.
    The input should be one driver's stream within one session.
    """
    samples = []
    missing, invalid = dict.fromkeys(CHANNELS, 0), dict.fromkeys(CHANNELS, 0)
    seen, gaps, streams = {}, [], set()
    bad_timestamps = duplicates = conflicts = reversed_steps = 0
    previous = None
    for row in rows:
        stamp = _utc(row.get("date"))
        values = tuple(row.get(channel) for channel in CHANNELS)
        speed, rpm, gear, throttle, brake, drs = values
        valid = (
            _number(speed) and speed >= 0,
            _integer(rpm) and rpm >= 0,
            _integer(gear) and 0 <= gear <= 8,
            _number(throttle) and 0 <= throttle <= 100,
            _number(brake) and brake in (0, 100),
            _integer(drs) and drs in DRS_CODES,
        )
        for channel, value, ok in zip(CHANNELS, values, valid):
            missing[channel] += value is None
            invalid[channel] += value is not None and not ok

        streams.add(_driver_stream(row))
        if stamp is None:
            bad_timestamps += 1
        else:
            if stamp in seen:
                duplicates += 1
                # Include types so a malformed True does not compare equal to 1.
                conflicts += seen[stamp] != tuple((type(value), value) for value in values)
            else:
                seen[stamp] = tuple((type(value), value) for value in values)
            if previous is not None:
                gap = (stamp - previous).total_seconds()
                reversed_steps += gap < 0
                if gap > 0:
                    gaps.append(gap)
        previous = stamp
        samples.append({
            "date_utc": stamp.isoformat() if stamp is not None else None,
            "source_date": row.get("date"),
            "session_key": row.get("session_key"),
            "driver_number": row.get("driver_number"),
            "meeting_key": row.get("meeting_key"),
            "speed_kmh": speed if valid[0] else None,
            "speed_mps": speed / 3.6 if valid[0] else None,
            "rpm": int(rpm) if valid[1] else None,
            "gear": int(gear) if valid[2] else None,
            "throttle_pct": throttle if valid[3] else None,
            "brake": brake == 100 if valid[4] else None,
            "drs": int(drs) if valid[5] else None,
        })

    qc = {
        "sample_count": len(samples),
        "missing_counts": missing,
        "invalid_counts": invalid,
        "invalid_timestamp_count": bad_timestamps,
        "duplicate_timestamp_count": duplicates,
        "conflicting_duplicate_timestamp_count": conflicts,
        "out_of_order_step_count": reversed_steps,
        "stream_count": len(streams),
        "maximum_positive_gap_s": max(gaps, default=None),
    }
    qc["passed"] = (
        len(samples) >= 2 and len(streams) == 1 and None not in streams
        and not (bad_timestamps or duplicates or reversed_steps or any(missing.values()) or any(invalid.values()))
    )
    return samples, qc


def _driver_stream(row):
    session, driver = row.get("session_key"), row.get("driver_number")
    if not (_positive_int(session) and _positive_int(driver)):
        return None
    return int(session), int(driver)


def _weather_context(rows, start, end, max_age):
    observations = defaultdict(list)
    for row in rows:
        stamp = _utc(row.get("date"))
        if stamp is not None and stamp < end:
            observations[stamp].append(row)
    dates = sorted(observations)
    index = bisect_right(dates, start) - 1
    prior = dates[index] if index >= 0 else None
    age = (start - prior).total_seconds() if prior is not None else None
    fresh = age is not None and age <= max_age
    matched = observations[prior][0] if fresh and len(observations[prior]) == 1 else None

    relevant = dates[bisect_right(dates, start):]
    if fresh:
        relevant.insert(0, prior)
    readings = [row.get("rainfall") for stamp in relevant for row in observations[stamp]]
    uninterrupted = fresh and all(
        (b - a).total_seconds() <= max_age for a, b in zip(relevant, relevant[1:] + [end])
    )
    if any(type(value) in (bool, int) and value == 1 for value in readings):
        rain = "rain_reported"
    elif uninterrupted and readings and all(type(value) in (bool, int) and value == 0 for value in readings):
        rain = "no_rain_reported_at_samples"
    else:
        rain = "unknown"
    return {
        "weather_at_start": matched,
        "weather_age_at_start_s": age if matched is not None else None,
        "weather_start_status": (
            "missing" if prior is None else "stale" if not fresh
            else "ambiguous" if matched is None else "matched"
        ),
        "weather_max_age_s": max_age,
        "rainfall_summary": rain,
        "dry_track_verified": False,
    }


def _stint_context(rows, lap_number):
    matches = [
        row for row in rows
        if _positive_int(row.get("lap_start")) and _positive_int(row.get("lap_end"))
        and row["lap_start"] <= lap_number <= row["lap_end"]
    ]
    return {
        "stint": matches[0] if len(matches) == 1 else None,
        "stint_status": "assigned" if len(matches) == 1 else "ambiguous" if matches else "unknown",
        "stint_candidate_count": len(matches),
    }


def _event_context(lap, start, end, pit_rows, control_rows):
    lap_number, driver = lap["lap_number"], lap["driver_number"]

    def in_lap(row):
        stamp = _utc(row.get("date"))
        return stamp is not None and start <= stamp < end

    pits = [row for row in pit_rows if row.get("lap_number") == lap_number or in_lap(row)]
    controls = [
        row for row in control_rows if row.get("driver_number") in (None, driver)
        and (in_lap(row) or (row.get("driver_number") == driver and row.get("lap_number") == lap_number))
    ]
    sectors = [lap.get(f"segments_sector_{number}") for number in range(1, 4)]
    segments = [code for sector in sectors if isinstance(sector, list) for code in sector]
    deleted = any(
        row.get("driver_number") == driver and row.get("lap_number") == lap_number
        and "DELETED" in str(row.get("message", "")).upper() for row in controls
    )
    # Mini-sector 2048 is a timing colour, not a race-control yellow flag.
    flagged = any(
        str(row.get("flag", "")).upper() in {"RED", "YELLOW", "DOUBLE YELLOW"}
        or str(row.get("category", "")).upper().replace(' ', '') == 'SAFETYCAR'
        for row in controls
    )
    return {
        "pit_records": pits,
        "race_control_records": controls,
        "pit_status": "pit_activity_reported" if pits or lap.get("is_pit_out_lap") is True or 2064 in segments else "unknown",
        "track_status": "flag_reported" if flagged else "unknown",
        "validity_status": "deletion_reported" if deleted else "unknown",
    }


def align_laps(
    laps, car_data, *, weather=(), stints=(), pit=(), race_control=(),
    max_weather_age_s=120, max_lap_overlap_s=0.0,
):
    """Join same-session/driver native samples to half-open lap intervals.

    Samples in overlapping intervals are left unassigned. Overlaps exceeding
    the configured tolerance fail QC. Weather at start uses only the latest
    observation at or before start within the configured age. In-lap rain
    observations are separate.
    Stints use inclusive reported lap numbers. Public context does not verify
    dry track, complete flag history, absence of pit activity, or lap validity.
    """
    if not _number(max_weather_age_s) or max_weather_age_s <= 0:
        raise ValueError("max_weather_age_s must be positive and finite")
    if not _number(max_lap_overlap_s) or max_lap_overlap_s < 0:
        raise ValueError("max_lap_overlap_s must be nonnegative and finite")
    by_stream, bad_stamps, invalid_streams = defaultdict(list), Counter(), 0
    for index, sample in enumerate(car_data):
        stream, stamp = _driver_stream(sample), _utc(sample.get("date"))
        if stream is None:
            invalid_streams += 1
        elif stamp is None:
            bad_stamps[stream] += 1
        else:
            by_stream[stream].append((stamp, index, sample))
    dates = {}
    for stream, rows in by_stream.items():
        rows.sort()
        dates[stream] = [entry[0] for entry in rows]

    laps = list(laps)
    intervals, lap_groups, identities = {}, defaultdict(list), Counter()
    for index, lap in enumerate(laps):
        stream = _driver_stream(lap)
        number = lap.get("lap_number")
        bounds = lap_bounds(lap)
        if stream is not None and _positive_int(number):
            identities[stream, number] += 1
            # Excluded out-laps may include garage time in their durations.
            # They must not claim or invalidate later timed-lap samples.
            if bounds is not None and lap.get('is_pit_out_lap') is not True:
                intervals[index] = bounds
                lap_groups[stream].append((*bounds, index))

    overlaps = defaultdict(list)
    for group in lap_groups.values():
        group.sort()
        for i, (start, end, index) in enumerate(group):
            for j in range(i + 1, len(group)):
                other_start, other_end, other_index = group[j]
                if other_start >= end:
                    break
                overlap = (max(start, other_start), min(end, other_end))
                overlaps[index].append(overlap)
                overlaps[other_index].append(overlap)

    weather_by_session, controls_by_session = defaultdict(list), defaultdict(list)
    stints_by_stream, pits_by_stream = defaultdict(list), defaultdict(list)
    for rows, groups in ((weather, weather_by_session), (race_control, controls_by_session)):
        for row in rows:
            session = row.get("session_key")
            if _positive_int(session):
                groups[int(session)].append(row)
    for rows, groups in ((stints, stints_by_stream), (pit, pits_by_stream)):
        for row in rows:
            stream = _driver_stream(row)
            if stream is not None:
                groups[stream].append(row)

    results = []
    for index, lap in enumerate(laps):
        item = {
            "lap": lap, "lap_number": lap.get("lap_number"), "lap_start_utc": None,
            "lap_end_utc": None, "samples": [], "qc": {"passed": False, "sample_count": 0},
            "context": {}, "clean": False, "quality_flags": [],
        }
        results.append(item)
        flags = item["quality_flags"]
        if index not in intervals:
            flags.append("pit_out_lap_not_aligned" if lap.get('is_pit_out_lap') is True
                         else "invalid_lap_interval_or_identity")
            continue
        start, end = intervals[index]
        stream = _driver_stream(lap)
        stamps = dates.get(stream, ())
        window = by_stream[stream][bisect_left(stamps, start):bisect_left(stamps, end)]
        entries = sorted(
            (position, stamp, row) for stamp, position, row in window
            if not any(a <= stamp < b for a, b in overlaps[index])
        )
        samples, qc = normalise_car_data(row for _, _, row in entries)
        for sample, (_, stamp, _) in zip(samples, entries):
            sample["lap_elapsed_s"] = (stamp - start).total_seconds()
        first = min((stamp for _, stamp, _ in entries), default=None)
        last = max((stamp for _, stamp, _ in entries), default=None)
        duplicate_identity = identities[stream, lap["lap_number"]] > 1
        maximum_overlap = max(((b - a).total_seconds() for a, b in overlaps[index]), default=0.0)
        qc.update(
            channel_and_timestamp_checks_passed=qc["passed"],
            duplicate_lap_identity=duplicate_identity,
            overlapping_lap_count=len(overlaps[index]),
            maximum_pairwise_overlap_s=maximum_overlap,
            max_lap_overlap_s=max_lap_overlap_s,
            ambiguous_sample_count=len(window) - len(entries),
            unassigned_invalid_timestamp_count=bad_stamps[stream],
            unassigned_invalid_stream_count=invalid_streams,
            coverage_span_s=(last - first).total_seconds() if first is not None else None,
            leading_gap_s=(first - start).total_seconds() if first is not None else None,
            trailing_gap_s=(end - last).total_seconds() if last is not None else None,
        )
        qc["passed"] = qc["passed"] and not (
            maximum_overlap > max_lap_overlap_s or duplicate_identity
            or bad_stamps[stream] or invalid_streams
        )
        context = {
            **_weather_context(weather_by_session[stream[0]], start, end, max_weather_age_s),
            **_stint_context(stints_by_stream[stream], lap["lap_number"]),
            **_event_context(lap, start, end, pits_by_stream[stream], controls_by_session[stream[0]]),
        }
        if not qc["passed"]:
            flags.append("car_data_qc_failed")
        if overlaps[index]:
            flags.append("overlapping_lap_intervals")
        if duplicate_identity:
            flags.append("duplicate_lap_identity")
        flags.extend((
            context["rainfall_summary"] if context["rainfall_summary"] == "rain_reported" else "dry_track_unverified",
            "pit_" + context["pit_status"] if context["pit_status"] == "unknown" else context["pit_status"],
            "track_" + context["track_status"],
            "validity_" + context["validity_status"],
        ))
        if context["stint_status"] != "assigned":
            flags.append("stint_" + context["stint_status"])
        item.update(
            lap_start_utc=start.isoformat(), lap_end_utc=end.isoformat(),
            samples=samples, qc=qc, context=context,
        )
    return results
