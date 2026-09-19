---
project: dfb
created: 2026-09-19
current_sprint: sprint-02
current_ticket: T009
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
| T010 | CRSF/ELRS support for crossfire receivers | medium | pending |
| T011 | gRPC API for lower-latency client-deck communication | medium | pending |
| T012 | Safety certification artifacts (hazard analysis, test reports) | high | pending |

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

## Done

| ID | Title | Completed |
|----|-------|-----------|
| T009 | Service hardening: auto-restart, graceful degradation, health checks | 2026-09-19 |
| T008 | Decision engine with real telemetry (state estimation + advisory) | 2026-09-19 |
| T007 | MAVLink telemetry ingestion pipeline on Steam Deck | 2026-09-19 |
| T006 | MuJoCo physics + neural inference via ONNX Vulkan on Steam Deck | 2026-09-19 |
| T004 | Client library / CLI to query Deck service | 2026-09-19 |
| T003 | Decision engine (CPU) + safety gate + visualization | 2026-09-19 |
| T002 | Initial service tests, maze sim & resource monitoring | 2026-09-19 |
| T001 | SSH connectivity & service scaffold on Steam Deck | 2026-09-19 |
| — | Project scaffold (AES, docs, git) | 2026-09-19 |