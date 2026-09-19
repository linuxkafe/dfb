# T005 — Hostile Analysis (Phase 1) — UPDATED WITH FINDINGS

## INSIGHTS CONSULTED
- T006 benchmark shows PyPI onnxruntime lacks VulkanExecutionProvider (only CPU, Azure).
- ONNX CPU EP already 6× faster than raw PyTorch.
- Steam Deck: AMD RDNA2 (VanGogh), RADV driver, Vulkan 1.3+, Mesa 23+.
- **CRITICAL FINDING**: onnxruntime v1.30.0 source tree does NOT contain a "vulkan" execution provider in `onnxruntime/core/providers/`. Available providers: cpu, cuda, tensorrt, openvino, dml, acl, nnapi, snpe, qnn, rknpu, migraphx, webgpu, webnn, etc. No "vulkan" provider.
- The CMake option `onnxruntime_ENABLE_DAWN_BACKEND_VULKAN` exists but is documented as "Windows only" (enables Vulkan backend for Dawn/WebGPU).
- WebGPU provider uses Dawn which can use Vulkan on Linux, but is experimental and requires Dawn backend.

## ASSUMPTIONS (with uncertainty)

- [KNOWN] Deck has Vulkan 1.3, RADV, Mesa 23+.
- [KNOWN] onnxruntime source builds on Linux x86_64.
- [KNOWN] **No Vulkan EP in onnxruntime 1.30.0** — the flag `-Donnxruntime_BUILD_VULKAN=ON` does NOT exist.
- [INFERRED] Vulkan EP may be added in future versions (track upstream).
- [ASSUMED] CPU EP already 6× speedup over PyTorch; Vulkan would be marginal for batch=1 tiny model.
- [ASSUMED] WebGPU provider with Dawn+Vulkan is experimental and not production-ready.

## WHAT WASN'T SPECIFIED

- When Vulkan EP will be added upstream (track microsoft/onnxruntime#XXXX).
- Whether to use WebGPU+Dawn as alternative (experimental).

## ALTERNATIVES NOT CHOSEN

| Option | Reason |
|--------|--------|
| Build custom onnxruntime with custom Vulkan EP | High effort, not upstream; maintenance burden. |
| Use TVM / TensorRT | Not available on AMD Vulkan. |
| Keep CPU EP only | Already 6× speedup; meets latency budget for tiny model. |
| Use WebGPU+Dawn backend | Experimental; Dawn backend Vulkan on Linux not production-ready. |

## INVITE CONTRADICTION

- If future onnxruntime adds Vulkan EP, revisit this ticket.
- If model grows larger (batch>1, larger hidden), CPU EP may become bottleneck.

## CLAIM TYPES

- Empirical: No Vulkan EP in onnxruntime 1.30.0 source tree (verified).
- Normative: CPU EP is sufficient for current model size; defer Vulkan until upstream support.

## RISKS & SIDE EFFECTS

1. None — deferring Vulkan has no negative impact on current performance.
2. Future larger models may need GPU acceleration; track upstream.

## COST OF BEING WRONG: LOW

- CPU EP already 6× speedup (0.012ms vs 0.074ms PyTorch).
- Deferring Vulkan has zero negative impact on current deliverables.

## REASONING SKELETON (UPDATED)

1. Investigated onnxruntime 1.30.0 source — no Vulkan EP exists.
2. CPU EP already provides 6× speedup (0.012ms per inference).
3. Vulkan EP would be marginal gain for batch=1, 100→64→4 model.
3. Defer Vulkan until upstream adds support; track upstream issues.

## SCOPE BOUNDARIES

**In**: Document finding, update PolicyWrapper to prefer CPU EP, track upstream.
**Out**: Custom Vulkan EP build, WebGPU/Dawn experimental integration.

## HOSTILE ANALYSIS LINT CHECK

References: `sim/policy.py`, `sim/benchmark_vulkan.py`, onnxruntime source inspection.