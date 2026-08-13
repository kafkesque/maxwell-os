# Maxwell OS v3.0 — MASTER TASK REGISTER
> **Updated:** 2026-08-13 10:14 | **Decisions:** D2000-D2321 (310 decisions)
> **S5 Architecture:** DeBERTa-only NLI, threshold 0.10 (D2298). Final. No ongoing human adjudication.
> **Active Models:** Qwen3-Coder-30B (S2), GPT-OSS-20B (S4), DeBERTa-v3-large (S5), bge-m3 (Emb)
> **Redundant/Removed:** RoBERTa-large, Phi-4-mini (S5), all Gemma variants
> **Diagnostic:** 188 FBs, 72.4% S5 pass rate → T1.1 authorized
> **Detailed tasks:** `governance/aggregated_remaining_tasks.md`
> **Buglog:** `governance/buglog.md`

---

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

## 🔴 OPEN BUGS

| Bug ID | Severity | Description |
|--------|----------|-------------|
| BUG-001 | 🔴 CRITICAL | Empty pass loop — verification checks random principles |
| BUG-014 | 🔴 CRITICAL | Cloud burst code violates C1/C3 |
| BUG-054 | 🔴 CRITICAL | Qwen3-Coder delegate fails — OMLX JSON parse error |
| BUG-085 | 🔴 CRITICAL | hybrid_s2_extract() not wired to stage2_extract.py |
| BUG-013 | 🟠 HIGH | OMLX guard uses pkill -f (kills pipeline itself) |
| BUG-012 | 🟠 HIGH | sqlite-vec not loaded before CREATE VIRTUAL TABLE |
| BUG-055 | 🟠 HIGH | related_fbs vs related_blocks field name mismatch |
| BUG-083 | 🟠 MED | domain_anchors.yaml predates current corpus (80.5% "emerging") |
| BUG-084 | 🟠 MED | Golden depth calibration: universal=1, specialized=1 |
| BUG-045 | 🟡 MED | Stage 2 evidence passages inflated (metadata bloat) |
| BUG-050 | 🟡 MED | Only 3 of 20 books chunked — insufficient convergence |
| BUG-051 | 🟡 MED | just smoke processes ALL 852 books instead of 1 |
| BUG-011 | 🟡 MED | Zero tests |
| BUG-073 | ⚪ LOW | CONV-035/037 false convergence (D2232 pending) |

### ✅ RESOLVED BUGS (this + recent sessions)

| Bug ID | Description | Resolution |
|--------|-------------|------------|
| BUG-080 | call_omlx_json returns list/str — S4 crashes | ✅ FIXED (guards applied) |
| BUG-080.1 | _save_diag_state flush/fsync outside with block | ✅ FIXED |
| BUG-080.9 | S5 method tag dict missing "nli+LLM-echo" | ✅ FIXED |
| BUG-080.10 | S5 method tag dict missing "mech_quality" | ✅ FIXED |
| BUG-081 | evals/golden_cases.json v2 format | 🟡 OPEN |
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
| D2298 | **DeBERTa-only NLI** — RoBERTa removed. Threshold 0.10 (P=1.000, R=0.556, F1=0.714). Single encoder. No human adjudication needed. | ✅ DONE |
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
1. P0.1 (D2276) → Wire hybrid S2 to production (~8h) — highest quality lever
2. P0.2-P0.6   → Pipeline manifest, schema split, ISOR, golden tiers, DSPy gates (~13h)
3. T1.1         → Launch full S1.3→S6 run (~26h wall-clock)
4. T1.2         → Yield diagnostic on full run output
5. P1.x         → Claim decomposition, golden expansion, enrichment verification
6. T2.x         → Business PI, atomic evidence, trust state machine
```

## 🧭 HANDOFF POINTER

```
1. Verify OMLX health: curl -s localhost:11435/health
2. Active S5: DeBERTa-only, threshold 0.10, stage5_verify.py clean
3. Config: verifier=DeBERTa-v3-large, classifier=gpt-oss-20b-MXFP4-Q8, generator=Qwen3-Coder-30B
4. S2 hybrid NOT wired (BUG-085) — highest priority
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
