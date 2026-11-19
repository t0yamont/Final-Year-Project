import unittest
from types import SimpleNamespace
from unittest.mock import patch
import torch
from f1energy.training_device import require_cuda,verify_cuda_training


class TrainingDeviceTests(unittest.TestCase):
    def test_missing_cuda_rejects_cpu_fallback(self):
        with patch('torch.cuda.is_available',return_value=False):
            with self.assertRaisesRegex(RuntimeError,'CPU fallback is disabled'):require_cuda()
    def test_cpu_model_cannot_claim_cuda_training(self):
        model=SimpleNamespace(policy=torch.nn.Linear(2,1))
        with self.assertRaisesRegex(RuntimeError,'not all on CUDA'):verify_cuda_training(model)
