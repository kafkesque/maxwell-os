# HANDOFF 2026-10-25 — THE REGISTER STOPPED OVER-REPORTING (BUG-481), AND ITS TOP OF QUEUE WAS PHANTOM

**C15 POINTER (required while ≥5 bugs are open):** `governance/buglog.md` is the ONE home; the live census is
`governance/bug_status.json` (**244 open / 521 closed of 765**; DIVERGENT 0). Never quote a count from this file —
re-derive: `python3 scripts/bug_status.py`.

## 1. WHAT WAS FOUND (measured, before any edit)

The session opened by re-deriving the declared "next critical step" instead of trusting it, and every one of the
three orderings in play was stale in the same direction — *work that was already done still looked owed*.

1. **The handoff of 2026-10-23 named "the 4 open CRITICAL bugs" as the #1 agent-executable item. All four are
   closed** (BUG-709 CLOSED, 710 CLOSED 2026-10-13, 712 CLOSED 2026-10-24, 713 RESOLVED 2026-10-12).
2. **T-187 — the instrument every model decision was said to wait for — is `state: done`** (`config/task_register.yaml`,
   closed 2026-10-19; the two-step fixture landed; promotion made by D-3104). Yet FIVE rows in
   `governance/NOT-YET-EVALUATED-RESEARCH.md` still gate a candidate "on T-187", i.e. on a referent that no longer
   exists (D-3034).
3. **The register's severity axis — the one T-104/D-2985 exists to make ORDERABLE, and the axis used to answer
   "which is highest leverage" — ranked THREE ids CRITICAL, and two of the three were phantom:** BUG-299 and
   BUG-305 both declare their own resolution in the BODY, and BUG-297's entire substance is BUG-299's. Remedies
   verified to have LANDED: `pipeline/serving_gate.derive_status` consumed by `verify_record.py:267` and
   `stage6_commit.py`, the four illegal status writers measured at ZERO status writes; `definition_nli_verify.py`
   carrying D-284 arm C and `_r5_hash()`, with BUG-307 RESOLVED. **The top of the queue was phantom.**

The class was already registered — **BUG-481 (MED, 2026-09-25)** — with EIGHT instances. Those eight had been
reconciled by later headers and **SEVEN NEW ones had silently accumulated in their place**. So the class had been
noticed, fixed *by example*, and never *guarded*.

## 2. WHAT LANDED

1. **The probe** (`scripts/bug_status.py#divergent_statement`): an OPEN bug whose own last paragraph CLAIMS a
   closure is DIVERGENT — reported with id, body line and claim in `bug_status.json#divergent` and on the face.
   Narrow by measurement: a line must LEAD with the verdict AND carry its evidence (date / decision paren /
   terminator), or be an explicit `Status:` field. The two LIVE false positives a looser probe produced are
   known-answer controls (`CLOSED, so any consumer …` = BUG-314; `CLOSED probe vocabulary` = BUG-773).
   **43 controls** fire (`python3 scripts/bug_status.py --selftest`).
2. **The guard** (`config/gov_sync.yaml#bug_divergence_grandfathered: 0`, enforced by
   `scripts/gov_sync.py#divergence_ceiling_faults`): SHRINK-ONLY (D-2644), PURE, two-sided, and it names the ids
   over the ceiling. A new mutation entry `the_divergence_ceiling_may_stop_binding` REDs its oracle — the mutation
   gate ran **64 rules SEEN to red, 1 negative control green**.
3. **The reconciliations** (status EVENTS in `governance/buglog.md`, each naming its own reading): BUG-297, 299,
   300, 301, 302, 305, 394, 628. Register **253 open → 245**, and the severity axis **CRITICAL 3 → 0**
   (now CRITICAL 0 · HIGH 35 · MED 79 · LOW 31 · UNLABELLED 99 = 244).
4. **An ADJUDICATION, not a closure:** BUG-263's body says `**Status: FIXED** (code)` AND "Run artifact pending",
   so OPEN is CORRECT. The code half was verified (`config/pipeline_config.yaml:484` declares
   `relabel_judge_max_tokens: 1024`); the 200-record cross-family pass is still owed.
5. **The dangling gate replaced:** `config/task_register.yaml#T-199` — the LOOP BATTERY (distractor, parallel-call
   formatting, argument-NAME trap, enum-argument trap), the thing that RANKS where one fixture only ADMITS. A
   dated correction row in `NOT-YET-EVALUATED-RESEARCH.md` points the five "gated on T-187" rows at it. No verdict
   above is retracted; nothing is downloaded to run it (the served roster is the first population, 0 GB).
6. **D-3146** minted (1272 decisions): five clauses, one accepted negative, four honest limits. `gov_sync` reads
   **4 faces equal** (1272 decisions / 765 bugs / 56 open tasks).

## 3. HIDDEN CONFLICTS FOUND, AND HOW EACH WAS CLOSED

1. **A third state would have released a frozen bug.** Removing a divergent id from `open` would silently free an
   obligation in `config/freeze_window.yaml` (which reads this register) and would red
   `scripts/check_bug_recall.py`, whose agreement join compares its own fold against `open_n`. **REFUSED** — the
   divergence is a QUALIFIER, recorded as an accepted negative with its reason (D-3038). This is the change in the
   design that the measurement forced, and the reason BUG-481's own "emit a divergent STATE" was amended.
2. **The probe was wrong first, and it hid a real case.** Version 1 required a body line to LEAD with the verdict;
   a grep for an explicit `Status:` field found BUG-263 at line 454 — the exact shape BUG-481's own strict probe
   used. The rule gained that shape in BOTH directions (`Status: OPEN` is not a closure) plus 4 controls. *A
   detector that cannot be shown to have missed something has not been tested.*
3. **R5 review (gemma-4-E4B, different family, journaled `DJ-20261025T133204Z-b846`) found 5 defects; 3 accepted,
   2 refuted with reasons.** Accepted: 4 natural verdict forms were missed (bullet / full stop / em dash / bold
   keyword + colon); a compound word after the field (`FIXED-LENGTH`) was a false positive; FIRST-match instead of
   LAST-word (so a body ending "still open" was falsely divergent) — now last-claim-wins with negation as a
   SUPPRESSOR, which also fixed a genuine false negative (`RESOLVED (was UNRESOLVED for 3 days)` had been
   suppressed by a whole-line substring test); and the ceiling's `named` slice claimed to know WHICH ids were new,
   which a COUNT cannot say — it now names the ids and faults if the count and the list ever disagree. Refuted: a
   per-record fence-state carry-in (the fence rule is COPIED from `scan()` on purpose, one fence rule for one file,
   and `FENCE_RE` forbids leading whitespace so an indented block cannot toggle); and a case-sensitivity worry
   about `rec["status"] != "open"` (the fold emits lowercase literals only).
4. **Two tripwires are now at ZERO headroom, deliberately, and must not be "fixed" by raising a ceiling:**
   `severity_grandfathered: 99` and `bug_divergence_grandfathered: 0`. Together they ARE T-104's claimed but
   never-existing enforcement: a new `## BUG-n` heading with no severity token, or a closure recorded only in a
   body, now makes `gov_sync --check` RED and NAMES the id. A ceiling may only be LOWERED (D-2644).
5. **One loophole is recorded, not hidden:** a divergence is computed over the LAST body, so appending a header
   re-frames it. That is legitimate only if the new body ANSWERS the claim (D-3146 clause 5 — BUG-263 is the
   worked example: confirmed, not overruled), and it is not mechanically prevented.

## 4. NEXT CRITICAL STEPS (strategic-leverage order)

1. **T-199 the LOOP BATTERY** — the gate that replaced a closed task. It settles R-14/R-15 and any candidate at
   0 GB, and it is the ONLY thing that can promote `AGENT_LOOP_FAST` / `AGENT_LOOP_WORKHORSE` (D-3058).
2. **BUG-263's owed receipt** — the 200-record cross-family pass. The code is landed and verified; without the
   receipt "zero disagreements" is still unreadable as a result.
3. **T-104's remaining half** — 99 open ids still carry no severity. Backfill is OWNER-GATED judgement (severity is
   a claim), and it is the only thing standing between the register's ordering axis and completeness.
4. **T-101 / T-116** — the retrieval gate is still SATURATED (recall@10 = 1.000), so no RAG change can be proven an
   improvement; T-116 is the instrument that ADDS harder goldens.
5. **BUG-1001** (still OPEN, LOW) — `guard_stacks_single_source.py` turns "my probe could not run" into "service is
   down". One declared home, cheap, and the same class this session spent its time on: *an instrument may not
   report a fact about the world when what failed was the instrument.*
