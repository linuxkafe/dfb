# Task: Fix [Bug Description] (Issue #[number] if applicable)

## Objective
Resolve the specific defect described as "[clear bug description]" to restore correct behavior.

## Pre-Implementation Checklist (Karpathy Principles)
- [ ] **Think Before Coding** — What is the minimal understanding needed? Can I explain the bug in one sentence? What assumptions am I making about the root cause?
- [ ] **Simplicity First** — What's the minimal fix? Am I adding unnecessary complexity?
- [ ] **Surgical Changes** — Can I fix this by changing the fewest possible lines? Does this touch unrelated code?
- [ ] **Goal-Driven Execution** — How will I verify the fix works? What's my rollback plan if this introduces a regression?

## Context
[Include steps to reproduce, expected vs. actual behavior, and any relevant logs, error messages, or screenshots. Reference the issue tracker if applicable.]

## Constraints
- Fix must be minimal and focused on the root cause
- Should not introduce new bugs or regressions
- Must not change behavior for correctly functioning scenarios
- If the bug involves security considerations, follow security response procedures
- Fix should be testable and verifiable

## Success Criteria
- The specific steps to reproduce no longer produce the erroneous behavior
- Expected behavior is now observed consistently
- Related tests (especially those covering this functionality) pass
- No new test failures introduced
- For regressions: previously passing tests related to this area still pass