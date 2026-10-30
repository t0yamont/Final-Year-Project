import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from f1energy.availability import collect, cohort

class Schedule:
    def __init__(self, events):
        self.events = events
    def to_dict(self, orient):
        return self.events

class AvailabilityTests(unittest.TestCase):
    def test_testing_sprints_and_unknown_support(self):
        def fetch(year, **options):
            self.assertEqual(options, dict(include_testing=True, backend='fastf1'))
            return Schedule([dict(RoundNumber=0, EventName='Testing', Session1='Practice 1'),
                             dict(RoundNumber=1, EventName='Fixture', Session1='Sprint',
                                  Session2='Qualifying', F1ApiSupport=float('nan'))])
        rows, failures = collect([2025], fetch)
        self.assertFalse(failures)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]['round'], 0)
        self.assertTrue(all(r['source_support'] is None for r in rows))
        self.assertTrue(all(r['telemetry_status'] == 'not_checked' for r in rows))

    def test_empty_and_failed_seasons_remain_visible(self):
        def fetch(year, **options):
            if year == 2024:
                raise RuntimeError('fixture outage')
            return Schedule([])
        rows, failures = collect([2024, 2025], fetch)
        self.assertEqual(rows, [])
        self.assertEqual([f['season'] for f in failures], [2024, 2025])

    def test_literal_none_session_is_not_catalogued(self):
        rows, errors = collect([2025], lambda *a, **kw: Schedule([
            dict(RoundNumber=1, EventName='Fixture', Session1='Qualifying', Session2='None')]))
        self.assertFalse(errors)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['session'], 'Qualifying')

    def test_cohorts(self):
        self.assertEqual([cohort(y) for y in (2021, 2022, 2025, 2026)],
                         ['pre_2022', '2022_2025', '2022_2025', '2026_onward'])

if __name__ == '__main__':
    unittest.main()
