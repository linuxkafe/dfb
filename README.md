# dfb

A compute framework for Steam Deck (x86_64 Linux, AMD APU) with Vulkan acceleration.

## Overview

This project provides a Vulkan compute engine and a neural co-processor prototype running on Steam Deck hardware, accessible remotely via SSH.

## Architecture

- **Client** (development machine): requests, UI, orchestration
- **Server** (Steam Deck via SSH): Vulkan compute service, neural inference

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

Telemetry format: `[Bússola: 42° | Alerta (Oct): 0.78 | Afinidade: +0.35 | Temp: 0.65]`

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