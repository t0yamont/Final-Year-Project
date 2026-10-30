import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from f1energy.dynamics import State, Vehicle, step

class DynamicsTests(unittest.TestCase):
    def test_lossless_constant_power_identity(self):
        s, evidence = step(State(20, 10000), Vehicle(800, 1000, 500, 0.8, 0), 500, 2)
        self.assertAlmostEqual(s.speed_m_per_s, math.sqrt(400 + 2*1500*2/800))
        self.assertAlmostEqual(s.energy_j, 8750)
        self.assertAlmostEqual(evidence['kinetic_change_j'], 3000)

    def test_drag_energy_balance_and_monotone_decay(self):
        vehicle = Vehicle(800, 0, 500, 1, 0.4)
        s, e = step(State(40, 10000), vehicle, 0, 1)
        self.assertLess(s.speed_m_per_s, 40)
        self.assertAlmostEqual(e['drag_work_j'], 0.4*s.speed_m_per_s**3)
        self.assertAlmostEqual(e['kinetic_change_j'] + e['drag_work_j'], 0)

    def test_drag_refinement_towards_analytic_solution(self):
        vehicle = Vehicle(800, 0, 0, 1, 0.4)
        exact = 40 / (1 + 0.4*40*10/800)
        errors = []
        for n in (10, 100, 1000):
            s = State(40, 0)
            for _ in range(n):
                s, _ = step(s, vehicle, 0, 10/n)
            errors.append(abs(s.speed_m_per_s-exact))
        self.assertLess(errors[1], errors[0]/5)
        self.assertLess(errors[2], errors[1]/5)

    def test_depletion_preserves_reserve_and_accounts_losses(self):
        s, e = step(State(20, 1100), Vehicle(800, 0, 1000, 0.8, 0), 1000, 2, 100)
        self.assertEqual(s.energy_j, 100)
        self.assertEqual(e['executed_deployment_w'], 400)
        self.assertEqual(e['electrical_wheel_work_j'], 800)
        self.assertEqual(e['battery_draw_j'], 1000)

    def test_invalid_inputs(self):
        v = Vehicle(800, 0, 1000, 0.8, 0)
        for action, duration, reserve in [(1001, 1, 0), (-1, 1, 0), (0, 0, 0), (0, 1, 101), (float('nan'), 1, 0)]:
            with self.assertRaises(ValueError):
                step(State(20, 100), v, action, duration, reserve)

if __name__ == '__main__':
    unittest.main()
