# SESSION HANDOFF — 2026-10-07 (continuation: forensic audit + register-divergence reconciliation)

> **Resume:** say `continue` — this file + `governance/CONTEXT_INDEX.md` are the entry points.
> The previous handoff (D-2860 commit-frontier gate) is SUPERSEDED by this one for state and next-steps.

## HEADLINE (the audit answer)

The prior sitting's handoff claimed "Rails GREEN" for three rails (`check_decision_membership`,
`check_bug_status`, `check_commit_frontier`) but did **not** run the full ladder. A full `just health`
this sitting is **RED**: **4 fatal (rc=1) drifts** + several owner-owed (rc=2) drifts. This sitting fixed
the one that is unambiguously mechanical (register divergence); the other three are re-baseline/decision
drifts and are left RED, classified below. Do **not** build Phase 2/3/4 on a red baseline.

## STATE VERIFIED (measured, not assumed)

- git HEAD **`1426df9`** (unchanged this sitting; no commit yet at audit time). Porcelain after the fix:
  `config/register_divergence.yaml` only.
- `just health` = **RED** (aborts at `check_register_divergence`, line 40). Full `run_ladder.py --collect health`
  shows 4 fatal faults (below).
- Bug register 422 carried (unchanged). Decisions 990 (D-2860 = last, still ACTIVE).

## WHAT LANDED THIS SITTING

**Reconciled `config/register_divergence.yaml` (BUG-571 shrink-only list):** removed 25 STALE pins
(BUG-099/148/151/159/160/168/169/182/222/223/224/228/229/230/231/232/234/235/236/237/238/241/242/243/267 —
all now carry a HEADER, so the pin was stale) and pinned the one NEW uncarried name
(BUG-429, first named `governance/buglog.md:8678`, no header). Ceiling `declared_max_uncarried` 63→39.
`check_register_divergence.py` now exits 0. This is STRUCTURAL (a verified fact about names-vs-headers),
not a status decision: BUG-429's actual open/closed state was **not** invented (D-2645 backfill rule).

## FORENSIC AUDIT — the 4 fatal drifts (and one meta-finding)

1. ✅ **register divergence** — FIXED this sitting (above).
2. ❌ **check-label-provenance** — boundary population CHANGED: 7983 rows belong to declared generation runs
   `[t11, bug198_reinject, e2e]` but `config/label_provenance.yaml#boundary.measured_rows` declares 7995
   (a 12-row delta). Store change OR deliberate re-baseline required (BUG-501/D-2638). **Decision + owner.**
3. ❌ **build_anchor_store_bridge** — committed bridge (`governance/ANCHOR_STORE_BRIDGE_20260926.json`) no
   longer re-derives (a join/name/input moved since D-2813/D-2812). **Re-derive or re-baseline — decision.**
4. ❌ **verify_handoffs** — `config/decisions.yaml` declared append_only but receipted bytes are not a prefix:
   first 911661 bytes hash `8eb0167cf8bf52f8` ≠ receipted `b2145053e96128b2` — a byte inside the receipted
   region was edited in place (BUG-376 class). Likely introduced in `65339ae` (D-2826..D-2859 "rename/promote"
   batch). **Re-baseline the receipt via the declared route — decision.**

**META-FINDING (hidden failure):** running `just health` / `run_ladder.py --collect` **dirties 4 tracked
files as a side effect** — `config/derivations.yaml` (check_config_defaults auto-raises the shadowed/undeclared
ceiling 221→229 / 2→3), `governance/RECONCILIATION.json`, `governance/METRICS.jsonl`, `governance/MUTATION_JOURNAL.jsonl`.
A "health check" is not read-only. These were reverted this sitting; the ceiling raise is itself owner-owed debt
(8 new shadowed + 1 new undeclared config key since 2026-10-03) and needs review, not a silent commit.

Owner-owed (rc=2, pre-existing, NOT addressed): ANCHOR-4 context drift (BUG-431 open, owner gate), workbook
rulings RED (R001 depth_final), write_guard 7/10 writers, config-default ceiling stale.

## NEXT CRITICAL STEPS (in consequence order)

- **D-2864 (mint): re-baseline the 3 red drifts** — (a) `label_provenance.yaml#boundary.measured_rows` 7995→7983
  after confirming the 12-row delta is a legitimate store change; (b) re-derive the anchor<->corpus bridge; (c)
  re-baseline the `decisions.yaml` append-only receipt (confirm the in-place edit was intentional, then re-baseline).
  These are STRUCTURAL re-baselines but each touches a receipted boundary → one decision each, owner-ratified.
- **BUG (open):** file BUG-659 for the `check_config_defaults` ceiling auto-RAISE (221→229 shadowed / 2→3
  undeclared) — shrink-only ceiling must not be silently raised by the check; flag the 9 new keys for review.
- **BUG (open):** file BUG-660 for the health-ladder write side effects (health must be read-only, or its writes
  declared + committed as part of the run).
- **BUG-429 header:** give BUG-429 a proper HEADER (real bug "UNRESOLVED contains RESOLVED", BUG-572 family) —
  requires knowing its true status → human/owner decision, then remove the pin.
- **OWNER-GATE (unchanged, do NOT cross unilaterally):** referee =
  `governance/discipline_anchor_rederived_v6_20261006d.json` + 28-row remap → finish D-2853.
- **D-2860 ratification:** flip ACTIVE→RATIFIED after owner reads.
- **Phase 2 [D-2861]:** canonical `config/bugs.yaml` + `config/tasks.yaml` (render MD as DERIVED, C13 backup first).
- **Phase 3 [D-2862]:** cross-entity invariants in `reconciliation.yaml` + 2-3 check kinds in `reconcile.py`.
- **Phase 4 [D-2863]:** enforce `decisions.yaml` shape via Pydantic/JSON Schema (C12).
- **Pipeline (D-2859):** menu 65/44 vs taxonomy 64/43 off-by-one; D-2857 split; D-2858 recalib+flip; new A/B.

## GOV DEPENDENCIES SYNCED THIS SITTING

`config/register_divergence.yaml` (BUG-571 list reconciled) · this handoff. No decision minted, so
`decisions.yaml` / `decisions_summary.json` / `DECISION-LOG.md` / census unchanged (990).
