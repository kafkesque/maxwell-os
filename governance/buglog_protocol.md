# Buglog Protocol v1.0
> **Ratified:** 2026-07-20 | **Decision:** D2011
> **File:** `governance/buglog.md`

## Rule

**Whenever recurring bugs and issues accumulate, gather them in `governance/buglog.md` with full documentation so they can be passed to the next LLM in a handoff.**

This is a standing rule — not a one-time action.

## Trigger

When 5+ bugs are unresolved, the full buglog MUST be appended to all LLM handoff documents so the next LLM has complete context.

## Auto-Log Rule (2026-07-22)

**Agent MUST log any bug immediately upon discovery.** No deferring. If a tool call fails unexpectedly, returns garbled output, or reveals a systemic issue — log it NOW. This applies to: model failures, API errors, config mismatches, pipeline crashes, data corruption, duplicate files, stale references, and any behavior that deviates from expected operation.

## Bug Entry Format

Every bug entry must include:

| Field | Required | Description |
|-------|----------|-------------|
| Bug ID | ✅ | Unique identifier (BUG-NNN) |
| Severity | ✅ | 🔴 CRITICAL / 🟠 HIGH / 🟡 MEDIUM / 🟢 LOW |
| File | ✅ | Path relative to project root |
| Lines | ✅ | Line numbers or function name |
| Symptom | ✅ | What the user/operator observes |
| Root Cause | ✅ | Why the bug exists |
| Proposed Fix | ✅ | Concrete change with approximate LOC |
| Source | ✅ | Which document/audit discovered it |
| Status | ✅ | OPEN / IN PROGRESS / RESOLVED |
| Phase | ✅ | Which roadmap phase addresses it |

## Severity Definitions

| Level | Criteria |
|-------|----------|
| 🔴 CRITICAL | Data loss, pipeline failure, constitutional violation, produces incorrect FBs |
| 🟠 HIGH | Broken feature, incorrect output, scaling failure at ≤1000 FBs |
| 🟡 MEDIUM | Quality degradation, missing optimization, edge case |
| 🟢 LOW | Cosmetic, documentation, future improvement |

## Resolution Requirements

- Bug is RESOLVED when: fix is committed AND verified (test passes, re-run produces correct output)
- Move to RESOLVED section with reference to commit hash
- Keep resolved bugs for 90 days (audit trail), then archive

## Ownership

- Every open bug must have a proposed fix and a target phase
- No bug stays "acknowledged but unassigned" for >1 session
- Phase assignment follows the roadmap: Phase 0 (immediate), Phase 0.5 (pre-processing), Phase 1 (intent+verify), Phase 1.5 (modularize), Phase 2+ (deferred)

## Handoff Format

When appending to LLM handoff:

```markdown
## BUGLOG (from governance/buglog.md)

The following bugs are unresolved as of {date}. Full details in `governance/buglog.md`.

| Bug ID | Severity | File | Symptom | Phase |
|--------|----------|------|---------|-------|
| BUG-001 | 🔴 CRITICAL | stage5_verify.py:115 | Verification checks random principles | 0 |
| ... | ... | ... | ... | ... |

See `governance/buglog.md` for root cause analysis and proposed fixes for each.
```
