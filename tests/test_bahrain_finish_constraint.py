import json
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from bahrain_finish_constraint import build_constrained_env, prepare_constraint
from bahrain_pace_model import build_env


class FinishConstraintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = json.loads((ROOT / "results/bahrain-pace-calibration-001/model.json").read_bytes())
        cls.cells = 80
        cls.certificate = prepare_constraint(cls.model, cls.cells)

    def test_counterfactual_previews_do_not_advance_real_plant(self):
        constrained = build_constrained_env(self.model, self.cells, self.certificate)
        bare = build_env(self.model, self.cells)
        constrained.reset()
        bare.reset()
        for _ in range(bare.blocks):
            obs, _, done, _, block = constrained.step([0.])
            executed = block["finish_constraint"]["issued_action"]
            bare_obs, _, bare_done, _, control = bare.step([executed])
            np.testing.assert_array_equal(obs, bare_obs)
            self.assertEqual(done, bare_done)
            self.assertEqual(block["state"], control["state"])
            self.assertEqual(constrained.discharged_j, bare.discharged_j)
            self.assertEqual(constrained.recovered_j, bare.recovered_j)
        self.assertGreater(constrained.constraint_stats["interventions"], 0)
        self.assertLessEqual(constrained.constraint_stats["lookahead_transitions"], 12)
        self.assertLess(abs(bare.state.speed_m_per_s - bare.initial_speed), 1e-5)

    def test_discharge_limit_protects_backup_even_with_charge_available(self):
        env = build_constrained_env(self.model, self.cells, self.certificate)
        env.reset()
        env.env.discharged_j = env.regeneration.deployment_limit_j - self.certificate["protected_draw_j"]
        _, _, _, _, block = env.step([1.])
        self.assertLess(block["action"], 1e-12)
        self.assertLess(block["battery_discharged_j"], 1e-5)
        self.assertTrue(block["finish_constraint"]["changed"])
        self.assertEqual(block["finish_constraint"]["lookahead_transitions"], 0)
