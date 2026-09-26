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
| decisions census (total, per-state, by_category, content stamp) | `config/decisions_summary.json` (writer: `scripts/recompute_decision_summary.py`) | **D-2655, 2026-09-26**: a derived value has NO home inside the append-only artifact it describes, so `config/decisions.yaml` is RECORDS ONLY and extends to end-of-file, and the mint is a CHECKED pure byte-append. The census keys' absence from the registry IS the contract |
| suite red ceiling (which tests are DECLARED red + the collection floor) | `config/test_isolation.yaml#suite_rail` (writer: `scripts/check_tests.py`) | **D-2656, 2026-09-26**: the SUITE is a RAIL. The red set is a declared SHRINK-ONLY ceiling (3 ids, all in the depth/domain contract whose status is 'proposed'/owner gate). A NEW failure is FATAL, an unreadable summary or a collection-floor breach is FATAL, a declared red that now PASSES is OWNER-OWED (2). `health-deep` demands the ceiling EMPTY (`--strict`) |

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
| **G6** | decide the Dropbox/synced-folder question (C3) — **PARTLY SETTLED 2026-09-25**: the GIT DIR left the synced tree (BUG-500: git metadata now lives at /Users/barn/maxwell_os_gitdirs/maxwell_os_2_0.git behind a 58-byte pointer, and RAIL 0 FAILS if any git dir sits inside a declared sync domain). **STILL OWED**: the worktree and knowledge pipeline/maxwell.db are still synced — D-366(1-2) accepts that as a dated exception with a torn-upload guard; D-366(4) rejects selective sync | `FORENSIC_AUDIT_20260917.md` F-09 · `governance/dropbox_selective_sync.md` · `config/repo_integrity.yaml` | leak-risk posture |
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

## 2026-09-24 — ANCHOR-3 / ANCHOR-4 ADDED TO THE RECALL MAP (they were missing — BUG-424)

The 150-row **frozen anchor was cited nowhere in this file**, which is the mechanical reason the owner
could not find it (2026-09-24: "I cant find ANCHOR_RULER_CONSOLIDATED"). It exists, in exactly one
place on disk. Three artifacts + two manifests:

| artifact | path | OWNS | key | status |
|---|---|---|---|---|
| **ANCHOR-3** — consolidated 150-row anchor | `governance/ANCHOR_RULER_CONSOLIDATED_20260923.csv` (+ `.md`) | `content_type_final`, `discipline_final`, `extraction_type_final` | `item_id` | **FROZEN** `29393d5f9d529205…`, 150 rows × 31 cols, tier `human-mixed+llm-attested` |
| **ANCHOR-4** — depth blind coding sheet | `governance/ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv` | `DEPTH (1-4)` (EMPTY until freeze) | `item_id` | DERIVES CT/DISC/FORM from ANCHOR-3 |
| **registry + join contract** | `governance/ANCHOR_FAMILY_CONSOLIDATION_PLAN_20260924.md` | which anchor artifact owns which axis | — | live |
| manifests (C12) | `governance/ANCHOR_MANIFEST_20260923.json`, `governance/ANCHOR4_MANIFEST_20260924.json` | sha256 / rows / allowed + forbidden uses / verify command | — | live |

- ANCHOR-3 is **RELATIVE-ONLY (D-337)** — no absolute error floor or "accurate to X" may be cited from it.
- The three context columns of ANCHOR-4 are **DERIVED** by `scripts/consolidate_anchor4_context.py` (the only
  writer; `--check` runs in `just health`) — never hand-edit them, always re-run the generator.
- **ANCHOR-3 ≠ ANCHOR-1/2.** ANCHOR-3 is the *consolidated owner-adjudicated* form of the RULER-150 sheet
  (`consolidate_anchor_ruler.py`, deterministic). Do not concatenate it with ANCHOR-1/ANCHOR-2.
- **The `domains` axis is NOT part of this family.** It is owned by `governance/s4_domain_verdicts.jsonl` on a
  DIFFERENT 216-row cohort that intersects the 150 by **2 rows** (R109, R142); `config/eval_integrity.yaml`
  defers it (`axes_deferred: [depth, domains]`). See the registry, its section "Axes this family does NOT own".

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

## 2026-09-23 - POINTER (B6/D-352): every quoted 0.4741/116 is SUPERSEDED, never re-derive it

The discipline figure 0.4741 (n=116) is not reconstructible (BUG-391) and is superseded by the re-score on the
ruler in force: base 0.5533 (n=150), adopted point 0.5000 at 25 percent abstain (D-353). Do NOT reconcile the
old and new numbers by hand (BUG-342): the old denominator is a SUBSET. Sites still quoting it and their status:

- config/eval_integrity.yaml:341 - POINTED (protected file, floors deliberately not rewritten)
- config/incumbent_ruler_score.yaml:45 - POINTED (same)
- config/knn_arm.yaml:14 - POINTED (same)
- governance/REPRESENTABILITY_SWEEP_20260923.md:76 - POINTED (quoted, never re-derived - correct behaviour)
- governance/R3_HELDOUT_RESULT_20260921.md:36,40 - POINTED; R3 itself is DEFERRED (B5): its ANCHOR-1 sheet/key do not exist

Executed this turn: B7 (temp inputs -> data/anchor_inputs/), B8 (mtp_enabled false). B5 recommendation recorded:
DEFER the R3 held-out run (repointing it to ANCHOR-3 is a new pre-registration, not a fix).

### 2026-09-23 15:27 - audit (d): the state-aware control, the bool coercion, the meter's silent axis fallback

D-355 minted (a control must assert the state it is in) + D-354 synced into DECISION-LOG.md (it had been minted
into config/decisions.yaml and 4 governance files but not into the log, where every D-3xx entry lives - a real
sync gap, closed). BUG-395 is now state-aware AND wired into just health as the 10th control (standalone exit 0,
health exit 0). BUG-388 fixed code-side. BUG-390: the R2 meter can speak about extraction_type (its axis map had
silently fallen back to the DOMAINS list for unlisted axes). BUG-397 opened (two live defaults point at retired or
absent artifacts). F5 CLOSED by measurement: the ANCHOR-3 ruler and all five declared inputs are tracked in git,
so it reproduces from a clone. F7 CLOSED: the only surviving typo is inside a verbatim quote in decisions.yaml.

POINTER (R3): governance/ANCHOR1_BLIND_SHEET_20260920.csv and governance/ANCHOR1_KEY_20260920.json DO NOT EXIST
on disk and are not tracked. Six artifacts still cite them (governance/R3_HELDOUT_PREREG_20260921.md,
governance/R3_HELDOUT_RESULT_20260921.md, governance/FORENSIC_AUDIT_20260921b.md,
governance/FORENSIC_AUDIT_20260923b.md, governance/ARTIFACT_REGISTRY.md, governance/buglog.md). Those citations
are historical and unreproducible as written. The LIVE harness is scripts/r3_preflight.py (inside just health),
which binds source 'anchor2' + authority ANCHOR-3. GO/DEFER on the R3 result stays an owner call (repointing is a
new pre-registration).

## RECALL ADDENDUM 2026-09-23 (session 21) - A2 / depth / which stage gets a student / the sync incident

**Which stage gets a student (the agreement).** S4 CLASSIFICATION ONLY - never S2 (FB text generation, stays
Qwen3-Coder) and never S5 (verification, stays DeBERTa NLI). TWO SEPARATE ModernBERT-base (139M) FULL
fine-tunes, no LoRA (LoRA q_proj/v_proj is a SILENT no-op on disentangled attention, D2578): (a) CRIBS +
discipline/domains (61-way softmax + 43-way sigmoid head), (b) a dedicated 4-way DEPTH head so rare depth
classes are not swamped. Teacher / label oracle = gpt-oss-20b (D2577, user-approved 2026-09-23; D2607 C).
"Overtake" is a HYBRID CASCADE, not a replacement: student pre-classifies, abstain/low-confidence escalates
to gpt-oss, and the KPI is END-TO-END ACCURACY WITH FALLBACK (D2607 C), gated on ARM-3 abstention plus
student readiness, with gpt-oss teacher retirement BLOCKED until the student wins (D2635). It is
DATA-limited, not model-limited: discipline macro-F1 0.2621 -> 0.2036, top-1 27.7%, cannot reach 90%
precision at ANY coverage (best 75% at 4% coverage); the coarse 10-way head (54% top-1) is the better
abstention signal and IS wired (student_classifier.py, coarse_threshold 0.70, override of DISCIPLINE/DOMAINS
only, never depth). Per D274d nothing may be trained, distilled or swapped on the current labels.

**Depth anchor - the honest answer (BUG-415, NEW).** An older manual reference DOES exist and is still in
use: `governance/gold_4axis.jsonl`, 251 rows / 234 with depth, 132 human-derived + 81 joint-vote + 21
reliable-pair revote + 17 n/a = coverage 0.526 vs the 0.50 floor, which is why `axes_deferred: [depth,
domains]` (config/eval_integrity.yaml:220). But NO BLIND ANCHOR exists for depth: the ruler/anchor family
(RULER_BLIND_SHEET_20260917, F11_ANCHOR_REVIEW, ANCHOR-3 150x31) carries ZERO depth columns, and the live
reference is the 996-row 3-voter LLM consensus, which is ADVISORY and RELATIVE-ONLY (D-329/331/337). So the
D2577 depth head cannot be certified and the D274f test-retest is unbuilt. Owner-accepted fix: ANCHOR-4 =
the same 150 ruler rows + a blind `DEPTH (1-4)` column + a second coder, then the 30-row test-retest
(governance/ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv + _RUBRIC_20260923.md). Coder 2 is what turns a coding
into an anchor.

**A2 (reclaim) - superseded rule.** D-370 amends D-369 by append-only note: a model store is classified by
RESOLUTION (readlink + the SERVED-MODEL LIST), never by directory name and never by du (du reports 0 MB for
a symlink then the full size of its target). hf hub is NOT a cache - it IS the serving store for 5 of 7
served models. A digest test is not a deletion test. Safe-reclaim evidence = absent from the serving list +
zero config/code/golden references + a survivor that loads and ANSWERS after restart + a logged restorable
source id. Execute last-verified-first. The current list is
`governance/MODEL_STORE_RECLAIM_A2_CORRECTED_20260923.md` (supersedes the original; ~81.2 GB); NOTHING has
moved and the owner still answers two knowledge questions (the 27.1 GB orphan Qwen3.6-35B-A3B-6bit, and the
20.6 GB .mtplx Qwopus3.6 that model_assignments.yaml calls a phantom).

**Writer incident (BUG-402, FIXED).** `tools/sync_decisions.py` was INVERTED and was run before its own
tombstone landed: it re-dumped config/decisions.yaml (3526+/2259-) and the damage was committed as 934f755.
Recovered from 32404ce (736 records) + D-370 appended surgically (737, stamp 64fddc833723eba3). The tool is
now a hard-fail tombstone (exit 2) and the stamp is derived + checked in `just health`. Standing rule: never
invoke a tool whose retirement is only planned - neuter FIRST, then verify.

**Gates accepted 2026-09-23:** Gate B, Gate E, Gate A/A2, Gate F, the depth anchor, BUG-403/405 (Gate D),
the BUG-410 repoint, A2 execution and the abstention shadow run. Gate F acceptance changes NOTHING today
(verify_abstention.yaml enabled: false, status: gated; abstention is PER-AXIS, so content_type keeps 100%
coverage); the recommendation stands to DROP the content_type 30% point and keep discipline 25%.


## 2026-09-25 additions — REGISTRATION (read before resuming)

**The boot health rail is now LIVE for the first time.** `justfile` had TWO parse offenders (line 13 AND
line 15); both dedented. `just --list` parses; 20/20 declaration rails were run and are GREEN. Standing rule:
a rail that has never run is not a rail.

**New artifacts (this session):**
- `config/depth_domain_contract.yaml` — the depth<->domain consistency contract. `status: proposed`;
  `scripts/validate_depth_domain_contract.py` is non-gating until the owner sets `status: active` (C22).
- `tests/test_depth_domain_contract.py` — the adversarial battery (S1-S12) + real-data regression (rail 5).
- `scripts/build_form_elicitation.py`, `scripts/score_form_gate.py` — FORM instrument + scorer (refuses to
  score an incomplete instrument: exit 3).
- `config/menu_axis_hashes.yaml` + `scripts/menu_axis_hashes.py` — PER-AXIS menu hashing (BUG-453).

**Answers that must not be re-derived by assumption (BUG-422 class of error):**
- **FORM already HAS an anchor.** Read `config/anchor_family.yaml` -> `axes.extraction_type`: owned by
  ANCHOR-3, column `extraction_type_final`, intersection **145/150**, human labels write-locked
  (`extraction_type_human`). The four values are `causal_mechanism / descriptive_model /
  normative_heuristic / empirical_pattern` (config/content_types.yaml, D2323). DEPTH is the un-anchored
  axis (intersection 0). Never answer "does axis X exist" from an artifact's own column.
- **FORM cannot admit depth class 1.** MEASURED (BUG-451): the 7 retractions span 3 of the 4 FORM classes;
  the warrant-admissible pool is 91/150 = 60.7 % vs the 2.7 % class 1 can hold; `empirical_pattern`
  excludes 14 rows and catches 0 of the 7. The un-anchored object is the CLAIM-SHAPE bit
  (comparative + stated exchange rate + boundary) - and it must NOT be named FORM (C21).
- **`menu_hash` is a composite of 7 sub-objects** used as an answer-space pin (BUG-453). Per-axis hashes now
  exist; `answer_space_hash` covers `[domains, abstention]`. MEASURED: artifact->live drift is
  `['disciplines']` ONLY; "answer space moved: NO". D-285 (definitions feed the menu) and D-321 ("the menu was
  not touched") are both half-true; D-321's premise as written is falsified.
- **`flags` names two namespaces** (config flags vs the workbook's per-row flag column) — `audit_flag_consumers`
  cannot see the new consumer (BUG-454). A green rail is not a coverage proof.

**Bug register:** BUG-446 FIXED (two offenders); BUG-447 scoped + made checkable; BUG-448/449 OPEN;
BUG-450 (FORM labels carry no rater) / 451 (FORM cannot admit class 1) / 452 (raw-agreement panel, 2 of 4
models) / 453 (composite pin) / 454 (flags collision) OPEN.

## 2026-09-25 (second pass) - new artifacts, and the traps they close

- **Receipt:** `governance/evidence/AUDIT_20260925_SECOND_PASS/` (`AUDIT_FINDINGS.md` + `EVIDENCE_MANIFEST.json`).
  The buglog's earlier pointer to `governance/AUDIT_20260925_SECOND_PASS.md` was DANGLING - that file never
  existed (F-04); this directory is the receipt.
- **`config/claim_shape_instrument.yaml`** - the D1/D2 instrument declared ONCE (cohort, columns, questions,
  guards). Read by `scripts/build_claim_shape_instrument.py` and `scripts/score_claim_shape_gate.py`.
  The old `build_form_elicitation.py` / `score_form_gate.py` are GONE: they named the CLAIM-SHAPE bit `FORM_*`,
  which collided with AXIS 2 `extraction_type` (D-374, BUG-461), and the builder overwrote the live instrument,
  dropping 2 declared columns (BUG-460). The instrument CSV columns are now `claim_shape_*`.
- **MEASURED, and it corrects a docstring:** `FORM (1-4)` = 145/150 non-blank in the depth blind sheet;
  `extraction_type_final` = 145/150 in the consolidated ruler. FORM IS ANCHORED - the earlier "there is NO FORM
  anchor" was FALSE (BUG-459, third false absence of the cycle; ledger row NEG-002). The blank column is DEPTH.
- **`config/anchor_family.yaml` understates depth:** it says `intersection: 0`, the TRACKED sheet carries
  18/150 owner depth cells (`reviewer=human`, `13.09.26`). BUG-463 - the freeze must start from 18.
- **New rails:** `scripts/check_bug_status.py` (a generated register must equal its re-derivation; the register
  was 13 ids stale while health was green) and `@just --list` as the FIRST line of `just health` (BUG-446's owed
  self-parse probe). `config/agreement_floor.yaml` still has NO consumer (BUG-462) - D-373's floor is a
  decoration until a >=2-rater scorer reads it.
- **Decisions D-377..D-380** (claim-shape != FORM, one declaration; a generator must not overwrite an answered
  instrument; a prose existence-negative must be a measured ledger row; a register must equal its re-derivation).


## 2026-09-25 (third pass) - the aggregate rail was RED, and the depth state has three layers
- **`just health` was RED for a whole pass** (`RED r2_meter: scripts/definition_nli_verify.py CHANGED since it was pinned`). A pinned script was edited in the previous pass and verified with individual rails only; the DIGEST rail only runs in the aggregate recipe (BUG-467). Re-pinned under D-382. **Run `just health`, not a hand-picked subset, after any edit to a pinned/locked artifact.**
- **The 5 recurring ids are 4 open cells + 1 contradiction**: `depth_final_class` blank on R070/R080/R130 (BUG-465), `domains_final` blank on R140 (declared `BLANK-AS-SUBMITTED`), and R040 carrying `emerging` + depth class 3 (a contradiction, not a blank).
- **`owner_answer_needed` is a stale snapshot**, not a worklist: it claims ~150 rows still need a domain that they already have, and misses the cell that is actually blank (BUG-464). Derive the owed set from the data.
- **No missing classification beyond that**: FORM has ZERO claim-bearing blanks (its 5 blanks are all declared `noise drop`), depth is 145/148 adjudicated, domains 147/148. The 28 `DISC (1-62)` blanks are mostly declared noise drops (11) and are the DISC-bridge territory (BUG-326), not the depth/domain contract's.
- **Depth state, declared**: 13.09 partial 18/150 -> 24.09 complete 150/150 (`Copy of ...`, sha `bc1cc956...`) -> 25.09 adjudicated 145/148. Intra-rater alpha 0.914 nominal / 0.896 ordinal (raw 0.710), adjacent-dominated. `config/anchor_family.yaml` no longer says `intersection: 0` (BUG-463).
- **148 vs 150, undeclared**: R003 and R146 are absent from the adjudication workbook with no exclusion rule anywhere (BUG-466).
- `flags` -> `row_flags` (D-383) in the workbook; declared in `config/anchor_workbook_fixes.yaml`.

## 2026-09-25 (fourth pass) - owner-accepted rulings implemented; two audit repairs first
- **The four blocked cells are RESOLVED (D-387/D-388).** R070/R080/R130 carry their 24.09 depth forward (2/3/3, policy: omission is
  not withdrawal); R040 is ruled `arts & culture` (3/3 coders lead there; 'emerging' is the abstention slot, not a domain);
  R140 is DECLARED axis-exempt (CT='noise drop') and reported, never owed. The contract now has **0 hard, 0 owner-owed, 10 soft**.
- **A declared abstention is TERMINAL** (`abstention.terminal: true`): an exit-2 gate that no owner act can close is a gate the
  owner learns to ignore. Owed-ness is now reserved for cells an owner act CAN close (a real blank).
- **`scripts/apply_workbook_rulings.py` is the only writer of an owner ruling, and `just health` runs it `--check`** - because
  `normalize_owner_workbook.py --apply` re-derives a blank and WOULD revert a ruling that lives only in the CSV.
- **BUG-469 FIXED**: the archive rail flipped RED on a Finder-written `.DS_Store` (no content change). OS metadata is now excluded
  from counts and from directory dates. **BUG-470 FIXED**: a live test asserted a literal that D2454 had refuted.
- **OPEN: BUG-471** (the suite fails in one collection order and passes in another), **BUG-464** (stale `owner_answer_needed`
  snapshot; rename deferred), **BUG-466** (148 vs 150 cohort, no exclusion rule), **BUG-468** (digest in prose for a live file).

### 2026-09-25 (fifth pass) - isolation, the deep rail, and the floor's first number

- **BUG-473 FIXED** (severity 1): the suite rotated the LIVE 1.03 GB t11 checkpoint. Root-caused to one test that
  patched the loader but not the checkpoint path; `tests/conftest.py` now fails a session that moves an undeclared
  production artifact (`config/test_isolation.yaml` declares tolerated test run ids; tolerated touches are REPORTED).
- **BUG-471 FIXED**: the order-dependence was the production-lock leak — `S5_LOCK_PATH` is bound at import from
  `STAGE5_CHECKPOINT`, so the first S5 test left a live lock and the second died on it. **BUG-475 OPEN** (the
  pipeline-side structural fix; pipeline/** untouched this pass).
- **`just health-deep` added (D-390)**: the aggregate rail plus the full suite, because a rail does not read the suite
  (BUG-470 hid exactly there). Full suite now: **232 passed, 5 skipped, 0 failed**.
- **BUG-462 CLOSED**: `scripts/depth_pass_agreement.py` is the agreement floor's first consumer. It reports
  **alpha nominal 0.4004 / ordinal 0.5701** on 144 independent units - **below_reporting**, so **the depth axis may
  NOT be frozen** (D-391). D274f is now mandatory, not a formality.
- **BUG-466 CLOSED**: `config/cohort_declaration.yaml` declares 150 declared / 148 measured / R003,R146 absent.
- **BUG-501 CLOSED (2026-09-25)**: a dangling declaration pointer was reported as a pending ruling - `reconcile.py` now calls an unresolvable `declares` key DRIFT in every kind, `optional: true` can no longer launder it, and the cohort denominator is DECLARED (`measured_rows`) + asserted against the workbook by two independent oracles (D-2638, D-402).
- **BUG-499 CLOSED (2026-09-25)**: the label ontology is DECLARED and its rule has ONE home - epistemic_status and status are CO-DERIVED (both functions of the same verification record, label strictly finer), so rail.label_relationship: co_derived in config/serving_gate.yaml and check_serving_gate.py now PROVES it by re-deriving every stored label (0/7,995 mismatch, max_label_mismatch: 0). The rule's three inline copies (stage5_verify, sync_s5_checkpoint_from_db, reinject_bug198_singletons) collapsed into pipeline/serving_gate.py::derive_epistemic_status. Also OPEN: BUG-502 (the duplicate-rule class) and BUG-503 (just migrate-d2205 would add 8 abandoned D2205 columns incl. a 4th epistemic column to fbs).
- **BUG-497 CLOSED (2026-09-25, D-2640)**: the label-provenance quartet (menu_hash + 3 *_source) is empty on 7,995/7,995 rows because the corpus predates the R1/D-279 stamp. Declared as a PRE_PROVENANCE_BOUNDARY in config/label_provenance.yaml (closed set of generation runs + declared measured_rows), classified by pipeline/label_traceability.py, enforced by scripts/check_label_provenance.py (6/6 controls; a row OUTSIDE the boundary without the quartet is a DEFECT), and EXPOSED as the query-surface field label_traceability (pipeline/retrieve.py::_row_to_dict, all four legs). NEVER backfilled (D-277); NOT an R14 exemption.
- **BUG-502 score axis FIXED (2026-09-25, D-2642)**: the S5 score axis (confidence + needs_human_review) was a verbatim copy in stage5_verify.py and reinject_bug198_singletons.py; it now lives once in pipeline/serving_gate.py::derive_conf_and_review and is re-proved against the stored corpus by scripts/check_s5_score_axis.py (7995 MATCH, wired into just health). A re-derivation proof must feed the FULL row.
- **BUG-504 FIXED (2026-09-25, D-2644)**: the five S5 score-axis weights were governed by SILENT CODE DEFAULTS (no stage5.confidence block existed); now DECLARED in config/pipeline_config.yaml and read by a loud _s5_conf() - a config miss is an error again.
- **BUG-503 TOMBSTONED (2026-09-25, D-2643)**: the three justfile recipes that reached the ABANDONED D2205 migration are removed and the script exits 2 (owner-owed) - an abandoned ontology must not have a REACHABLE write path.
- **D274a has BOTH halves now (2026-09-25)**: the pre-write refusal lives in pipeline/serving_gate.py::pre_write_verdict and is called by pipeline/stage6_commit.py::insert_fb (the ONE INSERT path); the same comparator (store_verdict) is imported by the rail - one rule, two enforcement points. MEASURED: 0/7,995 stored rows refused.
- **BUG-474 FIXED**: a duplicate `expect_blank:` key in `config/anchor_workbook_fixes.yaml`.
- **STILL OPEN**: BUG-464 (stale `owner_answer_needed` snapshot), BUG-468 (digest in prose for a live file),
  BUG-475, and the S2/S4 smoke tests that still write under their smoke run ids in the production trees.

## 2026-09-25 (sixth pass) — the panel that was not run, and the class-1 gate question
## 2026-09-25 (seventh pass) — the audit found the data-loss path, and the claim-shape gate was measured

- **BUG-478 HIGH (OPEN, mitigated)**: `scripts/cross_examine_anchor_axes.py::write_outputs` rebuilds the ANCHOR-4 workbook with mode `"w"` and blanks `WORKBOOK_OWNER_COLS` (`domains_final`, `depth_final`, `owner_note`, `owner_date`). The declared way to complete a panel would have destroyed 148 owner cells. Mitigated by `scripts/ingest_panel_column.py` (one column, refuses any other change) + `agreement_floor.yaml#panels.depth_axis_panel.ingest`. Root fix still owner-gated.
- **BUG-480 MEDIUM (OPEN)**: the D-374 claim-shape gate, first measured blind with a NON-AUTHOR elicitor (Qwen3.8-27B, identity withheld, temp 0): negatives **7/7 rejected**, FP **0**, candidates **3/4** (U002 missed) -> **10/11**, so `score_claim_shape_gate.py` exits 1 and class-1 admission stays UN-GATED (D-395's own bar is 4/4). `q3` (boundary) = **11/11** -> it is a CONSTANT on this cohort and gates nothing; only q1/q2 discriminate.
- **D-397** depth load-bearing is now a RAIL (`scripts/check_depth_load_bearing.py` reads `depth_domain_contract.yaml#load_bearing.forbidden_traces`); **D-398** panel ingest path; **D-399** the claim-shape measurement.
- **BUG-476 ROOT RESOLVED AS A DECLARATION**: the panel now declares `rater_status` (3 `run`, 2 `declared_not_run`) instead of leaving two empty columns that alpha cannot distinguish from skipped rows.

- **BUG-476 OPEN (rail FIXED, root OPEN, severity HIGH)**: `config/agreement_floor.yaml#panels.depth_axis_panel`
  declares FIVE raters; only THREE rated. `Qwen3.8-27B-MLX-4bit_depth` = **0/148** and `deepseek-v4-pro_depth`
  = **0/148** (both hold 148/148 on the DOMAIN axis - the depth pass was never run for them). alpha is
  missing-cell capable, so an EMPTY COLUMN was invisible and the receipt said "5 declared rater column(s)".
  FIX: the consumer now prints `raters rated` per rater, names every zero-rating rater, and `--gate` fails on it.
- **The depth reading, decomposed** (all measured this pass, 144 units): alpha nominal **0.4004** / ordinal
  **0.5701**; LLM-only (claude+kimi) **0.5472/0.6397**; owner vs claude raw 0.507, owner vs kimi raw 0.590;
  leave-one-out: drop kimi 0.2701, drop owner 0.5472, drop claude 0.3875. **86% of disagreements are
  off-by-one** (2<->3 x75, 3<->4 x66), 60/144 units unanimous, 3 units span the whole menu -> the ORDERING is
  sound, the BOUNDARY fails. Class 1 is 2.1-4.9% of ratings, so alpha there is uninterpretable
  (**+0.1730 nominal on 91.5-95.8% raw agreement** — the kappa paradox, not disagreement).
- **D-394**: the depth axis is NOT load-bearing (no gate, no anchor edit, no head); the panel must be made TRUE
  before any new rater is bought; D274f (window opens 2026-10-08) is the next measurement; the completed panel is
  the falsification test of Spearman-Brown (0.5472 at 2 coders -> ~0.83 at 4 IF errors are independent).
- **D-395 / BUG-451**: FORM is demoted from candidate gate by measurement (catches **1 of the 7** retracted
  class-1 calls; warrant pool 91/150 = 60.7% vs a 2.7% class-1 capacity). The class-1 gate is the **D-374
  CLAIM-SHAPE bit**, judged as a DECISION RULE against the declared cohort (7/7 negatives rejected, 4/4
  candidates admitted), NOT by alpha. A FORM 4-coder panel would buy a reliability number for an axis that is
  already owner-anchored and cannot gate - rejected as future tax.
- **BUG-477 OPEN**: the FORM coder columns hold `label (margin)` strings, and `owner_form` is declared but
  **0/108** - the same declared-but-empty defect as BUG-476. Any FORM agreement figure needs a declared parse.
- **`just health` RED at line 20 was `check_bug_status.py`**: appending to `governance/buglog.md` makes
  `governance/bug_status.json|md` stale and the rail correctly fails until `python3 scripts/bug_status.py`
  is re-run (OPEN 111 / CLOSED 108 of 219). Not a defect - the rail working. STANDING RULE: after any buglog
  write, re-run `scripts/bug_status.py` before `just health`.

## 2026-09-26 - THE DECODE RULE HAS ONE HOME (BUG-516 sweep; recall map, BUG-424 class)

New artifacts (register them before looking anywhere else in the repo for an encoding decision):
- `scripts/lib/artifact_encoding.py` - THE home for "read an artifact in the encoding it DECLARES" (D-2644/D-2649).
  Joins the config declaration with the byte-level declaration (BOM / valid UTF-8). A disagreement FAILS CLOSED
  naming the artifact, both encodings, both homes and the first diverging character. 14 known-answer controls.
- `scripts/check_encoding_homes.py` + `config/encoding_homes.yaml` - the AST rail that makes the D-2646 one-home
  invariant MACHINE-DETECTED (not grep, not memory). ceiling 12 -> 0 on 2026-09-26; SHRINK-ONLY (D-2642).
- `scripts/lib/yaml_guard.py`; `governance/CONFLICT_REGISTER.md` (both added 2026-09-26).

SUPERSEDED CLAIM: "the repo carries latin-1 sheets" - MEASURED FALSE. The owner instruments are Mac Roman, and the
latin-1/cp1252 fallbacks turned the owner's em dash into "N-tilde" without crashing (BUG-511/BUG-514). Declared
encodings live in `config/reconciliation.yaml#artifact_encodings` (3 artifacts, all mac_roman).

## 2026-09-26 - THE C16 SILENT-REPAIR CLASS HAS A DETECTOR, AND THE OPERATOR-KEY RULE HAS ONE HOME

- `scripts/lib/operator_env.py` - THE home for "the operator's key: --flag, environment, or the repo's .env" (BUG-519, D-2646).
  Reads `.env` through the DECODE home, so a non-UTF-8 byte FAILS CLOSED instead of being dropped. 10/10 known-answer controls.
  `.env` is NOT declared in `config/reconciliation.yaml`: it is gitignored, so a tracked declaration would be unverifiable.
- `scripts/check_silent_repair.py` + `config/silent_repair.yaml` - the rail that makes "no reader silently repairs bytes" (C16)
  MACHINE-DETECTED: `allowed` (runtime logs / foreign streams) | `debt` (artifact reads, SHRINK-ONLY ceiling 20) | NO ENTRY = DRIFT.
  An entry with no measured site is reported STALE. 12/12 controls. Wired into `just health`.
- SUPERSEDED CLAIM: "the silent-repair reads are a style issue" - MEASURED FALSE. Fourteen of 32 sites read repo artifacts or
  source text, where a repair is not robustness but an error leak (BUG-511: no crash, changed text).
- MEASURED blind spot: `tools/` was NEVER in the first errors= census; the rail's scan_roots now include it (4 sites declared).

## 2026-09-26 (second pass) - THE PIN RULE NOW HAS ITS WRITE MOMENT (BUG-526)

`just health` was run to COMPLETION for the first time today (it had been aborting at line 22). It reports three
independent states, and TWO of them were created by this assistant's own work hours earlier:
1. RED line 22 `check_bug_status.py` - appending BUG-525 to `governance/buglog.md` (13:59) made the DERIVED register
   (`governance/bug_status.json|md`, last built 12:34) stale. The rail working, not a defect. Re-derived:
   OPEN 120 / CLOSED 142 of 262. STANDING RULE: after ANY buglog write, re-run `python3 scripts/bug_status.py`
   BEFORE `just health`.
2. RED line 69 `verify_recalibration_pins.py` - `scripts/definition_nli_verify.py` is digest-pinned as the r2_meter
   reference (D-382) and its bytes moved TODAY at 12:44 (a `provenance:` block added to the R2 report + the BUG-522
   one-rule decode home). Both changes are SEMANTIC, so the ratified R2 measurement is no longer reproducible from
   the tree. OWNER-OWED: re-measure and mint. A self-minted pin update would be laundering.
3. WARN-only: ANCHOR-4 context DRIFT (5 problems, expected - BUG-431 owner gate) and the depth/domain contract's 38
   hard findings (status 'proposed', suppressed by `--gate-if-active`).

NEW / CHANGED HOMES (read these before touching the pins or the hook):
- `scripts/verify_recalibration_pins.py` - the pin rule at BOTH moments: `--staged` (WRITE gate, driven by the
  pre-commit hook) and no-args (SCAN gate in `just health`). 6 known-answer controls (BUG-492), including the
  OVERREACH control: a staged set naming no pinned artifact is TOLERATED while the tree is RED. The digests still
  have ONE home (`config/recalibration_pins.yaml`); this module never restates them (D-2646).
- `scripts/install_git_hooks.sh` - the ONLY HOME of the installed pre-commit hook, now with `--check`: the hook is a
  DERIVED artifact and must equal its own re-derivation. MEASURED: the strongest gates in this repo lived OUTSIDE
  version control, where no rail could see them drift. Wired into `just health`.

SUPERSEDED CLAIM: "a rail in `just health` is an enforced invariant" - MEASURED FALSE. An invariant enforced only at
scan time is unenforced during the interval in which the work happens; the commit is the act that makes an edit
permanent, and it did not consult the pin. `just health` was NOT run between 12:34 and 14:11 today.

### 2026-09-26R - rail 0 un-saturated (BUG-547); 6 Dropbox siblings vaulted; may_touch widened by 5 NAMED paths
- `scripts/check_repo_integrity.py` - rail 0 now CONSUMES `archive_dir` from `config/conflict_policy.yaml`: an
  ARCHIVED sibling is a FIXED POINT, not a finding. MEASURED before the fix: 36 owner-owed rows, 30 of them its own
  archive, saturating the exit-2 gate so it could not signal a NEW divergence. Controls 9 -> 10, TWO-SIDED (BUG-492).
  rc=0: `0 conflict-marked names in 2 sweeps`.
- Dropbox sibling disposition (D-2647): vault `~/maxwell_os_conflict_snapshot_20260925/vaulted/`, manifest
  `RESOLUTION_20260926.jsonl`, 6 rows, NO byte deleted. workbook = SUPERSEDED-BY-DECLARED-RENAME;
  bug_status.json|md = SUPERSEDED-BY-REGENERATION; stage5 input_fingerprint = OWNER-OWED-PIPELINE-STATE (measured
  Dropbox REVERT: the sibling is NEWER and names HEAD 96b1e9c while the live file names 81b813f); 2 pytest caches =
  CACHE-NO-GIT-BASE.
- SUPERSEDED CLAIM: "`may_touch` is this session's contract". MEASURED: it enumerated ONE mission's artifacts and
  left every LATER session's record-keeping surface outside it - `DECISION-LOG.md` was already MODIFIED (16
  uncommitted lines minting D-2649) and REFUSED, and `governance/RECONCILIATION.json` (a DECLARED artifact,
  `writer_of_record: scripts/reconcile.py`, `derived_regenerable`) was not in git AT ALL. WIDENED by FIVE
  NAMED PATHS (widening_log entry 15), never globs.

### 2026-09-26S - the plan stops lying to its own reviewer (BUG-548 FIXED; `widening_log` now CHECKED)

- **BUG-548 (HIGH, FIXED)**: `widening_log` was a RECORD WITH NO CONSUMER. FOUR of 15 entries claimed widens that
  `may_touch` never granted (`governance/ANCHOR4_MANIFEST_20260924.json` #1, `governance/CONFLICT_REGISTER.md` #6,
  `scripts/*.sh` #9, `governance/NOT-YET-EVALUATED-RESEARCH.md` #14), so the plan documented permissions it did not
  give - and two artifacts were dropped from COMMIT 1 the same day by that gap. `scripts/check_session_plan.py` now
  CHECKS the log (5 new controls, 2 anti-overreach); the four paths are GRANTED as NAMED paths (entry 16) and the
  glob is WITHDRAWN in favour of the exact path `scripts/install_git_hooks.sh`.
- **SUPERSEDED CLAIM**: "a widening_log entry is a permission". It is a RECORD. The permission is `may_touch`,
  and only a rail that reads the record can make the two agree (D-2649 applied to the plan itself).
- **SUB-FINDING, OWED**: `fnmatch` makes `*` cross `/`, so `scripts/*.py` grants `scripts/lib/**` - `may_touch` is
  LOOSER than it reads. Entries #5/#7 were granted by accident. Tightening it is its own decision.
- **D-2657 (OPEN)**: the rule above, minted. `config/decisions.yaml` is records-only (D-2655), so the mint is an
  append + `recompute_decision_summary.py`, never a mid-file edit (BUG-539).


### 2026-09-26S - the register that points at CODE stops pointing at COORDINATES (BUG-542 class fix; the ladder is unblocked)
- **BUG-542 FIXED (class; third occurrence)**: `config/silent_repair.yaml` keyed rail 0's repair site by `lines: [280]`; rail 0's BUG-547 edit moved it to 306, so ONE site was reported TWICE (STALE 280 + DRIFT 306) and the FATAL DRIFT **aborted `just health` at justfile line 51** - every rail below it, including the R2 OWNER-OWED pin, never ran. Sites are keyed by CONTENT (`match:`) now; `scripts/check_silent_repair.py::declared_sites`, 24/24 controls.
- **SUPERSEDED CLAIM**: "BUG-542 REMEDY APPLIED 2026-09-26" (buglog). What was applied was a new LINE NUMBER. A coordinate fix is not a class fix.
- **HERO FACT**: the ladder's RED at line 51 had nothing to do with the R2 pin - and the R2 red was BELOW the abort, so it could not be seen at all (BUG-457).
- **D-2658** (OPEN, owner ratify) - the rule, its home and its proof.
- **BUG-549 FIXED (class)**: the store-authority rail could not tell a STORE from the FINGERPRINT OF NOT-A-STORE, and the SANCTIONED deletion path (safe_delete copies to backup/deletions/{ts}/ before deleting) re-manufactured the same FATAL; fixed with a DECLARED tombstone region (preimage_regions:, counted and bounded) plus EMPTY-STORE named by CAUSE; controls 9 -> 16. D-2659.
- **BUG-550 FIXED (record repaired; class OWED)**: the D-2659 mint CLONED D-2658's files/bugs/rationale - the id and the title were D-2659's, the payload was D-2658's. Found by the PRE-COMMIT forensic audit of the A1 bridge + BUG-549 change-set, before either record landed; repaired IN PLACE (a first commit that never happened is not history, so BUG-539 stands) and the summary re-derived. OWED: minting has NO HOME and NO validator - a receipted minter (next free id; non-empty title/rationale; named files exist; named bugs exist; the rationale NAMES its bugs) with a cloned-payload control.
- **BUG-551 FIXED**: the anchor<->corpus bridge exited 2 on the GOLDEN side while `declared_unresolved` was `[]` - the verdict claimed a declaration nobody made (the BUG-548 class, on the receiving side). `declared_golden_unjoined:` now names both ambiguous golden rows (S4-GOLD-MINED-00478, S4-GOLD-MINED-00600) with a why; UNDECLARED unjoined = 1 (DRIFT), DECLARED = 2, thin why = 1, a declaration that starts JOINING = 2 (shrink-only, loudly). Controls 15 -> 19; the artifact now records `unjoined_detail` (cause + candidates).
- **BUG-552 FIXED / D-2660 (the mint's FIELD-LEVEL join)**: --mint validated a record's SHAPE and never its CLAIM, so BUG-550 (a record carrying another record's files, bugs and rationale) was invisible to every rail. FIX: four clauses in the mint's ONE home (scripts/recompute_decision_summary.py) - next FREE id; cited bugs exist in governance/bug_status.json; the payload names its OWN bugs; every cited file exists; a whole-payload CLONE is refused by name. Controls 0 -> 10 (incl. the control record having to PASS), wired as --selftest. FORWARD-ONLY: 559/790 landed records carry no title and 26 file citations do not resolve - the rule applies at the MOMENT OF MINT and never rewrites history (BUG-539). ORDER MATTERS: register the bug BEFORE the decision that cites it - the gate now refuses the reverse.

- **BUG-553 FIXED / D-2661 (the coordinate join)**: `table:`/`column:` of every registry row were read by NO rail -
  a row could cite a coordinate that exists NOWHERE and the rail stayed green (BUG-550's class again: a mismatch
  inside one record no rail sees, because no rail reads two fields of one record together). FIX: a 4th clause in
  scripts/check_derivation_homes.py - every cited `table` must name a `coordinate_homes` entry whose `kind` is
  machine-distinct: `document` (exists, parses, `column` is a TOP-LEVEL KEY, producer exists) or `store_census`
  (DELEGATED to config/store_columns.yaml: `rail` exists, declared table EQUALS the row's, `column` in the map at the
  declared `membership:` path). NO store is ever opened (vec0 -> `no such module: vec0` would be fatal day one).
  Controls 7 -> 23; 3 negatives SEEN to fire on live bytes. Cascade fixed first: silent_repair.yaml keyed this rail's
  own site by `lines: [78]` -> re-keyed to `match:` (D-2658 applied to its own register).

- **BUG-554 FIXED / D-2662 (the PARITY join)**: scripts/check_derivation_homes.py gained its 5th clause - a cited
  parity_rail must EXIST and the LADDER DECLARED at config/derivations.yaml#enforcement.ladder (justfile) must INVOKE
  it as a whole token on a recipe line; a mention in a comment is not a run; a row claiming status homed may not
  leave it null (two fields of ONE record joined, the BUG-550 class); an unreadable ladder fails CLOSED. Controls
  23 -> 32; 4 negatives fired on LIVE bytes (registry restored byte-identical); silent-repair debt UNCHANGED 17/17
  and config-defaults rc=0 (no cascade). VALUE parity stays each parity rail's own job - re-measuring it here would
  be a second home (D-2646).

- **BUG-555 FIXED / D-2663 (the R2 pin re-mint)**: `scripts/definition_nli_verify.py` is pinned at e2ced5fa... under
  D-2663 (the scan is `0 DRIFT, 0 OWNER-OWED`). The debt D-382 left is closed by MEASUREMENT - the same frozen
  probe under HEAD ca91c520... and the final bytes gives the SAME `results` sha a4c9a1d6f37433a1, the same counts
  231/21/0, and only an added `provenance` key - never by the prose word "additive". The audit the re-mint forced
  found BUG-555: `coder_key_present` was a SUBSTRING test ("coder" in the whole raw text) that printed `true` on
  400/400 live records carrying NO `coder` key (the BUG-528 class inside the BUG-450 block); it is a membership
  test on the parsed rows now, with counts and 4 controls at `--selftest`.

- **BUG-537 FIXED / BUG-556 FIXED / D-2664 (the archive index)**: `archive/index.yaml` silently de-listed
  `.DS_Store` when the BUG-469 ignore block landed (the block blaming the 2026-09-26T15:54 remedy run is
  CORRECTED with both digests: `ecfe29517a941e1b...` already had 32 entries and no `.DS_Store`; HEAD `07e8e3559727bc99...`
  still had it). The index now carries an `excluded` census and `--check` asserts indexed-or-declared-excluded;
  the unreachable `^\.DS_Store$` rule is deleted and `shadowed_rules()` exits 2 on that shape. Chasing it found
  BUG-556: a transient SQLite sidecar (`-shm`, mtime written by the health run itself) moved the rail's own input
  (files 3/135528448 B/2026-09-19 counted vs files 1/135495680 B/2026-09-17 excluded). 7 controls at `--selftest`.

### D-2666 (2026-09-26) - RATIFY: the depth/domain ruler is ACTIVE, the certified workbook is restored (4th instance of the artifact_encoding join)
- `config/depth_domain_contract.yaml` status: active (owner_gate: RATIFY). Its validator is now GATING: `just health` runs it (tri-state guard) and its 38 former findings are the scheduled work list.
- The live workbook is the CERTIFIED generation again (972def3224a1abba), and its pre-ruling image (f2778a488610cbf1) is a declared sealed revision locator re-derived from git:44c249b. The foreign body (574aafef64f0cff7) survives only in backups/ + the sealed blob store, as evidence.
- The workbook's encoding has ONE value in all THREE homes: `utf-8`. Read `config/reconciliation.yaml#artifact_encodings` for why a declaration measured off the bytes on disk is how a foreign body becomes certified (BUG-558).
- BUG-559 (a receipt cut over bytes joined to no revision), BUG-560 (the applier writes a human_authored artifact outside write_guard): both OPEN, both named in the register.
- The suite ceiling is 0 (was 3) and SHRINK-ONLY: the 3 declared red ids were red ONLY because the ruler was unratified.
