# D-2767 C+B GATE — Senior RAG / Ontological Engineer Recommendation (2026-10-09)

> **Owner gate:** emerging_rate <= 0.35 **AND** coarse_kappa >= 0.73
> (`config/pipeline_config.yaml#discipline_coarse_kappa_floor`, owner-ruled D-2767).
> **Status:** awaiting owner ruling. This doc is the recommendation, not a ruling.

## 1. Measured (D-2767 v8 A/B, flag-ON, n=194)

| granularity | kappa | vs floor |
|---|---|---|
| fine 62-way | 0.4216 | — |
| 9-way group | 0.5696 | — |
| **3-way coarse** | **0.5621** | **< 0.73 → FAIL** |
| emerging rate | 0.0155 | <= 0.35 → PASS |

**Verdict:** the C+B gate FAILS on coarse kappa (0.5621 < 0.73). D-2727 Option A (full S4 rerun) must **not**
launch — a below-gate discipline classifier would bake into all 6,591 canonical FBs.

## 2. Ontological diagnosis (why the fine axis cannot pass)

- `discipline` is the **rigid kind** — the tradition a construct comes from. Its menu is 62–65 fine classes.
- The **human ceiling** on this taxonomy is already measured (D-2796): **fine 0.581 / 9-way 0.728 / 4-way 0.729 /
  3-way 0.766**. No human reaches the 0.80 operative floor on fine discipline.
- Therefore a **0.73–0.80 fine-discipline gate is ontologically unreachable** — not an engineering gap but a
  resolution mismatch. The classifier at 0.42 fine / 0.56 coarse is below even the 3-way human ceiling.

## 3. Options examined

| # | Option | Verdict |
|---|---|---|
| (a) | **Discipline advisory-only** — fine discipline becomes provenance/multi-label; routing gates on the **3-way macro + domains** | **RECOMMENDED** |
| (b) | **Decider-model A/B** — autotrust/JEV-27B-VL or perplexity-ai/pplx-decider-v1.1-27b against the owner referee | **RECOMMENDED in parallel** |
| (c) | Coarsen further | **REJECTED** — 3-way 0.766 is already the coarsest defensible; fewer buckets = lossy routing |
| (d) | D-2727 full rerun under current gate | **BLOCKED** — below-gate classifier would bake into the corpus |

## 4. Recommendation

**(a) + (b), in parallel.**

1. **Demote fine discipline to advisory** (multi-label tags with provenance), and make the **3-way macro the
   operative routing facet** (its human ceiling 0.766 ≳ the 0.73 floor). Domains remain the retrieval primary.
2. **Run the decider-model A/B** as a candidate for the *macro* gate (not fine). A distinct-family decider at the
   3-way resolution is the only path that could clear 0.73 without shipping a below-ceiling classifier.
3. **Do not coarsen below 3-way** and **do not launch D-2727** until the owner rules.

## 5. Prerequisite fixed this session (BUG-690 part 2)

The coarse-kappa metric was being computed against a **stale macro map**: `config/discipline_macro_groups.yaml`
(and both consumers' menu pins) were built against `closed_menu_v5` (9 groups) and omitted the
**Business & Management** group first present in v6/v7/v8 (`business administration`, `entrepreneurship studies`,
`marketing`). ~21 rows collapsed to `UNMAPPED`, corrupting the coarse kappa. **FIXED (uncommitted):**
- `discipline_macro_groups.yaml` — added `Business & Management` → `Method & Business` (3-way) + `Method & Operations` (4-way); header now cites v8 / 10 groups.
- `discipline_macro_classify.py` — `DEFAULT_MENU` v5 → v8 (+ docstring).
- `discipline_advisory_rescore.py` — menu pin v5 → v8 (+ docstring).
- Verified: fail-closed guard covers all 10 v8 groups (0 uncovered); 3 B&M values → `Method & Business`.

**The gate still FAILS** (coarse ≈ 0.56 < 0.73) with the corrected metric — the fix makes the owner's ruling
*accurate*, it does not change the outcome.
