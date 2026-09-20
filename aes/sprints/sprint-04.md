# Sprint 04 — Safety Gate Closure & Evidence

**Goal**: Close the gRPC safety-gate bypass, add real test evidence (gRPC, HTTP
routes, CLI), clean repo hygiene, verify Vulkan on Steam Deck, and validate a
fly-brain + Ollama neural co-processor PoC.

Per sprint-03 retrospective: *no ticket done without committed code + tests +
passing gates.*

## Tickets

| ID | Title | Status |
|----|-------|--------|
| T013 | Close gRPC safety gate hole + add test evidence (gRPC/HTTP routes/CLI) | in_progress |
| T014 | Vulkan on Steam Deck — functional verification + crash fix (T005 un-defer) | done |
| T015 | Neural co-processor PoC: Ollama + CPU/Vulkan neural net on-deck | done |

## T014 — Retrospective

**Root cause of the deck crash**: `VK_DESCRIPTOR_TYPE_STORAGE_BUFFER = 7`, not 5.
The engine (and the C probe) used `5` (= `STORAGE_TEXEL_BUFFER`), so RADV read
`pTexelBufferView` = NULL → SIGSEGV. Confirmed with a C ABI reproducer:
crashes with 5, runs clean with 7. The earlier "RADV dev-build bug" hypothesis
was wrong and is superseded.

Additional fixes found while verifying (RC-1..RC-6):
- RC-1 `VkPhysicalDeviceMemoryProperties` was under-sized (264 B instead of 520 B).
- RC-2 ctypes `value` handles.
- RC-4 every `VK_STRUCTURE_TYPE_*` constant was wrong; synced to canonical
  `vulkan_core.h` values (e.g. `SUBIT_INFO=4`, `WRITE_DESCRIPTOR_SET=35`,
  `MEMORY_BARRIER=46`, `COMMAND_BUFFER_BEGIN=42`).
- RC-6 `vkCmdBindDescriptorSets` had one extra `c_uint32` argtype →
  `TypeError: takes at least 9 arguments (8 given)`.
- RC-5 (core numeric bug): a single command buffer holding both compute passes
  returned results lagging one input behind (`out = f(input[i-1])`) because this
  RADV build does not honour an intra-CB pipeline barrier between two compute
  passes on the same buffer **even with `vkQueueWaitIdle`**. Fix: one submission +
  fence wait per pass → bit-exact results.

**Proof**: `aes/tickets/T014-verify.md`. `make test`: 92 passed, 1 skipped,
lint clean. Kanban T014 -> done.

**Residual risk**: the Deck RADV dev build's intra-command-buffer barrier
behaviour remains a documented quirk; the engine now relies on submission-boundary
fencing, which is also the more defensive pattern generally.

## T015 — Retrospective

Shipped the 4 modules + test under `sim/`. Neuronal step measured at **0.229 ms
per turn** (budget 50 ms). A 3.2 s/warm "fala-me de drones" turn produced:

```
[Bússola: 99° | Alerta (Oct): 0.49 | Afinidade: +0.16 | Temp: 0.51]
```

and an abrupt topic switch showed the connectome recognisably reshaping the reply:

```
[Bússola: 323° | Alerta (Oct): 0.73 | Afinidade: -0.00 | Temp: 0.70]
```

E-PG bump rotated 99°→323°, octopamine rose 0.49→0.73, temperature 0.51→0.70.

**Findings**:
- 13 test cases validate all three required phenomena + AC-3 timing + AC-4
  telemetry format + AC-1 import cleanliness.
- Deck APU sustains only ~4 tok/s for `llama3.1:8b`; full reply 45–170 s when the
  model is cold-loaded. `keep_alive=30m` warm-up avoids mid-demo stalls.
- Coverage remains a pre-existing 43% (non-gating `|| echo` in `Makefile`).

**Follow-ups**: simulation can move to the Vulkan compute kernel
(`src/dfb/vulkan_engine.py`) as T005 was un-deferred; the scratch bridge
`sim/fly_ollama_bridge.py` is superseded by the PoC modules.

## Reopened items

- None for T014/T015. T013 remains the only open ticket (safety-gate closure).