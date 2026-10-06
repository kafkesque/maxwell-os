# OWNER GATE — BUG-528 pipeline/** lock re-scope (D-2801 LANDED — RESOLVED 2026-10-03)

> **Status:** RESOLVED 2026-10-03 — D-2801 LANDED (git HEAD 933aea9) and D-2805 OWNER RATIFIED
> (BUG-528 lock re-scoped to an accountability gate: R5 + D-naming + stage_code_fingerprint). The S4 rerun
> is UNBLOCKED. This proposal is now historical record of the owner decision that landed.
> Written 2026-10-03 by the assistant (R5 generator). Forensic audit state at time of writing: 4 rails
> GREEN, session-plan GREEN, worktree RED on exactly the 20 paths below (BUG-528, owner-gated).

---

## 1. The deadlock (why this is urgent, and why it needs YOU)

`pipeline/**` sits in `will_not_touch` (session_plan_20260924.yaml). But `pipeline/` is the single most
actively-edited directory in the repo. The working tree carries **745 insertions across 19 files + 1
untracked file** of legitimate, decision-backed work that landed against the lock and can therefore
**neither be committed (lock violated, rail 4 refuses) nor reverted (it would break the build)**:

- `stage4_merge.py` **imports** `reroute_content_type` and `derive_applicability` from `content_types.py`
  (D-2747 / D-2757). Revert `content_types.py` → the import fails → S4 breaks. Commit it → lock violated.
- `stage6_commit.py` adds the `evidence_passages` / `evidence_passages_shown` columns (D-2352/BUG-111) that
  downstream consumers and `golden_validate` check #4b already read.

This is the C27 "no dead ends" rule made concrete: **the tree cannot be made clean without an owner
decision.** Every prior session that touched `pipeline/` needed a bespoke `crossing: true` owner-ack
(BUG-499, BUG-503/504, D-2643/D-2644). That ceremony has now fired ~5× in a week — the lock is being
honored only in the breach, which is the textbook signal that the lock's *semantic* is wrong.

## 2. The 20 blocked files (so you can review exactly what is gated)

| file | delta | known provenance |
|---|---|---|
| `pipeline/content_types.py` | +265 | D-2747 `reroute_content_type`, D-2757 `derive_applicability` (BUG-611/BUG-170) |
| `pipeline/runner.py` | +127 | runtime/run-id plumbing |
| `pipeline/stage4_merge.py` | +97 | D-2747/D-2757, BUG-614 `_stage_code_fingerprint`, D-2798 advisory, BUG-148 quarantine |
| `pipeline/retrieve.py` | +63 | retrieval pathing |
| `pipeline/stage4_merged_call.py` | +61 | S4 classifier call path |
| `pipeline/text_cleaner.py` | +30 | cleaning |
| `pipeline/golden_validate.py` | +28 | BUG-596 check #4b, BUG-600 (D-2720) source-diversity skip |
| `pipeline/stage2_extract.py` | +28 | evidence_passages emit |
| `pipeline/pipeline_paths.py` | +14 | D-2644 S5 score axes, D-2716 run-id |
| `pipeline/stage6_commit.py` | +11 | evidence_passages/evidence_passages_shown migration |
| `pipeline/metrics.py` | +10 | D-2716 run-id `get_run_id()` |
| `pipeline/probe_run.py` | +9 | BUG-596 alignment |
| `pipeline/retrieval_benchmark.py` | +8 | HNSW benchmark |
| `pipeline/stage1_3_prefilter.py` | +6 | D-2703 chunking |
| `pipeline/golden_sampler.py` | +5 | D-2716 run-id |
| `pipeline/omlx_watchdog.py` | +5 | — |
| `pipeline/stage1_chunk.py` | +5 | D-2703 re-chunk |
| `pipeline/stage1_5_domain_cluster.py` | +3 | D-2716 run-id |
| `pipeline/run_diagnostic.py` | +2 | D-2716 run-id |
| `pipeline/practicality.py` | **untracked (new)** | D-2622 practicality/applicability filter (proposed feature) |

## 3. Recommendation (senior-systems: re-scope the lock, don't keep granting crossings)

**Diagnosis.** `will_not_touch` is the wrong tool for code. It protects *immutable* artifacts — owner
instruments (`governance/F11_*`, `ANCHOR_RULER_CONSOLIDATED_*.csv`, `ANCHOR4_DEPTH_BLIND_SHEET_*.csv`).
Actively-developed code is *not* immutable; it is governed by version control + review + tests, not an
edit-prohibition lock. `pipeline/**` was lumped into the same family as owner instruments, so the lock
has been silently drifting from "don't touch" to "touch with ceremony" — the worst of both.

**Tier 1 — re-scope (the fix).** Remove `pipeline/**` from `will_not_touch`. Replace the edit-gate with an
**accountability gate** that is already half-built:

1. **R5 generator≠verifier** — every pipeline diff is reviewed by a *different* model family before commit.
2. **D-naming** — every pipeline change is attached to a named decision (D-xxxx) in DECISION-LOG.md.
3. **`stage_code_fingerprint` (BUG-614)** — stage4_merge.py already hashes the byte-content of
   `stage4_merge.py` + `content_types.py` + config and binds every checkpoint to it, so any *unreviewed*
   edit silently invalidates the checkpoint fail-closed at resume. Extend this pattern (it is the
   enforcement mechanism the lock should have been).

This converts "don't touch" → "touch with accountability", which is what is *actually* happening, and makes
the machine enforce review instead of making a human re-ack the same permission every session.

**Tier 2 — structural (prevent recurrence, C27).** The `crossing: true` convention was designed as a
ONE-OFF owner ack. It has been used ~5× in a week for the same family. Add a rail that **counts crossings
per family per window and refuses (rc=2, owner gate) above N** — forcing a *family-level* re-scope (one
decision) instead of N *file-level* crossings. That detects lock-semantic drift automatically.

**Tier 3 — governance cadence.** On every registry increment, re-ask: "is each `will_not_touch` family's
semantic still correct?" A lock that rots into a lie trains the operator to expect false REDs and ignore
real ones — worse than no lock.

## 4. Exact change (applied only on your ack)

`governance/session_plan_20260924.yaml`, `will_not_touch:` block — remove one line:

```yaml
will_not_touch:
  - governance/F11_*            # owner instruments (write-locked)
  - governance/ANCHOR_RULER_CONSOLIDATED_*.csv
  - governance/ANCHOR4_DEPTH_BLIND_SHEET_*.csv
  - pipeline/**                 #  <-- REMOVE (the mis-scoped lock)
```

The 20 files then become committable under the ordinary `may_touch` rules once each carries a D-xxxx and
passes R5 review. The owner instruments keep their lock, untouched.

## 5. Your decision (one word)

- **`ok`** → I apply the re-scope (remove `pipeline/**` from `will_not_touch`), mint **D-2801** (bug
  BUG-528/BUG-563-recurrence; files session_plan + the 20 pipeline files), commit the 20 files with
  per-file D-attribution + R5 review, then re-run the re-chunk → classify-150 → S4 sequence.
- **`revert`** → I restore the 20 files to HEAD and re-file the lost work as a D-28xx "parked features"
  record so the work is not silently lost (it is currently uncommitted — a Dropbox conflict could wipe it).

**No self-resolution is legal here:** widening `may_touch` to cover `pipeline/**` is refused by rail 4
(BUG-528/BUG-445 — `will_not_touch` OUTRANKS `may_touch`), and narrowing the lock is a plan change that is
owner-owned. That is exactly why this file exists.
