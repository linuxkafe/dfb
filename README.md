# dfb — Deck FlyBrain

Autonomous flight **decision service** for FPV drones, running as a service on
**Steam Deck** hardware (x86_64 Linux, AMD APU), accessed remotely via SSH /
LAN. Flight-controller integration is via **MAVLink/CRSF only** — no FC
firmware is ever touched.

## Architecture

```
Client (dev machine)  ── HTTP :8082 / gRPC :8083 ──▶  Steam Deck (server)
                                                         │  compute
                                                         ▼
                          MAVLink ─ /dev/ttyACM0 ──┬──▶ ingest ──▶ state estimator
                          CRSF    ─ /dev/ttyACM1 ──┘         (NED→ENU, fusion)
                                                        │
                                                        ▼
                                        advisor ──▶ safety envelope ──▶ advisory
```

- **Server (Steam Deck):** telemetry ingestion (MAVLink + CRSF), state
  estimation, safety envelope, and the decision (advisory) engine. Runs as a
  systemd user service (`flybrain`) — HTTP (uvicorn, `8082`) + gRPC (`8083`).
- **Client (development machine):** requests, UI, orchestration — over an SSH
  tunnel or direct LAN.

## Components

| Area | Source | Role |
|------|--------|------|
| HTTP API | `src/dfb/service.py` | `/health`, `/version`, `/telemetry`, `/decide`, `/metrics`, `/confirm/issue`, `/command`, `/confirm/verify` |
| gRPC API | `src/dfb/grpc_server.py`, `grpc_service.py` | Same surface over protobuf, `8083` |
| MAVLink ingest | `src/dfb/mavlink_ingest.py` | Telemetry from flight controller (`/dev/ttyACM0`) |
| CRSF/ELRS ingest | `src/dfb/crsf_ingest.py` | Telemetry from radio link (`/dev/ttyACM1`) |
| State estimation | `src/dfb/state_estimator.py` | Consistency checks, NED→ENU, anomaly detection |
| Safety envelope | `src/dfb/safety_envelope.py` | Geofence/altitude/battery/link/GPS/speed limits |
| Advisor | `src/dfb/advisor.py` | Mission-goal advisory + safety gating |
| Compute engines | `src/dfb/cpu_engine.py`, `vulkan_engine.py` | Inference backends; Vulkan optional, CPU fallback |
| Metrics | `src/dfb/metrics.py` | Prometheus exposition at `/metrics` |
| JSON boundary | `src/dfb/serialization.py` | Sanitizes non-finite floats → `null` (no HTTP 500) |
| CLI | `src/dfb/cli.py` | `dfb` — health, version, decide, decide-telemetry, telemetry, issue/verify-token, command |

Decision is **advisory only**: the service recommends; a human (or the pilot)
issues safety-critical commands, which require a short-lived confirmation
token on `/command`. The system never sends conflicting safety-critical
commands without explicit confirmation.

## Quick Start

```bash
make setup                 # install dependencies
make run                   # start the HTTP service (uvicorn :8082)
make check                 # run quality gates (docs, tests, lint, tautology, safety)
make deploy-deck           # deploy to Steam Deck (systemd user service)
make test-deck             # LAN integration + resource monitor on Deck
make test-deploy           # offline deployment tests (systemd unit, smoke boot)
```

Requires Python ≥ 3.11. Extras: `pip install -e .[cli,sim,grpc]`.

### CLI (dev machine)

```bash
dfb health --host steamdeck
dfb decide '{"position":[1,1],"grid":[[...]],"exit":[9,9]}'
dfb decide-telemetry --lat 47.001 --lon 8.001 --alt 50 --speed 10
dfb telemetry
dfb issue-token && dfb command ARM arming --token <TOKEN>
```

## Vulkan Compute Engine

`src/dfb/vulkan_engine.py` — a ctypes-based Vulkan 1.3 wrapper (optional):
two-pass compute pipeline with per-submission fencing. **Graceful
degradation**: if Vulkan is unavailable, inference falls back to the CPU
engine — the service runs on any Deck regardless of driver state.

## Neural Co-Processor Prototype (sim/)

A CPU-only research prototype (`sim/`):

- `fly_coprocessor.py` — E-PG ring attractor, mushroom body with DAN
  plasticity, octopamine habituation
- `semantic_encoder.py` — text → topic angle with pre-synaptic habituation
- `neuro_to_ollama.py` — connectome state → Ollama parameters
- `chat_cli.py` — interactive CLI with `++`/`--` feedback + Giant Fiber
  frustration circuit
- `test_coprocessor.py` — offline validation cases

```bash
python sim/chat_cli.py --mock                        # offline demo (mock Ollama)
python sim/chat_cli.py --base-url http://steamdeck:11434 --model llama3.1:8b
```

## Deployment

See **`docs/DEPLOYMENT.md`** for the full guide (prerequisites, systemd unit,
verification, rollback). Highlights:

- systemd user unit `flybrain`: uvicorn runs **under** `systemd-inhibit` so
  the Deck never sleeps mid-flight; `MemoryMax=2G`, `CPUQuota=200%`
  (thermally-throttled Deck budget).
- `scripts/deploy_deck.sh` is idempotent (rsync `--delete` + venv recreate) —
  re-deploying any older tree is a full rollback.

## Quality Gates

`make check` runs, in order:

| Gate | Command | Result today |
|------|---------|--------------|
| Docs check | `make docs-check` | BLOCKER — docs missing/stale |
| Code check | `make code-check` | BLOCKER — TODOs |
| Test check | `make test-check` | WARNING — coverage < 80% |
| Lint check | `make lint-check` | BLOCKER — ruff errors (`src tests`) |
| Tautology check | `make tautology-check` | BLOCKER — always-true assertions |
| Safety check | `make safety-check` | BLOCKER — traceability matrix |

CI (`.github/workflows/ci.yml`) runs the same gates on every PR. Current
state: **213 tests pass, 18 skipped, 80.7% coverage**, 20 REQs / 46 hazards
traced. Every HTTP JSON response is sanitized by
`SanitizingJSONResponse`; see `docs/QUALITY_GATES.md` for details.

## Project Docs

- `docs/VISION.md` — problem space
- `docs/REQUIREMENTS.md` — functional requirements & safety traceability
- `docs/ROADMAP.md` — sprints, milestones, risk register
- `docs/DESIGN.md` — architecture
- `docs/DEPLOYMENT.md` — deployment guide
- `docs/QUALITY_GATES.md` — gate definitions

## Hardware Target

Steam Deck (AMD APU, VANGOGH GPU, RADV Vulkan driver). No FC firmware
changes — integration via MAVLink/CRSF only. Sprint 03 hardware validation
(T010–T013) is pending access to the physical Deck.