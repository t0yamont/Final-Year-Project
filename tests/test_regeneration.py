import math
import unittest
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
from f1energy.event_power_lap import Regeneration, integrate_segment
from f1energy.power_lap import PowerState, PowerVehicle
from f1energy.circuit_control import CircuitControlEnv, baseline_policy, rollout
from f1energy.terminal_guard import TerminalGuardEnv


class RegenerationTests(unittest.TestCase):
    def setUp(self):
        self.vehicle = PowerVehicle(base_power_w=0., electrical_limit_w=10000., drag_kg_per_m=0.)
        self.parameters = Regeneration(capacity_j=1e6, max_power_w=1e9)
        self.length = (30.**2-20.**2)/(2*8.)

    def braking(self, parameters=None, energy=100000., action=0., **kwargs):
        return integrate_segment(self.vehicle, PowerState(30., energy), self.length, 20., action,
                                 regeneration=parameters or self.parameters, **kwargs)

    def assert_balances(self, info):
        self.assertLess(abs(info['energy_residual_j']), 1e-5)
        self.assertLess(abs(info['battery_residual_j']), 1e-5)
        self.assertAlmostEqual(info['battery_draw_j'],
                               info['battery_discharged_j']-info['battery_recovered_j'], places=6)
        self.assertAlmostEqual(info['battery_recovered_j'],
                               .8*info['regenerative_braking_work_j'], places=6)

    def test_analytic_braking_replaces_friction_independent_of_action(self):
        plain, legacy = integrate_segment(self.vehicle, PowerState(30., 100000.), self.length, 20., 0.)
        state, info = self.braking()
        self.assertAlmostEqual(state.speed_m_per_s, plain.speed_m_per_s, places=8)
        self.assertAlmostEqual(state.elapsed_s, (30.-20.)/8., places=8)
        self.assertAlmostEqual(state.elapsed_s, plain.elapsed_s, places=8)
        self.assertAlmostEqual(info['regenerative_braking_work_j'], 200000.*.4, places=6)
        self.assertAlmostEqual(info['friction_braking_work_j'], 200000.*.6, places=6)
        self.assertAlmostEqual(state.energy_j, 164000., places=6)
        self.assertAlmostEqual(legacy['friction_braking_work_j'], 200000., places=6)
        self.assertEqual((state, info), self.braking(action=1.))
        self.assert_balances(info)

    def test_generator_power_bound(self):
        state, info = self.braking(replace(self.parameters, max_power_w=10000.))
        self.assertAlmostEqual(info['regenerative_braking_work_j'], 10000.*1.25, places=5)
        self.assertAlmostEqual(state.energy_j, 110000., places=5)
        self.assert_balances(info)

    def test_capacity_recovery_and_simultaneous_saturation(self):
        for capacity, budget in [(110000., 1e6), (1e6, 10000.), (110000., 10000.)]:
            with self.subTest(capacity=capacity, budget=budget):
                p = replace(self.parameters, capacity_j=capacity, recovery_limit_j=budget)
                state, info = self.braking(p, sample_spacing_m=1.)
                self.assertAlmostEqual(state.energy_j, 110000., places=5)
                self.assertAlmostEqual(info['battery_recovered_j'], 10000., places=5)
                self.assertAlmostEqual(info['friction_braking_work_j'], 187500., places=5)
                self.assertEqual(len(info['events']), 1)
                self.assertIn(info['events'][0]['kind'], ('battery_full', 'recovery_limit'))
                self.assertTrue(all(s['energy_j'] <= capacity+1e-5 for s in info['samples']))
                self.assert_balances(info)
        for p, energy in [(replace(self.parameters, capacity_j=100000.), 100000.),
                          (replace(self.parameters, recovery_limit_j=0.), 100000.)]:
            _, info = self.braking(p, energy)
            self.assertEqual(info['battery_recovered_j'], 0.)
            self.assertEqual(info['events'], [])

    def test_deployment_exhaustion_survives_recharge(self):
        p = replace(self.parameters, deployment_limit_j=1000.)
        vehicle = replace(self.vehicle, base_power_w=1000.)
        state, first = integrate_segment(vehicle, PowerState(20., 100000.), 100., 100., 1.,
                                         regeneration=p)
        self.assertAlmostEqual(first['battery_discharged_j'], 1000., places=6)
        self.assertEqual([e['kind'] for e in first['events']], ['deployment_limit'])
        distance = (state.speed_m_per_s**2-20.**2)/16.
        charged, brake = integrate_segment(vehicle, state, distance, 20., 0., regeneration=p,
                                           discharged_j=first['battery_discharged_j'])
        self.assertGreater(charged.energy_j, state.energy_j)
        final, last = integrate_segment(vehicle, charged, 100., 100., 1., regeneration=p,
                                        discharged_j=first['battery_discharged_j'],
                                        recovered_j=brake['battery_recovered_j'])
        self.assertEqual(last['electrical_work_j'], 0.)
        self.assertEqual(final.energy_j, charged.energy_j)
        for info in (first, brake, last):
            self.assert_balances(info)
        # Recovery remains deployable when the cumulative deployment budget permits it.
        _, available = integrate_segment(vehicle, charged, 100., 100., 1., regeneration=self.parameters,
                                         discharged_j=first['battery_discharged_j'],
                                         recovered_j=brake['battery_recovered_j'])
        self.assertGreater(available['battery_discharged_j'], 0.)

    def test_invalid_parameters_and_cumulative_inputs(self):
        for name, value in [('capacity_j', 0.), ('charge_efficiency', 0.), ('charge_efficiency', 1.1),
                            ('braking_fraction', 1.1), ('max_power_w', -1.), ('recovery_limit_j', math.nan),
                            ('deployment_limit_j', math.inf), ('max_power_w', True)]:
            with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                replace(self.parameters, **{name: value})
        for kwargs in [dict(recovered_j=-1.), dict(discharged_j=True), dict(recovered_j=math.nan),
                       dict(discharged_j=self.parameters.deployment_limit_j+1.),
                       dict(recovered_j=self.parameters.recovery_limit_j+1.)]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.braking(**kwargs)
        with self.assertRaises(ValueError):
            self.braking(energy=self.parameters.capacity_j+1.)

    def env(self, guard=False):
        grid = SimpleNamespace(lengths_m=np.full(6, 100.), cell_speed_cap_mps=np.full(6, 100.),
                               distance_m=np.arange(7, dtype=float)*100.)
        kwargs = dict(blocks=3, initial_speed=20., initial_energy=5000., reserve=1000.,
                      regeneration=Regeneration(capacity_j=100000., recovery_limit_j=20000.,
                                                deployment_limit_j=5000.))
        if guard:
            return TerminalGuardEnv(grid, PowerVehicle(base_power_w=150000.),
                                    protected_energy_j=2000., terminal_blocks=1, **kwargs)
        return CircuitControlEnv(grid, PowerVehicle(base_power_w=150000.), **kwargs)

    def test_zero_budgets_are_observed_as_exhausted(self):
        env = self.env()
        env.regeneration = replace(env.regeneration, recovery_limit_j=0., deployment_limit_j=0.)
        np.testing.assert_array_equal(env.reset()[0][6:], [0., 0.])

    def test_environment_counters_observations_and_reset(self):
        env = self.env()
        result = rollout(env, baseline_policy('full', env))
        self.assertAlmostEqual(env.recovered_j, sum(t['battery_recovered_j'] for t in result['trace']), places=6)
        self.assertAlmostEqual(env.discharged_j, sum(t['battery_discharged_j'] for t in result['trace']), places=6)
        self.assertGreater(env.recovered_j, 0.)
        self.assertLessEqual(env.discharged_j, env.regeneration.deployment_limit_j+1e-5)
        obs = env._obs()
        self.assertTrue(env.observation_space.contains(obs))
        self.assertEqual(obs.shape, (8,))
        self.assertAlmostEqual(float(obs[6]), 1-env.recovered_j/20000., places=6)
        self.assertAlmostEqual(float(obs[7]), 1-env.discharged_j/5000., places=6)
        energy = env.state.energy_j
        env.recovered_j = env.discharged_j = 0.
        self.assertEqual(env.state.energy_j, energy)
        self.assertFalse(np.array_equal(obs, env._obs()))
        env.recovered_j = env.discharged_j = 1.
        obs, _ = env.reset()
        self.assertEqual((env.recovered_j, env.discharged_j), (0., 0.))
        np.testing.assert_array_equal(obs[6:], [1., 1.])
        self.assertEqual(env.state.energy_j, env.initial_energy)

    def test_guard_restores_physical_reserve_observation(self):
        env = self.env(True)
        obs, _, _, _, info = env.step([1.])
        self.assertEqual(env.reserve, 1000.)
        self.assertAlmostEqual(float(obs[2]), (env.state.energy_j-1000.)/99000., places=7)
        np.testing.assert_array_equal(obs, env._obs())
        self.assertEqual(info['terminal_guard']['reserve_floor_j'], 3000.)
        plain, disabled = self.env(), self.env(True)
        disabled.guard_enabled = False
        self.assertEqual(rollout(plain, baseline_policy('full', plain)),
                         rollout(disabled, baseline_policy('full', disabled)))


if __name__ == '__main__':
    unittest.main()
