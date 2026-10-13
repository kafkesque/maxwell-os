# SESSION HANDOFF — 2026-10-13 — D-2987: A STATE IS A CLAIM (BUG-765 FIXED, T-101's instructions repaired)

> Previous act: `governance/SESSION-HANDOFF-20261013-D2986.md` (D-2986 — a HEADING is a claim).
> This act closes the fourth of four claim surfaces and repairs the INSTRUCTIONS the owner was given.

---

## 1. THE LEVERAGE CALL

The owner's standing rule is *go forward on the strategically most consequential, highest-leverage item*. The
answer was **not** the top of the pipeline lane (T-104/BUG-757) — it was **the owner lane itself**.

MEASURED before this act: **three owner-gated items** (T-101 MUST, T-103 MUST, T-107 SHOULD) and the owner could
not act on two of them unambiguously. The pipeline has ten items it can advance alone; the binding constraint is
the owner's hand, and this is the **fourth consecutive act** whose subject was a front-facing surface that
misled the person reading it:

| act | the surface that was lying |
|---|---|
| D-2984 | the ROWS and prose BELOW the history marker |
| D-2985 | the LIVE region ABOVE it |
| D-2986 | the HEADINGS between them |
| **D-2987** | **the STATES those surfaces name** — and the instructions the owner acts on |

So the call was to stop repairing individual lies and give the face **a declared vocabulary** and **a declared
sign**, then let rails hold both.

---

## 2. WHAT WAS MEASURED (before → after)

| thing | before | after |
|---|---|---|
| the DERIVED decisions line | **981 of 1114** — 133 decisions unaccounted | 67 + 698 + 349 + 0 = **1114** |
| the state `ratified` | declared NOWHERE, printed NOWHERE | declared, signed `⚖`, bucketed |
| signs in the DERIVED block (the authority) | **zero** | task priorities, 14 decision states, 4 severities, rules |
| the owner's review vocabulary | `keep/replace/drop/add` in TWO handoffs — accepted NOWHERE | `anchor/rewrite-query/retire-query/ambiguous`, in config, in plain English, pre-flighted |
| `owner_signature` (D-2939) | written by the generator, read by **NOTHING** | enforced on the write |
| `gov_sync.py --selftest` | 19 known answers | **21** |
| `check_governance_faces.py --selftest` | 38 controls | **44** |
| mutation locks | 38 rules + 1 negative control (floor 39) | **40 + 1 (floor 41)**, both new ones SEEN red |
| `tests/test_governance_faces_spec.py` | 15 green | **17 green** |
| open tasks | 13 | 14 (T-116 — the measured GAP in T-101's infrastructure) |

---

## 3. RULE → MECHANISM → SEEN-TO-FAIL

| rule | mechanism | seen to fail |
|---|---|---|
| every DECLARED state carries a sign, and the authority renders it | `state_glyphs` (config/gov_sync.yaml) + `_cell()` in the renderer + `glyph_faults` (2 limbs) | ✅ both directions; the PRESENCE limb reddened all 3 faces until `--apply`; mutation lock `the_state_sign_completeness_limb_is_load_bearing` |
| the declared decision buckets PARTITION the register | 4 bucket lists in config + `partition_faults` | ✅ **SEEN to red on the PRE-D-2987 config** — *"the census counts ['abandoned','active','archived','ratified','rejected','resolved','revoked','stale','superseded'] (1047 decision(s)) but NO declared bucket holds them"*; mutation lock `the_state_partition_limb_is_load_bearing` |
| the review vocabulary has ONE home and is enforced | `retrieval_benchmark.reanchor.decisions` in config + fail-closed read + `--check` pre-flight | ✅ `--check` rc=1 on the unfilled sheet, naming the vocabulary and the out-of-phase query |
| anchors are OWNER-SIGNED (D-2939) | `owner_signature_required` + a refusal on the write | ✅ the refusal path is the same guard that already fails closed on an unresolvable name |

---

## 4. THE DEFECT THE RAIL FOUND ON ITS FIRST RUN (BUG-765)

The sign limb was written to answer *"does the authority render the signs it declares?"* Its completeness limb
reddened on six census keys the new map did not cover. **Five were not states at all** (`total`, `by_category`) —
a fault of the RULE, repaired by sourcing the required set from the DECLARED axes instead of the census's keys
(the D-2986 lesson, applied instead of re-learned). **The sixth was `ratified` — and it was not a fault of the
rule.** 133 decisions, 12% of the register, in a state that no artifact under governance declared, printed,
signed, or defined against `active`. The line printed its own total two words earlier.

**A state with no sign is a state the face does not show.** This is BUG-757's shape on the decisions axis, and it
was found by a control rather than by reading — which is the whole argument for the control.

---

## 5. THE T-101 INSTRUCTION DEFECT (the owner's actual question)

The owner said, plainly: *"T101 instruction are not clear and confusing. I asked precisely to give clear fucking
instruction what keep/replace/drop means in this context."* **He was right, and the instructions were wrong.**

`keep` / `replace` / `drop` / `add` are accepted **nowhere**. The applier reads
`anchor` / `rewrite-query` / `retire-query` / `ambiguous`, and that vocabulary existed **only as a Python tuple
inside the reader**. TWO consecutive handoffs (D-2985, D-2986) restated the wrong tokens — the classic
BUG-588/D-2692 shape: *a value restated in prose drifts the moment it is written.*

Repaired at the root, not in the prose:
* the vocabulary moved to **one home** (`config/pipeline_config.yaml`);
* the applier **fails closed** without it;
* a **`--check` PRE-FLIGHT** reports what `--apply` would refuse **before** the sitting is spent;
* **`governance/golden_reanchor_instructions.md`** states the four tokens in plain English, with a worked example
  and the fact the owner writes **30 cells, not 150**.

Two further measured defects in the same infrastructure: D-2939's "no model may sign an anchor" had **no control**
(BUG-492) — the `owner_signature` column was written and read by nothing; and the candidate draft is out of phase
with the live set by one deliberately-retired query, so `--check` now warns that anchoring it would silently
**ADD** it back.

---

## 6. FORENSIC AUDIT (done BEFORE any write)

* **Every parser of the derived block was read first.** `DEC_ROW_RE` and `BUG_ROW_RE` require the id to be the
  **first** cell after `|`; `BARE_STATE_RE` requires a decision row's state cell to stay a **bare** declared word
  below the marker; `LIVE_CENSUS_RE` parses the `Register truth:` line under a strict shape. Consequence, decided
  from the code and not from taste: **no sign may be placed before an id, and no sign enters a decision row's state
  cell.** The signs went where nothing parses them — the lane cells, the summary lines, the bug list, the boot face.
* **Encoding:** every read/write in `gov_sync.py` and `check_governance_faces.py` is explicit `encoding="utf-8"`,
  so the signs are byte-safe in a **byte-compared** block (`--check` re-derives and compares).
* **Bloat (C28):** the first version printed three always-zero states every run into a file a boot-loaded face
  carries into EVERY session. Now a zero-valued state is suppressed and an empty bucket prints nothing — the axis
  stays DECLARED and `partition_faults` still holds it, so nothing is lost but nine tokens per face.
* **One home, no second copy:** `open_decision_states` was already the declaration for "needs action", so the other
  three lists were added as its siblings — **no list is duplicated**, and no separate sum check was added because a
  complete partition makes the sum exact by construction (a second check would be a second home, D-2642).
* **Nothing deleted (R-D410):** BUG-765's OPEN-tier row was **re-tiered** into the CLOSED index as a bullet and its
  resolution **appended** to its own section.
* **Self-inflicted error, caught by a rail:** the first BUG-765 heading carried **both** `FILED` and `FIXED` in the
  authoritative leading parenthetical, and `scripts/bug_status.py` read it as CLOSED while the OPEN-tier row named
  it — `check_buglog_tiers` reddened. Repaired by saying ONE thing in the slot that IS the state.
* **The mutation gate was run in full**, and the two new locks are both in the SEEN-to-red list.

---

## 7. RESIDUALS — DECLARED, NOT DECIDED

1. **Is `ratified` a distinct live state, or a synonym of `active`?** An **ontology** question for the owner. This
   act made the state visible and gave it its own sign; it did **not** merge two domain states (D-2898 — merging
   states is a claim about the domain). One line in `config/gov_sync.yaml` if the owner rules they collapse.
2. **The bug axes have no buckets.** `state_tokens` and `severity_tokens` are declared; their partition is not.
3. **Three census states have no WRITER** (`stale`, `revoked`, `abandoned`, all 0) — a declaration without a
   producer.
4. **T-101's real goal still has no instrument.** The sheet RE-anchors the existing queries; it cannot ADD one.
   Filed as **T-116** rather than implied away.
5. **The sign map is a naming convention the rail can check for COMPLETENESS, not for TASTE.** It enforces that
   every declared state has *a* sign; it cannot know the sign is the *right* one.

---

## 8. THE OWNER LANE — what only YOU can move

**T-101 (MUST) — the instructions are now clear; the work is unchanged.**
* **The file:** `governance/golden_reanchor_candidates_20261011.csv`
* **The instructions:** `governance/golden_reanchor_instructions.md` ← *read this, not any handoff*
* **The vocabulary:** `anchor` on ONE row per query (the row whose `cand_name` is the right answer) + your
  signature on that row. **30 cells, not 150.** Leave the other four rows of each query blank.
* **Before you apply:** `python3 scripts/reanchor_retrieval_goldens.py --check` (writes nothing)
* **Success signal:** `recall@10` drops **below 1.000**.

**T-103 (MUST) — one word:** may the label re-derivation be **written to the store**? (*Gate: the owner word that
licenses the store write.*) 457 rows at a 6.9% claim gap, split four ways with each queue's cause named in
`governance/buglog.md`'s BUG-749 record. Nothing else is waiting on an answer this cheap.

**T-107 (SHOULD) — one decision: does the MCP payload keep advertising the two dead fields?**
**VERIFIED, not assumed** — measured on the served canonical run over 4,503 PASS rows:
`borp_score` = a constant 0.0 (one non-null value, one distinct); `feedback_score` = populated on **ZERO** rows;
`confidence_score` = 147 distinct (0.7522..1.0) and is the **only live one**. So the spec's own note ("retired/
derived fields") **understates it**: both are dead, and `feedback_score` is not "derived" — it is EMPTY.
*Recommendation:* **drop `borp_score` from the payload; drop or explicitly null-and-document `feedback_score`;
keep `confidence_score`.** It needs a spec bump on `specs/retrieval_serving.spec.md` (INV-7's surface), which is
why it is a one-word gate and not an edit.

---

## 9. NEXT CRITICAL STEPS, IN ORDER

1. **T-104 / BUG-757** — the severity backfill: 101 open bugs carry no severity token, so the register cannot be
   ordered by criticality (**101 UNLABELLED of 184 open**). Note this act measured the SAME shape on the
   decisions axis and fixed it there — the bug axis is the remaining half.
2. **T-116** — the instrument that ADDS goldens (T-101's real objective).
3. **T-114** — the ladder faults, each shrink-only ceiling LOWERED per wave (D-2644).
4. **T-105 / T-106 / T-108**, then **T-112 / T-113 / T-109 / T-110 / T-111**.
5. **T-101** remains the ONE unblocker that needs the owner's hand — now with instructions that match the machine.

---

## 10. DELEGATION & R5

No ad-hoc delegate was used: the act is ONE rule with two limbs whose writers are the same two files the rails
own, and splitting it would have created **two writers of one rule** (the D-2984 lesson). The ratified local-LLM
call is the R5 gate on the changed rails.
