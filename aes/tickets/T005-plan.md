---
ticket: T005
title: Vulkan GPU acceleration for decision engine (build onnxruntime with Vulkan EP)
sprint: sprint-01
priority: medium
status: in-progress
created: 2026-09-19
---

# T005 — Hostile Analysis (Phase 1)

## INSIGHTS CONSULTED
- T006 benchmark shows PyPI onnxruntime lacks VulkanExecutionProvider (only CPU, Azure).
- ONNX CPU EP already 6× faster than raw PyTorch.
- Steam Deck: AMD RDNA2 (VanGogh), RADV driver, Vulkan 1.3+, Mesa 23+.
- Building onnxruntime from source requires CMake, Python, ninja, protobuf, flatbuffers, CUDA toolkit optional.
- Vulkan EP build flag: `-Donnxruntime_BUILD_VULKAN=ON` (and possibly `-Donnxruntime_USE_VULKAN=ON`).
- Build time ~30-60 min on Deck (4-core Zen2). Need ~4 GB RAM.
- Resulting wheel can be installed locally and used by PolicyWrapper.

## ASSUMPTIONS (with uncertainty)

- [KNOWN] Deck has Vulkan 1.3, RADV, Mesa 23+.
- [KNOWN] onnxruntime source builds on Linux x86_64.
- [INFERRED] `-Donnxruntime_BUILD_VULKAN=ON` enables Vulkan EP (docs).
- [ASSUMED] Build dependencies (cmake>=3.20, ninja, python3-dev, protobuf-compiler, flatbuffers) are installable via pacman on SteamOS (Arch-based).
- [ASSUMED] Build will succeed without CUDA (we can disable CUDA).
- [UNKNOWN] Whether Vulkan EP supports all ops used by PolicyNet (Linear, ReLU, Tanh). Likely yes (basic ops).
- [UNKNOWN] Performance gain vs CPU EP for batch=1 tiny model (may be overhead dominated).

## WHAT WASN'T SPECIFIED

- Exact onnxruntime version to build (use same as PyPI: 1.30.0).
- Whether to build with optimizations (`-Donnxruntime_ENABLE_PYTHON_OPSET=ON`).
- Whether to package wheel for reuse.

## ALTERNATIVES NOT CHOSEN

| Option | Reason |
|--------|--------|
| Use TVM / TensorRT | Not available on AMD Vulkan. |
| Keep CPU EP only | Already 6× speedup; but GPU could lower latency further for larger models. |
| Use custom Vulkan compute (T003 vulkan_engine) | High effort; ONNX Runtime EP is standard and supports ONNX graphs. |

## INVITE CONTRADICTION

- If build fails due to missing deps or Vulkan EP not mature, fallback to CPU EP (already viable).
- If Vulkan EP slower for batch=1 due to launch overhead, document and keep CPU EP.

## CLAIM TYPES

- Empirical: Vulkan EP exists in onnxruntime source, can be built on Linux.
- Normative: We should provide GPU-accelerated inference for future larger connectome models.

## RISKS & SIDE EFFECTS

1. Build may OOM or take long on Deck.
2. Vulkan EP may not support `Tanh` or `Linear` in current version (need to verify).
3. Built wheel may not be portable (linked to system Vulkan loader).

## COST OF BEING WRONG: LOW-MEDIUM

- If Vulkan EP unavailable, CPU EP already meets latency budget.
- Time spent building is recoverable.

## REASONING SKELETON

1. Install build deps on Deck (pacman).
2. Clone onnxruntime 1.30.0 tag.
3. Configure CMake with `-Donnxruntime_BUILD_VULKAN=ON -Donnxruntime_ENABLE_CUDA=OFF`.
4. Build and install wheel.
5. Update PolicyWrapper to prefer Vulkan EP.
6. Benchmark again.

## SCOPE BOUNDARIES

In: build onnxruntime with Vulkan EP, integrate, benchmark.
Out: full connectome, MAVLink, safety certification.

## HOSTILE ANALYSIS LINT CHECK

References: `sim/policy.py`, `sim/benchmark_vulkan.py`, `scripts/deploy_deck.sh` (may need to add build step), `pyproject.toml` (maybe add build dep).