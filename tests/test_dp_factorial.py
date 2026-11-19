from itertools import product
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from report_regeneration_dp_factorial import contrasts


class FactorialTests(unittest.TestCase):
    def test_three_way_synergy_split_between_its_factors(self):
        times={f'{a}{w}{b}':100-a-2*w+3*b-6*a*w*b for a,w,b in product(range(2),repeat=3)}
        result=contrasts(times,['a','w','b'])
        self.assertEqual(result['allocation_s'],{'a':3.,'w':4.,'b':-1.})
        self.assertEqual(result['marginal_s'],{'a':2.5,'w':3.5,'b':-1.5})
        self.assertEqual(len(result['edges']),12)
        self.assertEqual(len(result['orders']),6)
