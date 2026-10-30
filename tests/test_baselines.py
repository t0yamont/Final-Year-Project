import unittest
from dataclasses import replace
from f1energy.lap import default_scenario,Scenario,Segment
from f1energy.baselines import dynamic_programming,exhaustive
class BaselineTests(unittest.TestCase):
    def test_replay_feasible_and_no_better_than_exhaustive(self):
        s=default_scenario();exact=exhaustive(s)
        for step in [100000.,10000.,1000.]:
            dp=dynamic_programming(s,step)
            self.assertTrue(dp['feasible'])
            self.assertGreaterEqual(dp['elapsed_s']+1e-9,exact['elapsed_s'])
            self.assertLessEqual(dp['elapsed_s'],dp['grid_objective_s']+1e-8)
    def test_one_segment_matches_exhaustive(self):
        s=replace(default_scenario(),segments=(Segment(180,25),))
        self.assertAlmostEqual(dynamic_programming(s,1000)['elapsed_s'],exhaustive(s)['elapsed_s'])
    def test_refinement_reaches_tiny_reference(self):
        s=default_scenario()
        self.assertAlmostEqual(dynamic_programming(s,100)['elapsed_s'],exhaustive(s)['elapsed_s'],places=8)
    def test_variable_speed_state_supported(self):
        s=replace(default_scenario(),segments=(Segment(1,100),))
        self.assertTrue(dynamic_programming(s,1000)['feasible'])
    def test_invalid_grid(self):
        for step in [0,-1,float('nan')]:
            with self.assertRaises(ValueError):dynamic_programming(default_scenario(),step)
