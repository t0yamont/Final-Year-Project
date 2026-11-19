import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from f1energy.circuit_control import CircuitControlEnv, baseline_policy, rollout
from f1energy.power_lap import PowerVehicle
from f1energy.terminal_guard import TerminalGuardEnv


class TerminalGuardTests(unittest.TestCase):
    def env(self, guarded=True, **options):
        grid = SimpleNamespace(lengths_m=np.full(6, 100.), cell_speed_cap_mps=np.full(6, 100.),
                               distance_m=np.arange(7, dtype=float)*100.)
        kwargs = dict(blocks=3, initial_speed=20., initial_energy=5000., reserve=1000.)
        kwargs.update(options)
        vehicle = PowerVehicle(base_power_w=150000.)
        return (TerminalGuardEnv(grid, vehicle, protected_energy_j=2000., terminal_blocks=1,
                                 **kwargs) if guarded else CircuitControlEnv(grid, vehicle, **kwargs))

    def test_disabled_replay_exact_including_spread_observations(self):
        for policy in ('full', 'spread'):
            plain = self.env(False)
            guard = self.env()
            guard.guard_enabled = False
            self.assertEqual(rollout(plain, baseline_policy(policy, plain)),
                             rollout(guard, baseline_policy(policy, guard)))

    def test_protected_depletion_and_release_preserve_energy_identity(self):
        env = self.env()
        result = rollout(env, baseline_policy('full', env))
        trace = result['trace']
        self.assertGreaterEqual(trace[0]['state']['energy_j'], 3000.-1e-5)
        self.assertTrue(trace[0]['terminal_guard']['protected_depletion_intervention'])
        self.assertGreater(trace[0]['terminal_guard']['depletion_events'], 0)
        self.assertEqual([t['terminal_guard']['reserve_floor_j'] for t in trace], [3000., 3000., 1000.])
        self.assertEqual(env.reserve, 1000.)
        self.assertAlmostEqual(sum(t['electrical_work_j'] for t in trace),
                               .9*(5000.-result['final_energy_j']), places=6)
        self.assertLess(abs(result['energy_residual_j']), 1e-5)

    def test_original_observation_and_spread_reserve_semantics(self):
        env = self.env()
        observation, _, _, _, _ = env.step([1.])
        self.assertEqual(env.reserve, 1000.)
        self.assertAlmostEqual(float(observation[2]), (env.state.energy_j-1000.)/4000., places=7)
        np.testing.assert_array_equal(observation, env._obs())
        expected = min(1., (env.state.energy_j-1000.)*.9 /
                       ((env.grid.distance_m[-1]-env.state.distance_m)/env.state.speed_m_per_s*60000.))
        self.assertAlmostEqual(baseline_policy('spread', env)(observation)[0], expected)

    def test_forced_tail_rejects_malformed_request_and_logs_override(self):
        env = self.env()
        env.step([0.]); env.step([0.])
        for action in ([-1.], [1.01], [np.nan], [], [0., 1.]):
            with self.assertRaises(ValueError):
                env.step(action)
        _, _, done, _, info = env.step([0.])
        self.assertTrue(done)
        self.assertEqual(info['action'], 1.)
        self.assertEqual(info['terminal_guard']['proposed_action'], 0.)
        self.assertTrue(info['terminal_guard']['action_changed'])

    def test_invalid_budget_and_span(self):
        for kwargs in (dict(initial_energy=2999.), dict(initial_energy=1000.)):
            with self.assertRaises(ValueError):
                self.env(**kwargs)
        env = self.env()
        for budget in (-1., float('nan'), True):
            with self.assertRaises(ValueError):
                TerminalGuardEnv(env.grid, env.vehicle, blocks=3, protected_energy_j=budget)
        with self.assertRaises(ValueError):
            TerminalGuardEnv(env.grid, env.vehicle, blocks=3, terminal_blocks=4)

    def test_restore_original_reserve_when_physics_raises(self):
        env = self.env()
        with patch.object(CircuitControlEnv, 'step', side_effect=RuntimeError('solver failed')):
            with self.assertRaises(RuntimeError):
                env.step([1.])
        self.assertEqual(env.reserve, 1000.)


if __name__ == '__main__':
    unittest.main()
