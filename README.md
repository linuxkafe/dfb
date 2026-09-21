# dfb — Deck FlyBrain 

A compute framework for the **FlyBrain** autonomous flight decision system, running on Steam Deck (x86_64 Linux, AMD APU) with Vulkan acceleration.

## Overview

This project provides a Vulkan compute engine and a neural co-processor prototype for the FlyBrain, running on Steam Deck hardware, accessible remotely via SSH.

## Architecture

- **Client** (development machine): requests, UI, orchestration
- **Server** (Steam Deck via SSH): Vulkan compute service, FlyBrain neural inference

## Quick Start

```bash
make setup      # install dependencies
make check      # run quality gates (lint, test, safety)
make deploy-deck  # deploy service to Steam Deck
```

## Vulkan Compute Engine

Located in `src/dfb/vulkan_engine.py` — a ctypes-based Vulkan 1.3 wrapper with:
- Two-pass compute pipeline (hidden + output shaders)
- Per-submission fencing for correct pass ordering
- Verified on Steam Deck RADV (VANGOGH, API 1.4.330)

## Neural Co-Processor (sim/)

A CPU-only neural co-processor prototype (`sim/`):

- `fly_coprocessor.py` — E-PG ring attractor, mushroom body with DAN plasticity, octopamine habituation
- `semantic_encoder.py` — text → topic angle with pre-synaptic habituation
- `neuro_to_ollama.py` — connectome state → Ollama parameters (temperature, num_predict, context-switch notes)
- `chat_cli.py` — interactive CLI with `++`/`--` feedback, telemetry line
- `test_coprocessor.py` — 13 offline validation cases

```bash
# offline demo (mock Ollama)
python sim/chat_cli.py --mock

# live against Steam Deck Ollama
python sim/chat_cli.py --base-url http://steamdeck:11434 --model llama3.1:8b
```

Telemetry format: `[Compass: 42° | Alert (Oct): 0.78 | Affinity: +0.35 | Temp: 0.65]`

## 🧠 Biological Co-Processor: Frustration Detection (Giant Fiber Circuit)

This project integrates an emulation of *Drosophila* neural circuits (specifically the **Giant Fiber Escape Neuron**) to manage dialogue dynamics in everyday conversations without relying on heavy sentiment classifiers.

### How It Works
* **Potential Accumulation:** Repetitive, frustrated, or unresolved messages increase the membrane potential of the biological circuit.
* **Escape Firing:** When the potential reaches the critical threshold (0.5), the assistant automatically truncates verbose explanations and adopts a strictly direct tone focused on immediate resolution.
* **Recovery:** Constructive dialogue and natural pauses allow passive decay of the potential.

### Practical CLI Example

```text
User: How do I list processes listening on port 8080?
[GF Potential: 0.05 | Mode: Normal | Temp: 0.60]
Bot: You can check which processes are listening on that port using lsof or ss with appropriate privileges:
1. With lsof: `lsof -i :8080`
2. With ss: `ss -tulpn | grep :8080`
Either will show the PID associated with the service.

User: Nothing happened.
[GF Potential: 0.35 | Mode: Normal | Temp: 0.50]
Bot: If the command returned no output, verify you are running it with sufficient privileges or that the port is actually active. Try `sudo ss -tulpn | grep 8080`.

User: Still nothing, it keeps failing!
[GF Potential: 0.82 | Mode: ESCAPE FIRED | Temp: 0.10]
Bot: 
- Run: `sudo ss -lnt` and check if the port appears in the listening column.
- If it does not appear, the service is not running. Do you want to start the service or check system logs?
```

## Development

```bash
make test   # run test suite (pytest)
make lint   # ruff check
make format # ruff format
```

## TODO

- [ ] Persistent memory/DB for co-processor state
- [ ] Streaming UI for chat_cli
- [ ] Real-time audio integration
- [ ] Move simulation to Vulkan compute kernel (un-defer T005)
- [ ] CI: add codecov token for coverage upload
- [ ] Safety gate closure for gRPC surface (T013)

## Hardware Target

Steam Deck (AMD APU, VANGOGH GPU, RADV Vulkan driver). No FC firmware changes — integration via MAVLink/CRSF only.