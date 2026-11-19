"""Protect the paired-grid design and failure-sensitive scientific gate."""
import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('circuit_sensitivity', ROOT / 'scripts/evaluate_circuit_sensitivity.py')
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


class SensitivityTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads((ROOT / 'configs/circuit_sensitivity_protocol.json').read_text())

    def test_predeclared_budget_and_physical_grid_pairing(self):
        study.validate_protocol(self.protocol)
        cases = study.planned_cases(self.protocol)
        self.assertEqual(len(cases) * 8 * 2, 160)
        self.assertEqual(sum(c['blocks'] == 110 for _, c in cases), 1)
        for _, cadence in cases:
            self.assertEqual(cadence['blocks'] * cadence['coarse_cells_per_block'], 4400)
            self.assertEqual(cadence['blocks'] * cadence['fine_cells_per_block'], 8800)
        self.protocol['cadences'][1]['fine_cells_per_block'] = 160
        with self.assertRaises(ValueError):
            study.validate_protocol(self.protocol)

    def test_one_at_a_time_does_not_mutate_nominal(self):
        nominal = dict(vehicle=dict(mass_kg=800., drag_kg_per_m=1.), smoothing_sigma_m=10.)
        original = copy.deepcopy(nominal)
        changed = study.scenario_reference(nominal, self.protocol['scenarios'][1])
        self.assertEqual(changed['vehicle']['mass_kg'], 720.)
        self.assertEqual(changed['vehicle']['drag_kg_per_m'], 1.)
        self.assertEqual(nominal, original)

    def test_gain_gate_uses_matched_zero_and_preserves_failure(self):
        rows = [dict(grid=g, policy=p, duration_s=t, status='completed', audit=dict(passed=True))
                for g, p, t in [('coarse', 'zero', 110.2), ('fine', 'zero', 110.),
                                ('coarse', 'ppo_seed0', 109.2), ('fine', 'ppo_seed0', 109.)]]
        pair = study.numerical_pairs(rows, ['ppo_seed0'], self.protocol['gates'])[0]
        self.assertTrue(pair['passed'])
        self.assertAlmostEqual(pair['gain_discrepancy_s'], 0.)
        rows[-1]['duration_s'] = 109.1
        self.assertFalse(study.numerical_pairs(rows, ['ppo_seed0'], self.protocol['gates'])[0]['passed'])
        rows[-1]['status'] = 'failed'
        failed = study.numerical_pairs(rows, ['ppo_seed0'], self.protocol['gates'])[0]
        self.assertFalse(failed['passed'])
        self.assertEqual(failed['reason'], 'missing rollout')

    def test_absolute_lap_gate_can_fail_when_relative_gain_is_exact(self):
        rows = [dict(grid=g, policy=p, duration_s=t, status='completed', audit=dict(passed=True))
                for g, p, t in [('coarse', 'zero', 112.), ('fine', 'zero', 110.),
                                ('coarse', 'ppo_seed0', 111.), ('fine', 'ppo_seed0', 109.)]]
        pair = study.numerical_pairs(rows, ['ppo_seed0'], self.protocol['gates'])[0]
        self.assertEqual(pair['gain_discrepancy_s'], 0.)
        self.assertFalse(pair['passed'])


if __name__ == '__main__':
    unittest.main()
