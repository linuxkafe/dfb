---
ticket: T006
title: MuJoCo physics + neural inference via ONNX Vulkan on Steam Deck
sprint: sprint-01
priority: high
status: pending
created: 2026-09-19
---

# T006 — MuJoCo physics + neural inference via ONNX Vulkan

## Context

We need a simulation loop where:
- Physics (MuJoCo `mj_step`) runs on CPU multithread.
- Neural network (connectome) inference runs on GPU via Vulkan using ONNX Runtime VulkanExecutionProvider.
- Optional rendering uses OpenGL over Vulkan (Zink).

Current repo has only a minimal FastAPI service. No MuJoCo, no neural net.

## Acceptance Criteria

- [ ] Add dependencies: mujoco, onnxruntime (with Vulkan EP), torch, onnx.
- [ ] Create a minimal MuJoCo model (e.g., simple pendulum or quadrotor) and simulation loop.
- [ ] Define a small neural network (e.g., 2-layer MLP) representing connectome policy.
- [ ] Export the policy network to ONNX (`torch.onnx.export`).
- [ ] Write `benchmark_vulkan.py` that loads ONNX with `providers=['VulkanExecutionProvider','CPUExecutionProvider']` and measures inference latency vs PyTorch CPU.
- [ ] Log any unsupported operators for Vulkan EP; propose hybrid fallback (dense layers on Vulkan, rest CPU).
- [ ] Provide a script to launch rendering with `MESA_LOADER_DRIVER_OVERRIDE=zink` and verify window opens.
- [ ] All quality gates pass (`make check`).

## Scope

**In scope:**
- Minimal physics + policy loop.
- ONNX export + Vulkan EP benchmark.
- Zink rendering test.

**Out of scope:**
- Full connectome dataset.
- Production safety gates.
- Distributed training.

## Dependencies

- T003 (CPU engine) done.
- System: Vulkan driver (RADV), Mesa Zink.

## Rollback

Remove added files and revert pyproject.toml.

## Known Risks

- ONNX Runtime Vulkan EP may not support all ops (e.g., custom activations).
- MuJoCo license / binary distribution.
- Zink may be unstable on some Mesa versions.

## Notes

- Keep neural net tiny for CI (e.g., 64->64->4).
- Use deterministic seeds for reproducibility.