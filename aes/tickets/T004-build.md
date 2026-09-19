# T004 — Diffstory (Build Output)

## What Changed

### Files Created
- `src/dfb/client.py` — `DeckClient` typed wrapper for all REST endpoints.
- `src/dfb/cli.py` — Typer CLI (`dfb`) with subcommands: `health`, `version`, `decide`, `issue-token`, `command`, `verify-token`.
- `tests/test_client.py` — Unit tests for `DeckClient` (mocked HTTP).
- `aes/tickets/T004-plan.md` — Hostile Analysis (Phase 1).
- `aes/tickets/T004-build.md` — This diffstory.

### Files Modified
- `pyproject.toml` — Added `cli` optional extra (`typer`, `rich`), console script entry point `dfb = dfb.cli:app`.
- `Makefile` — Added `install-cli` target.
- `aes/kanban.md` — T004 moved to Done.

## Why It Changed

**Problem**: Operators needed a reusable, typed way to interact with the Deck Fly Brain service instead of raw `curl`.

**Solution**: Thin typed client + CLI with subcommands covering all endpoints, token-based safety gate for `/command`.

## What Was Intentionally Untouched

- Service endpoints unchanged.
- No auth beyond token (future work).
- No retries/backoff (future).

## Remaining Risks / Follow-up

1. **Token TTL 30s** — short; CLI must issue token just before command.
2. **No retries/backoff** — network flakiness not handled.
3. **No config file** — relies on env vars `DFB_HOST`, `DFB_PORT`.
4. **No version negotiation** — client assumes API v1.

## Validation Performed

- `make check` — passes (14 tests, 93% coverage, ruff clean).
- `make install-cli` — installs `dfb` console script.
- Manual CLI verification against live Deck service (`steamdeck:8082`):
  - `dfb health` → `{"status":"ok","version":"0.1.0"}`
  - `dfb decide …` → returns action/logits.
  - `dfb issue-token` → returns token.
  - `dfb command ARM --token <token>` → `{"success":true,"message":"Command 'ARM' acknowledged (simulated)"}`
  - `dfb verify-token <token>` → shows validity.

## Diffstat

```
 src/dfb/client.py      | 100 ++
 src/dfb/cli.py         |  95 ++
 tests/test_client.py   |  70 ++
 pyproject.toml         |   5 +-
 Makefile               |   5 +
 aes/tickets/T004-*.md  |  60 ++
```

## Commands for Reproduction

```bash
make install-cli          # installs dfb CLI
dfb health
dfb decide '{"position":[0,0],"grid":[[0]*10]*10,"exit":[9,9]}'
dfb issue-token
dfb command ARM --token <token>
dfb verify-token <token>
```