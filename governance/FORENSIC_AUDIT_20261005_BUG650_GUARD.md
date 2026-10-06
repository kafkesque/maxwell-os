# Forensic Audit — 2026-10-05 — BUG-650 pre-A/B anchor-referee guard (D-2840)

## Scope
Implementation of the #1 critical step: the fail-closed pre-A/B anchor-referee guard
(BUG-650) plus governance sync. Run BEFORE the guard landed, on the guard + wiring,
and after. Flag remains OFF; tree remains uncommitted.

## Verdict

**NO BREAK, NO CASCADE, NO DRIFT.** The guard is additive and fail-closed. One
decision point resolved (depth axis intentionally unguarded). Governance census GREEN.

## Findings

- **F-01 (GAP, closed):** the 204-gold discipline/domain referee carried NO menu stamp
  at all (`discipline_anchor_conformance_20261002.json` has only `_provenance`, no
  `menu_hash`/`closed_menu_sha256`/`answer_space_sha256`). The guard treats a missing
  stamp as REFUSE (cannot certify a menu-v6 referee), so the A/B cannot silently run
  against it. Fixed by the guard itself.
- **F-02 (BLINDSPOT/HIDDEN-FAILURE, closed = BUG-650):** `anchor2_kappa.py` read
  `ANCHOR2_KEY_20260920.json` whose `menu_hash = 73597ee2...` (frozen v5). Confirmed
  frozen-invalid; guard now exits non-zero. Verified live: `anchor2_kappa.py` → exit 1.
- **F-03 (DECISION, documented):** depth axis (`depth_conformance_gate.py`) is NOT
  guarded. Rationale: menu v6 (D-2814/2815/2816) changed discipline slots, domain slots
  and the abstention token — NOT the 4-way depth axis (universal/cross-domain/domain/
  specialized). A depth kappa is not menu-circular. Deliberately scoped, not a gap.
- **F-04 (COVERAGE, verified):** `fit_eval_model_swap.py` is protected via its
  `from discipline_conformance_gate import load_anchor as load_discipline_anchor`
  import — the guard fires inside `load_anchor()`, so no separate wiring was needed.
  Import chain verified clean.
- **F-05 (CASCADE, none):** `--selftest` paths still pass (they never call
  `load_anchor`); `--dry-run` now fails-closed (correct — a majority-class baseline
  against a frozen-invalid gold is equally meaningless).
- **F-06 (CENSUS):** GREEN. 970 decisions (stamp f5faa921f90f053a after D-2840 mint);
  bug_status OPEN 145 / CLOSED 244 of 389 (BUG-650 PARTIAL → still OPEN with progress).
- **F-07 (BLINDSPOT, noted for next):** no `scripts/rederive_anchor_axes_v6.py` harness
  yet — D-2820 re-derivation has no executable yet. This is the #2 critical step and is
  OWNER-GATED to run.

## Superseded / resolved / deferred inventory (re-checked)
- **Superseded:** D-2814 `explicit none` → `emerging` (D-2834); D-2815 slot names →
  D-2829 JEL-M forms; D-2773 label-only menu → D-2814.
- **Resolved:** BUG-644/645/646/649/641; BUG-650 → PARTIAL (guard landed).
- **Deferred:** D-2832 (v6 re-stamp), D-2835 (prefix cache), D-2703, D-2836 gemma
  philosophy; D-2820 re-derivation + D-2839 ratification remain owner/human-gated.

## Next critical steps (in order)
1. **TASK** — build + R5-review `scripts/rederive_anchor_axes_v6.py` (D-2820):
   menu-v6 definition-anchored classify → owner adjudicate → second-coder + DeBERTa-NLI
   → D-274d stamp (anchor_version/menu_hash/taxonomy_version/coder/date/abstention).
2. **DECISION** — owner runs D-2820 re-derivation; signs off; D-2839 PROPOSED→RATIFIED.
3. **TASK** — full-204 A/B (D-2767: kappa≥0.800 AND emerging≤0.35) vs flag-OFF — now
   fail-closed safe (the guard refuses the frozen-invalid anchor).
4. **DECISION** — flip `definition_anchored_menu_enabled: true` iff A/B passes.
5. **TASK** — D-2822 S5 Gate A(d) + NLI recalibrate; then C1/BUG-642 alias_map
   shrink-then-remove + re-freeze `closed_menu_v6.json`; then ONE bundled commit.
