import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('openf1_motion',Path(__file__).resolve().parents[1]/'scripts/prepare_openf1_motion.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def sample(time,speed,**changes):
    row={'date_utc':f'2025-01-01T00:00:{time}+00:00','speed_mps':str(speed),'throttle_pct':'100',
         'brake':'False','gear':'7','drs':'12'}
    row.update(changes)
    return row


class MotionWindowsTests(unittest.TestCase):
    def test_signed_acceleration_retained(self):
        rows,ex=m.pairs([sample('00.000',70),sample('00.500',69)])
        self.assertEqual(rows[0]['acceleration_mps2'],-2)
        self.assertEqual(ex,{})

    def test_no_bridge_over_gap_missing_or_state_transition(self):
        for b,reason in [(sample('02.000',71),'pair_gap_over_limit'),
                         (sample('00.300',71,brake=''),'braking_or_unknown'),
                         (sample('00.300',71,gear='8'),'gear_change_or_unknown')]:
            rows,ex=m.pairs([sample('00.000',70),b])
            self.assertEqual(rows,[])
            self.assertEqual(ex,{reason:1})
