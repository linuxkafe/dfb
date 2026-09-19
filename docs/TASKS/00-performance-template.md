# Task: Optimize [Component/Operation] for Better Performance

## Objective
Improve the performance of [specific component, operation, or code path] to meet [specific performance target or improve by X%].

## Pre-Implementation Checklist (Karpathy Principles)
- [ ] **Think Before Coding** — Do I have a baseline measurement? Have I identified the actual bottleneck? Am I optimizing the right thing?
- [ ] **Simplicity First** — What's the simplest optimization? Can I remove work instead of accelerating it?
- [ ] **Surgical Changes** — Can I optimize the hot path without touching cold paths? Is this change independently measurable?
- [ ] **Goal-Driven Execution** — How will I benchmark before and after? What confidence interval is sufficient?

## Context
[Include current performance measurements, profiling data, or user impact that motivates this optimization. Specify the scenario being measured (e.g., API endpoint, batch job, user action).]

## Constraints
- Must not change functional behavior or correctness
- Optimizations should be justified by measurable gains
- Should not significantly increase code complexity without clear benefit
- Must maintain thread safety and other correctness properties if applicable
- Performance gains should be reproducible under similar conditions

## Success Criteria
- Performance measurements show [specific improvement] under test conditions
- No functional regressions in existing behavior
- Code remains maintainable and follows project conventions
- Any added complexity is justified by the performance gain
- Performance improvement is consistent across multiple test runs