---
name: spec-author
description: Creates 4-digit requirement specifications under specs/requirements/ with mandatory User Value Rationale and Negative Scope boundaries before any code is written.
---

# Skill: Spec Author (Gate 1)

Use this skill when drafting, refining, or decomposing requirements into formal specifications before any code is written.

## Core Rules

1. **Sequential 4-Digit Numbering:** Locate the highest existing number in `specs/requirements/` and increment (`0001-name.md`, `0002-name.md`).
2. **Mandatory User Value Rationale:**
   - Every spec MUST begin with a clear explanation of what direct value this feature provides to a paying trader.
   - If the feature provides no end-user value (e.g. gratuitous refactor, unused abstraction), stop and consult the user before writing the spec.
3. **Explicit Scope Separation:**
   - **What Is Needed (Scope):** Minimal, actionable requirements.
   - **What Is NOT Needed (Negative Scope):** Explicit boundaries preventing AI over-engineering (e.g. no unnecessary classes, no external message brokers, no unrequested caching layers).
4. **Kailash Nadh Minimalism:** Keep the proposed design boring, simple, and frugal.
5. **No Code Rule:** Under NO circumstance may this skill write application code. It only outputs the specification for user review and approval.
6. **Strict Frontend/Backend Seam (Parallel Dev Rule):** Every spec must be strictly categorized as either a **Backend Engine Spec** (Python engine generating/updating the Static API JSON contract) or a **Frontend Presentation Spec** (Static HTML/CSS/JS dashboard consuming the JSON contract). Never combine backend compute algorithms and frontend UI presentation in the same spec.

