# T014-verify — Proof of Vulkan GPU inference on Steam Deck

## Environment (Deck)

- Driver: `vulkan-radeon 26.0.0_devel.214837.steamos_25.11.15-1` (RADV, Mesa
  26.0.0-devel git-9cc9241790), API 1.4.330, driverVersion 25.99.99
- GPU: `AMD Custom GPU 0405 (RADV VANGOGH)` — Steam Deck APU
- Host: dev machine → `deck@steamdeck` (SSH, BatchMode); deploy path
  `~/.local/share/dfb`, venv `.venv/bin/python`

## Final proof (3 inputs, GPU vs CPU reference)

```
$ .venv/bin/python vk_proof3.py
W1[0][:3] = [ 0.04967142 -0.01382643  0.06476886]
b1[:3]    = [ 0.03301138 -0.08140107 -0.03656771]
W2[0][:3] = [-0.12077594  0.08091128 -0.08497209]
b2        = [ 0.05682734  0.10863807  0.03333699 -0.24928105]

ones: gpu=[0.010499999858438969, -0.4458400011062622, -0.0443900004029274, -0.4244599938392639]
ones: ref=[0.010499999858438969, -0.4458400011062622, -0.0443900004029274, -0.4244599938392639]   ✔
hot0: gpu=[-0.12060999870300293,  0.0398700013756752, 0.08399999886751175, -0.28016000986099243]
hot0: ref=[-0.12060999870300293,  0.0398700013756752, 0.08399999886751175, -0.28016000986099243]   ✔
cold: gpu=[ 0.06646999716758728, -0.391539990901947, 0.17287999391555786, -0.6625999808311462]
cold: ref=[ 0.06646999716758728, -0.391539990901947, 0.17287999391555786, -0.6625999808311462]   ✔
🧹 VulkanEngine cleaned up
```

Outputs identical to CPU reference — `gpu == ref` per input (float32 exact).

## Crash -> fix timeline

1. Original symptom (pre-fix): segfault during `initialize()`; faulthandler
   showed crash inside `_create_descriptor_set` → `vkUpdateDescriptorSets`.
2. RC-1 fixed (memory-props struct 264→520 B): crash *moved* to line 767
   (`vkUpdateDescriptorSets`) — not resolved. This proved RC-1 was necessary but
   not sufficient.
3. Isolated with 3 Deck probes + gdb: SIGSEGV inside `libvulkan_radeon.so`
   (`mov (%rax,%r12,8),%rax`, r12=0). Field offsets of `VkWriteDescriptorSet`
   verified ABI-correct — so a third cause (RC-3) was suspected.
4. Written minimal **C ABI reproducer** (`/tmp/opencode/vk_cprobe.c`, built with
   gcc, shipped as `/tmp/vk_cprobe`) — reproduced the same SIGSEGV with
   `descriptorType=5`. Changed to `7` → clean pass (`C-PROBE OK`, EXIT=0).
5. RC-3 confirmed: `VK_DESCRIPTOR_TYPE_STORAGE_BUFFER = 7`, not 5. Engine
   constant fixed → Python engine stopped crashing.
6. Numeric mismatch surfaced (output = previous input's result). Hidden-layer
   readback proved pass 2 was reading stale `hidden`; per-submission fence
   (RC-5) fixed it, giving bit-exact results.

## Local quality gates (dev machine)

- `make test` — 92 passed, 1 skipped, 8 warnings. `make lint` — All checks passed.
- `make check` — docs/code/test/lint/safety OK; coverage 43% (<80% threshold,
  pre-existing gap, non-gating per Makefile).

## Residual risk

- Deck runs a **dev** RADV build; intra-command-buffer pipeline barrier between
  the two compute passes is not honoured (degraded to submission-boundary
  fencing). If Valve ships this codepath in a stable mesa release the single-CB
  barrier may be restoreable for lower latency.
- `.spv` shaders exist only on Deck; sources in `shaders/*.comp`. Recompile
  requires glslang/glslc (not installed on either host) — sources checked in.