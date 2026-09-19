# Task: Initial project setup

## Goal
Establish working project with AES quality gates passing.

## Hostile Analysis
- What assumptions are we making about the runtime?
- What could break in deployment?
- Is this the simplest way to achieve the goal?

## Proposed Solution
1. Follow language-specific setup guide
2. Write simple "hello world" to verify toolchain
3. Ensure `make check` passes

## Surgical Plan
1. Create minimal src/main.* → verify: compiles/imports
2. Create tests → verify: `make test` passes
3. Configure linter/formatter → verify: `make lint` passes

## Validation
- [ ] Project builds without errors
- [ ] `make check` passes
- [ ] All docs exist and are filled
- [ ] Git initialized, first commit made
