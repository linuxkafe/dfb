# T003 — Hostile Analysis (Phase 1)

## INSIGHTS CONSULTED
- T002 baseline: Steam Deck GPU completely idle (VanGogh/RDNA2, Vulkan 1.4, compute queues available)
- Service: FastAPI on CPU only, `/decide` = greedy Python
- Resource monitor: CPU/mem/temp/power only, no GPU metrics
- Client: maze benchmark runs locally, no visualization

---

## ASSUMPTIONS I'M MAKING (with uncertainty classification)

- [KNOWN] Vulkan compute available on Deck: `maxComputeWorkGroupInvocations=1024`, 64KB shared mem
- [KNOWN] `/dev/dri/renderD128` accessible to `deck` user (render node)
- [INFERRED] `pyvulkan` or `vulkan` pip package works on Deck Python 3.13 — needs verification
- [ASSUMED] Systemd service can access GPU (render node) without special config — standard on modern systemd
- [ASSUMED] Matrix multiply compute shader is sufficient "hello GPU" — proves pipeline, then extend to MLP
- [ASSUMED] Pygame visualization on client machine (this machine) — has display, SDL2 works
- [UNKNOWN] `radeontop` or AMD GPU metrics available on Deck — need to check `/sys/class/drm/card0/device/`
- [UNKNOWN] Vulkan compute performance vs CPU for small matrices (10x10 → 64→10) — may be slower due to overhead
- [UNKNOWN] Safety gate token mechanism — file-based? env var? HTTP header? Start simple.

---

## WHAT WASN'T SPECIFIED (that matters)

- Exact decision engine architecture: MLP size? CNN? Planner? Keep minimal: 1 hidden layer.
- Vulkan Python binding choice: `pyvulkan` (official, verbose), `vulkan` (community), or skip Vulkan → use `tinygrad`/`onnxruntime-vulkan`?
- Visualization protocol: WebSocket? Polling HTTP? Shared memory? Start: polling `/decide` + `/state`
- Confirmation token storage: `/tmp/flybrain_confirm_<uuid>`? Redis? SQLite? Start: file in `/tmp/`
- Headless CI for viz: Xvfb + pygame? Or skip viz in CI, only run locally?

---

## ALTERNATIVES I DIDN'T CHOOSE (and why)

| Option | Description | Rejected Because |
|--------|-------------|------------------|
| CUDA | NVIDIA only | Deck is AMD |
| OpenCL | Cross-vendor compute | Vulkan is native on Linux/AMD, better driver support |
| `tinygrad` | High-level GPU tensor lib | Adds heavy dep; want minimal Vulkan to understand pipeline |
| `onnxruntime` + Vulkan EP | Run ONNX models | Overkill for stub; no model yet |
| Web-based viz (FastAPI + JS) | Browser UI | More complex; pygame simpler for real-time grid viz |
| gRPC for service | Binary protocol | HTTP/JSON fine for dev; gRPC later |

---

## INVITE CONTRADICTION

- **What would disprove this approach?**
  - If `pyvulkan` doesn't install on Deck Python 3.13 (Arch) — fallback to `ctypes` + `libvulkan.so`
  - If Vulkan compute shader overhead > CPU for tiny matrices — GPU only wins at batch>1 or larger dims
  - If systemd service can't access `/dev/dri/renderD128` — need `DeviceAllow=` or `SupplementaryGroups=render`
  - If pygame window on client can't keep 60fps over LAN — latency too high

- **Critical flaw I might be missing:**
  - **Vulkan initialization is heavy** — creating instance, device, queue, command pool, buffers, pipeline takes 100ms+. For a decision engine called every 100ms, must reuse everything. Service must hold Vulkan context alive.
  - **No GPU memory management** — need to allocate/free buffers; leaks will OOM VRAM.
  - **Safety gate is theater** if token file is on same machine — but requirement is "explicit human confirmation", not cryptographic.

---

## DISTINGUISH CLAIM TYPES

- **Empirical (what is):**
  - Vulkan compute caps — verified via `vulkaninfo`
  - GPU hardware present — verified via `lspci`
  - Current CPU-only baseline — measured in T002

- **Normative (what should be):**
  - "Use Vulkan for decision engine" — architectural choice for learning/extensibility
  - "Safety gate via token file" — pragmatic dev choice
  - "Pygame for viz" — simplicity over web stack

---

## RISKS & SIDE EFFECTS

1. **Vulkan boilerplate explosion** — 200+ lines for one matmul. Mitigation: minimal wrapper class, copy from `vulkan-tutorial.com` compute example.
2. **GPU context lifetime** — Service must initialize once at startup, cleanup on shutdown. FastAPI `lifespan` handler.
3. **Thread safety** — Vulkan not thread-safe by default; service is single-threaded (uvicorn 1 worker) — OK.
4. **Monitor GPU metrics** — `radeontop` needs root? Check `/sys/class/drm/card0/device/gpu_busy_percent` etc.
5. **Viz-network sync** — Client polls at 10Hz; service decides at 10Hz; acceptable for dev.

---

## COST OF BEING WRONG: MEDIUM

- If Vulkan path fails: fallback to CPU numpy (already works), delay GPU to later ticket
- If viz fails: headless benchmark still works
- Safety gate: even if token mechanism weak, it's explicit confirmation — better than nothing

---

## REASONING SKELETON FOR KEY CLAIMS

**Claim**: "Minimal Vulkan compute shader + persistent context in FastAPI service is viable"

- Premise 1: Deck has Vulkan 1.4 + compute queues (verified)
- Premise 2: `renderD128` accessible to `deck` user (standard udev rules)
- Premise 3: Python can load `libvulkan.so.1` via `ctypes` or `pyvulkan`
- Premise 4: FastAPI `lifespan` allows startup/shutdown hooks for Vulkan init/cleanup
- Inference: Service can hold `VkDevice`, `VkQueue`, `VkCommandPool`, pipeline, buffers as globals
- Conclusion: Proceed with minimal matmul shader; measure latency vs CPU numpy

**Claim**: "Graphical viz as separate pygame client is correct architecture"

- Premise: Service is headless on Deck; visualization is a *client* concern
- Premise: Pygame runs on dev machine (has display), connects via LAN
- Inference: Separation of concerns — service doesn't know about viz
- Conclusion: Viz module in `tests/viz/` or `tools/viz/`, not in `src/dfb/`

---

## SCOPE BOUNDARIES DECLARATION

**In bounds:**
- Vulkan compute shader (matmul → MLP)
- FastAPI service integration (lifespan, `/decide` uses GPU, `/command` needs token)
- Pygame viz client (grid, fly, path, obstacles, real-time)
- Extended monitor (GPU busy %, VRAM, GPU temp)
- Safety token file mechanism

**Deliberately excludes:**
- Neural network training
- Model serialization/loading (random weights for now)
- MAVLink integration
- Web UI / WebSocket
- Multi-GPU / multi-queue
- Production hardening (mTLS, auth, audit log)

---

## HOSTILE ANALYSIS LINT CHECK

File references:
- `src/dfb/service.py` — add lifespan, `/command`, Vulkan context
- `src/dfb/vulkan_engine.py` — new: Vulkan wrapper (instance, device, pipeline, buffers)
- `shaders/decide.comp` — SPIR-V compute shader (matmul/MLP)
- `tools/viz_maze.py` — pygame visualization client
- `scripts/monitor_deck.py` — extend with GPU metrics
- `scripts/deploy_deck.sh` — install `vulkan-tools`, `python3-vulkan`/`pyvulkan`
- `pyproject.toml` — add `vulkan`, `pygame`, `numpy` to optional deps
- `Makefile` — `test-deck` with viz support