# T-101 — HOW TO FILL THE RETRIEVAL GOLDEN SHEET

> **For:** the owner. **Written:** 2026-10-13 (D-2987). **Authority:** D-2939 (anchors are owner-signed),
> D-2988/D-2898 (a guess is not a label).
> **The file you edit:** `governance/golden_reanchor_candidates_20261011.csv`
> **The checker:** `python3 scripts/reanchor_retrieval_goldens.py --check`
> **The applier:** `python3 scripts/reanchor_retrieval_goldens.py --apply`

---

## 0. THE VOCABULARY, CORRECTED

**Two earlier session handoffs (D-2985 and D-2986) told you to write `keep` / `replace` / `drop` / `add`.**
**Those four words are read by NOTHING.** They appear nowhere in the code. That was an error in the
instructions, not in your reading of them.

The applier accepts exactly **four tokens**, and they are declared in ONE place
(`config/pipeline_config.yaml` → `retrieval_benchmark.reanchor.decisions`):

| token | what it means, in one sentence |
|---|---|
| **`anchor`** | **"THIS row's `cand_name` is the correct answer to this query."** |
| **`rewrite-query`** | "The question is worth asking but this wording is broken — drop it for now." |
| **`retire-query`** | "This is no longer a question the system should answer — drop it on purpose." |
| **`ambiguous`** | "I looked and I genuinely cannot tell." **Parks the query and BLOCKS the apply.** |

`ambiguous` is honest but it is not a soft option: a query left `ambiguous` will make `--apply` refuse the
whole sheet. That is deliberate — a guess is not a label — but know that it stops the write.

---

## 1. WHAT A ROW ACTUALLY IS

The CSV has **150 rows**, but they are not 150 decisions. They are:

**30 queries × 5 candidate answers each.**

Read one row like this:

| field | meaning |
|---|---|
| `query` | the search question |
| `cand_name` | **a candidate answer.** ← the only thing you are judging |
| `cand_definition` | the first ~220 characters of what that answer says |
| `cand_status` | `PASS` / `QUARANTINE` — whether the pipeline trusts the record |
| `leg_score` | the retrieval leg's score. **EVIDENCE ONLY — not a threshold.** The scores are NOT calibrated (measured spread −6.0 … +8.6 on known-positive pairs), so do not reason from the number |
| `leg_margin_to_next` | the gap to the next candidate. Also evidence only |
| `old_name` | what the golden set expects **today** — i.e. the answer we are re-checking |
| `rank` | where the system ranked this candidate |
| `decision` | ← **YOU WRITE HERE** |
| `owner_signature` | ← **AND HERE** |

---

## 2. WHAT YOU DO

For each of the 30 queries, look at its 5 candidate names and decide which ONE is the right answer.

**Write `anchor` in the `decision` cell of that one row. Leave the other four rows of that query BLANK.**

Then put your initials or name in the `owner_signature` cell **of the row you anchored**.

### The count: 30, not 150.

* **30 cells in `decision`** (one per query — the row you pick).
* **30 cells in `owner_signature`** (the same rows).
* The other **120 rows stay blank.** Blank is not "undecided" — it means "not the chosen answer".

> **If the query is already correct**, still write it: anchor the row whose `cand_name` equals `old_name`.
> Anchoring what is already right is the most valuable cell you can write — it converts an inherited
> assumption into an owner-signed claim.

### Worked example

```
query                          , rank, cand_name                       , old_name                    , decision, owner_signature
how do organizations recover…  , 1   , Institutional Response to Crisis , Collective Intelligence Rec… ,         ,
how do organizations recover…  , 2   , Resilience in Adversity          , Collective Intelligence Rec… , anchor  , B.
how do organizations recover…  , 3   , Mentorship Through Adversity     , Collective Intelligence Rec… ,         ,
```

Row 2 is anchored → this query now expects **"Resilience in Adversity"**. The old expectation
("Collective Intelligence Recovery") is replaced. That is what "replace" meant.

---

## 3. THE THREE THINGS THAT WILL STOP YOU (AND WHY THEY ARE GOOD)

1. **A token that is not one of the four.** Typing `keep` gets you
   `row 42: decision 'keep' is NOT one of ['ambiguous','anchor','retire-query','rewrite-query']`.
   The allowed set is printed back to you.
2. **Zero or two anchors in a query.** Exactly one is required.
3. **An anchor with no signature.** D-2939 says anchors are owner-signed and **no model may sign one**.
   Since D-2987 the applier enforces that instead of only declaring it. (Before, the `owner_signature`
   column was written by the generator and read by *nothing* — a rule with no control behind it.)

**Run the checker the moment you finish, not at the end of the sitting:**

```bash
python3 scripts/reanchor_retrieval_goldens.py --check      # writes nothing, touches no store
```

It reports the same judgement `--apply` will, **before** any write — so a wrong token costs you nothing.

---

## 4. THEN

```bash
python3 pipeline/retrieval_benchmark.py                     # BEFORE  (today: recall@10 1.000 / MRR 0.919)
python3 scripts/reanchor_retrieval_goldens.py --apply       # takes a C13 backup, then writes
python3 pipeline/retrieval_benchmark.py                     # AFTER
```

**Success signal:** `recall@10` **drops below 1.000**. A perfect score on an easy ruler is the defect,
not the goal. `MRR` (0.919 today) is the only live number until that happens — which is exactly why this
task exists: *a saturated metric cannot gate an improvement.*

---

## 5. THE HONEST GAPS (so you are not surprised)

* **This sheet RE-ANCHORS the 30 existing queries. It does not ADD new ones.**
  T-101's actual goal — *"add harder/abstract and adversarial goldens"* — has **no instrument**. That is a
  real gap, recorded as a separate task. Do not expect this CSV to produce harder queries; it cannot.
* **One draft query is out of phase.** The draft carries
  `can a large language model be compressed into a smaller one`, which a previous apply **retired on purpose**.
  `--check` now warns about it: anchoring that row would **ADD** it back. Adding is legitimate — but it must
  be a deliberate act, not a side effect.
* **Judge the NAME, never the id.** The names are the anchors (D-2939); ids are resolved per run and may change
  without re-signing.
* **`leg_score` is not a threshold.** If you find yourself ranking by the number, stop — the number is not
  calibrated and the file will not let you use it as a gate.

---

## 6. THE REVISION (2026-10-13, D-2991) — your review was REFUSED for a rule the ruler never had

**What you wrote:** 120 `anchor` marks (3-5 candidate answers per query), 11 `rewrite-query`, and 19 cells reading
`ambigouos`. **What the applier answered:** **48 faults** — 19 rows carried a token read by *nothing* (one missing
`u`), and 29 queries marked **more than one** anchor where §2 above told you "exactly ONE".

**Your reading was right; the instruction was wrong.** A query's expected answers are a **SET**:

* `pipeline/retrieval_benchmark.py::_recall_at_k` divides by **`len(expected)`** — every expected name must be
  retrieved, so a bigger expected set is a **STRICTER** ruler, never an easier one;
* `config/golden/retrieval_queries.yaml` stores `expected_names` as a **list**, and `pipeline/golden.py` resolves
  **every** entry.

"Exactly one" was the applier's own rule, written in two copies. Neither the format nor the harness ever had it.

**MEASURED (read-only, 2026-10-13, the same 29 queries):**

| ruler | production | fts | vector | hybrid |
|---|---|---|---|---|
| today's live set (29 queries × **1** anchor) | 1.000 · MRR 0.919 · P@k 0.100 | 0.655 | 0.862 | 0.931 |
| your review read as a SET (29 × **120** anchors) | 1.000 · MRR 0.954 · P@k 0.414 | **0.408** | **0.694** | **0.712** |

Your marks turn three legs that all looked "fine" (0.655 / 0.862 / 0.931) into a ranking that **separates** them —
the instrument T-101 said was missing. What it does **not** do: `production` stays at 1.000, because the candidates
you judged were drawn from the production leg's own top-5, and a leg scored on its own pool cannot lose.
Desaturating `production` needs a POOLED candidate list and harder queries (T-116), not more anchors.

**THE ONE WORD THAT BLOCKS THE WRITE:**

* **`set`** — your marks are a coverage judgement: every anchored candidate is a correct answer, and recall is
  measured over the whole set. This is the reading that produces the table above. **Recommended.**
* **`single`** — you meant exactly one correct answer per query and the other anchors were merely plausible. Then
  the marked rows are not a set, and I need a **rank per query** (30 cells), because no model may pick your anchor
  (D-2898).

**What was NOT touched:** your `anchor` column, and the mode. `reanchor.anchor_mode` ships as `single` (unchanged
behaviour); under it the applier REFUSES the sheet and names the one-line config edit that licenses the other
reading. Fixed without your involvement: the 19 `ambigouos` cells (a misspelling — the checker now *suggests*
`ambiguous` and still refuses to apply it; md5 cc68ae64… → 7cf7f66f…, 19 lines, one character each).

After your word: `python3 scripts/reanchor_retrieval_goldens.py --check` (must be clean) → `--apply` (C13 backup,
then the write, `version: 5`) → `python3 pipeline/retrieval_benchmark.py`.

---

## 7. WHAT WAS WRONG WITH THE SHEET YOU WERE GIVEN (recorded so it is not repeated)

* **The `old_name` column described a golden set that no longer existed.** `old_name`/`old_fb_id` are looked up at
  GENERATION time, and this sheet was generated BEFORE the `20261011T221956Z` apply — which then changed the
  expectation of most queries. MEASURED: **30 of 30** `old_name` values are ABSENT from their own candidate list,
  while **30 of 30** live expectations are PRESENT. §2 told you to anchor "the row whose `cand_name` equals
  `old_name`": that row existed for **zero** queries. Filed as **BUG-771**.
* **The `ambiguous` rule was declared and never enforced.** §0 above said `ambiguous` "PARKS the query and BLOCKS
  the apply"; the code consulted it only when a query had **no** anchor. The rule §0 states is now SUPERSEDED by
  the precise one: an abstention excludes **that candidate** and is counted; a query with **no** anchor at all
  parks and blocks. `config/pipeline_config.yaml` carries the same words, and `--selftest` proves both arms.
