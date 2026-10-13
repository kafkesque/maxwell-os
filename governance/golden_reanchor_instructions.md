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
