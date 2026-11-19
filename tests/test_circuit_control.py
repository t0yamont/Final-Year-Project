import unittest
import numpy as np
from f1energy.circuit import PeriodicCentreline
from f1energy.circuit_control import control_grid,CircuitControlEnv,rollout,baseline_policy
from f1energy.power_lap import PowerVehicle


class ControlTests(unittest.TestCase):
    def setUp(self):
        t=np.linspace(0,2*np.pi,80,endpoint=False)
        self.curve=PeriodicCentreline(np.column_stack([100*np.cos(t),100*np.sin(t)]))
        self.vehicle=PowerVehicle(base_power_w=150000)
    def test_action_boundaries_identical_across_grids(self):
        coarse=control_grid(self.curve,8,3);fine=control_grid(self.curve,8,12)
        np.testing.assert_allclose(coarse.parameter_m[::3],fine.parameter_m[::12],atol=1e-12)
        np.testing.assert_allclose(coarse.distance_m[::3],fine.distance_m[::12],atol=1e-7)
    def test_rollout_energy_and_reward_identity(self):
        env=CircuitControlEnv(control_grid(self.curve,8,8),self.vehicle,8,20.,20000.,1000.)
        zero=rollout(env,baseline_policy('zero',env))
        env.reference_times=np.array([r['duration_s'] for r in zero['trace']])
        result=rollout(env,baseline_policy('full',env))
        self.assertTrue(result['feasible'])
        self.assertAlmostEqual(result['reward_sum'],zero['duration_s']-result['duration_s'],places=9)
        draw=env.initial_energy-result['final_energy_j']
        self.assertAlmostEqual(sum(r['electrical_work_j'] for r in result['trace']),.9*draw,places=5)
        work=sum(r['base_work_j']+r['electrical_work_j']-r['drag_work_j']-r['friction_braking_work_j'] for r in result['trace'])
        self.assertAlmostEqual(work,.5*self.vehicle.mass_kg*(env.state.speed_m_per_s**2-400),places=4)
        self.assertEqual(sum(e['kind']=='depletion' for r in result['trace'] for e in r['events']),1)
    def test_replay_determinism_and_invalid_actions(self):
        env=CircuitControlEnv(control_grid(self.curve,8,3),self.vehicle,8,20.)
        one=rollout(env,baseline_policy('spread',env));two=rollout(env,baseline_policy('spread',env))
        self.assertEqual(one,two)
        with self.assertRaises(RuntimeError):env.step([0.])
        env.reset()
        for action in [[-1.],[1.01],[np.nan],[0.,1.]]:
            with self.assertRaises(ValueError):env.step(action)
    def test_gym_interface(self):
        from stable_baselines3.common.env_checker import check_env
        env=CircuitControlEnv(control_grid(self.curve,8,3),self.vehicle,8,20.)
        check_env(env,warn=True)


if __name__=='__main__':unittest.main()
