import importlib.util,sys,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
spec=importlib.util.spec_from_file_location('validator',root/'scripts/validate_event_solver.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class EventValidationTests(unittest.TestCase):
 def test_analytic_cases(self): self.assertTrue(m.analytic_checks()['passed'])
 def test_invariant_grid_literal_trend_separate(self):
  row=dict(elapsed_s=20.,terminal_speed_m_per_s=20.,battery_draw_j=400000.,min_energy_j=50000.,max_residual_j=0.,max_envelope_excess_m_per_s=0.,rtol=1e-9)
  result=m.assess([row.copy() for _ in range(5)],[row.copy() for _ in range(3)],{'passed':True})
  self.assertEqual(result['gate'],'passed_synthetic_numerical_gate');self.assertFalse(result['original_strict_time_trend'])
  row['max_envelope_excess_m_per_s']=1.
  self.assertFalse(m.physical(row))
