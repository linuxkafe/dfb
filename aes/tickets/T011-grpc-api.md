---
ticket: T011
title: gRPC API for lower-latency client-deck communication
sprint: sprint-03
priority: medium
status: pending
created: 2026-09-19
---

# T011 — gRPC API

## Acceptance Criteria

1. **Protobuf schema**: Defines Telemetry, Decision, Command, SafetyToken messages
2. **gRPC service**: FlyBrainService with Decide, GetTelemetry, IssueToken, VerifyToken, SendCommand RPCs
3. **Streaming telemetry**: Server-side streaming GetTelemetryStream for real-time updates
4. **TLS/mTLS**: Optional mutual TLS for production (self-signed for dev)
5. **Client update**: DeckClient supports both HTTP and gRPC transports
6. **Benchmarks**: gRPC vs HTTP latency comparison (target: <5ms p99 vs ~20ms HTTP)
7. **Tests**: gRPC contract tests, streaming stress test

## Scope

- **In**: gRPC service implementation, protobuf definitions, dual-transport client, TLS config
- **Out**: HTTP/3, WebSocket fallback, gRPC-Gateway (REST proxy)

## Dependencies

- T004 (existing HTTP client)
- grpcio, grpcio-tools (new deps)
- protobuf (new dep)

## References

- docs/REQUIREMENTS.md REQ-34 (open question)
- src/dfb/client.py