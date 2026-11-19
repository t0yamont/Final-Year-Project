"""GPU-required training setup and evidence; never silently fall back to CPU."""
import torch


def require_cuda():
    if not torch.cuda.is_available():
        raise RuntimeError('GPU training requires CUDA-enabled PyTorch and a working NVIDIA driver. '
                           'See docs/gpu_training.md; CPU fallback is disabled.')
    device='cuda:0'
    torch.cuda.set_device(0)
    # Availability alone is insufficient: exercise forward, backward and optimizer
    # kernels on this architecture/driver before starting an experiment.
    with torch.random.fork_rng(devices=[0]):
        layer=torch.nn.Linear(8,4).to(device)
        optimizer=torch.optim.Adam(layer.parameters(),lr=.01)
        before=layer.weight.detach().clone()
        loss=layer(torch.ones((16,8),device=device)).square().mean()
        loss.backward();optimizer.step();torch.cuda.synchronize()
        if not torch.isfinite(loss) or torch.equal(before,layer.weight):
            raise RuntimeError('CUDA optimizer smoke check failed')
    props=torch.cuda.get_device_properties(0)
    return dict(device=device,gpu_name=props.name,total_memory_bytes=props.total_memory,
                compute_capability=list(torch.cuda.get_device_capability(0)),
                torch_version=torch.__version__,cuda_runtime=torch.version.cuda,
                cudnn_version=torch.backends.cudnn.version(),cuda_optimizer_smoke_passed=True,
                cpu_fallback_allowed=False)


def verify_cuda_training(model):
    parameters=list(model.policy.parameters())
    if not parameters or any(p.device.type!='cuda' for p in parameters):
        raise RuntimeError('Policy parameters are not all on CUDA')
    gradients=[p.grad for p in parameters if p.grad is not None]
    if not gradients or any(g.device.type!='cuda' or not torch.isfinite(g).all() for g in gradients):
        raise RuntimeError('Missing or invalid CUDA training gradients')
    moments=[v for state in model.policy.optimizer.state.values() for key,v in state.items()
             if key in ('exp_avg','exp_avg_sq')]
    if not moments or any(v.device.type!='cuda' for v in moments):
        raise RuntimeError('Adam optimizer moments are not on CUDA')
    torch.cuda.synchronize()
    return dict(policy_device=str(parameters[0].device),parameter_tensors=len(parameters),
                gradient_tensors=len(gradients),cuda_optimizer_moment_tensors=len(moments),
                allocated_bytes=torch.cuda.memory_allocated(),peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                passed=True)
