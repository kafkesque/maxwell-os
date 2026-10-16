---
name: diagnose-hard-bugs
purpose: Six-phase, gate-per-phase diagnosis that turns a hard or intermittent bug into a fixed, verified, logged resolution.
when_to_use: A named symptom that is wrong, throwing, failing or slow; an intermittent flake; a regression between two known-good states.
when_not_to_use: A proactive audit ("where are the bottlenecks?"); a question one message answers; an unconfirmed raw report (triage first); throwaway design exploration; anything with no nameable source of truth.
inputs: The symptom statement; the known-good and known-bad states if any; access to run the failing path.
outputs: One re-runnable RED->GREEN command (or a receipt); a minimised repro; a governance/buglog.md entry; a regression test; a cleanup receipt.
binding: ADAPTER-OWNED. This body names NO harness and NO provider. Invocation, routing and delegation live beside it in the adapter (config/agent_surface.yaml); a provider name inside SKILL.md is a review failure.
---

# diagnose-hard-bugs - phase gates, not a checklist

## Standing contract (holds in every phase)
- Evidence is a RECEIPT or a re-runnable COMMAND with pasted output - never prose. A claim with no receipt is a hypothesis, not a result.
- Scratch lives in `temp/` (auto-purged, 7d). Findings go to `governance/buglog.md` IMMEDIATELY on discovery - never deferred, never batched (Auto-Log Rule).
- Deletion only through `pipeline/safe_delete.py --reason "<why>"`; model-store bytes leave through `pipeline/model_store_sweep.py --apply --owner-word <D-id>` (D-3035).
- Config-first: every path, threshold, model id and magic number lives in `config/*.yaml` (C12/C20). A hardcoded value is a review failure.
- Bounded claims: once an instrument is invalidated (a re-run fails, the target moved, the cache is stale), every metric it produced is retired - quote no number from a dead instrument.
- Producer != verifier (R5): when the fix is code, the author and the verifying pass are different - a deterministic check, or a different model family.
- Exit-code grammar (BUG-457): 0 = the claim holds; 1 = declared and known-open (recorded, not silently green); 2 = cannot decide or the instrument is invalid -> fail closed, state no conclusion.

| Need | Repo machinery |
|---|---|
| scratch | `temp/` |
| findings | `governance/buglog.md` (immediate) |
| delete | `pipeline/safe_delete.py --reason "<why>"` / `pipeline/model_store_sweep.py` for weights |
| rails | `just health` / `just health-full` |
| config | `config/*.yaml` |
| where things live | `governance/CONTEXT_INDEX.md` |

## Phase 1 - Build the repro (GATE)
Deliverable: ONE named command, already run once, pasted with its output, that goes RED on THIS bug and GREEN when it is fixed. The loop must be fast (seconds), deterministic (same verdict every run), sharp (asserts the reported symptom, not "did not crash") and runnable without a human.

Gate into Phase 2: the command exists and its red output is pasted. If not, say so VERBATIM - "I cannot proceed: no named command exists yet that goes red on this bug. Phase 1 is a gate, so I will not form a theory. I need one of: (a) an existing failing command or receipt, (b) access to run the failing path, or (c) permission to add temporary instrumentation under temp/." - and stop. Do not enter Phase 2 on prose.
For an INTERMITTENT bug the target is a debuggable REPRODUCTION RATE: loop the trigger, parallelise, inject delays, until the flake rate is high enough to measure.

## Phase 2 - Minimise
Shrink the trigger until every remaining element is needed, and say why each survivor stays. Prefer a fixture or a saved artifact in `temp/` over the live corpus.
Gate into Phase 3: the repro reproduces AND is minimised.

## Phase 3 - Rank hypotheses
Write 3-5 ranked, FALSIFIABLE hypotheses. Each predicts: "if H holds, command X yields Y". Show the list before testing any of it. A hypothesis is never a result - label it a hypothesis everywhere, including in temp notes and the buglog draft.
Gate into Phase 4: the ranked list exists and is FROZEN before the first probe.

## Phase 4 - Instrument
One variable at a time. Every probe answers exactly one hypothesis's prediction. Tag every debug write (e.g. `[DEBUG-a4f2]`) so one grep finds them all. Probe output is a receipt in `temp/`, never a recollection.
Gate into Phase 5: at least one probe distinguishes a hypothesis BY A RECEIPT; the hypothesis survives or falls on that receipt, not on plausibility.

## Phase 5 - Fix, with a regression test
Write the regression test BEFORE the fix, with a correct seam: the test must exercise the bug as it occurs at the call site. If the only available seam is too shallow, say so and record the missing seam as a finding - never write a test that gives false confidence.
Then apply the fix and review it (R5): a deterministic check, or a different model family.
Append to `governance/buglog.md` immediately: symptom, the red command and its output, root cause, the fix, the guarding TEST and the reproduction rate if intermittent.
Gate to done: the original repro command goes GREEN, and the regression test FAILS on the old code and PASSES on the new.

## Phase 6 - Clean up
`grep -rn "\[DEBUG-"` and remove every hit. Delete scratch and instrumentation only through the declared route. Re-run the original repro last and paste the green output. The closing note names which hypothesis turned out correct.

## Common issues (how this skill degrades)
- Firing too often: skip it when there is no named symptom (audits, "where is it slow?"), when one message answers it, or when the report is unconfirmed (triage first). If no source of truth can be named, it is not this skill's job YET.
- NEVER cite a hypothesis as a result. A ranked guess or "it is probably the cache" is not evidence; only a receipt or a re-runnable command with output counts.
- Freeze rule: after an instrument is invalidated, quote no metric from it. Re-measure or drop the number.
- A slow or flaky test is not a gate: make it deterministic first, that is a task of its own.
- Do not let the fix precede the theory: no code change before Phase 3's frozen list and Phase 4's receipt.
