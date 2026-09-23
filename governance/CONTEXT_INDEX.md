# CONTEXT INDEX — governance recall map (Maxwell OS v3.0)

> **Created 2026-09-17. Read this FIRST when resuming — human or agent.**
> Purpose: one entry point that locates every authoritative artifact, defines every metric in
> exactly one place, records what is **superseded**, and marks every point where a **human
> decision or human labelling is mandatory**. It exists because the same facts had drifted into
> several documents and were restated by hand in each.

## 0. If you read only three things

1. `CONSTITUTION.md` — the rules that cannot be broken.
2. `governance/CONTEXT_INDEX.md` — this file: where everything lives and what is already wrong.
3. `governance/SEQUENCE_STATUS_20260917.md` — where we are, what is gated on a human.

## 1. The 2026-09-17 report set — what answers which question

| Artifact | Answers | Status | Depends on |
|---|---|---|---|
| `governance/PRIORITY_DECISION_20260917.md` | **which work is top priority, and why** (lever test + circularity) | awaiting ratification | F-05, F-10, BUG-267 |
| `governance/FORENSIC_AUDIT_20260917.md` | what is broken, invisible, or contradictory (F-01..F-16) | live, append-only | filesystem + DB re-derivation |
| `governance/MARKET_RESEARCH_20260917.md` | what external methods/tools are worth adopting (A1..A12, B, C) | advisory | feed.opml + live arXiv/HF/PyPI |
| `governance/STRATEGIC_PLAN_20260917.md` | the phased plan + rerun matrix + do-not list | live | priority decision |
| `governance/SEQUENCE_STATUS_20260917.md` | execution tracker + **HUMAN GATE REGISTER** | live | all of the above |
| `governance/buglog.md` (BUG-267 etc.) | the live defect register | live, append-only | — |
| `config/eval_integrity.yaml` | the floors, the anchor, the **provenance tier vocabulary** | authoritative | BUG-267 |

## 2. The axis ontology — 5 axes, 1 definition

`config/content_types.yaml` is the **only** definition of the axes and their values. Nothing else
may restate them (C12).

| # | axis | question | values | consumer |
|---|---|---|---|---|
| 1 | `content_type` | functional **ROLE** — what job does this object do? | 7 | S4 router |
| 2 | `extraction_type` | epistemic **FORM** — what kind of claim, how justified? | 4 | persisted S4->S6; **no verifier yet (F-15)** |
| 3 | `depth` | how widely does it apply? | 5 (incl. `n/a-non-principle`) | depth filter |
| 4 | `discipline` | which field owns it? (**singular**) | 61 | retrieval / routing |
| 5 | `domains` | which topics does it touch? (**multi-label**) | 43 | retrieval |

Role and FORM are **orthogonal** — one role accepts many forms. "Object type" is axis 1; the
un-adjudicated 5th axis is the FORM (axis 2). See `governance/FORENSIC_AUDIT_20260917.md` F-14.

## 3. Provenance vocabulary (BUG-267 / F-16) — exact match only

Defined in `config/eval_integrity.yaml::provenance_tiers`. An **unregistered** source fails closed.

| tier | meaning | counts toward the floor? |
|---|---|---|
| `human-blind` | decided **without seeing** a model's proposal | **strict: yes** (0 rows today) |
| `human-attested` | human decision, method unrecorded, or human **ratifying** a model proposal | lenient: yes |
| `model` | produced by an LLM (single, or a pair agreeing) | no |
| `frontier` | produced by a non-local API model | no |
| `na` | documented not-applicable sentinel, not a label | excluded |
| `UNKNOWN` / `NONE` | unregistered / missing | **FAIL CLOSED** |

## 4. Metric definitions — each lives in exactly ONE place

| metric | defined in | meaning |
|---|---|---|
| train/eval disjointness | `config/eval_integrity.yaml::anchor` | eval anchor must not overlap the train pool (today 0/1027) |
| human share (blind / attested) | `config/eval_integrity.yaml::provenance_tiers` + `human_share` | can this axis be used to judge a model? |
| FORM traceability | `scripts/audit_form_axis.py` | every FORM joinable to a provenance-bearing source record |
| runtime vs gold | `scripts/audit_runtime_vs_gold.py` | does the DB carry the adjudicated labels? |
| IAA (Krippendorff alpha) | **not built yet** (market research A2) | the correct per-axis agreement metric |
| n_min / stop rule | **not built yet** (market research A1) | minimum sample before a role decision |

## 5. Dependency graph — what gates what

```
human blind slice  ---- REQUIRED ----+
                                     v
                             the FLOORS  ----+
                                             +--> [RETRAIN / ROLE-SWAP / S2-S6 RERUN]
cross-family model labels ---- labels -----+     (modernBERT, DSPy)
                                             ^
                                             |
F-14 (FORM, 4054 untraceable) --------------+
   blocked by: F-02 provenance  +  G2 relabel-vs-retire ruling

R5 re-verification (6 decision lists, ~770 calls)
   blocked by: G3 judge calibration (human-scored)
```

## 6. Findings register

| id | severity | one line | status |
|---|---|---|---|
| F-01 | critical | runtime KB did not carry the adjudicated 4-axis labels | **CLOSED** 2026-09-17 |
| F-02 | high | relabel runs emit no judge/budget/cross-family provenance | open — **now a precondition of F-14** |
| F-03 | high | NULL depth read as "failed" instead of "not applicable" | **RE-SCOPED**: designed state, not a violation; stamp deferred until content_type is certified |
| F-04 | high | stranded 190-row vote; "vote to grow the anchor" falsified (3.2% agreement) | open |
| F-05 | med-high | the anchor is far less human than its name implies | open — BUG-267 sharpened it |
| F-06 | med | the benchmark harness has no test (root cause of BUG-262..266) | open |
| F-07 | med | the R5 review tool asked every script the wrong question | **FIXED** |
| F-08 | med | disk 95% (48 GiB) before a 40-52h rerun | open |
| F-09 | med | corpus/DB/config live in a third-party synced folder | open — decision required |
| F-10 | med | 6 scripts verify same-family (R5/C8 violation) | open — blocked on calibration |
| F-11 | low-med | silent-empty-answer surfaces remain | open |
| F-12 | low | vote set drawn from a partition that no longer matches the tiers | open |
| F-13 | low | accumulated tree drift (6 `__pycache__`, 122 `*.bak_2026*`) | open |
| F-14 | critical | FORM exists in TWO generations in one store (4054 untraceable) | open — **gated on G2** |
| F-15 | med | FORM has no verification consumer, so it is decorative | open |
| F-16 | med-high | human-provenance floor measured with a substring classifier over an ambiguous vocabulary | **FIXED** 2026-09-17 (BUG-267) |
| F-17 | high | judge calibration: on 3 of 4 testable decision tasks NO cross-family judge beats a constant answer, so the planned ~650-call re-verification buys no information | **MEASURED** 2026-09-17 (BUG-269) — T2 becomes deterministic; T3/T6 need a rubric, not a judge |
| F-18 | med | the frontier69 artifact disagrees with the DB on 10/69 objects; 2 concepts sit in BOTH taxonomies (648 rows affected) | open (BUG-270) |
| F-19 | med | object identity is content-derived: `fb_id = sha256(name|definition)`, so a rename orphans references (320 edges for one measured rename) while the graph is intact today (0 of 164,202 dangling) | **RULED** 2026-09-17 (D-271c) |
| F-20 | med | the axis contract says domains is 1..3 per row; reality is up to **7** (1,002 rows exceed 3) | open (BUG-273) |
| F-21 | low-med | the `related_fbs` graph is **56.8% asymmetric** (88,592 of 156,104 edges are one-way) + 7 self-references | open (BUG-274) |

## 6a. G4 RULER ARTIFACTS (2026-09-17) — the certified core

| artifact | path | note |
|---|---|---|
| instruction file (START HERE) | `governance/G4_RULER_INSTRUCTIONS.md` | the human runbook: menus, rules, budget, stop rule |
| blind labelling sheet | `governance/RULER_BLIND_SHEET_20260917.csv` | 150 rows, 18 cols, zero stored labels |
| answer menus (540 lines, explained) | `governance/RULER_MENUS_20260917.md` | CT 1-7 (5 roles + 2 dispositions), DISC 1-62, FORM 1-4. Per item: config definition + ASK + NOT THIS + TRAP + a real KB example (11 examples, verified 0 of them are sheet rows). Discipline section carries definition + aliases + near-neighbour NOT lists from `taxonomy_v5.yaml`. Regenerated by the builder: never hand-edit. |
| **answer key — do not open while labelling** | `governance/ruler_sheet_key_20260917.json` | holds the stored labels; opening it destroys blindness |
| sheet builder (R5 gemma APPROVE) | `scripts/build_ruler_sheet.py` | `--validate` = completeness + menu range + namespace |
| scorer (R5 gemma APPROVE) | `scripts/score_ruler_labels.py` | refuses an incomplete sheet; always reports the constant-answer baseline |
| measurement output | `governance/ruler_measurement_20260917.md` | written only after scoring |
| priority register | `governance/PRIORITY_REGISTER_20260917.md` | the critical items in consequence order |

Design facts worth remembering: stratum **A (100) = proportional** and it is the **only** stratum a floor may
be measured on; stratum **B (50) = forced-minority**, never the floor (BUG-269). The F-14 untraceable pocket
is 50.7% of the KB, so it appears **83 times** in the sheet and is compared untraceable-vs-traceable *within
stratum A*. Axis vocabulary: `pipeline/content_types.py::CONTENT_TYPES_ALL` is the authority for
content_type, NOT the yaml `content_types` key (BUG-277).

## 7. HUMAN GATE REGISTER

| gate | human action required | artifact | blocks |
|---|---|---|---|
| **G1** | ratify the priority ruling | `PRIORITY_DECISION_20260917.md` | the whole sequence |
| **G2** | rule **relabel vs retire** for the 4054 orphan rows (30-row sample) | `F14_RELABEL_OR_RETIRE_SAMPLE_20260917.csv` | F-14 (~4,054 calls) |
| **G3** | blind-label the judge-calibration rows | `JUDGE_CALIBRATION_SPEC_20260917.md` | R5 re-verification (770 calls) |
| **G4** | blind-label the certified eval core, n=100-150 | to be generated | every model-accuracy claim |
| **G5** | P2 freeze ratification (19 uncited roles) | `consolidation_drafts_20260916/02_model_assignments.yaml.draft` | config freeze |
| **G6** | decide the Dropbox/synced-folder question (C3) | `FORENSIC_AUDIT_20260917.md` F-09 | leak-risk posture |
| **G7** | decide domain aggregation policy (63 contested rows) | `governance/domain_aggregation_policy_decision.md` | domain axis |

| **G12 ✅** | approve constraining the facet filters (predicate in every leg + assert on the fused pool) — **IMPLEMENTED 2026-09-19** | ROUNDTABLE_CROSSEXAM_20260919.md | correctness of every retrieval number |
| **G13** | ~~approve the write-guard exemption~~ **SUPERSEDED BY G18** | — | — |
| **G14** | approve work-identity dedup at ingestion (re-run affected merges, or prevent future ones only?) | BUG-289 | the S1.5 merge criterion |
| **G15** | approve indexing what is already in the DB (body fields into FTS; evidence_passages as a leg) | BUG-288 | retrieval coverage (11.1% today) |
| **G16** | approve the chunk/evidence leg, and decide whether a hit returns the parent FB or the segment | D-273g | grounding precision |
| **G17 ✅** | **re-derive status from the verification record; make label-derived status writes impossible** — **IMPLEMENTED 2026-09-19** (PASS 4,745 → 3,299; de-serves 1,941 + 11 duplicates; deletes nothing) | BUG-299 / D-274a | **everything measurable** |
| **G18 ✅** | approve the guard SPLIT (row guard vs vocabulary lint) — **IMPLEMENTED 2026-09-19** | D-274 / ROUNDTABLE_CROSSEXAM | R1, and the 261 research-methodology rows |
| **G19** | persist the tier stage 5 already computes; withdraw the FLOOR estimand (**G4a withdrawn**) | BUG-295 / BUG-301 | the ruler's validity |
| **G20** | one writer for status + an audit stamp on any script that may touch it | BUG-299 | governance of the gate |
| **G4a** | ~~repoint the floors at the certified core~~ **WITHDRAWN** — the estimand is confused and a floor may not be re-anchored on a single coder | BUG-295 / BUG-296 | — |

## 8. ANTI-DRIFT RULES

1. **Never restate a config value in prose.** Cite the path. (Floors, sentinel, axis values and
   the tier vocabulary all live in config; prose copies have already drifted once.)
2. **One definition per concept.** If two files need it, one imports the other
   (`axis_authority.py` is the model for this).
3. **Every claim carries `{artifact, date, n}`.** An uncited number is not a measurement.
4. **Fail closed on unknown.** An unverified invariant is never "OK".
5. **A design state is not a violation.** Reporting a designed outcome as a defect creates
   pressure to weaken the gate (F-03; the NA-as-DRIFT inversion).
6. **Generator != Verifier by FAMILY, not by model** (R5/C8).
7. **Freeze = tag, not approval.** An explicit `UNVERIFIED` beats a silent assumption.
8. **No "spotless" without a number.** Agreement needs Krippendorff alpha + a per-axis n_min.

## 9. DO-NOT-QUOTE list (claims that were already wrong once)

| do not quote | quote instead |
|---|---|
| "the 1027 golden examples" | the 1,027 **silver** S4-distillation examples (gpt-oss teacher, *not hand-reviewed*, no FORM field) |
| "Qwen3.8 discipline accuracy 0.709" | **in [0.437, 0.854]**, unknown; the *ranking* is stable on all subsets |
| "human share content_type 0.116" | **0.000 blind / 0.116 attested**, and 0.116 is an **upper bound** (BUG-267) |
| "gemma for depth" | gemma for depth is **REFUTED** (62.5% vs gpt-oss 75%, gate >=90%) |
| "gpt-oss depth 87.5%" | **75%** (n=8) — the 87.5% was a governance claim that drifted |
| "3rd reliable voter as tie-break" | **disproven** — no local model within 28 points; none rescues >18% of errors |
| "majority voting improves classification" | **disproven** — avg 3-combo 0.541 vs 0.709 single |
| "causal_mechanism is a rare form" | pre-repair it was **44.8%**; the repair took it to ~5.8% (single-source ~4%) |
| "the KB is clean" | `classification_status=CLEAN` on all 7,995 rows **while** 4,054 carry an untraceable FORM |
| "gemma scores 0.875 on suffix-merge" | **degenerate** — equal to the constant-answer baseline 0.875 (always `merge`) |
| "the judge is 78% accurate" | **quote the lift, not the accuracy**: 0.778 with a 0.778 constant-answer baseline is zero information |
| "re-verify the 6 decision lists with a different family" | only **1 of 4** testable tasks has a judge that beats a constant answer; the rest must be made deterministic or human-owned (F-17) |

---

## 6b. ONTOLOGY FORENSIC + RULER RESULT (2026-09-19)

**Read first if resuming:** `governance/ONTOLOGY_FORENSIC_20260919.md` (measured diagnosis, F-A…F-L),
`governance/MARKET_RESEARCH_ONTOLOGY_20260919.md` (24 verified candidates, V/A/R/I),
`governance/ruler_measurement_20260917.md` (generated), `governance/ROUNDTABLE_MASTERPROMPT_ONTOLOGY_20260919.md`
(LLM roundtable brief), and buglog BUG-278…BUG-283.

**The certified result (blind human, 150 rows; stratum A n=100 is the ONLY floor denominator):**

| axis | stored-label accuracy | 95% Wilson | baseline | lift | verdict |
|---|---|---|---|---|---|
| content_type (ROLE) | 0.740 | [0.646, 0.816] | 0.750 | **−0.010** | no better than a constant |
| discipline | 0.506 | [0.401, 0.611] | 0.084 | +0.422 | floor INSIDE the CI → **unresolved** |
| extraction_type (FORM) | **0.831** | [0.740, 0.895] | 0.360 | +0.472 | **decisive PASS — best axis** |

**F-22..F-27 (new findings, do not restate them wrongly):**

| id | sev | claim | status |
|---|---|---|---|
| F-22 | crit | **THE AXIS INVERSION** — retrieval's primary exact filter (`discipline = ?`, 0.506) is the LEAST reliable axis, and the BEST axis (FORM 0.831) is not a retrieval facet at all | RULED D272b |
| F-23 | crit | **free-generation labelling**: `stage4_merge.py:341/:472` says "no canonical lists" while its own docstring claims D316 lists them inline → synonym rescue 49.9%, `emerging` dump 14.8%; ceiling ≈0.61 = the floor | RULED D272c |
| F-24 | crit | **`QUARANTINE` conflates unverifiable with untrue**; 40.7% hidden incl. **1,780 principles**; `NEUTRAL` vs `CONTRA` not persisted, so the distinction is unrecoverable | RULED D272d |
| F-25 | high | **ROLE is decorative**: `status=PASS` ⟺ `content_type='principle'` exactly (4,745 = 4,745, zero non-principle rows pass); `depth` is empty for all 1,470 non-principle rows | BUG-280 |
| F-26 | high | **no relevance axis**: `noise_drop` fuses "not extractable" with "true but irrelevant"; the reviewer asked for the split ~10× | RULED D272e |
| F-27 | high | **24 of 45 attribute columns are dead/near-dead**; `contradicts_fbs` NULL 100%, `usage_count`/`last_retrieved_at` empty 100%, `provenance` single-tier, `classification_status` always `CLEAN` | BUG-282 |

**F-14 IS RETARGETED (correction):** FORM does **not** degrade in the untraceable pocket (stratum A: 0.860
untraceable vs 0.804 traceable). **ROLE** does (0.667 vs 0.816). Do **not** re-derive FORM for 3,348 rows;
re-decide **ROLE** on the pocket. (RULED D272g.)

**Do-not-quote additions:** "the alias map is a synonym list" → it is a **999-rule compensating control**
(14.8:1 for domains). "The taxonomy is post-hoc" → `taxonomy_v5.yaml` shipped with the v2.0 pipeline
(2026-07-20); `alias_map.yaml` came **6 weeks later** (2026-09-02) and *is* post-hoc. "`is_summary` is a dead
field" → the gate **fires** (158 gated cluster ids in `stage2_extract/t11/checkpoint.jsonl.gated_ids`); the
field reads 0 because gated clusters never become FBs — what is missing is a **drop ledger**.

---

## 6c. SECOND-PASS FORENSIC (2026-09-19, later the same day) — the retrieval and ingestion layers

Read **§13 of `governance/ONTOLOGY_FORENSIC_20260919.md`** before acting on §6b. The first pass examined
**labels**; the second examined the **retrieval path**, the **ingestion path** and my own **sampling frame**, and it
**corrected three of my own claims**.

**THE THREE CORRECTIONS (do not quote the old versions):**

| old claim | now |
|---|---|
| "ROLE 0.740 vs baseline 0.750, lift −0.010" | the sheet sampled the **full KB** (47.3% PASS vs 59.3% in the KB). On **`status='PASS'` only**: ROLE **0.891 vs baseline 0.891, lift exactly 0.000** — and 0.472 vs 0.500 on quarantined rows. Discipline 0.492 (unchanged), FORM 0.852. |
| "discipline is the primary **exact-match filter**" | **the filter does not filter.** `search_fts`/`search_vector` take no facet params; only `search_keyword` applies `discipline = ?`; no post-filter. Measured: with `discipline='typography'`, **2 of the RRF top-10 were not typography.** It is a *nudge on one of three legs*. |
| "40.7% is **invisible** to retrieval" | **inconsistently visible.** `graph_expand` has **no status predicate** and `search_graph` includes contradictions/prerequisites by default, so quarantined rows **re-enter as graph neighbours** of a PASS seed. |

**F-28..F-37:**

| id | sev | claim | bug |
|---|---|---|---|
| F-28 | **crit** | **filters do not constrain** the hybrid result set | BUG-285 · D273a |
| F-29 | **crit** | the **write guard destroys the label D-271a ruled legal** (`research methodology` quarantined at S4, REJECTED at S6) → **blocks R1 as specified** | BUG-286 · D273b |
| F-30 | high | **graph expansion leaks** the quarantined 40.7% back in, and propagates label error structurally | BUG-287 · D273c |
| F-31 | high | **retrieval corpus = 11.1% of each FB**; 88.9% of the body and **4.8M chars of evidence are unindexed**; `source_text` is `"[book] " + definition` | BUG-288 · D273d |
| F-32 | med-high | **29.1% of "convergence" is the same book twice** (`source_diversity` counts filenames) — and it is the **merge criterion at stage 1.5** | BUG-289 · D273e |
| F-33 | med | **`emerging` is an illegal value inside the facets**: 744 domain rows (not canonical) + 447 PASS discipline rows | BUG-290 · D273f |
| F-34 | med | **`vec_fbs_ctx`** (7,995 label-prefixed embeddings) sits one argument from production | BUG-291 |
| F-35 | low | `fbs_fts` has an **INSERT trigger only**; **integrity-check PASSED** → latent, but nothing detects it | BUG-292 |
| F-36 | low | **mega-merges** up to **244 sources** for one FB. **Refuted:** they do NOT cause unlabelability — singletons are **3× more** unlabelable (24.1% vs 0%) | BUG-293 |
| F-37 | med | the ruler's strata are **not crossed with `status`**, conflating two estimands | BUG-294 · D273h |

**REFUTED HYPOTHESES (recorded so they are not re-run):** (a) FTS staleness — `fbs_fts` integrity-check **passed**
on a copy; (b) contextual embeddings poisoning production — `contextual_embed.enabled: False`, production vectors
are clean; (c) over-merging making FBs unlabelable — **the opposite holds**.

**RRF / CHUNKING — the direct answer:** RRF is **already implemented and correct** (k=60, `1/(k+rank)`, 1-based,
three legs). Chunk-level retrieval **is** worth adopting, at **step 8**: the DB's `source_segments` (214,220 refs)
join the stage-1 checkpoint **205,813/205,813 = 100%**, so the leg costs **~214k vectors (≈438 MB at 512d)**, needs
no mapping/re-chunking/re-extraction, and returns **verbatim source + section heading + parent-FB link**. But it
fixes **grounding precision, not label accuracy**, the 300/50-word overlap must be collapsed at fusion, and adding a
leg **before F-28 is fixed amplifies the filter leak**.

---

## 6d. REFERENCE LIBRARY (2026-09-19) — the bibliography for the ontology/retrieval programme

**Start here for any literature question:** `governance/REFERENCE_LIBRARY_20260919.md`.

- ~45 works, each with a DOI-verified (or W3C-standard) identifier, a `role` (why Maxwell OS cares), and a
  `bears` field tying it to the specific forensic finding or repair it justifies.
- **Metadata is FETCHED from OpenAlex by DOI, not typed** — title, year, venue and citation count are evidence,
  so a mistyped year cannot survive a rebuild. Result: **37 DOI-verified, 8 standards, 0 unresolved.**
- The fetch **exposed 7 metadata discrepancies** (e.g. OpenAlex returns 2002 for Broder 1997; 2016 for Paulheim
  2017) and they are rendered as `note:` lines rather than silently accepted — which is the point of fetching.
- Machine-readable: `governance/references_20260919.bib` (BibTeX), `governance/references_20260919.json`
  (resolved metadata snapshot; also the offline cache). Source of truth: `config/references.yaml` (C12).
- Rebuild: `python3 scripts/build_reference_library.py` (fetch) / `--cached` (offline) / `--check` (report only).
- Cited from: `MARKET_RESEARCH_ONTOLOGY_20260919`, `ROUNDTABLE_MASTERPROMPT_ONTOLOGY_20260919`,
  `ONTOLOGY_FORENSIC_20260919`, `buglog.md` (BUG-285…BUG-294), `DECISION_D271_IDENTITY_20260917`.

## 6e. ROUNDTABLE CROSS-EXAMINATION + STRATEGIC VERDICT (2026-09-19)

Three frontier reviews were returned against ROUNDTABLE_MASTERPROMPT_ONTOLOGY_20260919.md
(temp/qwen0080.md, temp/chatgpt0080.md, temp/claude0080.md). Every load-bearing claim was re-derived
against the repo or the live DB before acceptance. Record: governance/ROUNDTABLE_CROSSEXAM_20260919.md.

**THE FINDING NONE OF THE THREE REACHED — the serving gate is a LABEL, not a verification verdict.**

| id | sev | finding |
|---|---|---|
| F-38 | **crit** | status is set by scripts/apply_phase1_finalize.py:18 as (content_type == 'principle'); 4,745/4,745 PASS rows are principle, 0/1,470 non-principle rows pass; 2,447 rows (30.6%) disagree with their own persisted verification_results[factual].passed; 1,941 unverified/contradicted rows are served (138 NLI CONTRA-majority, 1,514 NEUTRAL, 278 evidence-flagged, 9 MECH FAIL, 2 conversion artifacts); 506 verified rows are hidden. An honest gate moves PASS 4,745 to 3,310 |
| F-39 | **crit** | therefore ROLE is the highest-leverage axis, not decorative — D6 / BUG-280 / D272g are inverted |
| F-40 | high | the RRF keyword leg is query-blind (retrieve.py:123 has no query param), insertion-ordered (borp_score 0.0 everywhere) and credited equal weight (:355-390); the rerank pool is cut from the fused list (:411-415) |
| F-41 | high | the ruler FLOOR column compares stored-label ACCURACY to min_human_share, a PROVENANCE SHARE (score_ruler_labels.py:136/184 vs eval_integrity.yaml:28-31). The STOPPED/CONTINUE verdicts are void as stated; only the constant-baseline lift survives |
| F-42 | high | the F-14 pocket retarget is statistically null (content_type 0.566 [0.459,0.668] vs 0.687 [0.568,0.785]; FORM 0.821 vs 0.787). The claim is withdrawn; the action survives for a different reason |
| F-43 | high | stage5 computes epistemic_status / isor / verification_method; stage6 has no columns for them. R3 is a wiring job, and :898 hardcodes the verifier stamp |
| F-44 | med | no label-provenance column exists anywhere, so min_human_share is unsatisfiable and NO axis is eligible as model-comparison ground truth — S2/S4 may not be trained or swapped on the current labels |
| F-45 | med | the D2128 route -> content_type fallback is documented as live and NOT dead; the route column does not exist in the DB |
| F-46 | med | three hand-run scripts can move serving eligibility on label grounds, unguarded and unstamped |

**Adjudication of the reviews.** Claude 10/10 load-bearing claims confirmed (D11 "worse", the guard
split, the verifier literal, parse-not-rerun, the catch-all sentinel, D19, the floor confusion, the
golden-set circularity) and it stopped one step short of F-38. ChatGPT confirms the diagnosis and is
best on architecture and market, but CONFIRMED D3 wrongly and asserts D6 in the wrong direction; its
claim that stage 5 does not preserve the NLI distinction is wrong (it is preserved and never queried).
Qwen is derivative (18 CONFIRMED rows, no re-derivation), repeats the D3 error, and adds two category
errors (constrained decoding cannot replace a semantic verifier; RAGAS/ARES measure retrieval quality,
not label correctness). **Consensus to act on:** retrieval correctness precedes label repair; emerging
must never be a facet value; the write guard must be split, not exempted; graph neighbours carry their
own tier; relevance is a versioned sidecar; FTS the body before embedding it; retire the alias map;
R5 -> R1 -> R2; every prior retrieval number measured an unconstrained system; do not tune RRF weights
at n=30.

**Programme order now:** 0a serving gate from the verification record -> 0b facet predicate in every leg
-> 0c guard split -> 1 persist the tier -> 2 correct the ruler estimand -> 3 R5 then R1 -> 4 index what
is already in the DB -> 5 work-identity dedup -> 6 S5 aggregation fix -> 7 chunk/evidence leg -> 8
distilled classifier.

**✅ IMPLEMENTED 2026-09-19 (later session): 0a, 0b, 0c.** (0a) `scripts/apply_serving_gate.py` is the single
writer for `status` (from `verification_results[factual].passed` + typed `s5_reason`, new `fbs.s5_reason`
column) — PASS 4,745 → 3,299, CI invariant 0 violations, duplicates hard-quarantined. (0b) facet predicate
in every retrieval leg + asserted on the fused pool — constraint-violation rate 0.5911 → 0.0000. (0c) write
guard split into row guard vs vocabulary lint — `research methodology` writes clean. Closed BUG-276/285/286/
299/300/302. **Remaining path: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8.**

**Explicitly excluded on priority grounds:** re-labelling the corpus, buying ~85 more stratum-A rows,
training S2/S4 on the current labels, extending the alias map, ACORN, re-cutting the ontology,
re-deriving FORM on the pocket, the chunk leg / vec_fbs_ctx / contextual embeddings / weighted RRF
before 0a-0b, deleting the junk rows, and R2 before R5/R1. The D-2637 model-eval workstream is NOT on
the critical path.

---

## 2026-09-19 (evening) — Ruler key inversion + content-type guardrail

**Revelation (user-forced, correct):** the G4 ruler was scored against the STORED label, but the stored
label IS the corrupt free-generated artefact under audit. "Stored-label accuracy" = agreement-with-corruption.
**D-275a (RESOLVED):** invert the key — blind human label = ground truth, stored label = under test,
report error rate. `scripts/rescore_ruler_inverted.py` written + run (FORM pass).

**D-275b (PROPOSED, pending ratification):** content-type guardrail — atomic unit = one self-contained
epistemic claim (not one sentence); principle/process_template discriminator = procedural intent + done
condition (not "≥2 steps", necessary-but-insufficient); FORM = primary epistemic commitment; taxonomy
one-or-many = self-containedness; checklist → process_template; decision matrix → inline_gate_content.

**Measured (inverted key, FORM):** stored error rate 0.253 [0.177, 0.346]; normative_heuristic 50% wrong
in storage (→ causal 9×, → descriptive 6×); "irrelevant" written in 4 FORM cells (evidence for R4).
Report: `governance/ruler_form_inverted_20260919.md`.

**Status:** ANCHOR-1 = 150 human rows (FORM final; CT/discipline pending reviewer update). Next:
reviewer re-labels CT/discipline with the D-275b guardrail → re-score those (inverted) → freeze ANCHOR-1
→ per-slot reliability → R5 (ratify slots) → R1 (closed menu) → R2 (definition NLI).

**G19 IMPLEMENTED 2026-09-19 (evening):** `stage6_commit.py` now persists all four S5 tier fields
(`s5_reason`, `epistemic_status`, `verification_method`, `isor`) + `verifier_model` is config-derived
(`S5_NLI_MODEL_LARGE` + `S5_NLI_PASS_THRESHOLD`). Live DB migrated to 71 columns; CHECK 8 passes (71=71).
Also fixed the latent 0a drift (s5_reason was in DB but not in stage6 CREATE TABLE/INSERT). BUG-301 resolved.

**D-275c (RESOLVED):** TypeSafe AI "System One Models / Jev" — REJECT as pipeline dependency (hosted paid
API, violates C1/C3/C2/C4/C22; does what the local stack does for $0). ADAPT the framing (calibrated
decision + typed abstention) as validation of R1/R2/R10. No new dependency.

---

## 2026-09-20 — Full-axis inverted re-score + ANCHOR-1 freeze

**Reviewer locked all three axes** (R021 FORM blanked, R146 → organizational theory, DISC fully
re-labelled with the menu, 4 trailing blank rows removed).

**Measured (inverted key, D-276):** stored-label error — **CT 0.353** [0.281, 0.433] (A 0.290),
**DISC 0.474** [0.386, 0.564] (A 0.487), **FORM 0.283** [0.216, 0.361] (A 0.255).

**Two systemic defects now measured, not asserted:**
- CT: the old classifier over-calls `principle` (93 stored vs 89 human), under-calls `quarantine`
  (18→6) and `process_template` (16→9) — the D-275b "step-count not procedural-intent" gap, quantified.
- DISC: 8 zero-agreement slots (design psychology 0/5, cultural studies 0/4, risk management 0/4,
  privacy & surveillance, political economy, visual perception, finance, cultural design) — the alias
  map silently discards them into `emerging`. Group-level near-miss: exact 0.430 → same-group 0.271.

**Artifacts:** `ruler_inverted_20260920.{md,json}` (measurement), `anchor1_frozen_20260920.{md,json}`
(frozen ground truth + R5 slot vote). `ruler_measurement_20260917.md` marked SUPERSEDED (A5).

**Status:** ANCHOR-1 frozen. Remaining path (dependency order): 1 R5 ratification → 2 R1 (closed menu +
`menu_hash` + `*_source` provenance) → 3 R2 (definition NLI). Provenance columns are the binding
prerequisite: `min_human_share` is unsatisfiable until `content_type_source` / `discipline_source` /
`extraction_type_source` / `menu_hash` exist.

---

## 2026-09-20 (later) — R5 repair-not-demote + D-275b ratified + raw/canonical clarified

**Three clarifications ratified (D-277, RESOLVED):**

1. **R5 is repair, not demote.** Zero-agreement DISC slots measure PIPELINE failure, not slot badness
   (two distinct causes). The initial DEMOTE vote was withdrawn. Corrected scheme: RE-DERIVE definition
   + include + exclude (OntoClean) for weak slots → BOUND (human review on write) → merge into the
   parent group only if still definitionally inseparable. Never DEMOTE first.
2. **Raw AND canonical are both post-hoc model stamps.** The corpus has ZERO human-derived labels; the
   raw string and the canonical slot both came from the 2-month-old corrupt run, so neither can be
   "recovered" into truth. Both demoted to provenance (G9); re-derive from source text only.
3. **The error rate is a meter, not an oracle.** Per-class stored error calibrates confidence and
   triggers abstention; it carries zero per-object information and never flips a label.

**D-275b RATIFIED (RESOLVED).** The content-type decision procedure (Mechanism A: ordered 7-question
tree, first-match-wins; checklist→process_template; decision-matrix→inline_gate_content; taxonomy
one-or-many by self-containedness) is written into `config/content_types.yaml` as
`content_type_decision_procedure`. `principle`/`process_template` descriptions updated to procedural
INTENT + done-condition (D-275b), the step-count framing demoted to necessary-but-not-sufficient.

**Artifacts updated:** `anchor1_frozen_20260920.{md,json}` (dispositions RE-DERIVE+BOUND, no DEMOTE);
`config/content_types.yaml`; `decisions.yaml` D-275b RESOLVED + D-277 added; BUG-304 corrected.

**Remaining path (dependency order):** 1 R5 repair execution (draft definition+include+exclude for the
BOUND slots) → 2 single-coder ceiling (second human on 30 rows) → 3 R1 (closed-menu renderer +
`menu_hash` + `*_source` provenance columns in stage4_merge/stage6_commit/schemas) → 4 R2
(definition-anchored NLI).

---

## 2026-09-20 (final batch) — Next-4 execution: R5 repair + single-coder ceiling + R1 + R2

Executed the four dependency-ordered steps. No new unexpected defect surfaced; the one
caught-and-fixed item was a placeholder-count drift in the stage6 INSERT I introduced
and self-corrected under verification (75==75==75, end-to-end temp-DB insert green).

1. **R5 repair (D-278):** `config/r5_slot_repair.yaml` drafts OntoClean
   definition + include + exclude for the 7 weak slots (design psychology, cultural
   studies, risk management, behavioral economics, decision making, quarantine,
   process_template) + the 2 BOUND-only slots (design thinking, organizational theory).
   Exclude sets name the correct sibling target → testable R2 rules. Awaiting human
   ratification; slots stay BOUND until then.
2. **Single-coder ceiling (D-280, HUMAN GATE):** `SINGLE_CODER_CEILING_SHEET_20260920.csv`
   (30 rows, stratified over the RE-DERIVE slots, labels blanked) + protocol. The second
   human pass is NOT done — it is the next human gate.
3. **R1 (D-279):** `pipeline/closed_menu.py` renders the closed menu (8 CT incl. `none`,
   4 FORM, 62 DISC, 44 domains) with `menu_hash` sha256 `25b10c44…`. `stage4_merge.py`
   stamps `content_type_source`/`discipline_source`/`extraction_type_source`
   (all `llm_extracted_from_source` — zero human labels, D-277) + `menu_hash`;
   `stage6_commit.py` persists the 4 columns (CREATE+migrate+INSERT); `schemas.py` FB
   model gained the 4 fields. Frozen menu: `config/closed_menu_v5.json` + `.sha256`.
4. **R2 (D-281):** `scripts/definition_nli_verify.py` — definition-anchored NLI
   (premise=FB definition, hypothesis=menu definition, R5 override first). Selfcheck
   green; the corpus-wide NLI run is the next action.

**Remaining path (dependency order):** 1 human ratification of the R5 definitions →
2 single-coder second pass (human) → 3 R2 corpus-wide NLI run → 4 re-measure per-slot κ
against ANCHOR-1 → 5 lift BOUND / merge only if inseparable.

---

## 2026-09-20 (forensic audit + D-282) — depth-vs-role conflation caught and fixed

User-caught defect in the D-278 R5 definitions: "a filter across 3+ domains" was used as
the principle-role boundary. That is the **universal-depth** threshold, not the
**principle-role** criterion — `specialized`/`domain` principles (1-2 domain labels) are
still principles (`depth is NOT domain count`). Fix (D-282): the principle role is "a
self-contained transferable rule at ANY scope"; scope is the separate depth axis.

**Audit findings this batch:**
- **CRITICAL (fixed):** "3+ domains" role conflation in `r5_slot_repair.yaml` +
  `content_types.yaml` (principle description, decision-procedure step 5, D-2587
  single-step rules). Re-rendered closed menu → new `menu_hash` `e8a8b546…`.
- **MEDIUM (documented, no code change):** the closed menu has 8 content_types (with
  `none` abstention); the human ruler (ANCHOR-1) used 7 (no `none`). `none` (classifier
  abstention) must reconcile with human blank-cell abstention when the κ scorer is built.
- **MINOR (fixed):** `definition_nli_verify.py` reused the S5 entail-pass threshold for a
  contra-dominance flag → now a dedicated `_CONTRA_DOMINANT_THRESHOLD`.
- **caught-and-fixed in batch:** stage6 INSERT placeholder drift (73 vs 75) → 75==75==75.

No other drift/leak/contamination/conflict/future-tax found in schemas.py / stage4 /
stage6 / closed_menu.py (all verified: py_compile, FB-model Literal validation,
end-to-end temp-DB insert, deterministic menu hash).

**Remaining path (unchanged order):** 1 human ratification of the D-282-corrected R5
definitions → 2 single-coder second pass (human) → 3 R2 corpus NLI run → 4 re-measure
per-slot κ → 5 lift BOUND / merge only if inseparable.

### 2026-09-21 (D-307..D-312) - menu repair closed, phantom version removed, assignment premise corrected
* `config/normalization_map.yaml` = owner-approved DOMAIN surface variants, wired into the kappa layer and
  **domain-scoped** (BUG-325: un-scoped use rewrote discipline tokens). Domains micro-kappa 0.5765 -> 0.5931
  (mean Jaccard 0.4515 -> 0.4737); discipline unchanged at 0.4395. Ablation reproduces both figures on identical
  taxonomy bytes -> the delta is the map, nothing else.
* `config/taxonomy_v5.yaml` is **v5.5 again** (D-309): v6.0 added zero slots and conflicted with the stamped
  `TAXONOMY_VERSION`; the marker now lives in `meta.menu_repair_20260921_*`.
* **Superseded claim (do not re-use):** "the pipeline never selects existing taxonomy slots / never emits ai & agents,
  brand identity, code & computation, ...". Whole-corpus measurement shows all 61+43 slots present; the claim came from
  the contra-stratified 60-row sample. See `governance/ASSIGNMENT_PATH_DIAGNOSIS_20260921.md` (D-310).
* New open items: R3 held-out validation (`R3_HELDOUT_PREREG_20260921.md`, D-311), calibrated abstention
  (`ABSTENTION_DESIGN_20260921.md`, D-312, inert), BUG-326 corpus assignment defects.

## 2026-09-21 (session 6, D-313) — forensic audit + BUG-328 landing

- **Landed**: G19/D274h serving gate + R1/D-279 `menu_hash`/`*_source` + D275b/D282/D283 principle-role
  semantics + D-291/D-293 pin/MTP. Safety evidence: `apply_serving_gate.py` dry-run = **0 writes** over
  7,995 rows (the rule exactly reproduces the stored PASS 3299 / QUARANTINE 4696); `menu_hash`
  73597ee2 matches the frozen `.sha256`; retrieval smoke-tested OK.
- **NEW HIGH — BUG-329 (corrects BUG-314)**: the ruler has three versions — freeze-time `4d0c856a`
  (bytes lost), HEAD `2d456720`, working `38323192` — and HEAD to working drift is substantive
  (41 CT / 7 DISC / 62 FORM cells). 0.4741 stays derivable from the frozen key, but NO re-measure is
  valid until gate 4 names the ruler.
- **NEW**: BUG-330 (stale assertion), BUG-331 (no R5 record for the gate write). `fbs` is one migration
  behind code (no `menu_hash`/`*_source` columns → D-279 stamps unwritten).
- **Superseded**: BUG-314's "zero substantive label drift".

<!-- s7-sync 2026-09-21 -->

### Session 7 (2026-09-21) — R3 held-out result and what it supersedes
- **`governance/R3_HELDOUT_RESULT_20260921.md`** is the authoritative R3 statement. It SUPERSEDES the
  in-sample "+6.0 pp" claim in `governance/anchor1_arbitration_20260921.json` (derivation on 116 ruler rows,
  now a historical record only) — read the held-out file before quoting any R3 number.
- **`governance/FORENSIC_AUDIT_20260921c.md`** — session-7 audit: cross-source artifact merge hazard (fixed),
  R5 rubber-stamp risk (BUG-333), effective-n hazard (BUG-334), plus the explicit negatives.
- Config: label sources are now named objects (`bakeoff.active_source`, `bakeoff.sources.<name>`) and the R1-R4
  rules live in `bakeoff.arbitration`; `scripts/r3_heldout_eval.py` is the scorer. `scripts/anchor1_arbitration.py`
  is the superseded DERIVATION helper (its hardcoded arm names were a C12 claim-vs-code mismatch, audit F-05).
- New bug numbers this session: BUG-332 (FIXED), BUG-333 (OPEN, R5 channel), BUG-334 (OPEN, effective n),
  BUG-335 (FIXED). BUG-328 now CLOSED with evidence.

## 2026-09-21 — NAME COLLISION FIXED (ANCHOR-1 vs ANCHOR-2)
Two instruments were both called "ANCHOR-1". Fixed: **RULER-150** = the 150-row stratified calibration
instrument (`anchor1_frozen_20260920.json` = authority; `RULER_BLIND_SHEET_20260917.csv` = human workspace,
menu `cac6e695`). **ANCHOR-2** = the 60-row contra-stratified adjudication/held-out instrument (renamed from
`ANCHOR1_*` -> `ANCHOR2_*`, pair = sheet + key, menu `73597ee2`, 58 held out for R3). Full map + rules:
`governance/ARTIFACT_REGISTRY.md`. Also corrected: `anchor1_arbitration_20260921.json` was a RULER-150
in-sample derivation, not ANCHOR-1/2 -> `ruler_arbitration_in_sample_20260921.json`. Rule: never concatenate
instruments; never pool across menus; pool only at read time with weights.

## 2026-09-21 — D-315 RATIFIED: THE CANONICAL RULER (BUG-329 CLOSED)
The canonical ruler is **`governance/anchor1_frozen_20260920.json`** (`0ec321a7…` — authority for the HUMAN labels and
for the measurement; immutable, committed, sha256-cited). `governance/RULER_BLIND_SHEET_20260917.csv`
(HEAD `38323192…`) is the human editing **workspace** and the only record of WHY a cell abstained — never the answer
key. `2d456720…` (commit `986fbc4`) is a **superseded draft**; `4d0c856a…` is **byte-lost / label-verified-identical**.
Ruler labels were judged under menu **`cac6e695`** (CT = 7, no `none`) — any quoted ruler number must carry it.
Authority/workspace/hashes/menu/truth_source/pooling are all declared in `config/eval_integrity.yaml:ruler_authority`
(do not re-derive them from prose). Scorers read truth from the authority (`--truth-source key`, the default);
`--self-test-blinding` is the mechanical leak guard for this path. Nothing may be pooled with ANCHOR-2.
## 2026-09-21 (session 9) — D-316: ONE answer key; annotation may be a second hash-pinned source
Ruler answer key = governance/anchor1_frozen_20260920.json (0ec321a7…), unchanged. BUG-340: that artifact cannot
express an abstention REASON (34 DISC nulls = 28 blank + 6 emerging), so the scorer restores the reason from the
human workspace CSV behind the declared sha256 (38323192…; drift = FAIL-CLOSED) and only where the authority cell
is empty. Machine-readable details: config/eval_integrity.yaml (ruler_authority, label_snapshots). Published
numbers unchanged (CT 0.3533 / DISC 0.4741 / FORM 0.2828). BUG-341: the live stage5 checkpoint is ABSENT again
(rotated at 18:59:42, no re-run); the bytes are citable as the .stale file, never copied back. C15 counts are now
mechanical (scripts/bug_status.py -> governance/bug_status.json): 60 open / 27 closed of 87 — the "17" was a
hand-count and is retracted.


## 2026-09-21 (session 10) — D-317: the human attestation is SIGNED (the evidence base is now attested)

The owner signed the reserved line: `human_attestation: "these 150 labels are mine, made blind to pipeline output."`
(2026-09-21). Recorded in `config/eval_integrity.yaml:ruler_authority.human_attestation` with scope n=150 (100 A +
50 B) and the attested artifact `governance/anchor1_frozen_20260920.json` (sha256 `0ec321a7…`).
Effect: "human-anchored" is **ATTESTED**, not merely verified-by-reconstruction; that owner gate is CLOSED and live
owner gates drop to TWO (laya-mlx benchmark-only install; abstention `t_low = p25`). No published number moves
(CT 0.3533 / DISC 0.4741 / FORM 0.2828, reproduced bit-identical from the authority). Attestation ≠ independence:
F-11 (no second coder) still forbids repointing any floor, and D-317 now requires that a closed gate be reflected in
config in the same session. BUG-344 opened+fixed: the declared pin hashes in config were never read by the scorer, so
the annotation drift guard was INERT in the run path and the artifact cited an empty hash.

## 2026-09-21 (session 10) — D-318: a declared pin is a control only if enforced in the run path
Audit found the pins in `config/eval_integrity.yaml:ruler_authority` were declared but NEVER READ (BUG-344) —
the BUG-340 drift guard was therefore inert and the artifact cited an empty `annotation_sha256`; once enforced,
the authority pin proved to carry a one-character typo (BUG-345, invisible to 16-char prefix checks). Both fixed;
`scripts/pin_audit.py` byte-compares every declared pin (standalone control). A second scorer
(`scripts/score_ruler_labels.py`) is retired (BUG-346) and the R5 verifier now demands quoted evidence (BUG-333).
Quotable pins: authority `0ec321a7…`, workspace/annotation `38323192…`, key `d4cb4595…`, stage5 survivor `2c206a25…`.

## 2026-09-23 (sessions 18-20) — C-1/C-2/C-3, ANCHOR-3, D-338/339/340: READ THIS BEFORE CITING ANY RUN
**Supersessions (do not quote the older claim):**

| older claim (still visible in this file / older reports) | superseded by |
|---|---|
| D-328: abstention ENABLED at p25 | **D-338**: approved IN PRINCIPLE, NOT ACTIVATED (`config/verify_abstention.yaml` = `status: gated`, `enabled: false`, `consumers: []`). D-328 was an unimplemented state assertion. |
| BUG-341: "the LIVE stage5 checkpoint is ABSENT" | **C-3/BUG-376**: the live checkpoint is PRESENT and COMPLETE (7995 = 5023 PASS + 2972 QUARANTINE), but its declared S4 input was rewritten 65 min AFTER the run and the verified image is gone. |
| ANCHOR sha256 `3911eece4555a2da…` | **ANCHOR-3 = `29393d5f9d5292053a39986582578e140121d8987448648ad63f528062cd2698`**, manifest `governance/ANCHOR_MANIFEST_20260923.json`. |
| D-327 "flip recorded as done 2026-09-21" | the flip had NEVER landed; applied 2026-09-23 (`stage4.boundary_inject_enabled: false`). |

**New binding rules (each has a machine check, not just prose):**
* **D-338** — a decision may assert INTENT and name the artifact, never implementation state. An enable/flip ruling
  needs an **implementation receipt** (config sha before/after, consumer, run fingerprint).
* **D-339** — a flag with no declared consumer, or whose state contradicts its cited decision, is a standing RED
  (`scripts/audit_flag_consumers.py` + `config/flag_consumer_registry.yaml`).
* **D-340** — a **declared stage input is immutable**; an in-place writer must publish a mutation notice at the moment
  of the change (`scripts/input_mutation_notice.py`), consumed by `scripts/verify_declared_inputs.py`.
* **BUG-342 rule** — never re-derive a governance count by hand; quote the generator (a hand derivation gave 75 vs the
  parser's 72 and was discarded).

**Frozen/citable artifacts (cite these, never a bare mutable path):**
* `ANCHOR-3` — manifest above; **RELATIVE-ONLY** (D-337): arm ranking/deltas, **no absolute error floor** (D-329/D-331).
* `FROZEN-S5-T11-20260922` — `governance/FROZEN_S5_T11_20260922.json` + `frozen/S5_t11_20260922/` (payload, 191 MB,
  gitignored). Any citation must carry: *"verdicts computed against the S4 image of 2026-09-22T11:26 (`2f8b34fb…`,
  no longer exists); frozen S4 copy is the LATER `0ca6f0f0…` image — same 7995-row corpus, not byte-identical"*.

**`just health` now runs 8 fail-loud checks:** guard_stacks, status, integrity --quick, audit_flag_consumers,
verify_anchor_manifest, verify_declared_inputs, verify_frozen_pair, r3_preflight. A RED here means a governance claim
and reality disagree — do not "fix" the check.

**HUMAN GATE REGISTER (current):** unchanged F-11 (REDEFINED, D-337) · **C-3/BUG-376** (S5 REVERIFY or cite the frozen
pair) · BUG-326 (author + R5 review, then apply — **only after the freeze**, it rewrites S4 rows in place) · R3 (GO;
preflight passes 58/58) · laya (GO, C22 opt-in) · REGISTER FLAGS (proposal ready) · BUG-378 (which S4 image is
authoritative). Open bugs: 73 OPEN / 51 CLOSED of 124 (`governance/bug_status.md`); C15 register in
`governance/SESSION-HANDOFF-2026-09-23.md`.


## 2026-09-23 (session 22) — audit + freeze/evidence/citation controls

| superseded claim | now |
|---|---|
| "BUG-326 repair (403/147/703)" is a live owner gate | **NOT APPLICABLE** — does not reproduce; closed 2026-09-21; gate withdrawn (BUG-380) |
| "S6 commit is the one-word-away terminal step" | the store holds a **different vintage** than the run (BUG-381): PASS 3299/QUAR 4696 (db) vs 5023/2972 (S5 09-22) |
| D-327's measurement = a config note | **frozen receipt** `governance/evidence/D327_BOUNDARY_AB_20260921/` (30/30 vs 0/30) — D-342 |
| S5 t11 verdicts citable from the live path | **D-341**: cite `FROZEN-S5-T11-20260922` + qualifier; the live path is not a citation surface |

**Binding now:** D-341 (frozen-pair citation), D-342 (measurement receipts), D-340 (input mutation notices),
D-338/D-339 (no state claim without a receipt; flag registry). **Health = 9 fail-loud checks** (adds
`verify_evidence_manifests.py`). **Open owner gates:** see `governance/FLAG_HYGIENE_TASKS_20260923.md`, BUG-381, BUG-382,
S5 REVERIFY (optional), R3 GO (staged), laya (recommended DEFER), disk chore.

### Supersession table — 2026-09-23 (session 23)
| superseded claim | now |
|---|---|
| "retrieval/k-NN is dead for the discipline axis" | DEAD only as a mislabel detector (D2575). As a REPRESENTATION it separates discipline (+15.2 pp over the constant) and domains (+22.2 pp) — D-343 |
| "content_type is merely degenerate (F-17)" | measured: kNN 0.7863 vs constant 0.8161 = **−2.98 pp**; classifying it is worse than always emitting the modal label — D-343 |
| "depth is a classification axis" | depth loses to the constant by 16.5 pp ('domain' alone is 82%); route constant+queue — D-343 |
| "ARTIFACT_AUTHORITY.json is written but unenforced" | enforced: 10th health check, 0 RED — D-344 |
- Binding rules: a model may not be adopted on a lift over chance alone; both references (null AND constant) must be beaten. Health = **10** checks.

| "a k-NN / retrieval arm is the cheap fix for discipline" | **DEAD, measured (D-345).** Loses on all three axes (-26.59 / -4.67 / -25.05 pp); 31/150 discipline rows tie. Separability ≠ deployability — D-345 |
| "the 19 remaining ON flags enforce nothing, so bulk FLAGS OFF is a no-op" | **DEAD (BUG-385).** All 19 have readers; OFF would have silently disabled 9 capabilities. Registry 43 verified / 0 RED / 1 unregistered — D-339b |
\n- k-NN/retrieval arm DEAD (D-345) | superseded by D-346 route contract | the quoting of ANCHOR-1 incumbent numbers is DEAD - re-score with scripts/incumbent_ruler_score.py (D-347).\n

## ADDENDUM 2026-09-23 (D-352) - the abstention points were re-scored, and two of them changed

NEW: sampling + reference audit of the ratified abstention points - governance/ABSTENTION_ROBUSTNESS_20260923.md,
     scripts/abstention_robustness.py, config/abstention_robustness.yaml (deterministic, LLM-free, no new inference).
NEW: BUG-391 (HIGH) the ratified discipline figure is not reproducible on the ruler in force (0.4741/116 legacy vs
     0.5533/150 re-scored); BUG-392 (LOW, FIXED) two defects in the checker that produced this audit.
SUPERSEDED-PENDING: the discipline point (-8.3 pp) and the content_type point (-4.2 pp) are marked supersession_pending
     in config/verify_abstention.yaml; re-ratification on ANCHOR-3 is an OWNER CALL. enabled stays false.
VERIFIED, UNCHANGED: the mechanism (the margin does discriminate: AUC 0.7035 [0.620, 0.785]; abstained-bucket error 0.711).
UNCHANGED: no label, menu, definition or pipeline artifact was touched.

## ADDENDUM 2026-09-23 (D-353) - audit (b): one HIGH wiring claim was false, and the abstention points were re-ratified

FIXED: BUG-393 - `just health` did not run the two menu checkers it was reported to run; all three are wired now.
NEW: config/recalibration_pins.yaml + scripts/verify_recalibration_pins.py (the BUG-391 class: a measurement must not survive a change to its own reference).
RE-RATIFIED: D-353 - discipline adopted at 25% abstain (gain 5.33pp, CI [1.37,10.26]); content_type rejected at 30% (CI [-1.81,8.86]).
SUPERSEDED (pointer only, protected files NOT rewritten): the 0.4741/116 figures in eval_integrity/incumbent_ruler_score/knn_arm/REPRESENTABILITY_SWEEP/R3_HELDOUT_RESULT.
DANGLING: ANCHOR1 sheet/key are cited by 7 artifacts and do not exist (blocks the R3 held-out run); temp/ consolidation inputs are untracked.
AUDIT: governance/FORENSIC_AUDIT_20260923b.md (F1..F15).

### 2026-09-23 — audit (c) addendum: D-354 + BUG-394/BUG-395 (vec-store referential audit)

- NEW BUG-394 (HIGH, OPEN): vec_fbs_ctx is 100 percent referentially DEAD (7995 rows, 0 live, 7995 orphans).
- CORRECTION: BUG-387 is not a 'doubling' (see BUG-394). Measured: fbs 7995 (rowids 7997..15991); vec_fbs 15990
  = 7995 live + 7995 orphans; distinct rowids 15990 (no collision); retrieval effect is dilution, not starvation.
- NEW gate D-354: config/vec_integrity.yaml + scripts/verify_vec_integrity.py (read-only, exits 1 TODAY).
  Deliberately NOT in 'just health' until the owner-authorised repair lands (a permanently RED gate is its own tax).
- NEW BUG-395 (MED, OPEN): scripts/verify_boundary_injection.py is run by NO recipe and exits 1 today because
  D-327 rejected the boundary block (stage4.boundary_inject_enabled: false) and the checker has no flag awareness.
  Its 'PASS' in SEQUENCE_STATUS:600 is stale.
- STANDING RULE from audit (c): no NEW retrieval-quality number until the vec orphans are repaired (a number taken
  on a diluted index is on a different ruler). Existing retrieval research predates the dilution and is clean.
