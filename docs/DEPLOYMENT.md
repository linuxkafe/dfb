# Production Deployment Guide

How to deploy Deck Fly Brain to the Steam Deck (`x86_64` Linux, AMD APU) and
verify it. Covers the systemd unit, the deploy script, verification,
rollback, and operational guarantees. Sprint 03 (T010) hardware validation
supplements this doc; everything here is provable offline.

## Architecture

- **Server (Steam Deck)** — compute node, telemetry ingestion, decision
  engine. Runs as a systemd **user service** `flybrain`.
- **Client (this machine)** — requests, UI, control over SSH tunnel / LAN.
- **Flight controller** — MAVLink/CRSF only; firmware is never touched.

## Prerequisites

1. Steam Deck reachable over SSH as `deck@steamdeck`.
   - If `ssh: Could not resolve hostname steamdeck`, add it to `/etc/hosts`
     or `~/.ssh/config` on this machine.
2. `deck` user in `dialout` group for serial (MAVLink) access:

   ```sh
   sudo usermod -a -G dialout deck
   ```

   `deploy_deck.sh` warns if this is missing. MAVLink uses
   `/dev/ttyACM0` @ 57600 baud; CRSF uses `/dev/ttyACM1` @ 420000 baud
   (set via the unit's `Environment=` lines).
3. SSH key auth working non-interactively (deploy script is `set -euo
   pipefail` and aborts on any SSH failure).

## Deploy

```sh
make deploy-deck
```

This runs `scripts/deploy_deck.sh`, which:

1. Creates the destination dir `~/.local/share/dfb` on the Deck.
2. rsyncs `src/`, `sim/`, `shaders/`, `pyproject.toml`, `Makefile`
   (excludes venv, caches, coverage artifacts).
3. Recreates the Deck venv and installs `-e . psutil` (psutil feeds the
   resource monitor used by `make test-deck`).
4. Installs `deploy/flybrain.service` into `~/.config/systemd/user/`.
5. `systemctl --user daemon-reload && restart && enable`.
6. Prints a `/health` curl as a smoke check.

## The systemd unit

`deploy/flybrain.service` (validated offline by
`tests/deploy/test_deployment.py`):

- **HTTP API** on `0.0.0.0:8082` (uvicorn), **gRPC** on `8083`.
- **Sleep-inhibit guarantee**: uvicorn runs *under* `systemd-inhibit
  --what=sleep:handle-lid-switch --mode=block`, so the Deck cannot sleep
  or suspend on lid-close while the service is up. The lock is held for
  the lifetime of the process (this is why the inhibitor wraps
  `ExecStart` — a bare `ExecStartPre systemd-inhibit` without a command
  would never hold it).
- **Resource limits** tuned for Deck (8 GB RAM, 4C/8T):
  `MemoryMax=2G`, `MemoryHigh=1.5G`, `CPUQuota=200%` (2 cores). Keeps
  thermally-throttled Deck stable during flight.
- `Restart=on-failure` / `RestartSec=5`; logs to journal
  (`journalctl --user -u flybrain`).

## Verify

```sh
# On Deck
curl -s http://localhost:8082/health
journalctl --user -u flybrain -f

# From LAN (no tunnel)
make test-deck
```

`make test-deck` deploys a resource monitor, runs a 20-episode maze
benchmark against the LAN endpoint, and writes a summary — Sprint 03's
T012 performance validation can reuse this path.

A healthy `/health` returns JSON `"status": "ok"` with component statuses.

## Rollback

```sh
ssh deck@steamdeck "systemctl --user stop flybrain"
```

Then `make deploy-deck` again with the previous commit checked out, or
restore the unit from git. The deploy is idempotent (rsync `--delete` +
venv recreate), so a re-deploy of any older tree is a full rollback.

## Operational notes

- The service listens on `0.0.0.0`; the LAN / SSH-tunnel exposure is your
  network's decision. No secrets are served by the API.
- Changing ports/`MAVLINK_*`/`CRSF_*` requires editing the unit, then
  `systemctl --user daemon-reload` on the Deck. The deploy tests assert
  port/env consistency, keeping unit and code from drifting.
- All HTTP JSON responses pass through `SanitizingJSONResponse` (the app's
  `default_response_class`), so non-finite floats (`inf`/`nan` link ages)
  become `null` rather than HTTP 500 — see QUALITY_GATES.md.