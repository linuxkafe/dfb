---
project: dfb
created: 2026-09-19
current_sprint: sprint-04
current_ticket: T013
---

# Kanban — dfb (Deck Fly Brain)

## Backlog

| ID | Title | Priority | Status |
|----|-------|----------|--------|
| T001 | SSH connectivity & service scaffold on Steam Deck | high | done |
| T002 | Initial service tests, maze sim & resource monitoring | high | done |
| T003 | Decision engine (CPU) + safety gate + visualization | high | done |
| T004 | Client library / CLI to query Deck service | medium | done |
| T005 | Vulkan GPU acceleration for decision engine | medium | deferred |
| T006 | MuJoCo physics + neural inference via ONNX Vulkan on Steam Deck | high | done |
| T007 | MAVLink telemetry ingestion pipeline on Steam Deck | high | done |
| T008 | Decision engine with real telemetry (state estimation + advisory) | high | done |
| T009 | Service hardening: auto-restart, graceful degradation, health checks | medium | done |
| T010 | CRSF/ELRS support for crossfire receivers | medium | done |
| T011 | gRPC API for lower-latency client-deck communication | medium | done* |
| T012 | Safety certification artifacts (hazard analysis, test reports) | high | done |
| T013 | Close gRPC safety gate hole + add test evidence (gRPC/HTTP routes/CLI) | critical | in_progress |
| T014 | Vulkan on Steam Deck — functional verification + crash fix (T005 un-defer) | critical | done |
| T015 | Neural co-processor PoC: Ollama + CPU/Vulkan neural net on-deck | high | done |

## Sprint 01 — Foundation

**Goal**: Establish SSH-deployed service on Steam Deck with MAVLink ingest stub.

| ID | Title | Status |
|----|-------|--------|
| T001 | SSH connectivity & service scaffold on Steam Deck | done |
| T002 | Initial service tests, maze sim & resource monitoring | done |
| T003 | Decision engine (CPU) + safety gate + visualization | done |
| T006 | MuJoCo physics + neural inference via ONNX Vulkan on Steam Deck | done |

## Sprint 02 — Telemetry & Decision

**Goal**: Establish MAVLink telemetry ingestion from flight controller, build state estimation, and produce safe advisory decisions on Deck.

| ID | Title | Status |
|----|-------|--------|
| T007 | MAVLink telemetry ingestion pipeline on Steam Deck | done |
| T008 | Decision engine with real telemetry (state estimation + advisory) | done |
| T009 | Service hardening: auto-restart, graceful degradation, health checks | done |

## Sprint 03 — Comms & Safety

**Goal**: Add CRSF/ELRS support, gRPC API for low latency, and safety certification artifacts.

| ID | Title | Status |
|----|-------|--------|
| T010 | CRSF/ELRS support for crossfire receivers | done |
| T011 | gRPC API for lower-latency client-deck communication | done* |
| T012 | Safety certification artifacts (hazard analysis, test reports) | done |

\* T011 evidence gap (no committed code, no tests, unguarded command surface) tracked
by T013. Retrospective: `aes/sprints/sprint-03.md`.

## Sprint 04 — Safety Gate Closure & Evidence

**Goal**: Close the gRPC safety-gate bypass, add real test evidence (gRPC, HTTP routes,
CLI), clean repo hygiene. Per sprint-03 retrospective: *no ticket done without committed
code + tests + passing gates.*

| ID | Title | Status |
|----|-------|--------|
| T013 | Close gRPC safety gate hole + add test evidence (gRPC/HTTP routes/CLI) | in_progress |
| T014 | Vulkan on Steam Deck — functional verification + crash fix (T005 un-defer) | done |
| T015 | Neural co-processor PoC: Ollama + CPU/Vulkan neural net on-deck | done |

Retrospective: `aes/sprints/sprint-04.md`

## Done

| ID | Title | Completed |
|----|-------|-----------|
| T010 | CRSF/ELRS support for crossfire receivers | 2026-09-19 |
| T011 | gRPC API for lower-latency client-deck communication | 2026-09-19 (evidence gap → T013) |
| T012 | Safety certification artifacts (hazard analysis, test reports) | 2026-09-20 |
| T009 | Service hardening: auto-restart, graceful degradation, health checks | 2026-09-19 |
| T008 | Decision engine with real telemetry (state estimation + advisory) | 2026-09-19 |
| T007 | MAVLink telemetry ingestion pipeline on Steam Deck | 2026-09-19 |
| T006 | MuJoCo physics + neural inference via ONNX Vulkan on Steam Deck | 2026-09-19 |
| T004 | Client library / CLI to query Deck service | 2026-09-19 |
| T003 | Decision engine (CPU) + safety gate + visualization | 2026-09-19 |
| T002 | Initial service tests, maze sim & resource monitoring | 2026-09-19 |
| T001 | SSH connectivity & service scaffold on Steam Deck | 2026-09-19 |
| — | Project scaffold (AES, docs, git) | 2026-09-19 |