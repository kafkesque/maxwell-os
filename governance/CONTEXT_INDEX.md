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

**REFUTED HYPOTHESES (recorded so they are not re-run):** (a) FTS staleness — `fits_fts` integrity-check **passed**
on a copy; (b) contextual embeddings poisoning production — `contextual_embed.enabled: False`, production vectors
are clean; (c) over-merging making FBs unlabelable — **the opposite holds**.

**RRF / CHUNKING — the direct answer:** RRF is **already implemented and correct** (k=60, `1/(k+rank)`, 1-based,
three legs). Chunk-level retrieval **is** worth adopting, at **step 8**: the DB's `source_segments` (214,220 refs)
join the stage-1 checkpoint **205,813/205,813 = 100%**, so the leg costs **~214k vectors (≈438 MB at 512d)**, needs
no mapping/re-chunking/re-extraction, and returns **verbatim source + section heading + parent-FB link**. But it
fixes **grounding precision, not label accuracy**, the 300/50-word overlap must be collapsed at fusion, and adding a
leg **before F-28 is fixed amplifies the filter leak**.
