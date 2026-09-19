---
ticket: T011
phase: plan
status: done
created: 2026-09-19
tier: standard
requires:
  - aes/kanban.md
  - aes/tickets/T011-grpc-api.md
produces:
  - aes/tickets/T011-plan.md
blocked_by: ''
---

# T011 — Plan: gRPC API for Lower-Latency Client-Deck Communication

## Reconnaissance Summary

**Current HTTP/REST API:**
- FastAPI service on port 8082
- Endpoints: `/health`, `/version`, `/telemetry`, `/decide`, `/confirm/*`, `/command`
- Client: `DeckClient` using `requests` library
- Latency: ~20ms p99 over LAN (HTTP/1.1 + JSON)

**Existing data models:**
- `TelemetryState` → `/telemetry` response
- `DecideRequest/Response` (dual mode: maze + telemetry)
- `CommandRequest/Response`, `ConfirmIssueResponse`, `VerifyResponse`
- Safety token mechanism (X-Confirmation-Token header)

**Dependencies available:**
- Python 3.11+, FastAPI, uvicorn
- `grpcio`, `grpcio-tools`, `protobuf` not yet in deps

## Hostile Analysis

### ASSUMPTIONS I AM MAKING:
- [KNOWN] gRPC with HTTP/2 provides lower latency (binary, multiplexed, header compression)
- [KNOWN] FastAPI doesn't natively support gRPC; need separate gRPC server or `grpc-aio`
- [INFERRED] Can run gRPC on separate port (e.g., 8083) alongside HTTP/8082
- [ASSUMED] Protobuf schema mirrors existing REST models (Telemetry, Decision, Command, Token)
- [ASSUMED] Server-side streaming for telemetry: `GetTelemetryStream` returns stream of updates
- [UNKNOWN] Whether to use `grpc-aio` (async) or sync gRPC with thread pool
- [UNKNOWN] TLS cert management for mTLS (self-signed for dev, proper CA for prod)
- [UNKNOWN] Backward compatibility: HTTP client must continue working

### WHAT WAS NOT SPECIFIED (that matters):
- Port allocation: gRPC on 8083? Or same port with ALPN?
- Connection pooling / keepalive settings
- Streaming frequency for telemetry (push vs pull interval)
- Error mapping: gRPC status codes vs HTTP status codes
- Authentication: token in metadata vs header

### ALTERNATIVES NOT CHOSEN:
| Option | Reason |
|--------|--------|
| gRPC-Gateway (REST proxy) | Adds complexity; dual server simpler |
| HTTP/3 (QUIC) | Limited Python ecosystem support |
| WebSocket for streaming | gRPC streaming is native and typed |
| Cap'n Proto / FlatBuffers | Protobuf standard, gRPC native |

### RISKS AND SIDE EFFECTS:
1. **Port conflicts** - need separate port or ALPN negotiation
2. **Protobuf version drift** - schema changes require coordinated client/server deploy
3. **Streaming backpressure** - telemetry at 50Hz may overwhelm slow clients
3. **TLS complexity** - cert generation, rotation, mTLS verification
4. **Client migration** - existing HTTP clients must not break

### COST OF BEING WRONG: MEDIUM
- gRPC optional alongside HTTP; HTTP remains primary
- If gRPC fails, fallback to HTTP works
- Main risk: wasted effort if latency gain negligible

### SCOPE BOUNDARY:
**In**: Protobuf schema, gRPC service (unary + streaming), dual-transport client, TLS config, benchmarks
**Out**: gRPC-Gateway, HTTP/3, WebSocket, authentication framework (use existing token)

### INVITATION FOR CONTRADICTION:
What if HTTP/2 + JSON is fast enough? → Benchmarks will tell. If <2x improvement, may not justify complexity.

## Technical Approach

### 1. Protobuf Schema: `proto/flybrain.proto`
```protobuf
syntax = "proto3";
package flybrain;

service FlyBrainService {
  rpc GetHealth(HealthRequest) returns (HealthResponse);
  rpc GetVersion(VersionRequest) returns (VersionResponse);
  rpc GetTelemetry(TelemetryRequest) returns (TelemetryResponse);
  rpc GetTelemetryStream(TelemetryStreamRequest) returns (stream TelemetryResponse);
  rpc Decide(DecideRequest) returns (DecideResponse);
  rpc IssueToken(TokenRequest) returns (TokenResponse);
  rpc VerifyToken(VerifyRequest) returns (VerifyResponse);
  rpc SendCommand(CommandRequest) returns (CommandResponse);
}

// Messages mirror REST models
message TelemetryResponse {
  double timestamp = 1;
  bool link_ok = 2;
  Position position = 3;
  Attitude attitude = 4;
  Velocity velocity = 5;
  Battery battery = 6;
  repeated float rc_channels = 7;
  map<string, int32> message_counts = 8;
  string source = 9;  // "mavlink" | "crsf"
}

message DecideRequest {
  bool use_telemetry = 1;
  double target_lat = 2;
  double target_lon = 3;
  double target_alt = 4;
  double target_speed = 5;
  // Legacy maze fields
  repeated int32 position = 10;
  repeated repeated int32 grid = 11;
  repeated int32 exit = 12;
}

message DecideResponse {
  Advisory advisory = 1;
  SafetyStatus safety = 2;
  // Legacy
  string action = 10;
  double confidence = 11;
  repeated float logits = 12;
}

// ... other messages
```

### 2. gRPC Server Implementation
- **Option A**: Separate gRPC server on port 8083 (simpler, no ALPN complexity)
- **Option B**: Same port with ALPN (complex, requires h2 support)

**Choice**: Option A - separate port, simpler deployment, clear separation

- Use `grpc.aio` for async server
- Run alongside FastAPI in same process (shared state via modules)
- Implement `FlyBrainServiceServicer` class

### 3. Streaming Telemetry
- `GetTelemetryStream`: Server-side streaming
- Push updates at configurable rate (default 10Hz, max 50Hz)
- Client controls rate via `TelemetryStreamRequest.interval_ms`
- Backpressure: respect gRPC flow control

### 4. Dual-Transport Client
- Extend `DeckClient` with `transport: "http" | "grpc"` parameter
- gRPC client uses generated stub, shares same method signatures
- Auto-fallback: try gRPC first, fall back to HTTP on failure
- Connection pooling: reuse gRPC channel

### 5. TLS/mTLS
- Dev mode: self-signed cert, `grpc.ssl_channel_credentials`
- Prod mode: load CA cert, client cert/key from env vars
- mTLS: verify client cert on server side

### 6. Benchmarks
- Script: `scripts/benchmark_grpc.py`
- Measure: latency (p50, p95, p99), throughput, CPU
- Compare: HTTP/JSON vs gRPC unary vs gRPC streaming

## Affected Files

| File | Operation | Description |
|------|-----------|-------------|
| `proto/flybrain.proto` | create | Protobuf schema |
| `src/dfb/grpc_service.py` | create | gRPC servicer implementation |
| `src/dfb/grpc_server.py` | create | gRPC server startup (port 8083) |
| `src/dfb/client.py` | modify | Add `GrpcDeckClient`, dual transport |
| `src/dfb/cli.py` | modify | `--transport` flag, gRPC benchmarks |
| `src/dfb/service.py` | modify | Shared state access for gRPC servicer |
| `pyproject.toml` | modify | Add `grpcio`, `grpcio-tools`, `protobuf` deps |
| `deploy/flybrain.service` | modify | Add gRPC port, TLS env vars |
| `scripts/benchmark_grpc.py` | create | Latency/throughput comparison |
| `tests/test_grpc.py` | create | Contract tests, streaming tests |

## Specification

### Protobuf Services
```protobuf
service FlyBrainService {
  rpc GetHealth(HealthRequest) returns (HealthResponse);
  rpc GetVersion(VersionRequest) returns (VersionResponse);
  rpc GetTelemetry(TelemetryRequest) returns (TelemetryResponse);
  rpc GetTelemetryStream(TelemetryStreamRequest) returns (stream TelemetryResponse);
  rpc Decide(DecideRequest) returns (DecideResponse);
  rpc IssueToken(TokenRequest) returns (TokenResponse);
  rpc VerifyToken(VerifyRequest) returns (VerifyResponse);
  rpc SendCommand(CommandRequest) returns (CommandResponse);
}
```

### Generated Python
```bash
python -m grpc_tools.protoc \
  --proto_path=proto \
  --python_out=src/dfb/grpc \
  --grpc_python_out=src/dfb/grpc \
  proto/flybrain.proto
```

### gRPC Server Integration
```python
# In lifespan or separate task
grpc_server = grpc.aio.server()
flybrain_pb2_grpc.add_FlyBrainServiceServicer_to_server(FlyBrainServicer(), grpc_server)
grpc_server.add_insecure_port('[::]:8083')
await grpc_server.start()
```

### Client Transport Abstraction
```python
class DeckClient:
    def __init__(self, transport="http", ...):
        if transport == "grpc":
            self._grpc = GrpcDeckClient(...)
        else:
            self._http = HttpDeckClient(...)
```

## Testing Strategy

**Unit tests:**
- `test_protobuf_serialization` - round-trip all message types
- `test_grpc_unary_calls` - all RPCs return expected responses
- `test_grpc_streaming` - telemetry stream yields updates
- `test_grpc_tls` - mTLS handshake succeeds
- `test_client_transport_fallback` - HTTP fallback on gRPC failure

**Integration tests:**
- `test_grpc_vs_http_latency` - benchmark comparison
- `test_concurrent_streams` - multiple streaming clients
- `test_backpressure` - slow consumer doesn't block server

**Contract tests:**
- Golden protobuf files for schema compatibility

## Verification Criteria

- [ ] `make check` passes (all tests, lint, coverage ≥80% for new code)
- [ ] gRPC server starts on port 8083 alongside HTTP/8082
- [ ] All 7 RPCs work: Health, Version, Telemetry, Decide, IssueToken, VerifyToken, Command
- [ ] Streaming telemetry delivers updates at requested interval
- [ ] gRPC client works with both insecure and TLS channels
- [ ] Dual-transport client falls back to HTTP on gRPC failure
- [ ] Benchmark: gRPC p99 latency <5ms vs HTTP ~20ms
- [ ] No regressions in HTTP API

## Estimation

- Complexity: **medium-high** (4–12h)
- Risk: **medium** (protobuf schema evolution, streaming backpressure, TLS)
- Blocking dependencies: **no** (T004 complete, new deps only)