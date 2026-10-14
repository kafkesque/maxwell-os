# THE OWNER'S MARKS — 2026-10-14

**Why this page exists.** Six open MUST tasks are blocked on the same thing and it is not code: YOUR WORD. Until
today each owed act lived only as prose (a `gate:` line in `config/task_register.yaml`), so no rail could read it,
no vocabulary validated it, and the one sheet that looked like an answer carried a machine screen (68 yes / 16 no,
written by no script in this repo) in a column NAMED `owner_ruling` — and its "identical text" column said **42**
where the measuring rail and the census both say **37** (BUG-782). A lane whose only machine-readable "ruling" was
minted by nobody is a lane an agent can read as RELEASED. The intake now exists; this page is the act.

**Your whole act is now ONE command — and the ledger half is already DONE by your hand.** MEASURED 2026-10-14
22:2x: `governance/duplicate_adjudication_review.csv` carries `owner_verdict` on **59 of 59** pairs (51 `MERGE` / 8
`KEEP_SEPARATE`), so the ledger's debt is CLOSED and **tiers L-A/L-B no longer need a signature at all** — a per-row
word always beats a blanket rule in the derivation (`override > tier_signature > none`), and signing the rule on top
of your 59 rows would generalise a word you gave pair by pair. What remains is the collapse sheet's 84 rows, and your
own typed cells are row-for-row exactly what tiers A+B+C expand to (37 + 31 + 16 = 84) — measured, on a copy:

```
python3 scripts/owner_marks.py --sign A B C             # THE OWNER'S WORD: 3 tiers, one act, dated today
python3 scripts/owner_marks.py --check                  # then rc 0 — 'every row of both homes carries a word'
python3 scripts/owner_marks.py --apply                  # expand the signed predicates; writes the 84 cells + provenance
```

A dry run on a COPY of the policy (nothing written) measured the outcome of those three ids: sheet **0 owed**, 0
conflicts, 0 binding faults, words `CONFIRM-ONE-WORK` 68 / `DISTINCT` 16, every row carrying provenance
`signature:A@…` (37) / `signature:B@…` (31) / `signature:C@…` (16).

The signer refuses an unknown tier id, refuses a tier whose `word` is `null` (there is nothing to sign), refuses to
overwrite an existing signature silently, and re-reads the date it just wrote before it returns — a signature that did
not land is not an act (D-2676). It never chooses WHICH tiers: the ids are your word. Then the last item is eight
cells (**§1.3**) — or a deliberate `PENDING`, which is itself a word.

> **WHY THE 84 CELLS YOU TYPED DID NOT LAND (2026-10-14, measured).** They went into `owner_ruling`, which is the
> DERIVED column (`--apply`'s output) — the column the OWNER writes is `owner_override`, and it is empty. Your 84
> words are, row for row, exactly what tiers A+B+C expand to (37 + 31 + 16 = 84), and your three notes were carried
> (`owner_note`). So nothing you decided is lost: the signature is that same act expressed in the form the machine
> can read, and it is why approving costs one command instead of 84 cells. (The v1 sheet's `owner_ruling` column
> held the machine screen, which is the name-collision BUG-782 retired.)

---

## §1 — T-129 / T-130: identity (is this ONE work or TWO?)

Two sheets, ONE ontology question, two vocabularies (T-130 already calls it *one act read twice*).

| home | file | rows | vocabularies | you write |
|---|---|---:|---|---|
| the collapse sheet | `governance/work_identity_collapse_review_20261014.csv` | 84 pairs / 72 groups | `CONFIRM-ONE-WORK` · `DISTINCT` · `LEAVE` | `owner_override` (exceptions only) |
| the ledger projection | `governance/duplicate_adjudication_review.csv` | 59 pairs | `MERGE` · `KEEP_SEPARATE` · `PENDING` | `owner_verdict` (exceptions only) |

The ONE home of the words, the tiers and the derivation is **`config/owner_marks.yaml`** (rendered by
`scripts/owner_marks.py`; the ledger stays the one home of its own verdicts).

### The five signatures (each is one word on one line)

`python3 scripts/owner_marks.py --sign A B C` stamps `signed: <date>` on these three tier lines in
`config/owner_marks.yaml` (by hand is equivalent; the command exists so the act is one keystroke and its refusals are
SEEN). Each signature covers the rows its predicate names — nothing has to be typed twice:

| tier | what it covers | rows | word | the evidence behind it |
|---|---|---:|---|---|
| **A** | `evidence_class == identical_normalised_text` | 37 | `CONFIRM-ONE-WORK` | the measurement itself: identical normalised text under two names IS one voice, no threshold involved (re-measured today: 37, not the 42 the old sheet claimed) |
| **B** | containment ≥ the declared bar **and** the screen agreed `yes` | 31 | `CONFIRM-ONE-WORK` | containment at/above 0.80 with both sides clearing the boilerplate screen. Containment CAN certify a collapse; what it cannot certify is that the shared text is the WORK rather than boilerplate — that judgement is what your signature supplies |
| **C** | containment ≥ the bar **and** the screen said `no` | 16 | `DISTINCT` | the false-positive class: 7 singleton pairs + the 3 series-volume groups (v1 groups 3, 5, 6). Eyeball three of them before signing; they are the `Poor Charlie's Almanack` vs `Seeking Wisdom`, `Great Mental Models Vol 1` vs `Vol 2/4`, `HBR Guide to Making Better Decisions` vs `…Unlocking Creativity` shape |
| ~~L-A~~ | (no signature needed — your 59 per-row words decide) ledger `hint in (subtitle_or_edition, title_rename, author_leak, noise_suffix)` | 48 | `MERGE` | the ledger's own declared hint classes: an edition/subtitle is the same work (D-2308), an author leaking into the title is a normalisation artefact, a piracy suffix is noise the sanitizer already strips |
| ~~L-B~~ | (no signature needed) ledger `hint == series_volume` | 3 | `KEEP_SEPARATE` | the boundary of D-2308 stated as a word: an EDITION of one work collapses, a VOLUME of a series does not |

### The eight cells — ✅ YOUR WORD HAS LANDED (recorded 2026-10-14, 22:2x)

`hint == review` — the 8 ledger pairs where no declared evidence speaks. **You ruled all 8 by hand**; the column is
`governance/duplicate_adjudication_review.csv#owner_verdict` and the table below is your word, kept beside my
recommendation so the two are never confused. Tier L-C carries no word on purpose (a tier with no evidence behind it
must not carry a blanked word: that is how a machine mints a label, D-2898).

| pair_id | the two names | my recommendation | YOUR WORD | |
|---|---|---|---|---|
| `a4ebdd393e24def2` | Sean Adams — *The Designer's Dictionary of **Color*** vs *… of **Type*** | `KEEP_SEPARATE` (high) | **`MERGE`** | ⚠️ see below |
| `68f90898423cce1d` | Neumeier — *The Brand **Flip*** vs *The Brand **Gap*** | `KEEP_SEPARATE` (high) | `KEEP_SEPARATE` | ✔ |
| `35c6778225c7ad32` | Miller — *Metaphorically Selling* vs *The Tall Lady With the Iceberg* | `KEEP_SEPARATE` (high) | `KEEP_SEPARATE` | ✔ |
| `f621222bfafc3f28` | Kotler — *Marketing 7.0* vs Kotler/Keller/Chernev/Sheth — *Marketing Management* | `KEEP_SEPARATE` (high) | `KEEP_SEPARATE` | ✔ |
| `e93136effd604167` | Pressfield — *The War of Art …* (two subtitle variants) | `MERGE` (high) | `MERGE` | ✔ |
| `03898151f8617e9f` | Neumeier — *The Brand Gap* vs *…, Revised Edition* | `MERGE` (high) | `MERGE` | ✔ |
| `833b7b704cd98478` | *Anonymous — The Essential Guide…* vs *Alison Branagan — the essential guide…* | `MERGE` (high) | `MERGE` | ✔ |
| `542f9b581dfccf15` | van Leeuwen & Djonov — *…semiotics of **kinetic** typography* vs *Towards a semiotics of typography* | `KEEP_SEPARATE` (medium) | `KEEP_SEPARATE` | ✔ |

> **TWO ROWS WHERE YOUR WORD OVERRIDES A DECLARED RULE OR MY ADVICE — recorded, not "fixed" (a resolved
> contradiction is a minted label, D-2898):**
> **(1) `ad02046ad2461eff`** — *The anatomy of type A graphic guide to 100 typefaces* (Coles + Spiekermann) vs *The
> Anatomy of Type* (Coles): the declared L-A rule says `MERGE`, and you wrote **`KEEP_SEPARATE` with the note "two
> different books"**. Your word stands and it is the safer error (splitting two identical rows costs nothing;
> merging two works inflates corroboration).
> **(2) `a4ebdd393e24def2`** — one row where I recommend you look again before the pipeline acts on it: the only
> detector that fired is the TITLE (`max_similarity 0.775`, no content overlap), the two titles name *different
> subject matter* (Color vs Type — two real books by the same author in one series), you wrote no note explaining the
> merge, and the same file's other "different books" call carries the note "two different books". If that MERGE was a
> slip, say the word and it is one cell: `KEEP_SEPARATE`. Nothing else in the 59 depends on it — but it is the one
> row where a wrong word creates a claim the evidence contradicts, which is precisely what this whole task removes.

| pair_id | the two names | why | recommend | conf. |
|---|---|---|---|---|
| `a4ebdd393e24def2` | Sean Adams — *The Designer's Dictionary of **Color*** vs *… of **Type*** | two different reference works (colour vs type) | `KEEP_SEPARATE` | high |
| `68f90898423cce1d` | Neumeier — *The Brand **Flip*** vs *The Brand **Gap*** | two different books | `KEEP_SEPARATE` | high |
| `35c6778225c7ad32` | Anne Miller — *Metaphorically Selling* vs *The Tall Lady With the Iceberg* | two different books by one author, both about metaphor | `KEEP_SEPARATE` | high |
| `f621222bfafc3f28` | Kotler et al. — *Marketing 7.0* vs Kotler/Keller/Chernev/Sheth — *…* | different titles by an overlapping author set | `KEEP_SEPARATE` | high |
| `e93136effd604167` | Pressfield — *The War of Art **Break Through the Blocks and Win your Inner Creative Battle*** vs *…**Winning the Inner Creative Battle*** | ONE book, publisher subtitle variance | `MERGE` | high |
| `03898151f8617e9f` | Neumeier — *The Brand Gap* vs *The Brand Gap, **Revised Edition*** | an EDITION of one work (D-2308) | `MERGE` | high |
| `833b7b704cd98478` | *Anonymous — The Essential Guide to Business for Artists and Designers* vs *Alison Branagan — The essential guide to business for artists designers* | author-leak ("Anonymous") + casing: ONE work | `MERGE` | high |
| `542f9b581dfccf15` | van Leeuwen & Djonov — *Notes towards a semiotics of **kinetic** typography* vs van Leeuwen — *Towards a semiotics of typography* | two publications; a revised/related paper, not the same artefact | `KEEP_SEPARATE` | medium |

Write the word in `governance/duplicate_adjudication_review.csv#owner_verdict` (that file exists — it is the ledger's
declared PROJECTION, generated by `--render`; the ledger `governance/duplicate_adjudication.json` stays the one home
of its verdicts). If you would rather not decide one of them, write `PENDING` — that is a word, it closes the OWED
reading, and it keeps the door shut on exactly that pair.

### "If I just approve, I approve"

**Yes — approving tiers A, B and C IS the act, and it is the recommended one** (L-A/L-B need no signature: your
59 ledger words are already in). Each of those rows
carries either the measurement itself (A) or a clearly-labelled, per-row-inspectable screen (B/C) or the ledger's
own declared hint classes (L-A/L-B); nothing is deleted, nothing merges in the store: your word releases the
*repair* (T-129's pipeline half) and opens the *door* (T-130).

**No — you cannot leave the 8 review pairs unworded:** without a word they stay OWED and the door stays shut for
every future batch. A deliberate `PENDING` on those 8 is itself a word and clears the OWED reading.

**Exceptions.** Disagree with a row? Write the opposite word in `owner_override` (an override always wins over a
signature) and a line in `owner_note`. The two hand notes already on the sheet — *"keep the revised edition"*,
*"keep enxpanded edition"* — are carried verbatim into `owner_note`; if they stand, put `DISTINCT` in
`owner_override` on those two rows, because as rendered they sit under a signature that says one work.

### What each word does (measured expectations, not promises)

| | today | after your word |
|---|---:|---:|
| `is_convergent = 1` rows (the count's certificate) | 1,393 | 863 |
| store rows advertising `epistemic_status = corroborated` | 257 | ≤ 123 |
| rows DELETED | 0 | **0** (R-D410: `duplicate_of` + QUARANTINE, never a delete) |
| the ingest door | refuses (`rc 2`) | refuses until every owed word lands, then opens for delta-scoped intake |
| `check_corroboration_bit` | green and honest (7,640/7,640) | green and honest over the repaired population |

Nothing here touches S2/S4 (the extracted text stays) and S5 cannot and must not catch this (NLI entailment is
not independence, D2298). The unsupported thing is the corroboration **claim** — a derived value — so this is
relabel + re-derivation, never a delete.

### The commands

```
python3 scripts/owner_marks.py --sign A B C   # THE OWNER'S WORD (the only writer of `signed:`; L-A/L-B need none)
python3 scripts/owner_marks.py --check      # what you still owe (rc 2 = owed, loud, NOT fatal)
python3 scripts/owner_marks.py --apply      # expand the signatures you signed + write the receipt, atomically
python3 scripts/owner_marks.py --render     # only if the measurement changed: re-measure + re-render both sheets
python3 scripts/owner_marks.py --selftest   # 13 known-answer controls (no store, no model)
```

`--apply` writes the derived word into the sheet's `owner_ruling` column **with its provenance** (`ruling_source`:
`row` | `signature:A@2026-10-14` | `none`), so a machine expansion can never be mistaken for your ruling. The
ingest door reads that column — and only that column, by declaration (`config/ingest_identity_gate.yaml#ledger.
collapse_word_column_from`), never by sniffing a column name: a name-sniff on the new sheet lands on
`proposed_ruling` (a proposal), which is exactly the BUG-782 class.

---

## §2 — The other four owner lanes (each its own home; listed so the act is one page)

| task | your act | where |
|---|---|---|
| **T-124** (MUST) | the anchor-bridge **ambiguity policy**: a name resolving to N rows must either stay declared-unresolved or be resolved by a DECLARED rule. A RULING, not a sheet — it unmasks the 68 masked rails and BUG-777/778. **My recommendation (see the session answer): (1) the DEFAULT is DECLARED-UNRESOLVED — a name that resolves to N rows never silently picks one; (2) a resolution is allowed ONLY where a DECLARED, ordered, deterministic rule selects exactly one row (exact id → served-run name+author → single-corpus-row), and the rule prints its tie-break; (3) anything the rule cannot resolve stays `declared_unresolved` and is COUNTED, never dropped — a fail-closed count, not a guess. That keeps the reference set honest and lets the ladder run past its first red line. ✅ **RULED 2026-10-14 — `D-2999`**, landed in `config/anchor_family.yaml#store_bridge.resolution`; the mover is now the pipeline (the resolution rung in `scripts/build_anchor_store_bridge.py`) |
| **T-117** (MUST) | ✅ **DONE AND CLOSED (2026-10-14)** — your 72 words plus the missing reader. **Your U022 word is recorded: `ABSTAIN`** (it read `CORRECT` with no home, and an incomplete word is not a word). MEASURED after the ingest: `scripts/ingest_relabel_rulings.py --apply` wrote **72** rulings keyed by `unit_key`, the 17 `owner_canonical` cells on non-CORRECT rows were reported ADVERSARIALLY as INERT (never written), the 3 owner notes were carried, and the applier now plans **0 ESCALATE over all 311 rows** (CONFIRM 38 / CORRECT 16 / ABSTAIN 4 / LEAVE 14) — the reader that did not exist is BUG-785, FIXED | `governance/canonical_relabel_review_20261014.csv` → `config/relabel_rulings.yaml` (ingest = `scripts/ingest_relabel_rulings.py`) |
| **T-101** (MUST) | ✅ **COMPLETE — nothing is owed, and nothing was ever missing** (BUG-784, measured 2026-10-14): your signed sheet reads `--check` **rc 0** — "29 of 29 queries carry a verdict, 120 anchor names, 19 abstentions, every chosen anchor owner-signed". The 30-fault reading was the applier defaulting to the GENERATOR's empty sheet; the paths are now DECLARED and the reader prints the sheet it read. **DONE 2026-10-14 (BUG-787 fixed): `--apply` LANDED** — `config/golden/retrieval_queries.yaml` v5, 29 queries × 120 owner-signed anchor names (the writer had been wired to the GENERATOR's sheet, so it refused all 29: the judgment was never wrong, the call site was). REMAINING = pipeline: the benchmark (and T-116: this ruler is saturated by construction) | `governance/golden_reanchor_candidates_20261011.reviewed.csv` + `governance/golden_reanchor_proposed_v5.yaml` (declared in `config/pipeline_config.yaml`) |
| **T-121** (SHOULD) | the **SOURCE KIND vocabulary** (an answer-space word) + whether a work and its re-publication are ONE voice. **My recommendation: YES — a re-publication is ONE VOICE** (D-2308's edition rule generalised: the corpus counts SOURCES, not printings; a preprint + its journal version + its repository copy is one voice, and counting three would inflate corroboration exactly as the 84 collapsing pairs did). On the vocabulary: do NOT invent one — declare the axis and ADOPT the controlled vocabulary that already exists for it (OpenAlex's work `type` set is the cleanest published starting point), keeping `book` as the value the current pipeline emits; the pipeline then builds the resolver. No non-book source is ingested before this lands. ✅ **RULED 2026-10-14 — `D-2998`**, landed in `config/content_types.yaml#source_kind` (10 adopted values, `emitted_by_pipeline: [book]`, and the gate a non-book ingest must first carry) |

---

## §3 — What is NOT covered (declared, because an unstated scope reads as coverage)

- **The paraphrase/translation class** — invisible to the lexical screen; it stays with `limb_semantic`
  (embeddings + NLI), declared as the residual in `config/corroboration_collapse.yaml` (`D-2996 §7`).
- **Content-level unrelated titles before S1.5** — that is L1 (the content screen tightening), a pipeline layer.
- **Non-book sources** — T-121 (above).
- **The 8 `review` pairs** — no declared evidence speaks; only your word or a deliberate `PENDING`.
- **Naming defects in the corpus** (3 leading/trailing whitespace, 34 repeated internal whitespace, 459
  ingest-site markers) — the fix is a *write* into filenames, tracked by the ingest door's own reading.
