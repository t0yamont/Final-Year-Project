import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from f1energy.lap import *

class LapTests(unittest.TestCase):
    def test_deployment_improves_time(self):
        sc=default_scenario()
        off,_=run_policy(sc,lambda s:0)
        on,rows=run_policy(sc,lambda s:1)
        self.assertLess(on.elapsed_s,off.elapsed_s)
        self.assertGreaterEqual(on.energy_j,sc.reserve_j)
        self.assertAlmostEqual(sc.initial_energy_j-on.energy_j,sum(r['battery_draw_j'] for r in rows))
    def test_exact_phase_distance_and_work_balance(self):
        sc=default_scenario(); before=initial_state(sc)
        after,r=transition(sc,before,0.5)
        self.assertAlmostEqual(r['acceleration_distance_m']+r['braking_distance_m'],sc.segments[0].length_m)
        change=0.5*sc.mass_kg*(after.speed_m_per_s**2-before.speed_m_per_s**2)
        self.assertAlmostEqual(change,r['base_work_j']+r['electrical_wheel_work_j']-r['braking_work_j'])
        self.assertGreater(r['braking_distance_m'],0)
        self.assertAlmostEqual(after.speed_m_per_s,sc.segments[0].exit_speed_cap_m_per_s)
    def test_no_braking_when_cap_not_reached(self):
        sc=Scenario((Segment(1,100),)); state,r=transition(sc,initial_state(sc),0)
        self.assertEqual(r['braking_distance_m'],0)
        self.assertAlmostEqual(state.speed_m_per_s,math.sqrt(400+4))
    def test_infeasible_entry_rejected(self):
        sc=Scenario((Segment(1,1),))
        with self.assertRaises(ValueError):transition(sc,initial_state(sc),0)
    def test_zero_usable_energy(self):
        sc=Scenario((Segment(100,20),),initial_energy_j=50000)
        state,r=transition(sc,initial_state(sc),1)
        self.assertEqual(r['executed_force_n'],0)
        self.assertEqual(state.energy_j,50000)

if __name__=='__main__':unittest.main()
