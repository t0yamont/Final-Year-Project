import random,unittest
import numpy as np
import torch
from f1energy.experiment import isolated_rng,describe,gain_discrepancy


class ExperimentTests(unittest.TestCase):
    def test_rng_restored_even_after_exception(self):
        random.seed(73);np.random.seed(73);torch.manual_seed(73)
        expected=(random.random(),np.random.random(),float(torch.rand(())))
        random.seed(73);np.random.seed(73);torch.manual_seed(73)
        with self.assertRaises(RuntimeError):
            with isolated_rng(100):
                random.random();np.random.random();torch.rand(5);raise RuntimeError('evaluation failure')
        actual=(random.random(),np.random.random(),float(torch.rand(())))
        self.assertEqual(actual,expected)
    def test_paired_draws_identical(self):
        with isolated_rng(101):a=(np.random.normal(size=5),torch.randn(5))
        with isolated_rng(101):b=(np.random.normal(size=5),torch.randn(5))
        np.testing.assert_array_equal(a[0],b[0]);self.assertTrue(torch.equal(a[1],b[1]))
    @unittest.skipUnless(torch.cuda.is_available(),'CUDA required')
    def test_cuda_rng_restored_and_paired(self):
        torch.cuda.manual_seed_all(73);expected=torch.randn(5,device='cuda')
        torch.cuda.manual_seed_all(73)
        with isolated_rng(101):a=torch.randn(5,device='cuda')
        actual=torch.randn(5,device='cuda')
        with isolated_rng(101):b=torch.randn(5,device='cuda')
        self.assertTrue(torch.equal(a,b));self.assertTrue(torch.equal(actual,expected))
    def test_seed_summary_and_matched_baseline(self):
        self.assertEqual(describe([1,2,3]),dict(n=3,mean=2.,sample_sd=1.,minimum=1.,maximum=3.))
        self.assertAlmostEqual(gain_discrepancy(111,109,112,110),0.)
        with self.assertRaises(ValueError):describe([1])
