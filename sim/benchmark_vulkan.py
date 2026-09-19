"""Benchmark Vulkan EP vs PyTorch CPU for policy inference."""
import time
import numpy as np
import torch
import onnxruntime as ort
from pathlib import Path
from sim.policy import PolicyNet, PolicyWrapper


def benchmark_pytorch(model: PolicyNet, runs: int = 1000) -> float:
    model.eval()
    dummy = torch.randn(1, 2, dtype=torch.float32)
    # warmup
    for _ in range(10):
        model(dummy)
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    t0 = time.perf_counter()
    for _ in range(runs):
        model(dummy)
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    elapsed = time.perf_counter() - t0
    return (elapsed / runs) * 1000  # ms per inference


def benchmark_onnx(onnx_path: Path, providers, runs: int = 1000) -> float:
    session = ort.InferenceSession(str(onnx_path), providers=providers)
    input_name = session.get_inputs()[0].name
    dummy = np.random.randn(1, 2).astype(np.float32)
    # warmup
    for _ in range(10):
        session.run(None, {session.get_inputs()[0].name: dummy})
    t0 = time.perf_counter()
    for _ in range(runs):
        session.run(None, {session.get_inputs()[0].name: dummy})
    elapsed = time.perf_counter() - t0
    return (elapsed / runs) * 1000


def main():
    onnx_path = Path("policy.onnx")
    if not onnx_path.exists():
        print("policy.onnx not found; run sim/policy.py export first")
        return

    print("=== Inference Benchmark ===")
    # PyTorch CPU
    model = PolicyNet()
    model.load_state_dict(torch.load("policy.pt") if Path("policy.pt").exists() else model.state_dict())
    pt_ms = benchmark_pytorch(model, runs=500)
    print(f"PyTorch CPU: {pt_ms:.3f} ms per inference")

    # ONNX CPU
    cpu_ms = benchmark_onnx(onnx_path, ["CPUExecutionProvider"], runs=500)
    print(f"ONNX CPU EP: {cpu_ms:.3f} ms per inference")

    # ONNX Vulkan (if available)
    try:
        vulkan_ms = benchmark_onnx(onnx_path, ["VulkanExecutionProvider", "CPUExecutionProvider"], runs=500)
        print(f"ONNX Vulkan EP: {vulkan_ms:.3f} ms per inference")
    except Exception as e:
        print(f"Vulkan EP not available or failed: {e}")
        vulkan_ms = None

    print("\n=== Summary ===")
    print(f"PyTorch CPU : {pt_ms:.3f} ms")
    print(f"ONNX CPU EP : {cpu_ms:.3f} ms")
    if vulkan_ms:
        print(f"ONNX Vulkan EP: {vulkan_ms:.3f} ms")
        speedup = pt_ms / vulkan_ms
        print(f"Speedup vs PyTorch CPU: {speedup:.2f}x")
    else:
        print("Vulkan EP unavailable; fallback to CPU.")


if __name__ == "__main__":
    main()