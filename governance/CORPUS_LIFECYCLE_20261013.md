# THE CORPUS LIFECYCLE — post-hoc corroboration, body revision, medium intake, and the 5-axis drift guardrails

**Asked by the owner 2026-10-13**, before committing to the BORP recommendation (retire `borp_score` + promote
`corroboration`; `keep-and-repair`). This file answers SEVEN questions with the mechanics that are in the tree
today — file and symbol named for every claim — and gives one recommendation per question, with the option
rejected and WHY. **READ-ONLY**: nothing in the store, no payload, no export surface and no axis label was
touched to produce this. Every external claim was verified before it was cited (D-2660); the two corrections the
verification returned are KEPT below rather than smoothed over.

**Answer in one line per question**

| # | the question | the recommendation | the option REJECTED |
|---|---|---|---|
| 1 | a singleton row that LATER gains a second source — does BORP/isor re-score it? | make corroboration a **derived, re-computable measure** (`config/derivations.yaml`), never a run-frozen boolean (T-120, BUG-772) | relying on a full re-run — it silently collapses the moment intake becomes incremental |
| 2 | a RICHER text source — is definition/mechanism/consequence/boundary/elaboration/application/failure_mode OVERWRITTEN? | **update the HEAD, never the RECORD**: append-only revision trail + `content_basis` writer; the axes move ONLY through their own instrument | (a) "never update" — it is not even the status quo (see §3), and (b) "update everything, in place, silently" — it violates C6 |
| 3 | the same question for all NON-principles | same engine (identity/revision/corroboration are WORK-layer), role-specific GATES: the role ladder stays OPEN (already instrumented: `reroute` + body-evidence + adjudication map), the vocabulary stays CLOSED | one rule per role — the drift would be the rules, not the objects |
| 4 | intake from the internet (journals, transcripts, video, threads, podcasts) — effect on `confidence_score`, BORP, provenance | **sequence it**: `confidence_score` is unaffected BY DESIGN; the COUNT can only inflate (the R3 failure at corpus scale); identity is the blocker (T-121, BUG-774) | ingesting first and repairing identity later — it re-opens BUG-289 (source_diversity by filename) |
| 5 | content-type drift risk + 5-axis drift guardrails | **closed menu, open assignment; never silent** — five named failure modes, each with a control that already exists | "freeze all axes" — it would block the system's own learning (`growth_edge` → `process_template` → `principle`) |
| 6 | what the owner must word (the batch) | T-101 `set` · T-107 `retire` + `promote corroboration` / `keep-and-repair` · T-118 `tier` · T-117 **per cause-group, never one blanket word** | a blanket word for T-117 — a CONFIRM nobody can evidence (D-2898) |
| 7 | what this does to the roadmap order | T-119 is not only a measurement — it is the **prototype of the engine** that makes T-120 and T-121 safe | proceeding with the intake programme now |

---

## §1 THE ONTOLOGY — a row has THREE times, and today only one of them is modelled

Identity, revision and corroboration move INDEPENDENTLY. That independence is the whole finding; every question
below is one of its consequences.

| time | what is fixed at that moment | the home in the tree | measured state |
|---|---|---|---|
| **t_extract** — a body is a READING | one model, one commit, one text → `definition, mechanism, consequence, boundary, elaboration, application, failure_mode, jargon, evidence_passages` | `pipeline/schemas.py`; stamps `gen_model`, `pipeline_commit`, `schema_version` (R14) | the reading is stamp-able but its BASIS is not: `content_basis` is a **RESERVED NAME WITH NO WRITER** (`config/dedup_identity.yaml` → `freshness_pointer`) |
| **t_identify** — a row is a WORK | `fb_id = SHA-256(name + definition)` (`pipeline/schemas.py:175`) — **definition-sensitive**, stated as the D-2949 root cause in `pipeline/dedup_identity.py`; the WORK identity under it is `source_id = SHA-256(normalize_author｜normalize_title)` (`pipeline/book_metadata.py::compute_source_id`), editions collapse by design (D-2308/D-2952) | the commit is `INSERT OR REPLACE INTO fbs` on a `fb_id TEXT PRIMARY KEY` (`pipeline/stage6_commit.py:764`, 77 columns) | a definition that moves by one character = a different `fb_id` = a SECOND row |
| **t_corroborate** — a claim is AGREED | `is_convergent` = "≥2 distinct canonical sources **in one cluster of one run**" (`pipeline/stage1_5_embed_cluster.py` header, D2176); `isor` persisted per row (D2284/D2309) | derived from the RUN's segment set (stage 1.3 checkpoint) | `isor` is populated on 6,591 rows and advertised by nothing; `is_convergent` is advertised as `borp_score` — a constant, its producer deleted (D-2990) |

**The rule that follows, in one sentence:** *the store's HEAD may change; the RECORD never does* (C6: never delete
pipeline output). Everything below is that sentence applied.

---

## §2 Q1 — the singleton that LATER gains a source: what happens, mechanically

The owner's question is the one that decides whether this corpus is a museum or a living organism. Today the
answer is neither, and the reason is precise:

**(i) Same definition text → same `fb_id` → the row is REPLACED.** `INSERT OR REPLACE` rewrites all 77 columns
from the S5 checkpoint. The previous reading and its evidence set are gone, with no revision and no basis pointer.

**(ii) Definition differs by one character → a different `fb_id` → a SECOND row is committed.** Both survive (a
commit never deletes, C6) and nothing reconciles them: two rows, one claim, divergent bodies.

**The instrument built for exactly this (D-2949/D-2950) cannot see the BORP case.** `pipeline/dedup_identity.py`
declares the GROUPING key as `(normalize_name(name), source_id)` — **the same WORK** — with a body-divergence
merge gate; `pipeline/dedup_gate.py` runs `mode: report` and its `would` vocabulary is
`link_duplicate | supersede_review | insert` (line 211). So it sees "the same work read twice" (editions, re-runs).
It cannot see "a DIFFERENT work asserting the same claim", because the grouping key differs by construction — and
that second case **is** the Book of Record Principle.

**The only path that works today is a FULL RE-RUN**: both works must be in the same run's segment set for S1.5 to
cluster their segments and for the claim to be re-extracted as convergent. Corroboration is therefore a property
of the RUN's clustering, not of the row's evidence. Consequences:

- **A row's tier can never rise.** A claim extracted from one work stays single-source in the store for ever, no
  matter how many later works assert it.
- **The moment intake becomes incremental — which the internet-intake plan makes unavoidable — corroboration
  SILENTLY COLLAPSES.** A new work alone in a delta run clusters with nothing, corroborates nothing, and the
  absence looks exactly like "no convergence" rather than like "the run could not see". That is BUG-772.

**THE FIX (recommended).** Make corroboration a **DERIVED, RE-COMPUTABLE MEASURE over the row's own evidence
set**, not a boolean frozen by one run's clustering:

```
independence(row) = f( row.source_segments → n_voices , row.source_ids → works × authors × domains )
n_voices          = |clusters of the row's source_segments by embedding similarity|, NLI-confirmed
```

- **Home**: `config/derivations.yaml` — ONE DERIVED VALUE, ONE HOME (D-2646); the register already holds
  `fbs.status`, `fbs.confidence_score`, `fbs.epistemic_status` with a parity rail each. `is_convergent` is the
  only high-stakes value that is an INPUT (a frozen cluster property) instead of an OUTPUT.
- **Funnel**: embedding similarity → NLI confirm (both models are already in the pipeline; the measure is not the
  generator, R5).
- **Cost**: computed only for rows whose tier would MOVE — never a full re-run, never a corpus-wide pass.
- **This is T-119's plan promoted** from "measure the collapse" to "re-derive the tier": one mechanism serves
  post-hoc corroboration, delta ingestion, and the collapse measurement.
- **FALSIFIER (kept)**: if `P(n_voices ≥ 2 | is_convergent = 1) ≈ 1`, the count is NOT contaminated in this
  corpus and the hardening is documentation only. A measurement that cannot say "no finding" is not a measurement.

---

## §3 Q2 — a richer text source: overwrite or not?

The owner offers (a) never update, sacrificing pragmatism, or (b) update everything post-hoc. **Neither (a) nor
(b) is the status quo, so (a) does not even buy what it claims.**

**(a) "NEVER update" — REJECTED.** It reads as stability and is in fact a FALSE stability: the current write path
already REPLACES the row silently whenever the definition is unchanged, and already FORKS a twin row whenever it
moves. Choosing (a) changes nothing about the code; it only declines to make the behaviour visible. It also
survives on a condition the corpus cannot accept: a knowledge base that cannot absorb a correction cannot absorb
a retraction either.

**(b) "UPDATE, post-hoc, in place" — REJECTED as written, ACCEPTED with two controls.** The recommendation is (b)
*done properly*: the HEAD may change; the RECORD never does.

**CONTROL 1 — the revision trail (and it is not optional: C6 already forbids the alternative).** A body is a
READING. Keep the superseded reading in an append-only sidecar (`fb_revisions`: `fb_id`, `revision_n`, the body
fields, `source_ids`, `gen_model`, `pipeline_commit`, `run_id`, `effective_from`/`effective_to`, `basis` = the
sanitised file name the body was read from) and mark the current head. This is two standard, named patterns —
verified 2026-10-13:

- **Slowly Changing Dimension Type 2** (Kimball): a new record per change with begin/end-effective datetimes
  (verified wording: "Type 2 requires that we generalize the primary key of the Employee dimension…"; the
  end-effective datetime of a record "must be exactly equal to the begin-effective-datetime of the next change").
- **Event sourcing** (Fowler, 2005): "Capture all changes to an application state as a sequence of events" — the
  log reconstructs past states and is kept "for the same lifetime as the application state itself".
- **The ontology layer** is PROV-O (W3C Rec 30 April 2013, ns `http://www.w3.org/ns/prov#`): `prov:wasRevisionOf`
  is a **subproperty of `prov:wasDerivedFrom`**, alongside `prov:wasQuotedFrom` and `prov:hadPrimarySource`;
  `prov:wasGeneratedBy` and `prov:invalidatedAtTime` are separately-defined properties. **CORRECTED in this act**:
  my first draft implied all five terms are subproperties of `wasDerivedFrom` — PROV-O states exactly three are.

**CONTROL 2 — an axis is a JUDGMENT; a body is EVIDENCE. A body revision may PROPOSE an axis change and may never
APPLY one.** The axes (`content_type`, `extraction_type`/FORM, `depth`, `discipline`, `domains`) move only through
their declared instruments: the body-evidence gates of D-2953/D-2955 for a ROLE move, the owner adjudication map,
the append-only raw→canonical calibrated path (D2066), the provenance-stamped `*_source` columns. The reason is
MEASURED, not philosophical: D-2953 found the "obvious" reroute was 88% router false positives; D-2955 found that
**a name is a PRIOR, never evidence**.

**AND the tree already declares Control 1 — on the wrong path.** `config/dedup_identity.yaml`
(`edition_supersession.execution`) says `never_at_commit: true  # D-2933 rule V: a commit may never rewrite an
existing row's body`, and `never_delete: true` with the superseded filename APPENDED to `source_ids`. The live
commit path does the opposite for any `fb_id` collision. That contradiction is BUG-773: the declared rule and the
write path disagree, and `content_basis` (the pointer that would make either case visible) has no writer.

**What the answer means for "richer text":** a richer source is a NEW READING, not a correction of the old one.
It becomes the head, stamped and dated; the prior reading is retained and addressable; the citation
(`primary_source` = ORIGIN, the earliest source held) is UNCHANGED by D-2952; `content_basis` says which text the
current body came from.

---

## §4 Q3 — the same questions for NON-principles

**Identity, revision and corroboration are WORK-layer properties → they are role-independent.** The evidence is
the commit tier itself: the D-2590 non-principle tier commits into the SAME store, with the same `fb_id` model
and the same skip-if-already-stored behaviour (`commit_status=ALREADY_STORED`) — so ONE engine, five roles.

**What IS role-specific, and must stay so:**

| role | body schema (`config/content_types.yaml` → `s2_body_fields`) | axis note |
|---|---|---|
| `principle` | core body + `application`, `failure_mode`, `elaboration` (empty → quarantine, D2371/D2488) | all five axes apply |
| `process_template` | `trigger, prerequisite, steps, done_condition, failure_mode` | all five |
| `process_instance` | `instance_text, actors, outcome_metric, outcome_qualitative, domain_context` | all five |
| `tool_instruction` | `tool_name, platform, description, syntax, parameters, output, example, caveats` | all five |
| `growth_edge` | `body, category, actionable, status, priority` | **keyed by body+status, NEVER discipline/domain** (D-2923/D-2924) |

**Consequence the owner should hold onto:** a `growth_edge` → `principle` promotion is NOT a relabel. GE
deliberately carries no discipline and no domains, so a promotion must POPULATE axes the object never had — and
each of those labels owes that axis's own instrument (definition-anchored classification, provenance stamp,
owner gate where the label is a judgment). That is the honest cost of an open ladder, and it is the reason the
ladder may be open while the vocabulary stays closed.

**The ladder is ALREADY open and ALREADY instrumented** — this is not a new design, it is the existing one:
`config/content_types.yaml` → `content_type_rules`, `content_type_decision_procedure`, `reroute`
(`ti_to_pt_require_body_evidence: true`, `open_tension_strict: true`), `adjudication_map` (the owner's own
rulings), and `dropped_content_types` (`fact`, `meta`) as the **cemetery for exactly the mistake of minting a
value**. Rule of the ladder: a move UP requires BODY evidence (ordered steps AND a done-condition/gate), never a
name prior; a new VALUE may not be minted ad hoc.

---

## §5 Q4 — intake from the internet: `confidence_score`, BORP, provenance

Three separate effects. Only one of them is modelled today, and it is not the one that breaks.

**(i) `confidence_score` — UNAFFECTED, and that is CORRECT.** It is the S5 NLI entailment score, a derived value
with ONE home (`pipeline/serving_gate.py::derive_conf_and_review`, parity rail `scripts/check_s5_score_axis.py`).
It answers "do this row's own evidence passages entail this claim", not "is this source trustworthy". A podcast
does not lower it; a retracted paper does not raise it. **Do not overload it** — source trust is the independence
axis, not the verification axis.

**(ii) BORP / `isor` — the COUNT can only INFLATE, and that is the R3 failure at corpus scale.** The count is
`≥2 distinct canonical source_ids` (D2176). A podcast in which the author reads his own book, a preprint and its
version of record, a journal article and its blog post, a thread quoting the book: **each becomes a second source
id and certifies corroboration between a voice and itself.** The collapse rule already exists and must be
GENERALISED — editions collapse to ONE `source_id` by design (D-2308/D-2952); a work and its re-publication in
another medium must collapse the same way. The external vocabulary for this is standard and verified 2026-10-13:

- **NISO RP-8-2008, Journal Article Versions (JAV)** defines **seven** versions — Author's Original (AO), Submitted
  Manuscript Under Review (SMUR), Accepted Manuscript (AM), Proof (P), Version of Record (VoR), Corrected Version
  of Record (CVoR), Enhanced Version of Record (EVoR). **CORRECTED in this act**: my first draft said four/five.
- **Crossref relation types** include `isVersionOf`, `isPreprintOf`, `isTranslationOf`, `isCommentOn`.
  **CORRECTED in this act**: `isRetractedBy` is NOT a Crossref relation type — retraction is carried by Crossmark
  **update** metadata, not by a relation code.
- **OpenAlex** classifies a work with one `type` from a controlled vocabulary (25 values: `article`, `preprint`,
  `book`, `book-chapter`, `dataset`, `dissertation`, `review`, `report`, `paratext`, `editorial`,
  `letter`, `erratum`, `peer-review`, …): a closed enumeration, externally governed. This is the vocabulary a
  source-kind axis should read rather than invent.

**(iii) PROVENANCE — this is where the plan BREAKS TODAY.** Identity is book-shaped:
`source_id = SHA-256(normalize_author｜normalize_title)` with a **FILENAME FALLBACK branch**
(`pipeline/book_metadata.py::compute_source_id`), and the evaluator's rail asserts that the fallback is never live
— `config/eval_integrity.yaml` → `source_identity.max_both_unknown_ratio: 0.0`, enforced fail-closed by
`scripts/verify_source_identity.py`, whose docstring records the ORIGINAL defect: `source_diversity` counted
FILENAMES, so "29.1% of convergence (757/2597 rows) was the same book twice". `pipeline/stage0_convert.py`
accepts only `{.epub, .pdf, .md}`. A transcript, a podcast episode, a social thread or a journal article has no
author｜title in any of those shapes → it lands on the fallback branch → **the closed defect class reopens**.

**VERDICT — (c) SEQUENCE IT.** Intake of new media is not an ingestion task; it is an IDENTITY + INDEPENDENCE
task. Prerequisites, in order:

1. **a source-kind axis + a per-kind identity resolver.** The precedent is already in-repo: `config/references.yaml`
   resolves bibliographic metadata from OpenAlex **by DOI** "rather than letting anyone type it (so a wrong year,
   venue or DOI cannot survive a rebuild)". That pattern, generalised per kind (paper→DOI, book→ISBN/author+title,
   podcast/video→channel+episode+URL, thread→URL+retrieved_at), is the fix.
2. **the independence rule**: same work across media = ONE voice (the D-2308 collapse rule, generalised).
3. **`content_basis` + `retrieved_at` + licence** written at extraction — a fact nobody records cannot be
   audited later (D-2952's own build order).
4. **only then** conversion (Whisper-class ASR for audio/video; the `.md` path already exists).

**And an owed complement:** a corpus that ingests the literature owes an UPDATE/RETRACTION path — Crossref's
Crossmark carries typed updates ("corrections, retractions, or updates to that record") and COPE defines
retraction as "a mechanism for correcting the literature" rather than as punishment. This is the strongest
argument against option (a) in §3.

---

## §6 Q5 — content-type drift and the guardrails for all five axes

**Two drifts that must never be conflated:** ROLE drift (what the object IS: `growth_edge` → `process_template` →
`principle`) and VOCABULARY drift (a value entering or leaving the answer space). The first is legitimate and
wanted; the second is a versioned, pin-moving event.

**Five failure modes, each with a control that already exists:**

| # | the drift | the control in the tree |
|---|---|---|
| 1 | alias creep — a raw label becomes canonical by use | append-only raw→canonical calibrated path + `emerging` as the DECLARED absence (D2066/D-2830) |
| 2 | a relabel by SIDE EFFECT (a body revision, a re-extraction, a better model) | axes move only through their instrument (D-2953/D-2955); `content_type_source` / `discipline_source` / `extraction_type_source` name the writer |
| 3 | a role minted ad hoc | the closed enum + `dropped_content_types` cemetery + the answer-space PIN (`config/menu_axis_groups.yaml`: a value change moves the pin and every stored label count becomes incomparable; a DEFINITION edit moves only a per-axis hash — the D-371/BUG-447 lesson) |
| 4 | a label changed at scale by a script without evidence | D-2938 (producer fix is forward-only; a re-stamp is not a licence), D-2898 (a judgment is not minted by a script), and the eval-integrity floor per axis (`content_type` human share is a DECLARED floor because most labels are model-voted) |
| 5 | a decision made against a GHOST — a premise that moved under the instrument | BUG-771: stamp the premise by hash and REFUSE a stale-stamp sheet |

**The axis naming itself has already drifted once, and it is recorded:** `config/claim_shape_instrument.yaml`
notes that an earlier revision named every column `FORM_*` and asserted "there is NO FORM anchor" — both wrong
(BUG-459/BUG-461). FORM is AXIS 2 `extraction_type` (4 epistemic forms), 145/150 anchored. A guardrail that
cannot name its own axis is not a guardrail.

**And the "keep it open" half — YES, for the OBJECT; NO, for the VOCABULARY; NEVER silently.** A system whose
`growth_edge` can never become a `principle` has nowhere to put what it learns. A vocabulary that quietly grows a
sixth content type, or a discipline that arrives by alias, has no pins and no denominator. So:
**closed menu, open assignment** — the menu is closed, versioned, pinned and append-only through a calibrated
path; the assignment is open, and moving requires body evidence, a provenance stamp, and (where the label is a
judgment rather than a derivation) the owner's gate.

---

## §7 The recommendation table (what to do, what it costs, and the rail)

| # | recommendation | why | cost | the rail / measure that makes it true |
|---|---|---|---|---|
| 1 | T-120: make corroboration a DERIVED re-computable measure; `is_convergent` stops being an INPUT | a tier that can never rise is not a record; a delta run cannot corroborate and looks identical to "nothing to corroborate" | one derived-value home + a parity rail; compute only on rows whose tier would move | register `fbs.independence` in `config/derivations.yaml` (D-2646) + parity rail; FALSIFIER stated |
| 2 | BUG-773: the revision trail + `content_basis` writer; the HEAD changes, the RECORD does not | C6 forbids the alternative; D-2933 rule V already declares it — on a path that does not enforce it | one append-only sidecar + one writer at extraction | the declared `never_at_commit` made TRUE; `fb_revisions` count == number of body changes |
| 3 | axes move only through their instrument | a body revision is evidence, an axis is a judgment (measured: 88% router false positives, D-2953) | none new — the gates exist | the D-2953/D-2955 body-evidence controls + `*_source` provenance |
| 4 | T-121/BUG-774: source-kind axis + per-kind identity + the re-publication collapse rule BEFORE intake | identity is the blocker, not the converter; the alternative re-opens BUG-289 | a source-kind block in config + a resolver per kind | `verify_source_identity.py` must stay at 0.0 both-unknown with a NON-book source in the cache |
| 5 | closed menu, open assignment; never silent | pins make a vocabulary change VISIBLE; an instrument makes an assignment justifiable | none new | `menu_axis_hashes` / `menu_axis_groups` + the cemetery + the provenance columns |

---

## §8 What this does to the order of work (the strategic consequence)

1. **T-107 (`retire` + `promote corroboration`) is the SURFACE change** — it stops advertising a dead constant and
   publishes the measure we actually hold.
2. **T-120 makes that surface STABLE** — the published corroboration must be re-derivable from the row's own
   evidence, or it is a second constant with a longer name.
3. **T-119 is the prototype of T-120**, not a separate measurement: `n_voices` and its distribution ARE the
   engine's first output, and the falsifier is what stops the hardening from becoming decoration.
4. **T-121 gates the intake programme.** Converting podcasts and papers before identity and independence exist
   would manufacture exactly the inflation the corpus spent BUG-289, D2176 and D-2308 removing.
5. **T-104/BUG-757 (the severity backfill) stays the top PIPELINE-lane repair** — it is what makes "highest
   leverage" answerable for every other item on this list.

---

## §9 THE OWNER LANE, IN PLAIN WORDS (the batch, with my recommendation per item)

**What "owner lane" means.** Some facts in this system are not derivable: a golden anchor, what the system is
allowed to SAY about weak evidence, whether a label is right, and what to do about a class of legacy labels.
Those are YOUR call, not the machine's (D-2898: no agent may decide what the system says about its own evidence).
The pipeline is BLOCKED behind them — not the other way round. Each needs ONE word from you; the word goes into a
named file (`governance/OWNER_LANE_BATCH_20261013.md` is that sheet), and a rail then refuses to run without it.
Nothing is applied by writing a word into prose: the word is read by a rail.

| id | what only you can decide | my recommendation | what happens if you choose otherwise |
|---|---|---|---|
| **T-101** | the ANCHOR SET semantics of your 150-cell review: does each query have ONE right answer (`single`) or a SET of acceptable ones (`set`)? | **`set`** | `single` would require you to pick one rank per query (30 more cells) and would DISCARD ~90 of your 120 marks. The measured consequence of `set`: recall is micro over the expected set, so the ruler gets STRICTER (production MRR 0.919 → 0.954, P@k 0.100 → 0.414, and the three legs finally separate: fts 0.408 / vector 0.694 / hybrid 0.712). Your marks were a coverage judgement; `set` is that judgement. |
| **T-107** | what the payload may advertise: `borp_score` → `retire` + `promote corroboration`; `classification_status` → `keep-and-repair` (`feedback_score` is already granted `keep-and-declare`) | **`retire` + `promote corroboration` + `keep-and-repair`** | anything else keeps three surfaces publishing a fabricated `0.0` (BUG-767) and keeps the real measure unadvertised. One word per field; the change-set is ONE move and the rail refuses a half-move. |
| **T-118** | what the system may SAY about the majority of served rows that no second source covers | **`tier`** | `withhold` would drop most of the served corpus with no rule supporting it (a corpus edit); `leave` is silence — the system would keep serving uncorroborated claims with no statement about them. `tier` is additive and declarative: serve the row and state its corroboration tier on every answer. |
| **T-117** | the ESCALATE surface: one word per unit for the units no ruling reaches | **NOT one blanket word — one word per CAUSE-GROUP.** The packet's own cause census gives three homogeneous classes: DEFINITION-RE-SCOPE (a definition moved, the row was judged against a sharper one) → **CONFIRM** where the recorded-menu control reproduced the stored label (the packet lists only those); ALIAS-LAYER-RETIRED (the live mapper is correct by design; the row is a legacy of an earlier map) → **CONFIRM** (declare the raw as an alias, no relabel); PROVENANCE-UNRESOLVED → **CORRECT + home** where a canonical fits, **ABSTAIN** where none does, **LEAVE** where the packet cannot evidence it | a blanket CONFIRM would declare every one of the units a link nobody can evidence — the D-2898 class, at scale. The packet's own note says the top 12 units carry most of the rows: settle those first. |

**Why I am not simply writing these for you:** the anchor is owner-SIGNED (D-2939/INV-3), severity and trust
tiers are CLAIMS (D-2898), and a ruling is not a licence for a script to generalise it to a whole class
(D-2988). What I can do — and did — is make the consequence of each option measurable, name the file and the
cell, and put a rail behind the word so a half-move cannot land.

---

## §10 Files, continuity, and the next critical step

**Created in this act:** this file · `governance/OWNER_LANE_BATCH_20261013.md` (the sheet) ·
`governance/SESSION-HANDOFF-20261013-D2992.md` (the act record) · `governance/decisions_mint_D2992.yaml` (the
mint record). **Filed:** BUG-772 (corroboration is run-frozen; no absorption path), BUG-773 (the declared
`never_at_commit` rule vs the live upsert; `content_basis` has no writer), BUG-774 (book-shaped identity blocks
the media plan; the fallback branch would go live). **Filed as tasks:** T-120 (the absorption path / derived
corroboration), T-121 (source-kind axis + per-kind identity + re-publication collapse). **Nothing was applied to
the store, no payload or export was touched, no axis label was moved.**

**Next critical step (pipeline lane):** T-104/BUG-757 — the severity backfill (the register still cannot be
ordered by criticality), then T-120's read-only step 0, then BUG-771's stale-premise stamp.
**Next critical step (owner lane):** the four words in §9.
