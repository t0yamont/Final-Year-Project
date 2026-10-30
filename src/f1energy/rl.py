"""Synthetic fixed-track Gymnasium environment; no empirical F1 validity claim."""
import gymnasium as gym
import numpy as np
from .lap import default_scenario, initial_state, transition

class LapEnv(gym.Env):
    metadata = {'render_modes': []}
    def __init__(self, scenario=None):
        self.scenario = scenario or default_scenario()
        self.action_space = gym.spaces.Box(0., 1., (1,), dtype=np.float32)
        self.observation_space = gym.spaces.Box(0., np.inf, (3,), dtype=np.float32)
        self.state = initial_state(self.scenario)
    def _observation(self):
        s = self.state
        return np.array([s.index / len(self.scenario.segments), s.speed_m_per_s / 100.,
                         (s.energy_j-self.scenario.reserve_j) / max(1.,self.scenario.initial_energy_j-self.scenario.reserve_j)], dtype=np.float32)
    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.state = initial_state(self.scenario)
        return self._observation(), {}
    def step(self, action):
        if self.state.index >= len(self.scenario.segments):
            raise RuntimeError('reset required after terminal transition')
        a = np.asarray(action)
        if a.shape != (1,) or not np.isfinite(a).all() or not 0 <= float(a[0]) <= 1:
            raise ValueError('action must be one finite fraction in [0,1]')
        self.state, info = transition(self.scenario,self.state,float(a[0]))
        done = self.state.index == len(self.scenario.segments)
        return self._observation(), -info['duration_s'], done, False, info
