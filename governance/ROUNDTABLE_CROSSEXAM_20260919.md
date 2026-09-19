# ROUNDTABLE CROSS-EXAMINATION + STRATEGIC VERDICT (2026-09-19)

**Scope.** Three independent frontier reviews were returned against
`governance/ROUNDTABLE_MASTERPROMPT_ONTOLOGY_20260919.md`:
`temp/qwen0080.md` (145 lines), `temp/chatgpt0080.md` (1,786 lines), `temp/claude0080.md` (253 lines).
Every load-bearing claim was re-derived against the repository or the live DB before it was
accepted. **This document is the adjudication, not a summary.**

Corpus at time of writing: `knowledge pipeline/maxwell.db`, 7,995 fbs, status PASS 4,745 /
QUARANTINE 3,250, content_type='principle' 6,525. All measurements read-only.

---

## 0. HEADLINE — the finding none of the three reviews reached

All three reviews assumed `status` is the output of Stage 5. **It is not.**

```
scripts/apply_phase1_finalize.py:18
    status = 'PASS' if content_type == 'principle' else 'QUARANTINE'
scripts/apply_phase1_finalize.py:163
    "UPDATE fbs SET content_type=?, depth=?, status=?, needs_human_review=? ..."
```

The observed data matches that rule with 100% fidelity: **4,745 of 4,745 PASS rows are
content_type='principle', and 0 of 1,470 non-principle rows are PASS.** The identity is exact in
the live DB and in the 2026-09-17 backups.

**The retrieval eligibility gate is a LABEL, not a verification verdict.** Measured consequences:

| measurement | value |
|---|---|
| rows where stored `status` disagrees with the persisted `verification_results[factual].passed` | **2,447 (30.6%)** |
| PASS rows whose own persisted verification says `passed = False` | **1,941** |
| — of those, NLI **CONTRA majority** (contradicted, served) | **138** |
| — of those, NLI **NEUTRAL** (unverified, served) | **1,514** |
| — of those, **all evidence flagged non-evidence fragments** | **278** |
| — of those, mechanism-quality **FAIL** | 9 |
| — of those, **BUG-181#1 conversion artifacts** | 2 |
| QUARANTINE rows whose NLI verdict is **ENTAIL majority** (verified, hidden) | **506** |
| honest gate ablation: `status := verification_results[factual].passed` | **PASS 4,745 → 3,310 (net −1,435)** |

Three hand-run scripts move rows across the gate on label grounds alone:
`apply_phase1_adjudication.py` ("principle -> keep principle, un-quarantine (status=PASS)"),
`apply_phase1_finalize.py`, `repass_pair_agreed.py`. Nothing in `pipeline/` links PASS to
content_type — the gate was established, and is still moved, outside the pipeline.

**Why this is the whole story.** The axis that decides what is retrievable is the axis measured at
**0.740 against a constant-answer baseline of 0.750 — lift −0.010 (no better than always answering
'principle')**, and the axis that Claude's D19 shows is mis-grouped. And 81.6% of the KB carries the
gate value, so the gate is close to a no-op that admits almost everything and refuses nothing.

Two of my own prior claims are corrected by this: **D6/BUG-280 ("ROLE is decorative") is inverted —
ROLE is the only gate.** And **D272g's F-14 retarget is withdrawn** (§3).

---

## 1. Cross-examination — Claude (`claude0080.md`)

The strongest of the three: it cloned the repo, read source, and volunteered three claims it could
not verify. Six of its load-bearing claims are exact.

| # | claim | verdict | evidence |
|---|---|---|---|
| C1 | D11 "confirmed, worse": `search_fts`/`search_vector` receive no facet; `search_keyword` receives **no query text** and orders by `borp_score` (all 0.0 → rowid order); with a filter, RRF leg 3 is a query-blind, insertion-ordered list credited 1/(60+rank); the rerank pool is cut from the fused list so violators can be promoted | **CONFIRMED, exactly** | `retrieve.py:123-134` — signature has no `query` param. `:363-370` — leg called only when a facet is present. `:355-390` — equal RRF credit for all three legs. `:411-415` — `pool = [fb_map[fid] for fid in ranked_ids[:pool_size]]`. `borp_score` avg 0.0 over 7,995 rows; `ranking.quality_score_enabled: false` |
| C2 | D12 is a category error: a vocabulary lint inside a row guard; fix = **split the guard**, not an exemption | **CONFIRMED and better than G13** | the collision check is name-overlap of two vocabularies; the `DECLARED` flag is still returned; callers treat any non-empty list as reject |
| C3 | D9: `verifier_model` is a hardcoded literal that lies after any config change | **CONFIRMED** | `stage5_verify.py:898`: `vfb["verifier_model"] = "DeBERTa-v3-large (D2322 calibrated, threshold 0.10)"` |
| C4 | D4 partly refuted: the NEUTRAL/CONTRA split is a **parse, not a re-run**, and QUARANTINE has 8+ causes, not 2 | **CONFIRMED** | `verification_results` populated on **7,995/7,995** rows (0 empty). `_b2_majority_verdict` emits `ENTAIL (majority…)`/`CONTRA (majority…)`/`NEUTRAL (ent …)`. Cause branches at `:811-843` (S4-fail, BUG-181#1 contamination, MECH FAIL, dual-encoder error) |
| C5 | D16 is by design: the taxonomy defines the sentinel as a facet value | **CONFIRMED** | `taxonomy_v5.yaml:2131-2132` `catch_all_domain/discipline: emerging` |
| C6 | D19: the per-class table is grouped by the **human** label, so "precision" is recall of the stored labeller; 24 of 34 human-principle stratum-B rows carry a non-principle stored role | **CONFIRMED in direction** (my independent count over all 150: 13 stored-principle→human-non-principle, **29** human-principle→stored-non-principle) | ruler key × sheet |
| C7 | D3 **REFUTED as stated** — the pocket contrasts are not significant | **CONFIRMED — my claim was over-stated** | my own numbers: content_type traceable 46/67=0.687 [0.568,0.785] vs untraceable 47/83=0.566 [0.459,0.668]; FORM traceable 48/61=0.787 vs untraceable 55/67=0.821. CIs overlap heavily in both directions |
| C8 | Q5: `min_human_share: 0.60` is a **human-provenance share** gate; the ruler compares an **accuracy** to it | **CONFIRMED — and it is my instrument's defect** | `eval_integrity.yaml:28-31` "Minimum share of labels that must come from a HUMAN-authoritative source before the axis may be used as ground truth for a MODEL comparison. A floor is a gate for the retrain, not a blocker for reading the axis." `score_ruler_labels.py:136` `floors = cfg.get("min_human_share")`, `:184` `floor = float(floors.get(axis, 0.0))` |
| C9 | Q9: `retrieval_benchmark` calls `search_hybrid` with no facets, and the golden ids were chosen from the live system's own output | **CONFIRMED, verbatim in the repo** | `config/golden/retrieval_queries.yaml` header: "verified to be the semantically-correct answer via live hybrid search BEFORE locking them in" |
| C10 | my cited line numbers `stage4_merge.py:341/472` are stale (`:345/468` at HEAD) | **CONFIRMED** | repo |

**Where Claude over-reaches or stops short.**
- It treats "five repairs suffice" as wrong because retrieval defects sit outside the five. Fair as
  bookkeeping; but the five were *labelling/instrument* repairs, and it does not show they are wrong.
- **D4 is right on the parse and one step short of the answer.** It explicitly marks "where a
  non-principle role becomes QUARANTINE" as **[UNVERIFIED]**. That code is not in stage5 at all —
  it is `apply_phase1_finalize.py:18` (§0). Having found that `verification_results` is a
  fully-populated per-row verdict sitting next to a `status` that need not agree with it, the
  disagreement itself was the finding.
- Two claims I could not verify: the second label path (`_merged_classification`) and the
  xgrammar/Harmony empty-content note at `omlx_call.py:401-405`. Both are marked **[UNVERIFIED]**
  here and must be checked before they are relied on.
- Its "accepted" `epistemic_status` proposal is already implemented and then dropped: stage5
  computes `epistemic_status ∈ {corroborated, source-supported, cross-source-unverified,
  speculative}` — the exact tier vocabulary its R3 asks for — and `epistemic_status`,
  `verification_method` and `isor` **are not columns in the DB**. R3 is a schema+wiring fix.

## 2. Cross-examination — ChatGPT (`chatgpt0080.md`)

Best on architecture and on market breadth; weakest on verification. It confirms D1/D5/D7/D8/D11/
D13/D16/D17/D18, all of which I independently confirm.

| # | claim | verdict | note |
|---|---|---|---|
| G1 | **D3 CONFIRMED** (FORM fine, ROLE degrades in the pocket) | **WRONG** | accepted my claim without an interval test; §1-C7 refutes it |
| G2 | **D6 CONFIRMED**, "the production retrieval path does not meaningfully use ROLE ... I would not delete the role ontology" | **INVERTED** | ROLE *is* the gate (§0). The conclusion ("keep the ontology") is right, the reason is not |
| G3 | "stage 5 computes all three NLI scores but the persistent state does not preserve the distinction" | **PARTLY WRONG** | the distinction **is** preserved in `verification_results` on 100% of rows; it is never *queried*. Projection problem, not persistence |
| G4 | its state model `VERIFIED / UNVERIFIED / CONTRADICTED / VERIFICATION_ERROR` + separate `retrieval_eligibility` | **CONFIRMED as design; cheap** | S5 already computes 4 tiers (G3/C10); the split is a projection + a schema column |
| G5 | "D2 ceiling ≈0.61 is not a statistical ceiling" | **CONFIRMED as a correction to my wording** | it is the observed agreement where the stored label was emitted verbatim, i.e. the easiest rows |
| G6 | its revised single-operator architecture: axis classifiers → ontological challenger → NLI → structural validator → decision engine, **no single call authoritative**, ABSTAIN a success, optimise accuracy|accepted over coverage | **CONFIRMED as the right destination** | matches where the project must land; see §6 for the two corrections |
| G7 | tax: `content_type` / `depth` / `extraction_type` should be rule-driven, not LLM-judged | **CONFIRMED and already written** | `config/content_types.yaml` §`content_type_rules` (D2587) *is* the decision procedure: top-down rules, `depth_test_domains_threshold: 3`, `descriptive_summary_resolution: noise_drop`, `ambiguous_resolution: quarantine`. It is not implemented as code |
| G8 | market: TaxoClass, ARES, RAGTruth, FActScore, SetFit, confidence-constrained clustering, taxonomy-aware embedding evaluation | **ACCEPTED, real additions** | TaxoClass (zero-shot hierarchical multi-label from class names + entailment) is the most relevant external work for the label problem; must-link/cannot-link is directly applicable to work-identity dedup |
| G9 | "you are the sole operator and will not use human annotation" | **PREMISE PARTLY FALSE** | the user IS the coder and has already produced 150 blind labels with abstentions. No *second* coder is available; a first coder is |

Its two structural misses: the gate, and it never questions the floor estimand (it repeats
"0.60" as a governance floor without noticing the confusion of estimands).

## 3. Cross-examination — Qwen (`qwen0080.md`)

The shortest and the most derivative: 18 rows of "CONFIRMED" that restate my own findings without
re-deriving any of them, plus the same D3 error as ChatGPT. What is usable:

| # | claim | verdict |
|---|---|---|
| Q1 | **D3 CONFIRMED** | **WRONG** (§1-C7) |
| Q2 | D10 "partially confirmed" — the five repairs ignore the retrieval defects | fair; same conclusion as the other two |
| Q3 | ordering: retrieval constraints before label repair | **CONFIRMED** |
| Q4 | sqlite-vec cannot take predicates efficiently without ACORN-like extensions → over-fetch then strict post-filter | **CONFIRMED mechanically**, and consistent with the schema: `vec_fbs`/`vec_fbs_ctx` are `vec0(definition_embedding float[512])` with **no metadata and no partition columns**, so the only in-scan mechanism is a rowid-IN subquery (Claude's correction) — the robust fix does not depend on which is true (over-fetch + assert on the pool) |
| Q5 | abstention is unmeasured and the denominator is biased | **CONFIRMED, and Claude quantified it better**: blank=wrong 42/100 → blank=right 59/100, i.e. discipline ∈ **[0.42, 0.59]** |
| Q6 | "Outlines/guided generation replaces R1/R2" | **OVER-REACH** — constrained decoding enforces *membership*, not *semantic correctness*; it cannot detect that the FB does not belong to the chosen label. Adopt as a structural guard, never as the verifier |
| Q7 | "RAGAS/ARES replace ad-hoc ruler metrics" | **CATEGORY ERROR** — RAGAS/ARES measure retrieval/answer quality, not whether a discipline label is correct. They cannot replace the ruler |
| Q8 | market claims marked `[UNVERIFIED arXiv ID]` | honest; un-retrieved |

## 4. Consensus (all three agree, and all three are right)

1. Retrieval correctness precedes label repair. 2. `emerging` must never be a facet value →
NULL + a status enum. 3. `research methodology` must not be destroyed at the write boundary
(Claude's guard-split is better than an exemption). 4. Graph expansion must return the neighbour's
**own** tier. 5. Relevance is relational → a versioned sidecar keyed by `fb_id`, never inside the
hash. 6. FTS the body fields before embedding the body. 7. Retire the 999-rule alias map to a
read-only drift ledger. 8. The written decision procedure precedes any relabel or verifier upgrade
(R5 → R1 → R2). 9. Every prior retrieval number is a measurement of a system that did not enforce
its own specification. 10. Do not tune RRF weights at n=30.

## 5. Adjudicated disagreements

| question | Qwen | ChatGPT | Claude | ruling |
|---|---|---|---|---|
| is the pocket contrast real? | confirm | confirm | refute | **Claude.** Not significant in either direction. Do not re-derive FORM — but for the *right* reason: FORM is already the best-measured axis, not because the pocket is clean |
| repair order | retrieval first | retrieval first, then R5→R1→R2 | free parse + D11 first, then R5→R1→R4, R2 conditional | **Claude, with the gate inserted at step 0** |
| primary verifier | add a second | demote DeBERTa, promote a second LLM | keep DeBERTa behind a protocol, fix the **aggregation** | **Claude.** The measured failure is the premise (single passage vs synthesised definition: 27.4% single-source / 31.1% convergent PASS in the 2026-09-03 e2e). Fix the aggregation, then measure a claim-level checker. Adding a second LLM verifier first multiplies a defect and doubles cost |
| constrained decoding | adopt as R1/R2 replacement | adopt with `none` as an enum member | adopt for non-reasoning models + permutation flip-rate test | **Claude/ChatGPT.** Structural guard only; menu rendered from `taxonomy_v5.yaml` at call time; stamp `menu_hash`; acceptance = flip-rate across shuffled menus |
| is a second human coder blocking? | yes | yes | yes (but proposes a cross-family LLM coder + test–retest as a $0 proxy) | **Claude's proxy.** The user is the only human; test–retest + a cross-family LLM coder gives an ambiguity map without a second person |

## 6. Corrections to my own record (BUGl-level, my instrument)

1. **BUG-295 (MEDIUM, mine):** the ruler compares stored-label **accuracy** to `min_human_share`,
   which is a **provenance share**. Two estimands, one number. The FLOOR column, the
   "STOPPED: decisive" / "CONTINUE: inside the margin" verdicts are void as stated. **The lift over
   the constant-answer baseline (BUG-269) survives and is the only valid reading**: ROLE −0.010,
   discipline +0.422, FORM +0.472.
2. **BUG-296 (MEDIUM, mine):** D272g's F-14 retarget is **withdrawn** (both contrasts null, §1-C7).
   The *action* survives on different grounds (FORM 0.831 is already the best-measured axis).
   D272g must be restated, not silently kept.
3. **BUG-297 (CRITICAL, mine):** D6/BUG-280 "ROLE is decorative" is **inverted** — ROLE is the only
   gate (§0).
4. **BUG-298 (MEDIUM):** the human-provenance gate is **unsatisfiable today**: there is no
   `content_type_source` / `discipline_source` column at all (only `primary_source`, a book field).
   So `min_human_share` cannot be computed on any axis, and per the config's own rule **no axis may
   be used as ground truth for a model comparison** — which is the state the config predicted.
5. Stale citations in the forensic (`stage4_merge.py:341/472` → `:345/468`) — correct in place.
6. The D2128 note in `content_types.yaml` says the `route → content_type` fallback "is now live —
   NOT dead". The `route` column **does not exist** in the live DB. Declared live, actually inert.

## 7. Strategic verdict

### 7.1 Is the runtime reliable to build on?
**The object model, the taxonomy structure and the RRF arithmetic are reliable. The two contracts
that connect them to the user are not, and the project has been measuring the wrong object.**
This is **instrument repair + two contract re-cuts**, not re-engineering (D272f stands). Effort
unchanged on the ontology (zero) and modest on retrieval/verification (2–3 days).

**Do not restructure the ontology.** All three reviews, the 150-row ruler and the D2587 decision
procedure agree it is not the bottleneck; re-cutting the 61+43 slots would invalidate the only
certified anchor you have.

### 7.2 What is critically first (the ordered programme, revised)

| step | work | why it is first | human? |
|---|---|---|---|
| **0a** | **Make `status` a function of the verification record.** One writer; recompute from `verification_results` + typed reasons; forbid label-derived status writes; CI invariant: `status='PASS' ⟹ factual.passed AND reason ∉ {CONTRA, MECH_FAIL, EVIDENCE_CONTAMINATED, NO_EVIDENCE}` | every other number is taken on a serving set whose membership rule is a label. Nothing measured before this means what it says | no |
| **0b** | **Facet predicate into every leg + assert on the fused pool**; delete or rewrite the query-blind keyword leg; feed the reranker the already-constrained pool | a leg can only add candidates; a filter must be able to *subtract* | no |
| **0c** | **Guard split** (row-level write guard vs vocabulary lint); separate the two | prerequisite for every relabel run; replaces G13's exemption list | no |
| **1** | **Persist the tier that already exists** (`epistemic_status`, `verification_method`, `isor`, typed `s5_reason`, `confidence_score` provenance) + fix the `verifier_model` literal | S5 computes it, stage6 drops it. R3 becomes a schema+wiring job | no |
| **2** | **Correct the ruler's estimand** and re-report: coverage, per-axis accuracy vs the constant baseline, abstention bounds, the gate crossed with the axis | the current report's FLOOR column is void | no |
| **3** | **R5 → R1** (vocabulary contract → closed-menu, decision-procedure-driven, `none` first-class, menu rendered from YAML with `menu_hash`) | only after the gate is honest can a relabel be measured | yes (ratify slots) |
| **4** | **Index what is already in the DB** (FTS the body fields, `evidence_passages` as a leg) | cheapest coverage win, no model risk | no |
| **5** | **Work-identity dedup** at ingestion (must-link) | 29.1% of "convergence" is duplicate filenames; it feeds the S1.5 merge criterion | yes |
| **6** | **S5 aggregation fix** (claim-level: every atomic claim needs ≥1 supporting passage), then measure a claim-level checker behind a protocol | the real verifier problem is the premise, not the model | no |
| **7** | chunk/evidence leg, per-field vectors, weighted RRF | all of it is premature before 0a–0b | — |
| **8** | distilled classifier / fine-tune | only with an anchor and an honest gate | — |

### 7.3 What NOT to do (priority-excluded, explicitly)

- **Do not re-label the corpus.** 3,000+ LLM calls into a gate defined by a script is the current
  state, not the fix.
- **Do not buy ~85 more stratum-A rows.** Value-of-information is zero: the decision (repair
  discipline) does not change at 0.51 vs 0.55, the floor estimand is void (BUG-295), and the ruler
  is contaminated for any row the R5 edit was derived from.
- **Do not fine-tune or train S2/S4 on the current labels.** `min_human_share` is unsatisfiable
  (BUG-298): zero labels carry human provenance. A model trained here learns the script's gate and
  the verifier's 0.48-F1 verdict.
- **Do not extend the alias map**, adopt ACORN, or build a new ANN for 8k×512d.
- **Do not touch the ontology** (61/43) and do not re-derive FORM on the untraceable pocket.
- **Do not add** the chunk leg, `vec_fbs_ctx`, contextual embeddings, HyDE or weighted RRF before
  0a/0b land.
- **Do not delete the noise_drop/quarantine rows** (R-D410; they are the audit trail).
- **Do not sequence R2 (NLI against label definitions) before R5/R1.** It inherits definition
  defects and its errors correlate with R1's, which will look like agreement.
- **Not the blocker:** the D-2637 model-eval workstream, the 4-bit/8-bit A/B, the Ornith benchmark,
  BUG-270/273/274/275/277, the domain-aggregation policy vote. All real, none on the critical path.

### 7.4 What must be re-engineered vs tested

| re-engineer (a contract, not a model) | est. | test (already sound) |
|---|---|---|
| the serving-gate contract: one writer, config-driven, verification-derived, invariant-tested | 1.0 d | the FB object model and `fb_id = sha256(name\|definition)` |
| the retrieval-predicate contract: no violating row may be returned by any leg, including rerank and graph | 1.5 d | RRF arithmetic (k=60, 1-based, correct) |
| the write guard: split lint from row-guard | 0.5 d | the taxonomy's structure (0 undeclared collisions) |
| the tier projection (persist what S5 already computes) | 0.5 d | checkpoint/resume (D2409) |
| the ruler's estimand + reporting rule | 0.5 d | the ruler *sheet* (blind, no stored labels exposed) |

### 7.5 The anchor — and why fine-tuning is not the next move

**You need an anchor. You do not need a training set yet, and you must not build one from the
current labels.**

The anchor is a **versioned, human-adjudicated conformance set**, not a corpus of training labels:

1. **ANCHOR-1** = the existing 150 blind rows, frozen, *with their 51 abstentions kept as
   abstentions*. Already banked and independently valid.
2. **ANCHOR-2** = ~100 fresh rows drawn **after** the vocabulary freeze (contamination control:
   R5 edits will be written while looking at ANCHOR-1).
3. **Test–retest** on 30 rows after ≥2 weeks → the single-coder ceiling, which is what the floors
   should be anchored to (not 0.60).
4. Per-axis **conformance sets**: positive / near-neighbour negative / out-of-vocabulary /
   contradiction-trap. ChatGPT's A–E list is the right spec.
5. **Must-link / cannot-link pairs** for work identity (the one place clustering constraints and
   pairwise NLI both apply).
6. **Known-item retrieval queries derived from `source_segments`** — system-independent ground
   truth, unlike the current golden set whose ids were chosen from live search output.

Each item stamped: `anchor_version`, `menu_hash`, `taxonomy_version`, coder, date, abstention.

**The different approach is not a different model — it is removing the LLM's authority over what
the rules already decide.** `config/content_types.yaml` already contains a top-down decision
procedure for ROLE (`content_type_rules`, D2587) and a deterministic legacy route
(`route_to_content_type`, D2128). Neither is implemented; an LLM free-generates instead, and a
script then promotes that free generation to the serving gate. Implement the declared procedure,
keep the LLM only where the rules underdetermine, let it answer `none`, and require a *second,
different-family* signal to overturn a rule — never to replace it.

Where fine-tuning *will* pay, later: after the anchor exists and the gate is honest, a cheap local
head (linear on bge-m3, or SetFit-class) trained on the adjudicated anchor, measured on a held-out
anchor version. That is step 8, and it is a cost optimisation, not an accuracy strategy.

---

## 8. New findings register

| id | sev | finding |
|---|---|---|
| F-38 | **critical** | the serving gate is `content_type='principle'` written by a hand-run script, not the S5 verdict; 2,447 rows (30.6%) disagree with their own persisted verification; 1,941 unverified/contradicted rows are served, 506 verified rows are hidden |
| F-39 | **critical** | ROLE is therefore the highest-leverage axis, not a decorative one — and it is the axis with zero lift over a constant (D6 inverted) |
| F-40 | high | the RRF keyword leg is query-blind and insertion-ordered yet receives equal RRF weight (retrieve.py:123/363) |
| F-41 | high | the ruler's FLOOR column compares accuracy to a provenance share (my instrument defect) |
| F-42 | high | the F-14 pocket retarget is statistically null; the claim is withdrawn |
| F-43 | high | S5 computes a 4-tier `epistemic_status` + `isor` + `verification_method`; stage6 has no columns for them |
| F-44 | medium | no label-provenance column exists anywhere → `min_human_share` is unsatisfiable → no axis is eligible as model-comparison ground truth |
| F-45 | medium | the D2128 `route → content_type` fallback is documented "live, NOT dead"; the `route` column does not exist |
| F-46 | medium | three hand-run scripts (`apply_phase1_adjudication`, `apply_phase1_finalize`, `repass_pair_agreed`) can move the gate on label grounds with no pipeline-side guard or audit stamp |

## 9. Gates this opens

| gate | decision |
|---|---|
| **G17** | approve **re-deriving `status` from `verification_results`** and making label-derived status writes impossible (net effect: serving set 4,745 → 3,310). This de-serves 1,941 rows; it does not delete them |
| **G18** | approve **guard split** instead of the G13 exemption list |
| **G19** | approve **persisting** the tier S5 already computes, and correcting the ruler's FLOOR estimand (no floor re-anchoring until test–retest exists) |
| **G20** | approve **one writer** for `status` + an audit stamp on any script that may touch it |

G4a (repoint the floors) is **withdrawn pending G19** — the floor cannot be re-anchored on an
estimand that is still confused, and not on a single coder.
