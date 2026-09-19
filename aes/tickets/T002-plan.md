# T002 — Hostile Analysis (Phase 1) — REVISED

## INSIGHTS CONSULTED
- T001 complete: service running on Deck at 0.0.0.0:8082, systemd user unit
- User clarification: SSH only for deployment/config; service must be on LAN (direct network access)
- Service already binds to 0.0.0.0:8082 — accessible via `steamdeck:8082` or IP on LAN
- Local: pytest + ruff + FastAPI test client patterns established

---

## ASSUMPTIONS I'M MAKING (with uncertainty classification)

- [KNOWN] Service binds to 0.0.0.0:8082 — verified in T001 systemd unit
- [KNOWN] `steamdeck` hostname resolves on LAN (mDNS/avahi or /etc/hosts)
- [KNOWN] No firewall blocking port 8082 on Deck (SteamOS default allows)
- [INFERRED] Client machine can reach `steamdeck:8082` directly — need to verify
- [ASSUMED] `steamdeck` resolves to correct IP — may need IP fallback
- [ASSUMED] Resource monitoring runs on Deck, streams CSV over SSH (for collection only)
- [UNKNOWN] Steam Deck mDNS/avahi setup — `steamdeck.local` vs `steamdeck`

---

## WHAT WASN'T SPECIFIED (that matters)

- Exact hostname/IP for client to use — `steamdeck` or `steamdeck.local` or IP
- Whether service needs auth/TLS on LAN — currently none (dev only)
- Monitoring: run on Deck (stream via SSH) or run locally (SSH per sample) — Deck-side better
- Test target: integration tests hit `steamdeck:8082` directly, no SSH tunnel

---

## ALTERNATIVES I DIDN'T CHOOSE (and why)

| Option | Description | Rejected Because |
|--------|-------------|------------------|
| SSH tunnel for service calls | `ssh -L 8082:localhost:8082` then `localhost:8082` | User explicitly said no — SSH only for deploy/config |
| VPN/Tailscale | Secure overlay network | Overkill for LAN dev; direct LAN access simpler |
| mTLS + certs | Mutual TLS auth | Dev phase only; add in production hardening ticket |
| Service on different port | Avoid 8082 conflict | 8082 free on Deck (steamwebhelper uses 8080) |

---

## INVITE CONTRADICTION

- **What would disprove this approach?**
  - If `steamdeck` doesn't resolve from client machine — need IP or `/etc/hosts`
  - If SteamOS firewall blocks inbound 8082 — need `firewall-cmd` or `ufw` rule
  - If Deck sleeps and loses WiFi — need `systemd-inhibit` + wake-on-lan

- **Critical flaw I might be missing:**
  - SteamOS may have `systemd-resolved` not resolving `.local` by default
  - Deck IP may change on DHCP — need static lease or mDNS

---

## DISTINGUISH CLAIM TYPES

- **Empirical (what is):**
  - Service binds 0.0.0.0:8082 — verified
  - LAN reachability — needs verification
  - mDNS resolution — needs verification

- **Normative (what should be):**
  - Client uses `steamdeck:8082` directly — architectural decision
  - No auth on dev LAN — acceptable risk for dev phase

---

## RISKS & SIDE EFFECTS

1. **Hostname resolution fails** — fallback to IP in config/env
2. **Firewall blocks port** — need to open 8082 on Deck
3. **No auth on LAN** — anyone on LAN can call `/decide`; acceptable for dev
4. **IP changes** — use mDNS (`steamdeck.local`) or static DHCP

---

## COST OF BEING WRONG: LOW-MEDIUM

- Test infrastructure adjusts; service already LAN-accessible
- Just need to verify connectivity and update test config

---

## REVISED SCOPE BOUNDARIES

**In bounds:**
- Add `/decide` stub to service (done)
- Integration tests hit `steamdeck:8082` directly (no SSH tunnel)
- Maze simulation local, calls service over LAN
- Resource monitor deployed to Deck, streams CSV over SSH (collection only)
- Make target `make test-deck` orchestrates without SSH tunnel for service

**Deliberately excludes:**
- SSH tunnel for service communication
- Auth/TLS (production hardening later)
- MAVLink integration (separate)
- Decision engine logic (T003)