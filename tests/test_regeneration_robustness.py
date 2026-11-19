"""Check one-factor construction and independent accounting rejection."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from run_regeneration_robustness import scenario_setup
from report_regeneration_robustness import audit, read


class RobustnessTest(unittest.TestCase):
    def test_one_factor_and_accounting(self):
        protocol = read('configs/regeneration_robustness_protocol.json')
        config = read('results/regeneration-validation-001/contract.json')['config']
        nominal_config, nominal_ref, _, _ = scenario_setup(config, protocol['scenarios'][0])
        for scenario in protocol['scenarios'][1:]:
            changed, ref, _, vehicle = scenario_setup(config, scenario)
            key = scenario['parameter']
            if key in ('charge_efficiency', 'braking_fraction'):
                self.assertEqual(changed['regeneration'].pop(key), scenario['value'])
                expected = copy.deepcopy(nominal_config); expected['regeneration'].pop(key)
                self.assertEqual(changed, expected)
                self.assertEqual(ref, nominal_ref)
            else:
                self.assertEqual(changed, nominal_config)
                expected = copy.deepcopy(nominal_ref)
                if key == 'initial_energy_j': expected[key] = scenario['value']
                else:
                    expected['vehicle'][key] = scenario['value']
                    self.assertEqual(vehicle.drag_kg_per_m, scenario['value'])
                self.assertEqual(ref, expected)
        record = read('results/regeneration-validation-001/regeneration_cells-160_full.json.gz')
        audit(record, nominal_config, nominal_ref)
        record['trace'][0]['state']['energy_j'] += 100
        with self.assertRaises(ValueError):
            audit(record, nominal_config, nominal_ref)


if __name__ == '__main__':
    unittest.main()
