# MARKET RESEARCH — ontologically accurate classification, drift elimination, contradiction handling, and objective relevance filtering
**Date:** 2026-09-19 · **Method:** OpenAlex title-verified (DOI + citation count on record) · **Constraint basis:** C1 ($0 marginal, local), C2/C4 (no lock-in), C3 (sovereign), C12 (config-first), C21 (swappable behind a protocol)
**Companion:** `governance/ONTOLOGY_FORENSIC_20260919.md` (the measured diagnosis these candidates must answer)

---

## 0. How to read this

Every candidate is scored on four axes, then given a **verdict**. No candidate is listed without a verified reference (DOI/arXiv or W3C/ISO standard).

| axis | question |
|---|---|
| **Viability** (V) | is it proven to work, with evidence, at this scale? |
| **Adaptability** (A) | can it be shaped to Maxwell OS's object model (FB + 5 axes + provenance) without distortion? |
| **Referenceability** (R) | can it be cited as a standard / defended to an auditor? |
| **Integratability** (I) | does it fit the existing 8-stage pipeline, local models, config-first and $0 marginal? |

Scale 1–5. **Verdict:** ADOPT (do it now) · ADAPT (do it with modification) · REFERENCE (design guidance, no code) · DEFER (correct but not yet) · REJECT (documented as wrong for this system).

---

## 1. The six problems, stated precisely

| # | problem as measured | forensic anchor |
|---|---|---|
| **P1** | Labels are free-generated, then rescued by a 999-rule synonym table; only 26.6% land cleanly | F-C, §3 |
| **P2** | The rescue cost is measurable: exact 0.61 → synonym 0.49 → `emerging` 0.33 human agreement | §3.1 |
| **P3** | ~10–12 vocabulary slots are too vague to apply reliably (abstract/coined 0.00–0.44 vs concrete 0.83–1.00) | F-F, §5 |
| **P4** | "Unverifiable" is treated as "untrue"; 40.7% of the KB hidden, incl. 1,780 principles; contradiction is never recorded | F-B, §6.1 |
| **P5** | No relevance axis: `noise_drop` fuses "not extractable" with "true but irrelevant" | F-E, §6.2 |
| **P6** | 24/45 attribute columns dead; no telemetry, so failures are invisible until sampled | F-H, §8 |

---

## 2. Candidates

### 2.1 P1/P2 — make the label a *decision*, not a *generation*

#### R1 · Entailment-based / definition-anchored classification — **VERDICT: ADOPT (highest leverage in this report)**
- **What it is:** instead of asking "what discipline is this?", present the closed label list **with each label's written definition** and decide the label by entailment between the FB text and each candidate definition. Yin, Hay & Roth formalised exactly this for zero-shot classification — *"Benchmarking Zero-shot Text Classification: Datasets, Evaluation and Entailment Approach"*, EMNLP 2019, **DOI 10.18653/v1/d19-1404** (529 citations).
- **What it kills:** the entire synonym/alias rescue layer. If the model must return one of 61 defined names (or an explicit `none`), `synonym` (49.9%) collapses toward `exact`, and the raw-label space collapses from 1,089 strings to ≤61 + `none`.
- **V (5):** standard, replicated method. **A (5):** pure prompt + local NLI change. **R (5):** citable. **I (5):** DeBERTa-v3-large is **already loaded in stage 5** — $0 marginal, no new model.
- **Cost:** ~1 day of prompt/plumbing + one corpus re-label run. **This is the change that dissolves F-C, F-I and most of F-F.**

#### R2 · Closed-vocabulary discipline is the *documented* design, not a new idea — **VERDICT: REFERENCE**
- Controlled-vocabulary-vs-free-text is a settled question with a 50-year literature: Lancaster, *Vocabulary Control for Information Retrieval* (1972, 236 citations); *"Natural language versus controlled vocabulary in information retrieval"*, JASIS 1998, **DOI 10.1002/(sici)1097-4571(199808)49:10<881::aid-asi4>3.0.co;2-y**. The finding is context-dependent: control wins for **recall/precision on curated corpora**; free text wins for large heterogeneous web text. Maxwell OS is the **curated** case.
- The production prompt does the exact opposite of the standard: `stage4_merge.py:341` — *"not what label fits best from a predefined list"*.

#### R3 · The authoritative analogue: **BCTTv1** — **VERDICT: ADOPT AS THE TEMPLATE**
- Michie et al., *"The Behavior Change Technique Taxonomy (v1) of 93 hierarchically clustered techniques: building an international consensus for the reporting of behavior change interventions"*, Annals of Behavioral Medicine 2013, **DOI 10.1007/s12160-013-9486-6** (8,202 citations).
- **Why this is the right model for Maxwell OS:** it is a **93-label, hierarchically clustered controlled vocabulary built by international consensus**, published with **per-label reliability**, a **coding manual**, and **mandatory training**. Three transferable lessons:
  1. a taxonomy that will be applied by *any* agent (human or model) needs **consensus-built labels with definitions and exclusion rules** — not labels invented at classification time;
  2. **per-label reliability is published** — which is exactly what the G4 ruler is producing for Maxwell OS, and exactly why the `typography` 1.00 / `cultural design` 0.00 split is the correct output to act on;
  3. **the taxonomy alone is not enough** — BCTTv1 ships a manual. `RULER_MENUS_20260917.md` is Maxwell OS's coding manual. It should be a **product**, not a one-off artifact for a ruler.

#### R4 · Inter-annotator agreement as a *vocabulary* acceptance gate — **VERDICT: ADOPT**
- Cohen, *"A Coefficient of Agreement for Nominal Scales"*, 1960, **DOI 10.1177/001316446002000104** (42,317 citations); Landis & Koch, *"The Measurement of Observer Agreement for Categorical Data"*, Biometrics 1977, **DOI 10.2307/2529310** (81,232 citations); Krippendorff, *Content Analysis*, **DOI 10.4135/9781071878781**.
- **What it changes:** the ruler measures *stored-label accuracy*; it should **also** measure *per-slot agreement*, and **any slot below κ ≈ 0.61 (Landis–Koch "substantial") is a vocabulary defect, not a data defect** and must be rewritten or demoted. This converts F-F from an opinion into a gate.

#### R5 · Label-error detection *without* re-running the pipeline — **VERDICT: ADOPT (cheap, immediate)**
- Northcutt et al., *"Confident Learning: Estimating Uncertainty in Dataset Labels"*, JAIR 2021, **DOI 10.1613/jair.1.12125** — reference implementation **`cleanlab`**.
- **What it does for Maxwell OS:** given the existing features/embeddings and the stored labels, it ranks rows **most likely to be mislabeled** *now*, at zero LLM cost. That is a **direct, cheap replacement for the sample-only ruler** when hunting misclassification across all 7,995 rows, and it is 100% local.
- **V (4) A (4) R (4) I (5).** Runs on the existing bge-m3 vectors.

---

### 2.2 P3 — repair the vocabulary itself

#### R6 · **OntoClean** — ontological hygiene per slot — **VERDICT: ADAPT (as a checklist, not a tool)**
- Guarino & Welty, *"Evaluating ontological decisions with OntoClean"*, Communications of the ACM 2002, **DOI 10.1145/503124.503150** (767 citations).
- OntoClean's four meta-properties — **rigidity, identity, unity, dependence** — are precisely the test for why `cultural design` fails and `typography` succeeds: `typography` is rigid (an object either is or is not typography), carries identity, and is independent; `cultural design` is anti-rigid, identity-less and dependent on the analyst's framing. **Apply the four questions to all 104 slots in a spreadsheet; demote what fails.**
- **A (5):** it is a review method, not software. **I (5).**

#### R7 · **OQuaRE / SQuaRE-style ontology metrics** — **VERDICT: REFERENCE**
- Duque-Ramos et al., *"OQuaRE: A SQuaRE-based Approach for Evaluating the Quality of Ontologies"* (2011, 104 citations). Gives **structural/semantic/functional metrics** (cohesion, completeness, consistency). Useful as the *scorecard language* for the vocabulary, overkill to implement.

#### R8 · **SHACL shapes validation** — **VERDICT: ADOPT (already 60% built)**
- W3C SHACL. **`config/taxonomy_shacl.ttl` already exists in this repo** — the vocabulary has a machine-checkable contract that is apparently not enforced on the taxonomy itself. Enforce: every slot has definition + include/exclude; mutually exclusive siblings; no alias key that is another axis's canonical (the 53 dual-axis + 1 `urban planning` case); domains 1..3 (BUG-273's 1,002 violations). **This is config-first (C12) quality gating at zero runtime cost.**

#### R9 · Taxonomy *induction* — for when the vocabulary is grown, not applied — **VERDICT: DEFER**
- Wong, Liu & Bennamoun, *"Ontology learning from text: A look back and into the future"*, ACM Computing Surveys 2012, **DOI 10.1145/2333112.2333115**; Shen et al., *"TaxoExpan: Self-supervised Taxonomy Expansion"*, WWW 2020, **DOI 10.1145/3366423.3380132**.
- Correct answer to *"is 61×43 the highest representative set for 1,000 books?"* — but **do not start here**. The measured problem is *application* (0.506), not *coverage*. Expanding a vocabulary that cannot be applied reliably expands the failure. Revisit after R1/R4.

---

### 2.3 P4 — verification, abstention, and not conflating "unverifiable" with "untrue"

#### R10 · **Selective classification / calibrated abstention** — **VERDICT: ADOPT (design pattern)**
- Geifman & El-Yaniv, *"Selective Classification for Deep Neural Networks"*, 2017, arXiv **1705.08500**; Angelopoulos & Bates, *"A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification"*, arXiv **2107.07511**.
- **What it licenses:** Maxwell OS may abstain — but the *reason* for abstention must be recorded as a **typed outcome** (`no-evidence`, `low-entail`, `contradicted`, `out-of-scope`) rather than collapsed into one `QUARANTINE`. Selective classification gives a principled threshold: choose the coverage/risk trade-off explicitly (e.g. "keep 85% of rows at ≤5% false-pass risk") instead of failing closed into arbitrary hiding.
- **Scores V 5 · A 5 · R 5 · I 4** (needs the verdict to be persisted — see R12).

#### R11 · NLI as a factual-consistency measure — adopt **with** its published caveats — **VERDICT: ADAPT**
- Honovich et al., *"TRUE: Re-evaluating Factual Consistency Evaluation"*, NAACL 2022, **DOI 10.18653/v1/2022.naacl-main.287**.
- **Critical for Maxwell OS:** TRUE's finding is that NLI-based factual-consistency scorers **correlate weakly with human judgement and are insensitive to important error types**. So the existing S5 (DeBERTa NLI, threshold 0.10) is a *usable filter with known blind spots*, not a truth oracle — and a `NEUTRAL` verdict must never be read as `FALSE`. This is the peer-reviewed citation that justifies R3 of the forensic repair.
- **Also adopt the eval discipline:** TRUE is a benchmark with human annotations. Maxwell OS should build the equivalent **retrieval + label benchmark** (see R15).

#### R12 · **PROV-O** — provenance as a typed graph — **VERDICT: ADAPT**
- W3C *PROV-O: The PROV Ontology* (2013, 232 citations on record). The KB's `provenance` column is a single constant (`llm_extracted_from_source` for 100% of rows, F-H). PROV-O gives the vocabulary for **entity / activity / agent** with `wasGeneratedBy`, `wasDerivedFrom`, `wasAttributedTo` — exactly the "which model, which prompt, which run, which sources, verified by whom" chain that R14 already demands and that is currently unpopulated. **Adapt the concept onto the existing flat columns; no RDF store needed.**

---

### 2.4 P4b — contradictions, and truth from conflicting sources

#### R13 · Truth discovery over conflicting sources — **VERDICT: ADAPT (the missing "contradicts" implementation)**
- Li et al., *"A Survey on Truth Discovery"*, ACM SIGKDD Explorations 2016, **DOI 10.1145/2897350.2897352** (431 citations). Core idea: **jointly estimate source reliability and claim truth** from agreement patterns — no ground truth needed.
- **Why Maxwell OS is unusually well-positioned:** it already stores `source_books`, `source_ids`, `source_diversity`, `is_convergent`, and `source_principle_ids`. The inputs truth discovery needs are **already in the DB**. `contradicts_fbs` is empty (F-H) purely because no pass computes it. Combine with…
- **R14 · KG refinement** — Paulheim, *"Knowledge graph refinement: A survey of approaches and evaluation methods"*, Semantic Web 2017, **DOI 10.3233/sw-160218** (1,224 citations): the standard taxonomy of **error detection / completion / repair** for exactly this class of graph. Use its evaluation vocabulary so the refinements (LINK-not-MERGE, the 17 `duplicate_of` rows, the 273 flagged semantic groups) are measured, not asserted.

---

### 2.5 P5 — objective relevance and noise filtering (your "what is relevant and what is not")

This is where the industry actually has hard answers — but they are answers about **utility for a purpose**, not intrinsic worth.

#### R15 · **QuRating** — quality as *explicit, human-rated criteria* — **VERDICT: ADOPT AS THE TEMPLATE for a relevance axis**
- Wettig et al., *"QuRating: Selecting High-Quality Data for Training Language Models"*, ICML 2024, arXiv **2402.09739**.
- **What it is:** four **explicit quality criteria** (writing style, facts & trivia, educational value, required expertise), **human pairwise ratings**, and a **judge trained on those ratings** that then scores the whole corpus.
- **Why this is the correct shape for Maxwell OS's relevance problem:** it converts a vague "is this good/relevant?" into **named criteria + human ratings + a reproducible local judge** — and it is the *same* pattern as the G4 ruler (blind human labels → certified core). The reviewer's repeated *"valid fact but irrelevant"* is a **criterion**, not noise: `personal utility`, `mission fit`, `actionability`. Make them explicit, rate a sample, train/verify a local judge, then filter **with the criteria visible** instead of swallowing the distinction into `noise_drop`.

#### R16 · **FineWeb / FineWeb-Edu** — a classifier on a small labelled set beats heuristics — **VERDICT: ADOPT (pattern)**
- Penedo et al., *"The FineWeb Datasets: Decanting the Web for the Finest Text Data at Scale"*, 2024, arXiv **2406.17557**.
- **The transferable result:** a **small set of human/LLM quality annotations + a trained classifier** outperforms regex/heuristic filtering for "is this educational/valuable". Maxwell OS's `stage1_3_prefilter.py` is a **regex** filter ("drop obvious structural garbage") — fine for TOC/copyright, structurally incapable of the relevance question the reviewer is asking. **Replace the relevance decision with a scored classifier; keep the regex for structure.**
- Supporting corpus-hygiene literature for the same lesson at scale: Lee et al., *"Deduplicating Training Data Makes Language Models Better"*, ACL 2022, **DOI 10.18653/v1/2022.acl-long.577**; and the open frameworks **Data-Juicer** (**DOI 10.1145/3626246.3653385**), NVIDIA `NeMo Curator`, HF `datatrove` — all local, all $0, all swappable behind a protocol (C21).

#### R17 · **Saracevic's relevance framework** — the theoretical fix for the word "relevant" — **VERDICT: REFERENCE (mandatory)**
- Saracevic, *"Relevance: A review of the literature and a framework for thinking on the notion in information science"*, JASIST 2007, **DOI 10.1002/asi.20682** (226 citations).
- **The finding Maxwell OS is violating:** relevance is **relational** — it only exists between a document, a *user*, and a *goal*; it is not an intrinsic property of text. Therefore:
  - `noise_drop` (intrinsic: "no extractable object") and *relevance* (relational: "matters to Barn, now") **are different axes and must be stored separately** — forensic F-E.
  - relevance must be **revisable** — the reviewer said of one row *"CRT is already outdated so it could also be quarantine, but since I'm interested in old tech it can be still relevant"*. An intrinsic content type can never express that; a scored, dated, user-relative field can.
- **This single reference legitimises the whole R4 (relevance axis) repair.**

#### R18 · Personal Knowledge Graphs — the closest architectural analogue — **VERDICT: REFERENCE**
- Balog & Kenter, *"Personal Knowledge Graphs: A Research Agenda"*, 2019 (9 citations — a small but exact-match literature). PKGs are explicitly **user-scoped, privacy-bound, and non-canonical**, i.e. they assume *personal* relevance and *personal* vocabulary drift as first-class concerns. Maxwell OS is a PKG; the PKG literature's agenda (user modelling, privacy, personal vocabulary) is a better frame than a generic enterprise KG frame.

---

### 2.6 P1 auxiliary — should the label come from the cluster? (your original question)

#### R19 · **Constrained clustering with background knowledge** — the *only* peer-reviewed way to make clustering ontology-aware — **VERDICT: DEFER (with a specific, narrow use)**
- Wagstaff et al., *"Constrained K-means Clustering with Background Knowledge"*, ICML 2001 (2,412 citations) — **must-link / cannot-link** constraints; Basu et al., *"Semi-Supervised Clustering by Seeding"*, ICML 2002 (805 citations).
- **This is the honest answer to "is cluster-derived labelling feasible":** you *can* inject ontology into clustering — by telling the clusterer that two disciplines may never share a cluster (cannot-link) — but that produces **discipline-pure clusters**, not a **label from the cluster**. It constrains the *input* to labelling; it does not replace labelling.
- **Verdict DEFER because** the forensic analysis (§2.1) shows the label must remain a function of the FB for reproducibility, and the measured failure is in *labeling*, not *clustering*. **Where it IS worth doing (small, later):** use cannot-link constraints to stop cross-discipline FBs being merged in stage 1.5, then verify with the retrieval benchmark. Related, also DEFER: HDBSCAN (Campello et al., **DOI 10.1007/978-3-642-37456-2_14**, 2,548 citations) for stability measurement, and **BERTopic** (Grootendorst, arXiv **2203.05794**, 1,388 citations) whose **c-TF-IDF topic representation** is the standard way to *name* a cluster — the piece stage 2 currently skips.

#### R20 · The industry-standard alternative worth knowing: **weak supervision** — **VERDICT: DEFER**
- Ratner et al., **Snorkel**, VLDB Journal 2020, **DOI 10.1007/s00778-019-00552-1** (520 citations). Labeling functions + a generative model that learns their accuracies — a principled way to combine *many cheap rules* (regex, NLI, embedding-kNN, alias map) into one label **with estimated accuracy per rule**. Would let the existing alias map become one *voted* signal among several instead of a silent overwrite. Useful after R1; not before.

---

### 2.7 P6 / P1 — retrieval, and proving the KB actually works

#### R21 · Benchmark the retrieval, don't assume it — **VERDICT: ADOPT**
- Chen et al., *"Benchmarking Large Language Models in Retrieval-Augmented Generation"* (RGB), AAAI 2024, **DOI 10.1609/aaai.v38i16.29728** (378 citations); Gao et al., *"Retrieval-Augmented Generation for Large Language Models: A Survey"*, arXiv **2312.10997** (747 citations).
- RGB's central measured finding is that **noise robustness is the dominant failure mode** of RAG systems. Maxwell OS has **no retrieval benchmark at all** — so the axis inversion (F-A), the substring `domains LIKE` filter, and the 59.3% visible slice have never been measured *end to end*. An N-question retrieval eval with known answers is the missing instrument that turns "is the runtime reliable?" into a number.
- **Also from the RAG literature, directly relevant:** graph-structured retrieval (Microsoft GraphRAG — *"From Local to Global"*, arXiv 2404.16130) beats flat chunk retrieval for multi-hop/summarisation. Maxwell OS already has the graph (164,202 edges, 0 dangling) and does not use it in retrieval. **Cheapest high-value retrieval upgrade available.**

#### R22 · Faceted classification / controlled vocabulary for navigation — **VERDICT: REFERENCE**
- Prieto-Díaz & Freeman, *"Implementing faceted classification for software reuse"*, CACM 1991, **DOI 10.1145/103167.103176** (511 citations). The canonical demonstration that **a small set of orthogonal facets, each with controlled values, scales to real navigation** — and that facets must be **orthogonal** (Maxwell OS's `depth` is not: it is undefined for all 1,470 non-principle rows, §7). MeSH / ACM CCS / IEEE Thesaurus are the living instances.

---

## 3. The composite programme (what to actually do, in order)

| order | action | candidates | dissolves | human gate |
|---|---|---|---|---|
| **1** | **Closed-menu, definition-anchored classification** — model must return one of 61/43 defined labels or `none`; log the raw answer | R1, R2, R3 | F-C, F-I, and most of F-F | 1 ruling |
| **2** | **Split `QUARANTINE` → `UNVERIFIED` / `CONTRADICTED`**, persist the S5 verdict, stop hiding verified-but-unverified rows | R10, R11 | F-B (recovers ~1,780 principles) | 1 ruling |
| **3** | **Relevance as its own axis** — named criteria + rated sample + local judge; keep `noise_drop` purely ontological | R15, R16, R17 | F-E | 1 ruling |
| **4** | **Vocabulary quality gate** — mandatory definition+include+exclude; OntoClean check on 104 slots; κ per slot; SHACL enforcement; domains 1..3 | R4, R6, R7, R8 | F-F, BUG-273 | ratify slot list |
| **5** | **Cleanlab pass over the existing 7,995 rows** — rank likely-mislabeled rows, no LLM, no re-run | R5 | F-C residue | no |
| **6** | **Truth-discovery / contradiction pass** — use existing source agreement; populate `contradicts_fbs` | R13, R14 | F-H (contradictions) | no |
| **7** | **Retrieval benchmark (RGB-style) + graph-aware retrieval** | R21, R22 | F-A (measure it) | no |
| **8** | Optional, later: constrained clustering, BERTopic-style cluster naming, weak supervision over the alias map | R19, R20 | future F-C recurrence | no |

**Steps 1–3 are the ones that stop the circling.** They are three prompts/enums plus one axis, and all three run on hardware already in the repo.

---

## 4. What NOT to adopt (and why) — documented so it is not re-litigated

| rejected | why |
|---|---|
| **Cluster-derived labels** (your original question) | the cluster is not a persistent object post-D2120/D2198; a convergent cluster is deliberately cross-discipline; and the label must be a function of the content-addressed FB. Fix the question, not the source. (§2.1) |
| **Free-form labelling with a bigger alias table** | measured ceiling 0.61 ≈ the floor; every rule added is a compensating control that hides the defect. (§3.1) |
| **Vector-only retrieval on bge-m3** | 512d Matryoshka over 7,995 rows is fine, but the graph (164,202 edges) and the facets are unused; RGB shows noise robustness, not embedding quality, is the failure mode. |
| **Re-introducing HDBSCAN as a hard partition** | D2120/D2198 removed it for reproducibility reasons that still hold. Use it only to *measure* stability (DEFER). |
| **External LLM APIs for labelling/verification** | violates C1/C3. Every adopted candidate above runs locally; R1/R2/R5/R6/R8/R13/R15 are all $0 marginal. |
| **RDF triple store / OWL reasoner as the runtime** | PROV-O/SHACL/OntoClean are adopted as **vocabularies and checks**, not as a new storage layer. The SQLite + Parquet + sqlite-vec spine is adequate and swappable (C21). |
| **Re-labelling the whole corpus before fixing the vocabulary** | would reproduce the same drift at full cost. Order matters: fix the vocabulary and the question **first** (steps 1–4). |

---

## 5. Verdict on restructuring vs adaptation

| question | answer | basis |
|---|---|---|
| Does Maxwell OS need **serious restructuring / re-engineering**? | **NO** | every adopted candidate is a prompt change, a verifier call, an enum split, a new scored axis, or a config/validation gate. The 8-stage pipeline, identity layer, schema, object/property model and provenance spine all survive intact. |
| Does it need **no change at all**? | **NO** | three axes measure at/below their floors; 40.7% of the KB is unreachable; the label path is free-generation. |
| What it needs | **instrument repair, behind protocols** (C21) | 5 bounded repairs (§3 steps 1–5), each swappable, each measurable, ~1 week of work total, all local |
| What it must NOT do | **re-derive labels from clusters, or re-label before the vocabulary is fixed** | §4 |

**The one-line answer:** *the ontology is structurally sound and the schema logic holds; the instrumentation feeding it is what failed, and every repair has a peer-reviewed precedent and a local implementation.*

---

## 6. Ranked candidate table (single view)

| rank | candidate | reference (verified) | V | A | R | I | verdict | serves |
|---|---|---|---|---|---|---|---|---|
| 1 | Definition-anchored entailment classification | Yin et al. EMNLP 2019, 10.18653/v1/d19-1404 | 5 | 5 | 5 | 5 | **ADOPT** | P1 P2 |
| 2 | Split UNVERIFIED/CONTRADICTED + selective abstention | Geifman & El-Yaniv arXiv 1705.08500; Angelopoulos & Bates arXiv 2107.07511 | 5 | 5 | 5 | 4 | **ADOPT** | P4 |
| 3 | Relevance as explicit rated criteria + local judge | Wettig et al. arXiv 2402.09739 (QuRating) | 5 | 5 | 4 | 4 | **ADOPT** | P5 |
| 4 | Per-slot inter-annotator agreement as a vocabulary gate | Cohen 1960, 10.1177/001316446002000104; Landis & Koch 1977, 10.2307/2529310 | 5 | 5 | 5 | 5 | **ADOPT** | P3 |
| 5 | cleanlab label-error ranking over existing rows | Northcutt et al. JAIR 2021, 10.1613/jair.1.12125 | 4 | 4 | 4 | 5 | **ADOPT** | P1 P6 |
| 6 | SHACL contract enforcement on the taxonomy | W3C SHACL (repo already has `taxonomy_shacl.ttl`) | 5 | 5 | 5 | 5 | **ADOPT** | P3 P6 |
| 7 | BCTTv1 as the consensus-vocabulary template | Michie et al. 2013, 10.1007/s12160-013-9486-6 | 5 | 5 | 5 | 5 | **ADOPT** | P1 P3 |
| 8 | Quality-classifier replacing heuristic relevance filtering | Penedo et al. arXiv 2406.17557 (FineWeb) | 5 | 4 | 4 | 4 | **ADOPT** | P5 |
| 9 | Truth discovery over existing source columns | Li et al. 2016, 10.1145/2897350.2897352 | 4 | 4 | 5 | 4 | **ADAPT** | P4 |
| 10 | OntoClean four-property slot audit | Guarino & Welty 2002, 10.1145/503124.503150 | 5 | 5 | 5 | 5 | **ADAPT** | P3 |
| 11 | Retrieve with the graph, not just the vectors | Gao et al. arXiv 2312.10997; RGB 10.1609/aaai.v38i16.29728 | 4 | 4 | 4 | 4 | **ADOPT** | P6 |
| 12 | PROV-O shaped provenance | W3C PROV-O 2013 | 5 | 4 | 5 | 3 | **ADAPT** | P6 |
| 13 | NLI consistency — with TRUE's caveats | Honovich et al. NAACL 2022, 10.18653/v1/2022.naacl-main.287 | 5 | 5 | 5 | 5 | **ADAPT** | P4 |
| 14 | KG refinement taxonomy for the repair itself | Paulheim 2017, 10.3233/sw-160218 | 4 | 5 | 5 | 4 | **ADAPT** | P4 P6 |
| 15 | Saracevic relevance (why relevance is relational) | Saracevic 2007, 10.1002/asi.20682 | 5 | 5 | 5 | 5 | **REFERENCE** | P5 |
| 16 | Controlled-vocabulary vs free-text literature | Lancaster 1972; JASIS 1998, 10.1002/(sici)1097-4571(199808)49:10<881::aid-asi4>3.0.co;2-y | 5 | 5 | 5 | 5 | **REFERENCE** | P1 |
| 17 | Faceted classification for navigation | Prieto-Díaz & Freeman 1991, 10.1145/103167.103176 | 5 | 5 | 5 | 4 | **REFERENCE** | P6 |
| 18 | OQuaRE ontology quality metrics | Duque-Ramos et al. 2011 | 4 | 4 | 4 | 3 | **REFERENCE** | P3 |
| 19 | Personal Knowledge Graph agenda | Balog & Kenter 2019 | 3 | 5 | 3 | 4 | **REFERENCE** | P5 |
| 20 | Taxonomy induction / expansion | Wong et al. 2012, 10.1145/2333112.2333115; TaxoExpan 10.1145/3366423.3380132 | 4 | 3 | 4 | 3 | **DEFER** | P3 |
| 21 | Constrained clustering (must/cannot-link) + cluster naming | Wagstaff et al. ICML 2001; BERTopic arXiv 2203.05794; HDBSCAN 10.1007/978-3-642-37456-2_14 | 4 | 3 | 5 | 3 | **DEFER** | P1 |
| 22 | Weak supervision over the alias map | Ratner et al. VLDB J 2020, 10.1007/s00778-019-00552-1 | 4 | 3 | 4 | 3 | **DEFER** | P1 |
| 23 | Corpus dedup + data-processing frameworks | Lee et al. ACL 2022, 10.18653/v1/2022.acl-long.577; Data-Juicer 10.1145/3626246.3653385 | 5 | 4 | 4 | 3 | **DEFER** | P5 |
| 24 | Record linkage for identity | Fellegi & Sunter 1969, 10.1080/01621459.1969.10501049 | 5 | 4 | 5 | 4 | **already adopted in spirit** | P6 |
| — | Cluster-derived labelling | — | — | — | — | — | **REJECT** | §4 |
| — | Bigger alias/synonym table | — | — | — | — | — | **REJECT** | §4 |
