import unittest
import numpy as np
from f1energy.circuit import PeriodicCentreline, closed_braking_envelope, simulate_circuit, periodic_speed_lap
from f1energy.power_lap import PowerVehicle


def circle(radius=100., n=120):
    angle = np.linspace(0, 2*np.pi, n, endpoint=False)
    return np.column_stack([radius*np.cos(angle), radius*np.sin(angle)])


class CircuitTests(unittest.TestCase):
    def test_circle_curvature_length_and_periodic_derivatives(self):
        curve = PeriodicCentreline(circle(), smoothing_sigma_m=0, resample_spacing_m=2)
        grid = curve.grid(9, 10, 90)
        self.assertLess(abs(grid.distance_m[-1]-200*np.pi), .2)
        # Polygon resampling has small curvature ripple; integral is the stronger check.
        from scipy.integrate import quad
        turn, _ = quad(lambda t: float(curve.curvature(t)*np.linalg.norm(curve.spline(t, 1))),
                       0, curve.source_length_m, points=curve.knots[1:-1], limit=500)
        self.assertAlmostEqual(turn, 2*np.pi, places=6)
        for derivative in (0, 1, 2):
            np.testing.assert_allclose(curve.spline(0, derivative), curve.spline(curve.source_length_m, derivative), atol=1e-12)

    def test_cell_curvature_bound_covers_interior_and_reversal(self):
        xy = circle(); xy[:, 0] *= 2
        curve = PeriodicCentreline(xy, smoothing_sigma_m=8)
        grid = curve.grid(40)
        for i in range(len(grid.lengths_m)):
            sample = np.linspace(grid.parameter_m[i], grid.parameter_m[i+1], 101)
            self.assertLessEqual(np.max(np.abs(curve.curvature(sample))), grid.max_abs_curvature_per_m[i]+1e-10)
        reverse = PeriodicCentreline(np.vstack([xy[0], xy[:0:-1]]), smoothing_sigma_m=8)
        np.testing.assert_allclose(curve.curvature(np.linspace(0, curve.source_length_m, 100)),
                                   -reverse.curvature(np.linspace(reverse.source_length_m, 0, 100)), atol=1e-9)

    def test_cyclic_braking_matches_all_downstream_constraints(self):
        lengths = np.array([20., 15., 30., 10., 25.])
        caps = np.array([70., 80., 75., 15., 90.])
        for drag in [0., 1.]:
            vehicle = PowerVehicle(drag_kg_per_m=drag)
            actual = closed_braking_envelope(lengths, caps, vehicle)
            nodes = np.minimum(caps, np.roll(caps, 1))
            expected = []
            for start in range(len(caps)):
                candidates = [nodes[start]**2]; distance = 0.
                for step in range(1, len(caps)):
                    distance += lengths[(start+step-1) % len(caps)]
                    q = nodes[(start+step) % len(caps)]**2
                    if drag:
                        exponent = 2*drag*distance/vehicle.mass_kg
                        q = q*np.exp(exponent)+vehicle.mass_kg*vehicle.friction_deceleration_m_per_s2/drag*np.expm1(exponent)
                    else:
                        q += 2*vehicle.friction_deceleration_m_per_s2*distance
                    candidates.append(q)
                expected.append(np.sqrt(min(candidates)))
            np.testing.assert_allclose(actual, expected+[expected[0]], atol=1e-10)
            rotated = closed_braking_envelope(np.roll(lengths, 2), np.roll(caps, 2), vehicle)
            np.testing.assert_allclose(rotated[:-1], np.roll(actual[:-1], 2), atol=1e-10)

    def test_periodic_lap_energy_caps_and_depletion(self):
        grid = PeriodicCentreline(circle(), smoothing_sigma_m=10).grid(20, 12, 80)
        vehicle = PowerVehicle(base_power_w=150000, electrical_limit_w=60000)
        result = periodic_speed_lap(grid, vehicle, 20000., 1., reserve_j=1000.)
        self.assertLess(abs(result['speed_closure_error_mps']), 1e-6)
        self.assertAlmostEqual(result['final_state']['energy_j'], 1000., places=5)
        self.assertAlmostEqual(result['totals']['electrical_work_j'], 19000*.9, places=4)
        self.assertLess(abs(result['totals']['energy_residual_j']), .01)
        self.assertLess(result['max_sample_cap_excess_mps'], 1e-6)
        self.assertEqual(sum(e['kind']=='depletion' for e in result['events']), 1)
        envelope = result['braking_envelope_mps']
        self.assertTrue(all(row['speed_m_per_s'] <= cap+1e-5 for row, cap in zip(result['nodes'], envelope)))
        self.assertTrue(all(b['energy_j'] <= a['energy_j']+1e-7 for a,b in zip(result['nodes'], result['nodes'][1:])))

    def test_shooting_power_limited_periodic_speed(self):
        grid = PeriodicCentreline(circle(), smoothing_sigma_m=10).grid(40, 30, 90)
        vehicle = PowerVehicle(base_power_w=1000, electrical_limit_w=0, drag_kg_per_m=1.)
        result = periodic_speed_lap(grid, vehicle, 0.)
        self.assertAlmostEqual(result['initial_speed_mps'], 10., places=5)
        self.assertAlmostEqual(result['duration_s'], grid.distance_m[-1]/10, places=4)

    def test_invalid_geometry_actions_and_entry(self):
        with self.assertRaises(ValueError): PeriodicCentreline(np.zeros((10, 2)))
        with self.assertRaises(ValueError): PeriodicCentreline(circle(), smoothing_sigma_m=-1)
        grid = PeriodicCentreline(circle()).grid()
        with self.assertRaises(ValueError): simulate_circuit(grid, PowerVehicle(), 100., 0.)
        with self.assertRaises(ValueError): simulate_circuit(grid, PowerVehicle(), 10., 0., actions=[0.])
        with self.assertRaises(ValueError): closed_braking_envelope([1., 2., 3.], [20., np.nan, 30.], PowerVehicle())

    def test_periodic_shooting_adapts_below_one_mps(self):
        grid = PeriodicCentreline(circle()).grid(40, 30, 10)
        vehicle = PowerVehicle(base_power_w=.125, electrical_limit_w=0, drag_kg_per_m=1.)
        result = periodic_speed_lap(grid, vehicle, 0.)
        self.assertAlmostEqual(result['initial_speed_mps'], .5, places=5)


if __name__ == '__main__': unittest.main()
