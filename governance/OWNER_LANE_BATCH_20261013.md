# OWNER LANE — the batch (2026-10-13): four words, and what each one does

**What this sheet is.** The pipeline is BLOCKED behind four decisions that no agent may make (D-2898): a golden
anchor is owner-SIGNED (D-2939), a trust tier is a POLICY about what the system may SAY, and a ruling is not a
licence for a script to generalise it to a class (D-2988). Each item below needs ONE word from you. The word goes
into the named file; a rail then reads it and refuses to run without it — prose is not a mechanism.

**Read this sheet, not the register.** Items 1–4 BLOCK the pipeline today; item 5 is filed by this act and is not urgent. Everything here is verified against the tree at 2026-10-13; the numbers
live in the artifacts named in the last column of each section.

---

## 1 · T-101 — the ANCHOR SET (`config/pipeline_config.yaml` → `retrieval_benchmark.reanchor.anchor_mode`)

**What you already did.** You filled the 150-cell re-anchor sheet: 120 cells marked `anchor`, 11 `rewrite-query`,
and the rest abstentions. Several candidate answers per query carry a mark.

**What is undecided.** Whether a query has ONE correct answer or a SET of acceptable ones. The applier currently
ships `single` and therefore REFUSES your sheet (48 semantics), naming the one-line config edit.

**MY RECOMMENDATION: `set`.**

| choice | what it means | the measurable consequence |
|---|---|---|
| **`set`** (recommended) | every marked candidate becomes part of the expected set; recall divides by the SET (micro) | stricter ruler: production MRR 0.919 → 0.954, P@k 0.100 → 0.414; and it separates the legs for the first time — fts 0.408 · vector 0.694 · hybrid 0.712 |
| `single` | "only this one is the answer"; the applier then needs ONE rank per query = ~30 more cells from you, and ~90 of your 120 marks are discarded | the old saturated ruler (production recall 1.000, P@k 0.100) which cannot gate any retrieval improvement |

**Why `set` is the right reading of your own sheet:** you marked 3–5 candidates per query, which is a COVERAGE
judgement ("any of these would be a defensible answer"), and a coverage judgement is what an expected SET is for.

**Then the pipeline runs, in this order:** `python3 scripts/reanchor_retrieval_goldens.py --check` (must be
clean) → `--apply` (C13 backup, writes golden version 5) → `python3 pipeline/retrieval_benchmark.py`.

---

## 2 · T-107 — the payload contract (`config/served_fields.yaml` → `declared`)

**Three advertised fields, three words.** `feedback_score` is already granted (`keep-and-declare`) and is being
made verifiable. What remains:

| field | MY RECOMMENDATION | why |
|---|---|---|
| `borp_score` | **`retire`**, and at the same time **`promote corroboration`** (`{sources, convergent, independence, independence_score, home}`) | `borp_score` is a constant `0.0` whose producer was DELETED at S5, still published by three outward surfaces (MCP payload, OKF export, Anytype push) — an agent reads `0.0` as "no corroboration" on rows that are in fact strong (BUG-767/BUG-768). The real measure exists (`pipeline/schema_accessor.py::isor_score`, D2284/D2309) and is advertised by nothing. |
| `classification_status` | **`keep-and-repair`** | it is a constant `CLEAN` on every served row while the store's own `status` column quarantines thousands: one row carrying two statuses is the D-2987 defect on the wire. The repair is a writer fix, not a contract change. |

**Shape of the change-set:** ONE move — delete the three MCP payload keys, retire `borp_score` from the OKF
export and the Anytype push, move the neutral prior out of `pipeline/retrieve.py` into
`config/feedback.yaml#serving.neutral_prior`, and publish the feedback + corroboration blocks. The rail reports
rc 2 (the owner lane) and refuses a half-move.

---

## 3 · T-118 — the SINGLE-SOURCE trust tier (`config/served_fields.yaml` / the surface policy)

**The situation, plainly.** The Book of Record Principle ("at least two independent sources") holds for the
MINORITY of served rows, because the corpus is admitted through two routes and only the CLUSTER route passes the
at-least-two-source gate. The other route (singletons) reaches the store with ONE source work, and nothing
re-asserts the principle per row. The system therefore serves a large set of claims it cannot certify.

**MY RECOMMENDATION: `tier`** — serve the row, and state its corroboration tier on every answer
(`{independence: weak|medium|strong, sources, convergent}`).

| choice | what it means | cost / risk |
|---|---|---|
| **`tier`** (recommended) | the answer says what the evidence is: "1 source, weak independence" | ADDITIVE and DECLARATIVE — no corpus edit, nothing withheld, reversible, and it is the only option that tells an agent the truth |
| `withhold` | exclude uncorroborated rows from the default answer path | drops the majority of the served corpus — a CORPUS EDIT with no rule behind it (measured in the assessment: the single-source share is large) |
| `leave` | accept single-source rows as first-class and say nothing | silence: the system keeps serving uncorroborated claims with no statement — the reader cannot tell whether a claim is corroborated |

**Note the dependency:** `tier` is only honest if the tier is MEASURED (T-119) and the measure is not a frozen
boolean (T-120). The hardening is what makes this word safe to give.

---

## 4 · T-117 — the ESCALATE surface (`governance/canonical_relabel_review_20261014.md` + `.csv`)

**What it is.** 72 review units (311 rows) whose stored discipline label the live taxonomy no longer produces, so
no owner ruling reaches them. Each unit takes ONE of four words: `CONFIRM` (the stored label is the right home;
declare the raw as an alias — no relabel), `CORRECT` + a canonical home (relabel the unit), `ABSTAIN` (no home
fits — the label becomes the declared absence `emerging`), `LEAVE` (the mapping stands as a historical artefact;
nothing is written).

**MY RECOMMENDATION: do NOT write one blanket word for all 72. Word them BY CAUSE-GROUP** — the packet's own
cause census already groups them into homogeneous classes:

| cause | rows | the word I would write | why |
|---|---|---|---|
| `DEFINITION-RE-SCOPE` (D-2928) | 17 | **CONFIRM** on the units the packet lists (it lists only rows whose RECORDED-menu control reproduced the stored label) | the definition moved, the answer space did not; the recorded-menu control proves the label is right under its own recorded menu |
| `ALIAS-LAYER-RETIRED` (D-2814) | 173 | **CONFIRM** (declare the raw as an alias; no relabel) | the LIVE mapper is correct by design (D-2976's own note); the row is a legacy of an earlier map, and a CONFIRM writes an alias, not a label change |
| `PROVENANCE-UNRESOLVED` | 121 | **CORRECT + home** where a canonical plainly fits; **ABSTAIN** where none does; **LEAVE** where the packet cannot evidence it | a CONFIRM here would declare a link nobody can evidence (the D-2898 class); ABSTAIN writes the declared absence and is reversible by a later ruling |

**Batch mechanics that ARE legitimate:** start with the top 12 units (they carry ~59% of the rows), and give one
word per unit — the CSV is one row per decision, sorted by leverage. Apply only after the packet is returned; an
unrecognised word or a `CORRECT` with no canonical home fails closed.

---

## 5 · T-121 (NEW, filed by this act) — the SOURCE-KIND vocabulary (the media-intake prerequisite)

**Not urgent — nothing is blocked today.** No non-book source has been ingested, so no row is wrong. But the intake
programme (journals, transcripts, video, threads, podcasts) cannot start safely without this, and it is an
ANSWER-SPACE change, which makes it yours.

**MY RECOMMENDATION: (i) accept a source-KIND axis** (read the vocabulary from an external authority rather than
inventing it — OpenAlex carries a controlled 25-value work `type`, and `config/references.yaml` already resolves
bibliographic metadata from OpenAlex by DOI), and **(ii) rule that a work and its re-publication are ONE voice**
(preprint → version of record; the author's book → the author's podcast; a paper → its blog post).

| choice | consequence |
|---|---|
| **(i) yes + (ii) ONE voice** (recommended) | a new medium can corroborate a claim only when it is genuinely another VOICE; the edition-collapse rule the corpus already applies (D-2308) simply generalises |
| (i) yes + (ii) count them separately | a preprint and its published version, or a book and the author's own reading of it, would each certify "two independent sources" — the echo/slop pattern the Book of Record Principle exists to stop |
| no axis at all | ingest falls onto the FILENAME fallback branch the corpus spent a defect class removing: a podcast has no author｜title, and `source_diversity` would start counting filenames again |

---

## The words, in one block (fill and return; each is read by a rail, never by prose)

```
T-101  anchor_mode        : set | single
T-107  borp_score         : retire | keep | keep-and-declare | keep-and-repair | promote <field>
T-107  classification_status : ...
T-118  single-source      : tier | withhold | leave
T-117  escalate units     : one word per unit on governance/canonical_relabel_review_20261014.csv
```
