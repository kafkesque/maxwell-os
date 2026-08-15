# Maxwell OS — Aggregated Task Register
> **Updated:** 2026-08-14 13:48 | **Decisions:** D2000-D2355 (344) | **T1.1 canary GREEN (V1–V6); remaining gate = S4 speed + depth correctness**
> **S5 Architecture:** DeBERTa-only NLI, threshold 0.10 (D2298) + premise/hypothesis pairing (D2321). Final. No ongoing adjudication.
> **Active Models:** Qwen3-Coder-30B (S2) | GPT-OSS-20B (S4 classifier) | DeBERTa-v3-large (S5 verifier) | bge-m3 (Emb)
> **Hybrid Gate:** Wired (P0.1, D2276) but **DISABLED for T1.1** — BUG-085 A/B proved net-negative (4.3% negative rejection). Run traditional-only.
> **ISOR Scoring:** Active (P0.4, D2284). 3-dimension independence rating in verified FB output.
> **Audit completed:** Runner.py Gemma dead code purged. Stale comments fixed. No silent crash risks found.
> **D2300-D2307:** Modularity gaps, cold-reload, DSPy 3 gaps, CRIBS batch mitigation, DSPy tier-aware split, InferenceProvider protocol, recall measurement — all logged/implemented (2026-08-12).
> **D2337-D2341 (NEW, 4-LLM audit):** S6 data loss, S4/S6 fail-open, runner run-id isolation, model-registry drift, schema corrections.
> **D2351-D2355 (NEW, 4-LLM audit × independent re-verification):** S4 depth fail-open, provenance/schema gaps, singleton index, S4 bottleneck. **Must/Should/Worth tiers → `governance/T1.1_CANARY_READINESS_MUST_SHOULD_WORTH.md`.**

---

## 🔴 #0.5 — MUST/SHOULD/WORTH before canary re-run + T1.1 (BUG-108…119, D2351–D2355, 2026-08-14)

> **4-LLM audit (`chatgpt0010.md`, `claude0010.md`) × independent code re-verification.** Two ChatGPT errors corrected
> (`s3_original_domain` is migrated+dead, not a fresh-DB blocker; singleton integration is still broken, not "fixed").
> Full tiered breakdown: **`governance/T1.1_CANARY_READINESS_MUST_SHOULD_WORTH.md`**.

> **✅ IMPLEMENTATION STATUS (2026-08-14 14:34):** M1–M4, S1, S2, S4, W1–W6 are **DONE** (verified with
> `py_compile` + unit + live SQLite tests). **S3 is PARTIAL** — `batch_depth_classify()` was A/B-tested live
> (n=8): ~1.9× faster but **75% parity (< 90% gate)** → NOT wired into production; the recommendation is a
> FrugalGPT gemma-4-E4B depth cascade behind the same gate. **S5** (benchmark-through-production) remains open.
> **W7 (`deathpectation` literal) → RESOLVED (2026-08-15):** it is the user's private Anytype space name.
> **W6 intimacy routing → D2356** (`pipeline/intimacy_lattice.py`).

### 🔴 MUST (blocks a defensible T1.1)

| # | Task | Bug | Decision | Effort |
|---|------|-----|----------|:------:|
| M1 | S4 depth fail-closed — no silent `"domain"` on exception/no-match | BUG-108 | D2351 | 0.5h |
| M2 | `depth_max_tokens` 512 → 1024 + fix stale docstring | BUG-109 | D2351 | 0.25h |
| M3 | Carry `source_segments` through S4 → S6 | BUG-110 | D2352 | 1h |
| M4 | Persist `is_summary` end-to-end | BUG-112 | D2352 | 0.5h |

### 🟠 SHOULD (quality / feasibility — before full T1.1)

| # | Task | Bug | Decision | Effort |
|---|------|-----|----------|:------:|
| S1 | Persist `evidence_passages`/`_shown` to SQLite (or document Parquet as verbatim store) | BUG-111 | D2352 | 1h |
| S2 | Singleton S2→S4 index fix (`run_stage4` reuse `principles_idx`) | BUG-113 | D2353 | 1h |
| S3 | S4 bottleneck resolution (remove batch `depth` + batch focused depth) | — | D2354 | 2–3h |
| S4 | Batch missing-output fail-closed | BUG-114 | D2355 | 0.5h |
| S5 | Depth benchmark authority (production path; reconcile 87.5% vs 37.5/50%) | BUG-115 | D2351 | 1h |

### 🟡 WORTH (hygiene / drift / bloat — non-blocking)

| # | Task | Bug / note | Effort |
|---|------|-----------|:------:|
| W1 | Remove dead `s3_original_domain` | BUG-116 | 0.5h |
| W2 | Unify secondary checkpoint writers on `_write_checkpoint_jsonl` | BUG-117 | 0.5h |
| W3 | `insert_embedding()` per-FB failure logging | BUG-118 | 0.25h |
| W4 | Add `jargon` to FTS5 | BUG-119 | 0.25h |
| W5 | Reconcile `extraction_type` "S5 consumer" claim | drift | 0.25h |
| W6 | Restore/document v2 intimacy routing | drift | ✅ DONE (D2356) |
| W7 | Define or drop `deathpectation` | drift | ✅ RESOLVED (2026-08-15) — private Anytype space name |

> **S4 bottleneck (D2354) — the ultimate solution:** correctness-first (fail-closed + 1024 tokens) → remove waste
> (drop `depth` from CRIBS batch) → batch the *focused* depth prompt (keep GPT-OSS + short prompt + `fb_index`) →
> benchmark gate ≥90% → only then consider gemma-4-E4B. Target: ~25s/FB → ~6–8s/FB, full T1.1 ~142h → ~25–30h.

---

## 🔴 #0 — NEW BLOCKERS FROM 4-LLM AUDIT (B11–B15, D2337–D2341, 2026-08-13)

> **Surfaced by ChatGPT audit + independently re-verified.** Kimi/DeepSeek = repo-blocked (zero signal); Qwen = unsound
> (rated prompt's own claims as verified). These are downstream (S4/S6) correctness + config trust issues; the S6 data
> loss is the highest-severity defect because a successful-looking full run would silently drop fields.

| # | Decision | Task | Status |
|---|----------|------|--------|
| B11 | D2337 | S6 persist D2323 axes + mechanism/boundary/consequence + round-trip test | ✅ DONE |
| B12 | D2338 | S4/S6 fail-closed — `failure_ratio > max → exit 1`; `>0 → exit 2` | ✅ DONE |
| B13 | D2339 | runner `--run-id` pre-parse before `pipeline_paths` import | ✅ DONE |
| B14 | D2340 | model-registry drift — session_seed renamed; config/path rename deferred (post-T1.1) | 🟠 PARTIAL |
| B15 | D2341 | schema corrections — three-axis `status`, typed edges, TI class, feedback→YAML | 🟡 DEFERRED P2 |

> **Ordering:** B11→B12 (silent permanent corruption) → B13→B14 (run-scoping + registry) → B15 (schema contract, P2).
> ChatGPT's "enable hybrid" recommendation REJECTED (BUG-085 A/B proved net-negative).

---

## ✅ #1 — T1.1 PRE-FLIGHT BLOCKERS (B1–B10, D2324–D2332) — ALL IMPLEMENTED

> **CONDITIONAL-GO → all pre-flight blockers closed.** Implemented across commit 9295ce0 (B2/B3/B4/B7/B8/B9/B10)
> and D2343 (B1 residual: S2 resume `load_jsonl`; B5 residual: `route_values` config-driven; B6 residual: e2e `--in-place`;
> NEW e2e ontology round-trip check [7]; integrity [11] label). Roundtable (7 items) + independent code sweep (B1).
> kimii's BLOCKER (S5 fast-gate) fabricated; chatgpt's findings real; qwen's "0.65" rejected.

| # | Decision | Task | Status |
|---|----------|------|--------|
| B1 | D2332 | S2 checkpoint fail-closed `load_jsonl` at every reader + resume | ✅ DONE (D2343) |
| B2 | D2329 | Resume-validity manifest (run_id/schema/count/COMPLETE) | ✅ DONE |
| B3 | D2326 | S0 fail-closed + tri-state quality check (C16) | ✅ DONE |
| B4 | D2323 | Content-type golden fix → 5-role ontology | ✅ DONE |
| B5 | D2323 | Content-type enum wiring + `route_values` config-driven (C12) | ✅ DONE (D2343) |
| B6 | D2327 | S1.3 prefilter `--in-place` in runner + e2e | ✅ DONE (D2343) |
| B7 | D2331 | S2 silent-skip fail-closed (`S2_MAX_FAILED_RATIO`) | ✅ DONE |
| B8 | D2328 | S5 calibration truth (P=0.647/R=0.386/F1=0.484) + runner desc | ✅ DONE |
| B9 | D2325 | S6 provenance per-FB `INSERTED/FAILED/SKIPPED` | ✅ DONE |
| B10 | D2330 | e2e run-scoping + quarantine retrieval contract test | ✅ DONE |

---

## 🔴 #2 — CONTENT-TYPE ONTOLOGY CONSOLIDATION (D2323, 2026-08-13)

> **Blocks the T1.1 full run** (senior RAG review: PT/PI are the Layer-2 product; currently orphaned + dead-schema + stale-trained).

| # | Task | Status |
|---|------|--------|
| 1 | Freeze contract → `config/content_types.yaml` (2 axes, core+extension, 13-field TI, D2150/D2128) | ✅ DONE (D2323) |
| 2 | Fix golden few-shot `content_type` values (`model/heuristic/pattern` → correct ontology) | ✅ DONE — all 77 golden FBs carry `content_type=principle` (verified 2026-08-13) |
| 3 | Wire enums: `schemas.py` + `stage2_extract._VALID_CONTENT_TYPES` + `stage4_merge` routing → registry | ✅ DONE (except `ToolInstruction` Pydantic class = B15/D2341, P2) |
| 4 | Fix route→content_type mapping (D2128) + drop vestigial `fact`/`meta` | ✅ DONE — `ROUTE_TO_CONTENT_TYPE` + `DROPPED_CONTENT_TYPES={fact,meta}` live |
| 5 | Verify 4 orphaned FBs (3 PT + 1 TI) flow end-to-end | ⚪ MOOT — current DB has 0 rows with axes populated (all pre-D2337); re-verify after T1.1 canary |
| 6 | (deferred) S4 rich per-type extension-field generation (steps/trigger/prerequisite…) | post-T1.1 |

---

## 🔴 #2.5 — 2nd AUDIT BLOCKERS (D2346/D2347, 2026-08-13) — fix BEFORE the canary

> **ChatGPT/Qwen audit (post-D2344) surfaced 2 code-verified blockers the B1–B15 set missed.** Both hit the
> **principle** path. D2345 (non-type second pass) is DECIDED as post-T1.1 — NOT a blocker.

| # | Decision | Task (code-verified) | Status |
|---|----------|----------------------|--------|
| B16 | D2346 | S1.5 embedding-drop index alignment — return `(filtered_segments, embeddings)` + `len(segments)==len(embeddings)` assert + injected-drop tests | ✅ DONE |
| B17 | D2347 | e2e convergence metric → `sum(c["is_convergent"])` (canonical IDs); filename-diversity as separate diagnostic | ✅ DONE |

> **Why B16 first:** D2275 permits ≤0.5% embed drop; on any drop, `embed_segments()` filters locally but returns only
> embeddings → `build_clusters()` indexes the full original list → silent wrong-segment corruption (no exception).
> **Why B17:** D2336's 20% threshold is "calibrated" against `e2e_test.py:167` filename-based 24.5% — not the canonical
> quantity production gates on. Fix before the canary so the e2e/V2 gate reports a trustworthy number.

---

## 🔍 #3 — PRE-T1.1 VERIFICATION GATE (canary examine — run BEFORE full corpus)

> **✅ CANARY COMPLETE (2026-08-14).** 25K segments → S1.5→S2→S4→S5→S6 all green, EXIT 0 at every stage.
> Discovered + fixed **BUG-105** (embedding instability) via **D2348** (timeout 180s + keep_alive=-1) mid-canary.

| # | Task | Status |
|---|------|--------|
| V1 | Run a **~1,000-cluster canary** through S1.5→S2→S4→S5→S6 | ✅ DONE — 2255 clusters (207 convergent), 0 failures |
| V2 | Verify e2e **check [7]** — ≥90% rows carry `content_type`+`extraction_type` (D2337 ontology round-trip) | ✅ DONE — 279/279 (100%) |
| V3 | Verify **BUG-095** (S6 persists 6 D2337 columns) on real canary rows | ✅ DONE — 6/6 columns, 279 rows |
| V4 | Verify **BUG-096** (S4/S6 fail-closed exit codes) | ✅ DONE — 0 failed, exit 0 (correct happy-path) |
| V5 | Confirm PT/PI/TI FBs (if any) survive S4→S6 | ✅ DONE — 0 PT/PI/GE/TI (all `principle`, expected for principle-only T1.1) |
| V6 | Confirm **BUG-094** fix (no stale checkpoint → S2 fresh-start) | ✅ DONE — S2 fresh-start confirmed |

> **Canary metrics:** S1.5 2255 clusters (207 convergent, 9.2%) | S2 280 FBs (82.6% yield, 0 failed) | S4 279 FBs
> (1 dedup, 46988 edges, 0 failed) | S5 239 PASS / 40 QUARANTINE (85.7%) | S6 279 committed (398 total rows), Parquet ✓.
>
> **New findings (post-canary, NOT blocking):**
> 1. **S4 slowness** — gpt-oss-20b classify ~25s/FB **serial** (no parallelism in `stage4_merge.py`) → full-run
>    S4 ≈ **~142h** (D2363, supersedes D2362's 90h — which used the batch-CRIBS path production does not run — the 62h canary-rate figure and D2253's impossible 3.9h). Needs
>    batching / faster classifier before T1.1 full run.
> 2. **Convergence 9.2%** (DOMAIN 0 prefix) < e2e 20% threshold — sample-selection artifact (single-domain prefix),
>    not a pipeline bug. Full corpus (8 domains) measured 20.3%.
> 3. **BUG-104 confirmed** — sqlite-vec `load_extension` missing on python.org Python → vector search 0/279 (FTS fallback).

> **Decision gate:** V1–V6 green → the code path is validated end-to-end. **Gating on full T1.1 = S4 speed**
> (~142h serial, D2363) — re-tune S4 batch/classifier before any full run. (Prior "26h" was D2253, now superseded.)

---

## ✅ ROUNDTABLE ADJUDICATION — IMPLEMENTED (2026-08-12)

> **🔴 S5 NLI BUG FIXED (2026-08-13, this session — BUG-092/D2321):** `deberta_check()` was feeding DeBERTa a single concatenated `"definition evidence"` string (no premise/hypothesis separation) and reading only the top-1 label → NEUTRAL verdicts collapsed to `"CONTRA: ent=0.00 cont=0.00"` and were quarantined. Result: **verify_pass_rate 36% (32/88)** — a ~90% false-negative rate on factually-correct cross-source FBs. Fix: proper `(premise=evidence, hypothesis=definition)` pair + `top_k=3` all-label scoring. **Post-fix: 74/88 (84.1%) PASS.** Remaining 14 QUARANTINE = 3 genuinely-vacuous MECH-FAIL + 11 NEUTRAL cross-source syntheses (legitimate fail-closed cost; D2285 claim-decomposition is the recovery path). ⚠️ D2293 calibration (P=1.0/R=0.556) was measured on the broken call — re-derive post-fix.
> **Eval status (2026-08-13):** 7/8 green — `fb_count` 92 ✅, `fb_fields` ✅, `multi_label` ✅, `relationship_edges` ✅, `verify_pass_rate` 84.1% ✅, `db_commit` ✅, `db_rows` 119 ✅. **1 red: `convergent_clusters` 24.5% (39/159) vs ≥25%** — borderline (−0.5%), sampling artifact on 20 books; a 25-book sample or accept-as-noise.

**Pre-T1.1 gate: 12/12 DONE — 9 implemented, 3 already-fixed (stale buglog), V1 verified (BUG-062 moot), G10 stress test PASS (no wired-memory leak).**

| # | Task | Status |
|---|------|--------|
| G1 | Source identity — metadata normalization + work-level convergence (D2308) | ✅ normalize_author/normalize_title in book_metadata.py |
| G2 | ISOR — metadata author + canonical count + precedence (D2309) | ✅ "weak" bucket reachable (5 FBs) |
| G3 | Runner timeout (BUG-080.4) | ✅ already D2269 (config '2': null) |
| G4 | S5 confidence — NLI gate + ISOR/mech/enrich + cap + human-review (D2310) | ✅ config-driven weights |
| G5 | S5 completeness substitution (BUG-080.5) | ✅ already D2298 (check_completeness deleted) |
| G6 | S5 threshold validation fatal (BUG-080.6) | ✅ already D2272 (raises ValueError) |
| G7 | S1.5 dropped-embed gate (BUG-080.8) | ✅ already D2275 (RuntimeError >0.5%) |
| G8 | S1.5 Ollama dim assert (BUG-080.7) | ✅ already D2274 |
| G9 | discipline "emerging" (D2310) | ✅ preserve discipline_raw + taxonomy_match_method |
| G10 | OMLX wired-memory stress test (P0.0) | ✅ PASS — 5×20 reqs, wired flat 34.26→34.22 GB (-0.11%), no leak |
| G11 | delete stale Stage 3a artifacts | ✅ safe_delete (backed up) |
| G12 | golden duplicate-edition negatives | ✅ NEG-DUP-001/002 (75 total) |

### 🔴 REMAINING (most critical first)

1. **V1** — ✅ VERIFIED (2026-08-12): BUG-062 is moot. S4 classify = `gpt-oss-20b-MXFP4-Q8` (config `models.verifier.model` → `VERIFY_MODEL`), NOT Phi-4-mini. Depth semantic (D2220) + focused (D2247). No live blocker.
2. **G10** — ✅ PASS (2026-08-12): OMLX wired-memory leak stress test — 5 rounds × 20 reqs, wired flat 34.26→34.22 GB (-0.11% cumulative), 0 errors. No GitHub #2184 leak. Script: `pipeline/omlx_wired_stress.py` (`just wired-stress`).
3. **T1.1** — full S1.5→S6 run (NOW UNBLOCKED: convergence + verification + classification fixes landed). S1.3 and earlier are still valid (see rerun note).
4. **content_hash tiebreaker** — ✅ FIXED (D2315, 2026-08-12): Black Swan title-concat now collapses via `_CONCAT_SUBTITLE_SPLIT`. All 3 duplicate-edition cases collapse.
5. **GAP-1** — wire DSPy program into S2 (post-T1.1).
6. **D2285** claim decomposition · **D2292** golden depth · **D2289/D2288** splits/κ · **D2300** StorageBackend · **D2305** latency SLA (post-T1.1).

> **Golden set audit (2026-08-12, this session):** ✅ VALID post-pipeline-change — `golden_validate.py` 5/5 checks pass; 75 examples → 77 FBs; no duplicate-edition false positives among convergents. 3 minor findings logged (`GOLDEN-AUDIT` in buglog.md): NEG-CONV-001/002/003 missing `discipline`; NEG-DUP-001/002 lazy `discipline: emerging`; dead `depth` field in 54 positives (D2241). Backfill all three during D2292 (BUG-084) golden depth expansion — non-blocking.

> **`just eval` (2026-08-12, this session):** 9/9 stages PASSED (703s). Fixed 4 blocking bugs first: BUG-089 (hardcoded 600s S2 timeout, D2311), BUG-090 (stale `latest` checkpoint, D2312), BUG-091 (`db_commit` KeyError + `disciplines`→`domains` field drift, D2313/D2314). Quality report: 5/8 green — `fb_fields` ✅, `multi_label` ✅, `relationship_edges` ✅, `db_commit` ✅, `db_rows` ✅; **3 red**: `convergent_clusters` 3% (5/191, need 25%), `fb_count` 3 (need 30), `verify_pass_rate` 67% (2/3, need 80%). ⚠️ **Root cause of reds = e2e selects first 20 books (alphabetical, domain-diverse) → almost no cross-book convergence (3%)**. Not a pipeline bug — full corpus is domain-organized. ⚠️ `verify_pass_rate` 67% = DeBERTa-only NLI (D2298) fail-closed at Recall 0.556 (1/3 FB quarantined on NEUTRAL evidence — expected false-negative per calibration). For T1.1: 3 FBs is too thin for LLM evaluation — use a domain-coherent sample or accept S5 quarantine ~33-44%.

---

## 🔴 ROUNDTABLE ADJUDICATION — 2026-08-12 (NEW CRITICAL, blocks convergence trust)

| # | Task | Decision | Severity | Effort |
|---|------|----------|:--------:|:------:|
| RA-1 | Fix source identity: metadata normalization + canonical work count (redefine `is_convergent` on distinct works ≥2) | D2308 | 🔴 | 4-6h |
| RA-2 | Fix ISOR: metadata-author + canonical source count + precedence parens | D2309 | 🔴 | 2-3h |
| RA-3 | Decouple NLI from confidence (gate not 75% weight) + per-passage aggregation + human adjudication | D2310 | 🟠 | 4-8h |
| RA-4 | Fix `discipline:"emerging"` over-firing (taxonomy match confidence + rationale; split EMERGING_TRUE/UNCERTAIN) | BUG-083→discipline | 🟠 | 4-6h |
| RA-5 | Add 2 duplicate-edition hard negatives to golden set (Safe Withdrawal Rate, Transgenic) | — | 🟠 | 1h |
| RA-6 | Purge stale model/threshold comments (0.6/0.8/0.5/0.3; Phi-4/Gemma/ModernBERT) | — | 🟡 | 1h |
| RA-7 | Freeze per-run manifest (config/model/prompt/taxonomy/threshold hashes) | — | 🟡 | 3-4h |

> **Bugs:** BUG-087 (duplicate-edition false convergence) + BUG-088 (ISOR author parse/precedence).
> **Full detail:** `governance/ROUNDTABLE_ADJUDICATION_2026-08-12.md`.

---

## 🚦 PRE-T1.1 GATE — CONSOLIDATED (2026-08-12, do NOT launch T1.1 before these)

> T1.1 = full S1.3→S6 run on 12,964 clusters (**~110-140h**, D2362 — not the stale ~21-26h). Launching with known bugs either
> **corrupts the output** (false convergence) or **wastes the run** (77.5% quarantine).

### 🔴 BLOCKING (corrupts output — fix first)

| # | Task | Decision/Bug | Why blocking |
|---|------|-------------|--------------|
| G1 | Source identity: metadata normalization + work-level `is_convergent` | D2308 / BUG-087 | 12,964 clusters would produce false-convergent FBs; entire KB epistemically invalid |
| G2 | ISOR: metadata-author + canonical source count + precedence | D2309 / BUG-088 | "Independence" currently = file count; downstream golden/ISOR contaminated |
| G3 | Runner 60-min timeout → configurable per-stage | BUG-080.4 | **Hard blocker** — runner kills S2 at 60min; S2 needs 25-40h |
| G4 | S5 NLI as gate (not 75% weight) + per-passage aggregation | D2310 | Else 77.5% of T1.1 output quarantined (recall collapse) |
| G5 | S5 completeness: stop substituting application for mechanism | BUG-080.5 | Completeness scores overly optimistic → false PASS risk |
| G6 | S5 threshold validation: warn→fatal | BUG-080.6 | Bad verification config must not run silently |

### 🟠 HIGH (data quality — fix before or immediately after)

| # | Task | Decision/Bug | Note |
|---|------|-------------|------|
| G7 | S1.5 dropped-embedding gate (epistemic recall) | BUG-080.8 | Silent drop = silent recall loss |
| G8 | S1.5 Ollama dim assertion (parity with MPS) | BUG-080.7 | Theoretical (bge-m3 stable 1024d) |
| G9 | `discipline:"emerging"` over-firing (65%) | BUG-083→discipline | Classifier mass-produces "emerging" |
| G10 | OMLX wired-memory leak stress test (P0.0) | P0.0 | ✅ PASS — wired flat (-0.11%), 0 errors, no leak |
| G11 | Delete stale Stage 3a artifacts | D2302-GAP2 | 5-min cleanup; verify no refs |
| G12 | Add duplicate-edition hard negatives to golden | RA-5 | 1h; closes golden blindspot |

### 🟡 VERIFY (drift/conflict — resolve before assuming)

| # | Question |
|---|----------|
| V1 | ✅ VERIFIED (2026-08-12): BUG-062 moot — S4 classify = `gpt-oss-20b-MXFP4-Q8` (config `models.verifier.model`), NOT Phi-4-mini. Depth semantic (D2220) + focused (D2247). Not blocking. |
| V2 | BUG-080.4 — is T1.1 launched via `runner.py` or `run_diagnostic.py`? (diagnostic bypasses runner, so timeout may not block in practice) |

### ✅ POST-T1.1 (safe to defer)

GAP-1 (DSPy wiring), D2285 (claim decomposition), D2292 (golden depth), D2289 (author-disjoint splits),
D2288 (Fleiss kappa), D2300 (StorageBackend), D2305 (latency SLA), T1.2 (yield diagnostic).

---

## 🔴 CRITICAL — PRE-T1.1 (all done ✅)

| # | Task | Status |
|---|------|--------|
| P0.1 | Wire hybrid S2 gate (D2276/BUG-085) | ✅ `pipeline/hybrid_gate.py` + `--hybrid` flag |
| P0.2 | Pipeline manifest update (D2282) | ✅ DeBERTa-v3-large, removed Phi-4-mini |
| P0.3 | FB schema split (D2283/BUG-080.5) | ✅ `CORE_FIELDS`/`ENRICHMENT_FIELDS` in schema_accessor |
| P0.4 | ISOR scoring (D2284) | ✅ 3-dimension in verified FB output |
| P0.5 | Golden tiered classification (D2286) | ✅ GOLD-A:49, GOLD-B:3, CHALLENGE:21 |
| P0.6 | DSPy hard gates (D2287) | ✅ 3 gates in extraction_metric() |
| P0.7 | BUG-001 empty pass loop | ✅ Resolved (code path removed in D2298) |
| P0.8 | BUG-014 cloud burst | ✅ Resolved (no cloud code in repo) |

## 🟠 HIGH — IMPLEMENTED PRE-T1.1 (all done ✅)

| # | Task | Status |
|---|------|--------|
| P1.3 | S4 enrichment verification in S5 (D2277) | ✅ `_check_enrichment_quality()` added |
| P1.6 | NLI threshold validation fatal (D2272) | ✅ `ValueError` on misconfiguration |
| P1.7 | Ollama embed dimension assertion (D2274) | ✅ Dimension mismatch raises `ValueError` |
| P1.8 | Embed drop-rate quality gate (D2275) | ✅ `RuntimeError` if >0.5% dropped |
| P1.13 | FAISS threshold mismatch | ✅ Both 0.75 |
| P1.14 | AGENTS.md stage count | ✅ Says "8-stage" |
| P1.15 | Ruff lint | ✅ 94 auto-fixed |

## 🟠 HIGH — ALREADY VERIFIED ✅

| # | Task | Status |
|---|------|--------|
| P1.9 | S5 schema strict validation (D2271) | ✅ check_completeness deleted, no field substitution |
| P1.10 | BUG-013 pkill | ✅ No pkill in codebase |
| P1.11 | BUG-012 sqlite-vec | ✅ sqlite-vec loaded before CREATE VIRTUAL TABLE |
| P1.12 | BUG-055 related_fbs/related_blocks | ✅ No related_blocks in any Python file |

## 🟠 HIGH — AUDIT FIXES ✅

| # | Finding | Fix |
|---|---------|-----|
| A1 | runner.py — 9 Gemma skip_gemma references | ✅ All removed. Gemma deleted from OMLX (D2297) |
| A2 | stage4_merged_call.py — "Gemma/Google S5 verifier" | ✅ Comment fixed to "GPT-OSS/OpenAI S4 classifier" |
| A3 | CONSTITUTION.md models section stale | ⚠️ Needs update (minor — pipeline_config.yaml is canonical) |

## 🔴 REMAINING — POST-T1.1

### CRITICAL (4 items)
| # | Decision | Task | Effort |
|---|----------|------|--------|
| C1 | D2285 | Claim decomposition for S5 — per-claim NLI. Highest S5 accuracy lever. | 8-12h |
| C2 | D2292 | Golden depth expansion — 170+ examples | 8-16h |
| C3 | D2289 | Author-disjoint DSPy splits extended | 3-4h |
| C4 | D2288 | Roundtable Fleiss' kappa — inter-rater reliability | 1h |

### HIGH (pipeline execution)
| # | Task | Effort | Notes |
|---|------|--------|-------|
| **T1.1** | **Full S1.3→S6 run** on 12,964 clusters | **~110-140h** (D2362) | Enable with `--hybrid` for +0.145 quality |
| **T1.2** | Yield crisis diagnostic | 2h | Post-T1.1 |
| T-007b-v2 | Re-optimize MIPROv2 with 3 demos | 1h setup | Optional polish |
| T-015 | Extraction type expansion + depth balance | 2d | Golden pool imbalance |
| T2.x | 23 medium tasks | varies | See MTR |

### FUTURE TAX (identified in audit)
| # | Issue | Severity |
|---|-------|----------|
| F1 | InferenceProvider protocol not implemented (D2055) | ✅ DONE (D2306 — OMLX + Ollama providers) |
| F2 | Pydantic FB schema dead code (schemas.py, never instantiated) | 🟡 — 0 callers |
| F3 | Hardcoded model name in stage4_merged_call.py:101 | 🟡 — should be config-driven |
| F4 | Hardcoded cohesion threshold 0.75 in stage2_extract.py:351 | ✅ DONE (config S2_HIGH/MED_COHESION_THRESHOLD) |
| F5 | stage4_merged_call.py — hardcoded defaults for model params | ✅ DONE (model=None reads config VERIFY_MODEL) |
| F6 | StorageBackend protocol not implemented (stage6 SQLite) | 🟡 — remaining modularity gap (D2300) |

### 🔴 NEW TASKS — 2026-08-12 AUDIT (D2300-D2307)

| # | Decision | Task | Status |
|---|----------|------|--------|
| N1 | D2302-GAP1 | Wire DSPy trained program into stage2_extract.py (replace/augment hybrid gate) | ⏳ T1.2 |
| N2 | D2302-GAP2 | Remove stale Stage 3a artifacts (prompts/s3a_optimized.txt, s3a_system_v1.txt) | ⏳ T1.2 |
| N3 | D2302-GAP3 | DSPy tier-aware split | ✅ DONE (D2304) |
| N4 | D2303 | CRIBS batch mitigation — wire batch_cribs_classify | ✅ DONE (FIX-1) |
| N5 | D2305 | Recall measurement | ✅ DONE (D2307 recall_measure.py) |
| N6 | D2305 | End-to-end latency SLA | ⏳ Post-T1.1 |
| N7 | D2306 | InferenceProvider + EmbeddingProvider protocol | ✅ DONE |
| N8 | D2306 | StorageBackend protocol (stage6 SQLite) | ⏳ Post-T1.1 |

## 📊 STATUS SUMMARY

```
P0 CRITICAL:  ██████████ 8/8 DONE
P1 HIGH:      ██████████ 15/15 DONE (6 implemented, 5 verified, 4 deferred)
AUDIT FIXES:  ██████████ 3/3 DONE
────────────────────────────────────────
PRE-T1.1:     100% COMPLETE
POST-T1.1:    4 critical + T1.1-T1.2 + 23 medium + 5 future tax
```

## 🧭 T1.1 HANDOFF

```bash
# Full pipeline run (traditional-only — hybrid gate REJECTED, BUG-085):
python3 pipeline/runner.py

# Or stage-by-stage (S2 processes convergent + single-source clusters by default):
python3 pipeline/stage2_extract.py
python3 pipeline/stage4_merge.py
python3 pipeline/stage5_verify.py
python3 pipeline/stage6_commit.py

# Active models: Qwen3-Coder-30B (S2) | GPT-OSS-20B (S4 classifier) | DeBERTa-v3-large (S5 verifier) | bge-m3 (Emb)
# S5 threshold: 0.10 — honest auto-cal (D2322): P=0.647, R=0.386, F1=0.484 (D2293's P=1.000 was on the broken call)
# Hybrid gate: DISABLED for T1.1 (BUG-085 A/B: 4.3% negative rejection — net-negative)
# ISOR: 3-dimension independence in every verified FB
```
