#!/usr/bin/env python3
"""Safety check script for traceability matrix validation.

Runs the traceability matrix completeness gate. Fails if:
- any REQ references an unknown hazard
- any hazard lacks both a resolvable test reference and a documented N/A justification
- any referenced test path does not exist in the repo
- any hazard is not referenced by any REQ (orphan)
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    sys.path.insert(0, os.path.join(ROOT, "docs", "safety"))
    try:
        import traceability
    except Exception as exc:  # pragma: no cover - import failure must fail the gate
        print(f"FAIL: could not import docs/safety/traceability.py: {exc}")
        return 1

    cache = {"root": ROOT}
    errors = traceability.check_traceability()
    if errors:
        print(f"FAIL: {len(errors)} traceability issue(s):")
        for err in errors:
            print(f"  - {err}")
        return 1

    n_test = sum(1 for refs in traceability.HAZARD_TO_TESTS.values() if refs)
    print(f"OK: {len(traceability.REQ_TO_HAZARDS)} REQs, {len(traceability.HAZARDS)} hazards, "
          f"{n_test} hazards with automated test evidence, "
          f"{len(traceability.N_A_TESTS)} documented as non-automated.")
    print("All safety checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())