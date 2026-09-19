# T002 — Diffstory (Build Output)

## What Changed

### Files Created
- `src/dfb/service.py` — Added `/decide` endpoint (POST) with Pydantic models
- `tests/maze_sim.py` — Maze simulation with BFS solver, Fly agent, benchmark runner
- `tests/deck/test_integration.py` — Integration tests (health, version, decide, latency, maze benchmark)
- `scripts/monitor_deck.py` — Resource monitor (runs on Deck, streams CSV: CPU%, mem%, temp°C, power_W)
- `scripts/run_monitor.py` — Local runner: SSH-deploys monitor, collects CSV
- `scripts/generate_summary.py` — Generates markdown summary from CSV + test results
- `aes/tickets/T002-plan.md` — Hostile Analysis (Phase 1)
- `aes/tickets/T002-build.md` — Solution Proposal (Phase 2) + this diffstory

### Files Modified
- `scripts/deploy_deck.sh` — Added `psutil` install for monitoring
- `pyproject.toml` — Added optional dependencies: `test` (requests, psutil), `monitor` (psutil)
- `Makefile` — Added `test-deck` target (direct LAN, no SSH tunnel for service calls)
- `aes/kanban.md` — T002 moved to Done

## Why It Changed

**Problem**: Need initial integration tests, maze benchmark, and resource monitoring baseline for Fly Brain service on Steam Deck.

**Solution**: 
- Service now has `/decide` stub for decision requests
- Maze benchmark runs 20 episodes (10x10 empty grid) via direct LAN to `steamdeck:8082`
- Resource monitor deployed via SSH, runs on Deck, streams CSV over SSH stdout
- SSH used ONLY for deployment and monitor collection; service calls go direct LAN

## What Was Intentionally Untouched

- MAVLink integration (T003 separate)
- Decision engine logic (T003) — stub only
- Auth/TLS on service (dev LAN only)
- Client library (T004)

## Remaining Risks / Follow-up

1. **Service `/decide` stub is naive greedy** — doesn't handle obstacles/boundaries; T003 replaces with real engine
2. **Maze benchmark uses empty grid (obstacle_density=0)** — so greedy matches BFS; obstacles need smarter service
3. **Power reading via AMD hwmon** — works but may not be true package power; RAPL not available on Deck
4. **Temperature stable at 47-48°C** — well below throttling threshold (80°C+)
5. **CPU usage low (avg ~3%, peaks ~15%)** — plenty of headroom for real decision engine
6. **Monitor runs 120s fixed** — should be tied to test duration dynamically

## Validation Performed

- `make check` — passes (8 tests, 80% coverage, ruff clean)
- `make deploy-deck` — succeeds, service healthy on Deck
- `make test-deck` — succeeds:
  - Direct LAN access verified (`steamdeck:8082`)
  - 20 maze episodes: 100% success, avg latency ~3ms
  - Resource monitor: 122 samples over 120s
  - CSV logged to `aes/verification/T002/raw/resources.csv`
  - Summary generated at `aes/verification/T002/summary.md`

## Resource Baseline (for future optimization)

| Metric | Avg | Min | Max | P50 | P95 |
|--------|-----|-----|-----|-----|-----|
| CPU | ~3% | 0% | 21% | 0% | ~10% |
| Memory | 16.9% | 16.9% | 17.0% | 16.9% | 17.0% |
| Temperature | 47.5°C | 47°C | 48°C | 47°C | 48°C |
| Power | ~2.3W | 2.1W | 4.1W | 2.1W | 3.1W |

**Key observation**: Steam Deck runs cool (47-48°C) with plenty of thermal headroom. CPU and power are minimal with current stub service. Real decision engine (T003) will increase load — monitor for regression.