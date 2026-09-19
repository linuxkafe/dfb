---
ticket: T010
phase: plan
status: done
created: 2026-09-19
tier: standard
requires:
  - aes/kanban.md
  - aes/tickets/T010-crsf-elrs.md
produces:
  - aes/tickets/T010-plan.md
blocked_by: ''
---

# T010 — Plan: CRSF/ELRS Support for Crossfire Receivers

## Reconnaissance Summary

**Existing telemetry infrastructure:**
- `src/dfb/mavlink_ingest.py`: MAVLink ingestion with `MavlinkReader` class, background task, `TelemetryState` dataclass
- `src/dfb/state_estimator.py`: Converts MAVLink `TelemetryState` (NED) to `EstimatedState` (ENU)
- `src/dfb/service.py`: `/telemetry` endpoint returns MAVLink data; lifespan manages MAVLink task
- `src/dfb/health.py`: Component health checking for MAVLink link
- Serial transport via `pymavlink.mavutil.mavlink_connection` (already in deps)

**Current TelemetryState fields:** position, attitude, velocity, battery, RC channels, flight_mode, armed, msg_counts

**New requirements for CRSF/ELRS:**
- CRSF frame format: 0xC8 header, variable length, CRC8
- Channels: 16 channels × 11 bits = 22 bytes packed
- Link statistics: RSSI, LQ, SNR, RF mode (ELRS-specific)
- Battery: voltage, current, capacity
- GPS: lat, lon, alt, speed, satellites
- Need unified API with source tagging (MAVLink vs CRSF)

## Hostile Analysis

### ASSUMPTIONS I AM MAKING:
- [KNOWN] CRSF protocol documented (OpenTX/EdgeTX, crsf-py reference)
- [KNOWN] pyserial already in deps for MAVLink serial
- [INFERRED] CRSF uses 420000 baud (standard) vs MAVLink 57600/115200
- [INFERRED] Single serial port - need autodetection or separate UART
- [ASSUMED] CRSF telemetry is one-way (RX only) for now; TX commands out of scope
- [ASSUMED] ELRS telemetry embedded in CRSF frames (type 0x10-0x1F)
- [UNKNOWN] Whether Steam Deck has second UART or need USB-CRSF adapter
- [UNKNOWN] Frame timing - CRSF ~150Hz vs MAVLink ~50-100Hz

### WHAT WAS NOT SPECIFIED (that matters):
- Serial port for CRSF (separate from MAVLink?)
- Autodetection logic: how to distinguish MAVLink vs CRSF frames
- Failover behavior details - which source takes priority?
- Data fusion: how to combine MAVLink + CRSF in EstimatedState
- CRC8 implementation - use crsf-py or custom?

### ALTERNATIVES NOT CHOSEN:
| Option | Reason |
|--------|--------|
| crsf-py library | Adds dependency; protocol simple enough for custom parser |
| Separate CRSF service | Overhead; integrate into existing telemetry pipeline |
| TX command support | Out of scope per ticket (safety: FC remains authority) |

### RISKS AND SIDE EFFECTS:
1. **Serial conflict** - if same UART used for MAVLink and CRSF, need multiplexing
2. **Frame misidentification** - autodetection could misclassify frames
3. **CPU overhead** - parsing two protocols simultaneously
4. **Data inconsistency** - conflicting RC channels from MAVLink vs CRSF

### COST OF BEING WRONG: MEDIUM
- CRSF parsing bugs → wrong RC channels → safety decisions based on bad data
- But FC still has own RC input; our advisory only supplements
- Failover to MAVLink if CRSF parsing fails

### SCOPE BOUNDARY:
**In**: CRSF frame parser, ELRS telemetry extraction, unified `/telemetry` with source tags, serial autodetection
**Out**: CRSF TX (commands), frequency hopping, CRSF binding/management, ELRS Lua scripts

### INVITATION FOR CONTRADICTION:
What if CRSF and MAVLink share same serial port? → Need hardware clarification. For now, assume separate UART or USB adapter.

## Technical Approach

### 1. New Module: `src/dfb/crsf_ingest.py`
- `CRSFFrame` dataclass: header, length, type, payload, crc
- `CRSFParser` class: incremental frame parser, CRC8 validation
- `CRSFTelemetry` dataclass: channels[16], link_stats, battery, gps, elrs_info
- `CRSFReader` class: serial connection + background task (mirroring MavlinkReader)

### 2. Extended TelemetryState
Add optional CRSF fields to `TelemetryState` (or create `UnifiedTelemetryState`):
```python
@dataclass
class UnifiedTelemetryState:
    # MAVLink fields (existing)
    mavlink: Optional[TelemetryState] = None
    # CRSF fields (new)
    crsf: Optional[CRSFTelemetry] = None
    # Source priority
    primary_source: Literal["mavlink", "crsf", "none"] = "none"
```

### 3. Serial Autodetection
- Read first bytes: MAVLink starts with 0xFE (v1) or 0xFD (v2/signing); CRSF starts with 0xC8
- Try CRSF parser first (0xC8), fallback to MAVLink
- Configurable via `TELEMETRY_PROTOCOL=auto|mavlink|crsf`

### 4. Unified `/telemetry` Endpoint
Returns both sources with metadata:
```json
{
  "mavlink": {...},
  "crsf": {...},
  "primary": "mavlink",
  "fused": {...}  // best available data for advisor
}
```

### 5. Failover Logic
- If MAVLink `link_ok=false` and CRSF `link_ok=true` → use CRSF for RC channels, link quality
- Advisor reads from `UnifiedTelemetryState.fused` (merged view)

### 6. Health & Metrics
- Extend `check_mavlink_link` → `check_telemetry_links` (both sources)
- Add CRSF metrics: frames_total, crc_errors, link_rssi, link_lq

## Affected Files

| File | Operation | Description |
|------|-----------|-------------|
| `src/dfb/crsf_ingest.py` | create | CRSF frame parser, ELRS telemetry, background reader |
| `src/dfb/mavlink_ingest.py` | modify | Export parser for autodetection; maybe share base class |
| `src/dfb/service.py` | modify | Dual-protocol lifespan, unified telemetry endpoint |
| `src/dfb/state_estimator.py` | modify | Accept unified telemetry, fuse sources |
| `src/dfb/health.py` | modify | Check both MAVLink and CRSF links |
| `src/dfb/metrics.py` | modify | Add CRSF metrics |
| `src/dfb/__init__.py` | modify | Export CRSF public API |
| `deploy/flybrain.service` | modify | Add CRSF_* env vars |
| `src/dfb/client.py` | modify | Update TelemetryDecideResponse for dual source |
| `src/dfb/cli.py` | modify | Add CRSF telemetry CLI options |
| `tests/test_crsf.py` | create | Unit tests with captured frames |
| `pyproject.toml` | modify | Add crsf-py optional dep (for reference) |

## Specification

### CRSF Frame Format
```
Header: 0xC8
Length: payload length (1 byte)
Type: frame type (1 byte)
Payload: variable
CRC: CRC8 (1 byte, covers type+payload)
```

### Key Frame Types
- 0x10: RC Channels (16×11bit packed)
- 0x14: Link Statistics (RSSI, LQ, SNR)
- 0x15: RX Link Statistics
- 0x16: TX Link Statistics
- 0x17: ELRS-specific (RF mode, etc.)
- 0x08: Battery (voltage, current, capacity)
- 0x09: GPS (lat, lon, alt, speed, sats)

### Data Structures
```python
@dataclass
class CRSFTelemetry:
    timestamp: float
    link_ok: bool
    channels: list[float]  # 16 channels, normalized -1..1
    rssi: Optional[float] = None
    lq: Optional[float] = None
    snr: Optional[float] = None
    rf_mode: Optional[int] = None
    voltage: Optional[float] = None
    current: Optional[float] = None
    capacity: Optional[float] = None
    gps: Optional[dict] = None  # lat, lon, alt, speed, sats
```

## Testing Strategy

**Unit tests** (`tests/test_crsf.py`):
- `test_crsf_frame_parsing` - valid frames, CRC validation
- `test_rc_channels_decode` - 11-bit packing/unpacking
- `test_link_stats_parse` - RSSI, LQ, SNR extraction
- `test_elrs_telemetry_parse` - RF mode, etc.
- `test_crc8_validation` - valid/invalid CRC
- `test_incremental_parser` - split frames across reads
- `test_autodetection` - MAVLink vs CRSF frame identification

**Integration tests**:
- `test_dual_protocol_lifespan` - both readers start/stop
- `test_unified_telemetry_endpoint` - `/telemetry` returns both
- `test_failover_logic` - MAVLink lost, CRSF takes over

## Verification Criteria

- [ ] `make check` passes (all tests, lint, coverage ≥80% for new code)
- [ ] CRSF parser decodes RC channels from real captured frames
- [ ] ELRS telemetry (RSSI, LQ, SNR) extracted correctly
- [ ] `/telemetry` returns both MAVLink and CRSF with source tags
- [ ] Autodetection distinguishes MAVLink vs CRSF frames
- [ ] Failover: when MAVLink link lost, CRSF data used for advisory
- [ ] Health checks report both links independently
- [ ] Metrics include CRSF frame counts, CRC errors, link quality
- [ ] No regressions in existing MAVLink functionality

## Estimation

- Complexity: **medium** (2–8h)
- Risk: **medium** (protocol parsing, serial autodetection, data fusion)
- Blocking dependencies: **no** (T007 complete, pyserial in deps)