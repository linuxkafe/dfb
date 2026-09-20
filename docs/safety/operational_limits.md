# Operational Limits

## Overview
This document defines the operational envelope for the Deck Fly Brain (DFB) system. All advisory decisions and safety checks are constrained by these limits. Parameters are configurable via environment variables or configuration files.

## Geofence

### Default Configuration
| Parameter | Default Value | Unit | Description |
|-----------|---------------|------|-------------|
| `GEOFENCE_ENABLED` | `false` | - | Enable/disable geofence |
| `GEOFENCE_MIN_LAT` | `-90.0` | degrees | Minimum latitude |
| `GEOFENCE_MAX_LAT` | `90.0` | degrees | Maximum latitude |
| `GEOFENCE_MIN_LON` | `-180.0` | degrees | Minimum longitude |
| `GEOFENCE_MAX_LON` | `180.0` | degrees | Maximum longitude |

### Configuration
Geofence can be configured via environment variables or configuration file:
```bash
export GEOFENCE_ENABLED=true
export GEOFENCE_MIN_LAT=47.0
export GEOFENCE_MAX_LAT=48.0
export GEOFENCE_MIN_LON=8.0
export GEOFENCE_MAX_LON=9.0
```

### Violation Response
- **Severity**: CRITICAL
- **Action**: Advisory mode = RTL (Return to Launch)
- **Recovery**: Manual pilot intervention required

---

## Altitude Limits

| Parameter | Default | Unit | Description |
|-----------|---------|------|-------------|
| `ALTITUDE_MIN` | 5.0 | meters AGL | Minimum altitude AGL |
| `ALTITUDE_MAX` | 120.0 | meters AGL | Maximum altitude AGL |

### Violation Response
- **Below minimum**: CRITICAL → Advisory = RTL
- **Above maximum**: CRITICAL → Advisory = RTL + descent command

---

## Battery Reserve

| Parameter | Default | Unit | Description |
|-----------|---------|------|-------------|
| `BATTERY_RESERVE_PCT` | 20.0 | % | Minimum battery reserve |
| `BATTERY_CRITICAL_PCT` | 10.0 | % | Critical battery level |

### Violation Response
- **Below reserve (20%)**: CRITICAL → Advisory mode = RTL
- **Critical (10%)**: CRITICAL → Immediate RTL + land

---

## Link Quality

### MAVLink
| Parameter | Default | Unit | Description |
|-----------|---------|------|-------------|
| `MAVLINK_MAX_AGE` | 2.0 | seconds | Max age of MAVLink message |
| `MAVLINK_MIN_RATE` | 1.0 | Hz | Minimum message rate |

### CRSF/ELRS
| Parameter | Default | Unit | Description |
|-----------|---------|------|-------------|
| `CRSF_MAX_AGE` | 5.0 | seconds | Max age of CRSF frame |
| `CRSF_MIN_LQ` | 50 | % | Minimum link quality |

### Violation Response
- **Link lost > max age**: CRITICAL → Advisory = RTL
- **Link quality < threshold**: WARNING → Reduced performance

---

## GPS Quality

| Parameter | Default | Description |
|-----------|---------|-------------|
| `GPS_MIN_FIX_TYPE` | 3 (3D fix) | Minimum GPS fix type |
| `GPS_MAX_HDOP` | 2.0 | Max horizontal dilution of precision |
| `GPS_MAX_VDOP` | 2.0 | Max vertical dilution of precision |

### Violation Response
- **Fix type < 3**: CRITICAL → Advisory = RTL
- **HDOP/VDOP > threshold**: WARNING → Reduced confidence

---

## Speed & Attitude Limits

| Parameter | Default | Unit | Severity |
|-----------|---------|------|----------|
| `MAX_GROUND_SPEED` | 25.0 | m/s | WARNING |
| `MAX_CLIMB_RATE` | 5.0 | m/s | WARNING |
| `MAX_SINK_RATE` | 3.0 | m/s | WARNING |
| `MAX_ROLL` | 40.0 | degrees | WARNING |
| `MAX_PITCH` | 40.0 | degrees | WARNING |

---

## Weather Limits

| Condition | Limit | Advisory |
|-----------|-------|----------|
| Wind speed | < 15 m/s | Reduced performance |
| Visibility | > 3 km | VFR only |
| Precipitation | None | No flight |

---

## Configuration Priority

1. Environment variables (highest)
2. Configuration file (`config/operational_limits.yaml`)
3. Default values (lowest)

## Runtime Modification

Limits can be adjusted at runtime via gRPC/HTTP API:
- `POST /config/limits` - Update limits
- `GET /config/limits` - Query current limits

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-09-20 | Initial version |

---

*Document version: 0.1.0 | Part of T012 Safety Certification*