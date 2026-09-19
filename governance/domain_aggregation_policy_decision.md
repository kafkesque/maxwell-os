# Domain-Aggregation Auto-Policy — Decision Request (D2618 P1 follow-up, D2628/D2633)

> **Status:** ✅ **RESOLVED (2026-09-14) — user ruling: B (overlap → union).**
> Final domain set = sorted **union** of both reliable voters, **always including
> DeepSeek's classification**. Disjoint → abstain (never fabricate). Executed via
> `scripts/aggregate_domain_votes.py` → `governance/p1_domain_aggregation.json`
> (**148/216 accepted**: 42 exact-set + 106 union; 2 discipline-unanimous disjoint
> → domain-abstain; 66 contested discipline). The same policy applies to the 59
> queue rows under re-vote (D2631) with zero re-compute.

## Context
The D2618 P1 reliable-pair vote (DeepSeek-v4-pro + Qwen3.8-27B-MLX-4bit) voted
**discipline + domain** on the 216 principle anchor rows. Discipline is 61-way
**single-label**; domains are 43-way **multi-label** (1-5 per row). The pair
agrees on discipline far more often than on the *exact* domain set — multi-label
domains disagree on granularity even when both voters agree on the core.

## Measured (deterministic, from `governance/discipline_domain_vote_checkpoint.jsonl`)
| Metric | Count | % of 216 |
|---|---|---|
| rows voted | 216 | — |
| discipline unanimous | 150 | 69.4% |
| domains **exact-set** unanimous | 42 | 19.4% |
| domains **overlap** (non-empty ∩, sets differ) | 116 | 53.7% |
| domains **disjoint** (no ∩) | 2 | 0.9% |
| **auto-acceptable** (discipline unanimous AND domains at-least-overlap) | **148** | 68.5% |

Overlap rows: union size min 2 / max 6 / **avg 3.60**; intersection avg **1.57**.
Of 116 overlap rows, **65 are granularity sub/superset** (union == one voter,
e.g. `{ai & agents}` vs `{ai & agents, code & computation}`) and **51 are true
merges** (both voters add distinct domains).

## The open policy question
When the reliable pair agrees on discipline but returns **different** domain
sets, which rows are auto-accepted and how is the final domain set formed?

## Options
- **A. Exact-set unanimity (conservative)** — accept domains only when both
  voters return the identical set → **42 rows (19.4%)**; 106 rows abstain → human
  review. Zero granularity risk; highest review cost.
- **B. Overlap → union (balanced)** — accept when domain sets overlap →
  **148 rows (68.5%)**; final set = **union**. Highest coverage; union can
  over-include (true merges may add a domain neither voter would keep alone).
- **C. Overlap → intersection (strictest useful)** — accept 148 rows but final
  set = **intersection** (avg 1.57 domains); risks *dropping* granularity.

## Recommendation: **B (overlap → union)**
1. **Matches measured human behavior** — in the 216 human-adjudicated domain
   verdicts (D2628), the final set matched the pair's **union** in 94/216 cases
   (the most common outcome) vs intersection in only 22/216.
2. **Domains are multi-label by design** — union pools both voters' knowledge;
   the 2 truly-disjoint rows still abstain (no fabrication).
3. **3.5× auto-acceptance** (148 vs 42) without weakening the discipline gate
   (discipline unanimity is still required) → cuts human review cost.

**Caveat:** union can over-include on true merges. These labels remain
**advisory** (a downstream human/classifier refines them); if maximal precision
outweighs coverage, choose **C (intersection)** instead. **A** is the default
until ruled.

## Action after ruling
One-line deterministic re-aggregation of the stored votes (DeepSeek + Qwen3.8
domain sets are already checkpointed) — no API re-spend. Applies to both the
148 auto-acceptable P1 rows and the 59 queue rows under re-vote.
