# T006 — Hostile Analysis (Phase 1)

## INSIGHTS CONSULTED
- Existing repo: FastAPI service, CPU engine (numpy MLP), Vulkan engine (WIP), pygame viz.
- No MuJoCo, no ONNX, no ONNX Runtime.
- Steam Deck: RADV Vulkan, Mesa Zink available.
- PyTorch wheels lack Vulkan; must export to ONNX.

## ASSUMPTIONS (with uncertainty)

- [KNOWN] Steam Deck has Vulkan 1.3+ via RADV.
- [KNOWN] Mesa provides Zink OpenGL-on-Vulkan.
- [INFERRED] ONNX Runtime Vulkan EP works on Linux x86_64 with RADV (docs claim support).
- [ASSUMED] MuJoCo Python bindings install via `pip install mujoco` (official wheels exist).
- [ASSUMED] ONNX Runtime can be installed with `onnxruntime-gpu` (includes Vulkan EP) or `onnxruntime` + Vulkan EP.
- [UNKNOWN] Which ONNX ops are unsupported by Vulkan EP (e.g., LayerNorm, GELU, custom autograd).
- [UNKNOWN] Performance gain vs CPU for tiny MLP (may be overhead dominated).

## WHAT WASN'T SPECIFIED

- Exact MuJoCo model (pendulum, quadrotor, etc.).
- Neural net architecture (size, activations).
- Batch size (likely 1 for real-time control).
- Whether inference runs every physics step or at lower rate.

## ALTERNATIVES NOT CHOSEN

| Option | Reason |
|--------|--------|
| PyTorch CUDA | No NVIDIA GPU on Deck. |
| TVM / TensorRT | Not available on AMD Vulkan. |
| Direct Vulkan compute (custom) | High effort; ONNX Runtime EP is standard. |
| Keep all on CPU | Defeats acceleration goal. |

## INVITE CONTRADICTION

- If Vulkan EP fails for key ops, we must fallback hybrid.
- If MuJoCo license blocks CI, we may need a dummy physics stub.

## CLAIM TYPES

- Empirical: Vulkan EP supports Linear, ReLU, Add, MatMul.
- Normative: We should use ONNX Runtime Vulkan EP for inference.

## RISKS & SIDE EFFECTS

1. ONNX export may require opset version compatible with Vulkan EP.
2. Vulkan EP may be slower for batch=1 due to launch overhead.
3. Zink rendering may crash if Mesa version mismatched.
4. MuJoCo simulation step may dominate runtime, hiding inference gains.

## COST OF BEING WRONG: MEDIUM

- If Vulkan EP unsupported, we still have CPU fallback (already implemented).
- Time spent on export/benchmark is recoverable.

## REASONING SKELETON

1. Physics on CPU (MuJoCo) → produces state vector.
2. Policy network (MLP) maps state → action.
3. Export policy to ONNX (opset 17).
4. Load ONNX with `VulkanExecutionProvider`.
5. Benchmark latency vs PyTorch CPU.
6. If unsupported ops → hybrid: run supported subgraph on Vulkan, rest CPU.

## SCOPE BOUNDARIES

In: minimal pendulum MuJoCo model, 2-layer MLP policy, ONNX export, benchmark script, Zink test.
Out: full connectome, training, safety certification.

## HOSTILE ANALYSIS LINT CHECK

References: `src/dfb/cpu_engine.py`, `src/dfb/service.py`, `pyproject.toml`, new files `sim/`, `benchmark_vulkan.py`.