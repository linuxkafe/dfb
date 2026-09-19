---
ticket: T003
title: Decision engine with Vulkan compute + graphical maze visualization
sprint: sprint-01
priority: high
status: pending
created: 2026-09-19
---

# T003 — Decision engine stub + Vulkan compute + graphical visualization

## Context

T002 baseline shows Steam Deck GPU (AMD VanGogh/RDNA2) is completely unused:
- CPU avg 3%, GPU 0%
- Vulkan 1.4 available with compute queues (1024 invocations, 64KB shared mem)
- Current `/decide` is pure Python greedy stub

For a real "Fly Brain", we need:
1. **Decision engine** that can run neural nets / planners on GPU
2. **Safety gate** — explicit human confirmation for any aircraft command
3. **Graphical visualization** — see maze solution, fly path, heatmaps

## Acceptance Criteria

- [ ] Vulkan compute pipeline for matrix ops / small NN inference (Python → Vulkan via pyvulkan or ctypes)
- [ ] Decision engine stub using GPU for forward pass (even if weights random)
- [ ] Safety gate: `/decide` returns advisory only; `/command` requires `confirmation_token` from human
- [ ] Graphical maze viz: pygame/SDL2 window showing grid, fly, path, obstacles, exit
- [ ] Viz runs on client machine, connects to Deck service, updates in real-time
- [ ] Resource monitor extended: GPU utilization, VRAM, GPU temp
- [ ] `make test-deck` runs viz headless (offscreen) for CI, interactive for dev

## Scope

**In scope:**
- Minimal Vulkan compute shader (matrix multiply or 1-layer MLP)
- Python wrapper using `pyvulkan` or `vulkan` package
- Decision service `/decide` uses GPU path; `/command` requires confirmation
- Pygame visualization client (separate process, connects to `steamdeck:8082`)
- Extended resource monitor: `radeontop` or `amdgpu` hwmon for GPU metrics

**Out of scope:**
- Full neural network training
- MAVLink integration (separate)
- Production safety certification

## Dependencies

- T001, T002 done
- Steam Deck: `vulkan-tools`, `python3-vulkan` or `pip install vulkan`
- Client: `pygame`, `numpy`

## Rollback

- Revert `/decide` to CPU greedy
- Remove `/command` endpoint
- Disable viz module

## Known Risks

- **Vulkan from Python**: `pyvulkan` is low-level; boilerplate heavy. Alternative: `tinygrad`/`onnxruntime` with Vulkan EP, or custom C extension.
- **GPU context in systemd service**: Service runs as `deck` user, needs access to `/dev/dri/renderD128` (should work by default)
- **Viz on headless CI**: Need virtual display (Xvfb) or offscreen Vulkan/EGL
- **Safety gate UX**: How does human provide confirmation? CLI flag? Web UI? Start simple: token file.

## Notes

- Start with **matrix multiply compute shader** as "hello GPU" — verifies pipeline works
- Then upgrade to **1-layer MLP** (input→hidden→output) for decision
- Visualization: 600x600 window, 10x10 grid = 60px cells, color-coded
- Safety: `/command` returns 403 without `X-Confirmation-Token` header matching file in `/tmp/flybrain_confirm_*`