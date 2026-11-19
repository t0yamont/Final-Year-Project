"""Record the separate host-RAM and CUDA allocations for a saved PPO setup."""
import argparse,ctypes,json,hashlib
from pathlib import Path
import numpy as np
import torch
from stable_baselines3 import PPO


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    if not torch.cuda.is_available():raise RuntimeError('CUDA required')
    model=PPO.load(args.checkpoint,device='cuda:0')
    # SB3 restores configuration and allocates a new host rollout buffer. This is
    # allocated-buffer sizing, not reconstruction of historical training contents.
    arrays={k:int(v.nbytes) for k,v in vars(model.rollout_buffer).items() if isinstance(v,np.ndarray)}
    class MemoryStatus(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(name,ctypes.c_ulonglong) for name in
          ['total_physical','available_physical','total_pagefile','available_pagefile','total_virtual','available_virtual','available_extended_virtual']]
    status=MemoryStatus();status.length=ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):raise ctypes.WinError()
    report=dict(checkpoint=str(args.checkpoint),checkpoint_sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
        gpu_name=torch.cuda.get_device_name(0),dedicated_cuda_capacity_bytes=torch.cuda.get_device_properties(0).total_memory,
        system_ram_total_bytes=status.total_physical,system_ram_available_bytes=status.available_physical,
        shared_gpu_limit_gib_user_reported=32,shared_limit_independently_measured=False,
        rollout_storage='NumPy arrays in system RAM; minibatches transferred to CUDA',
        reconstructed_rollout_arrays_bytes=arrays,reconstructed_rollout_total_bytes=sum(arrays.values()),
        policy_device=str(next(model.policy.parameters()).device),
        cuda_allocated_bytes_this_audit_process=torch.cuda.memory_allocated(),
        cuda_reserved_bytes_this_audit_process=torch.cuda.memory_reserved(),
        interpretation='Host RAM and dedicated VRAM are separate pools. Windows shared-memory allowance is not extra dedicated CUDA VRAM. This audit does not claim forced spillover or measure peak host usage during training.')
    args.output.write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps(report,indent=2))


if __name__=='__main__':main()
