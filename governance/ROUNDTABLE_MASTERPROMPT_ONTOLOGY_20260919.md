# LLM ROUNDTABLE — MASTER PROMPT
## Ontological accuracy, classification-drift elimination, and the reliability of the Maxwell OS knowledge runtime

**Document ID:** ROUNDTABLE-ONTOLOGY-20260919
**Prepared:** 2026-09-19
**For:** Claude / GPT / Gemini / Grok / any frontier model acting as an independent reviewer
**Roundtable protocol:** each participant answers independently, from the same evidence, **before** seeing another's answer
**Subject artifacts:** `governance/ONTOLOGY_FORENSIC_20260919.md` (diagnosis), `governance/MARKET_RESEARCH_ONTOLOGY_20260919.md` (candidate solutions), `governance/ruler_measurement_20260917.md` (the measurement), `governance/RULER_MENUS_20260917.md` (the vocabulary's coding manual)

---

## PART 0 — YOUR ROLE AND YOUR OBLIGATION

You are a **Tier-1 Senior RAG & Knowledge Architect**: you have shipped production retrieval systems, you have designed and audited controlled vocabularies, ontologies and taxonomies, and you have run corpus-scale evaluation. You are not a cheerleader.

**Your obligation on this roundtable is to falsify, not to agree.** The person who commissioned this has been told six times that the system is nearly ready and has watched six new failure modes appear. Therefore:

- **Resolve, don't search blindly.** The bibliography is `governance/REFERENCE_LIBRARY_20260919.md` (~45 works with a DOI-verified identifier, a role, and the specific finding each supports). Read it **before** doing your own market research, cite by its `id`, and **say explicitly if you find work that is not in it** — an omission is a finding about this brief, not just about your search.
- **If a proposal below is wrong, say so and explain the mechanism of failure.** A polite summary is a wasted turn.
- **If you agree, you must add something the proposal does not contain** — an edge case, a cost, a second-order effect, a citation, or a measurement that would change the decision.
- **Anything you cannot verify from the evidence provided must be marked `[UNVERIFIED]`.** Do not silently invent. Numbers you assert will be checked against the artifacts.
- **Do market research yourself** where you have access. Cite real work with a DOI/arXiv id. If your retrieval returns nothing, say so — do not fabricate a plausible citation.

---

## PART 1 — THE SYSTEM (what it is and what it must be)

**Maxwell OS** is a personal, sovereign knowledge-extraction runtime. It ingests a personal corpus (~1,000 books, EPUB/PDF → Markdown) and produces **Foundation Blocks (FBs)** — atomic, reusable knowledge objects with full provenance. It is used for personal navigation and retrieval (design, business, self-improvement, plus fringe interests).

**The 8-stage pipeline (CONSTITUTION §2):**

```
stage0        EPUB/PDF → MD (Pandoc/Docling)
stage0.5      MD → author/title (LLM)
stage1        MD → segments + SHA-256 dedup
stage1.3      regex prefilter (drops TOC/copyright/bibliography/nav)
stage1.5      bge-m3 embeddings + FAISS cosine + SOURCE DIVERSITY  → clusters
stage2        cluster → convergent FB (name + definition/mechanism/boundary/consequence/
              application/failure_mode) — Qwen3-Coder-30B          ← NO DISCIPLINE LABEL HERE
stage4        FB prose → LLM FREE-GENERATES a raw discipline + raw domains  ← THE LABEL IS BORN
              raw string → synonym/alias table → canonical, else "emerging"
stage5        DeBERTa-v3-large NLI, fail-closed: ENTAIL ≥0.10 → PASS; NEUTRAL → QUARANTINE; CONTRA → QUARANTINE
stage6        SQLite (sqlite-vec) + Parquet export
```

**IRON RULES that constrain every answer you give (these are non-negotiable for the client):**
- **C1** — $0 marginal cost: all generation/verification on local hardware. No API calls in the pipeline.
- **C2/C4** — no vendor lock-in; open formats; multiple model families.
- **C3** — sovereign; all data and compute stay local.
- **C12** — never hardcode any value (paths, thresholds, model names, magic numbers) → `config/*.yaml`.
- **R5/C8** — generator ≠ verifier; verification uses a **different model family**.
- **R14** — every persistent object stamped with `schema_version`, `gen_model`, `pipeline_commit`.
- **C6** — crash-safe writes (tempfile → fsync → os.replace). **R-D410** — never delete pipeline output.
- **C21** — every component behind a protocol/abstraction (swappable).
- **$0 + local + swappable** means: any solution requiring a hosted service, a paid API, or a new runtime dependency is **out of scope unless it is optional and off by default**.

**The 5-axis label ontology (all in `config/`):**
1. `content_type` — ROLE: 5 roles (`principle`, `process_template`, `process_instance`, `tool_instruction`, `growth_edge`) + 2 dispositions (`noise_drop`, `quarantine`). *Two vocabularies in one column.*
2. `extraction_type` — FORM (epistemic form): `causal_mechanism`, `descriptive_model`, `normative_heuristic`, `empirical_pattern`, each with a `verification_standard`.
3. `depth` — `universal | cross-domain | domain | specialized`
4. `discipline` — SINGULAR, 61 canonical values (+ `emerging`)
5. `domains` — MULTI-LABEL, 43 canonical values, contract 1..3

---

## PART 2 — THE EVIDENCE (measured 2026-09-17/19; do not re-derive, but do attack)

### 2.1 The blind ruler (150 rows; 100 proportional stratum A + 50 forced-minority stratum B)

A human labelled 150 rows **blind** (sheet contained zero stored-label columns; answer key in a separate file). Stratum A is proportional and is the ONLY legitimate floor denominator.

| axis | n scored | unanswered | stored-label accuracy | 95% Wilson | constant-answer baseline | lift | floor 0.60 | verdict |
|---|---|---|---|---|---|---|---|---|
| `content_type` (ROLE) | 100 | 0 | **0.740** | [0.646, 0.816] | **0.750** ("principle") | **−0.010** | PASS numerically | fails the +0.15 margin rule ⇒ **no better than a constant** |
| `discipline` | 83 | **17** | **0.506** | [0.401, 0.611] | 0.084 | +0.422 | floor inside CI | **UNRESOLVED** (needs ~85 more rows) |
| `extraction_type` (FORM) | 89 | 11 | **0.831** | [0.740, 0.895] | 0.360 | +0.472 | **PASS** | decisive, best axis |

Reviewer sanity: confidence is monotone with correctness (FORM: conf 1.0→90%, 0.8→76%, 0.6→0%). 31 cells were typos of real labels (`casual mechanism`→`causal_mechanism`), 2 cells used a non-existent label (`leadership`), and 29+22 cells were left **blank** — 21 of the 29 blanks are in the untraceable pocket.

### 2.2 Where the drift comes from (the root cause, from source)

`pipeline/stage4_merge.py:472` — `"""Build a FREE scientific classification prompt — no canonical lists.`
`pipeline/stage4_merge.py:341` — *"CRITICAL: Classify based on what the principle IS, not what label fits best from a predefined list. Use precise, scientifically accurate names… do not round it off."*
`pipeline/stage4_merge.py:500` — *"(Use the most precise discipline name you know — not generic buckets)"*

This is deliberate design (**D2138**: two-stage "classify freely, then map"). Meanwhile the module docstring at line 13 claims *"single-pass prompt lists all valid labels inline (D316)"* — **the documentation contradicts the implementation.**

**Measured consequences:**

| `taxonomy_match_method` | rows | share | human agreement (discipline) |
|---|---|---|---|
| `synonym` (table rescued the label) | 3,990 | **49.9%** | **0.49** |
| `exact` | 2,127 | 26.6% | **0.61** |
| `emerging_real` (no home → dumped) | 1,181 | **14.8%** | **0.33** |
| `alias` | 697 | 8.7% | 0.57 |

Raw label space: **1,089** distinct raw discipline strings → 61 slots (17.9:1). **4,982** distinct raw domain members → 43 slots (**115.9:1**); only 31 of the 4,982 are canonical; **61% are hapax** (appear once in 7,995 rows). `config/alias_map.yaml` holds **999 curated rescue rules** (362 discipline + 637 domain) for 104 slots — 14.8:1 for domains.

**Chronology:** `taxonomy_v5.yaml` added 2026-07-20 (same commit as the v2.0 pipeline). `alias_map.yaml` added **2026-09-02, six weeks later** — it is a post-hoc drift ledger, not a synonym list.

### 2.3 Which labels fail (the vagueness, located)

| stored discipline | n | human agreement |
|---|---|---|
| `typography`, `information science`, `organizational theory` | 3 each | **1.00** |
| `research methodology`, `human-computer interaction`, `operations research` | 6 each | 0.83 |
| `design thinking`, `strategic thinking` | 7 each | 0.57 |
| `psychology` | 9 | 0.44 |
| `behavioral economics` | 5 | **0.20** |
| `cultural design` | 3 | **0.00** |
| `emerging` | 9 | **0.11** |

**Abstract / hybrid / coined / method-named labels fail; concrete discipline-of-record labels succeed.** ~10–12 slots carry the drift.

### 2.4 The hidden 40.7%

`status`: **PASS 4,745 (59.3%) · QUARANTINE 3,250 (40.7%)**. Retrieval **defaults to `status='PASS'`**.

- **1,780 rows labelled `principle` are hidden** from retrieval.
- 2,940 hidden rows carry a real, non-`emerging` discipline.
- `contradicts_fbs` is **NULL for 100% of rows** — contradiction is never recorded, and stage 5 collapses `NEUTRAL` (unverifiable) and `CONTRA` (contradicted) into the same `QUARANTINE`.
- `PASS ⟺ content_type='principle'` **exactly** (4,745 = 4,745; **zero** non-principle rows pass). In production the 5-role ontology has **one effective value**.
- All 1,470 non-principle rows also have **empty `depth`** → `depth` is undefined for every non-principle object.

### 2.5 Relevance has no axis

`noise_drop` (1,055 rows) fuses two different questions: *"this is not an extractable object"* (ontological) and *"this is true but irrelevant to me"* (user-relative). The blind reviewer said this out loud ~10 times, e.g.: *"it's a valid fact but irrelevant… too niche, nothing to do with any of my interest (design, business, personal improvement) so closer to noise drop"* and *"CRT is already outdated so it could also be quarantine, but since I'm interested in old tech it can be still relevant."* There is nowhere in the schema to store that.

### 2.6 The schema is 53% dead

**24 of 45 attribute columns are dead or near-dead (>90% one value).** Genuinely dead (not stamps): `contradicts_fbs` (NULL 100%), `classification_status` (`CLEAN` 100% — the write-boundary validator has never reported anything), `classification_errors` (`None` ×7,993, so the 1,002 domains-contract violations were never recorded), `provenance` (`llm_extracted_from_source` 100% — the tier system is unused), `prerequisite_fbs`/`procedural_skill` (empty 100%), `usage_count`/`last_retrieved_at` (`0`/`''` 100% — **no retrieval telemetry at all**), `feedback_score`/`feedback_count` (empty 100%), `borp_score` (0.0 100%).

Also: 67.5% of the KB is single-source; convergence does **not** predict label agreement (1 src → 0.54, 2 src → 0.37, 3+ src → 0.55).

### 2.7 THE AXIS INVERSION (the central structural claim)

| axis | measured human reliability | used in retrieval? | filter |
|---|---|---|---|
| `extraction_type` (FORM) | **0.831** | **NO** | — |
| `content_type` (ROLE) | 0.740 (−0.010 lift) | via `status` only | — |
| `discipline` | **0.506** | **YES — primary** | `discipline = ?` exact |
| `domains` | unmeasured | YES | `domains LIKE '%x%'` substring (non-sargable) |
| `depth` | unmeasured | YES | `depth = ?` exact |
| `status` | — | YES | default `PASS` |

**Claim: the axes are ordered inversely to their measured reliability relative to their retrieval load. An exact-match filter on a 0.506-accurate label over a 59.3% slice of the KB is the mechanism behind "every day a new weak point appears."**

### 2.7a CORRECTION TO §2.7 (second pass, same day) — the filters do not filter

`search_hybrid` applies the facet predicate to **one of three legs**: `search_fts` and `search_vector` accept **no**
facet parameters, only `search_keyword` applies `discipline = ?` (and it is called only when a filter is present),
and the fused ranking is truncated with **no post-filter**. Measured on the live DB with
`discipline='typography'`: **2 of the RRF top-10 rows were not typography.** So the row above should read
"**intended** filter — does not constrain the result set". This is a correctness defect **independent of label
quality** and it precedes every labelling question (BUG-285).

### 2.8 SECOND-PASS FINDINGS (the parts the first pass did not examine)

**a) The write guard destroys a label the ruling made legal (CRITICAL).** `validate_discipline_domain` fires on the
discipline alone (`'research methodology'` with **any** domains, or none) and is a hard error at
`stage4_merge.py:823` (quarantine) and `stage6_commit.py:402` (**REJECTED**, never inserted). **D-271a ruled the
opposite** ("DECLARED HOMONYM — change nothing"). Every *new* row labelled `research methodology` therefore dies at
the write boundary; the 261 existing rows predate the guard. **Consequence for the proposed R1:** a closed menu of
the 61 canonical disciplines includes `research methodology` (one of the *most* reliable labels at 0.83 human
agreement) — **so R1 as specified would get every correct answer for that label destroyed.** (BUG-286.)

**b) Graph expansion re-admits the quarantined 40.7%.** `graph_expand` selects neighbours with **no status
predicate** and `search_graph` defaults to `include_contradictions=True, include_prerequisites=True`. Seeds are
PASS-only; neighbours are not. Because the edges were built from `discipline_overlap`/`domain_overlap` over labels
that were ~50% wrong, expansion both leaks NLI-unverified content and **propagates label error structurally**.
Corrects the "40.7% invisible" claim: it is **inconsistently visible**. (BUG-287.)

**c) The retrieval corpus is 11.1% of the knowledge.** The 512d vector leg embeds **`definition` only** =
1,765,980 chars of a 15,918,888-char FB body; **88.9%** (`mechanism`, `boundary`, `application`, `failure_mode`,
`consequence`, `elaboration`) is **neither embedded nor FTS-indexed**; and **4,802,857 chars of verbatim
`evidence_passages` are indexed by nothing at all**. `source_text` is **misnamed** — 100% of rows contain
`"[book.md] " + definition`, median **300 chars**. (BUG-288.)

**d) 29.1% of "convergence" is the same book ingested twice.** `source_diversity` counts **filenames**, not works:
of 2,597 rows with diversity ≥2, **757 (29.1%)** collapse to fewer works; **1,300 filenames** hide **369
work-identities with >1 filename**. `source_diversity` is the **merge criterion at stage 1.5** and `is_convergent`
is the headline quality claim — both inflated. (BUG-289.)

**e) Two illegal values sit inside the facets.** `emerging` is used as a **domain** on 744 rows but is **not one of
the 43 canonical domains**; `discipline='emerging'` occurs on **447 `status='PASS'` rows**, i.e. the fallback value
is a member of the *exact-match* facet (and the human reviewer also typed `emerging` 9 times). (BUG-290.)

**f) A label-prefixed embedding table is one argument from production.** `contextual_embed.enabled: False` so
production is clean — **but `vec_fbs_ctx` (7,995 label-prefixed embeddings) exists in the live DB and
`retrieval_benchmark.py:159` fuses it.** Flipping it while labels are ~0.5 accurate creates a self-reinforcing
loop. (BUG-291.)

**g) `fbs_fts` has an INSERT trigger only** (`fbs_ai`), while the code does `UPDATE fbs`; a stale index would be
silent. **Hypothesis tested: `integrity-check` PASSED on a copy** (stage 6 rebuilds) — **latent, not live**. Kept
for the missing invariant. (BUG-292.)

**h) Mega-merges exist:** 883 rows >10 sources, 558 >20, 65 >50, **max 244 sources for one FB**. **Measured label
impact: none detectable** (only 8 sheet rows at 21+). **Refuted hypothesis, recorded so it is not re-run:**
over-merged FBs are *not* more unlabelable — discipline-blank rate is **24.1% for singletons** vs 0% for 3–20
sources, and `is_convergent` rows are 7% blank vs 24%. **Singletons are ~3× more likely to be unlabelable**, which
matches the untraceable pocket being *exactly* the singleton population. (BUG-293.)

**i) CORRECTION to §2.1 — the ruler's sampling frame.** The sheet sampled the **full KB** (47.3% PASS in sheet vs
59.3% in KB), mixing retrievable and hidden rows. Restricted to `status='PASS'`: **ROLE = 0.891 with baseline
0.891 → lift exactly 0.000** (cleaner and stronger than 0.740 / −0.010); discipline 0.492 (unchanged); FORM 0.852.
**Two estimands were conflated** and both must be reported. (BUG-294.)

### 2.9 RRF and chunking — the direct evidence

**RRF is already implemented and correct:** `Score(d) = Σ 1/(k + rank)`, `RRF_K = 60`, 1-based ranks, three legs,
rank-based (not score-based), with the D2511 keyword-pollution fix. **There is nothing to adopt; there is something
to feed.**

**Chunk-level retrieval is feasible at a measured, low cost.** The DB's `source_segments` (214,220 references) are
**verbatim stage-1 checkpoint `segment_id`s — sampled 205,813 / 205,813 = 100% join** against
`knowledge pipeline/stage1_chunk/t11/checkpoint.jsonl` (741.7 MB, 299,861 segments, keys `segment_id, text,
source_book, source_path, section_title, section_heading, word_count`). So a chunk leg needs **~214k vectors
(≈438 MB at 512d)**, one local embed job, **no mapping, no re-chunking, no re-extraction**, and each hit returns
**verbatim source + section heading + parent-FB link**. Granularity reference: Chen et al., *"Dense X Retrieval:
What Retrieval Granularity Should We Use?"*, EMNLP 2024, `10.18653/v1/2024.emnlp-main.845`. Chunk config is
`chunk_size_words: 300`, `chunk_overlap_words: 50`, so **adjacent hits must be collapsed at fusion**.

---

## PART 3 — THE PROPOSALS YOU MUST CROSS-EXAMINE

The commissioning architect's position is:

> **The ontology is structurally sound; the schema logic and object/property model hold; what failed is the LABELING INSTRUMENT and the INSTRUMENTATION. It requires instrument repair, not re-engineering.**

### 3.1 The diagnostic claims to attack

- **D1** — The production classifier is instructed to free-generate labels (`stage4_merge.py:341/:472`), so the drift is a prompt defect, not a taxonomy defect.
- **D2** — The measured ceiling of the current design is **≈0.61** (the `exact`-match agreement), i.e. *at* the 0.60 floor ⇒ fixing the alias table alone cannot lift discipline above its floor.
- **D3** — **F-14 was misdiagnosed.** FORM does *not* degrade in the untraceable pocket (0.860 untraceable vs 0.804 traceable within stratum A); **ROLE** does (0.667 vs 0.816). Therefore the F-14 repair should be re-targeted from "re-derive FORM for 3,348 rows" to "re-decide ROLE on the pocket".
- **D4** — `QUARANTINE` conflates *unverifiable* with *untrue*, hiding 1,780 principles; the S5 verdict (`NEUTRAL` vs `CONTRA`) is not persisted, so the distinction the fail-closed rule depends on is unrecoverable.
- **D5** — `noise_drop` cannot be repaired without a separate **relevance** axis, because relevance is relational (Saracevic 2007), not intrinsic.
- **D6** — **ROLE is decorative in production** (`PASS ⟺ principle`; −0.010 lift over a constant) and should be either repaired or reduced.
- **D7** — Labels should **not** be derived from clusters: the cluster is not a persistent object post-D2120/D2198, a convergent cluster is deliberately cross-discipline, and the label must remain a function of the content-addressed FB for reproducibility.
- **D8** — The 14.8:1 domain alias density is a *compensating control* for a prompt defect; its size, not its contents, is the finding.
- **D9** — Green instrumentation is *why* failures stay invisible: 24/45 columns dead, no usage telemetry, `classification_status` always `CLEAN`.
- **D10** — Verdict: **no serious restructuring needed**; 5 bounded repairs (below) suffice.
- **D11 (NEW)** — The facet filters are **advisory, not constraining** (BUG-285). This is a **correctness** defect that no label repair touches and that precedes every labelling question.
- **D12 (NEW)** — The write guard **destroys** the label D-271a ruled legal, so **R1 as specified cannot ship** without a config-driven exemption (BUG-286).
- **D13 (NEW)** — `graph_expand` has no status predicate, so the "hidden" 40.7% is **inconsistently visible** rather than hidden (BUG-287).
- **D14 (NEW)** — The retrieval corpus is **11.1%** of each FB; 88.9% of the body and **4.8M chars of verbatim evidence** are unsearchable; `source_text` is misnamed (BUG-288).
- **D15 (NEW)** — **29.1% of "convergence" is duplicate ingestion** (filenames ≠ works), and `source_diversity` is the merge criterion at stage 1.5 (BUG-289).
- **D16 (NEW)** — `emerging` is an **illegal facet value** on 744 domain rows and 447 PASS discipline rows (BUG-290).
- **D17 (NEW)** — The ruler's sampling frame is **not crossed with `status`**; on the retrievable slice ROLE's lift is **exactly 0.000** (BUG-294).
- **D18 (NEW)** — **Chunk-level retrieval is worth adopting, but at step 8, not step 1**: RRF is already correct; the cost is measured (~214k vectors, 100% joinable); and adding a leg **before** D11 is fixed would **amplify** the filter leak.

### 3.2 The proposed repairs (`R1`–`R5`), ordered

- **R1 · Closed-menu, definition-anchored classification.** Present the closed label list **with each label's definition**; require the model to return one of N or an explicit `none`; log the raw answer alongside. Kills the synonym layer at the source. (~1 day + one re-label run.)
- **R2 · Definition-anchored verification** using the **already-loaded DeBERTa NLI** (entailment between FB text and candidate label definitions). (~2 days, $0 marginal.)
- **R3 · Split `QUARANTINE` → `UNVERIFIED` / `CONTRADICTED`**, persist the stage-5 verdict, stop hiding verified-but-unverified rows. (~half day; recovers ~1,780 principles.)
- **R4 · Give relevance its own axis** (user-relative, revisable, scored), separate from `noise_drop` (ontological). (~1 day.)
- **R5 · Repair ~10–12 under-defined vocabulary slots** (mandatory definition + include + exclude; demote `cultural design`, `design thinking`, `strategic thinking`, `behavioral economics`, `design psychology`, `emerging`, or make them disjoint with scope notes).

### 3.3 The market-research findings to attack

Each was title-verified against OpenAlex (DOI + citation count on record). **Check them.** If a citation is misapplied, say so.

| ID | candidate | verified reference | proposed verdict |
|---|---|---|---|
| R1 | Entailment/definition-anchored classification | Yin, Hay & Roth, EMNLP 2019, `10.18653/v1/d19-1404` | ADOPT (highest leverage) |
| R3 | BCTTv1 — consensus vocabulary + published per-label reliability + coding manual | Michie et al., Ann Behav Med 2013, `10.1007/s12160-013-9486-6` | ADOPT as template |
| R4 | Per-slot inter-annotator agreement as a **vocabulary** gate (κ ≈ 0.61 = "substantial") | Cohen 1960 `10.1177/001316446002000104`; Landis & Koch 1977 `10.2307/2529310` | ADOPT |
| R5 | `cleanlab` / Confident Learning — rank likely-mislabeled rows over the existing 7,995, no LLM | Northcutt et al., JAIR 2021, `10.1613/jair.1.12125` | ADOPT |
| R6 | OntoClean (rigidity/identity/unity/dependence) slot audit | Guarino & Welty, CACM 2002, `10.1145/503124.503150` | ADAPT as checklist |
| R8 | SHACL contract enforcement (repo already has `taxonomy_shacl.ttl`) | W3C SHACL | ADOPT |
| R10 | Selective classification / conformal abstention (typed abstention reasons) | Geifman & El-Yaniv arXiv `1705.08500`; Angelopoulos & Bates arXiv `2107.07511` | ADOPT as pattern |
| R11 | NLI consistency **with TRUE's caveats** (weak human correlation) | Honovich et al., NAACL 2022, `10.18653/v1/2022.naacl-main.287` | ADAPT |
| R13 | Truth discovery from existing source columns → populate `contradicts_fbs` | Li et al., SIGKDD Expl. 2016, `10.1145/2897350.2897352` | ADAPT |
| R14 | KG refinement taxonomy for the repair | Paulheim, Semantic Web 2017, `10.3233/sw-160218` | ADAPT |
| R15 | Quality as explicit human-rated criteria + trained judge (the relevance axis) | Wettig et al., QuRating, arXiv `2402.09739` | ADOPT as template |
| R16 | Quality **classifier** beats heuristic filtering | Penedo et al., FineWeb, arXiv `2406.17557` | ADOPT as pattern |
| R17 | Relevance is relational, not intrinsic | Saracevic, JASIST 2007, `10.1002/asi.20682` | REFERENCE (mandatory) |
| R19 | Constrained clustering (must-link/cannot-link) — the *only* ontology-aware clustering | Wagstaff et al., ICML 2001 (2,412 cites) | DEFER |
| R21 | Benchmark retrieval (noise robustness is the dominant RAG failure mode); use the existing graph | Chen et al. RGB, AAAI 2024, `10.1609/aaai.v38i16.29728`; Gao et al. arXiv `2312.10997` | ADOPT |
| R22 | Faceted classification — facets must be **orthogonal** | Prieto-Díaz & Freeman, CACM 1991, `10.1145/103167.103176` | REFERENCE |
| — | Cluster-derived labelling | — | **REJECT** |
| — | Larger alias/synonym table | — | **REJECT** |

---

## PART 4 — WHAT YOU MUST PRODUCE

Answer **all** sections. Be specific and numeric. Where you disagree, give the mechanism of failure, not an adjective.

### Q1 — Verdict on reliability
Is the knowledge runtime **reliable to build on as-is**, **reliable after bounded repairs**, or does it require **serious restructuring/re-engineering**? State your verdict in one line, then defend it. If you would restructure, name **exactly which component** and what breaks that adaptation cannot fix.

### Q2 — Attack the diagnosis (D1–D10)
Go through each. For each: **CONFIRMED / PARTIALLY CONFIRMED / REFUTED**, with the reason. Pay special attention to **D3** (the F-14 re-targeting) and **D7** (reject cluster-derived labelling) — those two are the most consequential and the most falsifiable.

### Q3 — Attack the repairs (R1–R5)
For each repair: does it actually fix the stated defect? What does it **break**? What is the **second-order effect**? Order them by leverage and justify a different order if you have one.
Specific things we want you to test:
- Does **R1** (closed menu) risk **introducing** a new bias — e.g. the model now forced into `nearest available` slot rather than admitting `none`? How would you detect that?
- Does **R2** (NLI against label definitions) actually work when the *definitions themselves* are the failed artifact (R5 not yet done)? What is the correct **sequencing** of R1/R2/R5?
- Is **R3** (splitting QUARANTINE) safe, or does it risk re-emitting unverified content into retrieval? What **evidence tier** should a recovered row carry (R14)?
- Is **R4** (relevance axis) really user-relative, or can it be partly intrinsic? How would you keep it **revisable** without breaking content-addressed identity (`fb_id = sha256(name|definition)`)?
- Is **R5** the right list? Name the slots **you** would demote, using OntoClean or another stated criterion.

### Q4 — Independent market research (required)
Beyond the 24 candidates above, find solutions the commissioning architect **missed**. Required coverage — if a category has nothing better than what is listed, say so explicitly:
1. ontologically accurate clustering / constrained or knowledge-injected clustering
2. drift-free or drift-controlled labelling (definition-anchored, constrained decoding, taxonomy-constrained generation)
3. extraction/merging that preserves ontological commitments
4. contradiction detection & resolution across sources
5. **objective** relevance / utility / "what is worth keeping" filtering
6. vocabulary/ontology quality assurance and evaluation
7. retrieval quality measurement for a personal KB
For each find: name, reference (DOI/arXiv/repo), what it does, and **V/A/R/I** (viability, adaptability, referenceability, integratability on local-only $0 hardware) with a verdict (ADOPT/ADAPT/REFERENCE/DEFER/REJECT). **No fabricated citations** — mark anything you cannot verify `[UNVERIFIED]`.

### Q5 — The measurement critique
Where is the ruler **methodologically weak**? Address at minimum: the 17% discipline abstention rate; excluding `emerging` agreements; a single reviewer (no second coder ⇒ no inter-rater reliability); the forced-minority stratum's non-proportionality; the 0.60 floor's provenance; whether "stored-label accuracy" is even the right estimand versus per-slot κ; and the stop rule. **Propose the concrete next measurement** that would change a decision.

### Q6 — The consolidated final spec
Produce the spec you would sign off on, in this order:
1. **What must be fixed before any further pipeline runs** (and why each is a blocker)
2. **What the corrected label path looks like** — the exact sequence, inputs, model, output, and the gate at each step
3. **What is added to the schema** (new fields/enums) and what is **retired**
4. **How it is verified** — the tests, the floors, the acceptance criteria (remember: generator ≠ verifier, R5/C8)
5. **What is explicitly deferred and why** (including anything you conclude is a dead end)
6. **The 3 highest-value next actions**, with the human decision each requires

### Q7 — Cost, risk, and the circling question
- Estimate the work for your recommended program (in engineer-days).
- Name the **risks** that could make it fail.
- Answer directly: **is the "we go in circles" pattern a symptom of one root cause or many?** If one, name it.

### Q8 — Retrieval architecture (NEW; the second pass)
This is where the first pass was blind, and it changes the order of everything.
1. **The filters do not filter (D11).** Where should the predicate be enforced — pushed into each leg, applied to the fused pool before truncation, or both? What does ACORN (`10.1145/3654923`) imply for a **sqlite-vec** index that cannot take a predicate? What is the cheapest correct fix that does not break the cross-encoder rerank (`BAAI/bge-reranker-v2-m3`, which can promote a filter-violating row into the top-k)?
2. **Graph expansion leaks (D13).** Should a neighbour inherit the seed's status/verification tier, or be returned with its own tier and let the caller decide? What breaks either way?
3. **Coverage (D14).** Only `definition` is embedded (11.1%) and FTS covers `name/definition/keywords/jargon`. Rank these three fixes: embed the full body, FTS the body fields, index `evidence_passages` as a fourth RRF leg. Which is first and why? Is there a case for **weighted RRF** or per-leg normalisation instead of equal leg weight?
4. **Chunking (D18 / §2.9).** RRF is already correct; is a chunk/evidence leg worth it *given* that the FB is a synthesis? Should the leg return the parent FB (parent-document retrieval) or the segment? How do you handle the 50-word overlap, the 369 duplicate works, and the 952-segment mega-rows? Is `Dense X Retrieval` (`10.18653/v1/2024.emnlp-main.845`) directly applicable, or does a *synthesis* unit change the conclusion?
5. **`discipline = 'emerging'` (D16).** The fallback value is a member of the exact-match facet. How should a fail-closed fallback be represented so it can never be a filter value?

### Q9 — The correctness question, stated plainly
Given D11 (filters do not constrain), D13 (expansion leaks), and D14 (11.1% coverage): **have any retrieval-quality conclusions in this project ever been measured through a path that honours its own constraints?** If not, what does that imply for every prior retrieval benchmark, facet count, and "the KB is clean" claim — and what is the first number you would re-measure?

---

## PART 5 — OUTPUT FORMAT

```
## VERDICT (one line)

## Q1 Reliability verdict
## Q2 Diagnosis review            -> table: claim | verdict | reason  (D1-D18)
## Q3 Repair review               -> per repair: fixes / breaks / second-order / order
## Q4 Independent market research -> table: name | reference | V/A/R/I | verdict | what it adds
## Q5 Measurement critique        -> weaknesses + the next measurement
## Q6 Consolidated final spec     -> the 6 ordered parts
## Q7 Cost, risk, circling        -> days | risks | one-line root cause
## Q8 Retrieval architecture      -> filters | expansion | coverage | chunking | fallback values
## Q9 The correctness question    -> was any prior retrieval number measured on a constrained path?

## WHAT I WOULD CHANGE IN THE CLIENT'S PLAN
   (the 3–5 changes that matter most, each with the evidence that forces it)
## WHAT I COULD NOT VERIFY
   (explicit list; no silent guessing)
```

**Rules for your output:** no summaries of the evidence you were given (it is already known); no hedging adjectives without a mechanism; every factual claim traceable to the artifacts or to a cited source; disagreements stated first, agreements second.

---

## PART 6 — ANTI-PATTERNS (the failure modes this roundtable exists to prevent)

Do **not** produce any of the following. Each has already happened in this project's history:

1. **Affirming the plan and adding nothing** — a wasted turn.
2. **Quoting a number without its baseline or interval** — e.g. "84% accuracy" with no constant-answer baseline (BUG-269) and no Wilson interval (BUG-267).
3. **Proposing a fix whose cost exceeds its leverage** — e.g. re-deriving 3,348 rows of FORM when the measurement shows FORM is the *most* reliable axis (F-14 misdiagnosis, D3).
4. **Proposing a solution that needs a hosted API or a paid service** — violates C1/C3.
5. **Proposing a new runtime dependency without a protocol boundary** — violates C21.
6. **Adding a synonym/alias/exception rule to compensate for a prompt defect** — the mechanism that produced a 999-rule alias map.
7. **Hardcoding any threshold, path, or label** — violates C12.
8. **Deleting or rewriting pipeline output** — violates R-D410.
9. **Claiming a component works because a column is green** — 24 of 45 columns are green and empty (D9).
10. **Re-litigating a decision that is already measured and ruled** — e.g. D-271a is a **declared homonym** (change nothing; disciplines and domains are genuinely separate keys in `taxonomy_v5.yaml`, 0 undeclared collisions over 7,995 rows). Do not propose merging or renaming them.
11. **Proposing to add an RRF leg or a new index before the facet filters constrain** — order-dependent; it amplifies BUG-285.
12. **Treating a green column, a passing test, or a matching row count as evidence of correctness** — `integrity-check` passed on the FTS index (BUG-292) while the FTS index has no update/delete trigger, and 24 of 45 columns are green and empty. State the *invariant*, not the *status*.
13. **Quoting a retrieval number without stating the frame** — the ruler mixes `PASS` and `QUARANTINE` rows, and on the `PASS`-only frame ROLE's lift is exactly 0.000 while on all-rows it is −0.010 (BUG-294). Name the frame or the number is meaningless.
14. **Asserting that a filter filters** — measured otherwise (BUG-285). If you propose a facet-based design, say *where* the predicate is enforced.

---

## ANNEX A — Pipeline and governance references for deeper reading

| Artifact | What it holds |
|---|---|
| **`governance/REFERENCE_LIBRARY_20260919.md`** | **THE BIBLIOGRAPHY — start here.** ~45 works with their role and the finding each one supports. Metadata (title/year/venue/citation count) was **fetched from OpenAlex by DOI**, not typed, so it is checkable; 37 DOI-verified, 8 standards, **0 unresolved**. Machine-readable: `governance/references_20260919.bib` (BibTeX) and `governance/references_20260919.json`. Source of truth: `config/references.yaml`; rebuild with `python3 scripts/build_reference_library.py`. |
| `governance/ONTOLOGY_FORENSIC_20260919.md` | the full measured diagnosis (F-A…F-L) |
| `governance/MARKET_RESEARCH_ONTOLOGY_20260919.md` | the 24 verified candidates, V/A/R/I scored |
| `governance/ruler_measurement_20260917.md` | generated measurement: floors, Wilson intervals, baselines, per-class precision |
| `governance/RULER_MENUS_20260917.md` | the coding manual: every label with definition, ASK/NOT-THIS/TRAP, near-neighbour excludes |
| `governance/RULER_BLIND_SHEET_20260917.csv` | the 150 blind human labels (the certified core) |
| `governance/ruler_sheet_key_20260917.json` | the answer key (stored labels) — **must not be opened while labelling** |
| `config/taxonomy_v5.yaml` | 61 disciplines + 43 domains, with `raw` aliases and `exclude` lists |
| `config/alias_map.yaml` | 999 rescue rules (the drift ledger) |
| `config/content_types.yaml` | roles, dispositions, and the 4 FORMs with `verification_standard` |
| `config/eval_integrity.yaml` | floors (`min_human_share`), provenance tiers, ruler_sheet config, `judge_calibration` |
| `config/taxonomy_shacl.ttl` | the (unenforced) shape contract for the taxonomy |
| `pipeline/stage4_merge.py` | the free-generation classifier (lines 341, 472, 500) and the mapping layer |
| `pipeline/retrieve.py` | the retrieval facets: `discipline = ?`, `domains LIKE ?`, `depth = ?`, `status` default `PASS` |
| `pipeline/stage5_verify.py` | the fail-closed NLI gate (NEUTRAL→QUARANTINE) |
| `pipeline/reclassify_merged_axis.py` | the post-hoc repair script (~2,343 `emerging` rows, D2532) |
| `grep`-visible defect classes | `BUG-273`…`BUG-294` in `governance/buglog.md` — including BUG-285 (filters do not filter), BUG-286 (guard destroys a ruled-legal label), BUG-287 (graph-expansion leak), BUG-288 (11.1% coverage), BUG-289 (duplicate-work convergence), BUG-290 (illegal facet values), BUG-291 (`vec_fbs_ctx`), BUG-292 (FTS trigger set), BUG-293 (mega-merges), BUG-294 (ruler frame) |
| second-pass forensic | `governance/ONTOLOGY_FORENSIC_20260919.md` **§13** — the retrieval, ingestion and sampling-frame audit, plus the three corrections to the first-pass claims |
| `governance/CONTEXT_INDEX.md` | recall map: where everything lives, what is superseded, human gate register |
| `CONSTITUTION.md` | single source of truth; C1–C28, R5/R7/R14, §2 pipeline |

## ANNEX B — Human gates currently open (the client decides; you may recommend)

**New second-pass gates:**

- **G12** approve **constraining the facet filters** (push the predicate into every leg / post-filter the fused pool). No human cost, but it changes results for every existing query.
- **G13** approve the **write-guard exemption** for the declared homonym — **a hard prerequisite for R1** (BUG-286).
- **G14** approve **work-identity dedup at ingestion** (BUG-289): re-run affected merges, or only prevent future ones?
- **G15** approve **indexing what is already in the DB** (body fields into FTS, `evidence_passages` as a fourth RRF leg, full-body embeddings).
- **G16** approve the **chunk/evidence leg** (step 8) — and decide whether a hit returns the parent FB or the segment.

**Previously open:**

- **G4** ratify the certified ruler core and repoint the floors at it (recommended: repoint floors at the certified core, keep the anchor for eval).
- **G8** ratify D-271a as a **declared homonym** (change nothing).
- **D-G4a** continue the discipline ruler (~85 more stratum-A rows) because its floor is statistically **unresolved**.
- **R3** approve splitting `QUARANTINE` into `UNVERIFIED` / `CONTRADICTED` (re-exposes ~1,780 principles to retrieval).
- **R4** approve a separate relevance axis.
- **R5** ratify the list of ~10–12 vocabulary slots to rebuild or demote.
- **D-G2a** the 591 `noise_drop`/`quarantine` junk rows: exclude+flag (recommended) vs delete (R-D410 owns deletion).
- Open defects awaiting work: **BUG-273** (domains 1..3 contract violated by 1,002 rows, max 7), **BUG-274** (`related_fbs` 56.8% asymmetric, 88,592 one-way edges + 7 self-references), **BUG-275** (substring `domains LIKE` + facets were unindexed), **BUG-276** (`backup_guardian.sh` dead — **no automated DB backup exists**), **BUG-277** (`content_type` mixes two vocabularies; `pipeline/content_types.py::CONTENT_TYPES_ALL` is the authority, not the YAML `content_types` key), **BUG-278…BUG-283** (the six defects measured on 2026-09-19: quarantine conflation; free-generation labelling; ROLE decorative in production; no relevance axis; 24/45 dead columns; the ruler scorer's index-only assumption).

---

*End of master prompt. Participants: answer independently; do not read another participant's answer before writing yours.*
