import unittest
import numpy as np
from f1energy.inference import forward,reconstruct
class InferenceTests(unittest.TestCase):
    def test_independent_endpoint_identity_and_recovery(self):
        truth=np.array([40000.,60000.,80000.]);v=(30.**3+np.cumsum(3*(200000+truth)*np.array([100,150,100])/800))**(1/3)
        result=reconstruct(v,200000,42,truth)
        self.assertTrue(result['optimizer_success']);self.assertLess(result['action_rmse_w'],1e-4);self.assertTrue(result['energy_feasible'])
    def test_base_deployment_confounding(self):
        a=forward([40000,60000,80000],200000);b=forward([60000,80000,100000],180000)
        np.testing.assert_allclose([r['speed_m_per_s'] for r in a['rows']],[r['speed_m_per_s'] for r in b['rows']],rtol=1e-12)
        self.assertNotEqual(a['terminal_energy_j'],b['terminal_energy_j'])
    def test_infeasible_energy_flag_and_invalid_action(self):
        self.assertFalse(forward([120000]*3,initial_energy_j=50000)['feasible'])
        with self.assertRaises(ValueError):forward([-1,0,0])
