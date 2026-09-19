# T005 — Solution Proposal (Phase 2)

## Chosen Approach

Build onnxruntime 1.30.0 from source on Steam Deck with Vulkan EP enabled, install wheel, update PolicyWrapper to prefer Vulkan EP, benchmark.

## Steps

1. **On Deck**: install build dependencies via pacman.
2. **Clone** onnxruntime v1.30.0.
3. **Configure** CMake with Vulkan EP, disable CUDA.
4. **Build** and create wheel (`pip wheel`).
4. **Install** wheel in project venv.
3. **Update** `sim/policy.py` PolicyWrapper to try Vulkan EP first.
4. **Run benchmark** to compare Vulkan EP vs CPU EP.
4. **Document** result.

## What Will Change

- `scripts/deploy_deck.sh` (optional: add build step for CI).
- `sim/policy.py` PolicyWrapper provider order.
- New artifact: `onnxruntime-1.30.0+vulkan-linux_x86_64.whl` (stored locally).
- `sim/benchmark_vulkan.py` will now show true Vulkan EP latency.

## What Will NOT Change

- MuJoCo model, simulation loop.
- CPU EP fallback remains.
- Existing tests.

## Verification Criteria

- Build completes without error.
- `onnxruntime.InferenceSession(..., providers=['VulkanExecutionProvider','CPUExecutionProvider'])` succeeds and provider list includes Vulkan.
- Benchmark shows Vulkan EP latency (expect similar or slightly better than CPU EP for batch=1).
- If Vulkan EP slower, keep CPU EP as default.

## Remaining Risks

- Build may fail due to missing deps or Vulkan EP maturity.
- If Vulkan EP unsupported for `Tanh`/`Linear`, fallback to CPU EP automatically.

## Commands (to run on Deck)

```bash
# 1. Install build deps
sudo pacman -Sy --needed cmake ninja python-protobuf flatbuffers python-setuptools python-wheel python-pip git base-devel

# 2. Clone and build
cd /tmp
git clone -b v1.30.0 --depth 1 https://github.com/microsoft/onnxruntime.git
cd onnxruntime
./build.sh --config RelWithDebInfo --build_vulkan --skip_tests --parallel $(nproc) --build_wheel

# 3. Install wheel
pip install /tmp/onnxruntime/build/Linux/RelWithDebInfo/wheel/*.whl

# 4. Verify
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

## Acceptance Criteria

- [ ] Build succeeds and wheel installed.
- [ ] `VulkanExecutionProvider` appears in `ort.get_available_providers()`.
- [ ] `sim/benchmark_vulkan.py` runs with Vulkan EP and prints latency.
- [ ] Latency ≤ CPU EP (or documented why not).
- [ ] `make check` passes.