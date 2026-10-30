from pathlib import Path
import math
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from f1energy.braking import braking_envelope

class BrakingTests(unittest.TestCase):
    def test_single_corner_matches_stopping_distance(self):
        speeds = braking_envelope([100], [100, 20], [5])
        distance = (speeds[0]**2 - speeds[1]**2)/(2*5)
        self.assertAlmostEqual(distance, 100)
        self.assertLess(speeds[0], 100)

    def test_downstream_corner_propagates_across_segments(self):
        speeds = braking_envelope([50, 50], [100, 100, 20], [5, 5])
        self.assertAlmostEqual(speeds[0], math.sqrt(1400))
        self.assertAlmostEqual(speeds[1], 30)
        self.assertEqual(speeds[2], 20)

    def test_local_cap_and_terminal_bound_preserved(self):
        caps = [10, 50, 40]
        speeds = braking_envelope([10, 10], caps, [5, 5], 0)
        for actual, expected in zip(speeds, (10, 10, 0)):
            self.assertAlmostEqual(actual, expected, places=12)
        self.assertEqual(caps, [10, 50, 40])
        self.assertEqual(braking_envelope([1], [5, 3], [1], 10)[-1], 3)

    def test_refinement_invariance_constant_deceleration(self):
        coarse = braking_envelope([100], [100, 10], [4])
        fine = braking_envelope([25]*4, [100]*4+[10], [4]*4)
        self.assertAlmostEqual(coarse[0], fine[0])

    def test_all_returned_nodes_satisfy_segment_braking_inequality(self):
        lengths, decels, caps = [5, 30, 12], [2, 7, 3], [30, 25, 10, 4]
        speeds = braking_envelope(lengths, caps, decels)
        for i in range(3):
            self.assertLessEqual(speeds[i]**2, speeds[i+1]**2+2*decels[i]*lengths[i]+1e-10)
            self.assertLessEqual(speeds[i], caps[i])

    def test_invalid_data(self):
        for lengths, caps, decels in [([], [1], []), ([0], [1,2], [1]),
            ([1], [1], [1]), ([1], [1,2], [0]), ([1], [1,float('nan')], [1]),
            ([True], [1,2], [1]), ([1], [-1,2], [1])]:
            with self.assertRaises(ValueError):
                braking_envelope(lengths, caps, decels)

if __name__ == '__main__':
    unittest.main()

