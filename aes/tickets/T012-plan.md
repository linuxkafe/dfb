---
ticket: T012
phase: plan
status: done
created: 2026-09-20
tier: heavy
requires:
  - aes/kanban.md
  - aes/tickets/T012-safety-certification.md
produces:
  - aes/tickets/T012-plan.md
blocked_by: ''
---

# T012 — Plan: Safety Certification Artifacts

## Reconnaissance Summary

**System context:**
- Fly Brain = advisory-only companion computer on Steam Deck
- FC (Flight Controller) remains ultimate authority (ArduPilot/INAV/PX4)
- Safety gate: token confirmation for any command toward aircraft
- MAVLink telemetry ingestion + CRSF/ELRS (T010) → state estimation → advisor
- Safety envelope: geofence, altitude, battery, link, GPS, speed, attitude
- Watchdog monitors MAVLink/CRSF links and decision engine
- Resource limits: MemoryMax=2G, CPUQuota=200%
- Graceful degradation: service stays up on link loss

**Existing safety mechanisms:**
- Token confirmation gate (single-use, 30s TTL) for `/command`
- Safety envelope in `check_safety()` - CRITICAL violations block advisory
- Mode awareness: no advisory in MANUAL/ACRO; RTL/LAND not interfered
- Watchdog: MAVLink link monitoring, decision engine responsiveness
- Resource limits: MemoryMax=2G, CPUQuota=200%
- Graceful degradation: service stays up on link loss

**Test evidence:**
- Unit tests for safety envelope (geofence, altitude, battery, link, GPS, speed, attitude)
- Unit tests for advisor mode logic (manual→advisory, auto-safety→no-interfere)
- Integration tests for MAVLink ingestion, health endpoints
- Chaos tests for link loss, OOM (planned)

## Hostile Analysis

### ASSUMPTIONS I AM MAKING:
- [KNOWN] System is advisory-only; FC has final authority (REQ-19)
- [KNOWN] Safety envelope implemented with CRITICAL/WARNING classification
- [KNOWN] Token confirmation gate prevents unauthorized commands
- [INFERRED] ARP4761/ISO 26262 lite appropriate for experimental UAS
- [INFERRED] Hazard severity: Catastrophic (loss of aircraft/life), Hazardous (serious injury), Major (minor injury/damage), Minor (nuisance), No Effect
- [ASSUMED] Experimental use only - not commercial passenger carrying
- [ASSUMED] Pilot always in loop (manual override possible)
- [UNKNOWN] Regulatory environment (country-specific UAS rules)
- [UNKNOWN] Whether insurance/waiver requires specific artifacts

### WHAT WAS NOT SPECIFIED (that matters):
- Exact GSN/CAE notation standard for safety case
- Traceability matrix format (DOORS-style table? Markdown? Excel?)
- Whether to include software tool qualification (unlikely for experimental)
- Whether to address common cause failures (e.g., Steam Deck hardware failure)
- Review process: who signs off? (self-assessment vs external)

### ALTERNATIVES NOT CHOSEN:
| Option | Reason |
|--------|--------|
| Full DO-178C/DO-254 | Overkill for experimental advisory system |
| MIL-STD-882E full | Too heavy; use lite version |
| STPA (Systems Theoretic Process Analysis) | Good but team more familiar with FHA/FTA |
| No formal artifacts | Unacceptable for any system touching aircraft |

### RISKS AND SIDE EFFECTS:
1. **Documentation drift** - artifacts must be updated with code changes
2. **False confidence** - artifacts ≠ safety; must reflect reality
3. **Scope creep** - certification scope expands beyond experimental
4. **Maintenance burden** - keeping artifacts current with rapid iteration

### COST OF BEING WRONG: HIGH
- Safety artifacts used to justify flight operations
- If hazards missed → actual flight risk
- If artifacts not maintained → false confidence

### SCOPE BOUNDARY:
**In**: SSA, FHA, FTA, traceability matrix, safety case (GSN), operational limits, emergency procedures
**Out**: DO-178C code certification, flight test reports, production certification, tool qualification

### INVITATION FOR CONTRADICTION:
What if the advisor becomes authoritative (not just advisory)? → Would need DO-178C. Current design explicitly prevents this.

## Technical Approach

### 1. System Safety Assessment (SSA) — `docs/safety/ssa.md`
- System description: functions, interfaces, boundaries
- Operating environment: Steam Deck, LAN, FC, RF link
- Safety requirements derived from hazards
- Safety architecture: advisory-only, FC authority, safety gate

### 2. Functional Hazard Analysis (FHA) — `docs/safety/fha.md`
| Function | Failure Condition | Phase | Severity | Mitigation |
|----------|------------------|-------|----------|------------|
| Advisory generation | Wrong heading/alt/speed | Flight | Hazardous | Safety envelope, FC authority |
| Advisory generation | No advisory when needed | Flight | Major | Watchdog, FC fallback |
| Command execution | Unauthorized command | All | Catastrophic | Token gate, FC authority |
| Telemetry ingestion | Stale/wrong state | Flight | Hazardous | Link monitoring, safety envelope |
| Mode awareness | Advisory in MANUAL | Flight | Major | Mode check, advisory-only |

### 3. Fault Tree Analysis (FTA) — `docs/safety/fta.md`
**Top events:**
- TE1: Unintended command sent to FC
- TE2: Loss of telemetry link undetected
- TE3: Wrong advisory accepted by pilot/FC
- TE4: Safety envelope bypassed

**Example TE1 analysis:**
```
TE1: Unintended command sent to FC
  ├── Token gate bypassed
  │   ├── Token prediction (low probability)
  │   └── Token replay (mitigated: single-use, 30s TTL)
  ├── FC accepts command without verification
  │   └── FC bug (outside our scope)
  └── MAVLink injection vulnerability
      └── Serial port compromise (physical access required)
```

### 4. Traceability Matrix — `docs/safety/traceability.md`
| Req ID | Requirement | Hazard(s) | Test(s) | Status |
|--------|-------------|-----------|---------|--------|
| REQ-19 | FC firmware never modified | All | Code review | Pass |
| REQ-11 | Advisory decisions safe | H1, H2 | test_advisor.py | Pass |
| REQ-17 | SSH keys only | H3 | deploy test | Pass |
| REQ-20 | Service auto-restart | H2, H4 | test_health.py | Pass |

### 5. Safety Case (GSN) — `docs/safety/case.md` (or Markdown)
```
Goal: Residual risk acceptable for experimental flight
  Strategy: Defense in depth
    Sub-goal 1: FC remains authority
      Evidence: REQ-19, architecture diagram
    Sub-goal 2: Advisory constrained by safety envelope
      Evidence: FHA mitigations, test_advisor.py
    Sub-goal 3: Commands require explicit confirmation
      Evidence: Token gate, test_client.py
    Sub-goal 4: Link loss detected and handled
      Evidence: Watchdog, test_health.py
    Sub-goal 5: System fails safe
      Evidence: Graceful degradation, no command on link loss
```

### 6. Operational Limits — `docs/safety/operational_limits.md`
- Geofence: configurable lat/lon box (default: unrestricted)
- Altitude: 5-120m AGL (configurable)
- Battery reserve: 20% (configurable)
- Link: MAVLink/CRSF max age 2s/5s
- Weather: VFR only, wind <15m/s (advisory)
- Link budget: RF margin >10dB (ELRS)
- Pilot: current license, currency, simulator proficiency

### 7. Emergency Procedures — `docs/safety/emergency.md`
1. **Link loss**: Pilot takes manual → RTL if configured
2. **Wrong advisory**: Pilot ignores → manual override
3. **Battery critical**: Auto-RTL at 20%, land at 10%
4. **Geofence breach**: Advisory RTL → pilot manual
5. **Kill switch**: FC hardware disarm (external)
5. **Steam Deck failure**: FC failsafe (RTL/land)

## Affected Files

| File | Operation | Description |
|------|-----------|-------------|
| `docs/safety/ssa.md` | create | System Safety Assessment |
| `docs/safety/fha.md` | create | Functional Hazard Analysis |
| `docs/safety/fta.md` | create | Fault Tree Analysis |
| `docs/safety/traceability.md` | create | Requirements→Hazards→Tests matrix |
| `docs/safety/case.md` | create | Safety Case (GSN-style) |
| `docs/safety/operational_limits.md` | create | Operational envelope |
| `docs/safety/emergency.md` | create | Emergency procedures |
| `docs/safety/README.md` | create | Index and maintenance guide |

## Testing Strategy

**Document review:**
- Peer review of each artifact (SSA, FHA, FTA, Safety Case)
- Traceability matrix completeness check
- Consistency check: hazards ↔ mitigations ↔ tests

**Automated checks:**
- `make safety-check` - validates traceability matrix completeness
- CI gate: all hazard mitigations have at least one test
- CI gate: safety case goals all have evidence

## Verification Criteria

- [ ] SSA documents system, environment, safety requirements
- [ ] FHA identifies ≥10 failure conditions with severity classification
- [ ] FTA analyzes ≥4 top events with minimal cut sets
- [ ] Traceability matrix covers all REQs → Hazards → Tests
- [ ] Safety Case (GSN) argues residual risk acceptable
- [ ] Operational Limits documented with configurable parameters
- [ ] Emergency Procedures cover 6 scenarios
- [ ] All artifacts reviewed and approved
- [ ] CI gate: `make safety-check` passes

## Estimation

- Complexity: **medium** (4–10h)
- Risk: **medium** (documentation quality, traceability maintenance)
- Blocking dependencies: **T007, T008, T009** (system must be functional to analyze)

## Two-Agent Analysis (Heavy Ticket)

### Critic Phase

## Como se fosse uma criança
The safety documents are like a rulebook that says "here's what could go wrong and how we prevent it." But rulebooks can be wrong, outdated, or ignored. Just because we write down "we check the battery" doesn't mean the code actually checks it before every flight.

## Como se fosse um especialista
This is a lightweight safety case for an experimental advisory system. Key challenge: the artifacts must accurately reflect the implemented system, not an idealized version. The traceability matrix is the linchpin - if it rots, the whole case rots.

[FAILURE MODE 1]
Mechanism: Documentation drift - artifacts describe v0.1 but code is at v0.5 with different safety envelope defaults.

[FAILURE MODE 2]
Mechanism: False confidence - artifacts claim "safety envelope prevents all hazardous advisories" but code only checks geofence/altitude, not attitude limits.

[FAILURE MODE 3]
Mechanism: Traceability gaps - new hazard added in code review but not traced to FHA/FTA/test, creating silent gap.

[ASSUMPTION]
If false: Artifacts become decorative rather than functional safety evidence.

[ALTERNATIVE FRAMING]
Instead of static docs, generate safety artifacts from code annotations (like Rust's `#[safety]` attributes) so they can't drift.

## Porquê? ×5
1. Why formal artifacts? → Because experimental flight needs evidence of due diligence
2. Why ARP4761 not DO-178C? → Advisory-only system doesn't need code certification
3. Why FHA+FTA not STPA? → Team familiarity; FHA/FTA standard for aviation
4. Why GSN not CAE? → GSN more visual, easier to review
5. Why traceability matrix? → Required by any credible safety standard

What are we optimizing that we shouldn't be?
Optimizing for document completeness rather than artifact-code alignment.

### Implementor Phase

## Como se fosse uma criança
The safety documents are like a map that shows where the monsters live and where the safe paths are. We need to make sure the map matches the territory, and update it when the territory changes.

## Como se fosse um especialista
Implement as living documents in Markdown with automated checks. The traceability matrix will be a Markdown table with CI validation. Safety case in GSN format using Mermaid diagrams.

[ADDRESSING FAILURE MODE 1]
Mechanism: Add `make safety-check` CI step that validates traceability matrix completeness and checks that every hazard has at least one test reference.

[ADDRESSING FAILURE MODE 2]
Mechanism: Safety envelope constants defined in single source (`safety_envelope.py:DEFAULT_SAFETY_CONFIG`), referenced by both code and FHA doc via include or generation.

[ADDRESSING FAILURE MODE 3]
Mechanism: Traceability matrix is the single source of truth; CI gate fails if any REQ lacks hazard link or any hazard lacks test.

[ADDRESSING ASSUMPTION]
Validation: CI gate `make safety-check` validates matrix completeness and cross-references.

[ADDRESSING ALTERNATIVE FRAMING]
Incorporation: Safety envelope constants are the single source of truth; docs reference them via `{% include %}` or similar.

[SOLUTION PROPOSAL]
Create 7 safety artifact files in `docs/safety/` with:
1. SSA: system description, safety requirements, architecture
2. FHA: table of ≥10 failure conditions with severity
3. FTA: 4 top events with minimal cut sets
4. Traceability: Markdown table REQ→Hazard→Test with CI validation
5. Safety Case: GSN-style argument in Mermaid + Markdown
6. Operational Limits: documented with config references
7. Emergency Procedures: 6 scenarios with decision trees

All artifacts in Markdown for version control, reviewable in PRs.

## Porquê? ×5
1. Why Markdown? → Version control, diffable, renderable in GitHub
2. Why GSN? → Visual, structured, accepted in aviation
3. Why Mermaid? → Diagrams in Markdown, version controlled
4. Why CI validation? → Prevents drift, enforces traceability
5. Why not Word/Doors? → Version control, diffable, free tooling

What are we optimizing that we shouldn't be?
Optimizing for document completeness rather than artifact-code alignment.

---

## Verification Criteria

- [ ] SSA documents system, environment, safety requirements
- [ ] FHA identifies ≥10 failure conditions with severity classification
- [ ] FTA analyzes ≥4 top events with minimal cut sets
- [ ] Traceability matrix covers all REQs → Hazards → Tests
- [ ] Safety Case (GSN) argues residual risk acceptable
- [ ] Operational Limits documented with configurable parameters
- [ ] Emergency Procedures cover 6 scenarios
- [ ] All artifacts reviewed and approved
- [ ] CI gate: `make safety-check` passes

## Estimation

- Complexity: **medium** (4–10h)
- Risk: **medium** (documentation quality, traceability maintenance)
- Blocking dependencies: **T007, T008, T009** (system must be functional to analyze)