import json
import math
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from bahrain_free_finish import build_free_env, free_rollout
from bahrain_pace_model import build_env
from f1energy.circuit_control import rollout


class FreeFinishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = json.loads((ROOT / "results/bahrain-pace-calibration-001/model.json").read_text())

    def test_backward_braking_from_last_cell_on_both_evaluation_grids(self):
        for cells in (160, 320):
            with self.subTest(cells=cells):
                fixed = build_env(self.model, cells)
                free = build_free_env(self.model, cells)
                caps = fixed.grid.cell_speed_cap_mps
                np.testing.assert_array_equal(caps, free.grid.cell_speed_cap_mps)
                bounds = np.empty(len(caps) + 1)
                bounds[-1] = caps[-1]
                for i in range(len(caps) - 1, -1, -1):
                    vehicle = fixed.regime_vehicles[i // cells]
                    k = vehicle.drag_kg_per_m
                    m = vehicle.mass_kg
                    x = 2 * k * fixed.grid.lengths_m[i] / m
                    v2 = (bounds[i + 1] ** 2 * math.exp(x)
                          + m * vehicle.friction_deceleration_m_per_s2 / k * math.expm1(x))
                    bounds[i] = min(caps[i], caps[i-1], math.sqrt(v2))
                np.testing.assert_allclose(free.envelope, bounds, rtol=0, atol=1e-10)
                self.assertTrue((free.envelope >= fixed.envelope - 1e-10).all())
                self.assertGreater(free.envelope[-1], fixed.envelope[-1])
                self.assertEqual(free.initial_speed, fixed.initial_speed)
                self.assertEqual(free.initial_energy, fixed.initial_energy)

    def test_crossing_speed_is_measured_and_feasibility_still_checks_energy(self):
        env = build_free_env(self.model, 40)
        plain = rollout(env, lambda _: [0.0])
        free = free_rollout(env, lambda _: [0.0])
        self.assertFalse(plain["feasible"])
        self.assertTrue(free["feasible"])
        self.assertEqual(free["trace"], plain["trace"])
        self.assertEqual(free["finish_speed_mps"], free["trace"][-1]["state"]["speed_m_per_s"])
        self.assertGreater(abs(free["finish_speed_mps"] - env.initial_speed), 1e-4)
        self.assertAlmostEqual(free["final_energy_j"], env.initial_energy + env.recovered_j - env.discharged_j)
