# GPU-required training

The user's execution preference is GPU training. All three PPO entry points (`train_circuit_ppo.py`, `train_event_ppo.py`, `train_synthetic_ppo.py`) now require `cuda:0`. They fail with an actionable error if CUDA is unavailable; there is no silent CPU fallback. Checkpoint evaluation within these training scripts also uses CUDA.

`src/f1energy/training_device.py` performs a CUDA forward/backward/Adam smoke check before creating experiment output. After learning it verifies that policy parameters, gradients and Adam moment tensors reside on CUDA, and records device identity, runtime version and memory use. NumPy/SciPy vehicle integration remains on CPU; neural-network inference, gradients and optimization run on GPU. Small MLP experiments need not be faster merely because CUDA is enabled.

## Installation

Project interpreter: `.venv/Scripts/python.exe`. Hardware detected: NVIDIA A16-16Q, 16 GB; installed NVIDIA driver 553.24. Install the CUDA 12.6 variant of the same PyTorch 2.14.1 release from the official PyTorch wheel index:

```powershell
.venv/Scripts/python.exe -m pip install --force-reinstall --no-deps torch==2.14.1+cu126 --index-url https://download.pytorch.org/whl/cu126
.venv/Scripts/python.exe -m pip check
$env:PYTHONPATH='src'
.venv/Scripts/python.exe -c "from f1energy.training_device import require_cuda; print(require_cuda())"
```

The `--no-deps` command is for this existing environment, whose same-version dependencies are already installed. Use the saved GPU environment lock for its complete package inventory. No system CUDA toolkit is required for these prebuilt PyTorch operations. The current NVIDIA driver is retained if the live forward/backward/optimizer checks pass.

Official references: [PyTorch CUDA 12.6 wheel installation](https://pytorch.org/get-started/previous-versions/), [NVIDIA CUDA minor-version compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html). The driver reports its supported CUDA version separately from PyTorch's bundled runtime. Runtime checks establish compatibility for the operations this project actually executes.

## Training

```powershell
$env:PYTHONPATH='src'
.venv/Scripts/python.exe scripts/train_circuit_ppo.py --baselines results/circuit-control-baselines-001 --output results/circuit-ppo-gpu-NEW
```

Choose a fresh output directory. The numerical and baseline gates remain mandatory. Historical CPU results are retained as originally generated; new GPU experiments record their own runtime and sources. GPU/CPU arithmetic and random-number generation can differ, so a matching seed is not a guarantee of identical learned policies.

## Dedicated and shared memory

The 18 November actor-width experiment holds PPO's value network at two hidden layers of 32 neurons. The actor receives eight observations and outputs one deployment request. With two hidden layers of width (w), its deterministic action path contains (w^2+11w+1) weights and biases. Width 32 uses 1,377 parameters and width 64 uses 4,801. These counts exclude the value network and the action distribution's training-only log standard deviation. The 16,384 simulator steps per seed correspond to about 298 laps' worth of decisions at 55 decisions per lap on nominal Sakhir.

Increasing depth at the same time would change two experimental variables. Each additional dense layer of width w adds w² + w trainable parameters and another sequential computation per decision. GPU memory sets a practical limit that also depends on activation storage, batch size, optimiser state, precision and concurrency. The experiment therefore measures feasible lap times across seeds, transfer to a changed model, peak PyTorch allocation per worker and time to issue 55 decisions. Its inference timing uses the same 55 inputs for both widths, three warm-up laps and 21 timed repetitions with CUDA synchronisation. [Actor-width protocol](../configs/regeneration_ppo_actor64.json)

On continuous-control locomotion benchmarks, Ota, Jha and Kanezaki found that simply enlarging the networks did not yield the gains they obtained after changing the architecture and training procedure. Those results motivate checking return and computational cost for each architecture on the actual task. The present study measures that trade-off directly for Sakhir. [Ota et al., 2024](https://doi.org/10.1007/s10994-024-06547-6) · [Measured Sakhir results](ppo_actor_width.md)

The machine exposes approximately 64 GiB of system RAM and 16 GiB of dedicated CUDA memory. The user reports a 32 GiB Windows shared-GPU-memory allowance. That allowance comes from system RAM; it is not an additional 32 GiB of dedicated VRAM or a guaranteed 48 GiB CUDA allocation pool. SB3 already holds PPO rollout arrays in system RAM and transfers minibatches to the GPU. Geometry, simulation state and caches also use host memory. Policy parameters, gradients and Adam moments reside on CUDA.

Use host RAM for larger rollout/data caches as experiments scale, while keeping active neural-network work in dedicated VRAM. No artificial allocation or forced spillover is needed for the small current policy. Consider pinned host buffers only when transfer profiling justifies them. Microsoft documents the higher access cost of non-local memory: [Microsoft memory guidance](https://learn.microsoft.com/en-us/windows/win32/dxtecharts/resource-management-best-practices). PyTorch explains pinned host transfers: [PyTorch pinned-memory guidance](https://docs.pytorch.org/tutorials/intermediate/pinmem_nonblock.html).

scripts/audit_training_memory.py records dedicated capacity, system RAM, reconstructed SB3 host-buffer allocation and CUDA policy placement from a checkpoint. It distinguishes the user-reported shared allowance from measured memory and does not claim historical shared-memory usage.

## Verified outcome — 11 November 2026

Installation completed with PyTorch 2.14.1+cu126 and CUDA runtime 12.6 on the existing NVIDIA 553.24 driver. Only the torch package changed; pip dependency checks pass. Full environment inventory: environment-gpu-lock.txt. Before/after installation evidence is retained under logs/agent_tools/2026-11-11.

All 119 tests pass after installation. The circuit CUDA verification run results/circuit-ppo-gpu-001 completed 4096 training steps in 180.81 seconds, with 13 CUDA parameter tensors, 13 CUDA gradient tensors and 26 CUDA Adam moment tensors verified. Checkpoint reload is exact and fine-grid replay passes. PyTorch peak allocated memory was 17,157,120 bytes (about 16.36 MiB); this excludes driver/context and other processes, and is not total dedicated GPU usage.

The GPU pilot's deterministic fine-grid lap is 109.415539 s, saving 0.059667 s against zero request but trailing the full-request baseline by 0.807432 s. It finishes with 1.908298 MJ. Its gain differs by 0.000424 s between training and fine grids. These are preserved short-pilot results, not evidence of convergence or of CPU/GPU superiority. The prior CPU pilot remains an independent historical run. GPU execution is now required for further training despite this small workload's limited utilization; no performance improvement is claimed from this migration.

The memory audit of the final checkpoint confirms a configured host rollout allocation of 13,312 bytes and policy placement on cuda:0. This reconstructs an empty buffer from saved settings; it does not measure historical RAM peak or Windows spillover. Hardware memory is approximately 16 GiB dedicated and 64 GiB system RAM. The user's 32 GiB shared allowance is retained as reported, not independently measured. System RAM is already used by NumPy rollout arrays and simulation data; no artificial memory consumption was added.

Dissertation figures: figures/dissertation/circuit-ppo-gpu-v1 (two inspected PNG/PDF pairs). Final verification: logs/agent_tools/2026-11-11/gpu_final_verification.json; memory audit: gpu_memory_audit.json. No training jobs remain running.
