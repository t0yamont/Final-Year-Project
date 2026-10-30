import unittest
import numpy as np
from f1energy.rl import LapEnv
class RLTests(unittest.TestCase):
    def test_reward_terminal_and_reset(self):
        env=LapEnv();env.reset(seed=2);total=0.;done=False
        while not done:
            obs,r,done,truncated,info=env.step(np.array([.5],dtype=np.float32));total+=r
            self.assertFalse(truncated);self.assertTrue(env.observation_space.contains(obs))
        self.assertAlmostEqual(-total,env.state.elapsed_s)
        with self.assertRaises(RuntimeError):env.step([.5])
        env.reset();self.assertEqual(env.state.index,0)
    def test_invalid_action(self):
        for action in ([float('nan')],[-.1],[1.1],[]):
            with self.assertRaises(ValueError):LapEnv().step(action)
