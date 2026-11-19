"""Check unpruned forward DP against all paths in a small regenerative circuit."""
from itertools import product
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from optimize_regeneration_dp import search, replay
from f1energy.circuit_control import CircuitControlEnv
from f1energy.event_power_lap import Regeneration
from f1energy.power_lap import PowerVehicle


class CircuitDPTest(unittest.TestCase):
    def test_exhaustive_and_width_bound(self):
        grid=SimpleNamespace(lengths_m=np.full(8,100.),cell_speed_cap_mps=np.array([80.,80.,28.,28.,80.,80.,80.,80.]),
                             distance_m=np.arange(9)*100.)
        env=CircuitControlEnv(grid,PowerVehicle(base_power_w=150000.),blocks=4,
                              initial_speed=20.,initial_energy=150000.,reserve=10000.,
                              regeneration=Regeneration(recovery_limit_j=60000.))
        actions=[0.,.5,1.]
        exhaustive=[replay(env,path) for path in product(actions,repeat=4)]
        optimum=min(r['duration_s'] for r in exhaustive if r['feasible'])
        settings=dict(name='test',actions=actions,width=100,speed_bin_mps=1e-10,energy_bin_j=1e-8)
        result=search(env,settings,[1.]*4)
        self.assertAlmostEqual(result['search_time_s'],optimum,places=9)
        narrow=search(env,dict(settings,width=2),[1.]*4)
        self.assertLessEqual(max(r['retained'] for r in narrow['layers']),2)
        self.assertLessEqual(narrow['search_time_s'],narrow['incumbent_time_s'])
        self.assertGreaterEqual(narrow['search_time_s'],optimum-1e-9)
