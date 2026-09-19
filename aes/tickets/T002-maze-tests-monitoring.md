---
ticket: T002
title: Initial service tests, maze simulation & resource monitoring on Steam Deck
sprint: sprint-01
priority: high
status: pending
created: 2026-09-19
---

# T002 — Initial service tests, maze simulation & resource monitoring

## Context

Now that T001 deployed the basic health service on Steam Deck, we need to:
1. Run initial integration tests against the deployed service (health, version, latency)
2. Create a test suite simulating a "fly in a maze" — a pathfinding benchmark that
   exercises the decision engine loop (stub for now) and measures latency/throughput
3. Monitor Steam Deck resource usage (CPU, RAM, thermal, power) during test runs
   via SSH and log to local machine for future optimization

This establishes the testing & observability foundation before T003 (decision engine).

## Acceptance Criteria

- [ ] Integration test suite runs against `deck@steamdeck` service (health, latency, concurrent requests)
- [ ] Maze simulation test: configurable grid, fly starts at (0,0), exit at (N-1,N-1), obstacles random
  - Fly uses simple BFS/DFS/A* to find path (pure Python, no ML yet)
  - Records: path length, steps taken, time per decision, success/failure
- [ ] Resource monitor: SSH to Deck, sample `/proc/stat`, `/proc/meminfo`, `/sys/class/thermal/`, `powercap` every 1s during test
  - Logs CSV locally with timestamps: cpu%, mem%, temp°C, power_W
  - Runs for duration of maze test (configurable episodes)
- [ ] Make target `make test-deck` runs full suite and produces report
- [ ] Results stored in `aes/verification/T002/` with summary markdown

## Scope

**In scope:**
- Integration tests (pytest) hitting remote service via SSH tunnel
- Maze simulation as standalone test module (no service changes yet)
- Resource monitoring script (Python + SSH)
- Local CSV/JSON logs + summary report
- Makefile integration

**Out of scope:**
- Actual MAVLink integration (T002 separate ticket)
- Decision engine logic (T003)
- Service modifications — tests only observe

## Dependencies

- T001 done (service running on Deck)
- SSH access to Deck verified
- Python 3.11+ on both machines

## Rollback

No service changes — only test code. Remove `tests/deck/`, `scripts/monitor_deck.py`, `scripts/maze_sim.py`.

## Known Risks

- SSH tunnel latency adds noise to latency measurements
- Deck thermal throttling may kick in during sustained load
- `powercap`/`RAPL` may not be exposed on Steam Deck AMD APU
- Concurrent test runs may conflict with service port (8082)

## Notes

- Maze size: start with 10x10, 20% obstacle density, 100 episodes
- Resource sampling: 1 Hz, non-blocking SSH commands
- Use `paramiko` or `subprocess` for SSH (paramiko cleaner for persistent connection)
- Store raw CSV in `aes/verification/T002/raw/`, summary in `aes/verification/T002/summary.md`