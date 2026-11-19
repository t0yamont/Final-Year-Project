import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
from f1energy.circuit import CircuitGrid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from bahrain_pace_model import limits


class BahrainEnvelopeTests(unittest.TestCase):
    def test_regime_at_braking_cell_and_speed_dependent_corner(self):
        nodes=np.arange(56,dtype=float)*8
        curvature=np.zeros(55)
        curvature[28]=.06
        grid=CircuitGrid(nodes,nodes,np.zeros((56,2)),np.zeros(55),curvature,np.full(55,95.))
        drs=[False]*55
        drs[27]=True
        model=dict(geometry="fixture",geometry_sha256="",line_offset_fraction=0.,lateral_base_mps2=20.,
                   lateral_aero_per_m=.01,max_speed_mps=95.,initial_speed_mps=40.,vehicle={"mass_kg":800.,
                   "friction_deceleration_m_per_s2":12.,"drag_kg_per_m":1.}, drs_blocks=drs,drs_drag_factor=.7)
        with patch("bahrain_pace_model.geometry",return_value=grid):
            capped,envelope,drag=limits(model,1)
        self.assertAlmostEqual(capped.cell_speed_cap_mps[28],20.)
        self.assertAlmostEqual(envelope[28],20.)
        expected=20.**2*math.exp(2*.7*8/800)+(800*12/.7)*math.expm1(2*.7*8/800)
        self.assertAlmostEqual(envelope[27]**2,expected)
        self.assertEqual(drag[26],1.)
        self.assertEqual(drag[27],.7)
        self.assertEqual(envelope[-1],40.)


if __name__=="__main__":
    unittest.main()
