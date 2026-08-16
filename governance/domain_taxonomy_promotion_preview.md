# Domain Taxonomy Promotion — Preview & Mechanism (G3 / D2394 remainder)

> **Updated:** 2026-08-16 | **Status:** awaiting human review (post-T1.1) | **Blocks:** nothing (post-commit remap)

## TL;DR

Domain `emerging` is 93.9% (261/278) on the canary — the v5 taxonomy is design-centric
(descends from the original design-book corpus) but the actual corpus is
**business / psychology / economics / operations**-centric. This is a **post-commit remap**,
NOT a pre-run blocker: `domains_raw` preserves every LLM original label, so promotion can
re-map the committed `domains` field without re-running any LLM stage.

**Sequencing (confirmed):** T1.1 full run → `taxonomy_counts` seeded from `domains_raw` at
S6 (`run_post_commit_taxonomy`) → `check_for_replacements()` emits `human_review_taxonomy.json`
→ human approves → `taxonomy_manager.py --apply` → `generate_taxonomy_yaml()` → re-map
`domains` from `domains_raw`.

## Canonical usage (new-278 canary, 2026-08-16)

`emerging` 261 · business operations 118 · legal & public policy 66 · organizational behavior 64 ·
engineering practice 39 · digital product 34 · health & wellness 34 · research & methodology 34 ·
education 33 · business development 23 · user experience 20 · systems & frameworks 10 ·
finance & investment 9 · code & computation 8 · marketing & communications 8 …

## Promote candidates (raw labels with no canonical cover, freq ≥ 8)

| Raw label | canary freq | Proposed canonical domain | Group |
|---|---|---|---|
| risk management | 31 | `risk management` | Business & Strategy |
| project management | 21 | `project management` | Business & Strategy |
| human resources | 18 | `human resources` | Business & Strategy |
| behavioral economics | 18 | `behavioral economics` | Business & Strategy |
| psychology | 16 | `psychology` | Behavioral & Cognitive (new) |
| operations management | 14 | `operations` (merge + operations research 10) | Business & Strategy |
| data science | 13 | `data & decision science` (merge decision science 11) | AI & Computing |
| innovation management | 12 | `innovation` | Business & Strategy |
| personal development | 12 | `personal development & coaching` | Behavioral & Cognitive |
| strategic planning | 10 | `strategy` (merge business strategy 28) | Business & Strategy |
| economics | 10 | `economics` | Systems, Semiotics & Knowledge |
| public health | 10 | `healthcare & public health` (merge healthcare 8) | Systems, Semiotics & Knowledge |
| change management | 9 | `change management` | Business & Strategy |

(~13 new domains; exact set + naming is a HUMAN call — this is a starting point, not final.)

## Demote candidates (design-centric canonicals, ~0 usage)

`brand identity` (0) · `motion design` (0) · `illustration` (0) · `packaging` (0) ·
`computational art` (0) · `creative technology` (0) · `web & ui` (0) · `graphic design` (1) ·
`data visualization` (1) · `arts & culture` (2) · `environmental design` (3) ·
`media & entertainment` (3) · `editorial & advertising` (4) · `semiotics & communication` (6)

Cap is **35** (`taxonomy.max_domains`). Promoting ~13 requires demoting ~13 — use
`check_for_replacements()`'s promote-with-demote pairing (weakest canonical displaced by each
approved emerging label), then human review of the regenerated YAML before activation (C8-G2).

## Guardrails honored

- **C8-G3 flood detection:** `TAXONOMY_FLOOD_THRESHOLD = 0.20` — >20% emerging pauses for batch review.
- **D2378 caps:** 35 domains / 72 disciplines enforced in `pipeline_config.yaml`.
- **Not auto-applied** — requires `approved: true` per candidate (D2066 promote-with-demote).
- **`domains_raw` provenance preserved** (D2394) — promotion is reversible and lossless.

## References

- D2394 (taxonomy gap + synonym/alias fixes), D2378 (caps), D2066 (dynamic canonical taxonomy).
- Mechanism: `pipeline/taxonomy_manager.py` → `check_for_replacements` / `apply_replacements` /
  `generate_taxonomy_yaml`.
