# PRIORITY REGISTER — the critical items in strategically consequential order (2026-09-19, revised)

Ranked by **consequence**, not by effort or recency. Each row names what it unblocks and whether a human is
required. Companion to ROUNDTABLE_CROSSEXAM_20260919.md (which re-ordered the programme),
SEQUENCE_STATUS_20260917.md (which records the rulings) and CONTEXT_INDEX.md (the recall map).

> **WHAT CHANGED ON 2026-09-19.** G4 — "certify the ruler" — was #1 and is **DONE** (150 blind human labels).
> The ruler then surfaced a defect that outranks every item on the previous list: **the serving gate is a
> label, not a verification verdict** (BUG-299 / D-274a). 4,745/4,745 PASS rows are content_type='principle';
> 2,447 rows (30.6%) disagree with their own persisted verification; 1,941 failed rows are served, 506
> verified rows are hidden. **Every measurement taken before this is fixed is uninterpretable**, so 0a is
> now #1. G4a (repointing the floors) is **WITHDRAWN** — the estimand was confused (BUG-295).

| # | item | type | unblocks | human? | effort |
|---|---|---|---|---|---|
| **0a** | **G17 — make status a function of the verification record** (one writer; typed s5_reason; label-derived writes become hard errors; CI invariant PASS ⟹ factual.passed). Measured effect: serving set **4,745 → 3,310**; de-serves 1,941 rows (138 NLI CONTRA-majority, 1,514 NEUTRAL, 278 evidence-flagged, 11 MECH/artifact); restores 506 verified rows. Deletes nothing (R-D410) | task | **everything measurable** — every retrieval number, every label accuracy claim, every benchmark frame | no | ~1 day |
| **0b** | **G12 — the facet predicate in EVERY leg + asserted on the fused pool**; delete/rewrite the query-blind keyword leg (retrieve.py:123 has no query param, :363-370 calls it only when a facet is present, :411-415 cuts the rerank pool from the fused list) | task | correctness of facet-constrained retrieval; the whole chunk/embedding roadmap | no | ~1.5 days |
| **0c** | **G18 — SPLIT the write guard** (row-level guard vs vocabulary lint) — replaces the G13 exemption list | task | R1; and the 261 research-methodology rows currently destroyed at the write boundary | no | ~0.5 day |
| **1** | **G19 — persist the tier stage 5 already computes** (epistemic_status / isor / verification_method; stage6 has no columns) + de-literal the verifier stamp (stage5_verify.py:898) | task | the QUARANTINE split (R3) as a wiring job instead of a modelling job | no | ~0.5 day |
| **2** | **Correct the ruler estimand** — the FLOOR column compares stored-label accuracy to min_human_share, a provenance share. Re-report lift over the constant baseline (ROLE −0.010, discipline +0.422, FORM +0.472) with coverage and abstention bounds | task | the validity of every accuracy number the project publishes | no | ~0.5 day |
| **3** | **R5 → R1** — the vocabulary contract, then closed-menu classification driven by the decision procedure config/content_types.yaml ALREADY declares (content_type_rules / D2587), with none as a first-class outcome and a menu_hash stamp | task | label quality; retires the 999-rule alias map | **YES** (ratify the slot list) | 2–3 days |
| **4** | **G15 — index what is already in the DB** (body fields into FTS first; evidence_passages as a fourth leg; per-field vectors later) | task | retrieval coverage (11.1% of each FB is searchable today; 4.8M chars of evidence indexed by nothing) | no | ~1 day |
| **5** | **G14 — work-identity dedup at ingestion** (source_diversity counts filenames: 29.1% of "convergence" is one book twice; it feeds the S1.5 merge criterion) | task | corpus integrity; the merge criterion | **YES** | 1–2 days |
| **6** | **S5 aggregation fix** — claim-level (every atomic claim needs ≥1 supporting passage) against the single-passage-vs-synthesised-definition premise; then measure a claim-level checker behind a protocol | task | the meaning of PASS; the 27.4%/31.1% PASS rates | no | 2–4 days |
| **7** | **G16 — chunk/evidence leg** (join is 100%: 205,813/205,813; ~214k vectors ≈ 438 MB), plus per-field vectors and weighted RRF | task | grounding precision — but only after 0a–0b | no | ~2.5 days |
| **8** | **Distilled classifier / fine-tune** — only with an honest gate AND an anchor (D-274f); measured on a held-out anchor version | task | a cost optimisation, not an accuracy strategy | no | days |
| **9** | **BUG-276 — restore the safety net** (C13 backup_guardian.sh is dead; no automated DB backup) + F-08 disk | bug | safe execution of every bulk write above | no | hours |
| **10** | **Decision queue** — ratify D-271a (revised), D-271b/c, D-G2a/b, D-G3a/b, G1, G5–G7, G17–G20 | decision | items 0a–3 (they are blocked on paperwork, not work) | **YES**, minutes each | minutes |

## Explicitly EXCLUDED (do not spend on these)

Re-labelling the corpus; buying ~85 more stratum-A rows (**value-of-information ≈ 0** — the decision does
not change at 0.51 vs 0.55 and the estimand is void); **training/fine-tuning or swapping S2/S4 on the
current labels** (no provenance column exists, so min_human_share is unsatisfiable — D-274d); extending the
alias map; adopting ACORN; re-cutting the 61/43 ontology; re-deriving FORM on the pocket (the F-14 contrast
is statistically null — BUG-296); the chunk leg / vec_fbs_ctx / contextual embeddings / HyDE / weighted RRF
before 0a–0b; R2 before R5/R1; deleting the junk rows (R-D410). **The D-2637 model-eval workstream is NOT on
the critical path.**

## Which is the most important

**0a — G17.** One sentence: *the set of objects the system will answer from is currently decided by a
content_type value written by a hand-run script, on an axis whose lift over a constant answer is −0.010, and
that set contains 138 rows that NLI has already contradicted.* Until status is derived from the verification
record, nothing else in this table can be measured — and each additional artefact produced before it
compounds the error, which is the documented mechanism of the circling.

## What must NOT be trusted until 0a lands

Any retrieval benchmark number; any "the KB is clean" claim; the F-14 retarget (withdrawn); the 0.60 floor
(withdrawn); any PASS-only frame (it is a ROLE frame, not an epistemic one); any accuracy number compared to
a floor rather than to the constant-answer baseline; and the golden retrieval set whose expected ids were
chosen from live hybrid search output.
