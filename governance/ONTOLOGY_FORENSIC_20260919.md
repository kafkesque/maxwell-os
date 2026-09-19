# ONTOLOGY FORENSIC — the blind ruler, the post-hoc label path, and the vocabulary itself
**Date:** 2026-09-19 · **KB:** `knowledge pipeline/maxwell.db` (7,995 rows, 164,202 identity edges) · **Scope:** read-only measurement + written findings
**Evidence:** `governance/ruler_measurement_20260917.md` (generated) · `governance/RULER_BLIND_SHEET_20260917.csv` (150 rows, reviewer `human`, 17.09.26) · `config/taxonomy_v5.yaml` · `config/alias_map.yaml` · `pipeline/stage4_merge.py`

---

## 0. The one-paragraph verdict

The ruler was answered blind, by a human, against the same menus the pipeline is supposed to use. Three of the four label axes measured **below or at their own floor**, and the two axes the KB actually uses for retrieval are **the two least reliable ones**. The cause is not bad luck and not the human: the production classifier is instructed, in writing, to **invent a free-text label** rather than choose from the closed vocabulary (`stage4_merge.py:341`, `:472` — *"no canonical lists"*), and a post-hoc synonym table then squeezes 1,089 raw discipline strings and 4,982 raw domain strings into 61 + 43 slots. Every rescue the table performs costs accuracy (exact 0.61 → synonym 0.49 → dumped-as-emerging 0.33 human agreement). Meanwhile 40.7% of the KB is hidden from retrieval by a fail-closed rule that **treats "unverifiable" as "untrue"**, and 24 of 45 attribute columns are dead or near-dead constants. The ontology is not the problem; **the labeling instrument is**, and it is a bounded, fixable instrument.

---

## 1. Are the human's classifications ontologically valid?

**Yes — and that is exactly why they are admissible as a reference.** Four independent validity checks were applied before any of the numbers below were trusted.

| validity check | result | why it matters |
|---|---|---|
| **Blindness** | sheet carried **zero stored-label columns**; the answer key is a separate file | the human could not copy the KB |
| **Reviewer-effort signature** | took the task as real: 31 typo'd but intended answers, 51 free-text objections, 2 vocabulary gaps (`leadership`) | not a rubber-stamp |
| **Calibration** | confidence predicts correctness monotonically. FORM: conf 1.0 → 90%, 0.8 → 76%, 0.6 → 0%. DISC: 1.0 → 68%, 0.8 → 30% | the reviewer knew when they knew |
| **Refusal to answer** | 29 discipline cells and 22 FORM cells left **blank**; 21 of those 29 are in the F-14 pocket | blank is a datum, not a gap — and it is reported, never imputed |

The blanks are the strongest validity signal available: a reviewer who wanted to look decisive would have filled 150/150. Instead they abstained where the object genuinely has no home, and 72% of those abstentions land in the untraceable pocket.

### 1.1 The measured RULER result (stratum A, n = 100 — the only floor denominator)

| axis | n scored | unanswered | stored-label accuracy | 95% Wilson | constant-answer baseline | lift | floor | verdict |
|---|---|---|---|---|---|---|---|---|
| content_type (ROLE) | 100 | 0 | **0.740** | [0.646, 0.816] | **0.750** ("principle") | **−0.010** | 0.60 | STOPPED — decisive |
| discipline | 83 | 17 | **0.506** | [0.401, 0.611] | 0.084 ("operations research") | +0.422 | 0.60 | CONTINUE — inside the margin (0.094 < 0.10) |
| extraction_type (FORM) | 89 | 11 | **0.831** | [0.740, 0.895] | 0.360 ("descriptive_model") | +0.472 | 0.60 | STOPPED — decisive |

Read that table in the order it is printed:

1. **ROLE is not a classifier.** 0.740 against a 0.750 constant-answer baseline is a **negative lift**. Delete the axis and answer "principle" every time and you are *marginally more accurate*. The floor of 0.60 is passed only because the class prior is 82% `principle`; the axis fails the BUG-269 margin rule outright.
2. **DISCIPLINE is informative but not yet proven above its floor.** +0.422 lift over a 0.084 baseline is a real signal — but 0.506 with an upper bound of 0.611 means the floor of 0.60 is *inside* the interval. The honest status is **UNRESOLVED, not failed**: ~85 more stratum-A rows would settle it. Also: the reviewer, holding the full 61-item menu, could not name a discipline for **17% of stratum-A rows**.
3. **FORM is the best axis in the system** (0.831, +0.472 lift) — and FORM is the axis **retrieval does not use**.

### 1.2 The F-14 hypothesis is falsified, in the direction opposite to the assumption

F-14 claimed the pre-repair untraceable pocket (4,054 rows, 50.7% of the KB) carries a distorted FORM distribution (`causal_mechanism` 55.8% vs 8.8% in the traceable generation). Split **within** stratum A — one sampling frame, both sides proportional:

| axis | untraceable | traceable | reading |
|---|---|---|---|
| content_type | 34/51 = 0.667 | 40/49 = 0.816 | the pocket is **worse** (−0.149) |
| discipline | 24/39 = 0.615 | 18/44 = 0.409 | the pocket is *better* (+0.206) |
| extraction_type | 37/43 = 0.860 | 37/46 = 0.804 | **no material difference** |

FORM agreement does **not** degrade in the pocket. The pocket's problem is **ROLE**, not FORM — the KB is filing pocket content into the wrong *kind of object*, not mis-describing its epistemic form. That re-targets the F-14 repair from "re-derive FORM for 3,348 rows" to "re-decide ROLE for the pocket".

### 1.3 Where ROLE actually breaks (stratum B, forced-minority ⇒ per-class precision only)

| stored class | human agreement | reading |
|---|---|---|
| tool_instruction | 3/3 | clean |
| noise_drop | 2/3 | see §6 — the bin is contaminated |
| process_template | 2/3 | usable |
| process_instance | 1/2 | thin |
| quarantine | 1/4 | it is a **verification verdict worn as a content type** (see §6.1) |
| growth_edge | 0/1 | no evidence this class exists |
| **principle** | **10/34** | the forced slice is drawn from the rare-discipline and untraceable pockets — where ROLE is **29% right** |

FORM per class: `causal_mechanism` 11/15, `descriptive_model` 9/11, `empirical_pattern` 5/6, `normative_heuristic` 4/7. The `normative_heuristic`/`process_template` boundary (D2587) is the weakest FORM edge — consistent with the reviewer's notes, which repeatedly say *"not sure if its process template and not normative heuristic"*.

**The reviewer's own uncertainty text is the real finding.** Of 51 free-text notes, the overwhelming majority are of the form *"not sure if the discipline is not behavioural economics / semiotics / operations research"* — i.e. **boundary disputes between named canonical labels**, not errors of fact. When a domain expert cannot separate `behavioural economics` from `psychology` or `strategic thinking` after reading a definition, the vocabulary is under-specified, not the KB. That is a **definitional reliability** failure (Krippendorff α-class), and no amount of re-running the classifier fixes it.

---

## 2. "Post-hoc labels, not derived from the cluster" — confirmed, and here is the exact mechanism

Your suspicion is correct. The path is:

```
stage1_5  embed + FAISS cosine + source-diversity  →  clusters (topical neighbourhood, no partition)
stage2    cluster → convergent FB (name + 6 body fields)          ← NO label here
stage4    FB text → LLM FREE-GENERATION of a raw discipline string ← the label is BORN HERE
          raw string → synonym/alias table → canonical, else "emerging"
```

The label is produced **per-FB, from the FB's own prose, by a model that has never seen the corpus, the cluster, or the other rows**. `build_classify_prompt` says so explicitly:

> `"""Build a FREE scientific classification prompt — no canonical lists.` (`stage4_merge.py:472`)
> *"CRITICAL: Classify based on what the principle IS, not what label fits best from a predefined list."* (`:341`)
> *"Use precise, scientifically accurate names. If the principle is about 'neuroaesthetics', say 'neuroaesthetics'"* (`:341`)
> *"(Use the most precise discipline name you know — not generic buckets)"* (`:500`)

This is **D2138 by design** — a deliberate two-stage "free then map" architecture. It is not a bug someone introduced; it is a design choice that the measurement now falsifies.

### 2.1 Why cluster-derived labelling was not feasible — four reasons, three of them structural

You asked *why* the labels were not derived from the cluster. Each reason is checkable:

1. **The cluster is not a persistent object.** D2120/D2198 removed HDBSCAN and its partition; stage1_5 now yields a FAISS cosine neighbourhood under a source-diversity constraint, not a stable, identified group with a lifetime. A label derived from cluster identity would be **unreproducible across runs** — unacceptable for a content-addressed store whose identity rule is `sha256(name|definition)`.
2. **A convergent cluster is cross-book and deliberately cross-discipline.** The source-diversity rule *forces* merges across books; the specialist case was removed (the t11 pre-single-source-rerun directory names it). The natural label of such a unit is a *convergent claim*, not a discipline. Majority-voting a discipline across a forced-multidisciplinary cluster would produce a label that is definitionally an artefact of the merge rule.
3. **The label must attach to the FB, and the FB is content-addressed.** Identity is derived from `name|definition`. Any label that is a function of a transient cluster cannot survive a re-cluster without orphaning every edge — the same failure mode already measured in the identity layer (one rename orphans 320 edges).
4. **Naming a cluster still requires an LLM.** You cannot read a discipline off an embedding centroid. So "derive from the cluster" does not remove the LLM from the loop; it only makes the LLM's input *less* specific (a centroid, not the text).

**Therefore the correct fix is not "label from the cluster". It is "constrain and verify the label against a definition".** The label must stay a function of the FB (so it stays reproducible), but it must be chosen **from a closed, defined vocabulary** and then **checked** — which is precisely what the human just did, by hand, for 150 rows. That is mechanisable (§ market research, R1/R2).

---

## 3. Raw → canonical promotion is measurably unreliable

`taxonomy_match_method` records how each stored label was obtained. The distribution over 7,995 rows:

| method | rows | share | meaning |
|---|---|---|---|
| `synonym` | 3,990 | **49.9%** | the model did **not** produce the canonical term; a synonym table rescued it |
| `exact` | 2,127 | 26.6% | the model happened to emit the canonical term |
| `emerging_real` | 1,181 | **14.8%** | no home in the vocabulary → dumped into `emerging` |
| `alias` | 697 | 8.7% | curated override |

**Only 26.6% of the KB was labeled cleanly on the first attempt. Half needed rescue. 14.8% had nowhere to go.**

### 3.1 The rescue cost, measured against the human (the decisive causal test)

Human agreement, by how the stored discipline was obtained:

| match method | n | human agreement |
|---|---|---|
| `exact` | 41 | **0.61** |
| `alias` | 7 | 0.57 |
| `synonym` | 55 | **0.49** |
| `emerging_real` | 18 | **0.33** |

Monotone: **the more the pipeline had to intervene to place the label, the less true the label is.** Same gradient on ROLE (exact 0.68 → synonym 0.59 → emerging 0.56); FORM is flat (0.78–0.89), because FORM comes from a different, better-posed question.

Two consequences that matter more than the gradient itself:

- **The ceiling of the current design is ~0.61**, i.e. *at* the 0.60 floor. Fixing the synonym table alone cannot lift discipline above its floor, because even a perfect lookup on a free-generated string is still bounded by the string. The vocabulary and the question must change, not the map.
- **`emerging` is not a label, it is a defect counter.** 1,181 rows (14.8%) sit there, and when the human agrees it is usually *because they too were forced to say "emerging"* — a vacuous agreement deliberately excluded from the scorer.

### 3.2 The raw label space, measured

| axis | distinct raw values | canonical slots | ratio |
|---|---|---|---|
| discipline | **1,089** raw strings | 61 | 17.9 : 1 |
| domains | **4,982** raw members | 43 | **115.9 : 1** |

- **4,951 of the 4,982 raw domain members are not canonical.** Only 31 are.
- **61% of raw domain members occur exactly once in 7,995 rows** (3,040 hapax labels). A label used once, for 43 slots, is not a label — it is the model paraphrasing.
- Top non-canonical domain members by row count: `public policy` (429), `business strategy` (428), `product development` (386), `marketing` (366), `human resources` (351), `innovation management` (282), `user experience design` (278), `product management` (273), `advertising` (271).

Note what those are: **applied practice domains that the taxonomy deliberately demoted** (D2512–D2516 moved applied-practice pseudo-disciplines to domains). The model keeps re-inventing exactly the labels the taxonomy chose to abandon — because the prompt removes the vocabulary and then asks for "the most precise name you know". **The drift is not random; it is the demoted vocabulary re-entering through the front door.**

---

## 4. Are `taxonomy_v5.yaml` and `alias_map.yaml` valid representations?

### 4.1 Chronology — both suspicions are correct, in different ways

| artifact | first commit | reading |
|---|---|---|
| `config/taxonomy_v5.yaml` | **2026-07-20** — the `v2.0 initial commit`, alongside the pipeline | NOT post-hoc relative to the first extraction, but **contemporaneous with it**: induced in the same moment, from the early corpus |
| `config/alias_map.yaml` | **2026-09-02** — *6 weeks later* | **post-hoc by construction.** It is a drift ledger, accreted to absorb what the free-generation path emitted |

So: the taxonomy was **not** fitted to a first extraction afterwards — but it was authored **before the corpus had a chance to disagree with it**, on a small early sample. The alias map *is* post-hoc, and it is the forensic record of the disagreement: **362 + 637 = 999 curated rescue rules for 104 canonical slots.**

Whether 61 disciplines × 43 domains is "the highest representative" for a 1,000-book corpus: **the data says no, it is a bias-drift surface.** Evidence:

- 14.8% of rows have no home at all (1,181 `emerging`).
- A single discipline (`psychology`) holds 11.3% of rows; the distribution is a long tail under a few dumps.
- 4,982 distinct raw domain strings for 43 slots means the canonical set is **not the modal vocabulary of the corpus** — it is a curated projection of it.
- `discipline = 'emerging'` needed a dedicated repair script (`pipeline/reclassify_merged_axis.py`, ~2,343 rows, D2532) because it is used as a **fallback, not a category** (D2485 `emerging_real`).

### 4.2 Alias-map internal validity (5 defects, all measured, none fatal)

| check | result | severity |
|---|---|---|
| dangling targets (value not canonical) | **0** of 999 | clean |
| genuine duplicate keys (silent YAML loss) | **0** of 999 | clean |
| alias → alias chains | **0** | clean |
| no-op aliases (key == target) | **0** | clean |
| **same raw string present in BOTH tables** | **53** | **medium** — the axis is decided by column position, so a string that legitimately names a domain can be filed as a discipline |
| **one alias key IS the other axis's canonical** | **1** (`urban planning` in `discipline_aliases`) | low — the kind-swap class D2519 already patched |
| **list-valued domain aliases (1 raw → 2 canonical)** | **43** of 637 | medium — fan-out with no recorded preference; the reader may take `[0]` or all |
| alias density | 5.9 : 1 (discipline), **14.8 : 1 (domains)** | high — density is a *symptom*; a healthy controlled vocabulary is ≈1–2 : 1 |

**Verdict on the alias map:** it is *internally well-formed* (no dangling, no silent loss) and *strategically wrong*. A 14.8:1 rescue table is not an alias map, it is a **compensating control for a prompt defect**. Its size, not its contents, is the finding.

**Verdict on the taxonomy:** structurally sound (disciplines and domains are genuinely separate top-level keys — this is why D-271a could be ruled a declared homonym and left alone), but **under-defined for its use**. Which labels fail is not random — see §5.

---

## 5. "The canonical labels are too vague" — confirmed, and it is a specific, fixable list

The reviewer's disagreement is not spread evenly. Split by stored discipline:

| stored discipline | n | human agreement | class |
|---|---|---|---|
| `typography` | 3 | **1.00** | concrete craft |
| `information science` | 3 | **1.00** | concrete field |
| `organizational theory` | 3 | **1.00** | concrete field |
| `research methodology` | 6 | 0.83 | field (the D-271a homonym) |
| `human-computer interaction` | 6 | 0.83 | concrete field |
| `operations research` | 6 | 0.83 | concrete field |
| `computer graphics` · `semiotics` · `media studies` | 3 each | 0.67 | field |
| `design thinking` · `strategic thinking` | 7 each | 0.57 | **abstract method-word** |
| `software engineering` · `philosophy` | 4 each | 0.50 | mixed |
| `psychology` | 9 | 0.44 | **catch-all broad field** |
| `linguistics` | 3 | 0.33 | thin |
| `behavioral economics` | 5 | **0.20** | **abstract hybrid** |
| `cultural design` | 3 | **0.00** | **abstract coinage** |
| `emerging` | 9 | **0.11** | **not a category** |

**The pattern is crisp and it is the answer to your question:** the labels that fail are the **abstract, hybrid, coined, or method-named** ones — `design thinking`, `strategic thinking`, `behavioral economics`, `cultural design`, `design psychology` — and the catch-alls `psychology` and `emerging`. The labels that succeed are the **concrete, discipline-of-record, library-shelf** ones — `typography`, `information science`, `operations research`, `human-computer interaction`, `computer graphics`.

This is the classic **faceted-classification failure**: a facet value must be *mutually exclusive and definitionally anchored* (`scope note`, `include`, `exclude` — the SKOS/AAT pattern) or it cannot be applied by two independent agents with the same answer. `design thinking` and `strategic thinking` are not disjoint; `behavioral economics` and `psychology` overlap; `cultural design` is a coinage no two people will bound identically. The taxonomy already has `exclude` lists for *some* entries — the fix is to make definition + include + exclude **mandatory and discriminating for all 104 slots**, and to **demote or delete any slot that cannot be given disjoint boundaries**.

Actionable, and small: **~8–12 slots** are carrying the drift. That is a one-day vocabulary repair, not a re-engineering.

---

## 6. Noise, summaries, and the contaminated bin

Your instinct that "there is a lot of noise and summaries" is right, but the noise is in a different place than it looks.

### 6.1 The quarantine bucket is 40.7% of the KB, and it mixes four different things

`status`: **PASS 4,745 (59.3%) · QUARANTINE 3,250 (40.7%)**.

`QUARANTINE` is produced by stage 5, which is fail-closed (D2093): `ENTAIL ≥ 0.10 → PASS`, `NEUTRAL (unverifiable) → QUARANTINE`, `CONTRA → QUARANTINE`. So the KB currently **conflates "I could not verify this" with "this is not knowledge"**, and the cost is concrete:

- **1,780 rows labelled `principle` are hidden from retrieval** (retrieval defaults to `status='PASS'`).
- **2,940 hidden rows carry a real, non-`emerging` discipline.**
- 2,744 of the 3,250 sit at the `confidence_score` cap (0.25).
- `contradicts_fbs` is **NULL for 100% of rows** — contradiction is *never* recorded, so "CONTRA" and "NEUTRAL" are indistinguishable in the store. The distinction that the fail-closed rule depends on is **not persisted**.

This is the single most consequential retrieval finding in this report: **the KB's usable core is 59.3% of itself, and 22% of its principles are unreachable by default.**

### 6.2 The `noise_drop` bin is contaminated with real content

Stratum B sampled `noise_drop` deliberately: the human re-classified **2/3 as `noise_drop` but agreed only 1/4 on the `quarantine` rows**, and across the sheet, stored `noise_drop` rows were called `principle` 9 times and stored `quarantine` rows `principle` 4 times. Combined with the reviewer's notes — *"valid fact but irrelevant"*, *"doesn't provide any exact utilizable instruction, serves more like a SUMMARY even though random is important"* — the pattern is unmistakable:

> **The KB has no RELEVANCE axis, so `noise_drop` is doing two jobs at once:** "this is not an extractable object" (ontological) and "this is true but I don't care" (user-relative). Those are different axes, and the second one is *yours*, not the corpus's.

Saracevic's relevance framework (JASIST 2007) is the canonical statement that relevance is **relational** — it exists between a document and a *user with a goal*, not as an intrinsic property of the text. Maxwell OS's mission is personal (design, business, self-improvement, fringe interests). Therefore relevance must be a **separate, personal, revisable axis** (or a scored field), never fused into a content type. The reviewer said this out loud, repeatedly, and the schema has nowhere to put it.

### 6.3 The summary gate works — but it leaves no ledger

`is_summary` is `0` for **100% of stored rows**, which looks like a dead field. It is not: gated clusters are dropped at S2 (`stage2_extract.py:2502`, D2417 content-type-aware) and **never become FBs**. `knowledge pipeline/stage2_extract/t11/checkpoint.jsonl.gated_ids` holds **158 gated cluster ids** — the gate fires.

But its *output is invisible*: there is no ledger of what was dropped and why, so "how much did we throw away, and was it right?" is unanswerable. That is a §8-class observability defect, not a logic defect. It is also the reason the reviewer kept writing "SUMMARY" on rows that reached the sheet anyway: the gate is content-type-aware, so a summary that defaulted to a non-principle role **passes the gate**.

### 6.4 The corpus's own quality signal does not predict label quality

67.5% of the KB is single-source (5,398 / 7,995); `is_convergent` is true for only 2,603 rows. Convergent extraction is the corpus's headline quality claim. Measured against the human discipline label:

| source diversity | n | discipline agreement |
|---|---|---|
| 1 source | 82 | 0.54 |
| 2 sources | 19 | 0.37 |
| 3+ sources | 20 | 0.55 |

**No monotone relationship.** Convergence is not currently buying label accuracy. (It may well buy *claim* accuracy — a different question, untested here — but it is being used as a trust proxy it has not earned for labels.)

---

## 7. THE AXIS INVERSION — the core structural finding

| axis | human-measured reliability | used in retrieval? | how it is filtered |
|---|---|---|---|
| **extraction_type (FORM)** | **0.831** ✅ | **NO** | — |
| content_type (ROLE) | 0.740 (−0.010 lift ❌) | only via `status` | — |
| discipline | **0.506** ⚠️ | **YES — primary** | `discipline = ?` exact |
| domains | not measured (deferred) | YES | `domains LIKE '%x%'` substring |
| depth | not measured; undefined for all non-principle rows | YES | `depth = ?` exact |
| status | — | YES | default `status='PASS'` |

**The axes are ordered inversely to their measured reliability relative to their retrieval load.** The most reliable label in the system is unused; the least reliable is the primary exact-match filter; and a third `depth` is *defined only for rows that pass* (worth noting: all 1,470 non-principle rows have empty `depth`, so `depth` is structurally coupled to ROLE, not independent of it).

Add §6.1 and the compounding is severe: **an exact-match filter on a 0.506-accurate label, over a 59.3% slice of the KB.** That is the mechanism behind "we go in circles and every day a new weak point appears" — the retrieval layer is a narrow pipe built on the weakest field, so every sample finds a new hole.

Also note: `domains` top value is `["emerging"]` (8.8% of rows) — the catch-all propagates into the domain axis too. And `PASS ⟺ content_type='principle'` exactly (4,745 = 4,745; **zero** non-principle rows pass), so in the live KB **ROLE has exactly one effective value**. The 5-role ontology is, in production, decorative.

---

## 8. Schema theatre: 24 of 45 attribute columns are dead or near-dead

Not all constants are defects — **stamps** (`schema_version`, `gen_model`, `verifier_model`, `taxonomy_version`, `fb_version`, `pipeline_commit`, `pipeline_run_id`) are R14 provenance and *should* be constant for a single generation event. Their constancy is information. The rest are not:

| genuinely dead field | value | what it means |
|---|---|---|
| `contradicts_fbs` | NULL 100% | **contradiction detection does not exist in production** |
| `classification_status` | `CLEAN` 100% | the write-boundary validator has **never** reported anything |
| `classification_error` / `classification_errors` | empty / `None` ×7,993 | the 1,002 domains-contract violations (BUG-273) were **never recorded** |
| `provenance` | `llm_extracted_from_source` 100% | the F-02 tier system (human-blind/attested/model/frontier) is **not in use** |
| `prerequisite_fbs` · `procedural_skill` | `[]` · `''` 100% | no prerequisite graph, no skill graph |
| `usage_count` · `last_retrieved_at` | `0` · `''` 100% | **no retrieval telemetry at all** |
| `feedback_score` · `feedback_count` | `None` · `0` 100% | no feedback loop |
| `borp_score` | `0.0` 100% | dead |
| `is_summary` | `0` 100% | correct by construction (see §6.3) but leaves **no drop ledger** |
| `evidence` | `cited` 95.5% | near-dead |
| `depth` | `''` for all 1,470 non-principle rows | the facet is undefined for 18.4% of the KB |

**Why this matters more than it looks.** These fields are the *instrumentation*. `usage_count`/`last_retrieved_at`/`feedback_score` being uniformly empty means **the system has no idea which of its 7,995 rows have ever been used** — so "is the KB good?" cannot be answered by usage, only by a hand-run ruler. `contradicts_fbs` being empty means the "eliminate contradictions" goal has **no implementation whatsoever**. `classification_status = CLEAN` for 100% of rows means every write-boundary guard is a no-op in practice.

This is the honest answer to "new weak points pop up every day": **the instrumentation reports health, so failures stay invisible until a human samples the data.** The ruler found in 150 rows what 24 green columns had been reporting as fine.

---

## 9. Is the knowledge runtime reliable to build on?

**Yes — conditional on five bounded repairs. No — if the labelling instrument is left as it is.**

### 9.1 What is genuinely solid (do not touch)

- **Identity layer**: 7,995 objects, 164,202 identity-keyed edges, **0 dangling**, and the rename-freeze measurement already done (D-271c). Measured, sound.
- **Provenance spine**: every row traceable to `source_segments`/`source_books`/`source_principle_ids`; `evidence_passages` populated (7,990 distinct).
- **Stage 5 exists and is fail-closed.** It over-rejects, but a fail-closed verifier that over-rejects is a *tunable* verifier. That is a good starting position, not a bad one.
- **FORM**: 0.831 against the human. This axis is production-grade **today** and is being wasted.
- **Discipline structure**: 61/43 genuinely separate axes; D-271a's homonym ruling validated (0 undeclared collisions over 7,995 rows).
- **The pipeline runs end-to-end and is crash-safe** (C6/C13 patterns, atomic writes, backups — modulo the dead `backup_guardian.sh`, BUG-276).

### 9.2 The five repairs that stop the circling

| # | repair | replaces | cost | human? |
|---|---|---|---|---|
| **R1** | **Constrained classification**: show the model the closed menu **with each label's definition**, require one of N (or an explicit `none`), and log the raw answer alongside. Kills the synonym layer at the source. | `build_classify_prompt` "no canonical lists" | ~1 day + one corpus re-label run | no (ruling: yes) |
| **R2** | **Definition-anchored verification**: score each candidate label's definition against the FB text with the **existing DeBERTa NLI** (this is the Yin et al. 2019 entailment-classification method) and keep the label only if it entails. Uses hardware already loaded. | synonym/alias rescue table | ~2 days | no |
| **R3** | **Split `QUARANTINE` into `UNVERIFIED` vs `CONTRADICTED`**, persist the S5 verdict, and stop letting "verifiable-but-unverified" hide a row from retrieval. Recovers ~1,780 principles into reach. | the NEUTRAL→QUARANTINE conflation | ~half day | **yes (1 ruling)** |
| **R4** | **Give relevance its own axis** (user-relative, revisable, scored), separate from `noise_drop` (ontological). The reviewer asked for this ~10 times. | noise_drop doing two jobs | ~1 day | **yes (1 ruling)** |
| **R5** | **Repair ~10–12 under-defined vocabulary slots** (mandatory definition + include + exclude; demote `cultural design`, `design thinking`, `strategic thinking`, `behavioral economics`, `design psychology`, `emerging` or make them disjoint with scope notes). | the vagueness measured in §5 | ~1 day | **yes (ratify the slot list)** |

**None of these is a re-engineering.** They touch one prompt, one verifier call, one enum, one axis, and one YAML file. The 8-stage pipeline, the identity layer, the schema and the object/property logic all survive unchanged — which is the answer to your "does it require serious restructuring" question: **no, it requires instrument repair, not architecture repair.**

### 9.3 The one thing that WOULD be a re-engineering (and should be deferred)

Making the *label* cluster-derived (your original question) — that would require re-introducing a persistent partition, a stable cluster identity, and re-keying every edge to it. §2.1 shows why the payoff is negative. **Do not do it.** Constrain the post-hoc label instead.

---

## 10. Ranked findings (consequential order)

| # | finding | severity | evidence | human gate? | fix |
|---|---|---|---|---|---|
| **F-A** | **Axis inversion** — retrieval's primary exact filter (discipline 0.506) is the least reliable, while the best axis (FORM 0.831) is unused | **CRITICAL** | §7 | no | R1+R2 |
| **F-B** | **NEUTRAL→QUARANTINE conflation** hides 40.7% of the KB incl. 1,780 principles; S5 verdict not persisted | **CRITICAL** | §6.1 | yes (enum) | R3 |
| **F-C** | **Free-generation labelling** (D2138) contradicts the module docstring's D316 claim; 49.9% synonym rescue, 14.8% `emerging` dump; ceiling 0.61 ≈ floor | **CRITICAL** | §3, §6 | no | R1 |
| **F-D** | **ROLE is decorative in production**: `PASS ⟺ principle` (4,745 = 4,745, zero non-principle pass); role accuracy −0.010 lift over a constant answer | **HIGH** | §1.1, §7 | yes | R4 |
| **F-E** | **No relevance axis** — `noise_drop` fuses "not extractable" with "true but irrelevant"; the reviewer asked for the split ~10× | **HIGH** | §6.2 | yes | R4 |
| **F-F** | **~10–12 under-defined vocabulary slots** carry the drift (abstract/hybrid/coined labels 0.00–0.44 vs concrete 0.83–1.00) | **HIGH** | §5 | yes | R5 |
| **F-G** | **F-14 was misdiagnosed**: FORM does *not* degrade in the untraceable pocket (0.860 vs 0.804); ROLE does (0.667 vs 0.816). Re-target the repair | **HIGH** | §1.2 | no | retarget |
| **F-H** | **Instrumentation is decorative**: 24/45 attribute columns dead/near-dead; `contradicts_fbs` empty, `usage_count` 0, `provenance` one tier, `classification_status` always CLEAN | **HIGH** | §8 | no | add telemetry |
| **F-I** | **Alias map is a compensating control**, not a synonym list (14.8:1 domains; 999 rules/104 slots; 53 dual-axis keys; 43 fan-outs) | MEDIUM | §4.2 | no | dissolved by R1 |
| **F-J** | **Convergence does not predict label quality** (1src 0.54 / 2src 0.37 / 3+src 0.55); 67.5% single-source | MEDIUM | §6.4 | no | measure separately |
| **F-K** | **Summary gate fires (158 gated) but leaves no ledger**; `is_summary` reads 100% false | LOW-MED | §6.3 | no | drop ledger |
| **F-L** | Discipline floor is **UNRESOLVED**, not failed (0.506, CI [0.401, 0.611], 17 unanswered stratum-A rows) — ~85 more rows decide it | MEDIUM | §1.1 | yes | continue the ruler |

---

## 11. What this does to the priority register

- **#1 stays: certify the ruler (G4).** It has now paid for itself once already — it falsified F-14's FORM hypothesis, exposed the axis inversion, and located the drift in ~10 vocabulary slots. But it is **not finished**: discipline needs ~85 more stratum-A rows to resolve its floor (F-L). **Continue the ruler on discipline** before acting on R5.
- **NEW #2: F-B (the quarantine conflation).** It is the largest single recall loss in the system and the cheapest to fix. It outranks the identity layer because it changes how much of the KB is *reachable*.
- **NEW #3: F-C/R1 (constrained classification)**, which then dissolves F-I and much of F-F.
- **F-G retargets** the F-14 work: re-decide ROLE on the pocket, do not re-derive FORM.
- **Unchanged:** BUG-276 (dead backup, now also protecting the upcoming bulk writes), then the identity layer (D-271c).

**The honest bottom line for "are we going in circles": no — but the loop was real, and it had one cause.** Every cycle was re-discovering the same defect from a new angle because the label path was free-generation (F-C) and the instrumentation was green (F-H). The ruler is the first instrument in this project that can *see* the defect. Keep the instrument, fix the five bounded things, and the loop ends.

---

## 12. Open questions this measurement could not settle

1. **`domains` was deferred** from the ruler (axes_deferred). It is the second retrieval facet with a substring filter. Unmeasured.
2. **`depth` was deferred** and is undefined for all non-principle rows. Its 789 `cross-domain` rows load-bear the discipline axis — unmeasured.
3. **Claim-level accuracy** (is the *content* true?) was not tested; only *label* accuracy was. Convergence may predict claim quality even though it does not predict label quality (F-J).
4. **The 158 gated clusters** were never audited for false drops.
5. **S5's NEUTRAL/CONTRA split** is not recoverable from the DB (`contradicts_fbs` empty; `verification_results` holds one check). Re-measuring requires a stage-5 re-run on a sample.

---

# 13. SECOND-PASS FORENSIC (same day, 2026-09-19) — auditing my own analysis

The first pass examined the **labels**. It did not examine the **retrieval path**, the **ingestion path**, or my own
**sampling frame**. This section does all three, and it **corrects three of my own earlier claims**. Ordering is
deliberate: the corrections come first.

## 13.0 Corrections to my own earlier findings (read these before quoting sections 1, 6 and 7)

| my earlier claim | corrected | evidence |
|---|---|---|
| **§1.1** "ROLE 0.740 vs baseline 0.750, lift −0.010" | **The frame was mis-specified.** The sheet sampled the **full KB** (47.3% PASS rows in the sheet vs 59.3% in the KB), i.e. it mixed retrievable and hidden rows. Restricted to **`status='PASS'`** (what you can actually retrieve): ROLE = **0.891, baseline 0.891, lift exactly 0.000**. The conclusion is now *cleaner and stronger*: on the retrievable slice ROLE carries **zero information** over a constant answer, and on the quarantined slice it is **0.472 vs a 0.500 constant** (worse than a constant). Discipline is unaffected (0.492) and FORM improves slightly (0.852). | §13.5 |
| **§7** "discipline is the **primary exact-match filter**" | **The filter does not constrain the result set.** `search_fts` and `search_vector` take **no facet parameters**; only `search_keyword` applies `discipline = ?`; `search_hybrid` returns the fused top-N with **no post-filter**. Measured: with `discipline='typography'`, **2 of the RRF top-10 were not typography**. The facet is not an exact filter — it is a *nudge applied to one of three legs*. | §13.2 |
| **§6.1** "40.7% of the KB is **invisible** to retrieval" | **Invisible only to the direct path.** `graph_expand` selects neighbours with **no status predicate** (`SELECT … FROM fbs WHERE fb_id = ?`) and `search_graph` defaults to `include_contradictions=True, include_prerequisites=True`. Quarantined rows therefore **re-enter results as graph neighbours of a PASS seed**. The defect is worse than "hidden": the hiding is **inconsistent**, so the same row appears or not depending on whether a PASS row points at it. | §13.3 |

**F-14 retargeting (§1.2) stands unchanged** — it was measured within stratum A only.
**The root causes (F-C free-generation, F-H decorative instrumentation) stand unchanged.**

## 13.1 H1 — the write guard rejects the RULED-LEGAL label (CRITICAL, and it breaks my R1)

`pipeline/schemas.py::validate_discipline_domain` is enforced as a **hard error** at two write points:

- `pipeline/stage4_merge.py:823` — `for flag in validate_discipline_domain(discipline, domains): errors.append(flag)` → the row is **quarantined**
- `pipeline/stage6_commit.py:402` — `if dd_flags: … — REJECTED (fail-closed, D2620); return False` → the row **cannot be inserted at all**

And the guard fires on the **discipline alone**, independent of the row's own domains:

```
validate_discipline_domain('research methodology', ['brand identity'])  -> ["DECLARED: … DECLARED HOMONYM"]
validate_discipline_domain('research methodology', None)                -> ["DECLARED: … DECLARED HOMONYM"]
```

**Consequence:** D-271a ruled that `research methodology` **stays canonical** ("change nothing"), but **the code
enforces the opposite**. Every *new* row classified as `research methodology` is quarantined at S4 and rejected at
S6. The 261 rows in the DB predate the guard (D2620/D2626 landed 2026-09-17). The ruling is **not in force**.

**Why this matters for the solution, not just the record:** my **R1** repair proposes a closed menu of the 61
canonical disciplines. `research methodology` is one of them (83% human agreement — one of the *good* labels).
**Under the current guard, every correct answer of `research methodology` would be destroyed at the write
boundary.** R1 therefore cannot ship without a config-driven exemption for declared collisions — otherwise the
repair introduces a new, silent, data-destroying failure mode on the 6th-best label in the taxonomy.

## 13.2 H3 — the facet filters do not constrain retrieval (HIGH; measured)

`search_hybrid` (`pipeline/retrieve.py:329`) fuses three legs:

| leg | facet filters accepted |
|---|---|
| `search_fts(conn, query, limit, exclude_summaries, include_quarantine)` | **none** |
| `search_vector(conn, query, limit, ..., vec_table)` | **none** |
| `search_keyword(conn, domain, discipline, depth, …)` | **all** — and it is **only called when a filter is present** (D2511) |

Then: `results = [fb_map[fid] for fid in ranked_ids[:limit]]` — **no post-filter**. The optional cross-encoder
rerank (`BAAI/bge-reranker-v2-m3`, local CPU) reorders the pool by query relevance and **cannot restore the
facet**, so it can *promote* a filter-violating row into the top-k.

**Empirical (live DB, FTS + filtered-keyword legs, production RRF formula k=60):**

```
query='visual hierarchy design'  filter: discipline='typography'
  FTS leg      n=50  disciplines present: cultural design, decision making, design thinking,
                     emerging, human-computer interaction, information science, motion & time, psychology
  keyword leg  n=50  disciplines present: typography
  RRF top-10   -> 2 of 10 have discipline != 'typography'
```

Adding the (unfiltered) vector leg makes it worse. **So `discipline='…'`, `domain='…'` and `depth='…'` are
advisory, not constraining** — which also means every "facet count" claim in this project (including the 261/648
homonym rows and the 907/1538 maxima) describes the *label distribution*, never a *result set*.

**Fix:** apply the facet predicate to **all** legs (or post-filter the fused candidate pool before truncating to
`limit`), then re-run the retrieval benchmark. Adding legs to RRF **before** this fix amplifies the leak.

## 13.3 H4 — graph expansion leaks the quarantined 40.7% back in (HIGH)

```
graph_expand():  "SELECT fb_id, related_fbs, contradicts_fbs, prerequisite_fbs FROM fbs WHERE fb_id = ?"
                 "SELECT fb_id, name, definition, domains, borp_score FROM fbs WHERE fb_id = ?"
```

No `status` predicate, on either query, and `search_graph` passes `include_contradictions=True,
include_prerequisites=True` by default. Seeds are PASS-only; **neighbours are not**. Because the edges were built
from `discipline_overlap` / `domain_overlap` / `source_crossover` — i.e. **from labels that were ~50% wrong during
the generation window** — graph expansion simultaneously (a) leaks NLI-unverified content into the answer set and
(b) **propagates label error structurally**.

**Fix:** propagate the seed's status policy into expansion, or return neighbours with an explicit verification
tier instead of silently mixing them.

## 13.4 H5 — the retrieval corpus is 11.1% of the knowledge (HIGH)

| what is embedded / indexed | chars | share of the FB body |
|---|---|---|
| `definition` — the **only** text the 512d vector leg sees | 1,765,980 | **11.1%** |
| `mechanism` + `boundary` + `application` + `failure_mode` + `consequence` + `elaboration` — **embedded: NO, FTS: NO** | **14,152,908** | **88.9%** |
| `evidence_passages` — **verbatim source**, up to 5 quotes/FB, 7,990 distinct — **indexed by nothing** | 4,802,857 | — |

`fbs_fts` indexes `name, definition, keywords, jargon` only. So:

- the **vector leg is blind to 88.9%** of every FB — including `mechanism`, which is the field the entire FORM
  axis is *about*;
- **4.8M chars of real source text are searchable by nothing at all**;
- and `source_text` — the column that *sounds* like source — is **not source**: 100% of rows contain
  `"[book.md] " + definition`, median **300 chars**, min 138, max 695. It is the synthesis again, with a filename.

**This is the honest answer to "do we have accurate source text for retrieval": no — we have the synthesis, and the
evidence is unindexed.**

## 13.5 H13 — the ruler's sampling frame (self-correction; MEDIUM)

| frame | content_type | discipline | extraction_type |
|---|---|---|---|
| all stratum A (as reported) | 0.740 [0.646, 0.816], lift −0.010 | 0.494, lift +0.412 | 0.831, lift +0.472 |
| **`status='PASS'` only** (retrievable) | **0.891 [0.791, 0.946], baseline 0.891, lift +0.000** | 0.492, lift +0.393 | 0.852, lift +0.426 |
| `QUARANTINE` only | 0.472 [0.320, 0.630], baseline 0.500, lift −0.028 | 0.500, lift +0.375 | 0.786, lift +0.321 |

Two estimands are being conflated: *"is the stored label trustworthy across the KB?"* (the all-rows frame) and
*"is what I retrieve correctly labelled?"* (the PASS frame). **Both must be reported, and the ruler strata should
be crossed with `status`** so neither answer is smuggled in by the other. The correction *strengthens* the ROLE
finding (lift exactly 0.000) and leaves the other two axes intact.

## 13.6 H6/H7 — two illegal values sitting inside the retrieval facets (MEDIUM)

- **`emerging` is used as a DOMAIN on 744 rows but is not one of the 43 canonical domains.** The `domains`
  column holds 44 distinct values of which **1 is not canonical** — a live schema violation of the same class as
  BUG-273, and it sits *inside* a facet filter.
- **`discipline='emerging'` on 447 rows that are `status='PASS'`.** The fallback value is therefore a member of
  the *exact-match* facet: `discipline='emerging'` returns 447 rows of "we don't know". A human reviewer also used
  `emerging` 9 times — so the fallback and the answer space are the same string, which is a vocabulary-design
  error independent of accuracy.

## 13.7 H8 — 29.1% of "convergence" is the same book ingested twice (MEDIUM, and it feeds stage 1.5)

`source_diversity` counts **filenames**, not works. Measured: of the **2,597** rows with `source_diversity ≥ 2`,
**757 (29.1%)** collapse to fewer distinct works under filename normalisation. The corpus carries **1,300 distinct
book filenames but only 369 work-identities have >1 filename** (e.g. `About Face The Essentials of Interaction
Des…` vs `About Face. The Essentials of Interaction Des…`; `Design The Key Concepts (D. J. Hatz) (z-library.sk)`
vs `Design The Key Concepts (D. J. Huppatz).md`).

Why this is not cosmetic:
- `source_diversity` is the **merge criterion at stage 1.5** → an inflated diversity signal produces **merges that
  should not have happened**;
- `is_convergent` (2,603 rows) is the corpus's **headline quality claim** and is partly an artefact of duplicate
  ingestion;
- it also explains part of §6.4 (convergence does not predict label quality) mechanistically.

**This is an ingestion-layer defect that no label repair touches.** Work-identity dedup is a prerequisite.

## 13.8 H9/H10 — two latent risks, one refuted hypothesis (LOW/MEDIUM)

- **H9 — FTS has an INSERT trigger only.** `sqlite_master` holds exactly one trigger, `fbs_ai`. An
  external-content FTS5 table (`content='fbs'`) needs the insert **+ update + delete** trio; `reclassify_merged_axis.py:314`
  and `feedback.py:140/237` issue `UPDATE fbs`, and `stage6_commit.py:409` uses `INSERT OR REPLACE` (= delete+insert).
  **I predicted a stale index and measured it: `INSERT INTO fbs_fts(fbs_fts) VALUES('integrity-check')` on a
  throwaway copy PASSED — the index is consistent.** So this is **latent, not live** (stage6 rebuilds). It stays
  logged because nothing in the pipeline *detects* staleness: the invariant is one line and is missing.
- **H10 — mega-merges exist.** 883 rows have >10 sources, **558 >20, 65 >50, max 244** sources for one FB
  ("Visual Data Structuring", diversity 60; "Brand As Reputation and Identity", 69; "Typeface As Communicative
  Medium", 84). A claim that 244 books converge is almost certainly an over-merge. **Measured impact on labels:
  none detectable** — the sheet holds only 8 rows at 21+ sources.

**Refuted hypothesis (recorded so it is not re-run):** I proposed that over-merged FBs become *unlabelable*.
**It is the opposite.** Discipline-blank rate by source diversity: 1 source **24.1%**, 2 → 9.5%, 3–5 → 0%, 6–10 →
0%, 11–20 → 0%, 21+ → 12.5%. And `is_convergent` rows are 7% blank vs 24% for non-convergent. **Singletons are
~3× more likely to be unlabelable than merged rows** — consistent with §1.1's blanks, since the untraceable pocket
is *exactly* the singleton population (all 83 rows have `source_diversity = 1`).

## 13.9 H14 — a label-dependent vector table sits one argument away from production (MEDIUM)

`contextual_embed.enabled: False` in config — so **production vectors are NOT label-poisoned** (my first
hypothesis, refuted; good). But `backfill_embeddings.py --contextual` has **already run**: the live DB contains
`vec_fbs_ctx` (**7,995 rows**) holding embeddings of `discipline | domains | name . definition`, and
`pipeline/retrieval_benchmark.py:159` fuses that table as an A/B leg:

```
vec = search_vector(conn, query, limit=pool, vec_table="vec_fbs_ctx")
```

**With labels at ~0.5 accuracy, flipping production to that table creates a self-reinforcing loop**: wrong label →
label-prefixed embedding → retrieval prefers rows sharing the wrong label → the error is confirmed by retrieval and
becomes invisible. **Guard needed:** production must not point at `vec_fbs_ctx` while any label axis is below its
floor, and re-embedding becomes mandatory after R1/R5 land anyway.

## 13.10 Consolidated second-pass ranking (what to fix, in order)

| # | finding | severity | fixes what | human? |
|---|---|---|---|---|
| **H2-1** | **facet filters do not constrain retrieval** (§13.2) | **CRITICAL** | a correctness bug no label repair touches; prerequisite for any new leg | no |
| **H2-2** | **write guard rejects the ruled-legal label** (§13.1) | **CRITICAL** | blocks R1 as specified; destroys data | **yes (1 line)** |
| **H2-3** | **graph expansion leaks quarantined rows** (§13.3) | **HIGH** | corrects the quarantine fix (R3) scope | no |
| **H2-4** | **retrieval corpus = 11.1% of the knowledge; 4.8M chars of evidence unindexed** (§13.4) | **HIGH** | the actual "accurate source text" gap | no |
| **H2-5** | **29.1% of convergence is duplicate ingestion** (§13.7) | **MEDIUM** | the merge criterion at stage 1.5 | **yes** |
| **H2-6** | illegal facet values: `emerging` as a domain (744) and as a discipline inside PASS (447) (§13.6) | MEDIUM | facet hygiene | no |
| **H2-7** | `vec_fbs_ctx` one argument from production (§13.9) | MEDIUM | a self-reinforcing loop | no |
| **H2-8** | FTS lacks update/delete triggers; integrity never checked (§13.8) | LOW | latent staleness | no |
| **H2-9** | mega-merges up to 244 sources (§13.8) | LOW | merge sanity gate | no |
| **H2-10** | ruler strata not crossed with `status` (§13.5) | MEDIUM | estimator validity | no |

## 13.11 Chunk-level retrieval and RRF — direct answer

**RRF is already implemented and correct.** `search_hybrid` uses `Score(d) = Σ 1/(k + rank)` with `RRF_K = 60`,
1-based ranks, three legs, the D2511 keyword-pollution fix, and RRF is rank-based (not score-based). There is
nothing to adopt; there is something to *feed*.

**Chunking: yes — but it is the second fix, not the first, and the first is nearly free.**

1. **Do this first (no re-ingestion, no new corpus):** make the existing legs cover the FB. `mechanism`,
   `boundary`, `application`, `failure_mode` into FTS (recover 88.9% of the searchable body); embed the full body
   instead of `definition` alone; and index `evidence_passages` (**4.8M chars already in the DB, currently
   searchable by nothing**) as a fourth RRF leg. **This is where the missing "accurate source text" already lives.**
2. **Then add a chunk/evidence leg — and the cost is measured, not estimated.** The DB's `source_segments`
   (214,220 references) join the stage-1 checkpoint **exactly**: `knowledge pipeline/stage1_chunk/t11/checkpoint.jsonl`
   (741.7 MB, 299,861 segments, keys `segment_id, text, source_book, source_path, section_title, section_heading,
   word_count`) — sampled **205,813 / 205,813 = 100%** of DB segment hashes are verbatim checkpoint `segment_id`s.
   So a chunk leg needs **~214k vectors (≈438 MB at 512d float32)**, one local embedding job, **no mapping work,
   no re-chunking, no re-extraction**, and each hit returns **verbatim source text + section heading + a direct
   parent-FB link** (retrieve the chunk, return the FB — parent-document retrieval).
3. **Only after that**, consider indexing all 299,861 segments (adds content that produced no FB — a different
   feature: corpus-level search).

**Caveats that must ship with it:** chunk-level retrieval fixes **grounding precision, not label accuracy**; the
segments inherit the corpus defects (369 duplicate works → duplicate chunks); 300-word chunks with 50-word overlap
(**config: `chunk_size_words: 300`, `chunk_overlap_words: 50`**) will return near-duplicate neighbours, so adjacent
chunks need collapsing at fusion; and **adding legs before fixing §13.2 amplifies the filter leak.**

## 13.12 What changed in the priority register

**NEW #1 (H2-1) — constrain the facet filters.** It is a *correctness* bug: the discipline/domain/depth filters
currently do not filter. Every downstream conclusion about facets (including D-272b's framing) had to be re-stated
because of it, and it silently degrades every query you have ever run.

**NEW #2 (H2-2) — exempt the declared homonym from the write guard.** One config-driven line, human-owned, and a
hard prerequisite for R1.

**R3 (quarantine split) is now larger in scope** — it must fix the *graph-leak* path too, or splitting the enum
just moves the inconsistency.

**Unchanged:** R1, R2, R4, R5, the identity layer, BUG-276, and the verdict that this is instrument repair rather
than re-engineering.
