---
name: ponytail-tdd
description: Implements features using strict Test-Driven Development (TDD) adhering to Kailash Nadh radical simplicity and Ponytail lazy senior dev rules.
---

# Skill: Ponytail TDD (Gate 3)

Use this skill ONLY AFTER the user has explicitly approved both `specs/requirements/XXXX-name.md` and `specs/tests/XXXX-name.md`.

## Execution Workflow

1. **Verify Approvals First:** Check that both the requirement spec and test spec exist and have user sign-off. If not approved, STOP and request approval.
2. **Red Phase (Write Test First):**
   - Translate scenarios from `specs/tests/XXXX-name.md` into `tests/test_XXXX.py`.
   - Run the test suite and verify it fails for the expected reason.
3. **Green Phase (Write Minimum Code):**
   - Write the shortest working diff that satisfies the test.
   - Stop at the first rung that holds: standard library $\rightarrow$ numpy/scipy $\rightarrow$ simple function.
   - Zero unrequested abstractions, zero boilerplate classes.
   - Kailash Nadh mindset: flat functions, direct operations, minimal memory footprint.
4. **Refactor & Ceilings:**
   - Ensure tests pass completely.
   - Never modify `specs/tests/XXXX-name.md` to pass a test.
   - If a deliberate simplification is made (e.g. O(N) scan, naive cache), mark it with a `ponytail:` comment describing the known ceiling and upgrade path.
