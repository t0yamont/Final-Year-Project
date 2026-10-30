import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('grid_study',ROOT/'scripts/validate_power_grid.py')
study=importlib.util.module_from_spec(spec);spec.loader.exec_module(study)

class GridTests(unittest.TestCase):
    def test_same_physical_constraints_and_control(self):
        for spacing in study.GRID_SIZES:
            nodes,caps=study.grid(spacing)
            self.assertIn(400,nodes);self.assertEqual(nodes[-1],800)
            self.assertEqual([(x,c) for x,c in zip(nodes,caps) if c!=100],[(400,30),(800,20)])
            self.assertEqual({study.spatial_control(x) for x in nodes},{0.6})
    def test_constraints_and_accounting(self):
        summary,rows=study.run_grid(10)
        self.assertLess(summary['max_abs_energy_residual_j'],1e-6)
        self.assertLess(summary['max_envelope_excess_m_per_s'],1e-8)
        self.assertGreaterEqual(summary['min_energy_j'],study.RESERVE)
        self.assertAlmostEqual(summary['elapsed_s'],sum(r['info']['duration_s'] for r in rows))
        self.assertAlmostEqual(summary['battery_draw_j'],sum(r['info']['battery_draw_j'] for r in rows))
    def test_gate_rejects_nonconvergence(self):
        summaries=[dict(elapsed_s=t,battery_draw_j=100,max_abs_energy_residual_j=0,max_envelope_excess_m_per_s=0,min_energy_j=50000) for t in [10,11,13,17,25]]
        self.assertEqual(study.assess(summaries)['gate'],'rejected')

if __name__=='__main__':unittest.main()
