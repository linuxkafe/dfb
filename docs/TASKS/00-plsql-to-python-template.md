# Task: Migrate [PL/SQL Component] to Python

## Objective
Migrate the [specific PL/SQL package/procedure/function] to Python while preserving all functional behavior, maintaining performance within [X]% of original, and enabling future maintenance by the existing team.

## Pre-Implementation Checklist (Karpathy Principles)
- [ ] **Think Before Coding** — Do I understand every code path in the original PL/SQL? Have I mapped dependencies and Oracle-specific features?
- [ ] **Simplicity First** — Can I replicate the logic with idiomatic Python instead of a line-by-line transliteration?
- [ ] **Surgical Changes** — Can this migration be done incrementally (file by file, procedure by procedure)?
- [ ] **Goal-Driven Execution** — How will I verify behavioral equivalence? What performance baseline must I match?

## Context
[Include findings from reconnaissance:
- Current PL/SQL size (lines of code, number of units)
- Key dependencies on Oracle-specific features (e.g., packages, overloaded procedures, collections, object types)
- Performance baselines from existing tests
- Known pain points in current PL/SQL (complex error handling, difficult-to-test procedures)
- Deployment mechanism and integration points
- Team skills assessment]

## Constraints
- Must preserve exact business logic and data integrity
- Performance degradation must not exceed [X]% for critical paths
- Must not break existing dependent applications during transition
- Must use idiomatic Python (PEP 8) with appropriate Oracle connectivity (oracledb or cx_Oracle)
- Database schema changes require separate approval process
- Migration must be achievable in incremental, reversible steps
- Must maintain security compliance (SQL injection prevention, proper error handling)
- If applicable, maintain transactional behavior consistent with original PL/SQL

## Success Criteria
- All existing PL/SQL unit tests pass when run against Python implementation (using test database)
- Manual verification of key scenarios shows identical outputs
- Performance benchmarks show ≤[X%] degradation on critical transactions
- Code follows PEP 8 and project-specific Python style guides
- Documentation updated to reflect new implementation
- Rollback plan validated and tested
- Security scan shows no new vulnerabilities introduced