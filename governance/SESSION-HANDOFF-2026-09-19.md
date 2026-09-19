# SESSION HANDOFF — 2026-09-19 (ontology / retrieval / serving-gate)

> **Read this file first, then `governance/CONTEXT_INDEX.md` §6e, then
> `governance/ROUNDTABLE_CROSSEXAM_20260919.md`.** Commit at handoff: **937e559** on `origin/main`.
> Registry 639 decisions · buglog 50 entries / highest **BUG-301** · working-tree drift 0 (tracked).

---

## 0. TL;DR — the one thing to carry forward

**The serving gate is a LABEL, not a verification verdict.**

`scripts/apply_phase1_finalize.py:18` sets `status = 'PASS' if content_type == 'principle' else 'QUARANTINE'`
and writes it at `:163`. The live DB matches that rule on **4,745/4,745 PASS rows and 0/1,470 non-principle
rows**. Measured against `verification_results` (populated on **7,995/7,995** rows):

| measurement | value |
|---|---|
| `status` disagrees with its own persisted `verification_results[factual].passed` | **2,447 (30.6%)** |
| PASS rows whose own verification says `passed = False` | **1,941** |
| — NLI **CONTRA-majority** (contradicted, being served) | **138** |
| — NLI **NEUTRAL** (unverified, being served) | **1,514** |
| — all evidence flagged non-evidence fragments (served) | **278** |
| — MECH FAIL / BUG-181 conversion artifacts (served) | 11 |
| QUARANTINE rows that are NLI **ENTAIL-majority** (verified, hidden) | **506** |
| honest gate (`status := factual.passed`) | PASS **4,745 → 3,310** (net −1,435) |

Three consequences, in order of importance:

1. **ROLE is the highest-leverage axis, not a decorative one.** D6, BUG-280 and D272g are **inverted**. The
   gating axis is the one with **lift −0.010 over a constant answer** (0.740 vs a 0.750 baseline) on a column
   that is 81.6% one value — a gate that admits nearly everything and refuses nothing.
2. **Every retrieval/label number produced before this is fixed is uninterpretable.**
3. **Next action is `0a` / G17** — re-derive `status` from the verification record. ~1 engineer-day, no human,
   no model calls, deletes nothing (R-D410). Nothing else on the board has comparable leverage.

---

## 1. What happened this session (chronology, so the plot is not lost)

1. Started from the state of 2026-09-17/18: the 150-row blind ruler was certified, the ontology forensic
   (§1–§12) and the second pass (§13) were written, D-272/D-273 were ruled, BUG-278…BUG-294 logged, the
   market research and roundtable masterprompt were published, and a fetched reference library
   (45 entries, 40 DOI-verified) was built and pushed (`76d72c9`).
2. **Three frontier reviews were returned** against the masterprompt — `temp/qwen0080.md` (145 lines,
   derivative), `temp/chatgpt0080.md` (1,786 lines, best architecture/market), `temp/claude0080.md`
   (253 lines, best verification — cloned the repo and checked source).
3. **Each load-bearing claim was re-derived against the repo or the live DB**, not summarised. In doing so
   a claim none of the three had made was found and confirmed: the serving gate. That reframed the whole
   diagnosis and invalidated two of my own prior claims.
4. Corrections to my own instrument were logged (BUG-295…BUG-301), new decisions D274a–h were recorded,
   gates G17–G20 opened, G4a withdrawn, G13 superseded, and the programme was re-ordered so that a
   *correctness* fix precedes the labelling fix.
5. Everything was pushed as `937e559`, and all dependents were synchronised in this session (see §9).

---

## 2. Round-2 adjudication — what to take from each review, and what to ignore

### Claude — 10/10 load-bearing claims confirmed; the strongest review
| claim | verdict |
|---|---|
| D11 "confirmed, worse": `search_keyword` receives **no query text** (`retrieve.py:123-134`); called only when a facet is present (`:363-370`); its insertion-ordered rows get **equal RRF weight** (`:355-390`); the rerank pool is cut from the fused list (`:411-415`) | **CONFIRMED**, and it is bigger than the filter complaint: a facet-bearing query is partly answered by the *first-N-inserted* rows carrying the facet |
| D12 is a category error → **split the guard**, don't exempt it | **CONFIRMED and better than G13** → adopted as G18 |
| the `verifier_model` stamp is a hardcoded literal | **CONFIRMED** (`stage5_verify.py:898`) |
| the QUARANTINE split is a **parse, not a re-run**; 8+ causes | **CONFIRMED** (0 empty rows; 5 cause branches) |
| `catch_all: emerging` is by design | **CONFIRMED** (`taxonomy_v5.yaml:2131-2132`) |
| D19 — the per-class table is grouped by the **human** label, so "precision" is recall of the stored labeller | **CONFIRMED in direction** (my count: 13 stored-principle→human-non-principle; **29** human-principle→stored-non-principle) |
| **D3 REFUTED** — the pocket contrasts are not significant | **CONFIRMED: I over-claimed** |
| `min_human_share` is a **provenance share**, not an accuracy floor | **CONFIRMED — my instrument's defect** |
| the golden ids were chosen from live search output | **CONFIRMED verbatim** in `config/golden/retrieval_queries.yaml` |

**Its gap:** it found that `verification_results` is a fully-populated per-row verdict sitting next to a
`status` that need not agree — then marked *"where a non-principle role becomes QUARANTINE"* as
`[UNVERIFIED]`. **The disagreement was the finding.** Still unverified and to be checked before reliance:
its claim of a second label path (`_merged_classification`) and the xgrammar/Harmony empty-content note at
`omlx_call.py:401-405`.

### ChatGPT — best on architecture and market; weakest on verification
- **Take:** the destination architecture (per-axis classifiers → ontological challenger → NLI → structural
  validator → decision engine; **no single LLM call authoritative**; ABSTAIN is a success; optimise
  accuracy|accepted while monitoring coverage); the state model `VERIFIED/UNVERIFIED/CONTRADICTED/
  VERIFICATION_ERROR` **with retrieval eligibility as a separate dimension**; its market additions, above
  all **TaxoClass** (zero-shot hierarchical multi-label from class names + entailment — the single most
  relevant external work for R1/R5) and **confidence-constrained clustering** (must-link/cannot-link → work
  identity).
- **Reject:** "D3 CONFIRMED" (it replicated my error without an interval test); "D6 CONFIRMED — the
  retrieval path does not meaningfully use ROLE" (inverted — ROLE *is* the gate); "stage 5 does not preserve
  the NLI distinction" (it does; it is never *queried*).
- **Premise wrong:** it reasons as if no human is available. The user **is** the coder and has already
  produced 150 blind labels. There is no *second* coder — that is all.

### Qwen — derivative; two category errors
18 "CONFIRMED" rows restating my own findings with no re-derivation; the same D3 error. **Reject:**
"Outlines/guided generation *replaces* R1/R2" — constrained decoding enforces *membership*, not *semantic
correctness*; adopt it as a structural guard only. "RAGAS/ARES replace the ruler" — they measure
retrieval/answer quality, not whether a discipline label is right.

### Consensus all three reached (act on it)
Retrieval correctness precedes label repair · `emerging` must never be a facet value · the write guard must
be **split**, not exempted · graph neighbours carry their **own** tier · relevance is a versioned sidecar
outside `fb_id` · FTS the body before embedding it · retire the alias map to a drift ledger · R5 → R1 → R2 ·
every prior retrieval number measured an unconstrained system · don't tune RRF weights at n=30.

---

## 3. Corrections to prior beliefs — READ THIS BEFORE TRUSTING ANY OLD ARTEFACT

These are the derailment points. Older documents in this repo assert the opposite; the newer documents
(the ones listed in §9) supersede them.

| prior belief (still written in older artefacts) | current truth |
|---|---|
| "ROLE is decorative" / D6 / BUG-280 | **INVERTED.** ROLE is the only serving gate |
| the ruler has a 0.60 accuracy floor; discipline "FLOOR_UNRESOLVED" | **VOID.** `min_human_share` is a *provenance share*; the FLOOR column compared two estimands (BUG-295). Only the constant-baseline lift stands |
| F-14 was retargeted to ROLE on a pocket contrast | **WITHDRAWN.** Both contrasts are statistically null (BUG-296) |
| "QUARANTINE conflates NEUTRAL and CONTRA in the stored state" | **PARTLY WRONG.** `verification_results` preserves the three-way detail on 100% of rows; it is never *queried*. And stage5 already computes a 4-tier `epistemic_status` that stage6 has no column for (BUG-301) |
| "a filter filters" | **FALSE.** FTS/vector legs never receive the facet, and the one leg that does is query-blind (BUG-285/300) |
| "the 40.7% quarantined is invisible" | **Inconsistently visible** — graph expansion re-admits it (BUG-287) |
| "the KB is clean / the golden set is verified" | the golden ids were chosen from **live search output** (circular) |
| "the D-2637 model eval blocks progress" | **NOT on the critical path** |
| "we need ~85 more ruler rows" | **Value-of-information ≈ 0** — the decision does not change at 0.51 vs 0.55 |

---

## 4. Current priority order (and what is excluded)

**0a** G17 serving gate from the verification record → **0b** G12 facet predicate in every leg + assert on the
fused pool → **0c** G18 guard split → **1** G19 persist the tier + de-literal the verifier stamp →
**2** correct the ruler estimand → **3** R5 → R1 (driven by the decision procedure the config already
declares) → **4** G15 index what is already in the DB → **5** G14 work-identity dedup → **6** S5 aggregation
fix (claim-level) → **7** G16 chunk/evidence leg → **8** distilled classifier.

**Excluded (do not spend on these):** re-labelling the corpus; ~85 more stratum-A rows; **training/
fine-tuning or swapping S2/S4 on the current labels**; extending the alias map; ACORN; re-cutting the 61/43
ontology; re-deriving FORM on the pocket; the chunk leg / `vec_fbs_ctx` / contextual embeddings / HyDE /
weighted RRF before 0a–0b; R2 before R5/R1; deleting the junk rows; the D-2637 workstream.

**The anchor question, answered:** build a **versioned human-adjudicated conformance set**, not a training
set — ANCHOR-1 (the frozen 150 blind rows with their 51 abstentions), ANCHOR-2 (~100 fresh rows drawn after
the vocabulary freeze), a 30-row test–retest as the single-coder ceiling, per-axis
positive/near-neighbour/OOV/contradiction sets, must-link pairs for work identity, and known-item queries
derived from `source_segments`. **The "different approach" is not a different model — it is removing the
LLM's authority over what the config rules already decide** (`content_types.yaml` §`content_type_rules`
D2587 + `route_to_content_type` D2128, neither implemented). Fine-tuning is step 8, on a held-out anchor
version, once the gate is honest.

**RRF / chunking, answered:** RRF is already correct (k=60, 1-based, three legs) — nothing to adopt,
something to *feed*; a **leg** is broken, not the fusion. Chunking is worth adopting at **step 7**: the
`source_segments` join is **100% (205,813/205,813)**, cost ≈214k vectors ≈ 438 MB, each hit returning
verbatim source + section heading + a parent-FB link.

---

## 5. Open human gates

**New this session:** **G17** (re-derive status from the verification record — de-serves 1,941 rows, deletes
nothing) · **G18** (guard split, replaces G13) · **G19** (persist the tier + withdraw the FLOOR estimand) ·
**G20** (one writer for status + audit stamp).
**Withdrawn:** **G4a** (floor repointing — the estimand is confused and a floor may not be re-anchored on a
single coder), **G13** (superseded by G18).
**Still open from before:** G1, G2, G3, G5, G6, G7, G8, G9, G10, G11, G12, G14, G15, G16 — see
`CONTEXT_INDEX.md` §7.

**Offered and not yet taken up:** a one-line addition to the PROTECTED `AGENTS.md` `<knowledge_sources>`
block pointing at `governance/REFERENCE_LIBRARY_20260919.md` and this handoff.

---

## 6. Do-not-quote list (additions this session)

1. **"the 0.60 floor"** — two estimands, one number (BUG-295).
2. **"F-14 was retargeted to ROLE"** — the contrast is null (BUG-296).
3. **any PASS-only frame as an epistemic frame** — PASS is a ROLE frame (BUG-299).
4. **the golden retrieval set as ground truth** — its ids were chosen from live search output.

## 7. Measurements explicitly recorded as REFUTED (do not re-run)

FTS staleness (integrity-check passed) · label-poisoned production embeddings (`contextual_embed.enabled:
False`) · over-merge causing unlabelability (singletons are ~3× **more** unlabelable) · the F-14 pocket
contrast (null) · "the `%research%` LIKE probe is 66% noise" (withdrawn — the probe used a partial string;
with a full canonical label the LIKE filter is exact).

---

## 8. Where everything lives

| need | artifact |
|---|---|
| the round-2 adjudication + full evidence | `governance/ROUNDTABLE_CROSSEXAM_20260919.md` |
| the ontology forensic (2 passes) | `governance/ONTOLOGY_FORENSIC_20260919.md` |
| the certified ruler + measurement | `governance/ruler_measurement_20260917.md` / `.json`, `RULER_BLIND_SHEET_20260917.csv` |
| the market research (ranked, with DOIs) | `governance/MARKET_RESEARCH_ONTOLOGY_20260919.md` |
| the bibliography (45 entries, DOI-fetched) | `governance/REFERENCE_LIBRARY_20260919.md` + `config/references.yaml` |
| the prompt for the next round | `governance/ROUNDTABLE_MASTERPROMPT_ONTOLOGY_20260919.md` (PART 7 = round-2 premises, Q10) |
| the live register / priority / sequence | `governance/PRIORITY_REGISTER_20260917.md`, `SEQUENCE_STATUS_20260917.md` |
| the recall map + gate register | `governance/CONTEXT_INDEX.md` (§6e, §7) |
| the machine decision registry | `config/decisions.yaml` (639) · `DECISION-LOG.md` · `MASTER-TASK-REGISTER.md` |
| the bug register | `governance/buglog.md` (50 entries, highest BUG-301) |

## 9. Synchronised in this session

`config/decisions.yaml` (639, summary recomputed) · `DECISION-LOG.md` (D-272/273/274 in the D2552 table
format; header 611→639) · `governance/buglog.md` (BUG-295…BUG-301) · `config/eval_integrity.yaml` (estimand
correction) · `governance/CONTEXT_INDEX.md` (§6e + gates G12–G20, G4a withdrawn) ·
`governance/SEQUENCE_STATUS_20260917.md` (D-274 RULED) · `governance/PRIORITY_REGISTER_20260917.md`
(re-ranked, G4 done → 0a first) · `MASTER-TASK-REGISTER.md` (superseding MUST entry at the top) ·
`agent/session_seed.yaml` (`current_state` block) · `governance/ONTOLOGY_FORENSIC_20260919.md` (2 stale
citations fixed).

## 10. Hazards / unfinished business

- **`tools/*.py` and `tests/test_axis_authority_consolidation.py` are deliberately UNCOMMITTED** (concurrent
  D-2637 model-eval workstream). Do not sweep them into an unrelated commit.
- **Run A of the tier-A eval is dead** (PID 70847 gone, checkpoint frozen at ~4,260 rows / 1,044 in the log).
  Decide resume vs abandon. It is **not** on the critical path.
- **BUG-276 stands: there is NO automated DB backup** (`backup_guardian.sh` is dead). **Run one before 0a**,
  which is a bulk write to `status` even though it deletes nothing.
- **F-08 disk**: ~46 GiB free against a 150 GiB floor.
- **The DB is gitignored** — a re-clone will not reproduce any measurement in this handoff. Snapshot before
  and after 0a and record both in the artifact.
- **Stale artefacts to be careful with:** anything asserting that ROLE is decorative, that a 0.60 accuracy
  floor exists, that the golden set is verified, or that QUARANTINE is invisible. §3 is the correction list.

## 11. First three actions next session

1. **Back up the DB** (BUG-276), then implement **0a / G17**: one writer for `status`, derived from
   `verification_results` + a typed `s5_reason`; label-derived status writes become hard errors; add the CI
   invariant. Snapshot before/after and record both distributions. Expected: PASS 4,745 → 3,310.
2. **Re-measure the constraint-violation rate** (target exactly 0, not "low") over every discipline × ≥10
   queries, before and after 0b — this is the first number that means what it says.
3. **Correct the ruler's estimand** (G19) and re-publish the measurement with the constant-answer baseline,
   coverage and abstention bounds beside every accuracy.
