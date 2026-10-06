# Forensic Audit — D-2839 anchor-ratification gate (2026-10-05)

Scope: the D-2837 → D-2820 → D-2839 → D-2767 chain (definition-anchored menu ADOPTION → anchor
re-derivation → owner ratification → full-204 A/B). Read-only sweep; no LLM classification run.

## Verdict

**NO BREAK, NO CASCADE.** The chain is architecturally sound; D-2837 (ADOPT) and D-2838 (writer-limb)
are RATIFIED, the menu-v6 gate condition is SATISFIED, and governance census is GREEN (968 decisions,
stamp `5a2565c1d692cb36`, source_sha256 `e34464ff0bce0232`). Two gaps found and acted on:

- **F-01 (BLOCKING GAP):** no re-derivation harness exists for D-2820. The procedure is specified
  (D-2820/D-2703/D-2832) but there is no `scripts/rederive_anchor_axes_v6.py`. Existing scripts
  (`consolidate_anchor_208.py`, `build_split_manifest.py`, `vote_anchor_domains.py`) do NOT do the
  v6 definition-anchored re-derivation + owner/second-coder/NLI + stamping. → filed as TASK.
- **F-02 (BLINDSPOT / HIDDEN FAILURE):** the A/B referee is FROZEN-INVALID (D-2820) but NOTHING in code
  refuses a pre-D-2820 A/B. `benchmark_s4_ab.py`, `anchor2_kappa.py`, `fit_eval_model_swap.py` read the
  v5-stamped 204-gold / `taxonomy_v5.yaml` with no `menu_hash` pin check, so a kappa computed before
  re-derivation is CIRCULAR and would silently read GREEN at the 0.800 floor. → filed **BUG-650**.

## Findings

| # | Check | Result |
|---|---|---|
| F-01 | D-2820 re-derivation harness present? | **GAP** — none. TASK to build + R5-review before first run. |
| F-02 | Fail-closed guard blocks pre-D-2820 A/B? | **GAP** — none. **BUG-650** (filed). |
| F-03 | Menu-v6 gate condition (non-empty menu_hash)? | **SATISFIED** — composite `92f1a204...`, answer-space `d704d06e...` (config/menu_axis_hashes.yaml). |
| F-04 | Menu v6 definition-anchored, single abstention? | **CLEAN** — closed_menu_v6.json: abstention `emerging`, 65 disciplines / 44 domains; D-2830/D-2834 single token. |
| F-05 | D-2839 minted? | **GAP** — missing; minted this sitting as PROPOSED (owner gate). |
| F-06 | Governance census + registry records-only? | **GREEN** — 968 decisions, `--check` passes; D-2837/D-2838 present, flag OFF, tree uncommitted. |

## Superseded / Resolved / Deferred inventory

- **SUPERSEDED:** D-2814 "explicit none" → D-2830/D-2834 `emerging`; D-2815 slot names {marketing,
  management, entrepreneurship} → D-2829 {business administration, marketing, entrepreneurship studies};
  D-2773 label-only menu → superseded by D-2814 (mutual-exclusion guard D-2833); BUG-232 "recompute
  source_diversity" → SUPERSEDED (D-2176 already shipped).
- **RESOLVED:** BUG-644 (stamp silent-skip), BUG-645 (files list), BUG-646 (stale prose), BUG-649 (R5
  FAIL→fixed), BUG-641 (taxonomy_shacl v5.5 → v5.7).
- **DEFERRED:** D-2832 (v6 re-stamp → D-2820 step-3), D-2835 (group-prefilter), D-2703 primary_domain
  auto-classification (re-scoped to D-2820), D-2836 residual gemma philosophy (→ A/B).
- **IN PROGRESS (code changed, pending menu-v6 commit):** BUG-640, BUG-643, BUG-647.
- **OPEN in chain:** BUG-629 (emerging regression), BUG-630 (cross-axis guard blunt), BUG-631 (cardinality
  — writer-limb DONE, store sweep + 52 re-derive remaining), BUG-642 (alias_map), BUG-648 (token bloat).

## Recommendation (senior RAG/systems-engineer)

D-2837 is the right call and stays ADOPTED: verbatim closed menu + definition anchors + per-axis `emerging`
abstention is the only direction that makes classification ontologically *traceable* (menu_hash provenance,
D-279) and future-proof (label vocabulary decoupled from model output). It is NOT sufficient for *accuracy* —
that is why the flag flip is empirically gated (D-2767). D-2839 is the bridge that makes that gate sound:
**ratify the re-derived anchor as referee only after the four criteria (menu-v6 hash-stamped, owner-adjudicated,
second-coder + NLI cross-checked, D-274d-stamped).** Never let the A/B run circular (BUG-650 guard).

## Next critical steps (strategic order)

1. **BUG-650** — build the fail-closed pre-A/B anchor-referee guard (blocks any pre-D-2820 kappa).
2. **TASK** — build + R5-review `scripts/rederive_anchor_axes_v6.py` (menu-v6 definition-anchored classify →
   owner adjudicate → second-coder + DeBERTa-NLI → D-274d stamp).
3. **TASK** — run D-2820 re-derivation; owner signs off → flip D-2839 PROPOSED → RATIFIED.
4. **TASK** — full-204 A/B (D-2767): kappa ≥ 0.800 AND emerging ≤ 0.35 vs flag-OFF.
5. **DECISION** — flip `definition_anchored_menu_enabled: true` iff the A/B passes.
6. **TASK** — D-2822 S5 Gate A(d) (OR-entail + AND-no-contradiction) + NLI recalibrate.
7. **TASK** — C1/BUG-642 alias_map shrink-then-remove; re-freeze closed_menu_v6.json in the taxonomy commit.
