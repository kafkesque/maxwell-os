# Maxwell OS v3.0 — MASTER TASK REGISTER
> **Updated:** 2026-07-26 15:33 | **Sources:** MTR v2.2 + COMPREHENSIVE-TASK-REGISTER + Session Research
> **Rule:** Undone tasks at top (priority-ordered). Done tasks at bottom.
> **Buglog:** 11 open bugs (DELEGATE-001, BUG-044–054)

---

## ⚠️ DELEGATE WARNING — BOTH DELEGATE MODELS BROKEN

| Model | Bug | Status |
|-------|-----|--------|
| Phi-4-mini-instruct-8bit | **BUG-053:** HALLUCINATES — fabricates repo names, star counts, URLs. Do NOT use for factual/research tasks. | 🔴 OPEN |
| Qwen3-Coder-30B-A3B-Instruct-MLX-4bit | **BUG-054:** OMLX JSON parse error — `Failed to parse JSON: error decoding response body`. | 🔴 OPEN |
| DeepSeek API | **DELEGATE-001:** reasoning_content passthrough bug (thinking mode). | 🟡 WORKAROUND (don't use) |

**CURRENT STATE:** Delegation is DEAD. All 3 paths blocked. Do research & code tasks directly until BUG-053/054 resolved.
**Only safe delegate use:** Phi-4-mini for summarization WHEN source text is provided inline (no external data fetching).
**Untested:** gemma-4-E4B-it-MLX-4bit for delegates — may work, investigate.

---

## 🔴 CRITICAL — BLOCKS EVERYTHING (Session 2026-07-26)

| # | Task | Source | Effort | Impact | Status |
|---|------|--------|--------|--------|--------|
| C1 | **Delegate system fix** — Use local OMLX for ALL delegates (DeepSeek→$0) | DELEGATE-001 | 0h | Saved $$$ + attempted fix | ✅ DONE (workaround applied, but BUG-053/054 discovered) |
| C2 | **Governance sync** — decisions.yaml auto-sync, stale refs fixed, NLI mismatch resolved | Cross-audit | 2h | 115 decisions synced, zero contradictions | ✅ DONE |
| C3 | **Run `just smoke`** — Verify all Tier 0 fixes E2E | IMPL-PLAN | 0.5h | Blocked by BUG-051 | ⬜ BLOCKED — smoke processes 852 books (BUG-051) |
| C4 | **CONSTITUTION NLI mismatch** — roberta-large-mnli → DeBERTa-v3-base-mnli (D2111) | Deep Audit §5.1 | 0.1h | Stage 5 verification aligned | ✅ DONE |
| C5 | **DELEGATE-001 logged to buglog** | This session | 0.1h | Buglog current | ✅ DONE |
| C6 | **BUG-053 logged** — Phi-4-mini hallucination | This session | 0.1h | Prevents bad decisions | ✅ DONE |
| C7 | **BUG-054 logged** — Qwen3-Coder OMLX parse error | This session | 0.1h | Delegation status documented | ✅ DONE |
| C8 | **BUG-051 logged** — just smoke processes all books | This session | 0.1h | Smoke test fix tracked | ✅ DONE |

---

## 🟠 HIGH — THIS WEEK (Unblock Pipeline Scaling)

| # | Task | Source | Effort | Impact | Why High |
|---|------|--------|--------|--------|----------|
| H1 | **Fix BUG-051: `just smoke` limits** — Add `--limit 1` or pick first book | This session | 0.5h | Unblocks smoke testing | Can't verify any fix without working smoke test |
| H2 | **Investigate BUG-054: Qwen3-Coder OMLX parse** — Test raw curl completions, check for non-JSON output | This session | 1h | Unblocks code-gen delegation | All delegation dead until resolved |
| H3 | **Test gemma-4-E4B-it for delegates** — Only untested model, may be the fix for BUG-053/054 | This session | 0.5h | May restore delegation | gemma-4 is cross-family verifier, may work for delegates |
| H4 | **20-book FAISS calibration** | IMPL-PLAN T1#1 | 2h | Unlocks production scale | Threshold calibrated on 3 books only |
| H5 | **Stage 3: fix or remove** (BUG-048) | IMPL-PLAN T1#2 | 4h | Removes pipeline dead weight | Bypassed via bridge script |
| H6 | **LightRAG overlay** (Layer 1c) — 38,163★, MIT, updated daily, graph on top of existing vector store | Weekly Research + Feed Research | 4h | Highest benefit/effort ratio | Every independent source validates graph > vector |
| H7 | **20-book E2E test** | IMPL-PLAN T1#5 | 3h | Validates v3.0 at scale | Expect 50-200 FBs |
| H8 | **Stage 4 simplification** (D2112) | IMPL-PLAN T1#3 | 3h | Prevents subtle v3.0 bugs | 650-line script for old architecture |
| H9 | **Implement --dry-run mode** | IMPL-PLAN T3#17 + Weekly Research I4 | 4h | Noob vibecoder safety | "Preview before commit" — Beyang Liu pattern |
| H10 | **Resolve D316 vs D2066 — SALSA multi-label cleanup in code** | Deep Audit §2.8 | 1h | Removes architectural ambiguity | CONSTITUTION updated; code still references SALSA? |

---

## 🟡 MEDIUM — THIS MONTH (Quality, Layer 2 Foundation)

| # | Task | Source | Effort | Why |
|---|------|--------|--------|-----|
| M1 | **Evaluate Graphify** (96,158★) — Turn codebase+docs into queryable KG | Feed Research (NEW) | 3h | Could make Maxwell self-aware — ingest own codebase as KG |
| M2 | **Evaluate Cognee** (29,368★) — Open-source AI memory platform | Feed Research (NEW) | 4h | Persistent agent memory across sessions, self-hosted |
| M3 | **Evaluate Supermemory** (28,621★) — Local-first memory engine | Feed Research (NEW) | 3h | "Extremely fast, scalable, runs fully locally" — aligns with C1/C3 |
| M4 | **IBM Course study → Layer 2 blueprint** | Weekly Research I7 | 16h | Maps 1:1 to Maxwell needs (3 modules: agentic graph, graph memory, multi-agent) |
| M5 | **MCP server for knowledge access (C25)** | IMPL-PLAN T2#10 | 8h | Agent-agnostic FB query |
| M6 | **Implement skill.md standard** | IMPL-PLAN T2#9 | 4h | IBM production-proven agent skill composition |
| M7 | **Hardware probe (C24)** | IMPL-PLAN T2#11 | 3h | Auto-detect RAM, prevent OOM |
| M8 | **Golden set audit + convergent examples** | IMPL-PLAN T2#6,#8 | 3h | v3.0 schema coverage validation |
| M9 | **Schema migration scripts** | IMPL-PLAN T3#15 | 3h | Recover v1's 19,863 FBs |
| M10 | **Add "Trust But Verify" citation pattern** | Weekly Research R2 | 2h | Independently validated by Brightwave |
| M11 | **Evaluate Semantica** (1,440★) — Graph-native infrastructure for accountable AI | Feed Research (NEW) | 2h | Lightweight alternative to Neo4j for Maxwell Layer 2 |
| M12 | **Evaluate Neo4j llm-graph-builder** (4,963★) — Graph construction from unstructured data via LLMs | Feed Research (NEW) | 2h | Could replace/supplement Stage 2 extraction for graph layer |
| M13 | **Research: awesome-agent-skills + awesome-llm-apps** (127,802★) | Feed Research (NEW) | 2h | 100+ agent skills and RAG patterns for skill.md adoption |
| M14 | **Benchmark Qwen3-Embedding-0.6B vs bge-m3** | IMPL-PLAN T2#2 | 1h | Speed/quality tradeoff for Stage 1.5 |
| M15 | **Stratify golden sampling by type** | IMPL-PLAN T2#5 | 0.5h | 67/75 principle fix |

---

## 🟢 LATER — 6-12 Weeks (Graph Substrate, Speed, Cognitive Architecture)

| # | Task | Source | Effort |
|---|------|--------|--------|
| L1 | Benchmark USearch vs FAISS (4,234★, C++, SIMD+NEON for Apple Silicon) | Feed Research | 2h |
| L2 | Evaluate Zep/Graphiti for temporal provenance | IMPL-PLAN T3#13 + Weekly Research I9 | 4+8h |
| L3 | Benchmark MLX vs OMLX | IMPL-PLAN T3#14 | 2h |
| L4 | Integration test suite | IMPL-PLAN T3#16 | 4h |
| L5 | GAAMA 4-node memory architecture | Weekly Research I8 | 8h |
| L6 | Typed Graph Storage (F1) | IMPL-PLAN T4#F1 | 8h |
| L7 | Edge Type Ontology (F2) | IMPL-PLAN T4#F2 | 8h |
| L8 | Skill Subgraph Templates (F3) | IMPL-PLAN T4#F3 | 12h |
| L9 | Constitutional Constraint Graph (F4) | IMPL-PLAN T4#F4 | 16h |
| L10 | Self-Observation Protocol (F5) | IMPL-PLAN T4#F5 | 12h |
| L11 | Evaluate zvec performance (15,277★, C++, embedded vector DB, Alibaba) | Feed Research | 2h |
| L12 | Evaluate NornicDB (832★, Graph+Vector+Temporal MVCC, sub-ms HNSW) | Feed Research (NEW) | 2h |
| L13 | 130-book end-to-end run | IMPL-PLAN T3#S4 | 6-12h |
| L14 | FAISS GPU (Metal) acceleration for Stage 1.5 | IMPL-PLAN T3#S3 | 1h |

---

## 🔵 TIER 1 — ARCHITECTURE + VERIFICATION (15/18 DONE — moved to bottom)

### Architecture Restructure — 8/10 done
| ID | Task | Status |
|----|------|--------|
| A1 | Port FAISS clustering → `stage1_5_embed_cluster.py` | ✅ 407 LOC |
| A2 | Configure FAISS params (cos≥0.75, min_cluster=2, max=500) | ✅ Calibrated 0.70 |
| A3 | Embed raw segments via bge-m3 | ✅ 237 segments in 21s |
| A4 | Write stage2_cluster.py (HDBSCAN+UMAP) | ⬜ SKIPPED — redundant with FAISS |
| A5 | Rewrite stage2 for convergent extraction | ✅ 639 LOC |
| A6 | Add mechanism/boundary/consequence/is_summary/evidence_passages schema | ✅ |
| A7 | Merged extraction+classification in single LLM call | ✅ |
| A8 | Simplify stage4 → stage4_format_classify | ⬜ SKIPPED — cosmetic |
| A9 | Update pipeline_config.yaml stage ordering | ✅ |
| A10 | Update pipeline_paths.py with new checkpoints | ✅ |

### Stage 5 Verification Fix — 7/8 done
| ID | Task | Status |
|----|------|--------|
| V1 | Port DeBERTa NLI | ✅ |
| V2-V5 | Flip fail-open → fail-closed (4 return statements) | ✅ |
| V6 | Remove embedding similarity, replace with DeBERTa NLI | ✅ 83 lines removed |
| V7 | Compare against evidence_passages (verbatim) | ✅ |
| V8 | Wire cluster_noise.jsonl into Stage 4 read path | ✅ |

### Quick Fixes — 3/3 done
| ID | Task | Status |
|----|------|--------|
| Q1 | Fix YAML duplicate key | ✅ |
| D2108 | Fix cluster collapse | ✅ |
| D2109 | Vibecheck system | ✅ |

---

## 🔵 TIER 2 — QUALITY + CALIBRATION (2/7 done, remaining moved to MEDIUM)

| ID | Task | Status |
|----|------|--------|
| Q1 | Fix YAML duplicate key | ✅ |
| Q6 | 5-book E2E test (v3.0 validation) | ✅ 3 books, 237 chunks, 7 FBs |
| Q2-Q5,Q7 | Remaining Tier 2 | ⬜ → See M14, M15, M8 above |

---

## 🐛 OPEN BUGS (Prioritized)

| Bug | Severity | Description | Status |
|-----|----------|-------------|--------|
| **DELEGATE-001** | 🔴 CRITICAL | reasoning_content passthrough — DeepSeek delegates fail | 🟡 WORKAROUND (don't use DeepSeek for delegates) |
| **BUG-054** | 🔴 CRITICAL | Qwen3-Coder-30B OMLX JSON parse error — blocks code-gen delegation | 🔴 OPEN — see H2 |
| **BUG-053** | 🔴 CRITICAL | Phi-4-mini HALLUCINATES on factual tasks — blocks research delegation | 🔴 OPEN — see H3 (test gemma-4) |
| **BUG-051** | 🟠 HIGH | `just smoke` processes ALL 852 books — smoke test unusable | 🟡 OPEN — see H1 |
| **BUG-048** | 🟡 MED | Stage 3 semantic dedup bypassed | ⬜ OPEN — see H5 |
| **BUG-044** | 🟡 MED | Stage 3 clusters not used (bridge bypass) | ⬜ OPEN — same root as BUG-048 |
| **BUG-046** | 🟡 MED | Stage 4 complexity for v3.0 | ⬜ OPEN — see H8 |
| **BUG-045** | 🟡 MED | Stage 2 source_segments metadata inflated | ✅ FIXED (2026-07-26) |
| **BUG-047** | 🟡 MED | check_factual_llm old schema | ✅ FIXED (2026-07-26) |
| **BUG-049** | 🟡 MED | FAISS threshold monitoring with 5+ books | 🟡 Monitor — see H4 |
| **BUG-050** | 🟡 MED | Only 3/5 books chunked in old pipeline | 🟡 Run more converts |
| **BUG-017** | 🟢 LOW | OMLX kernel memory leak | Monitor |
| **BUG-037** | 🟢 LOW | OMLX registry stale | Needs OMLX GUI restart |

---

## ✅ DONE — Quick Reference

| Decision | What | Status |
|----------|------|--------|
| D2092-D2097 | Architecture diagnosis + fix plan | ✅ |
| D2098-D2106 | Cross-examination of 8 proposals | ✅ |
| D2107 | Tier 1 session partial | ✅ |
| D2108 | Cluster collapse fix | ✅ |
| D2109 | Vibecheck system | ✅ |
| D2110 | stage2_extract.py v3.0 (convergent) | ✅ |
| D2111 | stage5 DeBERTa NLI port | ✅ |
| D2112 | Tier 1 15/18 complete | ✅ |
| **D2115** | C12 de-hardcode + dead code archive + model sync + constitution fix + justfile + BUG-045/047 | ✅ |
| **D2116** | feed.opml expansion + weekly deep research + governance update + C12b-d sub-rules | ✅ |
| **D2117** | Tier 1-4 remaining tasks logged + IBM course Layer 2 blueprint | ✅ |
| **D2118** | Full feed.opml research + 6 NEW tool discoveries + BUG-051/053/054 logged + MTR merged | ✅ (2026-07-26) |
| **D2119** | Delegate cascade failure documented — Phi-4-mini hallucination + Qwen3-Coder parse error + DeepSeek thinking bug | ✅ (2026-07-26) |
| A1-A10 | Architecture restructure | 8/10 done ✅ |
| V1-V8 | Stage 5 verification fix | 7/8 done ✅ |
| C1-C2,C4-C8 | Session critical fixes | 7/8 done ✅ (C3 blocked) |

---

*Rule: Undone tasks at top (critical→high→medium→later). Done tasks at bottom.*
*Last action: BUG-051/053/054 logged, MTR merged with comprehensive register, 6 new tool discoveries from feed.opml research.*
*Next: H1 (fix just smoke) → H2 (investigate BUG-054) → H3 (test gemma-4 for delegates) → H6 (LightRAG overlay)*
