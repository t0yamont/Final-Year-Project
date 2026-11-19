"""Evaluation isolation and descriptive summaries for repeated training seeds."""
from contextlib import contextmanager
import random
import numpy as np
import torch


@contextmanager
def isolated_rng(seed):
    python_state=random.getstate();numpy_state=np.random.get_state()
    devices=list(range(torch.cuda.device_count())) if torch.cuda.is_available() else []
    try:
        with torch.random.fork_rng(devices=devices):
            random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
            if devices:torch.cuda.manual_seed_all(seed)
            yield
    finally:
        random.setstate(python_state);np.random.set_state(numpy_state)


def describe(values):
    values=np.asarray(values,dtype=float)
    if values.ndim!=1 or len(values)<2 or not np.isfinite(values).all():raise ValueError('at least two finite seed values required')
    return dict(n=len(values),mean=float(values.mean()),sample_sd=float(values.std(ddof=1)),
                minimum=float(values.min()),maximum=float(values.max()))


def gain_discrepancy(coarse_time,fine_time,coarse_zero,fine_zero):
    return abs((coarse_zero-coarse_time)-(fine_zero-fine_time))
