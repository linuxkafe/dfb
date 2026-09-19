---
ticket: T004
title: Client library / CLI to query Deck service
sprint: sprint-01
priority: medium
status: in-progress
created: 2026-09-19
---

# T004 — Hostile Analysis (Phase 1)

## INSIGHTS CONSULTED
- Service endpoints on Deck: `/health`, `/version`, `/decide`, `/confirm/issue`, `/command`, `/confirm/verify/{token}`.
- Service runs on `steamdeck:8082` reachable via LAN.
- Current interaction is raw `curl` / `requests` in test scripts.
- Need a reusable Python client library and a CLI (`dfb-cli`) for operators.

## ASSUMPTIONS

- [KNOWN] Service API stable (health, decide, command with token).
- [KNOWN] Communication over HTTP/JSON.
- [INFERRED] CLI should support: `health`, `decide`, `issue-token`, `command`, `verify-token`.
- [ASSUMED] Config via env vars (`DFB_HOST`, `DFB_PORT`) or config file.
- [UNKNOWN] Whether async client needed (likely not for CLI).

## WHAT WASN'T SPECIFIED

- Exact CLI UX (flags, subcommands).
- Auth beyond token (none for now).
- Packaging entry point.

## ALTERNATIVES NOT CHOSEN

| Option | Reason |
|--------|--------|
| gRPC | Overkill; HTTP fine. |
| WebSocket | Not needed. |
| Keep raw curl | Not reusable. |

## INVITE CONTRADICTION

- If service adds auth later, client must adapt.

## CLAIM TYPES

- Empirical: endpoints exist.
- Normative: provide typed client + CLI.

## RISKS

- Service API changes -> client breaks (versioning later).

## COST OF BEING WRONG: LOW

## REASONING SKELETON

1. Create `src/dfb/client.py` with `DeckClient` class (typed methods).
2. Add `src/dfb/cli.py` with `typer`/`click` subcommands.
3. Add entry point in `pyproject.toml` (`dfb = dfb.cli:app`).
4. Update `Makefile` target `install-cli` / `dfb-cli`.
5. Test against live Deck service.

## SCOPE BOUNDARIES

In: client lib, CLI, entry point, basic tests.
Out: auth, retries, circuit breaker, config file (later).

## HOSTILE ANALYSIS LINT CHECK

Refs: `src/dfb/service.py`, `tests/deck/test_integration.py`, `pyproject.toml`.