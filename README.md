# dfb — Deck Fly Brain

Autonomous flight decision service for FPV drones, running on Steam Deck hardware.

## Architecture

- **Client** (this machine): requests, UI, orchestration
- **Server** (Steam Deck via SSH): Fly Brain service — telemetry ingest, decision engine, MAVLink/CRSF link

## Quick Start

```bash
make setup      # install dependencies
make check      # run quality gates
make deploy-deck  # deploy service to Steam Deck (after T001)
```

## Development

This project follows the **AES (Ambrósio Engineering System)** protocol.
See `CLAUDE.md` for the operational contract.

## Fly-Brain Neural Co-Processor (sim/)

A bio-inspired "fly brain" that shapes a chatbot's temperament via connectome
circuits (numpy + requests only, CPU-only, <1.5 GB RAM):

- `sim/fly_coprocessor.py` — E-PG ring attractor, sparse mushroom body with
  DAN reward/punishment plasticity, octopamine habituation pool
- `sim/semantic_encoder.py` — topic -> E-PG angle, pre-synaptic habituation
- `sim/neuro_to_ollama.py` — connectome state -> Ollama temperature/length and
  context-switch / caution system notes
- `sim/chat_cli.py` — interactive CLI; `++` / `--` reward/punish; telemetry line
- `sim/test_coprocessor.py` — offline 5-turn validation (mock Ollama)

```bash
# offline demo (deterministic mock reply)
python sim/chat_cli.py --mock

# live against Steam Deck Ollama (llama3.1:8b)
python sim/chat_cli.py --base-url http://steamdeck:11434 --model llama3.1:8b
```

Telemetry: `[Bússola: 42° | Alerta (Oct): 0.78 | Afinidade: +0.35 | Temp: 0.65]`