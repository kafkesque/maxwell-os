# MAXWELL OS — SESSION HANDOFF 2026-10-12 (D2590 LANDED) — lossless resume

> Read this first when resuming. Single source of truth is still CONSTITUTION.md; this file is the live
> frontier + the exact stop point. Supersedes the earlier 2026-10-12 handoff (which stopped before D2590).
> Generated 2026-10-12 ~12:20 +02:00.

## THE ONE-LINE STATE

**D2590 LANDED.** The S4 sidecar records that were *extracted, routed, written and NEVER committed* are now
committed: the store went **6,591 → 7,640 rows in ONE run**, the served surface is **unchanged** (PASS
4,503 before and after), and every rail is green. The next unblocked critical step is **A2/BUG-274
(related_fbs asymmetry), which MUST be re-measured first because this landing changed its denominator**
(1,049 rows now carry no `related_fbs`).

## WHAT HAPPENED THIS SESSION (in order)

1. **Orientation + forensic audit.** Established the predecessor audit's F4 item 1 (tree stabilization) was
   already DONE by commit `0e28cff`, so D2590 was the next unblocked step. Wrote
   `governance/FORENSIC_AUDIT_D2590_20261012.md` (F0..F6 + an appended OUTCOME section with the measured
   before/after table).
2. **THE FINDING THAT MATTERED (F2).** D2590 as specified could not land: `insert_fb` refuses any row the
   serving gate cannot derive (`pre_write_enforcement: reject`), and non-FB rows have no verification record,
   so all 1,049 rows would be refused → 100% failure ratio → **BUG-708 ROLLS THE STORE BACK**. Measured, not
   theorised. Fixed as **D-2942**: a role declared in `serving_gate.content_types_without_factual_claim` with
   no record derives **`(QUARANTINE, s5_not_applicable)`** — NOT undecidable, NEVER PASS. Status stays
   QUARANTINE so the retrieval contract is byte-identical; the typed reason carries the distinction.
3. **F3.** The `type_body` field lists already existed in the ontology (`content_types.yaml::s2_body_fields`);
   the implementation reads them and subtracts `core_body`, so **no new config and no literal field list**
   was needed (`D-2943`).
4. **BUILT + APPLIED** (D-2942..D-2945): disposition rule; `type_body` column + `build_type_body`; sidecar
   loader (selects by the ROW's own `content_type`, never by file; quarantine shelf never a source;
   idempotent; S5-owned columns stripped); `S6_COMMIT_NON_FB` wired (it was DEAD config); `content_type`
   facet on every retrieval leg (D-2944); `pre_s6_gate` check 6; per-run receipt.
5. **A DEFECT I INTRODUCED AND CAUGHT** (BUG-722 → D-2945): a second pass inserted 0 rows, so a loader
   returning only un-stored rows SHRANK the S6 checkpoint 13.8% and **`io_guard`'s shrink guard refused the
   write**. Ruling: **an artifact describes the RUN, not the store's history.** The loader returns the whole
   tier + the stored subset; stage 6 writes only new rows (`ALREADY_STORED` for the rest) and both the
   checkpoint and the Parquet snapshot are run-stable. The guard was never force-bypassed.
6. **Verified** — dry run twice in a sandboxed store copy, then live: 1,049 inserted / 0 failed; vectors
   7,640/7,640 rowid-verified; `check_serving_gate` 7,640 MATCH / 0 mismatch / 0 undecidable;
   `audit_sidecar_commit --strict` rc=0; `check_tests` 344 collected / 339 passed / 0 declared red;
   `integrity_check` 10/10; `config_audit` no drift; `check_repo_integrity --worktree` 23/23 granted.
7. **R5 instrument FAILURE (BUG-721, HIGH, OPEN).** Delegation 1 ran out of turns; delegation 2 **stated it
   could not read the files and then "simulated" the review**, returning a verdict with invented findings;
   delegation 3 (payload inlined) produced correct traces but **self-contradictory FAIL labels** on correct
   code. Consequence: the apply was gated on **deterministic instruments only** (exhaustive both-ways scoping
   test, AST column/placeholder/value alignment check, two-pass sandbox dry run, three live rails). Adopted:
   inline the payload, require the TRACE not just the verdict, never let a delegate verdict be the sole gate.
8. **Governance sync:** D-2942..D-2945 minted (registry 1,069 → **1,073**); **BUG-713 + BUG-715 reconciled to
   CLOSED** (both had been resolved in PROSE only, so the register still read a CRITICAL and a MEDIUM bug
   OPEN); **BUG-700/701/702/703 given status events** (they existed ONLY as OPEN-table rows, so the register
   carried neither and `check_governance_faces` reported them as unknown ids); BUG-719/720/721/723 logged;
   BUG-722 resolved; **BUG-712 magnitude corrected and kept OPEN** on the producer side; three census faces
   resynced; `CONTEXT_INDEX` §6f added; `aggregated_remaining_tasks` T-P1.0 → DONE; session plan granted
   `governance/aggregated_remaining_tasks.md` BY NAME (BUG-563 — it had no home).

## GIT STATE

- Branch `main`. **`32f95ec` (gov)** on top of **`c7fd46c` (impl)** on top of `0e28cff`.
- Dirty, deliberately: **` M scripts/definition_nli_verify.py`** — OWNER-OWED (R2 pin, D-2903 bytes moved,
  BUG-536/535 lineage). **DO NOT COMMIT.** Everything else is committed.
- Register truth (do NOT restate counts elsewhere — BUG-588/D-2692): **1073 decisions · 484 bugs
  (174 open / 310 closed; highest OPEN = BUG-723)**.

## STORE TRUTH (measured 2026-10-12 after the apply)

ONE run (`rechunk-v4-20260929`), **7,640 rows**, 78 columns:
`principle 6,577 / process_template 774 / process_instance 156 / tool_instruction 108 / growth_edge 25`;
**status PASS 4,503 (UNCHANGED) / QUARANTINE 3,137**; `s5_reason` gains `s5_not_applicable` = **1,049**;
`type_body` non-NULL on the 1,049 (NULL only for the 6,577 principles — no declared body — and the 14 legacy
mislabels, BUG-714). Vector index 7,640/7,640. C13 backup before the run:
`knowledge pipeline/maxwell.db.bak_20261012_115824`. Receipt: `knowledge pipeline/checkpoints/non_fb_commit_receipt.json`.

**The non-principle tier is reachable ONLY with an explicit QUARANTINE scope plus a role facet** — a
deliberate consequence of D-2942, not an oversight. Verified: `--content-type process_template --status
QUARANTINE` → 4/4 templates; default query (no facet, PASS) → principles with `entail` only.

## OWNER GATES (manual — do NOT auto-resolve)

1. **BUG-714** — `tool_instruction` contract + retype the 14 code-snippet rows. Recommendation already
   recorded: a signature+intent key (`tool_name` exact/prefix + `description` vector), never discipline/domain.
   **NEW:** the 94 sidecar TI rows are now committed, so the contract question is no longer hypothetical.
2. **D-2924 GE category calibration — now with hard evidence:** **25/25 committed growth_edge categories are
   OFF the closed vocabulary** (`open_tension` / `unverified_correlation` / `contested_claim` /
   `capability_gap`). Flipping `growth_edge_ontology.yaml` advisory → enforcing today would reject 100% of the
   GE corpus. Nothing was normalised at commit time (owner-gated ontology act, D-2898); the counts are in the
   receipt. Mint `config/golden/ge_category_gold.yaml` → stamp `calibration_decision` → flip.
3. **R2 pin re-measure** — `scripts/definition_nli_verify.py` (D-2903): re-measure + **NEW decision id** +
   new sha256 in `config/recalibration_pins.yaml`.
4. **Serving policy for the non-principle tier (NEW gate surfaced by D-2942):** should procedures/instances
   be served by DEFAULT? That is a verification-DESIGN question (how *is* a tool instruction verified?), not
   a config flip. Until ruled, the tier is explicit-scope only.
5. **Independent golden anchors** (anchors not sourced from the candidate leg) → then settle
   `retrieval.method` + D-2537 `borp_score`.
6. **A3 outcome-driven lifecycle gate** (`fb_reliability` → promote/retire; owner-gated per D-2898; keep it a
   rank signal with a confidence interval, never a hard gate).

## NEXT CRITICAL STEPS — strategic-consequential order

**Unblocked machine work (do these in this order):**

1. **A2 / BUG-274 — related_fbs asymmetry — RE-MEASURE FIRST.** The last census (88,592/156,104 one-way =
   56.8%, + 7 self-refs) was taken on the **6,591-row** store; the denominator is now **7,640** and the 1,049
   new rows carry **no** `related_fbs` at all, so the ratio has moved by construction. Measure on the current
   store, then prune with `scripts/` + a receipt, then add `prerequisite`/`contradicts` operators to
   `graph_expand`. (This is the prerequisite for trustworthy graph expansion — A1/A3 lean on it.)
2. **A1 context-compiler contract** for the MCP harness: return a COMPILED payload (principles + template +
   instance + evidence + trust), not a bare list. Now meaningful for the first time, because templates and
   instances actually exist; `content_type` (D-2944) is its natural selector, and the QUARANTINE scope is the
   honest trust boundary. Owns the D-2590(d) deferred cross-ref producer (`consulted_fbs`/`parent_pt_id`).
3. **BUG-719 repair path** — the 196 rows whose own `content_type` is `principle` while sitting in the
   non-principle sidecars. Deterministic triage first (are they principles that S4 mis-filed, or GE objects
   mislabelled?); **never** fix by re-routing.
4. **BUG-720** — `stage4_merge.py` emits a `deduped_cluster_ids` receipt → the audit tolerance goes 7 → 0.
5. **BUG-702/703 close-out verification** — both look STALE (the `--practicality` and `discipline_raw`
   COALESCE fallbacks exist in `retrieve.py::_facet_conditions`), but they must be closed on END-TO-END
   evidence on the served run, never on the strength of a grep.
6. **BUG-712 producer fix** — S4/S2 computes the corrected `content_type` and DISCARDS it (root cause found
   2026-10-11). D2590 excluded the mislabelled rows rather than re-routing them; the fix belongs upstream.
7. **BUG-723** — reprocess the 232 corpus files that only the purged `t11` run covered (mechanical S0..S6
   run; the archive preserves them, nothing serves them).
8. **Meta-infrastructure (queued, additive):** `governance/correlation_graph.jsonl` +
   `scripts/continuity_context.py` (Tier-1 typed edges, deterministic compiler) — design in
   `research/COLLABORATION_CONTINUITY_CORTEX_20261012.md`.

**Do NOT do:** weaken the `io_guard` shrink guard (it caught BUG-722); flip `commit_non_fb_types` (D2590 is
not a toggle); auto-promote the non-principle tier to PASS; re-inject the archived superseded rows.

## CONTEXT TO CARRY (so the next session does not re-derive it)

- **D2590's real population: 1,049** (PT 774 / PI 156 / TI 94 / GE 25). The old "81 tool_instruction
  remaining" was an ARITHMETIC ERROR — the 14 committed TI rows came from `checkpoint.jsonl`, not from a
  sidecar (BUG-719).
- **Two artifacts are run-stable and must stay so:** the S6 checkpoint (7,640 records on every pass) and the
  Parquet snapshot.
- **The disposition is row-deterministic:** `derive_status(..., content_type=...)` reads the ROW, so the
  writer (`stage6_commit`) and the rail (`check_serving_gate`) can never disagree. Any future writer must go
  through the same rule — the pre-write comparator refuses anything else.
- **Absent record + `principle` ⇒ still UNDECIDABLE and refused.** If that ever stops being true, the
  disposition has become a bypass (asserted by test).
- **Evidence to quote for this session:** `governance/FORENSIC_AUDIT_D2590_20261012.md` (audit + OUTCOME),
  `knowledge pipeline/checkpoints/non_fb_commit_receipt.json` (per-run exclusions),
  `temp/dryrun_d2590.py` (the two-pass sandbox dry run; re-runnable).

## C15 — unresolved bugs that must travel with every handoff (5 ≥ threshold)

**BUG-714** (tool_instruction contract, owner) · **BUG-719** (196 mislabelled rows in the non-FB sidecars) ·
**BUG-720** (dedup receipt → tolerance 0) · **BUG-721** (HIGH: a delegate returned a FABRICATED verdict =
false assurance; harness cannot yet prove a delegate read its input) · **BUG-723** (t11-unique coverage debt).
Also OPEN and named here for completeness: **BUG-712** (producer side), **BUG-267/274/600s-class** items in
`governance/bug_status.json` (174 open / 310 closed).
