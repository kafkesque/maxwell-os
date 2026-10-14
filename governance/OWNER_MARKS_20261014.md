# THE OWNER'S MARKS — 2026-10-14

**Why this page exists.** Six open MUST tasks are blocked on the same thing and it is not code: YOUR WORD. Until
today each owed act lived only as prose (a `gate:` line in `config/task_register.yaml`), so no rail could read it,
no vocabulary validated it, and the one sheet that looked like an answer carried a machine screen (68 yes / 16 no,
written by no script in this repo) in a column NAMED `owner_ruling` — and its "identical text" column said **42**
where the measuring rail and the census both say **37** (BUG-782). A lane whose only machine-readable "ruling" was
minted by nobody is a lane an agent can read as RELEASED. The intake now exists; this page is the act.

**Your whole act, in one line:** five one-word signatures in `config/owner_marks.yaml`, plus eight cells (or one
word each) in the ledger projection. Everything else is already declared, rendered and gated.

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

Set `signed: 2026-10-14` (or any date) on these tier lines in `config/owner_marks.yaml`:

| tier | what it covers | rows | word | the evidence behind it |
|---|---|---:|---|---|
| **A** | `evidence_class == identical_normalised_text` | 37 | `CONFIRM-ONE-WORK` | the measurement itself: identical normalised text under two names IS one voice, no threshold involved (re-measured today: 37, not the 42 the old sheet claimed) |
| **B** | containment ≥ the declared bar **and** the screen agreed `yes` | 42 | `CONFIRM-ONE-WORK` | containment at/above 0.80 with both sides clearing the boilerplate screen. Containment CAN certify a collapse; what it cannot certify is that the shared text is the WORK rather than boilerplate — that judgement is what your signature supplies |
| **C** | containment ≥ the bar **and** the screen said `no` | 16 | `DISTINCT` | the false-positive class: 7 singleton pairs + the 3 series-volume groups (v1 groups 3, 5, 6). Eyeball three of them before signing; they are the `Poor Charlie's Almanack` vs `Seeking Wisdom`, `Great Mental Models Vol 1` vs `Vol 2/4`, `HBR Guide to Making Better Decisions` vs `…Unlocking Creativity` shape |
| **L-A** | ledger `hint in (subtitle_or_edition, title_rename, author_leak, noise_suffix)` | 48 | `MERGE` | the ledger's own declared hint classes: an edition/subtitle is the same work (D-2308), an author leaking into the title is a normalisation artefact, a piracy suffix is noise the sanitizer already strips |
| **L-B** | ledger `hint == series_volume` | 3 | `KEEP_SEPARATE` | the boundary of D-2308 stated as a word: an EDITION of one work collapses, a VOLUME of a series does not |

### The eight cells that need YOUR word (no evidence speaks for them)

`hint == review` — 8 ledger pairs. **Tier L-C carries no word on purpose**: a tier with no evidence behind it may
not carry a blanked word (that is how a machine mints a label, D-2898). For each of the 8, write in
`governance/duplicate_adjudication_review.csv#owner_verdict`:

- `MERGE` → they are one work · `KEEP_SEPARATE` → they are two · `PENDING` → **the word is withheld, deliberately**
  (the pair stays open and the ingest door keeps refusing — that IS the guarantee, not a failure).

### "If I just approve, I approve"

**Yes — approving tiers A, B, C, L-A and L-B IS the act, and it is the recommended one.** Each of those rows
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
python3 scripts/owner_marks.py --check      # what you still owe (rc 2 = owed, loud, NOT fatal)
python3 scripts/owner_marks.py --apply      # expand the signatures you signed + write the receipt, atomically
python3 scripts/owner_marks.py --render     # only if the measurement changed: re-measure + re-render both sheets
python3 scripts/owner_marks.py --selftest   # 9 known-answer controls (no store, no model)
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
| **T-124** (MUST) | the anchor-bridge **ambiguity policy**: a name resolving to N rows must either stay declared-unresolved or be resolved by a DECLARED rule. A RULING, not a sheet — it unmasks the 68 masked rails and BUG-777/778 | your word, then a decision mint (`D-2898` is the precedent) |
| **T-117** (MUST) | one word per unit on the ESCALATE reference sheet: `CONFIRM` / `CORRECT + home` / `ABSTAIN` / `LEAVE` (72 units, 311 rows) | `governance/canonical_relabel_review_20261014.md` |
| **T-101** (MUST) | the marks must reach the sheet the re-anchor applier reads; `anchor_mode: set` is already granted and declared — measured today the applier sees **0 of 30** queries with an anchor row and `--apply` would REFUSE | marks → `temp/golden_proposed_v5.yaml`, applier `scripts/reanchor_retrieval_goldens.py` |
| **T-121** (SHOULD) | the **SOURCE KIND vocabulary** (an answer-space word) + whether a work and its re-publication are ONE voice (recommended YES: the D-2308 edition rule generalised). No non-book source may be ingested before it lands | your word → `config/content_types.yaml` |

---

## §3 — What is NOT covered (declared, because an unstated scope reads as coverage)

- **The paraphrase/translation class** — invisible to the lexical screen; it stays with `limb_semantic`
  (embeddings + NLI), declared as the residual in `config/corroboration_collapse.yaml` (`D-2996 §7`).
- **Content-level unrelated titles before S1.5** — that is L1 (the content screen tightening), a pipeline layer.
- **Non-book sources** — T-121 (above).
- **The 8 `review` pairs** — no declared evidence speaks; only your word or a deliberate `PENDING`.
- **Naming defects in the corpus** (3 leading/trailing whitespace, 34 repeated internal whitespace, 459
  ingest-site markers) — the fix is a *write* into filenames, tracked by the ingest door's own reading.
