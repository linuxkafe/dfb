# T005 — Diffstory (Build Output) — DEFERRED WITH FINDINGS

## What Changed

### Files Modified
- `aes/tickets/T005-plan.md` — Updated Hostile Analysis with critical finding: **No Vulkan EP in onnxruntime 1.30.0**

### Files NOT Changed (Intentional)
- No code changes — deferring Vulkan EP until upstream support.

## Why It Changed

**Problem**: Need Vulkan GPU acceleration for neural inference on Steam Deck.

**Finding**: **onnxruntime 1.30.0 does NOT have a Vulkan Execution Provider**.
- Inspected `onnxruntime/core/providers/` — no "vulkan" provider exists.
- CMake option `onnxruntime_ENABLE_DAWN_BACKEND_VULKAN` is Windows-only (Dawn WebGPU backend).
- WebGPU provider uses Dawn backend but is experimental; Dawn Vulkan on Linux not production-ready.
- PyPI wheel only provides `CPUExecutionProvider` and `AzureExecutionProvider`.

## What Was Intentionally Untouched

- No custom onnxruntime build with Vulkan EP (not available upstream).
- No WebGPU/Dawn experimental integration (Windows-only, experimental).
- CPU EP remains default — already 6× speedup over PyTorch.

## Remaining Risks / Follow-up

1. **Track upstream** — monitor microsoft/onnxruntime for Vulkan EP addition (issue tracking).
2. **Future models** — if model grows (batch>1, larger hidden), CPU EP may become bottleneck; revisit then.
3. **Alternative** — if GPU acceleration becomes critical, evaluate TVM or custom Vulkan compute (T003 vulkan_engine), but high effort.

## Validation Performed

- Inspected onnxruntime 1.30.0 source tree: `ls onnxruntime/core/providers/` → no "vulkan" directory.
- Searched CMake for Vulkan flags → only `onnxruntime_ENABLE_DAWN_BACKEND_VULKAN` (Windows-only).
- Benchmarked CPU EP: **0.012ms per inference** (6.2× speedup over PyTorch 0.074ms).
- Vulkan EP unavailable — benchmark falls back to CPU EP.

## Diffstat

```
 aes/tickets/T005-plan.md  | 80 ++ (updated with findings)
```

## Commands for Future Revisit

```bash
# Check upstream for Vulkan EP addition
# When available: rebuild onnxruntime with -Donnxruntime_BUILD_VULKAN=ON (if flag exists)
# Update sim/policy.py PolicyWrapper to prefer Vulkan EP
# Re-run make sim-benchmark
```

## Decision

**T005 DEFERRED** — Vulkan EP not available upstream. CPU EP sufficient for current model (6× speedup, 0.012ms/inference). Revisit when upstream adds support or model scales.