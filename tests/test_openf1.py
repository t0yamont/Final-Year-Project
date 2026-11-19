"""Offline tests for cache integrity, bounded transport, and alignment."""

from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import json
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import unittest

try:
    import requests
except ImportError:
    requests = None

from f1energy.openf1 import (
    BASE_URL, OpenF1Client, OpenF1Error, align_laps, lap_bounds, normalise_car_data,
)


START = datetime(2025, 5, 31, 14, 0, tzinfo=timezone.utc)
STREAM = {"session_key": 1, "driver_number": 44}


def _date(seconds):
    return (START + timedelta(seconds=seconds)).isoformat()


def _sample(seconds, **changes):
    return {
        **STREAM, "date": _date(seconds), "speed": 252, "rpm": 10000,
        "n_gear": 7, "throttle": 100, "brake": 0, "drs": 12, **changes,
    }


def _lap(number, seconds, duration=1):
    return {
        **STREAM, "lap_number": number, "date_start": _date(seconds),
        "lap_duration": duration, "is_pit_out_lap": False,
    }


def _response(status, body=b"[]", **headers):
    return SimpleNamespace(status_code=status, content=body, headers=headers)


@unittest.skipIf(requests is None, "OpenF1 HTTP client requires requests")
class OpenF1ClientTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.tmp_path = Path(directory.name)

    def test_only_explicit_empty_window_is_cached_with_original_404_status(self):
        params={'session_key':1,'driver_number':44,'date>':_date(0),'date<':_date(1)}
        client=OpenF1Client(self.tmp_path,get=lambda *a,**k:_response(404,b'{"detail":"No results found."}'))
        self.assertEqual(client.fetch('car_data',**params),[])
        self.assertEqual(client.records[-1]['status'],404)
        self.assertTrue(client.records[-1]['empty_result'])
        offline=OpenF1Client(self.tmp_path,offline=True)
        self.assertEqual(offline.fetch('car_data',**params),[])
        self.assertTrue(offline.records[-1]['cache_hit'])
        wrong=OpenF1Client(self.tmp_path/'wrong',get=lambda *a,**k:_response(404,b'{"detail":"No results found."}'))
        with self.assertRaises(OpenF1Error):wrong.fetch('weather',session_key=1)
        unknown=OpenF1Client(self.tmp_path/'unknown',get=lambda *a,**k:_response(404,b'{"detail":"Not found"}'))
        with self.assertRaises(OpenF1Error):unknown.fetch('car_data',**params)

    def test_network_retries_paced_then_cache_hit_and_new_query(self):
        tmp_path = self.tmp_path
        clock, calls = [0.0], []
        responses = iter((
            _response(429, **{"Retry-After": "3"}),
            _response(503),
            _response(200, b'[{"speed":100}]'),
            _response(200),
        ))

        def sleep(seconds):
            clock[0] += seconds

        def get(url, *, timeout, allow_redirects, auth):
            assert timeout == (10, 25)
            assert allow_redirects is False
            assert auth(url) == url
            calls.append((clock[0], url))
            return next(responses)

        client = OpenF1Client(tmp_path, get=get, sleep=sleep, monotonic=lambda: clock[0])
        params = {"session_key": 1, "driver_number": 44, "date>": _date(0), "date<": _date(1)}
        assert client.fetch("car_data", **params) == [{"speed": 100}]
        assert client.fetch("car_data", **params) == [{"speed": 100}]
        assert client.fetch("weather", session_key=1) == []
        self.assertEqual([round(t, 3) for t, _ in calls], [0, 3, 7.2, 9.3])
        assert calls[0][1].startswith(f"{BASE_URL}/car_data?session_key=1&driver_number=44")
        assert "&date%3E=" in calls[0][1] and "&date%3C=" in calls[0][1]
        assert [r["status"] for r in client.records] == [429, 503, 200, 200, 200]
        cached = client.records[3]
        assert cached["cache_hit"] and cached["rows"] == 1
        assert cached["sha256"] == hashlib.sha256(b'[{"speed":100}]').hexdigest()


    def test_offline_cache_uses_audit_format_and_rejects_corruption(self):
        for fault in ("body", "meta", "partial"):
            with self.subTest(fault=fault):
                self._check_corrupt_cache(fault)

    def _check_corrupt_cache(self, fault):
        tmp_path = self.tmp_path
        url = f"{BASE_URL}/sessions?year=2025"
        key = hashlib.sha256(url.encode()).hexdigest()
        body = b'[{"session_key":1}]'
        raw, meta = tmp_path / f"{key}.json", tmp_path / f"{key}.meta.json"
        raw.write_bytes(body)
        info = {
            "url": url, "status": 200, "retrieved_utc": START.isoformat(),
            "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "cache_hit": False,
        }
        meta.write_text(json.dumps(info))

        def get(*args, **kwargs):
            self.fail("offline client made a network call")

        client = OpenF1Client(tmp_path, offline=True, get=get)
        assert client.fetch("sessions", year=2025) == [{"session_key": 1}]
        assert client.records[-1]["cache_hit"]
        with self.assertRaisesRegex(OpenF1Error, "cache miss"):
            client.fetch("sessions", year=2024)
        assert client.records[-1]["status"] == "cache_miss"
        if fault == "body":
            raw.write_bytes(body.replace(b"1", b"2"))
        elif fault == "meta":
            meta.write_text(json.dumps(dict(info, url=url + "0")))
        else:
            meta.unlink()
        with self.assertRaisesRegex(OpenF1Error, "Invalid OpenF1 cache entry"):
            client.fetch("sessions", year=2025)
        assert client.records[-1]["status"] == "cache_corrupt"


    def test_unusable_response_is_explicit_and_not_cached(self):
        cases = [
            (400, b"[]", "HTTP 400"),
            (200, b'{"data":[]}', "array of objects"),
            (200, b'[{"value":NaN}]', "numeric constant"),
            (200, b'[{"value":1e999}]', "non-finite"),
        ]
        for status, body, message in cases:
            with self.subTest(status=status, body=body):
                client = OpenF1Client(self.tmp_path, get=lambda *a, **kw: _response(status, body))
                with self.assertRaisesRegex(OpenF1Error, message):
                    client.fetch("sessions", year=2025)
                self.assertEqual(len(client.records), 1)
                self.assertEqual(list(self.tmp_path.iterdir()), [])


    def test_retry_budget_and_retry_after(self):
        tmp_path = self.tmp_path
        def timeout(*args, **kwargs):
            raise requests.Timeout("test timeout")

        client = OpenF1Client(tmp_path, get=timeout, max_attempts=1)
        with self.assertRaisesRegex(OpenF1Error, "test timeout"):
            client.fetch("sessions", year=2025)
        assert client.records[-1]["status"] == "request_failed"
        client = OpenF1Client(
            tmp_path, get=lambda *a, **kw: _response(429, **{"Retry-After": "120"}),
            sleep=lambda _: self.fail("Retry-After exceeds the configured budget"),
        )
        with self.assertRaisesRegex(OpenF1Error, "exceeds retry budget"):
            client.fetch("sessions", year=2025)
        assert len(client.records) == 1


class OpenF1AlignmentTests(unittest.TestCase):
    def test_normalisation_preserves_unknown_brake_and_native_utc_values(self):
        rows = [_sample(0, date="2025-05-31T15:00:00+01:00", brake=100),
                _sample(0.25, brake=None), _sample(0.5)]
        samples, qc = normalise_car_data(rows)
        assert samples[0]["date_utc"] == _date(0)
        assert samples[0]["source_date"] == rows[0]["date"]
        assert samples[0]["speed_kmh"] == 252
        assert samples[0]["speed_mps"] == 70
        assert [row["brake"] for row in samples] == [True, None, False]
        assert qc["missing_counts"]["brake"] == 1
        assert qc["maximum_positive_gap_s"] == 0.25
        assert not qc["passed"]
        assert normalise_car_data([rows[0], rows[2]])[1]["passed"]


    def test_timestamp_and_channel_errors_fail_qc(self):
        rows = [
            _sample(1), _sample(1, date="2025-05-31T15:00:01+01:00", speed=200),
            _sample(0, brake=True, rpm=-1, speed=-1, throttle=101, drs=99, n_gear=9),
            _sample(2, date="2025-05-31T14:00:02"),
        ]
        samples, qc = normalise_car_data(rows)
        assert qc["invalid_counts"] == dict.fromkeys(("speed", "rpm", "n_gear", "throttle", "brake", "drs"), 1)
        assert qc["duplicate_timestamp_count"] == qc["conflicting_duplicate_timestamp_count"] == 1
        assert qc["out_of_order_step_count"] == qc["invalid_timestamp_count"] == 1
        assert samples[2]["brake"] is None and samples[3]["date_utc"] is None
        assert not qc["passed"]


    def test_adjacent_lap_boundary_is_exclusive_and_stream_scoped(self):
        laps = [_lap(1, 0), _lap(2, 1)]
        car = [_sample(0), _sample(0.5), _sample(1), _sample(1.5), _sample(2),
               _sample(0.8, driver_number=16), _sample(1.8, session_key=2)]
        first, second = align_laps(laps, car)
        assert lap_bounds(laps[0]) == (START, START + timedelta(seconds=1))
        assert [r["date_utc"] for r in first["samples"]] == [_date(0), _date(0.5)]
        assert [r["date_utc"] for r in second["samples"]] == [_date(1), _date(1.5)]
        assert [r["lap_elapsed_s"] for r in second["samples"]] == [0, 0.5]
        assert first["qc"]["passed"] and second["qc"]["passed"]
        assert not first["clean"] and not second["clean"]


    def test_overlap_and_unlocatable_timestamps_fail_lap_qc(self):
        laps = [_lap(1, 0, 2), _lap(2, 1, 2)]
        car = [_sample(0), _sample(0.5), _sample(1), _sample(1.5),
               _sample(2), _sample(2.5), _sample(2.8, date=None)]
        first, second = align_laps(laps, car)
        for item in (first, second):
            assert item["qc"]["overlapping_lap_count"] == 1
            assert item["qc"]["ambiguous_sample_count"] == 2
            assert item["qc"]["unassigned_invalid_timestamp_count"] == 1
            assert not item["qc"]["passed"]
        assert [r["date_utc"] for r in first["samples"]] == [_date(0), _date(0.5)]
        assert [r["date_utc"] for r in second["samples"]] == [_date(2), _date(2.5)]


    def test_small_boundary_overlap_excludes_ambiguous_samples_without_double_assignment(self):
        laps = [_lap(1, 0, 2), _lap(2, 1.75, 2)]
        car = [_sample(t) for t in (0, .5, 1, 1.5, 1.8, 2, 2.5, 3, 3.5)]
        strict = align_laps(laps, car)
        self.assertTrue(all(not x['qc']['passed'] for x in strict))
        allowed = align_laps(laps, car, max_lap_overlap_s=.5)
        self.assertTrue(all(x['qc']['passed'] for x in allowed))
        self.assertTrue(all(x['qc']['maximum_pairwise_overlap_s'] == .25 for x in allowed))
        stamps = [s['date_utc'] for x in allowed for s in x['samples']]
        self.assertNotIn(_date(1.8), stamps)
        self.assertEqual(len(stamps), len(set(stamps)))
        self.assertEqual(allowed[1]['qc']['leading_gap_s'], .25)
        self.assertEqual(allowed[1]['qc']['trailing_gap_s'], .25)
        duplicate = align_laps([_lap(1,0,2), _lap(2,0,2)], car, max_lap_overlap_s=.5)
        self.assertTrue(all(not x['qc']['passed'] for x in duplicate))

    def test_outlap_garage_duration_does_not_mask_a_timed_lap(self):
        outlap = _lap(1, 0, 100)
        outlap['is_pit_out_lap'] = True
        timed = _lap(2, 10, 2)
        timed['segments_sector_1'] = [2048,2049,2051]
        a,b = align_laps([outlap,timed], [_sample(10),_sample(10.5),_sample(11)])
        self.assertEqual(a['samples'], [])
        self.assertIn('pit_out_lap_not_aligned',a['quality_flags'])
        self.assertTrue(b['qc']['passed'])
        self.assertEqual(b['context']['track_status'],'unknown')
        [flagged] = align_laps([timed], [_sample(10),_sample(11)],
            race_control=[{'session_key':1,'date':_date(10),'flag':'YELLOW'}])
        self.assertEqual(flagged['context']['track_status'],'flag_reported')

    def test_context_rejects_stale_and_future_weather_and_ambiguous_stints(self):
        weather = [
            {"session_key": 1, "date": _date(-121), "rainfall": 0},
            {"session_key": 1, "date": _date(0.5), "rainfall": 1},
            {"session_key": 2, "date": _date(0), "rainfall": 0},
        ]
        stints = [
            {**STREAM, "lap_start": 1, "lap_end": 2},
            {**STREAM, "lap_start": 2, "lap_end": 3},
            {**STREAM, "lap_start": 3, "lap_end": None},
        ]
        a, b = align_laps([_lap(1, 0), _lap(2, 1)], [], weather=weather, stints=stints)
        assert a["context"]["weather_at_start"] is None
        assert a["context"]["weather_start_status"] == "stale"
        assert a["context"]["rainfall_summary"] == "rain_reported"
        assert a["context"]["stint_status"] == "assigned"
        assert b["context"]["weather_at_start"] == weather[1]
        assert b["context"]["weather_age_at_start_s"] == 0.5
        assert b["context"]["stint_status"] == "ambiguous"
        assert b["context"]["stint"] is None


    def test_unknown_context_never_means_clean(self):
        [item] = align_laps(
            [_lap(1, 0)], [_sample(0), _sample(0.5)],
            weather=[{"session_key": 1, "date": _date(0.5), "rainfall": 0}],
        )
        context = item["context"]
        assert context["weather_start_status"] == "missing"
        assert context["weather_at_start"] is None
        assert context["rainfall_summary"] == "unknown"
        assert not context["dry_track_verified"]
        assert context["pit_status"] == context["track_status"] == context["validity_status"] == "unknown"
        assert item["qc"]["passed"]
        assert not item["clean"]
