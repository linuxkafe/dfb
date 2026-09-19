---
rubric-id: NARRATIVE-INTEGRITY-v1
candidate: NARRATIVE-INTEGRITY-SUITE — P1-P6 narrative integrity mitigations
created: 2026-08-19
dimensions:
  - correctness
  - security
  - epistemic-coherence
  - debt
  - reproducibility
---

# Review Rubric — NARRATIVE-INTEGRITY-SUITE

## Correctness

| ID | Criterion | Verifiable Check |
|----|-----------|-----------------|
| C-01 | write-access-log.sh produces valid hash chain entries | `./scripts/write-access-log.sh SD-TEST accessed test && tail -1 aes/shadow/access.log` has 6 fields, last two are 64-char hex |
| C-02 | verify-access-log.sh detects tampering | `echo "fake line" >> aes/shadow/access.log && ./scripts/verify-access-log.sh` exits non-zero; then restore from backup |
| C-03 | migrate-access-log.sh is idempotent | Run twice: second run prints "Already in hash chain format" |
| C-04 | parse_access_log() in scoring.py still works with new format | `python3 -c "from lib.memory.scoring import parse_access_log; from pathlib import Path; print(parse_access_log(Path('aes/shadow/access.log')))"` returns non-empty dict |
| C-05 | epistemic-debt-rules.sh --validate passes all 16 test cases | `./scripts/epistemic-debt-rules.sh --validate` prints "All rule functions working correctly" |
| C-06 | narrative-analysis.py exits 0 on current data | `python3 scripts/narrative-analysis.py` exits 0 (risk < 5) |
| C-07 | narrative-proof.sh produces valid JSON | `./scripts/narrative-proof.sh T210 && python3 -c "import json; json.load(open('aes/epistemic-proof/T210-proof.json'))"` exits 0 |
| C-08 | conflict-detection.sh finds stale references | `./scripts/conflict-detection.sh` outputs stale reference warnings |
| C-09 | token-budget-trace.py generates trace file | `python3 scripts/token-budget-trace.py && test -f aes/metrics/token-budget-trace.log` |
| C-10 | generate-index.py auto-calls trace | `python3 scripts/generate-index.py` outputs "Token Budget Trace" line |

## Security

| ID | Criterion | Verifiable Check |
|----|-----------|-----------------|
| S-01 | No shell injection via DOC_ID parameter | `./scripts/write-access-log.sh '; rm -rf /;' test 2>&1 || true` must not execute injected command |
| S-02 | Shellcheck passes on all .sh scripts | `shellcheck scripts/write-access-log.sh scripts/verify-access-log.sh scripts/migrate-access-log.sh scripts/epistemic-debt-rules.sh scripts/conflict-detection.sh` exits 0 |
| S-03 | No secrets or keys in scripts | `grep -rn "password\|secret\|api_key\|token" scripts/write-access-log.sh scripts/verify-access-log.sh scripts/migrate-access-log.sh scripts/epistemic-debt-rules.sh scripts/narrative-proof.sh scripts/conflict-detection.sh` returns 0 |

## Epistemic Coherence

| ID | Criterion | Verifiable Check |
|----|-----------|-----------------|
| E-01 | Access log format is documented in SKILL.md | `grep -q "TS DOC_ID ACTION PREV_HASH CHAIN_HASH" skills/user/aes-access-log/SKILL.md` |
| E-02 | All gates start as WARN (exit 0) | `./scripts/verify-access-log.sh; echo $?` returns 0; `./scripts/conflict-detection.sh; echo $?` returns 0 |
| E-03 | Thresholds are version-controlled in .aes/config.mk | `grep -q "AES_ACCESS_LOG_VERIFY_WARN" .aes/config.mk` |
| E-04 | Shadow docs have correct epistemic fields | `head -20 aes/shadow/SD-META-022.md` contains id, title, synthesis, epistemic_state, provenance |

## Debt

| ID | Criterion | Verifiable Check |
|----|-----------|-----------------|
| D-01 | No dead code in new scripts | `grep -n "^#" scripts/write-access-log.sh | grep -v "Usage\|Description\|Format\|Note\|EXAMPLE\|FIXME\|TODO\|NOTE" | wc -l` ≤ 5 (comment overhead) |
| D-02 | No duplicated threshold logic | `grep -c "VERIFICATION_RATE_MIN" scripts/epistemic-debt.sh` returns 1 (only the source line) |
| D-03 | All new scripts are executable | `test -x scripts/write-access-log.sh && test -x scripts/verify-access-log.sh && test -x scripts/migrate-access-log.sh && test -x scripts/epistemic-debt-rules.sh && test -x scripts/conflict-detection.sh && test -x scripts/narrative-proof.sh` |
| D-04 | generate-index.py fallback path is marked | `grep -n "Fallback" scripts/generate-index.py` returns at least 1 match |

## Reproducibility

| ID | Criterion | Verifiable Check |
|----|-----------|-----------------|
| R-01 | make access-log-verify passes | `make access-log-verify` exits 0 |
| R-02 | make conflict-check passes | `make conflict-check` exits 0 (warnings OK) |
| R-03 | make narrative-analysis passes | `make narrative-analysis` exits 0 |
| R-04 | make debt-rules-check passes | `make debt-rules-check` exits 0 |
| R-05 | make check exits 0 | `make check` exits 0 (all gates including new ones pass) |

---
pre-registered-hash: (computed after creation)
