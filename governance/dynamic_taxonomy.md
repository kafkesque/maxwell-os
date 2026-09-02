# Dynamic Taxonomy — Bounded Competitive Canonical System

> Logged 2026-08-31 (session). Authority: **D2066, D2378, D2399**, `governance/domain_labelling.md §5`, `pipeline/taxonomy_manager.py`.
> **Do NOT re-derive this.** Read this before touching taxonomy / "emerging" / canonical labels.

## Core concept
The canonical taxonomy (discipline + domain) is a **BOUNDED, FIXED-CAP set of slots**.
Raw labels are **NOT appended** — they **COMPETE** for existing slots via **promote-with-demote**.
`emerging` is the **waiting room** (placeholder for the long tail), **NOT an error**.

**Never hand-expand the taxonomy.** That blows the cap and bypasses the competition.

## Mechanism (D2066)
1. S4 classification is **open-set** → raw labels (`discipline_raw` / `domains_raw`) are preserved forever (G9).
2. Post-S6, `taxonomy_manager.update_counts_from_fbs` accumulates raw-label usage into the `taxonomy_counts` SQLite table.
3. `check_for_replacements`: an `emerging` label is flagged for review when
   `count(emerging) > count(weakest_canonical) × 1.10`
   i.e. it must **outnumber the weakest incumbent by ≥10%**.
4. **HUMAN approves** (C8-G1/G2) → raw **promoted** to canonical, weakest canonical **demoted** to `displaced`.
5. **Closed-loop:** canonical count never grows past cap. Auto-generates `taxonomy_v<N+1>.yaml`.

## Caps (config-driven, D2378)
- `max_domains: 35` (config/pipeline_config.yaml)
- `max_disciplines`: config-driven — **currently 75 real, LEAVE AS 75** (do not "fix" to 72)
- `REPLACEMENT_THRESHOLD_RATIO = 1.10` (emerging must exceed incumbent by 10%)
- `FLOOD_THRESHOLD_RATIO = 20%` (pause for batch review if >20% emerging — C8-G3)
- `EMERGING_FREQ_THRESHOLD` (raw→emerging promotion count)

## Status lifecycle
```
raw  →  emerging  →  canonical  →  displaced
```
(`displaced` = demoted but retained — history preserved, not deleted.)

## Deferred
**D2399:** promote/demote runs on **FULL-corpus** counts (post-T1.1 + D2345 single-source), **NOT** the canary.

## Consequence for "emerging" over-firing (BUG-150)
- Over-firing `emerging` caused by **missing ALIASES** → fix via **synonym-index mapping to EXISTING canonicals** (bounded, no new slots).
- Genuinely-novel **long tail** (no incumbent) → **STAYS `emerging`** by design → dynamic promote/demote decides later.
- Two separate fixes, never conflated:
  1. **Alias fix** (synonym index → existing canonical) — deterministic remap, safe now.
  2. **Dynamic promotion** (raw beats weakest incumbent → human approves → swap) — post-full-corpus, human-gated.

---

## Fix applied 2026-08-31 — long-tail accumulation (D2399 challenger pool)

**Bug:** `taxonomy_manager.update_counts_from_fbs` read ONLY canonical
`domains`/`discipline` and skipped `"emerging"`, so `*_raw` long-tail labels never
accumulated into `taxonomy_counts`. Consequence: `check_for_replacements` had an
**empty challenger pool** — the D2399 promote/demote competition could never fire.

**Fix:** the function now also reads `domains_raw`/`discipline_raw` and counts any
raw label that maps to no canonical (`_is_long_tail`: not a canonical, not in the
kind-constrained `get_synonym_index` → D2133). Applied to `pipeline/taxonomy_manager.py`.
Inert to the running S4 (module already loaded; S6 re-imports post-S4). Dry-run on a
fork of the live checkpoint (1,850 records) validated:
- `organizational behavior` → 31, auto-promoted raw→emerging ✓
- `graphic design`           → 41, emerging ✓
- `psychology`               → 233, canonical incumbent preserved (not double-counted) ✓

**Revelations from the dry-run (all post-S4 remap items — NOT new S4 defects):**
1. **Unicode dash variants still present in the live (pre-remap) checkpoint** —
   `human–computer interaction` (U+2013 ×9) and `human‑computer interaction`
   (U+2011 ×8) remain separate raw labels; Phase 0a NFKC/dash-folding collapses them.
2. **domain-not-discipline mis-filing is broader than graphic design** —
   `entrepreneurship` (a canonical **domain**, taxonomy_v5) is also emitted as a
   **discipline** by gpt-oss (9 records). Extends the BUG-150/BUG-167/D2422 cross-kind class.
3. `flood_warning=True` on the pre-remap checkpoint is EXPECTED (~29% emerging) —
   clears after the post-S4 alias remap (~5%).
