---
ticket: T001
title: SSH connectivity & service scaffold on Steam Deck
sprint: sprint-01
priority: high
status: done
created: 2026-09-19
---

# T001 — SSH connectivity & service scaffold on Steam Deck

## Context

First concrete step: verify SSH access to the Steam Deck, deploy a minimal
Python service that runs as a systemd unit (or podman container), and expose
a health-check endpoint over the SSH tunnel.

This unlocks all subsequent work (telemetry, decision engine, client).

## Acceptance Criteria

- [ ] SSH key-based access to `deck@steamdeck` works from this machine.
- [ ] A Python service starts on Deck via systemd (or podman) and stays alive.
- [ ] Service exposes a health endpoint reachable via SSH tunnel (e.g. `ssh -L 8080:localhost:8080 deck@steamdeck` then `curl localhost:8080/health`).
- [ ] Service logs visible via `journalctl -u flybrain` (or `podman logs`).
- [ ] Deploy script / Make target automates the push from this machine.

## Scope

**In scope:**
- SSH key setup verification / guidance.
- Minimal FastAPI (or aiohttp) service with `/health` and `/version`.
- systemd unit file (or Containerfile + systemd generator).
- Makefile target `make deploy-deck` that rsyncs/copies and restarts service.

**Out of scope:**
- MAVLink integration (T002).
- Decision logic (T003).
- Client library (T004).

## Dependencies

- Steam Deck reachable on LAN / Tailscale.
- User has `deck` sudo access on Deck.

## Rollback

`ssh deck@steamdeck 'sudo systemctl stop flybrain && sudo systemctl disable flybrain'`
(or `podman stop flybrain && podman rm flybrain`)

## Known Risks

- Steam Deck may sleep/suspend — need `systemd-inhibit` or similar.
- SSH tunnel stability for long-running connections.
- Deck OS (SteamOS) is immutable-ish — `/etc` changes persist but `/usr` doesn't.
  Use `/home/deck/.config/systemd/user/` or `/etc/systemd/system/` with care.

## Notes

- Start with systemd user service (no sudo) if possible.
- Python 3.11+ on Deck (SteamOS 3.x).
- Keep service minimal: health + version + structured logging.