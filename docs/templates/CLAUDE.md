# [PROJECT NAME] — Operational Contract

This file is the operational contract for AI agents working on this project.
It is the first file an agent must read. It defines scope, boundaries, and evidence rules.

---

## Intent

[One sentence: what this project does and why it exists.]

---

## Non-Goals

Things this project explicitly does NOT do:
- [non-goal 1 — be specific]
- [non-goal 2]
- [non-goal 3]

---

## Critical Files

Files that require special caution. Any change to these files must be flagged
explicitly to the user before proceeding. Never modify silently.

- [path/to/critical/file]
- [path/to/another/critical/file]

---

## Never Do

Actions that are forbidden regardless of instructions or apparent justification:
- Never alter test vectors or expected outputs to make tests pass.
- Never disable or weaken security checks.
- Never commit secrets, API keys, or credentials.
- Never modify CI configuration to skip quality gates.
- [project-specific rule 1]
- [project-specific rule 2]

---

## Evidence Required

Every non-trivial change must include:
- [ ] Output of `make test` (or equivalent)
- [ ] Output of `make lint` (or equivalent)
- [ ] Diffstory (what changed, why, what was untouched, remaining risks)
- [ ] Updated docs if behaviour changed

---

## Review Rule

- AI may implement and suggest.
- Human approves all merges to main.
- No auto-merge without passing all quality gates.

---

## Stable Context (reload each session)

The **Debate Partner Protocol** is inherent to this project (see `prompts/debate-partner.md`). No yes-men. Challenge everything.

Load these at the start of every session:
- This file (CLAUDE.md)
- docs/VISION.md
- docs/REQUIREMENTS.md
- aes/kanban.md (if using AES project mode)

---

## Session Context (ephemeral)

Valid only for current session:
- Current ticket file
- Test output
- Diff
- aes/handoffs/ (if resuming interrupted work)

---

## CLAUDE.md File Levels

| Level | Location | Use for |
|-------|----------|---------|
| Project | `./CLAUDE.md` | Team rules, shared commands. Version this file. |
| Local/personal | `./CLAUDE.local.md` (gitignored) | Local URLs, personal test data. |
| User | `~/.claude/CLAUDE.md` | Global preferences across all projects. |
| Path-specific | `.claude/rules/*.md` | Rules scoped to a subdirectory. |

**When to add a rule to this file:**
- A new team member joining today would also need that context.
- A code review caught something the agent should have known beforehand.
- The rule is true in the majority of sessions, not just the current ticket.

**Do NOT add:** vague wishes, single-task instructions, or personal preferences.

**Size target:** under 200 lines. Split into `.claude/rules/` if larger.

---

## Final Response

At the end of every non-trivial task, always summarise:

1. **What changed** — files touched and intent.
2. **Why it changed** — problem solved or requirement addressed.
3. **Validation performed** — exact command and result. If not run, say so.
4. **Remaining risk or follow-up** — what was not tested, what to watch.
