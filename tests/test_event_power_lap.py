from pathlib import Path
import sys,math,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from f1energy.event_power_lap import *

class EventTests(unittest.TestCase):
 def test_depletion_event_exact_constant_power_time(self):
  v=PowerVehicle(base_power_w=1000,electrical_limit_w=1000,drag_kg_per_m=0)
  s,r=integrate_segment(v,PowerState(20,1000),100,100,1,reserve_j=100,max_speed_m_per_s=100)
  e=next(e for e in r['events'] if e['kind']=='depletion')
  t=900*.9/1000
  expected_v=math.sqrt(400+2*2000*t/800)
  expected_x=800/(3*2000)*(expected_v**3-20**3)
  self.assertAlmostEqual(e['position_m'],expected_x,places=6)
  self.assertAlmostEqual(s.energy_j,100,places=6)
  self.assertAlmostEqual(r['electrical_work_j'],810,places=6)
 def test_exact_braking_transition_without_drag(self):
  v=PowerVehicle(base_power_w=0,electrical_limit_w=0,drag_kg_per_m=0)
  s,r=integrate_segment(v,PowerState(30,0),100,20,0)
  e=next(e for e in r['events'] if e['kind']=='braking')
  self.assertAlmostEqual(e['position_m'],100-(900-400)/16,places=7)
  self.assertAlmostEqual(s.elapsed_s,e['position_m']/30+(30-20)/8,places=7)
  self.assertAlmostEqual(s.speed_m_per_s,20,places=7)
  self.assertAlmostEqual(r['friction_braking_work_j'],200000,places=5)
 def test_output_grid_independence(self):
  outputs=[integrate_segment(PowerVehicle(),PowerState(20,450000),400,30,.6,50000,sample_spacing_m=h) for h in [40,10,2.5]]
  self.assertEqual(outputs[0][0],outputs[1][0]);self.assertEqual(outputs[1][0],outputs[2][0])
  self.assertLess(abs(outputs[0][1]['energy_residual_j']),.01)
 def test_speed_ceiling_event_and_cruise(self):
  s,r=integrate_segment(PowerVehicle(),PowerState(20,1e9),1000,30,1,max_speed_m_per_s=30,sample_spacing_m=5)
  self.assertTrue(any(e['kind']=='speed_ceiling' for e in r['events']))
  self.assertLessEqual(max(x['speed_m_per_s'] for x in r['samples']),30+1e-6)
  self.assertAlmostEqual(s.speed_m_per_s,30,places=6)
 def test_cruise_depletion_returns_to_power_limited_motion(self):
  v=PowerVehicle(base_power_w=1000,electrical_limit_w=60000)
  state,r=integrate_segment(v,PowerState(20,500000),2000,30,1,reserve_j=50000,max_speed_m_per_s=30,sample_spacing_m=10)
  self.assertEqual([e['kind'] for e in r['events']],['speed_ceiling','depletion'])
  self.assertLess(state.speed_m_per_s,30)
  self.assertAlmostEqual(state.energy_j,50000,places=6)
  self.assertLess(abs(r['energy_residual_j']),.01)
  self.assertLessEqual(max(x['speed_m_per_s'] for x in r['samples']),30+1e-6)
 def test_entry_on_braking_envelope_brakes_immediately(self):
  v=PowerVehicle(base_power_w=100000,electrical_limit_w=60000,drag_kg_per_m=0)
  initial_speed=math.sqrt(20**2+2*8*50)
  state,r=integrate_segment(v,PowerState(initial_speed,500000),50,20,1)
  self.assertAlmostEqual(state.speed_m_per_s,20,places=7)
  self.assertEqual(r['battery_draw_j'],0)
  self.assertEqual(r['base_work_j'],0)
  self.assertGreater(r['friction_braking_work_j'],0)
 def test_infeasible_entry(self):
  with self.assertRaises(ValueError):integrate_segment(PowerVehicle(),PowerState(100,0),1,10,0)

if __name__=='__main__':unittest.main()
