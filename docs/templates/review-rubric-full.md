---
rubric-id: AES-FULL-2026-07-21
candidate: Full AES Project Review (all phases, all code)
created: 2026-07-21
dimensions:
  - correctness
  - security
  - epistemic-coherence
  - debt
  - reproducibility
  - usability
  - architecture
---

# Review Rubric — Full AES Project

## Correctness

| ID | Criterion | Verifiable Check |
|----|-----------|-----------------|
| C-01 | `make check` passes on clean clone | `git clone /opt/aes /tmp/aes-test && cd /tmp/aes-test && make check` exits 0 |
| C-02 | All epistemic tests pass | `python3 -m pytest lib/epistemic/ -q` exits 0 with 346+ tests |
| C-03 | Kanban consistency check passes | `make kanban-check` exits 0 |
| C-04 | All phase commands exist and are callable | `make aes-plan TICKET=TXXX`, `make aes-build TICKET=TXXX`, `make aes-verify TICKET=TXXX`, `make aes-review TICKET=TXXX`, `make aes-learn TICKET=TXXX` all print usage (not error) when TICKET= is missing |
| C-05 | Pre-commit hooks execute without error | `.aes/hooks/pre-build.sh`, `.aes/hooks/pre-verify.sh`, `.aes/hooks/pre-review.sh` all exit 0 on clean repo |

## Security

| ID | Criterion | Verifiable Check |
|----|-----------|-----------------|
| S-01 | No shell injection in Makefile targets | `grep -r '\${TICKET}' Makefile` shows no unquoted expansions in shell commands |
| S-02 | No secrets in repo | `git log --all --full-history --oneline -- '*secret*' '*key*' '*token*' '*password*'` returns only legitimate test files |
| S-03 | Shell scripts pass shellcheck | `shellcheck scripts/*.sh bin/*` exits 0 |
| S-04 | File paths use strict quoting | `grep -r 'mktemp' scripts/*.sh | grep -v 'mktemp -d'` shows no unsafe temp file usage |
| S-05 | No eval or dynamic code execution | `grep -rn 'eval\|exec\|\$\(' scripts/*.sh | grep -v '^[^#]*#' | grep -v 'shellcheck'` returns empty |

## Epistemic Coherence

| ID | Criterion | Verifiable Check |
|----|-----------|-----------------|
| E-01 | Shadow docs have valid frontmatter | `find aes/shadow -name "*.md" -exec head -20 {} \; | grep -c '^---'` matches file count |
| E-02 | Every claim in INDEX.md has traceable evidence | `grep -n 'claim:' aes/INDEX.md | wc -l` > 0 and each cites a file/commit |
| E-03 | Pre-verify/pre-review hooks inject ILHA context | `grep -c 'ILHA' .aes/hooks/pre-verify.sh .aes/hooks/pre-review.sh` >= 2 |
| E-04 | Premise propagator runs at acordar/dormir | `grep -c 'run_propagation_for_regime' aes/gf/regime.py` >= 2 |
| E-05 | Wake context includes premise propagation status | `grep -c 'Premise Propagation' aes/gf/wake.py` >= 1 |
| E-06 | No "obviously/clearly" in codebase | `grep -ri 'obviously\|clearly' --include="*.py" --include="*.sh" --include="*.md" lib/ scripts/ aes/ | grep -v test | wc -l` == 0 |
| E-07 | GMIF levels mapped from epistemic_state correctly | `grep -A5 'gmif_from_epistemic' lib/epistemic/nanopub_bridge.py` shows correct mapping |

## Debt

| ID | Criterion | Verifiable Check |
|----|-----------|-----------------|
| D-01 | No dead code (unused functions) | `python3 -m vulture lib/epistemic/ --min-confidence 80 | grep -v test | wc -l` == 0 |
| D-02 | No duplicated logic between scripts | `diff -u <(sort scripts/generate-index.py | uniq -d) <(echo)` shows no duplicates |
| D-03 | No hardcoded ticket numbers in scripts | `grep -rn 'T[0-9]\{3\}' scripts/*.sh | grep -v test | grep -v '\.md' | wc -l` == 0 |
| D-04 | Test coverage >= 80% on core modules | `python3 -m pytest lib/epistemic/ --cov=lib.epistemic --cov-report=term-missing | tail -5` shows >= 80% |
| D-05 | No TODO/FIXME in production code | `grep -rn 'TODO\|FIXME\|XXX' lib/ scripts/ bin/ aes/gf/ | grep -v test | grep -v '\.md' | wc -l` == 0 |

## Reproducibility

| ID | Criterion | Verifiable Check |
|----|-----------|-----------------|
| R-01 | `make setup` installs everything | `rm -rf .llm_venv && make setup 2>&1 | tail -5` shows success |
| R-02 | New project scaffold works | `cd /tmp && make -f /opt/aes/Makefile new-project NAME=testapp LANG=python && cd testapp && make check` passes |
| R-03 | Skill installation works | `make install-skills` completes without error |
| R-04 | All Makefile targets are documented | `make help | wc -l` > 20 |
| R-05 | No flaky tests | `for i in 1 2 3; do python3 -m pytest lib/epistemic/test_premises_engine.py -q; done` all pass |

## Usability

| ID | Criterion | Verifiable Check |
|----|-----------|-----------------|
| U-01 | CLI help is comprehensive | `bin/aes --help 2>&1 | wc -l` > 20 |
| U-02 | Error messages are actionable | `make aes-plan 2>&1 | grep -c 'Usage\|usage\|TICKET'` >= 1 |
| U-03 | Session hooks install cleanly | `make install-session-hooks` completes |
| U-04 | Documentation matches reality | `grep -r 'lib/gf-premise-propagator' skills/user/` returns 0 (updated to lib/epistemic/premises) |

## Architecture

| ID | Criterion | Verifiable Check |
|----|-----------|-----------------|
| A-01 | No circular imports in lib/epistemic | `python3 -c "import lib.epistemic; print('ok')"` succeeds |
| A-02 | Core modules have single responsibility | `wc -l lib/epistemic/*.py | tail -1` no file > 500 lines (except propagator) |
| A-03 | Hooks don't duplicate logic | `diff -u <(grep -h 'can_promote' .aes/hooks/pre-*.sh | sort -u) <(echo)` shows minimal unique lines |
| A-04 | Skills don't overlap in scope | `grep -r 'summary:' skills/user/*.md | sort -u` shows unique summaries |

---
pre-registered-hash: <to-be-computed-after-commit>
