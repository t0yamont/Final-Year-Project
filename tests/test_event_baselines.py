import unittest
from dataclasses import replace

from f1energy.event_baselines import TransitionCache, InfeasiblePolicyError, dynamic_programming, exhaustive, replay
from f1energy.event_rl import EventScenario


class EventBaselineTests(unittest.TestCase):
    def test_dp_replay_matches_finite_reference_after_refinement(self):
        scenario = replace(EventScenario(), lengths_m=(50., 80.), exit_caps_m_per_s=(30., 20.), initial_energy_j=90000.)
        cache = TransitionCache(scenario)
        reference = exhaustive(scenario, cache=cache)
        for step in (20000., 5000., 1000.):
            result = dynamic_programming(scenario, step, cache=cache)
            self.assertTrue(result['feasible'])
            self.assertGreaterEqual(result['elapsed_s']+1e-5, reference['elapsed_s'])
        self.assertLessEqual(result['elapsed_s']-reference['elapsed_s'], 1e-4)

    def test_exhaustive_prefix_cache_and_identical_replay(self):
        scenario = replace(EventScenario(), lengths_m=(30., 30.), exit_caps_m_per_s=(30., 20.))
        bank = TransitionCache(scenario)
        result = exhaustive(scenario, cache=bank)
        before = bank.calls
        self.assertEqual(result['elapsed_s'], replay(scenario, result['actions'], cache=bank)['elapsed_s'])
        self.assertEqual(before, bank.calls)
        self.assertLessEqual(bank.calls, 3+9)
        self.assertGreater(bank.hits, 0)

    def test_no_usable_energy_and_unreached_exit_cap(self):
        scenario = replace(EventScenario(), lengths_m=(1.,), exit_caps_m_per_s=(100.,), initial_energy_j=50000.)
        result = dynamic_programming(scenario, 1000.)
        self.assertEqual(result['terminal_energy_j'], scenario.reserve_j)
        self.assertLess(result['terminal_speed_m_per_s'], 100.)
        self.assertAlmostEqual(result['elapsed_s'], exhaustive(scenario)['elapsed_s'])

    def test_infeasible_state_does_not_return_empty_optimum(self):
        scenario = replace(EventScenario(), lengths_m=(1.,), exit_caps_m_per_s=(1.,))
        for solve in (lambda: exhaustive(scenario), lambda: dynamic_programming(scenario, 1000.)):
            with self.assertRaises(InfeasiblePolicyError):
                solve()

    def test_budget_and_cache_scope(self):
        scenario = EventScenario()
        with self.assertRaisesRegex(RuntimeError, 'count'):
            replay(scenario, (0., 0.), cache=TransitionCache(scenario, max_transitions=0))
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            replay(replace(scenario, initial_energy_j=500000.), (0., 0.), cache=TransitionCache(scenario))
        with self.assertRaisesRegex(ValueError, 'budget'):
            exhaustive(scenario, max_sequences=2)

    def test_invalid_inputs(self):
        for step in (0, -1, float('nan'), True):
            with self.assertRaises(ValueError):
                dynamic_programming(EventScenario(), step)
        with self.assertRaises(ValueError):
            TransitionCache(replace(EventScenario(), exit_caps_m_per_s=(20.,)))
        with self.assertRaises(ValueError):
            exhaustive(EventScenario(), (float('nan'),))

    def test_cache_scope_cannot_change_after_computation(self):
        scenario = replace(EventScenario(), lengths_m=(5.,), exit_caps_m_per_s=(30.,))
        bank = TransitionCache(scenario, solver={'rtol': 1e-9})
        replay(scenario, (0.,), cache=bank)
        with self.assertRaises(TypeError):
            bank.solver['rtol'] = 1e-3
        with self.assertRaises(AttributeError):
            bank.scenario = replace(scenario, initial_energy_j=500000.)
        with self.assertRaises(AttributeError):
            bank.solver = {}

    def test_dp_rejects_unacceptable_physical_replay(self):
        from unittest.mock import patch
        scenario = replace(EventScenario(), lengths_m=(5.,), exit_caps_m_per_s=(30.,))
        bank = TransitionCache(scenario)
        step = bank.step
        def excessive_residual(*args):
            return dict(step(*args), energy_residual_j=1.)
        with patch.object(bank, 'step', side_effect=excessive_residual):
            with self.assertRaisesRegex(ValueError, 'replay failed'):
                dynamic_programming(scenario, 1000., cache=bank)

    def test_persisted_cache_roundtrip_and_scope_rejection(self):
        import json
        scenario = replace(EventScenario(), lengths_m=(5.,), exit_caps_m_per_s=(30.,))
        first = TransitionCache(scenario)
        result = replay(scenario, (1.,), cache=first)
        payload = json.loads(json.dumps(first.export()))
        second = TransitionCache(scenario)
        second.load_verified_records(payload)
        self.assertEqual(result, replay(scenario, (1.,), cache=second))
        self.assertEqual(second.calls, 0)
        self.assertEqual(second.loaded_records, 1)
        with self.assertRaisesRegex(ValueError, 'scope'):
            TransitionCache(replace(scenario, initial_energy_j=500000.)).load_verified_records(payload)
        with self.assertRaisesRegex(ValueError, 'scope'):
            TransitionCache(scenario, solver={'rtol': 1e-6}).load_verified_records(payload)
