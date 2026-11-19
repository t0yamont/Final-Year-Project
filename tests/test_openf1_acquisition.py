import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('openf1_acquisition', ROOT/'scripts/acquire_openf1_dataset.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AcquisitionContractTests(unittest.TestCase):
    def test_frozen_roles_have_no_cross_event_leakage(self):
        plan = json.loads((ROOT/'configs/openf1_dataset_plan.json').read_text())
        events = plan['events']
        self.assertEqual(len({e['meeting_key'] for e in events}), 8)
        all_keys = [k for e in events for k in e['session_keys']]
        self.assertEqual(len(all_keys), len(set(all_keys)))
        for key in (1257,1262):
            self.assertEqual(next(e['role'] for e in events if e['meeting_key']==key), 'development')
        self.assertNotIn(1260, {e['meeting_key'] for e in events})  # Imola is not Monza.
        self.assertNotIn(1253, {e['meeting_key'] for e in events})  # No pre-season testing.

    def test_unknown_weather_or_lap_edges_do_not_pass_screen(self):
        item={'qc':{'passed':True,'maximum_positive_gap_s':.3,'leading_gap_s':.2,'trailing_gap_s':.2},
              'lap':{'is_pit_out_lap':False},
              'context':{'weather_start_status':'matched','rainfall_summary':'no_rain_reported_at_samples',
                         'stint_status':'assigned','stint':{'compound':'SOFT'}}}
        good=module.screening(item,1)
        self.assertTrue(good['conditional_motion_candidate'])
        self.assertFalse(good['verified_clean_lap'])
        item['context']['weather_start_status']='stale'
        self.assertFalse(module.screening(item,1)['conditional_motion_candidate'])
        item['context']['weather_start_status']='matched'
        item['qc']['trailing_gap_s']=2
        self.assertFalse(module.screening(item,1)['conditional_motion_candidate'])

    def test_resume_rejects_changed_output(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);path=root/'car.csv'
            path.write_bytes(b'original')
            record={'outputs':{'car.csv':module.digest(path)}}
            module.verify_outputs(root,record)
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):module.verify_outputs(root,record)
