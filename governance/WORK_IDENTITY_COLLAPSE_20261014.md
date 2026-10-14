# WORK IDENTITY COLLAPSE — T-119's semantic limb is MEASURED, and the count was never the problem

**Date:** 2026-10-14 · **Rail:** `scripts/check_corroboration_collapse.py` (`--voice`) · **Rule:** `config/corroboration_collapse.yaml`
**Store writes: ZERO** (every number below is a read) · **Cost: $0** (local CPU, no model, no GPU)
**Authority for the numbers:** this file + `config/corroboration_collapse.yaml#lexical_limb` (ONE home, BUG-588/D-2692)

---

## §0. The answer in one paragraph

Of the **1,393 rows the count certifies as corroborated** (`is_convergent = 1`), **530 (38.05%)** are corroborated by
**the same text under two different names**. The set is **bounded and small**: **84 work-pairs**, forming **72
duplicate-work groups** (largest 3 members), of which **37 pairs are not "similar" but IDENTICAL** after
normalisation. **369 of the 530 collapsed rows are SERVED** (`status='PASS'`), and **134 of the 257 rows the store
advertises as `epistemic_status='corroborated'`** are in that set — advertising cross-source corroboration that is
one voice. The independence measure does **not** screen them: **205 of the 530** are rated **`isor` strong or
medium**, including **71 served rows rated STRONG** whose two "sources" are byte-identical text. This is not a
scoring defect and it is not a threshold defect. It is an **identity defect**, one level below the D-2309 fix that
removed filenames from the identity model.

## §1. What was believed, and the blindspot that hid it

T-120's step-0 measurement (D-2992/D-2993, `governance/T120_S1_RECON_20261014.md`) established something true and
narrow: `is_convergent` ⟺ `source_diversity >= 2` ⟺ `|source_ids| >= 2` on **7,640/7,640** rows. The falsifier it
attached to its own ruling fired, and the conclusion drawn was that the corroboration count is *"a PURE PROJECTION of
the source set: exact, and information-free beyond it"*, so the expensive half of the mechanism — re-cluster the
segments, confirm a second voice — *"would re-derive a number the row already states"*.

**Both halves of that sentence are true and the conclusion still does not follow.** The count is exact about **how
many sources are named**; it is silent about **whether those sources are different statements of it**. The
measurement never asked the second question, because the T-119 rail's semantic limb probed for **persisted
embeddings** (`**/*.index`, `**/*.npy`, `**/embeddings_cache/*`) found none, and reported **BLOCKED**.

**That probe was a blindspot, and it was mine.** The limb needs the segment **TEXT**, not the embedding vectors. The
S1 chunk store persists it — `knowledge pipeline/stage1_chunk/<run>/checkpoint.jsonl`, **730 MB**, canonical run
`rechunk-v4-20260929`, keys `segment_id / text / source_book / source_path`. All 148,831 segment ids referenced by
the population matched. The limb was **never blocked**; it was looking in the wrong place. (`blocked` was still the
right *state* to report — absent is not zero, D-2957 — the error was the artifact set, not the honesty.)

## §2. Method (declared, read-only, reproducible at $0)

One streaming pass over the 730 MB S1 store, keeping only the segments the population references:

| Parameter | Declared value | Home |
|---|---|---|
| population | `fbs WHERE is_convergent = 1` (1,393 rows) | `config/corroboration_collapse.yaml#population` |
| normalisation | lower-case, alphanumeric, single-spaced | `#lexical_limb.normalize` |
| sketch | bottom-48 MinHash over 5-word shingles, merged per (row, work) | `#lexical_limb.shingle_words/sketch_width` |
| boilerplate screen | both sides ≥ 120 words | `#lexical_limb.min_words_per_side` |
| collapse bar | containment ≥ 0.80 | `#lexical_limb.collapse_at_or_above` |
| certain class | **identical** normalised text under two names | `#lexical_limb.certain_class` |

Two classes are counted separately, because they carry different evidential weight: **containment** (one text
largely inside another — edition, re-export, re-upload) and **identity** (the two texts are the same string once
punctuation and case are removed — not a similarity judgement at all).

## §3. Results

| Measure | Value |
|---|---|
| rows tested (≥2 distinct `source_book` among their own segments) | **1,393** |
| collapsing work-pairs at ≥ 0.80 | **84** |
| — of which IDENTICAL normalised text | **37** |
| duplicate-work groups (connected components) | **72** (largest 3) |
| rows collapsed | **530** (38.05%) |
| — SERVED (`status='PASS'`) | **369** of 938 served |
| — advertised `epistemic_status='corroborated'` | **134** of 257 |
| threshold sensitivity | ≥0.90: 351 · ≥0.95: 284 · ≥0.99: 217 rows |

**The finding is not a threshold artifact** — it degrades smoothly and the IDENTICAL class (37 pairs, 184 rows)
needs no threshold at all.

**Worked pairs from the sheet (auditable in the store):**

| rows | work A | work B |
|---|---|---|
| 50 | `Hustle Harder, Hustle Smarter (Curtis 50 Cent…)` | `Hustle Harder, Hustle Smarter.md` |
| 42 | `Information Architecture For the Web and Beyond…` | `Information Architecture For the Web and Bey…` |
| 41 | `Designing for Growth A Design Thinking Toolkit…` | `Designing for growth a Design Thinking Toolk…` |
| 40 | `SYSTEMANTICS. THE SYSTEMS BIBLE_John Gall [G…` | `The Systems Bible_ The Beginner's Guide to …` |
| 37 | `Metaphorically Selling How to Use the Magic…` | `The Tall Lady With the Iceberg The Power of Me…` |
| 33 | `The Essential Guide to Doing Your Research P…` | `[O'Leary]-The-Essential-Guide-to-Doing-Your-…` |

The dominant shape is one book ingested twice — once under its **title** and once under its **filename**. The
`Metaphorically Selling` ↔ `The Tall Lady With the Iceberg` pair is the different and more interesting case: two
titles, one body of text (the same author's material under two covers) — a duplicate that no name-based instrument
can ever see.

**The independence axis is BLIND to it** (`isor`, D2284/D2309 — author independence × domain diversity × count):

| status | advertised | isor | rows |
|---|---|---|---|
| PASS | source-supported | medium | 220 |
| PASS | corroborated | **strong** | **134** |
| QUARANTINE | cross-source-unverified | medium | 88 |
| QUARANTINE | cross-source-unverified | **strong** | **71** |
| PASS | source-supported | weak | 15 |
| QUARANTINE | speculative | weak | 2 |

This is structural, not incidental: `isor` reads **metadata** (authors, domains, counts). When a book is ingested
twice under two names, the metadata differ — so the measure that exists precisely to detect non-independence rates
the duplicate **strong**. A content-level fact cannot be screened by a metadata-level measure.

## §4. Why the existing fixes do not cover it (and why nothing "regressed")

- **D-2309** ("canonical works, never filenames") fixed identity against *filenames* — it stopped 29.1% of convergence
  being "the same book counted twice" **when the names resolved to the same work**. Here the two names are genuinely
  different strings that resolve to **different** canonical works. D-2309 was necessary and is not sufficient.
- **`dedup_identity`** groups by `(normalize_name, source_id)` — the SAME WORK (D-2950) — so a second ingest of one
  book under another name is invisible to it **by construction**, exactly as BUG-772 describes. `duplicate_of` still
  has **0 writers**.
- **`check_corroboration_bit`** is green and stays green: `is_convergent == |source_ids| >= 2` **on 7,640/7,640 rows**.
  Nothing in this finding contradicts it. Two facts coexist: the count is exactly re-derivable **and** it carries no
  information about whether the named sources are distinct voices.
- **No serving regression**: the same works are already in the store; what is wrong is the **claim** attached to
  rows that cite both of them.

## §5. Consequence for the surfaces that just landed

`config/served_fields.yaml#tier_policy` (T-118, granted 2026-10-14) publishes
`{sources, convergent, independence, independence_score, home}`. On the 134 collapsed rows advertising
`corroborated`, that payload says **"convergent: true, independence: strong"** about **one voice**. D-2989's rule —
*an advertised field is a CLAIM* — applies one level down: **`independence` computed from metadata is not a
sufficient input to a corroboration claim.** Until the identity collapse lands, the tier is a true statement about
the count and a false statement about the evidence, and it is the false one an agent will read.

**The tier WRITE is owner-gated (D-2898) and is not touched here.** This document measures; it does not relabel.

## §6. Remedy — recommended, bounded, and NOT a scoring change

1. **Collapse the duplicate works at the identity layer (the recommended act).** 84 pairs / 72 groups is a
   *reviewable* set, not a corpus-wide repair. The 37 IDENTICAL pairs are **deterministic** (same text ⇒ same work);
   the 47 containment-only pairs need an owner word each (`CONFIRM-ONE-WORK` / `DISTINCT` / `LEAVE`).
   Sheet: `governance/work_identity_collapse_review_20261014.csv`.
2. **Then re-derive** `source_ids` / `source_diversity` / `is_convergent` for the affected rows — the parity rail
   (`scripts/check_corroboration_bit.py`) re-proves the whole population against its own evidence, so the repair is
   *checked*, not asserted. Collapsed rows lose `is_convergent` unless a genuinely distinct work also cites them.
3. **Do NOT touch `stage1_5.min_source_diversity`.** Raising a count threshold to compensate for an identity defect
   is risk **R2** of `governance/BORP_REVITALIZATION_RISK_20261013.md` (gate regression / yield loss) and would
   suppress real corroboration along with the fake.
4. **Do NOT mint a scalar.** A "duplicate-adjusted score" would be a fourth home for one fact (C12/C20, D-2646); the
   repair REMOVES a false claim instead of adding a compensating number.
5. **Feed the voice axis into the tier as a DECLARED input** (owner word), or state the tier's scope honestly: the
   `independence` field is a metadata rating and does not certify distinct voices. Recommended: the former, because
   the check is $0 and deterministic.

## §7. Falsifier, scope, and the residual that stays declared

- **The falsifier, run before the remedy:** if the collapsed share were ~0, the count would be uncontaminated in this
  corpus and this whole line would be documentation. It is **38.05%** at the declared bar and **184 rows** in the
  threshold-free IDENTICAL class. The rail can still say **NO FINDING** (rc=2) and is required to be able to.
- **Scope — this is a LOWER BOUND.** A LEXICAL screen can *certify* a collapse; it can never certify independence.
  Paraphrase, translation, and heavy editing are invisible to it. The embedding+NLI limb (`semantic_limb`) stays
  **declared as the residual** for exactly that class; it is no longer a blocker for this one.
- **Not asked, not answered:** whether a collapsed row's *claim* is still true. It may be perfectly true — it simply
  is not corroborated by two voices, and the store must not say that it is.

## §8. Owner decisions owed (do not assume)

| # | Decision | Why only the owner | Where the word goes |
|---|---|---|---|
| 1 | **One word per containment-only pair** (47 pairs): `CONFIRM-ONE-WORK` / `DISTINCT` / `LEAVE` | work identity is an ontology ruling; no agent mints a label (D-2898) | `governance/work_identity_collapse_review_20261014.csv#owner_ruling` |
| 2 | **The 37 IDENTICAL pairs**: confirm the deterministic collapse (or rule that identical text may stay two works) | the repair changes served identity | same sheet (pre-filled `identical_text=yes`) |
| 3 | **The tier contract**: add the voice axis to `independence`, or declare the field's scope as metadata-only | what the system may SAY about its evidence is a policy ruling (D-2989/T-118) | `config/served_fields.yaml#tier_policy` |
| 4 | *(carried over, unchanged)* persist the S1.5 index vs accept a re-embed pass | it is now **optional**, not blocking: the lexical limb answered the question at $0 | T-119 gate |

## §9. Artifacts

- `scripts/check_corroboration_collapse.py` — the rail; `--voice` re-measures this limb (read-only, streams the S1
  store, all parameters read from the rule file; never hardcoded, C12).
- `config/corroboration_collapse.yaml#lexical_limb` — the declared parameters, the measured counts (this file's one
  home) and the honest scope.
- `governance/work_identity_collapse_review_20261014.csv` — the owner sheet (84 pairs / 72 groups / rows affected /
  served rows / advertised-corroborated rows / blank ruling).
- `governance/buglog.md#BUG-780` — the defect, with severity and evidence.
- T-119 (gate narrowed to the residual class) · T-120 (parity rail landed; body-revision half remains) · T-129 (the
  identity repair, owner-moved).
