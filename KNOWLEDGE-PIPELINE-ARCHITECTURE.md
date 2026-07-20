# Maxwell OS v2.0 — Knowledge Pipeline Architecture
## Complete Reference for LLM Roundtable Cross-Examination
### 2026-07-19 | 7,299 lines of pipeline code | 852 books | 14 FBs deployed

---

## 0. EXECUTIVE SUMMARY

Maxwell OS v2.0 is a **sovereign, zero-cost knowledge extraction and orchestration pipeline** that converts unstructured books (EPUB/PDF/MD) into verified, classified, cross-referenced Foundation Blocks (FBs) — atomic knowledge units that serve as ground truth for skill orchestration and agentic automation.

**What makes it different from every RAG system, agent framework, and knowledge base:**

1. **Every claim is verified** — BORP (≥2 distinct source books), cross-model verification (R5), deterministic gate checks
2. **Every claim is classified** — 25-domain, 47-discipline taxonomy with raw label preservation for taxonomy evolution
3. **Every claim is traced** — source book, cluster provenance, pipeline run lineage
4. **Every claim is tested** — cumulative execution tracking measures whether FBs actually work in practice
5. **$0 marginal cost** — all models run locally on Apple Silicon (Qwen3-Coder-30B, Phi-4-mini, nomic-embed-text)
6. **100% sovereign** — no cloud, no API keys, no vendor lock-in

---

## 1. SYSTEM CONSTRAINTS (Non-Negotiable)

| ID | Constraint | Mechanism |
|----|-----------|-----------|
| **C1** | $0 marginal cost | All generation on local hardware (OMLX + Ollama) |
| **C2** | No vendor lock-in | Open formats, multiple model families, SQLite + Parquet |
| **C3** | Sovereign | All data and compute remain local. No cloud. |
| **C4** | Future-proof | No single-provider dependency. Model-agnostic wrappers. |
| **C6** | Crash-safe writes | tempfile → fsync → os.replace for all checkpoints |
| **C12** | Never hardcode paths | `pipeline/pipeline_paths.py` is single source of truth |
| **R5** | Generator ≠ Verifier | Different model family for extraction vs. verification |
| **R7** | temp=0.0 | All generation scripts use deterministic sampling |
| **R14** | Every object stamped | schema_version, gen_model, pipeline_commit, pipeline_run_id, taxonomy_version |

---

## 2. THE 6-STAGE PIPELINE

### Architecture Flow

```
BOOKS/                          852 books across 8 domain folders
  │
  ▼
┌──────────────────────────────────────────────────────────────┐
│ STAGE 0: CONVERT                   EPUB/PDF/MD → Markdown    │
│ Engine: Pandoc (EPUB/PDF)          280 lines                 │
│ Fallback: Docling                  7 functions               │
│ Output: stage0_convert.jsonl       (book paths → MD paths)   │
└──────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────┐
│ STAGE 1: CHUNK                    MD → Segments              │
│ Method: Section-aware splitting   268 lines                  │
│ Dedup: SHA-256 exact              6 functions                │
│ Size: ~300 words, 50-word overlap                           │
│ Output: stage1_chunk.jsonl        (segments + hashes)        │
└──────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────┐
│ STAGE 2: EXTRACT                  Segments → Principles      │
│ Generator: Qwen3-Coder-30B (OMLX) 277 lines                  │
│ Method: batch extraction prompt   7 functions                │
│ Dedup: MinHash near-dedup         temp=0.0 (R7)              │
│ Output: stage2_extract.jsonl      (principles + sources)     │
└──────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────┐
│ STAGE 3: CLUSTER                  Principles → Clusters      │
│ Embed: nomic-embed-text (Ollama)  253 lines                  │
│ Reduce: PCA (50 dims)             7 functions                │
│ Cluster: HDBSCAN (density-based)                            │
│ Output: stage3_cluster.jsonl      (clusters + cohesion)      │
└──────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────┐
│ STAGE 4: MERGE + CLASSIFY         Clusters → FBs             │
│ Generator: Qwen3-Coder-30B (OMLX) 473 lines                  │
│ Method: Merge principles → FB     8 functions                │
│ Classify: SALSA single-pass       temp=0.0 (R7)              │
│ SYNONYM MATCH: 643-entry index    (P1.5-B: new in v2.0.1)   │
│ RAW PRESERVE: domains_raw,        (P1.5-A: Channel B fix)    │
│              discipline_raw                                  │
│ PROVENANCE: s3_original_domain,   (P1.5-E: new in v2.0.1)   │
│             pipeline_run_id                                  │
│ Output: stage4_merge.jsonl        (FBs + classification)     │
└──────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────┐
│ STAGE 5: VERIFY                   FBs → Verified FBs         │
│ Verifier: Phi-4-mini (OMLX)       313 lines                  │
│ Checks: BORP (≥2 sources)         8 functions                │
│         Completeness (7 fields)    R5: Gen ≠ Verifier         │
│         Factual consistency        temp=0.0 (R7)              │
│ Status: PASS / FLAG / QUARANTINE                            │
│ Output: stage5_verify.jsonl       (verified FBs + results)   │
└──────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────┐
│ STAGE 6: COMMIT                   Verified FBs → Storage     │
│ Database: SQLite (FTS5 search)    364 lines                  │
│ Export: Parquet snapshot          9 functions                │
│ Schema: 31 columns                Auto-migration support     │
│ Output: maxwell.db + parquet/     (queryable knowledge base) │
└──────────────────────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────────────────────────────┐
│ RETRIEVAL LAYER                   Hybrid Search              │
│ Methods: FTS5 full-text           277 lines (retrieve.py)    │
│          Keyword + metadata        285 lines (query.py)      │
│          Vector (sqlite-vec)       140 lines (route.py)      │
│ Output: Queryable FB corpus for    (folder routing + counts) │
│         skills, agents, humans                               │
└──────────────────────────────────────────────────────────────┘
```

### Stage Processing Capacity (Triad Test)

| Metric | Value |
|--------|-------|
| Books processed | 14 (diverse: AI, design, business, code, physics) |
| Segments generated | 307 |
| Principles extracted | 188 |
| Clusters formed | 14 |
| FBs generated | 14 |
| PASS | 3 (BORP + completeness passed) |
| FLAG | 10 (BORP-only failure — single-source books) |
| QUARANTINE | 1 (too basic — syntax documentation) |
| Classification errors | 1 out of 14 (93% SALSA validity) |

---

## 3. CLASSIFICATION SYSTEM

### 3.1 Taxonomy

- **25 canonical domains** (graphic_design through research_&_methodology) + "emerging"
- **47 canonical disciplines** (visual_perception through philosophy) + "emerging"
- **Source:** `config/taxonomy_v5.yaml` — canonical labels are **temporary placeholders**
- **Labels are NOT fixed** — they earn their place through accumulation

### 3.2 Classification Method: SALSA (Single-pass LLM)

```
Stage 4 prompt → Qwen3-Coder-30B → JSON output →
  ├── SYNONYM MATCH (643-entry index from taxonomy raw aliases + synonym_map.yaml)
  ├── Pydantic Literal validation (structurally impossible to emit invalid labels)
  ├── Canonical assigned OR "emerging" + raw preserved
  └── Stamped: classification_method=SALSA, domains_raw, discipline_raw
```

### 3.3 Property Logic (P1.5-A/B/C — implemented 2026-07-19)

```
LLM OUTPUT:  "Visual Communication" (non-canonical)
     │
     ├── SYNONYM LOOKUP: "visual communication" → "graphic design" ✅
     │   → domains_canonical = ["graphic design"]
     │   → domains_raw = ["Visual Communication"]  ← PRESERVED FOREVER
     │
     └── NO MATCH: "Neuroscience" (no canonical, no synonym)
         → domains_canonical = ["emerging"]
         → domains_raw = ["Neuroscience"]  ← PRESERVED FOREVER
         → Accumulates. When enough FBs share "Neuroscience" raw,
           it earns a canonical slot in taxonomy_v5.yaml.
```

### 3.4 Folder Routing (P1.5-C)

```
Priority chain:
  1. First non-emerging canonical domain → safe folder name
  2. First non-emerging raw domain → safe folder name
  3. "emerging"

Example:
  canonical=["emerging"], raw=["Neuroscience"] → folder="neuroscience"
```

### 3.5 Provenance Fields (P1.5-E)

| Field | Source | Purpose |
|-------|--------|---------|
| `pipeline_run_id` | UUID generated once per run | Lineage — which run produced this FB |
| `s3_original_domain` | Source book path | Crawl provenance — which domain folder |
| `classification_method` | "SALSA" | Which classifier produced labels |
| `taxonomy_version` | "v5.0" | Which taxonomy was used |

---

## 4. FB SCHEMA (24 Fields After Inheritance)

### FB Body Fields

| Field | Type | Description |
|-------|------|-------------|
| `fb_id` | str | SHA-256 of name + definition |
| `name` | str | 3-7 word concept name |
| `definition` | str | 3-4 sentences (name + mechanism + constraints) |
| `application` | str | "When [situation] → do [action]" |
| `failure_mode` | str | How this principle fails |
| `elaboration` | str | 3-5 sentences of nuance |
| `keywords` | str | 3-5 comma-separated terms |
| `jargon` | str? | Specialized terms explained |

### Classification Fields

| Field | Type | Description |
|-------|------|-------------|
| `domains` | list[Literal] | 1-5 canonical domains (or ["emerging"]) |
| `discipline` | Literal | Canonical discipline (or "emerging") |
| `domains_raw` | list[str]? | LLM's original domains (preserved forever) |
| `discipline_raw` | str? | LLM's original discipline (preserved forever) |
| `depth` | Literal | universal / cross-domain / domain / specialized |
| `evidence` | Literal | cited (from source) / axiomatic (self-evident) |

### Provenance Fields

| Field | Type | Description |
|-------|------|-------------|
| `source_clusters` | list[int] | Cluster IDs that formed this FB |
| `source_books` | list[str] | Distinct source book paths |
| `s3_original_domain` | str? | Crawl provenance folder |
| `classification_method` | str | SALSA / FastFit / manual |
| `classification_errors` | list[str]? | Validation errors (empty = clean) |

### Verification Fields (Stage 5)

| Field | Type | Description |
|-------|------|-------------|
| `verification_results` | list[dict] | BORP + completeness + factual results |
| `borp_score` | float | distinct_sources / min_required |
| `status` | Literal | PASS / FLAG / QUARANTINE / PENDING |
| `needs_human_review` | bool | True if FLAG or QUARANTINE |
| `verifier_model` | str? | Model that performed verification |

### Stamp Fields (Inherited from StampedRecord)

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | str | "2.0" |
| `gen_model` | str? | Generator model |
| `pipeline_commit` | str | Git commit hash |
| `pipeline_run_id` | str? | UUID per pipeline run |
| `taxonomy_version` | str | "v5.0" |
| `created_at` | str | ISO 8601 timestamp |

---

## 5. DATA FLOW BETWEEN STAGES

### Inter-Stage Contracts

```
JSONL checkpoint files — each stage reads previous, writes its own:

stage0_convert.jsonl:  [{path, book_path, format, word_count}, ...]
stage1_chunk.jsonl:    [{segment_id, text, source_book, char_start, char_end, word_count}, ...]
stage2_extract.jsonl:  [{principle_id, principle_text, source_segments, source_books}, ...]
stage3_cluster.jsonl:  [{cluster_id, principle_ids, centroid_text, cohesion, size}, ...]
stage4_merge.jsonl:    [{fb_id, name, definition, ..., domains, discipline, domains_raw, ...}, ...]
stage5_verify.jsonl:   [{...all FB fields..., verification_results, status, borp_score}, ...]
stage6_commit.jsonl:   [{fb_id, name, status, committed_to_sqlite, parquet_snapshot}, ...]
```

### Deduplication Strategy

| Stage | Method | What It Prevents |
|-------|--------|-----------------|
| Stage 1 | SHA-256 hash of text | Exact duplicate segments |
| Stage 2 | MinHash LSH | Near-duplicate principles |
| Stage 3 | HDBSCAN + PCA | Semantic duplicates via clustering |
| Stage 4 | SHA-256 of name+definition | Duplicate FBs across runs |

---

## 6. STORAGE ARCHITECTURE

### SQLite Schema (31 columns)

```sql
fbs (
    -- Identity
    fb_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    
    -- Body (7 fields)
    definition TEXT NOT NULL,
    application TEXT,
    failure_mode TEXT,
    elaboration TEXT,
    keywords TEXT,
    jargon TEXT,
    
    -- Classification (6 fields)
    domains TEXT NOT NULL,        -- JSON array, canonical
    domains_raw TEXT,             -- JSON array, LLM original
    discipline TEXT NOT NULL,
    discipline_raw TEXT,          -- LLM original
    depth TEXT NOT NULL,
    evidence TEXT NOT NULL,
    
    -- Provenance (7 fields)
    source_clusters TEXT,         -- JSON array
    source_books TEXT,            -- JSON array
    s3_original_domain TEXT,
    classification_method TEXT,
    classification_errors TEXT,   -- JSON array
    verification_results TEXT,    -- JSON array
    borp_score REAL,
    
    -- Status
    status TEXT NOT NULL,
    needs_human_review INTEGER,
    verifier_model TEXT,
    
    -- Stamps (6 fields)
    schema_version TEXT,
    gen_model TEXT,
    pipeline_commit TEXT,
    pipeline_run_id TEXT,
    taxonomy_version TEXT,
    created_at TEXT,
    committed_at TEXT
);

-- Full-text search
fbs_fts USING fts5(name, definition, keywords, content='fbs');
```

### Parquet Snapshots

Timestamped exports: `data/parquet/fbs_snapshot_20260718_202842.parquet`
Compression: Snappy. Compatible with DuckDB, Pandas, any data tool.

---

## 7. MODEL ARCHITECTURE

### Active Models

| Role | Model | Provider | Port | Cost |
|------|-------|----------|------|------|
| **Generator** (Stages 2, 4) | Qwen3-Coder-30B-A3B-Instruct-MLX-4bit | OMLX | 11435 | $0 |
| **Verifier** (Stage 5) | Phi-4-mini-instruct-8bit | OMLX | 11435 | $0 |
| **Embedder** (Stage 3) | nomic-embed-text | Ollama | 11434 | $0 |
| **Planned: Cross-family verifier** | Gemma-4-26B-A4B-it-OptiQ-4bit | OMLX | 11435 | $0 |

### API Wrappers

```
pipeline/omlx_call.py:
  call_omlx(prompt, model, system, max_tokens) → str
  call_omlx_json(prompt, model, system, max_tokens) → dict
  check_omlx_health() → bool

pipeline/ollama_embed.py:
  embed_texts(texts, model) → list[list[float]]
  embed_query(query, model) → list[float]
```

---

## 8. FB RELIABILITY: EXECUTION-BASED APPLICABILITY TRACKING

### Concept (from v1 `tools/render_recipe.py`)

FBs aren't just extracted — they're **tested in practice**. Every time an FB is consulted during a Process Instance execution, the outcome is logged:

```sql
CREATE TABLE fb_reliability (
    fb_canonical TEXT PRIMARY KEY,
    total_executions INTEGER DEFAULT 0,
    valid_count INTEGER DEFAULT 0,
    irrelevant_count INTEGER DEFAULT 0,
    contradicted_count INTEGER DEFAULT 0,
    insufficient_count INTEGER DEFAULT 0,
    model_error_count INTEGER DEFAULT 0,
    reliability_score REAL DEFAULT 0.0,
    last_used TEXT,
    last_failed TEXT
);
```

### Execution Outcomes

| Outcome | Trigger | Reliability Impact |
|---------|---------|-------------------|
| `FB_VALID` | FB was applicable and correct | +1 valid_count |
| `FB_IRRELEVANT` | FB didn't apply to context | +1 irrelevant_count |
| `FB_CONTRADICTED` | FB's advice was wrong here | +1 contradicted_count |
| `FB_INSUFFICIENT` | Relevant but not enough | +1 insufficient_count |
| `FB_UNVERIFIED` | Couldn't determine | +1 model_error_count |

### Reliability Lifecycle

```
reliability_score = valid_count / total_executions

≥ 0.85, 10+ runs → STABLE — use confidently
0.50-0.84       → WATCH — flag in output, needs more testing
< 0.50, 5+ runs → UNSTABLE — flag for human review
< 0.20, 10+ runs → GARBAGE — propose archival
```

### Industry Gap

No existing system does **practical knowledge applicability testing**. Citation counting (Semantic Scholar), groundedness detection (Azure AI), and peer review (academia) all exist — but none answer: "When a real person tried to apply this principle to a real problem, did it actually help?" Maxwell's `fb_reliability` answers this. **This is novel.**

---

## 9. THE 3-ZONE BODY TEMPLATE

### Structure (from v1 `tools/render_zone.py`)

```
---
ZONE 1 - RELATIONS
---
status: open | draft | stable | archived
discipline: [canonical discipline]
evidence: cited | axiomatic

---
ZONE 2 - BODY
---
### DEFINITION
> 🏛️ [name + mechanism + constraints]

### APPLICATION
> 🔥 When [situation] → do [action]

### FAILURE MODE
> ⚠️ [How this principle fails in practice]

### JARGON
> 🤓 [Specialized terms explained]

---
ZONE 3 - STABLE GATE
---
### EVIDENCE
> ✅ Stable if: cited | axiomatic
source: [Author - Book Title]
```

### Zone Purposes

| Zone | Purpose | Immutable? |
|------|---------|------------|
| Zone 1 | Metadata header — machine-readable classification | Mutable (classification evolves) |
| Zone 2 | The knowledge — definition, application, failure mode | **Immutable after verification** |
| Zone 3 | Stabilization predicate — when is this FB trustworthy? | Updated by reliability system |

### Zone 3 Variants by Object Type

| Object | Zone 3 Name | Stabilization Criterion |
|--------|------------|------------------------|
| **FB** | STABLE GATE | Stable if: cited (≥2 sources) |
| **GE** (Growth Edge) | RESOLUTION | Resolves when: tested across 3+ contexts |
| **PT** (Process Template) | SHIP GATE | Tested across 3+ contexts → Active |

---

## 10. PROJECT AND MOC OBJECTS

### Project Object

```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    goal_statement TEXT,
    status TEXT CHECK(status IN ('active','paused','someday','done')),
    last_touched TEXT,
    next_action TEXT,
    owner_vs_delegated TEXT,
    est_hours_per_week REAL
);
```

**Purpose:** Container grouping related PTs/PIs toward a goal. Enables the Coordinator Recipe — daily cross-project triage. Connects PTs via `parent_project` property.

### MOC (Map of Content)

**Purpose:** Navigational structure linking related FBs and PTs in a domain. Human navigation layer (agents use vector search). Built via a recurring PT — "build a MOC for domain X." Turns "19,863 FBs" from paralyzing into "a queue of MOC-building PT executions."

### Relationship Map

```
PROJECT
  ├── MOC (navigational, human-facing)
  │     ├── FB (reliability: 0.91)
  │     └── FB (reliability: 0.72 — WATCH)
  ├── PT (procedural, references FBs)
  │     ├── Step 1: consult FB_1, FB_2
  │     └── Step 2: consult FB_3
  └── PI (one execution)
        ├── FB_1 outcome: FB_VALID
        └── → updates fb_reliability
```

---

## 11. SKILL ORCHESTRATION CHAIN

### The Complete Chain

```
BOOKS → [Stages 0-6] → VERIFIED FBs (with reliability scores)
                           │
                           ▼
                    PT (Process Template)
                    "procedure that references FBs"
                           │
                           ▼
                    PI (Process Instance)
                    "one execution, one goal"
                           │
                           ▼
                    FB EXECUTION LOGGING
                    "did each FB actually help?"
                           │
                           ▼
                    fb_reliability SCORES
                    "this FB works 94% of the time"
                           │
                           ▼
                    GOOSE RECIPE
                    "executable skill with grounded FBs"
                           │
                           ▼
                    TRUST LEDGER
                    "this skill auto-executes after 20+ successful runs"
```

### Three Skill Creation Paths

| Path | Reliability | Speed | Use Case |
|------|-----------|-------|----------|
| **A: FB-Grounded Recipe** | HIGH — every step cites verified FBs | Medium | Production skills |
| **B: MOC-Based Conductor Loop** | MEDIUM — multi-agent orchestration | Slower | Complex business ops |
| **C: Direct FB → Recipe** | LOWER — no formal procedure | Fast | Rapid prototyping |

### Goose Recipe Structure (Target Format)

```yaml
name: pricing-compass
version: 1.0.0
grounding_fbs:
  - fb_id: "sha256..."
    name: "Value-Based Pricing Over Cost-Plus"
    reliability: 0.91
steps:
  - id: assess-value
    description: "Determine client value drivers"
    consulted_fbs: [fb_id_1]
    done_when: "3 value drivers identified"
verification:
  model: "gemma-4-26B"  # R5: different family
gate:
  type: "bash"
  check: "grep -c 'Source:' output.md | grep -q '[3-9]'"
trust_tier: "watch"
```

---

## 12. FILE INVENTORY

### Pipeline Core (7,299 lines total)

| File | Lines | Purpose |
|------|-------|---------|
| `pipeline_paths.py` | 105 | Single source of truth for all I/O paths |
| `schemas.py` | 493 | Pydantic v2 models, Literal types, synonym index |
| `stamp.py` | 109 | R14 provenance stamps, UUID generation |
| `omlx_call.py` | 201 | OMLX HTTP wrapper (chat + JSON mode) |
| `ollama_embed.py` | 131 | Ollama embedding calls |
| `stage0_convert.py` | 280 | EPUB/PDF → Markdown |
| `stage1_chunk.py` | 268 | MD → Segments + SHA-256 dedup |
| `stage2_extract.py` | 277 | Principles + MinHash dedup |
| `stage3_cluster.py` | 253 | Embed + PCA + HDBSCAN |
| `stage4_merge.py` | 473 | Clusters → FBs + SALSA + synonym match |
| `stage5_verify.py` | 313 | BORP + completeness + factual check |
| `stage6_commit.py` | 364 | SQLite + Parquet + FTS5 |
| `retrieve.py` | 277 | Hybrid search (FTS5 + keyword + vector) |
| `query.py` | 285 | CLI browser for FBs |
| `route.py` | 140 | Folder routing + raw label accumulation counter |
| `status.py` | 201 | Pipeline dashboard |

### Utility Files (ported from v1)

| File | Lines | Purpose |
|------|-------|---------|
| `io_guard.py` | 163 | Crash-safe writes (C6) |
| `doc_guard.py` | 221 | Protected file access (R-D824) |
| `safe_delete.py` | 197 | Safe deletion (R-D410) |
| `model_lazyload.py` | 222 | Lazy model loading |
| `json_repair.py` | 391 | JSON repair for LLM output |
| `backup_guardian.sh` | 83 | Backups after batch writes (C13) |

### Config Files (2,921 lines, partially wired)

| File | Lines | Wired To |
|------|-------|----------|
| `taxonomy_v5.yaml` | ~500 | `schemas.py` (Literal types, synonym index) |
| `synonym_map.yaml` | 743 | `schemas.py` (643-entry synonym lookup) |
| `domain_disciplines.yaml` | 960 | NOT WIRED — available for future use |
| `domain_anchors.yaml` | ~500 | NOT WIRED |
| `pipeline_config.yaml` | ~200 | NOT WIRED — pipeline_paths.py hardcodes values |
| `model_assignments.yaml` | ~200 | Partially — model names in pipeline_paths.py |

---

## 13. CURRENT LIMITATIONS & OPEN QUESTIONS

### Acknowledged Gaps

| Gap | Status | Plan |
|-----|--------|------|
| **FB reliability not wired in v2** | v1 has it (`render_recipe.py`, 1070 lines). Not yet ported. | P1.5-F: port after Alpha Kit validates |
| **Zone 3 doesn't show reliability_score** | Static (BORP only). Dynamic rendering planned. | Phase 1.5 — render from DB |
| **Multimodal extraction** | Stage 0 does text only. Images/diagrams discarded. | Phase 2 — Docling/vision models |
| **Structured output** | JSON mode (model goodwill), not token-level constraint | Phase 2 — Toolio/Outlines |
| **Project/MOC objects** | Spec exists, not built in v2 | Phase 2 — after 50+ FBs |
| **Cross-domain relationships** | FBs are standalone. No supports/contradicts/extends links | Phase 2 |
| **14 FBs is not a knowledge base** | Pipeline proven. Needs scale. | Alpha Kit → 30-50 FBs per domain |

### Key Architecture Decisions Still Open

1. **Model2Vec + FastFit cascade** (Ultimate Spec) — 5,000x faster classification but needs 500+ S7-cleaned FBs to train. BLOCKED until we have more FBs.

2. **Taxonomy governance** (Seed + Candidate + Audit) — spec exists. Foundation built (raw preservation, synonym matching). Full audit engine deferred.

3. **Goose Recipes vs. Subagents** — is the YAML recipe format sufficient, or do skills need MCP tool access via subagents?

4. **Conformal prediction** — mathematical confidence sets. Needs calibration data (more FBs).

---

## 14. ROUNDTABLE EVALUATION QUESTIONS

### For Evaluation by Claude, Kimi, DeepSeek, Grok, Qwen

1. **Pipeline Architecture:** Is the 6-stage design optimal? Any stage that should be split, merged, or reordered?

2. **Classification:** Is SALSA + synonym matching sufficient for 25-domain, 47-discipline classification at scale? When should we switch to FastFit?

3. **FB Reliability:** Is cumulative execution tracking the right method? Should we use decaying windows (recent executions weighted more)?

4. **Skill Orchestration:** Is FB → PT → Recipe the right chain? Is the Goose Recipe format sufficient, or do we need full subagent-based skills?

5. **Missing Pieces:** What's the ONE capability this architecture needs that it doesn't currently address?

6. **Industry Comparison:** Where does Maxwell OS have genuine structural advantages vs. CrewAI, LangChain, Dify, Notion AI, Mem? Where will they catch up?

7. **Scalability:** Does this architecture scale to 850 books → 10,000 FBs → 100 skills? What breaks first?

8. **Lightweight Alternative:** Is there a simpler way to achieve the core goal (verified, grounded knowledge for agent skills) with fewer stages, less code, or fewer dependencies?

---

*Document: MAXWELL-OS-KNOWLEDGE-PIPELINE-ARCHITECTURE.md*
*7,299 lines of pipeline code | 852 books | 14 FBs | 6 stages | 31-column schema*
*For cross-examination and improvement proposals against Maxwell OS constraints*
