# Issue Tracker & Specification Conventions

Specifications and test scenarios for `dtwmagic` live in the `specs/` directory following the **4-Gate SDAD Protocol**:

## Storage Layout

- **Requirement Specs (Gate 1):** `specs/requirements/XXXX-name.md` (4-digit monotonic numbering: `0001`, `0002`, ...).
- **Frozen Test Specs (Gate 2):** `specs/tests/XXXX-name.md` (exact 1-to-1 match with requirement spec).
- **Change & Decision Records (Gate 4):** `specs/changes/XXXX-name.md` (post-implementation ADRs).

## Golden Rules for Skills

1. **Mandatory User Value:** Every requirement spec MUST include an explicit "User Value Rationale" justifying why a paying retail trader cares. If no user value exists, flag and stop.
2. **Negative Scope:** Every requirement spec MUST define "What Is NOT Needed" to prevent AI over-engineering.
3. **Frozen Evals:** Once approved by the user, test specs in `specs/tests/` are **IMMUTABLE**. Never modify test specs to make buggy code pass.
4. **Approval Gate:** Never run implementation skills (`tdd`, `implement-spec`) until the user has explicitly approved both the requirement spec and test spec.
5. **Kailash Nadh Minimalism:** Implement using boring, simple, frugal Python/NumPy/Parquet/SQLite with minimal dependencies.
