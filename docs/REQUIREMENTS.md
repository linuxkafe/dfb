# Requirements

## Functional

- [ ] Establish SSH connectivity to Steam Deck (deck@steamdeck).
- [ ] Deploy Fly Brain service to Steam Deck (systemd or container).
- [ ] Expose RPC/API on Steam Deck for client requests (decision queries, telemetry).
- [ ] Establish MAVLink/CRSF link from Steam Deck to flight controller.
- [ ] Client CLI / library to send requests to Deck service.
- [ ] Telemetry ingestion pipeline on Deck (MAVLink → internal state).
- [ ] Decision engine stub (returns safe advisory output).
- [ ] Safety gate: any command toward aircraft requires explicit confirmation.

## Non-Functional

- Performance: target still open (Steam Deck APU budgeted).
- Security: SSH keys only; no passwords. Commands toward aircraft pass explicit confirmation gate.
- Maintainability: AES protocol, tested Python, docs-first.
- Safety: FC firmware is never modified by this project.
- Reliability: service auto-restart on Deck; graceful degradation on link loss.

## Constraints

- Language: python (both client and server)
- Deployment: Steam Deck (x86_64 Linux, AMD APU) — systemd service or podman container
- Transport: SSH tunnel for control plane; local UDP/TCP for MAVLink
- Dependencies: pymavlink or mavsdk for MAVLink; CRSF binding TBD

## Open Questions

- Semantics of "Fly Brain" — confirmed? See docs/VISION.md [UNKNOWN].
- Which link protocol first (MAVLink vs CRSF) — likely MAVLink via pymavlink.
- Service deployment model: systemd vs podman/container.
- API protocol: gRPC, HTTP/JSON, or custom binary over SSH tunnel.
- Telemetry rate and bandwidth over SSH tunnel.