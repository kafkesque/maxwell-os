# Maxwell OS — Knowledge Layer Architecture: Round Table Handoff
> **Date:** 2026-07-18 | **Trigger:** Pipeline stagnation → root-cause re-evaluation
> **Purpose:** Define the ultimate knowledge layer BEFORE fixing the extraction pipeline
> **Status:** ANALYSIS — requires Maxwell review before any implementation

---

## EXECUTIVE SUMMARY

Maxwell OS has built 23 tools (9,837 LOC) of automation infrastructure around a pipeline that has never completed a single S1→S8 run. The 19,770 "validated" FBs are legacy data incompatible with the current taxonomy. **574 S3a principles are stuck with zero S3c verification, zero S5 generation.**

**Core insight:** The pipeline was built to feed Anytype. But Anytype is a proprietary presentation layer, not a sovereign knowledge store. The canonical storage should be open-format files — with Anytype as one of many possible consumers.

**Recommendation:** Redefine the knowledge layer using **Parquet + LanceDB + DuckDB** as the canonical store, with **JSON-LD** for relationships. Build the extraction pipeline to target this store. Push to Anytype as a secondary presentation layer.

---

## §1 — REQUIREMENTS: THE ULTIMATE KNOWLEDGE LAYER

### 1.1 Hard Constraints (from CONSTITUTION.md)

| Constraint | Requirement |
|------------|-------------|
| C1 ($0 marginal cost) | Must run on local hardware, no API calls for storage/retrieval |
| C2 (No vendor lock-in) | Open formats, migratable, no proprietary database |
| C3 (Sovereign) | All data on local disk, no cloud sync required |
| C4 (Future-proof) | Readable by any language, any framework, 10 years from now |
| C6 (Crash-safe) | Atomic writes, no corruption on power loss |

### 1.2 Functional Requirements

| # | Requirement | Why |
|---|-------------|-----|
| **R-KL1** | 100% factually accurate BORP principles | FBs must cite ≥2 distinct book sources, no hallucinated claims |
| **R-KL2** | Ontologically precise indexing | Domain + discipline + depth must be unambiguous and machine-queryable |
| **R-KL3** | Agentic-grade retrieval | LLM must retrieve exactly the right FBs for any business task |
| **R-KL4** | Transferable/migrateable | Move FBs between storage backends without data loss |
| **R-KL5** | Multi-modal ready | Store references to images, audio, video (not just text) |
| **R-KL6** | Version-tracked | Schema evolution, rollback, audit trail |
| **R-KL7** | Human + machine readable | FBs browsable by Maxwell AND queryable by Goose |
| **R-KL8** | Scalable to 20K+ FBs | Current target, but design for 100K+ |

### 1.3 Retrieval Requirements

An agent (Goose or future harness) must be able to:

```
1. Semantic: "Find principles about pricing strategy for solopreneurs"
2. Structured: "Show all FBs in domain=Business Operations, discipline=Marketing"
3. BORP-filtered: "Only show FBs with ≥2 distinct book sources"
4. Depth-filtered: "Only universal or cross-domain principles"
5. Graph-traversal: "Show principles that support AND contradict FB #1234"
6. Hybrid: "Marketing principles about pricing, from books published after 2015"
```

---

## §2 — MARKET RESEARCH: KNOWLEDGE STORAGE TECHNOLOGIES

### 2.1 Contender Matrix

| Technology | Type | License | Local | Vector | Structured | Graph | Portability | Maturity |
|-----------|------|---------|-------|--------|------------|-------|-------------|----------|
| **Parquet + DuckDB** | Columnar file + SQL | Apache 2.0 / MIT | ✅ | via VSS ext | ✅ SQL | via JSON-LD | ✅ single file | ✅ |
| **LanceDB** | Vector DB (Lance format) | Apache 2.0 | ✅ | ✅ native | ✅ PyArrow | via JSON-LD | ✅ Lance files | 🟡 maturing |
| **ChromaDB** | Vector DB | Apache 2.0 | ✅ | ✅ | 🟡 metadata | ❌ | 🟡 SQLite backend | ✅ |
| **FAISS + SQLite** | Vector + Relational | MIT | ✅ | ✅ | ✅ SQL | ❌ | 🟡 two files | ✅ |
| **Qdrant** | Vector DB (server) | Apache 2.0 | ✅ | ✅ | ✅ payload | ❌ | 🟡 server process | ✅ |
| **sqlite-vec** | SQLite vector ext | MIT | ✅ | ✅ | ✅ SQL | ❌ | ✅ single file | 🟡 new |
| **RDFlib (RDF/OWL)** | Semantic triple store | BSD | ✅ | ❌ | ✅ SPARQL | ✅ native | ✅ open standard | ✅ |
| **Neo4j** | Graph database | GPLv3/EE | ✅ | ❌ | ✅ | ✅ Cypher | 🟡 server process | ✅ |
| **Anytype** | Proprietary KM | Custom | 🟡 local sync | ✅ built-in | ✅ relations | ✅ links | ❌ proprietary | 🟡 |
| **JSON files** | Flat files | N/A | ✅ | ❌ | ❌ | ❌ | ✅ universal | ✅ |

### 2.2 Embedding Models

| Model | Dims | Size | MTEB Rank | License | Notes |
|-------|------|------|-----------|---------|-------|
| **nomic-embed-text** (current) | 768 | 274MB | ~30 | Apache 2.0 | Good, not best. Via Ollama. |
| **BGE-base-en** | 768 | 109MB | ~5 | MIT | Best size/perf ratio for local |
| **gte-base** | 768 | 80MB | ~10 | Apache 2.0 | Smaller than BGE, nearly as good |
| **gte-large** | 1024 | 300MB | ~2 | Apache 2.0 | Top quality, fits in 64GB |
| **jina-embeddings-v3** | 1024 | ~500MB | top tier | Apache 2.0 | Task-specific, multilingual |
| **multilingual-e5-large** | 1024 | ~500MB | top tier | MIT | Multilingual if needed later |
| **CLIP (ViT-B/32)** | 512 | 150MB | N/A | MIT | Image embeddings for multimodal |

**Recommendation:** Switch from nomic-embed-text to **gte-base** (80MB, MTEB rank ~10). Smaller, faster, better retrieval quality. Upgrade to gte-large later if quality gaps appear.

### 2.3 Retrieval Architectures (Agentic-Grade)

| Method | Description | Local? | Complexity | Effectiveness |
|--------|-------------|--------|------------|---------------|
| **Basic vector search** | Cosine similarity over embeddings | ✅ | Low | 🟡 |
| **Hybrid search** | Vector + keyword (BM25) + filters | ✅ | Medium | ✅ |
| **HyDE** | Generate hypothetical answer → embed → search | ✅ | Medium | ✅ |
| **Multi-vector** | Per-chunk + summary embeddings | ✅ | Medium | ✅ |
| **ColBERT** | Late interaction (token-level) | ✅ | High | ✅✅ |
| **GraphRAG** | Knowledge graph + community summarization | 🟡 | High | ✅✅ |
| **Self-querying** | LLM generates structured query from natural language | ✅ | Low | ✅ |
| **Re-ranking** | Retrieve N candidates → LLM re-ranks top K | ✅ | Low | ✅✅ |

**Recommendation:** Start with **hybrid search + re-ranking**. Simple, proven, local, effective. Add GraphRAG later when FBs have relationship data.

---

## §3 — RECOMMENDED ARCHITECTURE

### 3.1 The Sovereign Stack

```
┌─────────────────────────────────────────────────────────┐
│                    RETRIEVAL LAYER                        │
│  DuckDB (SQL filtering) + LanceDB (vector search)        │
│  → hybrid query: filter by domain THEN semantic search   │
│  → re-rank top 20 results with Phi-4-mini ($0)           │
├─────────────────────────────────────────────────────────┤
│                    INDEX LAYER                           │
│  LanceDB vector index (built from Parquet)               │
│  DuckDB FTS index (keywords, domains, sources)           │
│  JSON-LD relationship graph (supports, contradicts, ...) │
├─────────────────────────────────────────────────────────┤
│                CANONICAL STORAGE LAYER                    │
│  fbs.parquet          ← single file, all FBs            │
│  relationships.jsonld ← semantic relationships          │
│  embeddings.lance/    ← LanceDB index directory          │
│  migrations/          ← schema version history          │
├─────────────────────────────────────────────────────────┤
│                PRESENTATION LAYER                        │
│  Anytype              ← human browsing, manual curation  │
│  TUI (maxwell_tui.py) ← pipeline monitoring              │
│  Goose retrieval tool ← agentic query interface          │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Why Parquet as Canonical Format

| Property | Parquet | JSON | SQLite | Lance |
|----------|---------|------|--------|-------|
| **Open standard** | ✅ Apache-governed | ✅ | ✅ | ✅ Apache 2.0 |
| **Columnar** | ✅ (fast filtering) | ❌ | ✅ | ✅ |
| **Compression** | ✅ zstd/snappy | ❌ | ✅ | ✅ |
| **Schema enforcement** | ✅ | ❌ | ✅ | ✅ |
| **Nested types** | ✅ (lists, structs) | ✅ | 🟡 JSON ext | ✅ |
| **Readable by** | Python/R/Java/Rust/Spark/DuckDB/Polars | Everything | SQL clients | Python/Rust/JS |
| **Vector support** | ✅ (fixed-size list) | ❌ | via sqlite-vec | ✅ native |
| **Single file** | ✅ | ✅ | ✅ | ❌ (directory) |
| **Incremental writes** | ❌ (batch only) | ✅ | ✅ | ✅ |
| **10-year readability** | ✅ guaranteed | ✅ | ✅ | 🟡 newer format |

**Decision:** Parquet is the canonical format. It can be read by any data tool in any language. If LanceDB disappears tomorrow, the data is still accessible. If DuckDB is replaced by Polars, the Parquet files still work.

**Trade-off:** Parquet doesn't support incremental writes (must rewrite file). Mitigation: batch writes every N FBs, or use LanceDB for live storage with Parquet export for portability.

### 3.3 FB Schema (Proposed)

```yaml
fb_id: "fb_20260718_001"              # unique, sortable
principle: "Design systems enforce..." # the actionable principle (1-3 sentences)
principle_short: "Design systems..."   # truncated for UI (≤120 chars)
sources:                               # provenance
  - book: "Atomic Design"
    author: "Brad Frost"
    chapter: "Chapter 3"
    page: "p.47-52"
    excerpt: "..."                     # the actual quote (optional)
borp_sources: 3                        # ≥2 distinct books for BORP
domain_canonical: "digital product"    # from 25-domain taxonomy
discipline_canonical: "design systems" # from 47-discipline taxonomy
depth: "cross-domain"                  # specialized | cross-domain | universal
keywords: ["design system", "consistency", "tokens"]
jargon_explained: "Design systems use shared tokens..."  # plain-English explanation
schema_version: "2.0"
gen_model: "qwen3.6-35b"
pipeline_commit: "abc123"
created_at: "2026-07-18T13:00:00Z"
embedding: [0.023, -0.154, ...]       # 768d float32 vector
related_fbs: ["fb_...", "fb_..."]      # FB IDs
relation_types: ["supports", "extends"] # parallel to related_fbs
media_refs:                            # multimodal (future)
  - type: "image"
    path: "media/atomic_design_fig3.png"
    description: "Atomic Design hierarchy diagram"
```

### 3.4 Why This is Future-Proof

1. **Parquet is immortal.** It's the standard for columnar data. Even if Apache Foundation dissolves (unlikely), every data tool reads it.
2. **Vectors are stored as standard float arrays.** No proprietary embedding format.
3. **JSON-LD relationships are W3C standard.** Can be consumed by any semantic web tool.
4. **Migration path:** `fbs.parquet` → any future system. One file copy.
5. **Anytype is a consumer, not the owner.** Push FBs there for browsing, but Parquet is canon.

---

## §4 — THE EXTRACTION PIPELINE (What Feeds the Knowledge Layer)

### 4.1 The Current Pipeline: Why It Failed

| Stage | Problem |
|-------|---------|
| **S1 (extraction)** | No source files in 1.sources/. 0 extractions. |
| **S1.5 (clustering)** | Depends on S1 output. |
| **S3a (convergence)** | 574 principles across 9 domains — but no S3c verification, no S5. Stuck. |
| **S3c (verification)** | Never run on current data. 0 verified. |
| **S5 (FB generation)** | 0 FBs generated. The pipeline never reached this stage with new architecture. |
| **S6 (validation)** | 19,770 legacy FBs from old pipeline. Wrong taxonomy, wrong schemas. Dead data. |
| **S7 (human gate)** | Never reached. |
| **S8 (Anytype push)** | Never reached. |

**Root cause:** The pipeline has too many stages, too many dependencies, and too many architectural changes without completing a run. Each decision (D1055, D1056, D1055-FIX) changed the pipeline mid-flight without proving the end-to-end flow works.

### 4.2 Proposed: Simplified Pipeline

Instead of S1→S1.5→S3a→S3c→S5→S6→S7→S8, collapse to:

```
INGEST → EXTRACT → CONVERGE → GENERATE → VERIFY → STORE
  ↓         ↓         ↓          ↓         ↓        ↓
 Raw     Chunks    Principles   FBs     BORP     Parquet
 book    with      per book    from     check    +
 → MD   embeddings clusters    LLM     + stamp  LanceDB
```

**Stage simplification:**

| Old | New | What Changes |
|-----|-----|--------------|
| S1 extractive + S1.5 cluster | **INGEST + CHUNK** | One script: read book → chunk → embed chunks. No separate cluster stage. |
| S3a converge | **CONVERGE** | One LLM call per cluster: extract principles. Schema enforcement via Outlines. |
| S3c verify | **Built into GENERATE** | Verification happens during FB generation, not separate stage. |
| S5 generate + S6 validate | **GENERATE + VERIFY** | Generate FB → verify BORP → stamp → store. Single script per batch. |
| S7 human gate + S8 push | **STORE** | Write to Parquet (canonical). Push to Anytype (optional, async). |

**Key principles for new pipeline:**

1. **One script = one stage.** No multi-script stages.
2. **Each stage produces a checkpoint file.** Parquet or JSON. Resumeable.
3. **Generator ≠ Verifier always.** Different model family for verification (R5).
4. **temp=0.0 always.** No creativity in extraction (R7).
5. **BORP embedded in generation.** The LLM prompt requires ≥2 source citations per principle.
6. **Stamp at generation time.** Not as a post-processing step.

### 4.3 Multi-Modal Ingestion (Future)

The pipeline should accept:
- **Text:** MD, PDF, EPUB (current)
- **Audio:** MP3, WAV → Whisper transcription → text → pipeline
- **Video:** MP4 → Whisper + frame extraction → text + image refs
- **Web:** URL → scrape → Markdown → pipeline

This doesn't need to be built now. But the **knowledge layer schema supports it** (media_refs field) and the pipeline architecture should have hooks for it.

---

## §5 — WHAT'S ACTUALLY FEASIBLE (Avoiding More Over-Engineering)

### 5.1 The "Waste Pattern" to Avoid

The last two sessions followed this pattern:
1. Discover pipeline problem → design governance solution → build tools → pipeline still broken
2. Result: 23 tools, 9,837 LOC, 22 phantom decisions, 0 working FBs

**The anti-pattern:**
```
Problem → Analysis → More Architecture → More Tools → Pipeline Still Broken
```

**The productive pattern:**
```
Problem → Minimal Fix → Run Pipeline → See Output → Iterate
```

### 5.2 What CAN Be Done in One Session

| Task | Feasible? | Why |
|------|-----------|-----|
| Build full new pipeline | ❌ | Too much, will repeat over-engineering |
| Redesign knowledge layer | ✅ | Design doc only, no code |
| Migrate 19,770 legacy FBs | ❌ | Schema mismatch, needs careful mapping |
| **Run ONE book through simplified pipeline** | ✅ | Prove the concept works |
| **Generate 10 FBs with BORP in Parquet** | ✅ | Minimum viable proof |
| Set up LanceDB index | ✅ | 10 lines of code |

### 5.3 Recommended Next Session

**Phase A: Design (this session)**
- ✅ This handoff document (knowledge layer architecture)
- Maxwell reviews and approves/revises

**Phase B: Minimum Viable Pipeline (next session)**
1. Pick ONE book from `education/books/md/` — a business book with clear principles
2. Write a single Python script that:
   - Chunks the book
   - Sends chunks to Qwen3.6 → extract principles with BORP citations
   - Verifies with Phi-4-mini → check BORP, check factual accuracy
   - Writes 5-10 FBs to `fbs.parquet`
3. Set up LanceDB index from Parquet
4. Test retrieval: "find pricing principles" → get relevant FBs
5. **STOP.** Review output quality with Maxwell. Iterate.

**Phase C: Scale (subsequent session)**
- Run the proven script on all books
- Add relationship extraction (supports/contradicts)
- Push to Anytype

### 5.4 What NOT to Build (Yet)

| Don't Build | Why |
|-------------|-----|
| New governance tools | Constitution is sufficient |
| New pipeline stages | Simplify first, then automate |
| Guardian/monitoring upgrades | Guard the pipeline when it EXISTS |
| Multi-modal ingestion | Text first, prove it works |
| GraphRAG | FBs need relationships first |
| Parallel consensus | Single verifier is enough for 10 FBs |
| TUI upgrades | Terminal output is sufficient |

---

## §6 — DECISION POINTS FOR MAXWELL

### 6.1 Knowledge Layer

| Question | Option A | Option B | Option C |
|----------|----------|----------|----------|
| **Canonical format** | Parquet (recommended) | LanceDB directly | JSON files |
| **Embedding model** | gte-base (80MB) | nomic-embed-text (current) | gte-large (300MB) |
| **Vector DB** | LanceDB (recommended) | DuckDB VSS | FAISS + SQLite |
| **Anytype role** | Presentation layer (recommended) | Canonical store | Not used |

### 6.2 Pipeline

| Question | Option A | Option B |
|----------|----------|----------|
| **Pipeline complexity** | Simplified (5 stages) | Keep current (8 stages) |
| **First run target** | 1 book → 10 FBs (recommended) | All books → all FBs |
| **Legacy 19,770 FBs** | Ignore, rebuild clean (recommended) | Migrate to new schema |

### 6.3 Session Strategy

| Question | Option A | Option B |
|----------|----------|----------|
| **Next session focus** | Build MVP pipeline (1 book) | More architecture design |
| **Tool re-use** | Use simplified versions of existing tools | Rewrite from scratch |
| **Verification approach** | Phi-4-mini quick check (recommended) | Full Gemma-4 cross-verification |

---

## §7 — FILE MANIFEST

| File | Purpose |
|------|---------|
| `config/knowledge_layer.yaml` | Knowledge layer config (format, model, paths) |
| `schemas/fb_v2.parquet.yaml` | FB schema definition |
| `data/fbs.parquet` | Canonical FB storage |
| `data/embeddings.lance/` | LanceDB vector index |
| `data/relationships.jsonld` | FB relationship graph |
| `pipeline/ingest.py` | Book ingestion → chunks |
| `pipeline/extract.py` | Chunks → principles via LLM |
| `pipeline/generate.py` | Principles → FBs → Parquet |
| `tools/fb_query.py` | Retrieval interface for Goose |

---

*Generated by: Goose (Phi-4-mini for analysis, Qwen3.6 for reasoning) | Schema: N/A (handoff doc) | Pipeline commit: N/A*
