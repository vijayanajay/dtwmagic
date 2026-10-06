# Specification & Evaluation System (SDAD)

This directory houses the complete **Spec-Driven Agentic Development (SDAD)** lifecycle for the project, combining **Matt Pocock's agentic evaluation discipline** and **Kailash Nadh's radical simplicity**.

## Directory Structure

```
specs/
├── requirements/      # Gate 1: Functional specs (What is needed, what is NOT needed, user value)
│   └── XXXX-name.md   # Sequential 4-digit numbering (e.g., 0001-ohlcv-data-loader.md)
├── tests/             # Gate 2: Frozen test scenarios & evals (Given / When / Then)
│   └── XXXX-name.md   # Exactly matches requirement spec number (IMMUTABLE once approved)
└── changes/           # Gate 4: Change & Decision Records (ADR / Worklog)
    └── XXXX-name.md   # Post-implementation summary of changes, rationale, and ceilings
```

## Numbering & Workflow Rules

1. **4-Digit Sequencing:** Every feature starts with a 4-digit ID (`0001`, `0002`, ..., `9999`).
2. **1-to-1 Mapping:** Spec `0001` in `requirements/` MUST have a matching `0001` in `tests/` and eventually `0001` in `changes/`.
3. **Mandatory User Value:** Every requirement spec must have an explicit "User Value Rationale" justifying why a paying user cares. If there is no end-user value, it is flagged and discarded.
4. **Negative Scope:** Every requirement spec must define "What Is NOT Needed" to prevent AI over-engineering.
5. **Frozen Test Specs (Eval Protection):** Once approved by the user, a test spec is **frozen**. The agent is strictly forbidden from modifying test scenarios during implementation to make broken code pass.
6. **Zero Code Without Sign-Off:** No code implementation is permitted until the user explicitly reviews and approves the requirement spec and test spec.
