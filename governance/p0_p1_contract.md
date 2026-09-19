# P0 + P1 execution contract — FROZEN BEFORE WORK STARTS

**Written:** 2026-09-17 10:37 · **Status:** binding · **Change rule:** see §7

This file exists because of a specific failure: benchmark runs repeatedly spent hours of
model time and produced numbers that were then retracted (BUG-257, 258, 259, 260, 262,
263, OptiQ). The failure was never a model. It was that the harness **scored its own
breakage as a model result**, and "done" was declared from a **log line** instead of an
**artifact**. Neither is fixable by promising to be careful. Both are fixable by gating.

---

## 0. Why there was no preflight (root cause, stated once)

The repo *did* have preflight culture for the pipeline: `scripts/pre_s6_gate.py`,
`scripts/pre_commit_gate.py`, `scripts/preflight_checkpoint_check.py`, `tools/delegate_safe.py`.
The **benchmark harness had no equivalent.** `tools/model_eval_suite.py` sends a request,
reads the response, and if the response is ungradable it records a *wrong answer*. So:

| incident | what the harness saw | what it actually was | cost |
|---|---|---|---|
| BUG-262 | gpt-oss toolcalling 0.00 | reasoning-off prefix missing -> 20/20 "no json" | role wrongly flipped |
| BUG-263 | S2 relabel labelled nothing | `max_tokens=64` vs a Harmony reasoning model | silent no-op, unbounded |
| BUG-257 | niah 0.00 at ctx 32000 | HTTP 400 chat-template ceiling | whole tier misread |
| BUG-258 | REAP toolcalling 0.50 | transport errors counted as wrong answers | report wrong |
| BUG-259 | pruned models in decision table | no registry check | decisions on ghosts |
| BUG-260 | S4 discipline ~0.20 | raw label vs canonical gold | headline wrong |
| OptiQ | 31% "no json" | reasoning-first model vs `max_tokens=512` | 20.68 GB + hours |

**The single missing check:** *can this (model, suite) cell return a gradable answer at the
exact budget the suite will send?* That check is now `tools/bench_preflight.py`.

---

## 1. The three mechanisms (M1 / M2 / M3)

**M1 — Preflight gate.** `tools/bench_preflight.py` + `config/bench_preflight.yaml`.
Runs the REAL harness `call()` with the REAL per-item `max_tokens` for every (model, suite)
cell **before** scoring. Classifies each cell VALID / NO_CONTENT / NO_JSON / CTX_CEILING /
TIMEOUT / HTTP_ERROR / SUITE_BUILD_FAILED. Env checks: oMLX reachable, registry equals the
expected portfolio (catches ghosts), disk floor (catches BUG-261), and **no concurrent
benchmark** (an oMLX reload evicts the resident model — BUG-255). Writes a fingerprinted
artifact. Exit 0 / 1 / 2.

**M2 — Artifact-based "done".** No step may be reported complete from stdout. Each step
must produce a machine-readable artifact (`.json` / `.jsonl`) and a row count, and
`scripts/audit_final_chain.py` re-derives the count from the file. `run_final_chain.sh` has
no `set -e` and printed *"done in 0s, 0 new results"* both for a legitimate no-op and for a
silent crash — so log lines are explicitly inadmissible as evidence.

**M3 — This contract.** Acceptance criteria and adjudication rules fixed *before* the run.
The point is that a stall, a crash, or an ambiguous result cannot later be narrated into a
finding.

---

## 2. Binding invariants

1. **NA, never zero.** A cell that fails preflight is *Not Applicable*. It is excluded from
   every average, and it can never be the basis for assigning or removing a role.
2. **No artefact, no claim.** Every statement about a model carries a path + a row count.
   Prose without an artefact is not a result.
3. **Budget honesty.** Any LLM call whose consumer parses JSON asserts non-empty content
   per call (C16). A hardcoded token budget inside a loop is a defect (C12/C20) — budgets
   come from config.
4. **R5 / C8.** Generator != Verifier by FAMILY. New verification scripts are reviewed by a
   different family before `--apply`.
5. **Comparability.** Two numbers may only be compared if their preflight fingerprints
   match. Otherwise the comparison is void.

---

## 3. P0 — Fix BUG-263 (S2 cross-family relabel), acceptance criteria

Defect: `pipeline/stage2_relabel_extraction_type.py:165` sends `max_tokens=64`. gpt-oss is a
Harmony reasoning model: it emits a reasoning pass first and returns **0 content** until the
budget is large enough (measured: 64 -> content 0c; 256 -> 0c; 1024 -> 29-42c JSON). So
`_judge()` has been labelling **nothing**, silently, for every record.

P0 is DONE only when **all** of these exist:

- [ ] `max_tokens` for the judge is read from config (`stage2.relabel_judge_max_tokens`),
      value >= 1024, with the measured reason recorded next to it.
- [ ] `_judge()` asserts non-empty content and raises (C16) instead of returning an empty
      label; the error names the budget so the next reader does not re-diagnose it.
- [ ] A probe artifact shows, for gpt-oss, content length and JSON parseability at the new
      budget — before/after, same prompt.
- [ ] A relabel run over ~200 FBs produces `governance/`-resident artifact with a row count,
      and the before/after `extraction_type` distribution (the ~60% vs ~11% drift claim).
- [ ] `scripts/audit_final_chain.py` (or a sibling) exits 0 having checked the artifact, not
      the log.
- [ ] Independent review by a different family (gemma-4-E4B) recorded in the buglog entry.

**Pre-committed adjudication:** if the relabel still returns empty labels at >=1024, the
finding is *"gpt-oss cannot perform this judge under the current chat template"* and the
role moves to the next eligible family — it is **not** "S2 relabel works, results pending".

---

## 4. P1 — Tool-calling and planning roles, acceptance criteria

P1 is DONE only when all of these exist:

- [ ] Preflight artifact where the `toolcalling` and `planning` cells are **VALID** for each
      model that will be ranked. Any model whose cell is NA is excluded from the ranking and
      named in the report as NA (currently gpt-oss toolcalling is NA pending BUG-262 re-measure).
- [ ] Tool-calling ranking over the 20 realised items; planning over the 24 items
      (3 original + 21 computed by `tools/plan_cases_generated.py`).
- [ ] Every planning item's gold answer is **computed at build time**, not asserted by hand.
      The 17 hand-written items deleted on 2026-09-16 stay deleted; their rows stay in
      `INVALID_ITEM_IDS`.
- [ ] Role assignment written into `governance/consolidation_drafts_20260916/02_model_assignments.yaml.draft`
      with `evidence:` naming the artifact and n.
- [ ] `scripts/validate_role_claims.py` exits 0 for both roles.

**Pre-committed adjudication:**
- Tie within 1 item on n=20/24 -> **incumbent keeps the role**, no swap, and the tie is
  recorded. A 4.8x latency difference is not evidence of quality, but it is evidence for
  cost, and cost breaks a dead tie.
- Any cell that is NA cannot win and cannot lose.
- A model that wins on a suite whose gold answers are suspect has won nothing.

---

## 5. P2 — Freeze gate (only after P0 + P1)

The three config files may be frozen only when `scripts/validate_role_claims.py` reports
**0 uncited roles**, or every remaining uncited role is explicitly stamped `UNVERIFIED` in
the draft. Stamping is allowed; implying measurement is not. Gate evidence = validator
output + the frozen file hashes.

---

## 6. Waste ledger (what the missing gate cost, so this is not abstract)

- OptiQ A/B: 128 voting rows, 40 "no json" (31%), 20.68 GB of weights, 75.9 s/row — retired.
- Planning suite: 119 poisoned rows across 7 models, 13/17 items failed by *every* model.
- BUG-262: a whole tool-calling suite (n=20 x models) invalidated by one missing prefix.
- BUG-263: an unbounded silent no-op — the expensive kind, because it fails quietly.
- BUG-261: near-miss disk fill to **1.7 GiB free** during a 19 GB reclaim.
- Repeated full-chain reruns. Total: hours of wall clock and most of a day of model time.

Every one of those is caught by M1 in under a minute, before a single scored row.

---

## 7. How the no-drift guarantee is enforced (the honest answer)

I cannot promise a language model will not drift. What I can do is make drift
**mechanically unable to pass as done**:

1. **The gate runs first and exits non-zero.** `python3 tools/bench_preflight.py` before any
   scored run. Exit 1/2 => the run does not start. Non-negotiable, and it is a *program*,
   not a promise.
2. **Acceptance criteria are frozen in §3/§4 of this file, timestamped, before execution.**
   Loosening one requires an explicit written amendment in §8 with the reason — visible,
   not implicit.
3. **Done = artifact + count, re-derived by an audit script.** Never a log line, never my
   summary. If the audit exits non-zero, the work is not done regardless of how it reads.
4. **Adjudication is pre-committed per task** (§3, §4), so an ambiguous outcome has a
   written answer that was fixed in advance.
5. **Independent family review (R5/C8).** A different model family reviews the new code and
   the result before the role is frozen. My own confidence is not evidence.
6. **Kill criteria.** Timebox per task; on expiry I stop and report the *blocker with its
   artefact*, rather than continuing to spend model time to preserve the appearance of
   progress.
7. **One oMLX client at a time** (single resident model, BUG-255). Parallel benchmark work
   is forbidden; it corrupts timings and can silently evict a model mid-run.

---

## 8. Amendments

| date | section | change | reason | who |
|---|---|---|---|---|
| — | — | none yet | — | — |

---

*Amendment log is append-only. An empty amendment table after P0/P1 means the criteria were
met as originally written — which is the whole point of writing them down first.*
