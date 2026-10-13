# SPEC — Retrieval Serving Surface (P0)

spec_version: 1
governed: pipeline/retrieve.py (+ pipeline/retrieval_benchmark.py gate)
authority: D-2881 (canonical-run pin) · D-2939 (name anchoring) · D-2537 (quality ranking) · BUG-710 · BUG-713
stamp: 2026-10-13 · deterministic authoring (no LLM gen) · pipeline_commit: pending
status: owner-ratified spec-first direction; each invariant below is live-verified against the store

## Purpose

Definition of correct for the production retrieval serving path, written BEFORE the fix lands.
Every invariant maps 1:1 to an executable test in `tests/test_retrieval_serving_spec.py`.
The machine runner (`pytest`) is the grader — a local LLM may DRAFT a spec/test but never
"eyeball" correctness (R5: generator ≠ verifier; R7: temp=0 on the runner). This file is the
single source of truth for the surface: it is OVERWRITTEN in place when the contract changes
(never appended, never a new file per change); history lives in git + a D-number in DECISION-LOG.

## Invariants

### INV-1 — Golden set is pinned to the served run (BUG-710)
- **Correct:** every query in `config/golden/retrieval_queries.yaml` has `verified_run == CANONICAL_RUN`
  and a non-empty `expected_names` anchor. D-2939: the NAME is the anchor; the id is resolved per
  run by `pipeline/golden.py`.
- **Failure it prevents:** recall pinned to 0.000 because goldens live in a superseded run — the
  S1/S2/S3 adoption gate goes blind (a regression and an improvement are equally invisible).
- **Status:** ✅ SATISFIED (version 4, 29/29 `rechunk-v4-20260929`, all named).

### INV-2 — Every pool leg pins to CANONICAL_RUN (D-2881, BUG-713)
- **Correct:** keyword / fts / vector each filter `pipeline_run_id` and bind it to `CANONICAL_RUN`
  so superseded runs (t11 7,855; e2e 122; bug198_reinject 6) are never served.
- **Failure it prevents:** stale FBs competing at rank 1–2; 53.9% of KNN candidate slots dead.
- **Status:** ✅ SATISFIED (keyword uses `canonical_run_clause()`; fts/vector use `run_f` + `CANONICAL_RUN` bind).

### INV-3 — Ranking signal must not degenerate to a constant (D-2537)
- **Correct:** the ORDER BY uses the D-2537 fused quality score —
  `COALESCE(confidence_score, 0.5) * weight + convergent boost + diversity boost` —
  gated by `ranking.quality_score_enabled: true`.
- **Why the fallback is wrong:** with the flag `false`, `_rank_sql()` returns `ORDER BY borp_score DESC`,
  and `borp_score ≈ 0.0` for all 4,503 served PASS rows (live-verified: `COUNT(DISTINCT borp_score) == 1`,
  min = max = 0.0). A constant ORDER BY collapses to rowid order, so low-confidence rows
  (1,695/4,503 with NLI < 0.5) compete at rank 1–2.
- **Status:** ❌ VIOLATED. Fix = flip `ranking.quality_score_enabled → true` (the 4-factor clause is
  ALREADY implemented in `_rank_sql()`); the only gap is the config gate + confirming `confidence_score`
  is populated (docstring: avg 0.917, fully populated).

### INV-4 — Benchmark gate fails loud, never a false 0.000 (C16)
- **Correct:** `retrieval_benchmark.main()` aborts exit 2 on any unresolvable golden (run/status/scope),
  listing each unreturnable golden.
- **Status:** ✅ SATISFIED (fixed 2026-10-11 21:40).

## Non-goals (out of scope for this spec)
- BUG-713 index purge (superseded-run deletion) — a separate destructive op; needs backup_guardian + cascade audit.
- BUG-712 content_type routing collapse — separate P2 surface.
- The 4-factor WEIGHTS themselves live in `config/pipeline_config.yaml` (C12), not here.
