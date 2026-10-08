# Domain-axis calibrated abstention — plan + owner gates (2026-10-08)

## The (c) refinement — do NOT bolt on a new conformal/Platt framework

Recommendation (c) was "per-principle content-driven domains + a calibrated confidence limit."
The correct *implementation* is to **extend the framework Maxwell already ships**, not to introduce
a parallel one. Conformal prediction and Platt/isotonic scaling are already *instantiated* inside the
D-312 → D-349 calibrated-abstention machinery: it measures a selective-error-vs-abstain curve on a
frozen, fingerprinted ruler, picks a rank-margin operating point, and stays `enabled: false` until a
shadow run. That *is* distribution-free set-level abstention (conformal-style), in Maxwell's own idiom.

Bolt-on Platt/isotonic + a second conformal library would be **bloat + conflict + drift** (two
"confidence" systems, two rulers, two margin semantics) — the exact failure the owner forbids.

## What already exists (do not re-derive)

- `config/verify_abstention.yaml` (D-312/D-338/D-339/D-349): INERT calibrated abstention, with a
  ratified `abstention_policy` block. Curves exist for `discipline` (percent_rank) and `content_type`
  (r2_max_entail).
- `governance/ABSTENTION_CALIBRATION_20260923.json` (D-349): measured curves + operating points.
- `governance/R2_GATE_MEASUREMENT_20260923.json` (D-348): declares `unmeasurable_axes.domains =
  "no ruler truth column exists (declared, not guessed)"` — **this is the single documented gap.**

## The one real gap → now closed

The domain axis was unmeasurable only because no frozen ruler truth column existed. The 208-row
consolidated anchor authority (`ANCHOR_208_CONSOLIDATED_20261007.json`) *does* carry owner-finalized
domain truth. `scripts/build_domain_ruler.py` freezes it:

- `governance/DOMAIN_RULER_FROZEN_20261008.json` — **201 rows**, sha256 `affe259e…`, 7 empty-domain
  rows skipped. Cardinality: 91 single-domain, 110 multi-domain (2→5). Primary-domain spread is
  healthy (research practice 18, design strategy 14, UX 13, marketing 12, business dev 11 …).

This is the prerequisite for the domain abstention curve — nothing more is asserted by it.

## D2D map guard — already structural (verified, not a new task)

`scripts/build_anchor_v8_remap_triage.py::remap` fires the D2D default **only when `kept` is empty**
(after v8 drops). The "never override content" guard is already in the code path; the map is a
fallback prior, exactly as OntoClean rigidity permits. No change needed.

## Video examination — "Vector Databases Are Dead. Use This Instead" (turbopuffer)

Verdict: **confirmatory, not corrective.** Maxwell is already architecturally ahead of the video's
thesis, because it is an offline *curation* pipeline (compile → verify → serve), not a live-RAG chat.

| Video signal | Maxwell status | Impact |
|---|---|---|
| Vector index demoted from center | SQLite + sqlite-vec already (stage6_commit) | none — already aligned |
| Keyword/BM25 often beats vector | `retrieve.py` already: SQL + FTS5 + sqlite-vec + RRF hybrid (D2176) | none — already hybrid |
| Agentic search beats single-shot | `retrieve.py` docstring already lists "Agentic" leg | confirm existing, nothing to add |
| Compiled knowledge cites far better (40% vs 19%) | `stage5_verify` NLI fail-closed + cited evidence | validates Maxwell's core bet |
| Live MCP connectors | anti-sovereign (C3/C22) — rejected | none — out of scope by design |
| FRAMES / EnterpriseRAG-Bench methodology | `retrieval_benchmark.py` exists | reference for eval design only |

**Adjustments required: none to config/logic/pipeline/schematics.** The only optional, owner-gated
adoption is (1) weight the RRF keyword leg higher for exact/ID-style queries (tuning, not a gap), and
(2) cite FRAMES/EnterpriseRAG-Bench as external eval methodology in `retrieval_benchmark.py`.

## Next critical steps (strategically consequential order)

1. **Measure the domain abstention curve** on the frozen ruler (extend the D-312 sweep to the
   `domains` axis; percent_rank margin). Do NOT transplant discipline/content_type curves.
2. **Add a `domains` operating point** to `ABSTENTION_CALIBRATION` + `abstention_policy`, gated
   (`enabled: false`), with a shadow-run receipt before any flip (D-339 rule).
3. **Owner finalizes `D2D_DOMAIN_REVIEW_20261008.csv`** (`owner_final_domain`), then fold back into
   `discipline_domain_map.yaml` as one mint mirroring D-2870/D-2872.
4. **BUG-238 corpus remediation** (341 model_medium + 332 model_high bands) — after (1)–(2) land.
5. **Re-run S4 + A/B** against the now-consistent 208-authority.

## Owner gates (awaiting owner decision)

- Ratify the domain ruler as the canonical frozen reference for the `domains` axis.
- Approve the "extend D-312/D-349, never transplant" direction (no new framework).
- Confirm the D2D map remains a fallback prior (no override of content-driven domains).
