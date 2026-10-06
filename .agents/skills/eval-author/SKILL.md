---
name: eval-author
description: Authors short, crisp test scenarios and frozen golden evaluations under specs/tests/ matching 1-to-1 with requirement specs.
---

# Skill: Eval Author (Gate 2)

Use this skill to define test scenarios and behavioral specifications for features defined in `specs/requirements/`.

## Core Rules

1. **Exact 1-to-1 Pairing:** For every `specs/requirements/XXXX-name.md`, create `specs/tests/XXXX-name.md` using the exact same number and name.
2. **Short, Crisp Behavioral Language:**
   - Define scenarios using concise **Given / When / Then** or **Input $\rightarrow$ Expected Output** format.
   - Specify positive paths, negative paths, and numerical boundary conditions (e.g. empty series, NaNs, zero division).
3. **The Golden Eval Law (Immutability):**
   - Once approved by the user, this document is **FROZEN**.
   - During implementation, the agent is **STRICTLY FORBIDDEN** from modifying or relaxing the test spec to make buggy code pass.
   - If tests fail, the code must be fixed, never the test spec.
4. **No Framework Bloat:** Scenarios must be testable using minimal, standard tooling (`pytest` or assert-based test runners).
