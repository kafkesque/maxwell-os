# SESSION HANDOFF — D-2989 / T-107: the BORP archaeology, and the rail that turns one owner word into a config edit

**Date:** 2026-10-13 · **Commit:** (this act) · **Authority:** D-2989 · **Owner question:** the T-107 challenge

## 1. The leverage call

The owner re-opened T-107 with a demand, not a preference: *"what were the original concept behind BORP and lead for
drop besides there are no current infrastructure/logic behind it? DONT drop till I dont clear explanation and if it
can be revitalized with real scoring logic and feedback score keep how will exactly works and how will it be scored
how will the logic will look like."* That makes the answer itself the highest-leverage act: it is the only gate in the
OWNER LANE that a measurement can settle, and the measurement CHANGED THE RECOMMENDATION. So the act is: (a) recover
the concept from the repo's own history rather than from memory, (b) measure both fields, (c) answer the
revitalization question with the code that already exists, and (d) build the rail that makes the owner's one word a
config edit instead of a code decision.

## 2. What the archaeology found (the answer to the challenge)

| question | answer | evidence |
|---|---|---|
| what was BORP? | the **Book of Record Principle** — "≥2 independent sources for convergence" | `governance/master_evaluation_prompt.md:36` |
| how was it implemented? | `check_borp(fb)`: `distinct = len(set(source_books))`; `score = min(distinct / BORP_MIN_SOURCES, 1.0)`; `passed = distinct >= BORP_MIN_SOURCES` | `git show c95f7ff:pipeline/stage5_verify.py:105-115` |
| was it ever a score? | **NO.** The pass bar IS the denominator floor, so on the admitted population the ratio is exactly 1.0 — a boolean wearing a ratio's name | the formula itself (a proof, not a preference) |
| why is the stored value 0.0 then? | the check's score never reached the row: `pipeline/stage6_commit.py:910` default-injects `fb.get("borp_score", 0.0)` | measured: non-null `0.0` on 7,640/7,640 rows, 1 distinct |
| what KILLED it? | (i) the producer was DELETED at S5 ("BORP guarantee now provided by S1.5"), (ii) the ranking repair D-2979/D-2980 repointed its last live reader | `pipeline/stage5_verify.py:20`, `:554`; `config/pipeline_config.yaml#ranking` |
| the lead for the drop, besides "no infrastructure"? | the formula was information-free **before** it was unpopulated — and the stored `0.0` is a FALSE ABSENCE that **SQL reads as a value and Python reads as absence inside ONE function** | measured: `sqlite3 → 0.0`, `python → 0.5` on the same field |
| can it be revitalized with real logic? | **YES — and it already exists.** ISOR (D2284, canonicalized D2309 over the D2185 `source_ids`) measures INDEPENDENCE: author independence × domain diversity × source count → `score` + `strong/medium/weak`; persisted on 6,591 rows and advertised by NOTHING | `pipeline/schema_accessor.py::isor_score`; ratings weak 5,212 / medium 969 / strong 410 |
| and the principle itself? | **alive and UNDER-SERVED.** `is_convergent=1` is EXACTLY the ≥2-source set (1,393 rows); the SERVED population satisfies BORP on **938 of 4,503 rows = 20.8%**, and 5,198 of 6,591 verified rows carry ONE source — because the deleted per-row check was replaced by a gate only the CLUSTER route passes, leaving the SINGLETON route unguarded | the status × is_convergent × source_ids table in `governance/BORP_FEEDBACK_ASSESSMENT_20261013.md` |

**The corrected recommendation (the first one was wrong, and the owner's challenge was right):** RETIRE `borp_score`
from every served surface and PROMOTE `corroboration` (the ISOR block) in its place; KEEP `feedback_score` — it is a
**cache** whose **ledger** (`fb_feedback`) and **writer** both exist, and its defect is that a bare `null` cannot be
told from a score of `0.0`, not that it is dead. Dropping it would have deleted the served contract for the one
primitive that lets the corpus learn from *use*.

## 3. What was built (all additive; no store write, no payload change)

| artifact | what it is |
|---|---|
| `config/served_fields.yaml` | the ONE home: the surfaces, the registers that own each column's truth, the three owner-word rows (`word` + `anchor` + `owed`), the two source-owned acknowledgements, a `promotions` block whose home must RESOLVE, and a **shrink-only ceiling** |
| `scripts/check_served_fields.py` | the rail: the advertisement read from each surface's AST and intersected with `PRAGMA table_info(fbs)`; the flags READ from `config/derivations.yaml` + `config/store_columns.yaml` (a JOIN, never a second census); both directions joined; **rc 2 = the owner word is owed**, rc 1 = an undeclared advert or a stale declaration; **10 known-answer controls** |
| `config/feedback.yaml` | the feedback loop's numeric policy (thresholds, prior, formula, rounding, the declared absence shape, the serving skew) — the C12 home the code never had |
| `pipeline/feedback.py` | `declared_aggregate()` = the formula's ONE home (imported by the writer AND the rail); thresholds read FAIL-CLOSED (no code default); absence stays NULL (D-2957); `get_fb_feedback_stats` reports the tri-state `measured`/`no_feedback`/`unmeasured` (C16 — a failed read was previously reported as a healthy FB) |
| `scripts/check_feedback_parity.py` | the ledger→cache parity rail `config/derivations.yaml` declared as `parity_rail: null` (D-2642); 6 controls, including an INDEPENDENT oracle and the config-drives-the-formula control |
| `specs/served_fields.spec.md` + `tests/test_served_fields_spec.py` | the paired contract, INV-1..INV-9, **16/16 green** |
| 3 mutation locks | the undeclared-advert guard, the owner-word vocabulary guard, the feedback-absence guard — all SEEN to red (floor 43 → 46) |
| `governance/BORP_FEEDBACK_ASSESSMENT_20261013.md` | the EVIDENCE (the answer to the owner, in full, with the reproducible measurements) |
| `governance/OWNER_DECISION_T107_20261013.md` | the SHEET: three rows, five enforced tokens, the exact commands, nothing else to write |

## 4. Forensic audit (before and with the act)

* **No store write**: the rail opens the store `mode=ro`, and the only write in the act is `_update_fb_aggregates`'s
  behaviour-preserving refactor (verified by the parity rail's fixture, not by inspection).
* **No payload change**: the MCP output is untouched — that is the owner's word (T-107) and the whole point of the
  debt ceiling.
* **Behaviour identity**: with `prior_weight: 0.0` the declared formula IS `round(mean, 3)` — the historical value,
  byte for byte — so no ranking semantics moved. The shrink is ONE config key away (C27: no future tax).
* **No hidden consumer break**: `RETIREMENT_THRESHOLD`/`RETIREMENT_MIN_FEEDBACKS`/`BOOST_THRESHOLD` had NO consumer
  outside `pipeline/feedback.py` (checked); the four importers of the module use `record_feedback`,
  `mark_fb_retrieved`, `get_fb_feedback_stats` — all signature-stable, the stats dict only GAINING keys.
* **No rival home**: the formula is imported by the rail, never copied (asserted in the paired contract by AST), and
  the flags are read from the registers rather than re-censused (asserted by construction — the rail never counts a
  column the registers already measure).
* **The declaration cannot become a second truth**: the ceiling is measured at birth (3 = the 3 declared rows) and
  the rail refuses a count above it, so a new dead advert is a DEFECT, not a ceiling change (D-2644).
* **Cascade absorbed**: `config/derivations.yaml#fbs.feedback_score` gained the `parity_rail` its row lacked;
  `specs/retrieval_serving.spec.md`'s residual now points at the new home; the justfile gained four lines; the
  registry pins the two new rails' guard classes; and `config/config_defaults_census.json` was re-recorded through
  its own rail (BUG-769, found by this act: the receipt's measured module count had NO re-record path, so the
  coverage changed the number the paired contract compares while the rail stayed green — fixed with a pure helper,
  a `--record` path, a 15th control and a 47th mutation lock).
* **Blindspot closed by measurement, not by argument**: the `string_mentions` surface kind immediately found TWO
  fields nobody had looked at (`application`, `jargon` — published as FB text while the shape register measures them
  partially blank). They are declared as SOURCE-owned rather than forced into the owner's lane, which is the point of
  splitting the disposition into owner-gated and source-owned.

## 5. Residuals (declared, not implied)

1. **The three owner words are PENDING** (T-107). The rail reports rc 2 — loud, not fatal.
2. **The serving prior is still a literal** in `pipeline/retrieve.py:1070,1071,1090,1091` (four places in ONE
   function). The change-set moves all four onto `config/feedback.yaml#serving.neutral_prior`.
3. **`isor` is advertised by no surface** — the promotion is the recommendation, not yet a fact.
4. **The single-source TIER question is the owner's** (T-118): with 79.2% of the served population non-convergent,
   what may the system SAY? `tier` | `withhold` | `leave`.
5. **The BUG axis still has no severity partition** (T-104/BUG-757) — the same defect D-2987 settled on the decisions
   axis, and the next critical step.

## 6. Delegation (honest account)

No ad-hoc delegate was used for implementation: the act's core is measurement and guarded file edits where a
delegate's context could not see the registers, the ladder or the mutation gate. The local-LLM layer that WAS used is
the R5 gate (`scripts/r5_review_gate.py`: deterministic syntax/lint/C11-C12 layers, then ONE advisory reviewer from a
different model family), whose receipt is `governance/r5_review_gate.jsonl` — the same disposition as D-2988.
