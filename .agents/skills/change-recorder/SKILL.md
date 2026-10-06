---
name: change-recorder
description: Generates short, crisp Change & Decision Records (ADRs) under specs/changes/XXXX-name.md after successful implementation and test verification.
---

# Skill: Change Recorder (Gate 4)

Use this skill immediately after a feature's tests have passed and implementation is complete.

## Core Rules

1. **Exact 1-to-1 Pairing:** Create `specs/changes/XXXX-name.md` using the exact matching 4-digit ID and name.
2. **Short, Crisp Structure:**
   - **Summary of Changes:** Bulleted list of files modified or added.
   - **Design & Quant Decisions:** Key mathematical, architectural, or performance choices made (e.g. why Z-normalization instead of min-max, why Euclidean pre-filter).
   - **Known Ceilings & Future Upgrades:** Note any simplified trade-offs and when they need revisiting (e.g. memory scaling limit when expanding to 2000 stocks).
   - **Test Verification:** Proof that tests matching `specs/tests/XXXX-name.md` passed completely.
3. **No Fluff:** Keep it concise, high-density, and factual for easy future audits.
