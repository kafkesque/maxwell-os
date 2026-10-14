# THE INGEST DOOR — the enforcement point the identity machinery never had

**D-2997 · BUG-781 · T-130 · 2026-10-14.** Answers two questions asked in one breath: *"how does the
convergence defect get fixed post hoc, and what stops the next batch?"* — plus the forensic audit run BEFORE
the write, because the first act of a gate is to prove it does not move what it does not own.

---

## 1. What the collapse does to convergence (the honest shape)

MEASURED 2026-10-14 (D-2996, `config/corroboration_collapse.yaml#lexical_limb`): of the 1,393 rows the count
certifies as corroborated, **530 (38.05%) are ONE TEXT under TWO NAMES** — 84 work-pairs, 37 of them identical
normalised text, forming 72 groups; 369 of the 530 are SERVED; 134 of the store's 257 advertised
`epistemic_status = corroborated` rows are among them; `isor` rates 205 strong or medium.

**Are there fewer convergent primitives? No — there is one FALSE CLAIM per affected row, and no row dies.**
S2 extracted each FB from real text; what is unsupported is the *corroboration*, i.e. the derived claim that a
second VOICE asserted it. Which is why every remedy below is a **relabel + re-derivation**, never a delete:

| checkpoint | effect of the collapse |
|---|---|
| S2 extract | none directly — the duplicate pair is one WORK read twice, not one primitive extracted twice; `dedup_fb_id` cannot see it (BUG-772 shape) |
| S4 merge / classify | none — classification reads the body, and the body is real text |
| S5 verify (NLI) | **must not catch it, and cannot**: entailment between premise and claim says nothing about whether two sources are independent (D2298) |
| S6 commit | carries the FALSE claim: `is_convergent`, `source_diversity` (and the retired-but-read `borp_score`) written by S1.5 |
| parity rail | **green and honest**: `is_convergent == |source_ids| >= 2` on 7,640/7,640 — the count is exactly re-derivable AND says nothing about distinct voices |
| knowledge base | 369 served rows carry an overstated tier; the *facts* are unaffected |

Expected end state of the repair: `is_convergent` **1,393 → 863**, advertised corroborated **257 → ≤ 123**,
rows deleted **0**, parity rail green over all 7,640.

---

## 2. Post-hoc repair plan (bounded, cascade-free, owner-gated)

| # | step | mover | rail / proof |
|---|---|---|---|
| P1 | owner words: the 84 collapse rows **and** the 59 ledger pairs — ONE act in two vocabularies (mapping declared in `config/ingest_identity_gate.yaml#ledger.collapse_words`) | **owner** | `check_ingest_identity_gate.py --check` reports the owed count per sheet |
| P2 | the collapse is written as a DECLARED identity map — no row is marked "deleted", no body changes | pipeline | map is config, not code; `apply_dedup_marks.py` semantics (mark + QUARANTINE, never delete) |
| P3 | re-derive `source_ids` → `source_diversity` → `is_convergent` for the AFFECTED rows at their declared home (`config/derivations.yaml` → `stage1_5_embed_cluster.py::build_clusters`), not by a second implementation | pipeline | `check_corroboration_bit` re-proves the whole population; `check_derivations` keeps the home singular |
| P4 | write the `duplicate_of` marker via its declared writer (today 7,640 NULL, 0 marked — the writer had never run) | pipeline | `normalize_duplicate_of_marker.py` contract: absent is NULL, never `''` |
| P5 | re-derive the T-118 tier from the corrected inputs (the advertised claim falls on exactly the rows whose independence it never had) | pipeline | `config/served_fields.yaml#tier_policy` + the advertised-claim rail (D-2989) |
| P6 | re-serve and re-measure | pipeline | `check_serving_gate`, `check_corroboration_collapse.py --voice` reproduces the 530 census, `verify_source_identity` |
| P7 | receipt: the before/after counts, the words that released them, the rail verdicts | pipeline | this file + the four gov faces |

**Refused, and why they stay refused**: raising `stage1_5.min_source_diversity` (risk R2 — suppresses real
corroboration with the fake) and minting any duplicate-adjusted SCALAR (a fourth home for one fact,
C12/C20/D-2646). The voice axis enters the tier only as a **declared input**, which is the owner's D-2996 §5 word.

---

## 3. Future-batch plan (the four layers, each with its rail)

| layer | what it is | rail | owner word? |
|---|---|---|---|
| **L0 — the door** (landed) | pre-S0: a candidate whose sanitized identity or bytes match the corpus is DEFERRED; delta-scoped, so nothing ingested can move | `stage0_convert.py::apply_ingest_door` (unbypassable) + `check_ingest_identity_gate.py` | no — machine-decidable |
| **L1 — the content screen** | post-S0 / pre-S1.5: the D-2737 detector's pairs must all be covered by the ledger, else rc 1 (stale ledger = blind door) | `check_ingest_identity_gate.py --gate` (rc 2 REFUSES) | yes — for the pairs it surfaces |
| **L2 — voices, not names** | S1.5 diversity counts VOICES through the declared identity map (the P2 map, same home) | `check_corroboration_bit` + `verify_source_identity` | yes — the map is the owner's ruling |
| **L3 — the debt cannot go quiet** | the ladder reads the door every run: `just health` line, tri-state, owner-owed is loud and not fatal | `config/rail_registry.yaml` guard pinned to `tri_state` | no |
| **L4 — the batch receipt** | every batch writes what it deferred and which owner words are outstanding, so "how much is left?" has a measured answer (the D-2983 discipline, one artifact over) | the deferral receipt under `temp/ingest_deferrals/` | no |

---

## 4. Forensic audit (run BEFORE the write — and what it found)

**Cascade (the one that matters).** A gate placed on the ingest path could re-classify files the corpus
already certifies, moving rows, counts and checkpoints. Measured: **0 candidates over the live 940-file
corpus** (all names are in the 962-record metadata cache), so the door is *inert* on what exists and can act
only on a future batch. This is why the door is delta-scoped rather than a corpus re-screen — the corpus
re-screen is T-129, owner-gated, with its own rails.

**Blindness (fail-closed, C16).** Absent/unreadable policy, metadata cache, ledger or content report is
FATAL, never "nothing to see". Deliberate exception, declared: at **pre-S0** a missing metadata cache
degrades LOUDLY (`identity_available: false` in the receipt) because S0.5 writes it and pre-S0 no claim is
minted; the same absence at `--gate` (post-S0.5) is fatal.

**Wrong-reading risk (an rc that means two things).** rc 2 is owner-owed and not fatal in `just health`;
the same rc REFUSES at the ingest step. That is a *declared* difference (`door.ingest_reading: rc2_refuses`)
and the registry pins the health line to `tri_state`, so the two readings cannot drift into each other
silently.

**Two real defects, caught by the door's own controls (8/8) and not by reading the code.** (1) The
filename-fallback branch of `compute_source_id` returns a BARE digest — there is no `unknown|` prefix — so a
door that trusted the id's *shape* admitted a new file as its own duplicate; identity honesty is now decided
by the source (a cache record with author AND title). (2) The detector report carries **no** `pair_id` while
the ledger does, so a coverage check across two id *namespaces* reported all 29 content candidates as an
uncovered (stale) ledger — a false FATAL; coverage now joins on the unordered `{a_id, b_id}` pair key.

**Blast radius of the write.** The door writes ONE artifact: its deferral receipt under `temp/` (gitignored
runtime state). It never touches the store, the corpus, the checkpoints or the ledger. The ladder line adds
~1.5 s, runs no model, and reads no store.

**Not covered, declared (a blindspot named is not a blindspot).** Content-level same-work under *unrelated*
titles pre-S0 (no text exists yet — that is L1, after conversion); paraphrase/translation/heavy editing (the
D-2996 §7 lexical scope, still a lower bound); non-book sources (T-121's vocabulary, still owed).

**Interplay checked.** The corpus root and the checkpoint root come from `pipeline_paths` (one home); the
noise markers and the sanitizer from `book_metadata` (D2449, one home); the ledger vocabulary from
`config/eval_integrity.yaml#duplicate_gate` (one home). No value is restated anywhere, so no new drift surface.

---

## 5. What is owed (the release)

1. **Owner** — one word per row on `governance/work_identity_collapse_review_20261014.csv` (84 rows) and one
   per pair on the D-2738 ledger (59 pairs). The 37 identical-text pairs are deterministic and need
   confirmation only; the 47 containment-only pairs are the ones that need a ruling.
2. **Owner** — the D-2996 §5 word: does the tier take the voice axis as a second DECLARED input, or is its
   scope stated as metadata-only?
3. **Pipeline** — the door (this landing) is complete; L1–L4 follow the owner's words, never precede them,
   because they change what the corpus *claims*.
4. Until (1) lands, `just triad` REFUSES at `--gate` by design, and `just health` reports the debt loudly.
