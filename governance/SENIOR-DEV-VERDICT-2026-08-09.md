# Maxwell OS v3.0 — Senior Agentic RAG Developer Verdict
> **Date:** 2026-08-09 | **Trigger:** Post-Tier-0-Fixes Audit
> **Author:** Goose (AAIF) — Senior Agentic RAG Developer Perspective

---

## 1. S5 FACT-CHECKING — YES, IT'S THE FACUALITY GATE

S5 is the **primary factuality verification stage**. Two-tier architecture:

| Tier | Method | Model | Speed | Gate |
|------|--------|-------|-------|------|
| **Tier 1** | NLI entailment (MAX-entailment, D2215) | DeBERTa-v3-base-mnli-fever-anli (362MB, local) | ~0.3s/FB | auto-PASS at ≥0.8 entailment |
| **Tier 2** | Cross-family LLM deep check | Gemma-4-E4B-it-MLX-4bit (OMLX) | ~1s/FB | Only for flagged FBs |
| **Fail-closed** | D2093 | Any error → QUARANTINE | Instant | Never auto-PASS on failure |

**Factuality models used:**
- DeBERTa FEVER (factuality-trained on FEVER + MNLI + ANLI) → entropy-based entailment
- Gemma-4-E4B (cross-family: Gemma ≠ Phi ≠ Qwen = generator diversity)
- ModernBERT-base-nli (fallback, general NLI)

**Key insight:** DeBERTa FEVER is already the optimal factuality model for Maxwell's constraints. It's 362MB, runs locally (C3), $0 marginal cost (C1), and was purpose-built for claim-evidence verification. No swap needed.

---

## 2. S2 PRINCIPLE NAME NORMALIZATION — NOT DEFAULT

**Current state:** NO explicit name normalization in S2.

- `validate_fb_output()` checks: name exists, definition ≥30 chars, structural completeness
- Names come directly from LLM extraction (Qwen3-Coder)
- No `title_case` enforcement, no canonicalization, no dedup-by-name

**Risk:** Same concept across different clusters may get slightly different names (e.g., "Loss Aversion" vs "Loss Aversion Bias"). This creates false negatives in dedup.

**Recommendation:** Add name normalization in S4 merge (not S2). S4 already does classification — adding a `canonical_name` field that normalizes via LLM is natural. Priority: P2.

---

## 3. QUARANTINED FBs — THE FLOW

```
S2 Extract → S4 Merge → S5 Verify
                            │
                    ┌───────┼───────┐
                    ▼       ▼       ▼
                  PASS    FLAG   QUARANTINE
                    │       │       │
                    ▼       ▼       ▼
                 S6 Commit ←─┐   S5 Checkpoint (held)
                    │        │       │
                    ▼        │       ▼
               maxwell.db    │   Manual Review
                             │       │
                             └───────┘
                           (after fix)
```

**Quarantined FBs are NOT re-run through S2.** S2 extraction is done. They need:
1. Fix root cause (e.g., evidence_passages fix we applied today)
2. Re-run S4 merge (CRIBS + classification)
3. Re-run S5 verify (NLI + LLM check)
4. If PASS → S6 commit

**S6 gate:** `classification_status TEXT NOT NULL DEFAULT 'CLEAN'`. Only CLEAN FBs commit. FAILED stay out.

---

## 4. ANYTYPE CONTEXT PROPERTIES

`stage6b_anytype_push.py` handles full Anytype integration:

| Property | Source | Description |
|----------|--------|-------------|
| `context` | S4 classification | "business" / "academic" / "personal" / "cross-domain" |
| `accessibility` | Depth-derived | "beginner" / "intermediate" / "expert" / "self-evident" |
| `intimacy_boundary` | Default "public" | User-overridable privacy tier |
| `provenance` | Pipeline stamp | "llm_extracted_from_source" |
| `difficulty_level` | Depth-derived | beginner/intermediate/expert |
| `temporal_scope` | Classification | evergreen/contemporary/emerging/historical |
| `domains` | S4 classification | Multi-label, Anytype subfolders |

These are all populated by S4 and flow through to Anytype as formatted JSON with PushLedger tracking.

---

## 5. GOLDEN EXAMPLE EXPANSION — MASTER EVALUATION PROMPT

### Files to attach for LLM roundtable:

| Stage | File | What it contains | Use for |
|-------|------|-----------------|---------|
| **S2** | `knowledge pipeline/stage2_extract/latest/checkpoint.jsonl` (first 50 lines) | Raw extracted FBs: name, definition, mechanism, boundary, consequence, evidence_passages | Evaluate extraction quality |
| **S4** | `knowledge pipeline/stage4_merge/latest/SMOKE_TEST_REPORT.md` | CRIBS-enriched + classified FBs (12 diverse) | Evaluate classification + enrichment |
| **S5** | `knowledge pipeline/stage5_verify/latest/checkpoint.jsonl` | Verified FBs with NLI scores, status (PASS/QUARANTINE), epistemic_status | Evaluate verification quality |
| **Golden** | `config/golden/stage2_fewshot_convergent.yaml` | 27 current golden examples (18 positive, 9 negative) | Baseline comparison |

### Positive candidates (PASS FBs from smoke test):
- **FB #2: Opportunity Solution Tree Framework** — NLI PASS, universal depth, 15 source books
- **FB #3: Probabilistic Token Selection** — NLI PASS, domain depth, 33 source books
- **FB #5: Speculative Design As Social Critique** — NLI PASS, domain depth, strong mechanism

### Negative candidates (QUARANTINE FBs):
- **FB #6: Speculative Design Critique** — 2 evidence passages (too few), BORP suspect
- **FB #4: Embedding Dimensionality Tradeoff** — mechanism too generic, 5 source books
- **FB #1: Distributed Knowledge Architecture** — 54 source books (citation echo risk)

---

## 6. DEPENDENCY UPDATES — SAFE ONES APPLIED

| Package | Before | After | Risk | Applied |
|---------|--------|-------|------|---------|
| **certifi** | 2026.2.25 | 2026.7.22 | ✅ None (SSL certs only) | ✅ Applied |
| **charset-normalizer** | 3.4.4 | 3.4.9 | ✅ None (encoding only) | ✅ Applied |
| urllib3 | 2.7.0 | 2.7.0 | — Current | No change needed |
| requests | 2.32.5 | 2.32.5 | — Current | No change needed |
| faiss-cpu | 1.15.0 | 1.15.0 | — Current | No change needed |
| sentence-transformers | 5.6.1 | 5.6.1 | — Current | No change needed |
| torch | 2.10.0 | 2.10.0 | — Current | No change needed |

**OMLX verified:** 2 models still loaded after update. No impact.

---

## 7. DEPENDENCY MONITORING — GAP FOUND

**Current state:** `requirements.lock` exists (uv-generated) but:
- No automated staleness check
- `just preflight` doesn't check deps
- No version drift alert between lock and installed

**Recommendation:** Add to `just preflight`:
```bash
pip3 check  # Verify no broken deps
pip3 list --outdated --format=columns | head -20  # Show outdated
```

**Existing tools:**
- `requirements.lock` — pinned versions (uv pip compile)
- `requirements.txt` — loose constraints
- No sync script between them

---

## 8. MARKET RESEARCH — WHAT COULD IMPROVE THE PIPELINE

### 🔴 HIGH IMPACT — Implement Now

| Technology | What | Stage | Gain | Status |
|-----------|------|-------|------|--------|
| **USearch** | 10x faster FAISS replacement (SIMD NEON for Apple Silicon) | S1.5 clustering | 10x search speed, same API | ⭐4,216 GH stars. Evaluate vs FAISS |
| **Rapid-MLX** | 2-4x faster inference than OMLX, continuous batching | S2/S4/S5 LLM calls | 2-4x throughput, 0.08s cached TTFT | ⭐3,423. Cache issue: pulls from HF network (violates C1/C3). Monitor for fix. |
| **TurboVec** | 4-8x faster quantized search | S1.5 k-NN, FB retrieval | 4-8x search speed | ✅ Already installed (v0.8.0) |
| **LightRAG** | Graph-based RAG with entity extraction | FB retrieval | Better recall via graph traversal | ⭐37,713. EMNLP2025 paper. |

### 🟡 MEDIUM IMPACT — Evaluate

| Technology | What | Stage | Gain | Status |
|-----------|------|-------|------|--------|
| **MTPLX** | Native MTP speculative decoding | S2 extraction | 1.6-2.24x decode | ⭐1,102. M5 TensorOps required. M1 Max benefit unclear. |
| **LEANN** | 97% storage savings RAG | FB retrieval | Storage + privacy | ⭐12,688. MLsys2026 paper. |
| **memvid** | Agent memory layer (single-file, serverless) | Agent harness | Replace complex RAG pipelines | ⭐15,901. Knowledge graph support. |
| **zvec** | Lightning-fast embedded vector DB | Persistent vector storage | Replace FAISS for storage | ⭐14,942. Alibaba. HNSW, embedded. |
| **SiliconScope** | Native Apple Silicon monitor | System diagnostics | ANE/Memory-bandwidth tracking | ⭐802. SwiftUI. |

### 🔵 RESEARCH — Monitor

| Area | Source | Detail |
|------|--------|--------|
| **MLX ecosystem** | github.com/topics/mlx | New inference engines weekly |
| **Apple Silicon optimization** | github.com/topics/apple-silicon | M1-specific kernels, TensorOps |
| **RAG techniques** | github.com/topics/retrieval-augmented-generation | Agentic RAG, CRAG, Self-RAG developments |
| **AI Engineer YouTube** | @aiDotEngineer | Production agent patterns |
| **IBM Technology** | @IBMTechnology | CoALA, skill.md enterprise patterns |

---

## 9. COST EFFICIENCY & AGENT HARNESS IMPROVEMENTS

### Token Savings (everyday cost):
| Technique | Current | Proposed | Saving |
|-----------|---------|----------|--------|
| **Prompt caching** | No cache | Cache CRIBS_ENRICHMENT_SYSTEM + CLASSIFY_SYSTEM_PROMPT | ~500 tokens per FB call saved |
| **Merge CRIBS+Classification** | 2 LLM calls/FB | Single call with structured output | ~50% LLM calls (1.8h → 0.9h for 2,655 FBs) |
| **Batch classification** | Per-FB | Batch of 5-10 FBs per call | ~30% overhead reduction |
| **Evidence truncation** | 300-400 chars (hardcoded) | Config-driven 600-800 chars | Better factuality, fewer QUARANTINEs |

### Drift Reduction:
| Issue | Fix | Priority |
|-------|-----|----------|
| **Prompt lineage** | T2.15: stamp prompt_id + hash on every LLM call | P1 |
| **Model drift** | Log model version + quantization per run | P2 |
| **Classification drift** | `domain_disciplines.yaml` regeneration after S4 | P2 |

### Agent Harness Coding:
| Issue | Fix | Priority |
|-------|-----|----------|
| **Bare excepts** | 105 remaining `except Exception` blocks (C16) | P2 |
| **Type hints** | C17 compliance on all function signatures | P2 |
| **Ruff lint** | 120 remaining lint errors (mostly F841/E741) | P3 |

---

## 10. VERDICT

### Pipeline State: READY FOR S2

All Tier 0 fixes applied. Smoke test proves S4→S5 chain works end-to-end. Evidence flows correctly. DeBERTa FEVER factuality gate is operational. MAX-entailment scoring produces sensible results (3/12 auto-PASS, 9 escalate to LLM).

### Critical Path:
1. ⬜ **T0.5:** Run S2→S6 (~19h) — LAUNCH NOW
2. ⬜ **T1.7:** Golden eval on 25 examples (use smoke test report + master prompt)
3. ⬜ **Dependency:** Add `pip3 check` to just preflight
4. ⬜ **USearch:** Benchmark vs FAISS for S1.5 (10x potential speedup)
5. ⬜ **T2.15:** Prompt lineage stamping (drift prevention)

### What NOT to do now:
- ❌ Don't swap OMLX for Rapid-MLX (cache issue violates C1/C3)
- ❌ Don't add MTPLX (M5 TensorOps, M1 benefit minimal)
- ❌ Don't overhaul naming (S2 is fine, add canonical_name in S4 later)
- ❌ Don't update all 199 outdated packages (risk OMLX breakage)

### The S2 prerun checklist is green. Launch it.
