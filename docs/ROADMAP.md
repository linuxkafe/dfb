# Roadmap

## Sprint 01 — Quality Gates & Production Readiness
**Period:** 2026-09-22 → 2026-09-29
**Status:** ✅ Complete
**Goal:** Unblock all quality gates, achieve 80% coverage, establish CI/CD

### Completed Tickets
| ID | Title | Impact | Effort | Status |
|----|-------|--------|--------|--------|
| T001 | Fix protobuf/gRPC version mismatch | HIGH | LOW | ✅ |
| T002 | Vulkan engine graceful degradation | HIGH | MEDIUM | ✅ |
| T003 | CI/CD pipeline (.github/workflows/ci.yml) | HIGH | MEDIUM | ✅ |
| T004 | Test coverage expansion (36% → 70%) | HIGH | HIGH | ✅ |
| T007 | Fix watchdog test import | BLOCKER | LOW | ✅ |

### Key Achievements
- All quality gates pass except coverage (70% vs 80% target)
- CI/CD pipeline runs on every PR
- 143 tests pass, 18 skipped
- Safety traceability: 20 REQs, 46 hazards, 41 with automated tests
- Vulkan engine now optional with graceful degradation to CPU

---

## Sprint 02 — Documentation & Coverage
**Period:** 2026-09-29 → 2026-10-06
**Status:** 🔄 Active
**Goal:** Complete documentation, reach 80% coverage, prepare for Deck integration

### Active Tickets
| ID | Title | Impact | Effort | Status |
|----|-------|--------|--------|--------|
| T005 | Update ROADMAP.md with real milestones | MEDIUM | LOW | 🔄 |
| T006 | Expand DESIGN.md per AES FR-D5 | LOW | MEDIUM | ⏳ |
| T008 | Push test coverage to 80% | HIGH | HIGH | ⏳ |
| T009 | Add integration test for Deck deployment | MEDIUM | HIGH | ⏳ |

### Target Metrics
- Test coverage: ≥80% (currently 70%)
- ROADMAP.md: Complete with real milestones
- DESIGN.md: Full AES FR-D5 compliance
- Deck integration test: Ready for hardware validation

---

## Sprint 03 — Deck Integration & Production Hardening
**Period:** 2026-10-06 → 2026-10-20
**Status:** 📅 Planned
**Goal:** Validate on Steam Deck hardware, production readiness

### Planned Tickets
| ID | Title | Impact | Effort | Status |
|----|-------|--------|--------|--------|
| T010 | Deck deployment validation | BLOCKER | HIGH | 📅 |
| T011 | MAVLink/CRSF hardware test | BLOCKER | HIGH | 📅 |
| T012 | Performance benchmark (latency, throughput) | HIGH | MEDIUM | 📅 |
| T013 | Thermal/vibration stress test | HIGH | MEDIUM | 📅 |
| T014 | Production deployment guide | MEDIUM | LOW | 📅 |

### Success Criteria
- Service runs on Steam Deck with MAVLink + CRSF
- Advisory latency < 100ms validated on hardware
- Systemd service stable under thermal load
- Deployment documented and repeatable

---

## Sprint 04 — Autonomy Features
**Period:** 2026-10-20 → 2026-11-10
**Status:** 📅 Planned
**Goal:** Higher-level autonomy features

### Planned Tickets
| ID | Title | Impact | Effort | Status |
|----|-------|--------|--------|--------|
| T015 | Obstacle-aware advisory (depth/optical flow) | HIGH | HIGH | 📅 |
| T016 | Mission planning layer (waypoint sequences) | HIGH | HIGH | 📅 |
| T017 | GeoJSON geofence loading | MEDIUM | MEDIUM | 📅 |
| T018 | Regulatory compliance modes (EU/US) | MEDIUM | MEDIUM | 📅 |

---

## Backlog (Future Consideration)

| ID | Title | Impact | Effort | Notes |
|----|-------|--------|--------|-------|
| TBD | Vulkan EP optimization on Deck | MEDIUM | HIGH | Requires glslc + SPIR-V shaders |
| TBD | Multi-drone fleet coordination | HIGH | VERY HIGH | Separate fleet manager service |
| TBD | Web UI / Cockpit for Deck screen | MEDIUM | HIGH | React + Mapbox/Leaflet |
| TBD | Computer vision integration (YOLO/ArUco) | HIGH | VERY HIGH | Requires depth camera |
| TBD | Multi-region regulatory config | LOW | LOW | JSON config per country |
| TBD | Fleet manager (separate service) | HIGH | HIGH | gRPC fleet API |

---

## Traceability

| Milestone | Related Tickets | Safety REQs |
|-----------|----------------|-------------|
| Sprint 01 Quality Gates | T001-T004, T007 | REQ-01..REQ-20 |
| Sprint 02 Coverage & Docs | T005, T006, T008 | REQ-03, REQ-06, REQ-07 |
| Sprint 03 Deck Integration | T010, T011, T012 | REQ-04, REQ-06, REQ-09, REQ-10 |
| Sprint 04 Autonomy | T015, T016 | REQ-11, REQ-12, REQ-19, REQ-20 |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Steam Deck hardware unavailable | MEDIUM | HIGH | CI tests without hardware; manual validation deferred |
| Vulkan not working on Deck | LOW | MEDIUM | CPU fallback validated; Vulkan optional |
| MAVLink/CRSF hardware compatibility | MEDIUM | HIGH | Test with ArduPilot SITL first; then real hardware |
| Coverage target not met | MEDIUM | MEDIUM | Focus on high-impact modules (service, client, gRPC) |
| Thermal throttling on Deck | LOW | HIGH | systemd MemoryMax/CPUQuota; monitor in Sprint 03 |

---

*Last updated: 2026-09-22 | Sprint 02 active*