# Requirements

Numbered requirement baseline for the Deck Fly Brain (DFB) system.
IDs (REQ-01..REQ-20) are the traceability keys used by `docs/safety/traceability.md`
and validated by `make safety-check`. SATISFIED status refers to implementation
coverage; verification evidence lives in the traceability matrix.

## Functional

- [x] **REQ-01** — Establish SSH connectivity to Steam Deck (`deck@steamdeck`), key-based auth only.
- [x] **REQ-02** — Deploy Fly Brain service to Steam Deck as a systemd unit (auto-start, restart policy).
- [x] **REQ-03** — Expose RPC/API on Steam Deck for client requests (REST on :8082, gRPC on :8083).
- [x] **REQ-04** — Establish MAVLink and CRSF/ELRS link from Steam Deck to flight controller.
- [x] **REQ-05** — Client CLI / library (`dfb`) to send requests to Deck service.
- [x] **REQ-06** — Telemetry ingestion pipeline on Deck (MAVLink/CRSF → internal state).
- [x] **REQ-07** — Decision engine producing safe advisory output (state estimation + advisor).
- [x] **REQ-08** — Safety gate: any command toward aircraft requires explicit confirmation (single-use token, 30s TTL).
- [x] **REQ-09** — State estimator: NED→ENU transform, GPS/IMU fusion, anomaly detection.
- [x] **REQ-10** — Mode awareness: advisory gating by flight mode (no advisory in MANUAL/ACRO).
- [x] **REQ-11** — Advisory decisions constrained by safety envelope; CRITICAL violation → RTL advisory.
- [x] **REQ-12** — Safety envelope checks: geofence, altitude floor/ceiling, battery reserve, link age, GPS quality, speed/attitude limits.
- [x] **REQ-13** — CRSF/ELRS raw frame parsing with CRC8 validation and incremental framing.
- [x] **REQ-14** — gRPC API: unary calls + server-streaming telemetry stream.
- [x] **REQ-15** — HTTP/REST API: `/health`, `/version`, `/decide`, `/telemetry`, `/confirm/*`, `/command`, `/metrics`.
- [x] **REQ-16** — Health monitoring and Prometheus metrics endpoint (`/metrics`).
- [x] **REQ-17** — Security: SSH keys only; no passwords anywhere.
- [x] **REQ-18** — Structured JSON logging with correlation IDs.
- [x] **REQ-19** — Safety: FC firmware is never modified by this project (MAVLink/CRSF integration only).
- [x] **REQ-20** — Reliability: service auto-restart on failure; graceful degradation on link loss.

## Non-Functional Constraints

- Performance: advisory latency target < 100ms (CPU EP measured 6.2× faster than raw PyTorch).
- Deployment: Steam Deck (x86_64 Linux, AMD APU) — systemd service, MemoryMax=2G, CPUQuota=200%.
- Transport: SSH tunnel control plane; local UDP/TCP for MAVLink; CRSF serial.
- Dependencies: pymavlink, numpy (no PyTorch runtime dependency for inference).
- Maintenance: AES protocol, tested Python, docs-first with CI quality gates.

## Open Questions

- Semantics of "Fly Brain" — see docs/VISION.md [UNKNOWN].
- Regulatory environment (country-specific UAS rules) — outside DFB scope, affects ops not code.
- Vulkan EP build on Deck (T005 deferred) — CPU EP sufficient for current advisory load.