import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/'scripts/prepare_calibration_data.py'
spec=importlib.util.spec_from_file_location('prepare_data',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def row(time,speed):
    return dict(Time=time,Speed=str(speed),Throttle='100',Brake='False',nGear='7',DRS='12')

class CalibrationDataTests(unittest.TestCase):
    def test_si_derivative(self):
        data,reasons=m.windows([row('0 days 00:00:00.000',180),row('0 days 00:00:00.500',183.6)],4)
        self.assertEqual(reasons,{})
        self.assertAlmostEqual(data[0]['speed_start_m_per_s'],50)
        self.assertAlmostEqual(data[0]['acceleration_m_per_s2'],2)
    def test_no_bridge_across_gap_or_invalid(self):
        data,reasons=m.windows([row('0 days 00:00:00',100),row('0 days 00:00:02',110),row('bad',120),row('0 days 00:00:02.5',130)],4)
        self.assertEqual(data,[])
        self.assertEqual(reasons,{'gap_above_limit':1,'invalid_or_missing_value':2})
    def test_order_not_repaired(self):
        data,reasons=m.windows([row('0 days 00:00:01',100),row('0 days 00:00:00',110)],4)
        self.assertEqual(data,[]);self.assertEqual(reasons,{'nonincreasing_time':1})
