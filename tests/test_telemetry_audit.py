import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from f1energy.telemetry_audit import describe_samples, lap_flags, run_session_audit

class TelemetryAuditTests(unittest.TestCase):
    def test_missing_channels_and_false_brake(self):
        report = describe_samples([{'Speed': 100, 'Brake': False}, {'Speed': float('nan')}])
        self.assertEqual(report['missing_counts']['Speed'], 1)
        self.assertEqual(report['missing_counts']['Brake'], 1)
        self.assertEqual(report['missing_counts']['RPM'], 2)
        self.assertEqual(report['sample_count'], 2)

    def test_unknown_quality_fails_closed(self):
        self.assertEqual(len(lap_flags({})), 3)
        clean = dict(IsAccurate=True, Deleted=False, TrackStatus='1')
        self.assertEqual(lap_flags(clean), [])
        clean['PitOutTime'] = '0 days 00:01:00'
        self.assertEqual(lap_flags(clean), ['pit_in_or_out'])

    def test_limits_checked_before_dependency_or_network(self):
        with self.assertRaises(ValueError):
            run_session_audit(2025, 1, 'Q', '1', 'unused', max_laps=4)
        with self.assertRaises(ValueError):
            run_session_audit(2025, 0, 'Q', '1', 'unused')
