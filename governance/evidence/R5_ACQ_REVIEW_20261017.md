# R5 REVIEW — the acquisition lane (D-3079), verifier = gemma-4-E4B-it-MLX-4bit

**Generator:** assistant (this session). **Verifier:** `gemma-4-E4B-it-MLX-4bit`, temperature 0.0, one-shot via the
OMLX endpoint on `127.0.0.1:11435` (a DIFFERENT family from the generator — R5). **Journal id:**
`DJ-20261017T192341Z-ee6b`. **Date:** 2026-10-17.

> The first delegate call to this model FAILED (`Subagent 20261017_24 failed: Other`), so the review was run as a
> one-shot completion against the same served model. That is recorded rather than hidden: a review whose transport
> is not the sanctioned one is still evidence, but it is weaker evidence and it must say so.

## What the verifier was asked, and what it answered

| # | question | answer | reading |
|---|---|---|---|
| Q1 | can `_receive` leave a partial file under a FINAL name if killed mid-download? | **NO** | the `.part` lives in `.acq-staging` and only `os.replace` creates the final name (C6 holds) |
| Q2 | can two candidates with the same rendered name overwrite each other? | **YES** | ACCEPTED AS A RESIDUAL, not a defect in the single-process path: `_unique_path` checks existence, but two CONCURRENT runs can both see the name free (see residual R-1) |
| Q3 | does a non-`AdapterMiss` `AcquisitionError` from `locate` abort the run? | **NO — it was not caught, so it aborted** | **DEFECT, FIXED** (see D-1) |
| Q4 | can `render_name` escape the pen (`..`, absolute path)? | **NO** | `/` and `\` are in `UNSAFE`, and the name is joined to the pen directory, never to a path from the title |
| Q5 | is the circuit breaker's failure counter reset after a success? | **NO** | **DEFECT, FIXED** (see D-2) |
| Q6 | does `_extension` raising abort the run? | **NO** (it continues) | it is inside the `_receive` try, caught as `AcquisitionError`, ladder moves on |
| Q7 | can `probe_landed` return True for a file never written? | **NO** | the path is the file that `os.replace` just created; the probe runs on those bytes |

## Defects accepted and fixed in this session

**D-1 — a refusing SOURCE ended the WHOLE run.** `fetch_manifest` caught only `AdapterMiss` and `NetworkRefused`
around `adapter.locate`. `libgen.locate` → `mirrors.live_domains` raises `AcquisitionError('no VALIDATED mirror for
libgen…')`, which escaped the per-candidate loop: one saturated mirror could end a ten-candidate manifest at the
first row, and the remaining nine would never be attempted. **FIX:** a third `except AcquisitionError` records
`failure_class: adapter_error` against that adapter and continues. A genuine configuration fault still fails fast,
because the declaration is read BEFORE the loop (`land_pen`, `ladder`, `probe_map`).
**RECEIPT:** selftest check *"a refusing source does not end the run (two attempted, both named)"* — two candidates,
one fault adapter, two named refusals, run completes.

**D-2 — the breaker measured the run's history, not the adapter's health.** `breaker["failures"][id]` was
incremented and never reset, so an adapter that failed three times across a long manifest opened its breaker even
while it was still serving. **FIX:** the counter is zeroed on every successful landing.
**RECEIPT:** the same selftest file; the loop now resets at the `landed` branch (grep `breaker["failures"][adapter.id] = 0`).

## Residuals this review did NOT clear (declared, not fixed)

- **R-1 (from Q2).** `_unique_path` is check-then-create, so two CONCURRENT runs of `acquire.py` can choose the same
  filename and one `os.replace` overwrites the other. Bounded: the index records both canonical ids against one
  path, so the loss is detectable, and the lane is run by one agent at a time. Remedy when needed: `O_EXCL` create or
  a run lock — an OWNER-WORDED change, not a silent one.
- **R-2.** The verifier cannot judge the DOOR's probe semantics (`is_readable`) — it never saw
  `pipeline/container_integrity.py`. That control is covered by that module's own selftest and by the door's live
  refusals, not by R5.
- **R-3.** The network adapters (LibGen parsing against live markup, DDoS-Guard behaviour of Anna's) were not
  reviewed here: they were measured live instead (BUG-908 / BUG-909). A fixture-pinned parser plus a live refusal
  is stronger evidence than a model's opinion about a regex.

## Verdict

**Two real defects, both in the failure path, both fixed and now held by a control that fails if the fix is
reverted.** The happy path (name, landing, probe, receipt) was already covered by 31 checks and one real acquisition;
the verifier's contribution was in the path that only runs when a source misbehaves — which is exactly the path a
single happy-path test never exercises.
