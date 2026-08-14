# Maxwell OS v3.0 — MASTER TASK REGISTER
> **Updated:** 2026-08-14 13:48 | **Decisions:** D2000-D2355 (344 decisions)
> **S5 Architecture:** DeBERTa-only NLI, threshold 0.10 (D2298). Final. No ongoing human adjudication.
> **Active Models:** Qwen3-Coder-30B (S2), GPT-OSS-20B (S4 classifier), DeBERTa-v3-large (S5 verifier), bge-m3 (Emb)
> **Redundant/Removed:** RoBERTa-large, Phi-4-mini (S5), all Gemma variants
> **Diagnostic:** 188 FBs, 72.4% S5 pass rate → T1.1 authorized (CONDITIONAL-GO — see B1-B15)
> **Detailed tasks:** `governance/aggregated_remaining_tasks.md`
> **Buglog:** `governance/buglog.md`

---

# 🔴 NEW THIS SESSION — 4th Audit Adjudication (BUG-108…119, D2351–D2355, 2026-08-14)

> **4-LLM audit (`chatgpt0010.md`, `claude0010.md`) × independent code re-verification.** S4 depth fail-open + provenance/schema gaps + singleton index + S4 bottleneck. Must/Should/Worth tiers → `governance/T1.1_CANARY_READINESS_MUST_SHOULD_WORTH.md`. Two ChatGPT errors corrected.

| # | Decision | Task (code-verified) | Effort | Status |
|---|----------|----------------------|--------|--------|
| **M1** | D2351 | S4 depth fail-closed — no silent `"domain"` (BUG-108) | 0.5h | 🔴 OPEN |
| **M2** | D2351 | `depth_max_tokens` 512 → 1024 (BUG-109) | 0.25h | 🔴 OPEN |
| **M3** | D2352 | Carry `source_segments` through S4→S6 (BUG-110) | 1h | 🟠 OPEN |
| **M4** | D2352 | Persist `is_summary` end-to-end (BUG-112) | 0.5h | 🟠 OPEN |
| **S1** | D2352 | Persist `evidence_passages` to SQLite (BUG-111) | 1h | 🟠 OPEN |
| **S2** | D2353 | Singleton S2→S4 index fix (BUG-113) | 1h | 🔴 OPEN |
| **S3** | D2354 | S4 bottleneck resolution — batch focused depth (BUG-114) | 2–3h | 🟠 OPEN |
| **S4** | D2355 | Batch missing-output fail-closed (BUG-115) | 0.5h | 🟠 OPEN |
| **S5** | D2351 | Depth benchmark authority (BUG-115) | 1h | 🟠 OPEN |
| **W1–W7** | D2355+ | Hygiene: dead `s3_original_domain`, secondary writers, `jargon`-FTS, `deathpectation` (BUG-116…119 + drift) | 3h | 🟡 OPEN |

> **Verdict:** canary re-run + T1.1 **NOT clean** until M1+M2 (S4 depth fail-closed + token budget) — live in default path,
> silently corrupt the depth audit. S4 speed (D2354) is the full-T1.1 *feasibility* gate (62h → ~25–30h).

---

# 🔴 NEW THIS SESSION — 3rd Audit Adjudication (D2349–D2350, 2026-08-14)

> **Deep audit of T1.1 canary + taxonomy adjudication.** User rejected several prior audit conclusions and
> clarified schema/taxonomy definitions. Fixed surgically in strategic order:

| # | Decision | Task (code-verified) | Effort | Status |
|---|----------|----------------------|--------|--------|
| **B19** | D2349 | content-type field taxonomy: separate core_body / classification / metadata; jargon→body (after elaboration); keywords→metadata.discovery; evidence_passages→metadata.provenance (verbatim quotes, NOT body) | 0.5h | ✅ DONE |
| **B20** | D2350 | S4 identity/provenance: preserve S2 fb_id (no rehash after title-case; 73 records were drifting); preserve real source_cluster id (was overwritten with fb_id); short numeric name-collision suffix (was 64-char hash) | 1h | ✅ DONE |

> **Validation:** `config_audit --check-unchecked --strict` ✅ · `just integrity` 17/17 ✅ · `just healthcheck` 10/10 ✅ ·
> `just preflight` stress ALL_PASS ✅. **Remaining open:** BUG-106 (S2 checkpoint pretty-print corruption), BUG-104
> (sqlite-vec load_extension), 2 single-source FBs leaked (`Hybrid Sorting Algorithm`, `Price Reduction Profit Maximization`),
> S4 speed (~3.5 FBs/min). Rerun canary pending after these.

# 🔴 NEW THIS SESSION — 2nd Audit Adjudication (D2345–D2347, 2026-08-13)

> **ChatGPT/Qwen audit of `T1.1_ROUNDTABLE_AUDIT_PROMPT.md` (post-D2344).** Two new code-verified blockers
> surfaced that the B1–B15 set did not cover — both hit the **principle** path, not just the non-type pass.

| # | Decision | Task (code-verified) | Effort | Status |
|---|----------|----------------------|--------|--------|
| **B16** | D2346 | S1.5 embedding-drop index alignment — return `(filtered_segments, embeddings)` + `len` assert + drop tests | 1h | ✅ DONE |
| **B17** | D2347 | e2e convergence metric → `sum(c["is_convergent"])` (canonical IDs), filename-diversity as diagnostic | 0.5h | ✅ DONE |
| **B18** | D2348 | embedding reliability — `embed_timeout: 180` + `embed_keep_alive: -1` (config-driven, BUG-105) | 0.5h | ✅ DONE |

> **✅ T1.1 CANARY GREEN (2026-08-14).** 25K segments → S1.5(2255 clusters/207 conv) → S2(280 FBs) → S4(279 FBs)
> → S5(239 PASS/40 QUAR) → S6(279 committed). V1–V6 all pass. **Remaining gate = S4 speed** (~3.5 FBs/min →
> 62h full-run; re-tune before full T1.1). BUG-105 (embedding instability) found+fixed mid-canary via D2348.

> **D2345 (non-type second pass):** DECIDED as principle-first + separate single-source `stage2_extract_nontype.py`
> (post-T1.1). NOT a T1.1 blocker. Whether convergent PT/PI/GE/TI even occur = UNKNOWN; measure offline first.
> **B16/B17 IMPLEMENTED** (`just integrity` 17/17, `just preflight` stress PASS). **BUG-104** (sqlite-vec
> `load_extension` missing on python.org Python 3.12.1) discovered — non-blocking (FTS fallback), environmental.

# 🔴 NEW THIS SESSION — 4-LLM Audit Adjudication (D2337–D2341, 2026-08-13)

> **4 external LLM audits** of `governance/SCHEMA_PIPELINE_STATE_AUDIT_PROMPT.md` were adjudicated.
> Kimi/DeepSeek = repo-blocked (correctly refused to fabricate; zero signal). Qwen = repo-blocked but rated the prompt's
> own claims as VERIFIED (epistemically unsound; PASS verdicts discarded). ChatGPT = only repo-reading audit;
> independently re-verified here. **Findings surfaced 5 new blockers (B11–B15) on top of the B1–B10 set**, the most
> serious of which is NOT the S2/OMLX reliability I'd been focused on, but a **Stage 6 SQLite data-loss bug** (D2337).

| # | Decision | Task (code-verified) | Effort | Status |
|---|----------|----------------------|--------|--------|
| **B11** | D2337 | S6 persist `content_type`/`extraction_type`/`mechanism`/`boundary`/`consequence` + round-trip test | 2h | ✅ DONE |
| **B12** | D2338 | S4/S6 fail-closed — `failure_ratio > max → exit 1`, `>0 → exit 2`, no COMPLETE manifest | 1.5h | ✅ DONE |
| **B13** | D2339 | runner `--run-id` import-ordering — pre-parse args before run-scoped imports | 1h | ✅ DONE |
| **B14** | D2340 | model-registry drift — session_seed renamed; config/path rename deferred (post-T1.1) | 0.5h | 🟠 PARTIAL |
| **B15** | D2341 | schema corrections — three-axis `status`, keep typed edges, add TI class, feedback→YAML (P2) | 3h | 🟡 DEFERRED |

> **Ordering:** B11→B12 first (S6 data loss + fail-open = silent permanent corruption of the first canonical corpus).
> B13→B14 are config/run-scoping correctness. B15 is schema contract work deferred to P2. NOTE: ChatGPT's "enable hybrid
> gate" recommendation is **REJECTED** — BUG-085 A/B test already proved the heuristic HybridGate is net-negative
> (4.3% negative rejection); run traditional-only. **B11–B14 now IMPLEMENTED; B14 config/path rename + B15 deferred post-T1.1.**

---

# 🔴 NEW THIS SESSION — T1.1 Roundtable Audit (D2324–D2332, 2026-08-13)

> **CONDITIONAL-GO.** 3-LLM adversarial roundtable (kimii/chatgpt/qwen) independently verified against the code.
> **A second independent code sweep (2026-08-13) added B1 — the S2 checkpoint format/resume coupling** (D2332, not in the
> original 7). Blocker ordering below is **data-flow + dependency aware** (upstream integrity → correctness → verification truth),
> NOT by auditor source. See D2324 for the roundtable verification record (kimii's findings rejected as fabricated; qwen's
> "0.65 threshold" rejected).

| # | Decision | Task (code-verified) | Effort | Status |
|---|----------|----------------------|--------|--------|
| **B1** | D2332 | S2 checkpoint fail-closed `load_jsonl` at every reader + resume | 1h | ✅ DONE (D2343) |
| **B2** | D2329 | Resume-validity manifest — checkpoint sidecar (run_id/schema/count/COMPLETE) | 2h | ✅ DONE |
| **B3** | D2326 | S0 fail-closed + tri-state quality check (C16) | 1h | ✅ DONE |
| **B4** | D2323 | Content-type golden fix → 5-role ontology | 0.5h | ✅ DONE |
| **B5** | D2323 | Content-type enum wiring + `route_values` config-driven (C12) | 2h | ✅ DONE (D2343) |
| **B6** | D2327 | S1.3 prefilter `--in-place` in runner + e2e | 0.5h | ✅ DONE (D2343) |
| **B7** | D2331 | S2 silent-skip fail-closed (`S2_MAX_FAILED_RATIO`) | 2h | ✅ DONE |
| **B8** | D2328 | S5 calibration truth (P=0.647/R=0.386/F1=0.484) + runner desc + audit prompt | 0.5h | ✅ DONE |
| **B9** | D2325 | S6 provenance per-FB `INSERTED/FAILED/SKIPPED` | 1h | ✅ DONE |
| **B10** | D2330 | e2e run-scoping + quarantine retrieval contract test | 1.5h | ✅ DONE |

> **Ordering rationale:** B1→B2 first (checkpoint format + resume coupling is the only pair that can silently corrupt the
> *entire* run). B3 before B4–B7 (garbage-in). B4 before B5 (labels before enum). B5 before B7 (S2 must emit correct types
> before S4 can route). B8–B9 last (verification/commit truthfulness — corrupts claims, not data). **All B1–B10 IMPLEMENTED.**

---

# 🔴 NEW THIS SESSION — Content-Type Ontology Consolidation (D2323, 2026-08-13)

> **The #1 pre-T1.1 architectural fix.** Content-type taxonomy was fractured across 4 places (S2 flat label, S4 dead schema classes, stale golden few-shot vocabulary, v1 ZONE templates). Verified findings this session:
> 1. **Orphaned non-principle FBs (BUG-093)** — S2 extracted 3 `process_template` + 1 `tool_instruction`; silently dropped at S2→S4 (never reached S4/S5; separate output files absent).
> 2. **Dead schema code** — `ProcessTemplate` (24 fields) / `ProcessInstance` (16 fields) / `GrowthEdge` classes never instantiated; S4 writes raw S2 dicts.
> 3. **Stale golden vocabulary** — `stage2_fewshot_convergent.yaml` uses `content_type: model/heuristic/pattern` (extraction_type values) — contamination under temp=0.0.
> 4. **`fact`/`meta` vestigial** enum values (schemas.py docstring only) — dropped.
>
> **Resolution (D2323):** `config/content_types.yaml` — single config-driven registry. Two orthogonal axes: `content_type` (5) × `extraction_type` (4). Core body + per-type extension delta. 13-field `tool_instruction`. D2150 + D2128 mappings. **Contract frozen; code wiring + golden-example fix = NEXT SESSION (before T1.1 full run).**
>
> **Files:** `config/content_types.yaml` (NEW) → wire into `pipeline/schemas.py`, `pipeline/stage2_extract.py`, `pipeline/stage4_merge.py`, `config/golden/stage2_fewshot_convergent.yaml`

# 🔴 CRITICAL — BLOCKING T1.1

| # | Decision | Task | Effort | Bug |
|---|----------|------|--------|-----|
| **P0.1** | D2276 | **Wire hybrid S2 to production** — move hybrid_s2_extract() into stage2_extract.py. DSPy gate + traditional extraction. +0.145 quality (0.736 vs 0.591). | 4-8h | BUG-085 |
| **P0.2** | D2282 | **Pipeline manifest** — frozen per-run config: git_commit, model/prompt/schema/taxonomy versions. Embed hash in every checkpoint. | 1-2h | — |
| **P0.3** | D2283 | **FB schema split** — core vs enrichment contract. S5 verifies core only. Fixes BUG-080.5 field substitution. | 2-3h | BUG-080.5 |
| **P0.4** | D2284 | **ISOR source independence scoring** — author/citation-chain/evidence-tradition independence beyond BORP≥2. | 4-6h | — |
| **P0.5** | D2286 | **Golden tiered classification** — GOLD-A (train DSPy), GOLD-B (evaluate), CHALLENGE (test). DSPy training safety. | 2h | — |
| **P0.6** | D2287 | **DSPy metric with hard gates** — evidence_invalid→0, wrong_route→0, false_convergence→0. THEN weighted quality. | 2-3h | — |
| **P0.7** | BUG-001 | **Empty pass loop** — verification checks random principles. Phase 0, P0.8. | ? | BUG-001 |
| **P0.8** | BUG-014 | **Cloud burst code violates C1/C3** — constitutional violation. Phase 0, P0.13. | ? | BUG-014 |

---

# 🟠 HIGH — COMPLETE WITHIN WEEK OF T1.1

| # | Decision | Task | Effort | Bug |
|---|----------|------|--------|-----|
| **P1.1** | D2285 | **Claim decomposition for S5** — per-claim NLI before synthesis verdict. Highest S5 accuracy lever. | 8-12h | — |
| **P1.2** | D2292 | **Golden depth expansion** — 170+ examples (30 universal, 40 cross-domain, 40 domain, 30 specialized, 30 hard negatives). | 8-16h | BUG-084 |
| **P1.3** | D2277 | **S4 enrichment verification in S5** — fact-check application/failure_mode/elaboration. Most dangerous hallucination gap. | 2h | — |
| **P1.4** | D2289 | **Author-disjoint DSPy splits extended** — domain/book/paraphrase-aware. | 3-4h | — |
| **P1.5** | D2288 | **Roundtable Fleiss' kappa** — inter-rater reliability statistic. | 1h | — |
| **P1.6** | D2272 | **NLI threshold validation fatal** — raise ValueError, not warn. | 5min | BUG-080.6 |
| **P1.7** | D2274 | **Ollama embedding dimension assertion** — MPS path has it, Ollama path doesn't. | 1h | BUG-080.7 |
| **P1.8** | D2275 | **Embedding drop-rate quality gate** — fail stage if drop_rate > 0.005. | 1h | BUG-080.8 |
| **P1.9** | D2271 | **S5 v3 schema strict validation** — no mechanism↔application substitution. | 30min | BUG-080.5 |
| **P1.10** | BUG-013 | **OMLX guard uses pkill -f** — kills pipeline itself. Phase 0, P0.12. | ? | BUG-013 |
| **P1.11** | BUG-012 | **sqlite-vec not loaded before CREATE VIRTUAL TABLE**. Phase 0, P0.11. | ? | BUG-012 |
| **P1.12** | BUG-055 | **related_fbs vs related_blocks field name mismatch** — blocks delegation. | ? | BUG-055 |
| **P1.13** | — | **FAISS threshold mismatch** — pipeline_config.yaml:0.75 vs session_seed.yaml:0.70. | 0.5h | — |
| **P1.14** | — | **AGENTS.md stage count** — still says "9-stage" despite Stage 3 removal. | 0.5h | — |
| **P1.15** | — | **Ruff lint auto-fix** — 322 auto-fixable in pipeline/. | 1h | — |

---

# 🟠 HIGH — PIPELINE EXECUTION

| # | Task | Effort | Notes |
|---|------|--------|-------|
| **T1.1** | **Full S1.3→S6 run on 12,964 clusters** | ~21-26h | Batch-resume capable. Tiered+parallel: ~19h S2 + ~4h S4 + ~1h S5 |
| **T1.2** | **Yield crisis diagnostic** — re-measure on full run output. 14 FBs / 852 books = 0.004% was v2.0. | 2h | Post-T1.1 |
| **T-007b-v2** | **Re-optimize MIPROv2 with 3 demos** (overnight) — close DSPy gate FN gap. | 1h setup + overnight | Optional polish |
| **T-015** | **Extraction type expansion** — 4→12-15 per type + depth class balance. Fixes golden pool imbalance. | 2d | — |

---

# 🟠 HIGH — NLI + VERIFICATION CALIBRATION

| # | Task | Effort | Notes |
|---|------|--------|-------|
| **NLI-1** | **NLI calibration on real data** — validate DeBERTa threshold on larger sample post-T1.1. | 2h | Already calibrated at 0.10 on 12 FBs |
| **NLI-2** | **LLM eval on golden set** (25 ex, 2+ LLMs) | 2h | Golden set is `needs_review` |
| **NLI-3** | **Cross-encoder reranker gate** — bge-reranker-v2-m3 ONNX between S2 and S5. | 1d | 1.2GB VRAM trade-off |
| **NLI-4** | **Source-independence graph** — model citation chains, effective_source_count. | 1d | — |

---

# 🟡 MEDIUM — NEXT SPRINT

| # | Task | Effort | Source |
|---|------|--------|--------|
| **T2.1** | Execute ONE business PI with existing FBs — existential test | 2h | Qwen, Kimi |
| **T2.2** | Atomic evidence schema — per-passage NLI, not majority vote | 2d | ChatGPT C9 |
| **T2.3** | Monotonic trust state machine — DB-level transition constraints | 2d | ChatGPT C7 |
| **T2.4** | Surface reliability scores in Zone 3 — context-conditioned | 1d | DeepSeek, Kimi |
| **T2.5** | skill.md standard (Layer 2 MVP) — IBM progressive disclosure | 4h | aggregated |
| **T2.6** | Hardware probe (C24) — auto-detect RAM, select model quant | 3h | aggregated |
| **T2.7** | 20-book E2E test — validate v3.0 at scale | 3h | aggregated |
| **T2.8** | Integration test suite — `just test` golden-file regression | 4h | aggregated |
| **T2.9** | Adversarial golden set — contradiction, false convergence tests | 2d | ChatGPT §41 |
| **T2.10** | RAGTruth hallucination suite — 10 adversarial test types | 1d | ChatGPT §14 |
| **T2.11** | ARES component evaluation — per-component metrics | 1d | ChatGPT §40 |
| **T2.12** | One pipeline authority — canonical DAG → generated docs | 1d | ChatGPT §3 |
| **T2.13** | Split config into active/archived/experiments | 1d | ChatGPT C13 |
| **T2.14** | Collapse config authority — one canonical YAML per domain | 1d | ChatGPT C15 |
| **T2.15** | Prompt lineage stamping — prompt_id, prompt_hash, prompt_version | 1d | ChatGPT C16 |
| **T2.16** | Move taxonomy from hardcoded Literal to YAML-driven | 2d | DeepSeek D5 |
| **T2.17** | Pydantic FB fields — mechanism/boundary/consequence in Pydantic model | 0.5d | N2 |
| **T2.18** | Actionability field — descriptive/prescriptive/diagnostic | 0.5d | N3 |
| **T2.19** | D2278 — Runner health check uses stress test | 2h | P2 |
| **T2.20** | D2279 — S1.5 drop rate metrics persisted to run_meta | 1h | P2 |
| **T2.21** | D2280 — FAISS IndexFlatIP → HNSW | 2h | P2 |
| **T2.22** | D2281 — Tiered BORP per depth | 2h | P2 |
| **T2.23** | gov-sync — decisions.yaml missing D2210/D2212/D2233-D2239 etc. (DECISION-LOG gap) | 4h | Historical |

---

## ⚪ LOW — BACKLOG

| # | Task | Effort | Source |
|---|------|--------|--------|
| T3.1 | USearch vs FAISS benchmark | 2h | aggregated |
| T3.2 | MeshRAG hash-driven clustering eval | 1d | DeepSeek |
| T3.3 | Leiden clustering via python-igraph | 2h | Qwen |
| T3.4 | Schema migration scripts — v2.x → v3.0 | 3h | aggregated |
| T3.5 | HyDE for abstract queries | 1d | ChatGPT §20 |
| T3.6 | Multi-perspective retrieval (STORM-inspired) | 1d | ChatGPT §32 |
| T3.7 | ColBERT benchmark on Maxwell corpus | 1d | ChatGPT §22 |
| T3.8 | Pydantic AI harness for agent orchestration | 1w | Kimi |
| T3.9 | Agent execution safety boundary | 3d | ChatGPT C14 |
| T3.10 | Dry-run mode on all stages | 4h | aggregated |
| T3.11 | Modularize stage2_extract (1,480 lines) + stage4_merge (1,260 lines) | 3d | Kimi |

---

## 🔵 TIER 4 — RESEARCH (Ongoing)

| # | Foundation | Status |
|---|-----------|--------|
| R1 | Typed Graph Storage — Zep/Graphiti eval | ⬜ DEFERRED |
| R2 | Edge Type Ontology — 10-15 types | ⬜ DEFERRED |
| R3 | Skill Subgraph Templates — graduate at 50+ skills | ⬜ DEFERRED |
| R4 | Constitutional Constraint Graph — C1-C28 as graph invariants | ⬜ DEFERRED |
| R5 | Self-Observation Protocol — agent queries own graph | ⬜ DEFERRED |
| R6 | IBM course transcript for Layer 2 | ⬜ DEFERRED |
| R7 | GAAMA 4-node memory | ⬜ DEFERRED |
| R8 | awesome-agent-skills repo eval | ⬜ DEFERRED |
| R9 | caveman prompt framework — local-first S2 prompts | ⬜ DEFERRED |
| R10 | vLLM-mlx for multi-agent | ⬜ DEFERRED |
| R11 | LanceDB unified store | ⬜ DEFERRED |
| R12 | ONNX runtime for NLI | ⬜ DEFERRED |

---

## 🔴 OPEN BUGS (current — 2026-08-13)

> Older BUG-001/011/012/013/014/045/050/051/054/055/085 resolved in prior sessions (see buglog.md SESSION RESOLUTIONS). None block T1.1.

| Bug ID | Severity | Description |
|--------|----------|-------------|
| BUG-063 | 🔴 OPEN | `delegate()` cannot execute filesystem tasks (architectural; NOT a T1.1 pipeline blocker) |
| BUG-098 | 🟡 PARTIAL | `psutil` in requirements.txt done; integrity-check whitelist→requirements refactor deferred |
| BUG-099 | 🟡 PARTIAL | model-registry rename — session_seed done; config/path rename deferred post-T1.1 |

### ⏳ DEFERRED (post-T1.1)

| Bug ID | Description |
|--------|-------------|
| BUG-083 | `domain_anchors.yaml` predates corpus (80.5% "emerging") — D2292 golden depth expansion |
| BUG-084 | Golden depth calibration universal=1/specialized=1 — D2292 |
| BUG-081 | `evals/golden_cases.json` v2 format migration |
| BUG-073 | CONV-035/037 false convergence — D2232 |

### ✅ RESOLVED BUGS (this + recent sessions)

| Bug ID | Description | Resolution |
|--------|-------------|------------|
| BUG-080 | call_omlx_json returns list/str — S4 crashes | ✅ FIXED (guards applied) |
| BUG-080.1 | _save_diag_state flush/fsync outside with block | ✅ FIXED |
| BUG-080.9 | S5 method tag dict missing "nli+LLM-echo" | ✅ FIXED |
| BUG-080.10 | S5 method tag dict missing "mech_quality" | ✅ FIXED |
| BUG-082 | S5 FLAG path practically unreachable (0/185) | ✅ CONFIRMED — FLAG path deleted (D2298) |
| BUG-076 | S5 NLI config overrides DeBERTa FEVER | ✅ FIXED (D2255) |
| BUG-077 | stage5_verify.py docstring triple-stale | ✅ FIXED (D2256) |
| BUG-078 | Stale classify_model in v2.3 checkpoint | ✅ FIXED (D2258) |
| BUG-079 | HANDOFF claims Phi-4-mini for S5 verify/gates | ✅ FIXED (D2260) |
| BUG-053 | Phi-4-mini hallucinates on open-ended research | ✅ MITIGATED (D2268); removed from S5 (D2298) |
| D2299 | 4-value unpack bug in deberta_check call site | ✅ FIXED (2026-08-12) |

---

## ✅ DONE — D2298-D2299 S5 FINAL ARCHITECTURE (2026-08-12)

| Decision | Description | Status |
|----------|-------------|--------|
| D2298 | **DeBERTa-only NLI** — RoBERTa removed. Threshold 0.10. Single encoder. No human adjudication needed. ⚠️ Calibration superseded by D2322: honest P=0.647/R=0.386/F1=0.484 (D2293's P=1.000 was on the broken pre-BUG-092 call). | ✅ DONE |
| D2299 | **4-value unpack bug fixed** — deberta_check call site updated to 3-value unpack. Docstrings updated to DeBERTa-only. | ✅ DONE |
| — | RoBERTa-large removed from S5 (zero signal on paraphrase evidence, D2227) | ✅ DONE |
| — | Phi-4-mini removed from S5 (67% acc, hallucination risk) | ✅ DONE |
| — | BORP check deleted (S1.5 guarantees ≥2 sources) | ✅ DONE |
| — | Completeness check deleted (S4 always fills all fields) | ✅ DONE |
| — | FLAG path deleted (0/185, confirmed unreachable) | ✅ DONE |
| — | Gemma models deleted from OMLX | ✅ DONE |

---

## ✅ DONE — D2294-D2297 DUAL-ENCODER S5 + CRIBS GUARD (2026-08-12)

| Decision | Description | Status |
|----------|-------------|--------|
| D2294 | Dual-encoder S5: DeBERTa-large + RoBERTa-large replace Phi-4-mini | ✅ DONE (superseded by D2298) |
| D2295 | CRIBS quality guard in S4 — post-generation validation | ✅ DONE |
| D2296 | D2293 scaled down — calibration tool built | ✅ DONE (superseded by D2298) |
| D2297 | Gemma models deleted from OMLX configs | ✅ DONE |

---

## ✅ DONE — ROUND 2 CROSS-EXAMINATION P0 (2026-08-12)

| Decision | Description | Status |
|----------|-------------|--------|
| D2290 | Re-anchor taxonomy for AI/agents — fix 80.5% "emerging" catch-all | ✅ DONE |
| D2293 | Human-adjudicate FBs → S5 calibration | ✅ DONE (completed via D2298) |
| D2291 | S5 FLAG path audit — confirmed 0/185, FLAG deleted | ✅ DONE |
| D2269 | Runner 60-min timeout per-stage configurable | ✅ DONE |
| D2270 | Runner docstring fix | ✅ DONE |
| D2273 | S5 role naming sync — model_assignments | ✅ DONE |
| G1-G9 | Governance audit fixes (CONSTITUTION, AGENTS, model_assignments, etc.) | ✅ DONE |

---

## ✅ DONE — D2255-D2262 P0 AUDIT FIXES (2026-08-11)

| # | Task | Decision | Status |
|---|------|----------|--------|
| P0.1 | Swap S5 NLI to DeBERTa FEVER | D2255 | ✅ FIXED |
| P0.3 | Archive GOLDEN-REVIEW.md v2.0 | D2259 | ✅ DONE |
| P0.4 | Fix golden YAML meta count (36→55) | D2257 | ✅ FIXED |
| P0.5 | Fix stage5_verify.py docstring | D2256 | ✅ FIXED |
| P0.6 | Remove stale classify_model from config | D2258 | ✅ FIXED |
| P0.7 | Goose MacWebContentsOcclusion | D2262 | ✅ DOCUMENTED |
| P0.8 | Fix HANDOFF model registry | D2260 | ✅ FIXED |

---

## ✅ DONE — D2265-D2268 BOTTLENECK + GUARD FIXES (2026-08-11)

| # | Task | Decision | Status |
|---|------|----------|--------|
| P1.1 | Batch classification for S4 | D2265 | ✅ DONE |
| P1.2 | Process guard (PID file) | D2266 | ✅ DONE |
| P1.3 | Laptop sleep prevention | D2267 | ✅ DONE |
| P1.4 | BUG-053 mitigation | D2268 | ✅ DONE |
| P1.5 | Disk + memory pre-flight checks | — | ✅ DONE |
| P1.6 | Roundtable eval prompt v3.0 | — | ✅ DONE |
| P1.7 | Stale Gemma references purged | — | ✅ DONE |
| P1.8 | S5 model pre-warming | — | ✅ DONE |

---

## ✅ DONE — D2250-D2252 S4 CHAIN + HYBRID S2 (2026-08-10)

| Task | Result |
|------|--------|
| BUG-075 — Cross-domain depth 0% | ✅ FIXED (87.5%) |
| D2249 — S4 classifier swap Phi→GPT-OSS | ✅ DONE |
| T-007b — S2 positive-fidelity gap | ✅ Hybrid DSPy 0.736 (not wired — see P0.1) |
| Golden audit | ✅ 0 quality gaps |
| DSPy validation report | ✅ Hybrid approved |
| Cost model | ✅ T1.1 ~21-26h |

---

## ✅ DONE — EARLIER SESSIONS

| Session | Tasks |
|---------|-------|
| D2211 (2026-08-08) | 13 P0 circuit breaker + error propagation fixes |
| D2212 (2026-08-08) | MinHash race condition + SentenceTransformer cache |
| D2195-D2204 (2026-08-05/06) | Zero-vector fallback, LICENSE, config sync, 49→48 col fix, golden expansion 10→25 |
| D2184-D2186 (2026-08-05) | 14 hardcoded values → config, bare except fixes |
| Phase 0-1.5 (2026-07-26/28) | Schema accessor, runner, Stage 3 removal, smoke, parallel, golden set, Matryoshka 512d |

---

## ❌ REJECTED — Will Not Implement

| Proposal | Reason |
|----------|--------|
| Cloud burst (GPT-4o-mini) | C1/C3 violation |
| LangChain dependency | C2 vendor lock-in |
| Microsoft GraphRAG | Heavy, cloud-native |
| LanceDB/DuckDB storage | SQLite adequate (C5) |
| Dagster/Prefect orchestration | PipelineRunner <300 LOC |
| Full Pydantic migration | Schema accessors sufficient |
| Leiden algorithm | Louvain adequate at current scale |
| OpenFActScore | Overengineered |
| Self-RAG reflection token training | C1 cost + R7 temp=0.0 |
| CRAG web search fallback | C3 sovereignty |
| ColBERT late interaction | M1 Max memory |
| Multi-agent swarm | 39-70% coordination tax |
| Neo4j graph database | C3 external service |

---

## 🔗 NEXT EXECUTION ORDER

```
1. ✅ B1-B10 (D2325-D2332) → pre-T1.1 blockers — ALL IMPLEMENTED (9295ce0 + D2343)
2. ✅ B11-B14 (D2337-D2340) → S6 data-loss / fail-closed / run-id / registry — IMPLEMENTED (B14 config rename deferred)
3. ❌ P0.1 (D2276) hybrid gate → REJECTED for T1.1 (BUG-085 A/B net-negative 4.3% rejection) — run traditional-only
4. ⏳ B15 (D2341) schema corrections (TI class, three-axis status, typed edges, feedback→YAML) → DEFERRED P2
5. 🚀 T1.1 → Launch full run (canary first, then full corpus)
6. T1.2 → Yield diagnostic on full run output
7. P1.x → Claim decomposition, golden expansion, enrichment verification (post-T1.1)
8. T2.x → Business PI, atomic evidence, trust state machine
```

## 🧭 HANDOFF POINTER

```
1. Verify OMLX health: curl -s localhost:11435/health
2. Active S5: DeBERTa-only, threshold 0.10 (honest cal D2322: P=0.647/R=0.386/F1=0.484), stage5_verify.py clean
3. Config: verifier=DeBERTa-v3-large, classifier=gpt-oss-20b-MXFP4-Q8, generator=Qwen3-Coder-30B
4. Hybrid gate REJECTED for T1.1 (BUG-085) — run traditional-only: python3 pipeline/runner.py
5. D2298 marks S5 architecture final — no ongoing human adjudication
```

---

## ✅ DONE — D2300-D2307 SENIOR RAG AUDIT (2026-08-12)

| Decision | Description | Status |
|----------|-------------|--------|
| D2300 | Modularity gaps documented (InferenceProvider/EmbeddingProvider/StorageBackend unimplemented) | ✅ LOGGED |
| D2301 | Cold-reload recovery — `cold_reload_delay` 45s (content=None) | ✅ DONE |
| D2302 | DSPy 3 gaps logged (not-wired / stale Stage 3a / random split) | ✅ LOGGED |
| D2303 | CRIBS bottleneck — batch CRIBS selected + wiring fixed | ✅ DONE |
| D2304 | DSPy tier-aware split (GOLD-A→train/B→dev/CHALLENGE→test) + `load_optimized_program()` | ✅ DONE |
| D2305 | Pipeline audit revelation — recall + latency SLA blindspots | ✅ LOGGED |
| D2306 | InferenceProvider + EmbeddingProvider protocol implemented (OMLX + Ollama) | ✅ DONE |
| D2307 | Recall measurement — `pipeline/recall_measure.py` | ✅ DONE |

### ⏳ DEFERRED — POST-T1.1 (from D2300-D2307)

| # | Task | Source |
|---|------|--------|
| GAP-1 | Wire DSPy trained program into stage2_extract.py | D2302 |
| GAP-2 | Remove stale Stage 3a artifacts (prompts/s3a_*.txt) | D2302 |
| SLA | End-to-end latency SLA | D2305 |
| SB | StorageBackend protocol (stage6 SQLite) | D2300 |
