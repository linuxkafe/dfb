# T001 — Diffstory (Build Output)

## What Changed

### Files Created
- `src/dfb/service.py` — Minimal FastAPI service with `/health` and `/version` endpoints
- `deploy/flybrain.service` — systemd user unit for Steam Deck
- `scripts/deploy_deck.sh` — Automated deploy script (rsync + venv + systemctl)
- `aes/tickets/T001-plan.md` — Hostile Analysis (Phase 1)
- `aes/tickets/T001-build.md` — Solution Proposal (Phase 2)

### Files Modified
- `Makefile` — Added `deploy-deck` target
- `aes/kanban.md` — T001 moved to Done
- `aes/tickets/T001-ssh-deck-scaffold.md` — Status → done

## Why It Changed

**Problem**: Need a running Fly Brain service on Steam Deck accessible from dev machine via SSH.

**Solution**: Systemd user service + venv + rsync deploy, exposing FastAPI health endpoint on port 8082.

## What Was Intentionally Untouched

- Local `src/main.py` — remains dev entry point
- MAVLink integration (T002) — out of scope
- Decision engine (T003) — out of scope
- Client library (T004) — out of scope
- Production hardening (TLS, auth, secrets) — out of scope

## Remaining Risks / Follow-up

1. **Port 8082 hardcoded** — should be configurable via env var
2. **User service linger** — `loginctl enable-linger deck` needed for auto-start on boot (not tested)
3. **SSH tunnel automation** — `make deploy-deck` doesn't open tunnel; manual `ssh -L` needed for health check
4. **Service discovery** — no mDNS/avahi; hardcoded `deck@steamdeck` hostname
5. **pymavlink not yet used** — installed but unused; T002 will wire it
6. **Deck sleep** — `systemd-inhibit` in unit blocks lid-switch/sleep but not tested on actual suspend

## Validation Performed

- `make check` — passes (tests 80% coverage, ruff lint clean)
- `make deploy-deck` — succeeds, service starts on Deck
- `ssh deck@steamdeck 'systemctl --user status flybrain'` — active (running)
- `ssh deck@steamdeck 'curl -s http://localhost:8082/health'` — `{"status":"ok","version":"0.1.0"}`
- `ssh deck@steamdeck 'journalctl --user -u flybrain'` — logs visible
- SSH tunnel test — `ssh -L 8082:localhost:8082 deck@steamdeck` + local curl works