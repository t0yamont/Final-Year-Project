import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from f1energy.power_lap import *

class PowerLapTests(unittest.TestCase):
    def test_exact_constant_force_braking_accounting(self):
        v=PowerVehicle(base_power_w=0,electrical_limit_w=0,drag_kg_per_m=0)
        s,r=spatial_step(v,PowerState(30,1000),50,20,0)
        self.assertAlmostEqual(r['duration_s'],2)
        self.assertAlmostEqual(r['net_acceleration_m_per_s2'],-5)
        self.assertAlmostEqual(r['friction_braking_work_j'],200000)
        self.assertAlmostEqual(r['energy_residual_j'],0)
    def test_drag_coasting_converges_to_exact_spatial_solution(self):
        v=PowerVehicle(base_power_w=0,electrical_limit_w=0)
        exact=40*math.exp(-v.drag_kg_per_m*1000/v.mass_kg)
        errors=[]
        for n in [10,20,40]:
            s,_=simulate(v,[1000/n]*n,[100]*(n+1),PowerState(40,0),lambda i,s:0)
            errors.append(abs(s.speed_m_per_s-exact))
        self.assertLess(errors[1],errors[0]/3)
        self.assertLess(errors[2],errors[1]/3)
    def test_power_only_converges_to_exact(self):
        v=PowerVehicle(drag_kg_per_m=0,electrical_limit_w=0)
        exact=(20**3+3*v.base_power_w*100/v.mass_kg)**(1/3)
        errors=[]
        for n in [10,20,40]:
            s,_=simulate(v,[100/n]*n,[100]*(n+1),PowerState(20,0),lambda i,s:0)
            errors.append(abs(s.speed_m_per_s-exact))
        self.assertLess(errors[1],errors[0]/3)
        self.assertLess(errors[2],errors[1]/3)
    def test_action_energy_reserve_and_balance(self):
        v=PowerVehicle();start=PowerState(20,11000)
        off,_=simulate(v,[5]*40,[100]*40+[20],start,lambda i,s:0,1000)
        on,rows=simulate(v,[5]*40,[100]*40+[20],start,lambda i,s:1,1000)
        self.assertLess(on.elapsed_s,off.elapsed_s)
        self.assertGreaterEqual(on.energy_j,1000)
        self.assertAlmostEqual(start.energy_j-on.energy_j,sum(r['battery_draw_j'] for r in rows))
        self.assertLess(max(abs(r['energy_residual_j']) for r in rows),1e-6)
        self.assertTrue(any(r['friction_braking_work_j']>0 for r in rows))
    def test_infeasible_braking_rejected(self):
        with self.assertRaises(ValueError):spatial_step(PowerVehicle(),PowerState(100,0),1,10,0)
    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):spatial_step(PowerVehicle(),PowerState(20,0),0,20,0)
        with self.assertRaises(ValueError):spatial_step(PowerVehicle(),PowerState(20,0),1,20,2)

if __name__=='__main__':unittest.main()
