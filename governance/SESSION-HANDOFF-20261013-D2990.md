# SESSION HANDOFF — 2026-10-13 — D-2990 (BORP hardening) + D-2991 (an anchor is a SET)

> **Owner instruction (this act):** *"does BORP revitalization carry any risk, threat, can cause any cascade issue,
> leak, contamination, hidden error, failure issue (do we have any history with it previously) … revitalize but
> hardening (are there any existing similar proven grounded solution that can be adapted), or is it too risky or
> else"* + *"if your feedback score recommendation is reliable and futureproof (verifiable) I approve"* + the
> **T-101 reviewed sheet** attached + the standing rule (senior recommendation, infrastructure AND file for every
> manual task, forensic audit before any serious implementation, gov dependencies synched and updated).

## 1. The leverage call

Three things entered at once: a **risk question** about a decision I had recommended (BORP), an **approval**
(feedback_score), and an **artifact** (the owner's 150-cell golden review). The highest-leverage act was not to
re-argue: it was to **measure the owner's artifact**, because it failed for a reason nobody had declared — the
review was RIGHT and the tool was wrong — and that failure is the same class as the BORP failure (a rule that
lives in its reader instead of in a declared home).

## 2. What the owner asked, and what the measurement answered

**Q1 — does revitalizing BORP carry risk?** YES, and the risk is entirely in the two naive forms, not in the
principle. Measured on the canonical PASS population (N=4,503, read-only 2026-10-13):

| measurement | value |
|---|---|
| `isor` rating weak / medium / strong | 3,576 / 670 / 257 (populated on 4,503/4,503) |
| rows the COUNT certifies as corroborated (`is_convergent=1`) | 938 (20.8% of served rows) |
| …of those, rated **weak** by `isor` | 35 |
| …of those, **2+ sources but ONE AUTHOR** | 148 |
| …of those, **2+ sources but ONE DOMAIN** | 170 |

Worked row: *Chroma Subsampling in Jpeg Compression* — two source works, **both Rosa Menkman**, `isor` weak 0.5.
The count says CORROBORATED; independence says ONE VOICE. **So "revitalize BORP" cannot mean "restore the count" —
that would be a downgrade from the measure in hand.**

**The answer, in one line:** revitalize the PRINCIPLE with hardening — **declare the tier on the surface, never
gate the corpus; one measure (the one we have); harden and MEASURE the independence axis before advertising it.**
Restoring the score is HIGH risk and rejected (R1 tautology, R2 yield loss, R3 certifies the pattern it exists to
prevent, R4 absence/value leak); freezing the principle is LOW risk but leaves 79.2% of the served corpus unserved
and BUG-767 open. The three objects (principle / measure / surface) are the ontological fix that makes the choice
obvious: KEEP, KEEP-and-serve, RETIRE. Full register R1..R8 with in-repo history, the adapted precedents and the
hardening plan: `governance/BORP_REVITALIZATION_RISK_20261013.md`.

**Q2 — is the feedback_score recommendation reliable and futureproof?** It is now **verifiable**, which is why the
word could be granted: `pipeline/feedback.py::declared_aggregate` is the formula's ONE home (imported by the writer
AND by `scripts/check_feedback_parity.py`, 6/6 controls), the absence is NULL + count 0 (D-2957), the policy is
config (`config/feedback.yaml`), and a failed read reports `unmeasured` (C16). **GRANTED and landed as the owner
word** `keep-and-declare` in `config/served_fields.yaml` with its anchor; the rail now reports it as *written, not
yet landed* instead of *word pending*.

**Q3 — the attached sheet.** It was **refused** by the applier: **48 faults** (19 cells reading `ambigouos` — a
token read by nothing; 29 queries marking more than one `anchor`). MEASURED: the owner's marks are a **SET**, and
the tool's "exactly ONE" was a limit the ledger never had (`expected_names` is a list; `resolve_golden_anchors`
resolves every entry; `_recall_at_k` divides by `len(expected)`).

| ruler | production | fts | vector | hybrid |
|---|---|---|---|---|
| live set (29 × 1 anchor) | recall 1.000 · MRR 0.919 · P@k 0.100 | 0.655 | 0.862 | 0.931 |
| the review read as a SET (29 × 120 anchors) | 1.000 · MRR 0.954 · P@k 0.414 | **0.408** | **0.694** | **0.712** |

Three legs that all looked "fine" now **separate** — the instrument T-101 said was missing. **Stated, not
glossed:** `production` stays at 1.000 because the judged candidates came from production's OWN top-5; desaturating
production needs a pooled candidate list and harder queries (T-116), not more anchors.

## 3. What landed (each with its home; nothing promised)

* `scripts/reanchor_retrieval_goldens.py` — **`judge_review`**: ONE pure, store-free judgment, called by BOTH
  `--check` and `--apply` (the two copies that could disagree are gone — BUG-770); `--selftest` **11/11** controls;
  the store imports made **lazy** so the control is genuinely hermetic.
* `config/pipeline_config.yaml` — **`retrieval_benchmark.reanchor.anchor_mode: single | set`**, declared and read
  FAIL-CLOSED (an unknown mode refuses to start rather than guessing a golden set's semantics); the `ambiguous`
  comment now states the rule the code actually enforces (an abstention EXCLUDES a candidate and is COUNTED; a
  query with no anchor PARKS).
* `specs/retrieval_goldens.spec.md` INV-1..INV-10 + `tests/test_retrieval_goldens_spec.py` **21/21 green** — a write
  path that had NO spec, NO test and NO rail now has all three (D-2978).
* `justfile` + `config/rail_registry.yaml` — the selftest pinned `fatal` in the ladder, with the reason `--check`
  is NOT a ladder step (it needs a reviewed sheet).
* `governance/golden_reanchor_instructions.md` §6/§7 — the owner-facing sheet corrected: the revision, the
  recommended word, and what was wrong with the sheet itself (BUG-771).
* `governance/BORP_REVITALIZATION_RISK_20261013.md` — the risk answer + the hardening design + T-119's plan with
  its **falsifier**.
* `config/served_fields.yaml` — the granted `feedback_score` word; `promotions.corroboration.measured_gap` records
  the coarseness measurement next to the measure it indicts.
* `config/task_register.yaml` — T-101 re-gated to **one word** (`set | single`) with the measurement in
  `evidence`; **T-119** filed (the collapse delta).
* `governance/buglog.md` — **BUG-770** (the duplicated judgment — FIXED by this act) and **BUG-771** (the sheet's
  `old_name` column described a superseded golden state — OPEN, with the stamped-hash remedy).

## 4. Forensic audit (before the commit)

* **No store write, no payload change, no ranking change.** The MCP payload and the two exports are untouched: the
  borp_score change-set is ONE move and needs the owner's word (BUG-767, rail rc 2 = the owner lane, loud not
  fatal).
* **No silent normalisation.** The 19 `ambigouos` cells were normalised as a **misspelling** (md5
  `cc68ae64b7ca370c5251422e1a3b431c` → `7cf7f66fa28d31b2fe60d6dff574d947`, **19 lines, one character each**,
  recorded in the owner sheet §6); the `anchor` column and every signature are byte-untouched, and the applier
  REFUSES to guess a token (it suggests, then fails closed).
* **Cascade hunted and found once:** the YAML edit meant for the `reanchor` block first landed one level OUT (a
  stray `retrieval_benchmark.anchor_mode` key) — caught by the paired test within the act and moved into the block
  with 4-space indentation, verified by `yaml.safe_load` (`reanchor` now carries `anchor_mode`) and by
  `grep -n`.
* **Bug census caught stale:** the mint refused `BUG-770/BUG-771` because `governance/bug_status.json` is written by
  `scripts/bug_status.py`, not by `gov_sync.py` — re-run, 533 → **535** (188 open / 347 closed); then gov_sync rc=0
  (**1117 decisions / 535 bugs / 16 open tasks**).
* **Behaviour identity where it matters:** with `anchor_mode: single` (shipped) the applier's judgment on the
  owner's sheet is unchanged in KIND (it still refuses) and the ONLY behavioural change is that the pre-flight can
  no longer disagree with the writer.
* **Bloat check:** no new script beyond the spec/test; the new judgment REPLACED two copies; `--check` and `--apply`
  now share one printer.

## 5. Delegation

One delegate was used, for the one load-bearing EXTERNAL claim (read-only verification, per the routing rule that
open-ended research is not delegated to the local models): the three prior-art claims behind the hardening design.
It CONFIRMED the truth-discovery source-dependence line (Dong/Berti-Équille/Srivastava, PVLDB 2009 ×2) and W3C
PROV-O, and **corrected** the pooled-qrels claim: pooling approximates the recall denominator — "a single relevant
document saturates a metric" is our measured T-101 finding, NOT the literature's rationale. The correction was
kept in the document rather than smoothed over (D-2660: a citation is a claim at the moment of mint). The R5 gate
supplied the local-LLM review layer for the code.

## 6. Residuals (declared)

1. **The owner's word (blocking):** `set` | `single` for `anchor_mode`. `set` is recommended and the measurement
   above is the argument; `single` needs a rank per query (no model may pick an anchor, D-2898).
2. **T-107** still owes the `borp_score` word (`retire` + `promote corroboration`) and `classification_status`
   (`keep-and-repair`); until then the payload and exports keep publishing the fossil (BUG-767 OPEN).
3. **T-118** (the single-source tier: `tier` | `withhold` | `leave`) — unchanged, and now with the coarseness
   measurement behind it.
4. **BUG-771 OPEN**: the stale-premise rail (stamp the golden hash into the sheet; refuse a mismatched sheet).
5. **The self-referential candidate pool**: the review's candidates come from the production leg's own top-5, so
   production's recall cannot drop on a set built from them (T-116 + a pooled candidate list).
6. The `ratified`-vs-`active` ontology question from D-2987 remains the owner's, not this act's.

## 7. Next critical step (strategically consequential order)

1. **T-104 / BUG-757** — severity backfill: 101 of 188 open bugs carry NO severity token, so the register still
   cannot be ordered by criticality (the bug-axis half of the D-2987 partition defect). Top of the PIPELINE lane.
2. **BUG-771's fix** (small, self-contained, removes a ghost from the next owner sitting).
3. **BUG-766** — six population-shape drifts → reshape to TRUE NULL, then `--record`.
4. Then the owner lane in one batch: T-101 (`set|single`), T-107 (`retire`/`keep-and-repair`), T-118 (`tier`),
   T-117 (the 72-unit escalate sheet), and the `ratified` ruling.
