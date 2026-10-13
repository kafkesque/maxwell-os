# SPEC — Retrieval Serving Surface (P0)

spec_version: 2
governed: pipeline/retrieve.py · pipeline/retrieval_benchmark.py (the gate) · config/serving_call_sites.yaml (the call-site matrix)
authority: D-2881 (canonical-run pin) · D-2939 (name anchoring) · D-2537/D-2979 (quality ranking) · D-2724 (vector+rerank adopted) · D-2978 (spec-first) · D-2980 (one dispatcher, measured) · BUG-710
stamp: 2026-10-13 · deterministic authoring (no LLM gen)
status: owner-ratified spec-first direction; each invariant is live-verified by tests/test_retrieval_serving_spec.py

## Purpose

Definition of correct for the production retrieval serving path, written BEFORE a fix lands and
kept as the definition — not as a report. Every invariant maps 1:1 to an executable test.
The machine runner (pytest) is the grader — a local LLM may DRAFT a spec/test but never
"eyeball" correctness (R5: generator != verifier; R7: temp=0 on the runner).

Lifecycle (owner-approved, D-2978): this file is OVERWRITTEN IN PLACE when the contract changes
— never appended, never a new file per change. One spec per governed surface, paired 1:1 with
its test module; history lives in git plus the D-number that changed it.

## Invariants

### INV-1 — Golden set is pinned to the served run (BUG-710)
- **Correct:** every query in config/golden/retrieval_queries.yaml has verified_run == CANONICAL_RUN
  and a non-empty expected_names anchor. D-2939: the NAME is the anchor; the id is resolved per
  run by pipeline/golden.py.
- **Failure it prevents:** recall pinned to 0.000 because the goldens live in a superseded run —
  the S1/S2/S3 adoption gate goes blind (a regression and an improvement are equally invisible).
- **Status:** ✅ SATISFIED (version 4, 29/29 rechunk-v4-20260929, all named).

### INV-2 — Every pool leg pins to CANONICAL_RUN (D-2881)
- **Correct:** keyword / fts / vector each filter pipeline_run_id and bind it to CANONICAL_RUN, so a
  superseded run can never be served. (BUG-713: the superseded runs t11/e2e/bug198_reinject were
  purged from the store and the KNN index on 2026-10-12 — the pin is now a SECOND, independent guard,
  not the only one.)
- **Failure it prevents:** stale FBs competing at rank 1-2; dead KNN candidate slots.
- **Status:** ✅ SATISFIED.

### INV-3 — Ranking signal must not degenerate to a constant (D-2537 / D-2979)
- **Correct:** the ORDER BY is the D-2537 fused quality score
  (COALESCE(confidence_score, 0.5) * weight + convergent boost + diversity boost), gated by
  ranking.quality_score_enabled: true, and it has ONE home (_rank_sql()).
- **Why the fallback is wrong:** with the flag false, _rank_sql() returns "borp_score DESC" and
  borp_score is retired debt (constant 0.0, nothing writes it), so the ORDER BY collapses to rowid
  order and low-confidence rows compete at rank 1-2.
- **Status:** ✅ SATISFIED (D-2979 flipped the gate 2026-10-13; the signal is verified non-constant
  at the DATA level, not merely at the code level). The CLI fallback in pipeline/query.py carried a
  SECOND dead copy of this clause and was repointed to the ONE home by D-2980.

### INV-4 — The benchmark gate fails loud, never a false 0.000 (C16)
- **Correct:** retrieval_benchmark aborts exit 2 on any unresolvable golden (run/status/scope),
  listing each unreturnable golden instead of scoring it 0.
- **Status:** ✅ SATISFIED (fixed 2026-10-11 21:40).

### INV-5 — ONE production entry point, and every serving call site is DECLARED (D-2724 / D-2980)
- **Correct:** every declared production call site (MCP query_knowledge, graph_aware_search,
  agentic_search, the CLI default query path) calls the dispatcher search(); the dispatcher is the
  ONLY place retrieval.method is resolved. Every direct call to a retrieval LEG from any file in
  scope_globs is declared in config/serving_call_sites.yaml with a reason, and every declaration
  matches a LIVE call (both directions).
- **Why it is not bookkeeping:** D-2724 adopted vector+rerank and repointed THREE call sites; the
  MCP non-graph branch and the CLI default query path were missed and stayed on the superseded RRF
  path for two weeks with every rail green, because the fact "this module serves" had no home. An
  agent asking the MCP server saw a different retrieval method than the config declared.
- **Status:** ✅ SATISFIED (D-2980: both surfaces repointed; the matrix + its reader land together).

### INV-6 — The harness measures the SERVED path, not only A/B controls (D-2980)
- **Correct:** retrieval_benchmark reports a "production" leg that IS the dispatcher (same method,
  same pool policy, same rerank gate), and the label-free self-retrieval rail measures it too.
  The A/B legs are constructed at the SERVED pool width (serving.pool), not at a literal.
- **Failure it prevents:** the adoption gate measuring a function no user calls — the harness used
  candidate_pool 30 while production used 50-100, so "the benchmark" and "the product" were
  different functions; the ranking and rerank changes could not be validated against the served path.
- **Status:** ✅ SATISFIED (D-2980).

### INV-7 — The candidate-pool policy has ONE home (C12/C20)
- **Correct:** serving.pool in config/pipeline_config.yaml; read fail-closed (no code default, since
  a default moves the value out of config — D-2644/BUG-504 class); applied by _rerank_pool_size()
  and _rrf_leg_pool_size(), which BOTH the dispatcher and the harness call.
- **Status:** ✅ SATISFIED (D-2980 retired the two inline literals).

## Non-goals (out of scope for this spec)
- BUG-712 content_type routing collapse — a separate surface.
- The 4-factor WEIGHTS themselves live in config/pipeline_config.yaml (C12), not here.
- The MCP payload still EXPOSES borp_score / feedback_score (retired/derived fields). Changing an
  MCP output schema is a contract change and needs its own decision; it is named here so it is a
  declared residual rather than a blindspot.

## Open items recorded by this spec (so they are not blindspots)
1. The MCP query_knowledge payload advertises borp_score (retired constant) — awaiting an
   owner-gated payload decision.
2. config serving.superseded_runs still lists the purged runs: it is the purge/restore-path
   declaration read by scripts/purge_superseded_runs.py, and it is now inert for serving (nothing
   un-purged exists). Retiring it requires the archive-restore path to be re-declared.
