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