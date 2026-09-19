# T001 — Hostile Analysis (Phase 1)

## INSIGHTS CONSULTED
- SSH connectivity verified: `deck@steamdeck` reachable, key-based auth works
- Steam Deck: Python 3.13.5, systemd 257 (user services available), sudo works
- User systemd dir exists at `/home/deck/.config/systemd/user/`
- Local project: FastAPI + pymavlink, venv at `.venv/`, ruff + pytest passing

---

## ASSUMPTIONS I'M MAKING (with uncertainty classification)

- [KNOWN] SSH key-based access works — verified just now with `ssh -o BatchMode=yes deck@steamdeck echo OK`
- [KNOWN] Python 3.13.5 on Deck — verified via SSH
- [KNOWN] systemd user services supported — verified via `/home/deck/.config/systemd/user/` directory
- [INFERRED] System Python on Deck is sufficient (no venv needed) — evidence: Python 3.13.5 has pip, we can `pip install --user` or use `pipx`; risk: dependency conflicts with SteamOS packages
- [ASSUMED] `deck` user has passwordless sudo — not verified; if false, systemd system service install fails, but user service works
- [ASSUMED] Steam Deck stays awake during development — risk: Deck sleeps, systemd-inhibit may be needed
- [ASSUMED] LAN connectivity stable — if on Tailscale/WiFi, SSH tunnel may drop; need keepalive
- [UNKNOWN] Whether FastAPI/uvicorn/pymavlink install cleanly on Deck's Arch-based SteamOS — evidence: Arch packages exist, but pymavlink may need build deps (lxml)
- [UNKNOWN] Port allocation on Deck — 8080 assumed free; could conflict

---

## WHAT WASN'T SPECIFIED (that matters)

- Exact service name: `flybrain` vs `dfb` vs `flybrain.service` — ticket says `flybrain`
- Whether to use systemd user service (no sudo) or system service (needs sudo) — ticket says "start with user service if possible"
- Python dependency installation method on Deck: `pip install --user`, `pipx`, or venv
- How to handle Python path for the service (where is the code deployed?)
- SSH tunnel keepalive config
- Log rotation / journald config
- Whether service should auto-start on boot (user services need `loginctl enable-linger`)

---

## ALTERNATIVES I DIDN'T CHOOSE (and why)

| Option | Description | Rejected Because |
|--------|-------------|------------------|
| Podman/container | Containerfile + podman systemd unit | Adds complexity; SteamOS has podman but user systemd is simpler for Python service |
| Systemd system service (sudo) | Install to `/etc/systemd/system/flybrain.service` | Needs sudo; user service avoids this; SteamOS `/etc` persists but immutable-ish |
| Git pull on Deck | Clone repo on Deck, `git pull` in deploy | Overkill for scaffold; rsync is simpler for dev iteration |
| scp instead of rsync | `scp -r src/ deck@steamdeck:...` | rsync incremental + delete is better for repeated deploys |
| aiohttp instead of FastAPI | Lighter, no pydantic | FastAPI already in local deps; pydantic helps with health schema; team knows it |

---

## INVITE CONTRADICTION

- **What would disprove this approach?**
  - If `pip install --user fastapi uvicorn pymavlink` fails on Deck due to missing build deps (lxml, fastcrc)
  - If user systemd service doesn't start on boot without `loginctl enable-linger deck`
  - If SSH tunnel drops frequently making health checks unreliable
  - If Deck's Python 3.13 has breaking changes for pymavlink (unlikely, but possible)

- **Critical flaw I might be missing:**
  - SteamOS updates may wipe `/home/deck/.local/bin` or user systemd units? (Unlikely, `/home` persists)
  - pymavlink's `lxml` dependency may fail to build without `libxml2-dev`/`libxslt-dev` on Deck

---

## DISTINGUISH CLAIM TYPES

- **Empirical (what is):**
  - SSH works, Python version, systemd version, user systemd dir exists — verified
  - pymavlink installs on Arch — needs verification
  - User service persists across reboot — needs verification

- **Normative (what should be):**
  - "Use systemd user service" — preference for simplicity, avoid sudo
  - "rsync for deploy" — dev ergonomics choice
  - "FastAPI for health endpoint" — consistency with local stack

---

## RISKS & SIDE EFFECTS

1. **Build dependency failure on Deck**: pymavlink → lxml → needs libxml2/libxslt headers. Mitigation: pre-install on Deck or use manylinux wheels (pymavlink 2.4+ has wheels).
2. **Service not surviving reboot**: user systemd needs `loginctl enable-linger deck`. Must document.
3. **SSH tunnel instability**: long-running tunnels drop. Mitigation: `ServerAliveInterval`, `ExitOnForwardFailure`.
4. **Port conflict**: 8080 may be used. Mitigation: pick random high port or check.
5. **SteamOS read-only `/usr`**: Can't install system packages without `steamos-readonly disable`. User pip installs to `~/.local` avoid this.

---

## COST OF BEING WRONG: MEDIUM

- If deploy fails: T001 blocks T002/T003/T004 — all downstream work waits
- But: scaffold is throwaway; we can pivot to podman or system service
- No safety impact — this is ground infrastructure only

---

## REASONING SKELETON FOR KEY CLAIMS

**Claim**: "Systemd user service + rsync deploy is the simplest working path"

- Premise 1: User systemd dir exists and has active services (verified)
- Premise 2: `deck` user can run systemd user services (standard on systemd 257)
- Premise 3: rsync over SSH is installed on both ends (standard)
- Premise 4: Python 3.13 + pip can install FastAPI/uvicorn/pymavlink as user (Arch-based, likely)
- Inference: No sudo needed, no container overhead, dev iteration fast
- Conclusion: Proceed with user service + rsync

**Claim**: "pymavlink will install on Deck without system packages"

- Premise: pymavlink 2.4.49 on PyPI provides manylinux wheels including lxml
- Premise: Deck is x86_64 (AMD APU), compatible with manylinux_x86_64
- Inference: `pip install --user pymavlink` should fetch wheels, no build needed
- Conclusion: Acceptable risk; verify during deploy

---

## SCOPE BOUNDARIES DECLARATION

**In bounds (this analysis covers):**
- SSH verification, service scaffold, systemd user unit, rsync deploy Make target, health endpoint

**Deliberately excludes:**
- MAVLink integration (T002)
- Decision engine logic (T003)
- Client library (T004)
- Production hardening (TLS, auth, secrets management)
- Service monitoring/alerting
- Cross-compilation or binary deployment

---

## HOSTILE ANALYSIS LINT CHECK

File references in this analysis:
- `aes/tickets/T001-ssh-deck-scaffold.md` — ticket being analyzed
- `src/main.py` — local FastAPI entry point (to be adapted for Deck)
- `pyproject.toml` — dependencies (FastAPI, uvicorn, pymavlink)
- `Makefile` — deploy target to add
- `.venv/` — local venv (not deployed)
- `/home/deck/.config/systemd/user/` — Deck user systemd dir (verified)