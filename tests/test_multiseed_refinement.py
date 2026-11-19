import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from train_circuit_multiseed import refinement_assessment


class RefinementTests(unittest.TestCase):
    def test_matched_gain_and_all_gate_failures(self):
        limits=dict(max_paired_advantage_error_s=.005,max_relative_lap_time_error=.0025,
                    max_terminal_energy_error_j=10000.,max_recovery_error_j=5000.)
        fine=dict(duration_s=100.,final_energy_j=100000.,feasible=True,trace=[{'battery_recovered_j':2000000.}])
        refined=dict(fine,duration_s=99.9)
        result=refinement_assessment(fine,refined,100.1,100.,limits)
        self.assertTrue(result['passed'])
        self.assertAlmostEqual(result['paired_advantage_discrepancy_s'],0.)
        for modified in [dict(refined,duration_s=99.89),dict(refined,final_energy_j=110001.),
                         dict(refined,trace=[{'battery_recovered_j':1994999.}]),dict(refined,feasible=False),
                         dict(refined,duration_s=float('nan'))]:
            self.assertFalse(refinement_assessment(fine,modified,100.1,100.,limits)['passed'])
        # Equal paired advantages alone do not excuse a large lap-time error.
        self.assertFalse(refinement_assessment(fine,dict(refined,duration_s=99.),100.1,99.1,limits)['passed'])


if __name__=='__main__':unittest.main()
