import unittest
from f1energy.clean_laps import selection,time_quality

class CleanLapTests(unittest.TestCase):
    def test_unresolved_is_not_eligibility(self):
        row=selection(dict(IsAccurate=True,TrackStatus='1'))
        self.assertTrue(row['candidate'])
        self.assertFalse(row['modelling_eligible'])
        self.assertIn('deletion_unknown',row['unresolved_flags'])
    def test_pit_and_deleted_exclusion(self):
        row=selection(dict(IsAccurate=True,TrackStatus='1',Deleted=True,PitOutTime='x'))
        self.assertFalse(row['candidate'])
        self.assertEqual(row['exclusion_reasons'],['pit_in_or_out','deleted'])
    def test_order_and_gaps_not_hidden(self):
        result=time_quality([0,.25,.25,.1,None,2,3.2])
        self.assertEqual(result['nonincreasing_steps'],2)
        self.assertEqual(result['missing_time_count'],1)
        self.assertEqual(result['gaps_over_1s'],1)
