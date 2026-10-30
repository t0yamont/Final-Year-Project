import unittest
import numpy as np
from f1energy.identification import fit_effective,evaluate
class IdentificationTests(unittest.TestCase):
    def test_known_parameter_recovery(self):
        v=np.linspace(40,90,80);a=(650000.-.7*v**3)/(800*v)
        fit=fit_effective(v,a)
        self.assertAlmostEqual(fit['effective_total_power_w'],650000,places=5)
        self.assertAlmostEqual(fit['drag_coefficient_kg_per_m'],.7,places=8)
        self.assertLess(evaluate(fit,v,a)['acceleration_rmse_m_per_s2'],1e-10)
    def test_mass_assumption_scales_both_coefficients(self):
        v=np.linspace(40,90,80);a=(650000.-.7*v**3)/(800*v)
        fit=fit_effective(v,a,840)
        self.assertAlmostEqual(fit['effective_total_power_w'],682500,places=5)
        self.assertAlmostEqual(fit['drag_coefficient_kg_per_m'],.735,places=8)
    def test_constant_speed_unidentifiable(self):
        with self.assertRaisesRegex(ValueError,'variation'):fit_effective([60]*10,[1]*10)
