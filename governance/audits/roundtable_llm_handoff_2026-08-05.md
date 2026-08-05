# Maxwell OS v3.0 — Roundtable LLM Handoff
> **Generated:** 2026-08-05
> **Purpose:** Comprehensive pipeline evaluation by an external S-tier Senior RAG + Agentic Engineer LLM
> **Repository:** [Maxwell OS v2.0](https://github.com/barn/maxwell-os) (local: `/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0`)

---

## 1. SYSTEM OVERVIEW

### 1.1 What Maxwell OS Is
Maxwell OS is a **local-first, sovereign knowledge extraction pipeline** that transforms 953 technical/design/business books (EPUB/PDF → Markdown) into **Foundation Blocks (FBs)** — structured, verifiable, cross-referenced principle-entities stored in SQLite + Parquet with Anytype sync.

### 1.2 Iron Rules (from CONSTITUTION.md)
- $0 marginal cost — all generation on local hardware (MacBook M1 Max, 64GB)
- Sovereign — all data and compute remain local
- No vendor lock-in — open formats, multiple model families
- temp=0.0 on all generation scripts
- Generator ≠ Verifier — different model family for each
- Every persistent object stamped: schema_version, gen_model, pipeline_commit
- NEVER hardcode ANY value — paths, thresholds, model names → config/*.yaml
- Crash-safe writes: tempfile → fsync → os.replace
- Config-first default: if a value CAN be configurable, it MUST be in YAML

### 1.3 Hardware Constraints
- **Machine:** MacBook M1 Max, 64GB unified memory
- **GPU:** Apple Silicon MPS (Metal Performance Shaders)
- **Models must fit in ~24GB** (reserve for OS + other processes)
- **Thermal:** MPS throttles under sustained load (observed: 2.2→4.4s/batch degradation)

---

## 2. PIPELINE ARCHITECTURE (8 stages)

```
S0 (convert) → S0.5 (metadata) → S1 (chunk) → S1.3 (prefilter) → S1.5 (embed+cluster) → S2 (extract) → S4 (merge+classify) → S5 (verify) → S6 (commit) → S6b (anytype) → S6c (obsidian)
```

### 2.1 Stage Details

| Stage | Input | Output | Key Algorithm | Model |
|-------|-------|--------|---------------|-------|
| **S0** | EPUB/PDF files | Markdown | Pandoc/Docling | — |
| **S0.5** | Markdown | Author/title metadata | LLM extraction | Gemma-4-E4B |
| **S1** | Markdown | 323,226 segments | SHA-256 dedup chunking | — |
| **S1.3** | Segments | 323,226 (68 dropped) | Regex pre-filter (D2080) | — |
| **S1.5** | 323,226 segments | 1,110 clusters + 2,804 singletons | FAISS IndexFlatIP + R-NN | bge-small-en-v1.5 (MPS, 384d) |
| **S2** | Clusters | ~700-850 FBs + singleton FBs | Tiered LLM extraction + parallel | Qwen3.6-35B-A3B (Generator) |
| **S4** | FBs | Classified FBs + PT/PI/GE/TI | FB merge + SALSA classification | Qwen3.6 (merge) + Phi-4-mini (classify) |
| **S5** | FBs | Verified FBs | BORP + ModernBERT NLI + Gemma-4-E4B | DeBERTa/ModernBERT + Gemma |
| **S6** | FBs | SQLite (sqlite-vec) + Parquet | Commit + OKF export | — |
| **S6b** | FBs | Anytype pages (3-zone format) | Anytype API push | — |
| **S6c** | FBs | Obsidian vault | Markdown export | — |

### 2.2 Stage 3 — REMOVED (D2120)
Stage 3 (HDBSCAN semantic FB dedup) was removed in Phase 0 refactor. Clustering moved to S1.5 (pre-extraction). Dedup moved to S2 MinHash + S5 NLI.

---

## 3. MODELS & GENERATION STACK

### 3.1 Model Assignments
| Role | Model | Backend | Dims/Size | Notes |
|------|-------|---------|-----------|-------|
| **Generator** | Qwen3.6-35B-A3B-4bit | OMLX (MLX) | ~18GB | Primary FB extraction + merge |
| **Verifier** | Phi-4-mini-instruct-8bit | OMLX (MLX) | ~3.8GB | Classification (S4 SALSA) |
| **VerifierV2** | Gemma-4-E4B-it-MLX-4bit | OMLX (MLX) | ~4.2GB | Deep verification (S5) |
| **Embeddings** | bge-small-en-v1.5 | MPS (sentence-transformers) | 384d native | Clustering + coverage check |
| **NLI** | ModernBERT-base-nli → DeBERTa-v3 fallback | local transformers | 362MB | Entailment verification (S5) |

### 3.2 Known Model Limitations
- **Qwen3-Coder-30B-A3B:** Works via curl for code gen (D2146). Not used in pipeline.
- **Phi-4-mini:** HALLUCINATES on open-ended research (BUG-053). Only for summarization WITH source text.
- **Custom DeepSeek:** Reasoning passthrough bug (DELEGATE-001). NEVER use.
- **Memory budget:** ~24GB of 64GB for all models combined.

---

## 4. KEY DATA STRUCTURES

### 4.1 Foundation Block Schema (v3.0)
```json
{
  "fb_id": "sha256hash",
  "name": "3-7 word title",
  "definition": "3-4 sentences: name→mechanism→boundary→consequence",
  "mechanism": "X causes/enables/prevents Y because Z",
  "boundary": "Applies when [condition]. Fails when [counter-condition].",
  "consequence": "Because of this principle, [what follows].",
  "extraction_type": "causal_mechanism|empirical_pattern|normative_heuristic",
  "content_type": "principle|process_template|process_instance|growth_edge|tool_instruction",
  "is_summary": false,
  "evidence_passages": ["verbatim quote 1", "..."],
  "route": "FB",
  "source_books": ["Book A", "Book B"],
  "source_segments": ["seg_id1", "seg_id2"],
  "cluster_cohesion": 0.886,
  "source_diversity": 43,
  "is_convergent": true,
  "is_singleton_fb": false,
  "schema_version": "2.2",
  "gen_model": "Qwen3.6-35B-A3B-4bit",
  "pipeline_commit": "abc123"
}
```

### 4.2 Content Type Routing (D2150)
| extraction_type | → content_type | S4 Output |
|---|---|---|
| causal_mechanism | principle | FB checkpoint |
| empirical_pattern | growth_edge | S4_GE_OUTPUT |
| normative_heuristic (method) | process_template | S4_PT_OUTPUT |
| normative_heuristic (concept) | principle | FB checkpoint |
| tool-specific | tool_instruction | S4_TI_OUTPUT |
| case study | process_instance | S4_PI_OUTPUT |

### 4.3 Cluster Schema (S1.5 output)
```json
{
  "cluster_id": "cluster_322773_s213",
  "segment_ids": ["sha256...", ...],
  "source_books": ["Book Title (Author).md", ...],
  "source_diversity": 43,
  "is_convergent": true,
  "is_noise": false,
  "cohesion": 0.8598,
  "size": 25,
  "schema_version": "2.2"
}
```

---

## 5. CRITICAL ALGORITHMS

### 5.1 FAISS R-NN Clustering (S1.5)
**Algorithm:** Reciprocal Nearest-Neighbor clustering with cosine similarity.
- **Index:** FAISS IndexFlatIP on L2-normalized embeddings
- **k:** 50 nearest neighbors
- **Threshold:** cos ≥ 0.75
- **Reciprocity:** Edge only if A is in B's top-k AND B is in A's top-k
- **Why R-NN:** Fixes BUG-049 — old union-find suffered from transitive "bridge effect" merging unrelated clusters. R-NN guarantees minimum-radius clusters.
- **Cohesion:** Mean pairwise cosine within cluster (min 0.771, mean 0.886)
- **Splitting:** K-means split when >500 segments (638 sub-clusters created)
- **Source diversity:** Flag convergent when ≥2 distinct books
- **Peer-reviewed basis:** Brito et al. (1997), Qin et al. (2018), Chen et al. (2022, ACL)

### 5.2 Tiered + Parallel Extraction (S2)
**Two-tier prompt routing:**
- **Convergent clusters** (720): Full SYSTEM_PROMPT, ≤15 segment excerpts, golden few-shot injection
- **Single-source clusters** (390): SINGLE_SOURCE_SYSTEM (332 chars), 5 excerpts, no few-shot
- **Singleton segments** (2,804): SINGLETON_SYSTEM, 1 segment, content_type classification
- **Parallelism:** ThreadPoolExecutor(3) — 1.51× speedup measured
- **Gate:** Self-flagged is_summary=true → rejected (D2093 fail-closed)
- **NULL route:** LLM returns route=NULL when no extractable principle
- **MinHash dedup:** 128 perms, Jaccard > 0.9 against accepted FBs

### 5.3 NLI Verification (S5)
**Three-layer verification:**
1. **BORP:** ≥2 distinct source books (bypassable for certain types — D2083)
2. **ModernBERT NLI:** entailment(definition, evidence_passages) ≥ 0.6 → PASS; CONTRADICTION → escalate
3. **Gemma-4-E4B:** Cross-family deep check (R5: different model family from generator)
4. **Fail-closed:** ANY failure → QUARANTINE (D2093)

### 5.4 Coverage Gap Detection (D2149)
**Algorithm:** Post-S2 residual embedding check.
- Embed FB definition + all cluster segments (bge-small-en-v1.5)
- Cosine similarity FB↔segment
- Segments < 0.50 → "under-covered"
- >30% under-covered → FLAG cluster for re-extraction

---

## 6. CONFIGURATION AUDIT

### 6.1 Key Thresholds
| Parameter | Value | Rationale |
|---|---|---|
| FAISS threshold | 0.75 | R-NN cosine cutoff |
| Neighbor k | 50 (was 20, D2140) | Broader neighbor search → more convergent clusters |
| Embed dim | 384 (native bge-small) | Was 512 (mismatch, fixed) |
| Max cluster size | 500 | K-means split trigger |
| Min cluster size | 2 | Smaller → singletons |
| Min source diversity | 2 | ≥2 books = convergent |
| MinHash threshold | 0.9 | Jaccard near-dup cutoff |
| MinHash perms | 128 | Signature precision |
| NLI threshold | 0.6 | Entailment cutoff |
| BORP min sources | 2 | Distinct books for verification |
| Batch size (S2) | 10 | Segments per embedding batch |

### 6.2 Hardware-Optimized Settings
- **Embed backend:** MPS (fastest measured: 45 seg/s vs Ollama's slower throughput — D2131)
- **Embed model:** bge-small-en-v1.5 (smallest viable, 384d — Matryoshka 512d available via bge-m3 on Ollama but slower)
- **Generator:** Qwen3.6-35B-A3B-4bit (best quality/size ratio for 64GB)
- **Alternatives rejected:** Qwen3-Coder-480B-A35B (too large), Kimi K3 (no MLX port), SGLang (CUDA-only)

---

## 7. KNOWN ISSUES & RISKS

### 7.1 Critical
| ID | Issue | Impact | Mitigation |
|----|-------|--------|------------|
| DELEGATE-001 | Custom DeepSeek reasoning passthrough bug | Blocks delegate system | Use subprocess only |
| BUG-053 | Phi-4-mini hallucinates on open-ended research | Bad classifications if misused | Only use with source text |

### 7.2 Active
| ID | Issue | Impact | Status |
|----|-------|--------|--------|
| BUG-056 | Embedding speed claim doc mismatch | Docs say "~5 min" — reality 106 min via MPS | OPEN (D2131) |
| BUG-057 | 16 books missing from chunked corpus (4 corrupt, 0KB) | 1.7% corpus gap | OPEN (D2130) |
| BUG-058 | Silent classification fallback to "emerging" on error | 45% misclassification invisible | OPEN (D2134) |
| BUG-059 | embeddings.py missing — semantic edges never computed | Relationship edges absent | OPEN (D2136) |

### 7.3 Design Risks
| Risk | Severity | Description |
|------|----------|-------------|
| Under-extraction | MODERATE | R-NN conservative → 2 related principles in 1 cluster → 1 extracted. Mitigated by coverage_check.py |
| Thermal throttling | MODERATE | MPS degrades 2.2→4.4s/batch under sustained load. No mitigation yet |
| OMLX single-point | HIGH | All LLM calls through one OMLX server. If down, pipeline halts |
| Golden example coverage | MODERATE | Only 7 golden examples spanning 3 domains. Not diverse enough for dynamic selection |
| FB count reduction | COSMETIC | 19,438→6,500→~800 FBs. Architectural shift from per-segment to cluster-before-extract. Quality ↑, quantity ↓ |

---

## 8. DEPENDENCIES AUDIT

### 8.1 Python Environment
- Python 3.12
- Core: sentence-transformers, faiss-cpu, numpy, scikit-learn, pyyaml, datashaper
- MLX: mlx, mlx-lm (Apple Silicon only)
- OMLX: Custom MLX inference server
- NLI: transformers (ModernBERT, DeBERTa pipelines)

### 8.2 External Services
- OMLX server (localhost:8079) — REQUIRED for stages S2, S4, S5
- Ollama (optional, localhost:11434) — fallback for embeddings
- Anytype API (optional) — S6b push target

---

## 9. QUESTIONS FOR EVALUATION

### 9.1 Architecture
1. Is cluster-before-extract (1 FB per cluster) the optimal approach vs per-segment extraction with aggressive dedup?
2. Is R-NN (reciprocal nearest neighbors) at threshold 0.75 the best clustering method for this corpus? Would HDBSCAN on UMAP projections, spectral clustering, or Leiden community detection produce better clusters?
3. Does the 291:1 compression ratio (323K segments → 1,110 clusters) risk losing genuinely distinct principles?

### 9.2 Quality
4. Are the 5-layer defense against principle mixing (R-NN reciprocity, cohesion, k-means split, LLM gate, NLI verification) sufficient? What's the residual risk?
5. Is the content classification taxonomy (depth/discipline/domain) ontologically sound for agentic retrieval purposes?
6. Does the 3-zone FB format (Relations/Body/Stable Gate) provide sufficient context for downstream agentic consumption?

### 9.3 Configuration
7. Is neighbor_k=50 optimal? Would k=100 improve convergence without cluster quality degradation?
8. Is FAISS threshold=0.75 optimal? Would 0.78 reduce false merges? Would 0.72 recover more principles?
9. Is bge-small-en-v1.5 (384d) sufficient for 953-book semantic clustering, or should we use bge-m3 (1024d) despite the MPS throughput penalty?

### 9.4 Completeness
10. Are there any pipeline stages missing? (Graph overlay? Relationship edges? Multi-hop retrieval?)
11. Is the singleton extraction approach (2,804 single-segment FBs) the right granularity, or should singletons be processed differently?
12. Does the current pipeline serve its stated purpose: producing factually correct, non-bloated Foundation Blocks without missing crucial principles?

---

## 10. REPOSITORY STRUCTURE

```
maxwell os 2.0/
├── CONSTITUTION.md              # Single source of truth
├── DECISION-LOG.md              # 138 decisions (D2000-D2150)
├── MASTER-TASK-REGISTER.md      # Task tracker
├── AGENTS.md                    # Agent loader (this file's source)
├── config/
│   ├── pipeline_config.yaml     # 2151 lines — ALL config lives here
│   ├── decisions.yaml           # Auto-synced decision registry (136 decisions)
│   ├── taxonomy_v5.yaml         # Classification taxonomy
│   └── golden/                  # Few-shot examples
│       └── stage2_fewshot_convergent.yaml
├── pipeline/
│   ├── runner.py                # Single entry point (STAGE_ORDER)
│   ├── stage0_convert.py        # EPUB/PDF → MD
│   ├── stage0_5_extract_metadata.py
│   ├── stage1_chunk.py          # MD → SHA-256 deduped segments
│   ├── stage1_3_prefilter.py    # Regex pre-filter
│   ├── stage1_5_embed_cluster.py # FAISS R-NN clustering
│   ├── stage2_extract.py        # Convergent principle extraction (830→1000+ lines after D2148-50)
│   ├── stage4_merge.py          # FB merge + classification
│   ├── stage5_verify.py         # NLI + BORP verification
│   ├── stage6_commit.py         # SQLite + Parquet
│   ├── stage6b_anytype_push.py  # Anytype 3-zone format
│   ├── stage6c_obsidian_export.py
│   ├── coverage_check.py        # NEW (D2149): residual embedding coverage
│   ├── omlx_call.py             # OMLX inference client
│   ├── omlx_watchdog.py         # OMLX server lifecycle
│   ├── embeddings.py            # Shared embedding utilities
│   ├── schemas.py               # Classification taxonomy
│   ├── pipeline_paths.py        # Config→code path resolution
│   ├── feedback.py              # FB feedback tracking
│   ├── reliability.py           # FB reliability scoring
│   └── ...                      # 68 .py files total
├── governance/
│   ├── buglog.md                # Bug tracker (8 open)
│   ├── aggregated_remaining_tasks.md
│   └── audits/
├── knowledge pipeline/          # Pipeline data (gitignored)
│   ├── stage1_chunk/latest/     # 323,226 segments
│   ├── stage1_5_embed_cluster/latest/  # 1,110 clusters + 2,804 singletons
│   └── ...
├── tests/
├── benchmarks/
└── archive/                     # Old/removed code
    └── stage3_cluster.py.archived-2026-07-26
```

---

## 11. RUNNING THE PIPELINE

```bash
# Start OMLX server (required for S2+)
python3 pipeline/omlx_watchdog.py

# Full pipeline (single entry point, D2061)
python3 pipeline/runner.py

# Individual stages:
python3 pipeline/stage2_extract.py                    # Convergent + single-source
python3 pipeline/stage2_extract.py --process-singletons  # Singleton pass (D2149)
python3 pipeline/stage2_extract.py --only-convergent  # Skip single-source

# Coverage analysis (post-S2):
python3 pipeline/coverage_check.py                    # Analyze all FBs
python3 pipeline/coverage_check.py --output res.jsonl  # Export flagged
```

---

**End of handoff.** Please evaluate the pipeline architecture, algorithms, configuration, and completeness against peer-reviewed best practices in RAG, multi-document summarization, and agentic knowledge extraction. Flag any blind spots, gaps, conflicts, hidden failures, dead code, future tax, mismatches, misalignments, risks, vulnerabilities, bottlenecks, bugs, or threats.
