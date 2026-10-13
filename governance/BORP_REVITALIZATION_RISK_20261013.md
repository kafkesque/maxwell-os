# BORP — REVITALIZATION RISK ASSESSMENT AND HARDENING DESIGN

> **Authority:** D-2990 (minted with this file) · **Requested by:** the owner, T-107 · **Date:** 2026-10-13
> **Evidence (the archaeology):** `governance/BORP_FEEDBACK_ASSESSMENT_20261013.md`
> **Bugs of record:** BUG-767 (a retired metric still leaves the machine), BUG-768 (the principle is satisfied by
> 20.8% of the served corpus), BUG-769 (FIXED). **Tasks:** T-107 (one owner word per advertised field), T-118 (the
> single-source trust tier), T-119 (this file's §8: the collapse-delta measurement).
> **The rail:** `scripts/check_served_fields.py` (advertised field → declared disposition). **The rule:**
> `config/served_fields.yaml`.

---

## §0 — THE QUESTION, AND THE ANSWER IN ONE LINE

**Asked (verbatim):** *"does BORP revitalization carry any risk, threat, can cause any cascade issue, leak,
contamination, hidden error, failure issue (do we have any history with it previously)? … revitalize but hardening
(are there any existing similar proven grounded solutions that can be adapted), or is it too risky or else."*

**Answer: REVITALIZE THE PRINCIPLE WITH HARDENING — do NOT restore the score, and do NOT re-assert a per-row gate.**
The danger is not in the principle. The danger is in the two naive implementations of it that this repository has
already paid for: **a count wearing a ratio's name** (§3, R1) and **a gate applied to a corpus instead of a claim
attached to a row** (§2, R2). Revitalization is *low* risk if it is (i) **measured before it is advertised**,
(ii) **declared on the wire instead of enforced at admission**, and (iii) **never reused as a scalar oracle**.
Restoring the old form is *high* risk and is rejected — not for taste, but because the count is measurably
**coarser than the measure we already hold** (§4: 148 rows it certifies as two-source carry ONE author).

---

## §1 — THREE OBJECTS THAT KEEP BEING CONFLATED (the ontological fix this document is built on)

Almost every BORP argument in this repository's history is two people using one word for three different things.
They must be named separately, because they have different owners, different failure modes and different verdicts.

| # | object | what it is | state today (measured) | verdict |
|---|---|---|---|---|
| **1** | **BORP-THE-PRINCIPLE** | the *rule*: convergence requires ≥2 records that are **independent** — a statement about **evidence quality** | alive and load-bearing: expressed as `is_convergent`; satisfied by **938 of 4,503** served PASS rows (20.8%) | **KEEP — and serve its truth** |
| **2** | **BORP-THE-MEASURE** | the *function*: how independence is **computed** | was `min(distinct/2, 1.0)` → **constant** on the admitted set (degenerate); today it is `isor` (author independence × domain diversity × count), populated on **4,503/4,503** PASS rows | **KEEP the measure we have** (`isor`) — do not mint a second one (D-2646) |
| **3** | **BORP-THE-SURFACE** | the *value* an agent or export reads: `fbs.borp_score` | **dead**: constant `0.0` on 7,640/7,640 rows, home `null`, parity rail `null`, producer DELETED at S5 — **and still published by three surfaces** (BUG-767) | **RETIRE** (T-107) |

**The drop the owner asked about was correct for object 3 and over-broad for object 2.** Object 1 was never in
question — and it is the one that is under-served.

---

## §2 — THE RISK REGISTER (R1–R8): mechanism, history, blast radius, the control that removes it

Severity is the **blast radius if the naive form were restored or re-asserted today**, not the difficulty of the
work. "History" cites what this repository already measured; nothing here is hypothetical.

| # | risk | mechanism (why it bites) | history (measured, in-repo) | blast radius | control that removes it |
|---|---|---|---|---|---|
| **R1** | **Tautology** — the metric cannot vary | a ratio whose pass bar sits AT the denominator floor is a boolean wearing a ratio's name: `min(distinct/2, 1.0)` = 1.0 on every admitted row | git `c95f7ff:pipeline/stage5_verify.py:105-115`; the check was DELETED (S5, line 554) | the number is a **certificate of nothing**; every consumer that gates on it passes unconditionally | measure on the **independence** axis (`isor`), never on the count axis alone |
| **R2** | **Gate regression / yield loss** | a per-row ≥2-source gate is not a check, it is a **corpus edit**: it can only remove rows | Audit1 P1.4: *"BORP ≥2 sources drops single-source insights"*; today **3,565 of 4,503 served rows (79.2%)** are single-source | withholds ~79% of the served corpus from every answer — the exact recall loss T-101's ruler exists to measure | **never gate admission; DECLARE the tier on the answer** (T-118). The row stays; its provenance is stated |
| **R3** | **Correlated-source contamination — the real one** | counting DISTINCT TITLES is spoofable: one author's second book, a reprint, a translation, or a book that quotes another all count as "2 independent sources" → the **echo/slop pattern PASSES the check minted to stop it** | MEASURED 2026-10-13 (§4): of 938 count-certified rows, **148 carry ONE author** (15.8%), **170 ONE domain** (18.1%), **35 are rated weak by `isor`**; worked example: *Chroma Subsampling in Jpeg Compression* — 2 sources, **both Rosa Menkman**, `isor` = weak 0.5 | the system **certifies** the contamination it exists to prevent. Worst case: a false trust signal *amplifies* slop (an agent repeats it as corroborated) | define independence on a **derivation/voice axis** (shared ancestor collapses to one; §6/§8) — the same-author case is already caught by `isor`, the shared-origin case is what T-119 measures |
| **R4** | **False absence / wire leak** | one column read as a VALUE by SQL (`COALESCE(borp_score,0.5)` → 0.0) and as ABSENT by Python (`or 0.5` → 0.5) inside ONE function; absence and "score 0.0" are indistinguishable to a reader | MEASURED 2026-10-13 in `pipeline/retrieve.py` (`_quality_field`, the graph-aware SQL); D-2957; BUG-767 | agents and exports read **"no corroboration"** on rows that are `isor`-**strong**; ranking degrades to rowid order (F-40/BUG-710 class) | **absence is NULL and DECLARED** (D-2957); a **new field name** for any new signal; the served-fields rail refuses an advertisement with no declaration (D-2989) |
| **R5** | **Threshold re-litigation / drift** | reopening "BORP as a real score" reopens a settled-by-substitution question and invites a **second scoring system** beside `isor` | `config/decisions.yaml`: an unresolved **"BORP_MIN_SOURCES=2 vs BORP ≥ 3" discrepancy**; variant **D2053-C "Author-weighted BORP"** proposed and never landed | two homes for one derived value (D-2646); every consumer picks its own threshold; the register can no longer say what "corroborated" means | ONE measure (`isor`), ONE home (`pipeline/schema_accessor.py::isor_score`), and a **named rating** (`weak/medium/strong`) instead of a free scalar |
| **R6** | **Ranking coupling / hidden recalibration** | wiring a new trust signal into `ORDER BY` or the rerank factor silently changes every answer — a recalibration with no decision | the retired constant was ORDER BY-ed in **two** places (F-40/BUG-710; `pipeline/query.py` residual fixed by D-2979/D-2980) | unbounded, invisible recall/MRR movement; the golden ruler is already saturated (T-101) so it would not catch it | **measure → declare → then opt-in behind a flag**, with a before/after on the golden ruler; never a silent term |
| **R7** | **Agent-trust contamination** | publishing a scalar `0..1` "BORP score" to an agent is a **claim**; if it is a count dressed as a ratio, the agent's trust signal is runtime noise | D-2989: *an advertised field is a CLAIM* (the fifth claim surface); BUG-767 (three surfaces publishing `0.0`) | an agent **repeats** the fabricated measurement to a user; the error leaves the machine through OKF and Anytype | advertise a **graded, explainable tuple** (`{independence: weak|medium|strong, sources, convergent}` + components), never a scalar oracle |
| **R8** | **Reprocess/re-anchor rot** | anything keyed by a *count of book names* rots when the corpus is re-processed or re-chunked: `fb_id`s are content hashes and titles drift | BUG-710: **0/30** golden ids AND 0/30 names were re-anchorable after `rechunk-v4` | a metric that cannot survive a reprocess is a metric that measures the LAST reprocess | anchor on **stable keys** (`source_ids`, canonical works D2185) and on **owner-signed names**, never on a title string count |

**Net:** R1/R6/R8 are *engineering* (removed by measuring on the right axis and declaring before wiring). R2 is a
*policy* choice (T-118). **R3 is the only irreducible one** — and it is irreducible for the count, not for the
principle: it is exactly what a hardened measure is for. That asymmetry is the whole argument.

---

## §3 — THE HISTORY (so the risk is not hypothetical)

Five recorded encounters. Note that **four of the five failures are about the SURFACE or the GATE, not the rule.**

| when | what happened | what it teaches |
|---|---|---|
| v2 → S5 | `check_borp` computes `min(distinct / BORP_MIN_SOURCES, 1.0)` with the pass bar AT the minimum → **a constant 1.0 on every admitted row** | R1: a **score** whose gate equals its floor is a boolean. The rule was never the problem; the arithmetic was |
| Audit1 P1.4 | *"BORP ≥2 sources drops single-source insights"* — the yield cost of gating | R2: the principle applied as a **filter on the corpus** removes most of the corpus |
| D2053-C | "Author-weighted BORP" proposed (~30 LOC, Phase 1) — a **variant of the count** | R5: patching the count keeps the count's blindness; ISOR (D2284) superseded it by measuring independence directly |
| D2284/D2309 | **ISOR landed**: author independence × domain diversity × source count → `score` + `strong/medium/weak`, over canonical `source_ids` (D2185). Persisted, **advertised by nothing** | the revitalization the owner asked for **already exists**; the defect is SERVING, not logic |
| S5 + D2979/D2980 | `check_borp` DELETED (*"guarantee moved to S1.5"*) — but S1.5's ≥2-source gate covers the **CLUSTER route only**; the ranking repair repointed its last reader | R3/R4: the guarantee was **declared** for the whole corpus while enforced for one of two admission routes → singletons reach the store unguarded (BUG-768); the column was left as a public constant (BUG-767) |

---

## §4 — THE MEASUREMENT THAT SETTLES IT (the count is coarser than the measure we already hold)

Canonical run `rechunk-v4-20260929`, `status='PASS'` (N = 4,503). Read-only, 2026-10-13.

| measurement | value |
|---|---|
| `isor.rating` = weak / medium / strong | **3,576 / 670 / 257** (populated on 4,503/4,503) |
| rows the COUNT certifies as corroborated (`is_convergent=1`) | **938** (20.8% of served rows) |
| …of those, rated **weak** by `isor` | **35** |
| …of those, **2+ sources but ONE AUTHOR** | **148** (15.8%) |
| …of those, **2+ sources but ONE DOMAIN** | **170** (18.1%) |

**Worked example (a real row):** *Chroma Subsampling in Jpeg Compression* — `source_books` = two works, **both by
Rosa Menkman**; `source_authors` = 1 author; `isor` = `weak 0.5` ("1 authors, 1 domains, 2 sources"). The
count-based BORP says **corroborated**. The independence measure says **one voice**. Only one of them is right, and
we already own the one that is right.

**Reading.** The count is not merely *weak evidence*; on 15.8–18.1% of the rows it admits, it is **wrong in the
direction that matters** (it certifies single-voice repetition as independent corroboration). Therefore:
*"revitalize BORP"* **cannot** mean *"restore the count"*. Any revitalization that does not change the axis is a
downgrade from the measure we already hold.

---

## §5 — WHAT "HARDENING" MEANS HERE (three moves, two prohibitions)

**Move 1 — Revitalize the PRINCIPLE at the SURFACE, not at the gate.** The rule becomes a **statement the system
makes about each answer**, not a filter on what it keeps: every served row carries its corroboration tier, and the
answer text may not call a row *corroborated* unless its tier says so. This is `corroboration` (ISOR) promoted
(T-107) plus the **single-source tier word** (T-118) — the policy question "what may the system SAY about a row
BORP does not cover" is the owner's, not an agent's (D-2898).

**Move 2 — ONE measure, ONE home.** `pipeline/schema_accessor.py::isor_score` stays the measure; the wire publishes
a **graded tuple** (`independence: weak|medium|strong` + `sources`, `convergent`, and the score as a component) —
never a floating scalar oracle (R7). No second score is minted (R5, D-2646).

**Move 3 — HARDEN the independence AXIS with lineage (T-119, §8).** Independence must mean *"no shared ancestor"*,
not *"different title"*. The cheapest honest version uses what we already store (`source_ids`, `source_books`,
`source_authors`, `source_segments`, `origin`, `primary_source` for all 7,640 rows) and the embeddings S1.5 already
computed. **Measure the collapse delta BEFORE any surface claims corroboration as a guarantee.**

**Prohibition A — no per-row hard gate on the corpus.** A gate is a corpus edit (R2); it needs an owner policy and
it buys exclusion, not truth. Declare a tier instead.

**Prohibition B — no scalar "BORP score" on the wire.** A scalar invites R4 (absence/value confusion), R6 (silent
ranking coupling) and R7 (fabricated trust). A graded tuple with named components is auditable; a float is not.

---

## §6 — PROVEN, GROUNDED SOLUTIONS THAT CAN BE ADAPTED (do not invent)

Two are ours; three are external precedents. Each row states what it buys, and what it costs **here**.

| source | what it gives | cost here | verdict |
|---|---|---|---|
| **`isor` (D2284/D2309), already persisted** | independence computed from **author × domain × count**, with a named rating; populated on every PASS row | **zero** — it exists and is unadvertised | **ADOPT NOW** (T-107 word: `promote corroboration`) |
| **Stored provenance substrate**: `source_ids` (D2185 canonical works), `source_books`, `source_authors`, `source_segments` (S1 segment ids), `origin`, `primary_source` (with an *earliest-publication* reason) | the raw material for lineage: who wrote what, when, and which segments a claim came from | a mapping from `source_segments` (S1 ids) → text/vectors must be located (they are produced at S1/S1.5; the S1.5 index already embeds them) | **ADOPT** as the substrate of T-119 — **step 0 is locating it**, not building it |
| **External: source DEPENDENCE in truth discovery** (the literature that formalised "sources copy each other", so accuracy/dependence must be modelled instead of counting sources) | the established framing: **the independence assumption is false in practice** and is the dominant error in multi-source fusion; gives the scoring family (weight by dependence rather than count) | nothing to port wholesale — we adopt the **framing + the copy-collapse rule**, not an algorithm | **ADOPT the rule** (T-119) |
| **External: copy/near-duplicate detection** (shingling/MinHash, and embedding-similarity clustering used for "same story" grouping) | a deterministic, cheap way to collapse two works that are *one voice* into one; runs on artifacts we already have (bge-m3 embeddings of segments) | needs a similarity threshold — and a threshold needs a measured distribution, not a guess (**the T-101 lesson**: an uncalibrated number is not a gate) | **ADAPT, measure-first**: report the delta and the distribution; do **not** gate on the threshold |
| **External: W3C PROV-O** (`prov:wasDerivedFrom`, `prov:hadPrimarySource`) | the standard vocabulary for "this came from that", so ancestry is DECLARED instead of inferred from similarity; the honest upgrade path when a citation edge becomes available | a schema field + extraction work; more than the collapse proxy | **ADOPT the vocabulary now** (name the field `derived_from`/`primary_source`, already half-present), implement the edge later |
| **External: pooled qrels (TREC) — relevance is a SET** | the same defect class on the **evaluation** axis: a single-relevant-doc golden saturates exactly like a single-floor ratio. Confirms T-101's fix (a query's expected set must be complete) | none — it is the design the harness already supports (micro-recall over `expected_names`) | **ADOPT** (see the T-101 revision) |

**Note the pattern:** all three external precedents say the same thing in three fields — **independence and
relevance are SETS with ancestry, not COUNTS of names.** That is one design decision wearing three hats, and it is
the reason this is a hardening and not a rewrite.

---

## §7 — RECOMMENDATION (senior system + RAG engineer)

**REVITALIZE WITH HARDENING.** Risk verdict per option:

| option | risk | why |
|---|---|---|
| **(A) Restore `check_borp` / resurrect `borp_score` as a scalar** | **HIGH — rejected** | R1 (tautology), R2 (yield loss), R3 (certifies correlated sources), R4 (absence/value leak). It is *worse* than what we already hold |
| **(B) Leave it dead and say nothing** | **LOW risk, HIGH cost** | the principle stays unserved: 79.2% of served rows carry no tier statement, the surfaces keep publishing `0.0` (BUG-767 OPEN), and the corpus-level claim of "≥2 sources" stays false for one of two admission routes (BUG-768) |
| **(C) REVITALIZE WITH HARDENING — recommended** | **LOW/MEDIUM, bounded** | moves 1–3 (§5) are additive, declarative, reversible, and each has a rail: surface → `scripts/check_served_fields.py`; measure → `scripts/check_feedback_parity.py`-style parity + `isor`; axis → the T-119 measurement with a falsifier. Nothing is gated, nothing is silently wired, nothing is minted twice |

**Concretely, the disposition per object:** keep the principle (§1.1); keep the measure we have and **serve** it
(§1.2); **retire** the dead surface (§1.3, T-107 `retire borp_score` + `promote corroboration`).
**The one word that is still the owner's** is §T-118 (what the system may *say* about the 79.2%): `tier` |
`withhold` | `leave` — and it is the only place where a *policy* choice (not an engineering one) exists.

**What this does NOT do:** it does not touch the store, does not gate admission, does not change ranking, and does
not claim a new guarantee. It changes **what the system says about evidence it already holds**.

---

## §8 — THE HARDENING PLAN (T-119): the collapse-delta measurement

**Question:** *of the rows that claim ≥2 sources, how many collapse to ONE voice once shared ancestry/author is
applied — and how deep does the collapse go?*

**Step 0 (substrate check, before any code).** The independence axis needs the *segment → work* map and the segment
embeddings. MEASURED 2026-10-13: `source_segments` is populated on **7,640/7,640** rows (S1 `segment_id`s, written
by `pipeline/stage2_extract.py:2563`/`:2886`); the S1.5 embedding index and `data/checkpoints/bucket_clusters` hold
the segment side. **No new infrastructure is implied — but the map must be LOCATED first, and that is step 0.**
Done when: a row's `source_segments` can be resolved to (work, vector) for a sampled 200 rows.

**Step 1 (cheap, no similarity).** `author-collapse` and `domain-collapse` from stored fields:
`n_voices_author = |distinct source_authors|`, `n_voices_domain = |distinct domains|`. Already measured for the
convergent set: **148** one-author, **170** one-domain (§4). Deliverable: the delta table on the PASS population.

**Step 2 (the collapse proper).** For each convergent row, cluster its `source_segments` by embedding similarity
and count **clusters**, not segments/works. `n_voices = |clusters|`.
**Deliverable: the collapse delta** = `P(convergent)` vs `P(n_voices ≥ 2)`; plus the similarity **distribution**
(so any future threshold is measured, never guessed — T-101's lesson).

**Step 3 (the falsifier — the measurement must be able to say "no finding").** If `P(n_voices ≥ 2)` ≈
`P(convergent)` on a 200-row sample, the count is **not** contaminated at the segment level in this corpus and the
hardening is documentation only. If it collapses materially (first estimate from §4 suggests a floor: **≥15.8%**
one-author alone), then the surface may not claim "corroborated" for those rows without the tier.

**Step 4 (only then) the surface.** Promote `corroboration` with `n_voices` and the rating; add `derived_from` /
`primary_source` (PROV vocabulary) to the schema **only if** an ancestry edge becomes available.

**Cost:** read-only until step 4; one measurement script (`scripts/check_corroboration_collapse.py`, to be
spec-first like every other rail here) + the S1.5 index reuse. **No store write, no ranking change.**

**Residuals (declared, not hidden):** (i) the S1.5 gate covers the CLUSTER route only (BUG-768) — the tier
declaration is what makes the singleton route honest, and it is the owner's word (T-118); (ii) `borp_score` remains
advertised until the T-107 change-set lands (BUG-767, rail rc 2); (iii) the S1.5 threshold (`2`) is itself a
declared floor, not a measurement — T-119's step 2 distribution is what would replace it.

---

## §9 — FILES AND CONTINUITY

* The archaeology (what BORP was, why the score died, the measurements): `governance/BORP_FEEDBACK_ASSESSMENT_20261013.md`
* The disposition home (one owner word per advertised field): `config/served_fields.yaml` (feedback_score =
  `keep-and-declare`, granted 2026-10-13; `borp_score` pending → `retire + promote corroboration`)
* The rail: `scripts/check_served_fields.py` (rc 0 clean | 1 defect | 2 owner-owed) + `specs/served_fields.spec.md`
* The policy question that remains the owner's: T-118 (`tier` | `withhold` | `leave`)
* The hardening measurement: T-119 (this file §8)
* Bugs: BUG-767, BUG-768 (OPEN); the derived-measure rail: `scripts/check_feedback_parity.py`
