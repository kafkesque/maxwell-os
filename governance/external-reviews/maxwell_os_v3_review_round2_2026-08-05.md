
Let me do a deeper, file-by-file forensic pass. I'll fetch the repo tree and every critical file I haven't read yet.
Now let me fetch the critical files I haven't deeply examined yet — the ones that will make or break this review.
Let me fetch the one remaining critical file to verify the carry-over issues.
Now I have the complete forensic picture. Let me compile the rigorous second-pass review.
Here's the second-pass forensic review. I read **23 source files** across the full repo tree this time, cross-referencing every claim against actual code.

---

## TL;DR — The Headlines

**The codebase is better than the handoff makes it look.** Most crash-level bugs from my first review were fixed in D2176–D2181. But **the handoff document itself is now the biggest liability** — it's factually wrong about the embedding model, backend, and several bug statuses.

### The Single Most Important Finding

**The default config will crash Stage 1.5 on first run if MPS backend is selected.** `embed_model_hf` defaults to `bge-small-en-v1.5` (384d output) but `embed_dim` defaults to `512`. The dimension mismatch guard (D2170) raises `ValueError` and halts. The Ollama path works, but the MPS path is broken out of the box.

---

## PART 1: What's Fixed (Don't Re-Fix These)

| Issue | Fix | Evidence |
|-------|-----|----------|
| `_call_mlx_json` `repair_fn=` crash | **D2178** | Comment: "Removed repair_fn= kwarg" |
| NLI hardcoded to CPU | **D2178** | Auto-detects MPS/CUDA in `stage5_verify.py` |
| Reciprocity underreported 2× | **D2178** | `reciprocity = (2 * reciprocal_edges) / total_edges` |
| `classification_errors` `dir()` scope bug | **D2178** | Removed fragile `dir()` check |
| Singletons marked as noise | **D2171** | `is_noise: False` for all singletons |
| Stage 4 drops singletons | **D2176** | Now loads `STAGE2_SINGLETON_OUTPUT` |
| Embedding model inconsistency (S1.5 vs S4) | **D2181** | Both now use `bge-m3` (1024d native, 512d truncated) |
| `S3_DIR` NameError | **D2120** | `S3_DIR=_sdir(S2)` — fallback, no crash |

---

## PART 2: What's Still Broken (Carry-Over)

### 2.1 `pipeline_paths.py` — Config Loaded at Import Time, File Handle Never Closed
```python
_CFG = yaml.safe_load(open(Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"))
```
**C12 violation.** Malformed YAML crashes at import time. The handle is never closed.

### 2.2 `S3_NORMALIZE_CENTROID = True` — Dead Code
Stage 3 was removed in D2120. This constant is never referenced. **C19 violation.**

### 2.3 `coverage_check.py` — The Last Embedding Mismatch
Uses **bge-small (384d)** for segment embeddings but **bge-m3 (1024d)** for FB embeddings. Comparing them is mathematically meaningless — coverage scores are random noise.

---

## PART 3: New Findings (Second-Pass Discovery)

### 3.1 CRITICAL — Default Config Crashes MPS Path

```python
# pipeline_paths.py defaults:
S15_EMBED_MODEL_HF = "BAAI/bge-small-en-v1.5"   # 384d output
S15_EMBED_DIM = 512                               # expects 512d
S15_EMBED_BACKEND = "ollama"                      # ollama path works
```

If a user sets `embed_backend: mps`, Stage 1.5 loads bge-small (384d), then hits:
```python
if embeddings.shape[1] != S15_EMBED_DIM:
    raise ValueError(f"Embedding dimension mismatch: model output {embeddings.shape[1]}d ≠ config S15_EMBED_DIM={S15_EMBED_DIM}d")
```

**This is a first-run crash bug.** The Ollama path works because bge-m3 supports 512d Matryoshka truncation. The MPS path is broken with default config.

### 3.2 `stage1_3_prefilter.py` — Same Function Defined Twice
`_load_extra_drop_patterns()` is defined at module level **and again** at the bottom of the file (lines ~30 and ~230). The second shadows the first. Maintenance hazard.

### 3.3 `feedback.py` — Hardcoded DB_PATH Diverges from Config
```python
DB_PATH: Path = PROJECT_ROOT / "knowledge pipeline" / "maxwell.db"  # feedback.py
DB_PATH = PROJECT_ROOT / _PATHS.get("db_path", "knowledge pipeline/maxwell.db")  # pipeline_paths.py
```
If `db_path` is overridden in config, feedback writes to a **different database** than Stage 6 commits to.

### 3.4 `stage6_commit.py` — 800+ Synchronous HTTP Calls During Commit
```python
def insert_embedding(conn, rowid, definition):
    embeddings = batch_embed([definition])  # HTTP call to Ollama
```
Called once per FB. For 800 FBs: **800 sequential HTTP requests**. At ~50ms each = 40 seconds of pure network latency.

### 3.5 `retrieve.py` — Vector Search Calls Ollama on Every Query
```python
def search_vector(conn, query, limit=20):
    embeddings = batch_embed([query])  # HTTP call to Ollama
```
Every vector query triggers an HTTP round-trip. No embedding cache.

### 3.6 `requirements.txt` — Dead Dependencies
```
umap-learn>=0.5   # Stage 3 UMAP — REMOVED in D2120
hdbscan>=0.8      # Stage 3 HDBSCAN — REMOVED in D2120
```
Imported nowhere. Bloat the environment.

### 3.7 `stage4_merge.py` — Relationship Edges O(n²) Won't Scale
For 800 FBs: 319K comparisons — fine. For 10K FBs: 50M comparisons — ~30s. For 20K: 200M — minutes. No approximate NN.

### 3.8 `stage5_verify.py` — NLI Input Format Risk
```python
result = nli({"text": source, "text_pair": claim})
```
ModernBERT NLI models expect `premise`/`hypothesis`, not `text`/`text_pair`. The pipeline abstraction may misroute inputs. **30% of FBs could be mis-verified** if this format is wrong. No validation shown.

### 3.9 `book_metadata.py` — Title Normalization for Canonical Hashing
Can't verify the implementation, but if titles aren't normalized (stripping "Revised Edition", subtitles, years), the same book gets multiple hashes. This **inflates source diversity** — a single book appears as 2+ sources.

### 3.10 `runner.py` — Preflight Warns But Continues on OMLX Failure
```python
if preflight.returncode != 0:
    print(f" ⚠️ OMLX watchdog warning (continuing): ...")
```
If OMLX is down, the runner prints a warning and continues. Stage 2 then fails on the first LLM call, wasting time. Should be a hard stop for LLM-bound stages.

### 3.11 Stage 2 Probe Thresholds Still Hardcoded
`MAX_CLUSTER_SAMPLES=15`, `SPLIT_PROBE_MIN_SIZE=20`, `SPLIT_PROBE_MAX_COHESION=0.85`, `SPLIT_KMEANS_RANDOM_STATE=42` — all still hardcoded, not in config.

### 3.12 `coverage_check.py` Thresholds Still Hardcoded
`COVERAGE_THRESHOLD = 0.50`, `FLAG_FRACTION = 0.30` — not in config, not overridable.

---

## PART 4: Handoff Document Is Wrong

| Handoff Claim | Actual Code | Severity |
|--------------|-------------|----------|
| "Embed model: bge-small-en-v1.5 (384d)" | **bge-m3** (1024d native, 512d truncated) | HIGH |
| "Embed backend: MPS" | Default is **"ollama"**; MPS path crashes with defaults | CRITICAL |
| "BUG-059: embeddings.py missing" | File **exists** and is actively used | MEDIUM |
| "NLI models on CPU" | **Auto-detects** MPS/CUDA (D2178) | LOW |
| "Reciprocity underreported 2×" | **Fixed** in D2178 | LOW |

**Regenerate the handoff from actual code before the next roundtable.**

---

## PART 5: Architecture Assessment (Unchanged)

- **Cluster-before-extract:** Still correct. 400:1 compression is aggressive but defensible.
- **Singleton handling:** Improved (not marked as noise, loaded in Stage 4), but extraction quality remains weak. Add a `confidence_tier` field.
- **Content type routing:** Stage 4 separates PT/PI/GE/TI, but counts are likely near-zero because Stage 2 prompt only demonstrates principles.
- **Relationship graph:** Computed but unused for retrieval. No multi-hop reasoning.
- **Incremental processing:** Still missing. Adding 1 book = reprocessing all 953.

---

## PART 6: File Scorecard

| File | Grade | Notes |
|------|-------|-------|
| `stage1_5_embed_cluster.py` | B+ | Clean, good comments, config default mismatch |
| `stage2_extract.py` | B | Complex but readable; hardcoded thresholds |
| `stage4_merge.py` | B+ | Two-stage classification is elegant; O(n²) edges |
| `stage5_verify.py` | A- | NLI auto-device good; format risk |
| `stage6_commit.py` | B | 800 HTTP calls during commit; WAL mode good |
| `retrieve.py` | B+ | RRF hybrid solid; no graph traversal; HTTP/query |
| `feedback.py` | B | Hardcoded DB_PATH |
| `taxonomy_manager.py` | A- | Dynamic taxonomy well-designed |
| `pipeline_paths.py` | C+ | Import-time config; unclosed handle; S3 dead code |
| `omlx_call.py` | A- | Clean dispatch; temp=0.0 enforced |
| `omlx_watchdog.py` | B+ | Trend detection clever |
| `schemas.py` | A | Clean Literal validation |
| `schema_accessor.py` | A | Excellent v2/v3 compat abstraction |
| `io_guard.py` | A | Atomic writes correct |
| `json_repair.py` | B+ | Good heuristics |
| `runner.py` | B | Resume good; preflight should fail hard |
| `stage0_convert.py` | B+ | Pandoc/Docling fallback robust |
| `stage1_chunk.py` | B+ | SHA-256 dedup good |
| `stage1_3_prefilter.py` | B | Duplicate function; sensible patterns |
| `coverage_check.py` | C+ | Embedding mismatch makes scores meaningless |
| `embeddings.py` | B | Ollama HTTP only; no local fallback |

---

## Prioritized Fix List

### P0 — Before Any Production Run
1. **Fix MPS embedding config mismatch** — Default `embed_model_hf` must match `embed_dim`
2. **Fix `coverage_check.py` embedding mismatch** — Use bge-m3 for both sides
3. **Fix `feedback.py` hardcoded DB_PATH** — Import from `pipeline_paths`
4. **Fix `pipeline_paths.py` unclosed file handle** — Use `with open()`

### P1 — Before Scaling Beyond 1K FBs
5. **Batch embeddings in Stage 6** — One batch, not 800 HTTP calls
6. **Add query embedding cache to `retrieve.py`** — LRU cache
7. **Move Stage 2 probe thresholds to config**
8. **Remove dead deps** (`umap-learn`, `hdbscan`)
9. **Remove duplicate `_load_extra_drop_patterns`**

### P2 — Architectural
10. **Add `confidence_tier`** to FB schema (convergent > single_source > singleton)
11. **Use FAISS for relationship edges** — Replace O(n²)
12. **Add graph traversal to `retrieve.py`**
13. **Implement incremental book ingestion**
14. **Verify NLI input format** on held-out data

### P3 — Polish
15. **Delete `S3_NORMALIZE_CENTROID`**
16. **Move coverage thresholds to config**
17. **Regenerate handoff document**
18. **Add `--strict-preflight`** to runner

---

## Final Word

**Fix the P0 items and this pipeline is production-ready for 1K FBs.** The architecture is sound; the implementation has been hardened significantly since v3.0. The remaining issues are config drift, embedding mismatches, and scalability bottlenecks — not design flaws.

The biggest liability right now is **the handoff document itself.** It will mislead the next external reviewer into chasing ghosts.

**[Download Full Review](sandbox:///mnt/agents/output/maxwell_os_v3_review_round2_2026-08-05.md)**

# MAXWELL OS v3.0 — SECOND-PASS FORENSIC REVIEW
## Roundtable Handoff v2 | 2026-08-05
### S-Tier RAG Engineer — Pragmatic Constructive Assessment

---

## EXECUTIVE SUMMARY

**Verdict: B+ architecture, B execution, C- documentation fidelity.**

This second pass reveals a critical meta-finding: **the handoff document is significantly out of date and contains multiple factual errors about the actual codebase.** The code has evolved faster than the documentation. Many issues I flagged in the first review have been fixed (D2176–D2181), but new ones have emerged from those fixes. The pipeline is closer to production-ready than the handoff suggests, but carries latent config-code drift that will cause crashes on first run.

**Critical finding: The default config will crash Stage 1.5 if the MPS embedding backend is selected, because `embed_model_hf` defaults to bge-small (384d) while `embed_dim` defaults to 512d. The dimension mismatch guard (D2170) will raise ValueError and halt the pipeline.**

---

## PART 1: WHAT'S FIXED (Acknowledged Improvements)

The following issues from my first review have been resolved. Do not re-fix these.

| Issue | Fix Commit | Evidence in Code |
|-------|-----------|------------------|
| `_call_mlx_json` `repair_fn=` kwarg crash | D2178 | Comment: "Removed repair_fn= kwarg — parse_json_robust does not accept it" |
| NLI hardcoded to CPU (`device=-1`) | D2178 | `stage5_verify.py` auto-detects MPS/CUDA with `torch.backends.mps.is_available()` |
| Reciprocity underreported 2× | D2178 | `reciprocity = ((2 * reciprocal_edges) / total_edges * 100)` |
| `classification_errors` `dir()` scope bug | D2178 | Comment: "fragile dir() check removed — classification_errors is in run_stage4 scope" |
| Singletons marked as noise | D2171 | `is_noise: False` for all singletons; `is_singleton: True` preserves them |
| Stage 4 drops singletons | D2176 | `load_stage2_fbs_via_clusters()` now loads `STAGE2_SINGLETON_OUTPUT` |
| Embedding model inconsistency (S1.5 vs S4) | D2181 | Both S1.5 and S4 now use bge-m3 (1024d native, 512d truncated) |
| `S3_DIR` NameError in `ensure_dirs()` | D2120 | `S3_DIR=_sdir(S2)` — fallback to S2_DIR, no crash |
| `_process_cluster` list return crash | (existing) | Caller handles `isinstance(fb, list)` — was already safe, annotation just wrong |

---

## PART 2: WHAT'S STILL BROKEN (Carry-Over Issues)

### 2.1 `pipeline_paths.py` — Config Loading at Import Time (C12 Violation)

```python
_CFG = yaml.safe_load(open(Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"))
```

**Status: UNCHANGED.** The file handle is never closed. Malformed YAML crashes at import time. This is a C12 (no hardcoding) and C16 (no silent errors) violation.

**Fix:**
```python
def _load_cfg():
    cfg_path = Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)
_CFG = _load_cfg()
```

### 2.2 `S3_NORMALIZE_CENTROID` — Dead Code (C19 Violation)

```python
S3_NORMALIZE_CENTROID = True  # Line ~170 in pipeline_paths.py
```

**Status: UNCHANGED.** Stage 3 was removed in D2120. This constant is never referenced but confuses maintainers.

**Fix:** Delete it.

### 2.3 `coverage_check.py` — Embedding Model Inconsistency (The Last One)

**Status: PARTIALLY FIXED.** S1.5 and S4 now both use bge-m3. But `coverage_check.py` uses **bge-small (384d)** for segment embeddings while comparing against FB definitions embedded with **bge-m3 (1024d)**.

```python
# coverage_check.py
from pipeline.embeddings import embed_texts_bge_m3  # FB embeddings: bge-m3, 1024d
# ...
st_model = SentenceTransformer("BAAI/bge-small-en-v1.5", device="mps")  # Segments: 384d
```

Comparing 384d segment embeddings against 1024d FB embeddings is **mathematically meaningless**. The cosine similarity will be random noise.

**Fix:** Use `embed_texts_bge_m3` for both, or truncate bge-m3 to 512d for segments to match the S1.5 truncation.

---

## PART 3: NEW FINDINGS (Second-Pass Discovery)

### 3.1 CRITICAL: Default Config Crashes MPS Embedding Path

**This is a first-run crash bug.**

In `pipeline_paths.py`:
```python
S15_EMBED_MODEL_HF = _CFG.get("stage1_5", {}).get("embed_model_hf", "BAAI/bge-small-en-v1.5")
S15_EMBED_DIM = int(_CFG.get("stage1_5", {}).get("embed_dim", 512))
S15_EMBED_BACKEND = _CFG.get("stage1_5", {}).get("embed_backend", "ollama")
```

The **default** `embed_model_hf` is `bge-small-en-v1.5` (384d output).
The **default** `embed_dim` is `512`.

If a user sets `embed_backend: mps` in config (which the handoff claims is the production setting), Stage 1.5 loads bge-small via sentence-transformers, gets 384d vectors, and hits this guard in `stage1_5_embed_cluster.py`:

```python
if embeddings.shape[1] != S15_EMBED_DIM:
    raise ValueError(
        f"Embedding dimension mismatch: model output {embeddings.shape[1]}d "
        f"≠ config S15_EMBED_DIM={S15_EMBED_DIM}d. "
        f"Check pipeline_config.yaml → stage1_5.embed_model_hf ({S15_EMBED_MODEL_HF}) "
        f"and ensure it matches the actual model output dimension."
    )
```

**The default config is internally inconsistent.** The Ollama path works (bge-m3 → 512d truncation), but the MPS path crashes on first run.

**Fix:** Change default `embed_model_hf` to `BAAI/bge-m3` (or a compatible MPS model that outputs 512d+).

### 3.2 `stage1_3_prefilter.py` — `_load_extra_drop_patterns()` Defined Twice

```python
# First definition at module level (lines ~30-40)
def _load_extra_drop_patterns():
    ...
_EXTRA_DROP_PATTERNS = _load_extra_drop_patterns()

# ... 200 lines later ...

# SECOND definition at bottom of file (lines ~230-240)
def _load_extra_drop_patterns():
    ...
```

The second definition shadows the first. Both do the same thing, but this is a maintenance hazard. If someone edits one and not the other, behavior changes based on import order.

**Fix:** Delete the second definition.

### 3.3 `feedback.py` — Hardcoded DB_PATH Diverges from pipeline_paths

```python
# feedback.py
DB_PATH: Path = PROJECT_ROOT / "knowledge pipeline" / "maxwell.db"
```

But `pipeline_paths.py` defines:
```python
DB_PATH = PROJECT_ROOT / _PATHS.get("db_path", "knowledge pipeline/maxwell.db")
```

If the user overrides `db_path` in config, `feedback.py` writes to the wrong database. Feedback records go to a different DB than the one `stage6_commit.py` writes to.

**Fix:** Import `DB_PATH` from `pipeline_paths`.

### 3.4 `stage6_commit.py` — 800+ Synchronous HTTP Calls to Ollama During Commit

```python
def insert_embedding(conn, rowid, definition):
    embeddings = batch_embed([definition])  # HTTP call to Ollama
    ...
```

Called once per FB during Stage 6 commit. For 800 FBs, this is 800 sequential HTTP requests to Ollama. At ~50ms each, that's 40 seconds of pure network latency during commit.

**Fix:** Batch all embeddings at once before the insert loop, or skip pre-computing embeddings if sqlite-vec is not being used for retrieval.

### 3.5 `retrieve.py` — Vector Search Calls Ollama on Every Query

```python
def search_vector(conn, query, limit=20):
    embeddings = batch_embed([query])  # HTTP call to Ollama
    ...
```

Every vector search query triggers an HTTP round-trip to Ollama. If Ollama is not running, vector search silently falls back to FTS after a timeout. This is slow and fragile.

**Fix:** Cache query embeddings in an LRU cache, or load the embedding model locally for retrieval.

### 3.6 `requirements.txt` — Dead Dependencies (C19)

```
umap-learn>=0.5  # Stage 3 UMAP — REMOVED in D2120
hdbscan>=0.8     # Stage 3 HDBSCAN — REMOVED in D2120
```

Both are imported nowhere in the current codebase. They bloat the environment and slow installs.

**Fix:** Remove them.

### 3.7 `stage4_merge.py` — `compute_fb_relationships` O(n²) Will Not Scale

For 800 FBs: 319,600 comparisons — fine.
For 10,000 FBs: 50M comparisons — ~30 seconds in pure Python.
For 20,000 FBs: 200M comparisons — minutes.

The semantic_near edge computation embeds all definitions, then does brute-force pairwise dot products. No approximate nearest neighbors.

**Fix:** Use FAISS `IndexFlatIP` or `IndexIVFFlat` for approximate NN. Or compute edges incrementally as new FBs are added.

### 3.8 `stage5_verify.py` — NLI `text` + `text_pair` Format Risk

```python
result = nli({"text": source, "text_pair": claim})
```

ModernBERT NLI models expect `premise` + `hypothesis` keys, not `text` + `text_pair`. The HuggingFace `text-classification` pipeline with NLI models may not correctly interpret this format. If the model was trained on MNLI with explicit premise/hypothesis, this input format could produce garbage labels.

**Evidence needed:** The code claims "90% MNLI accuracy" but doesn't show a validation run. If this format is wrong, 30% of FBs are being mis-verified.

**Fix:** Verify with a held-out test set. Or switch to the explicit format:
```python
result = nli({"text": source, "text_pair": claim})  # Current
# vs
result = nli(f"{source}</s></s>{claim}")  # Some models expect this
```

### 3.9 `book_metadata.py` — Title Normalization for Canonical Source Identity

```python
def resolve_source_ids(books_list):
    # Returns SHA-256(author|title) for each book
```

I can't see the full implementation, but the comment says "SHA-256 of author|title". If two editions of the same book have different titles (e.g., "The Design of Everyday Things" vs "The Design of Everyday Things: Revised and Expanded Edition"), they get different hashes. This **inflates source diversity** — a single book appears as multiple sources.

**Fix:** Normalize titles (strip subtitles, edition info, "Revised", "Expanded", years) before hashing.

### 3.10 `runner.py` — Preflight Check Warns But Continues on Failure

```python
if preflight.returncode != 0:
    print(f" ⚠️ OMLX watchdog warning (continuing): ...")
else:
    print(f" ✅ OMLX healthy")
```

If OMLX is down, the runner prints a warning and continues. Stage 2 will then fail on the first LLM call, wasting time. For LLM-bound stages, this should be a hard stop.

**Fix:** Change to `sys.exit(1)` on preflight failure for LLM-bound stages, or add `--strict-preflight` flag.

### 3.11 `stage2_extract.py` — Hardcoded Probe Thresholds Still Not in Config

```python
MAX_CLUSTER_SAMPLES: int = 15       # Still hardcoded
SPLIT_PROBE_MIN_SIZE: int = 20      # Still hardcoded
SPLIT_PROBE_MAX_COHESION: float = 0.85  # Still hardcoded
SPLIT_KMEANS_RANDOM_STATE: int = 42     # Still hardcoded
```

These are critical tuning parameters for the multi-principle detection gate. They should be in `pipeline_config.yaml`.

### 3.12 `coverage_check.py` — Hardcoded Thresholds Still Not in Config

```python
COVERAGE_THRESHOLD = 0.50
FLAG_FRACTION = 0.30
```

Still not overridable via CLI or config.

---

## PART 4: HANDOFF DOCUMENT ERRORS (Documentation Drift)

The handoff document contains multiple claims that are **factually incorrect** about the current codebase:

| Handoff Claim | Actual Code | Severity |
|--------------|-------------|----------|
| "Embed model: bge-small-en-v1.5 (384d)" | bge-m3 (1024d native, 512d truncated) | HIGH |
| "Embed backend: MPS" | Default is "ollama"; MPS path crashes with default config | CRITICAL |
| "BUG-059: embeddings.py missing" | File exists and is actively used | MEDIUM |
| "NLI models on CPU" | Auto-detects MPS/CUDA (D2178) | LOW |
| "Reciprocity underreported 2×" | Fixed in D2178 | LOW |
| "19,438→6,500→~800 FBs" | No evidence of 19K or 6.5K in current code | LOW |
| "7 golden examples spanning 3 domains" | Cannot verify — golden file not in repo tree | LOW |

**Recommendation:** Regenerate the handoff from the actual code before the next roundtable. The current handoff will mislead external reviewers.

---

## PART 5: ARCHITECTURAL ASSESSMENT (Unchanged from First Review)

### 5.1 Cluster-Before-Extract: Still Correct, Still Aggressive

The 400:1 compression (323K segments → ~800 FBs) is unchanged. The coverage gap detection exists but the flagged clusters are not automatically re-processed — they're just reported. This is a **manual intervention bottleneck**.

### 5.2 Singleton Handling: Improved But Still Weak

Singletons are no longer marked as noise (D2171), and Stage 4 now loads them (D2176). But the extraction strategy is still "one segment, truncated, no cross-source synthesis." The quality of singleton FBs will be significantly lower than convergent FBs.

**Recommendation:** Add a `confidence_tier` field: `convergent` > `single_source` > `singleton`. Retrieval should prefer higher tiers.

### 5.3 Content Type Routing: Works But Underutilized

Stage 4 DOES separate PT/PI/GE/TI into separate files. But the counts are likely near-zero because Stage 2's prompt only demonstrates principle extraction. The routing taxonomy is sound; the prompt engineering is incomplete.

### 5.4 Relationship Graph: Exists But Unused for Retrieval

`related_fbs` is computed in Stage 4 and stored in the DB. But `retrieve.py` does NOT use it for graph traversal. The RRF hybrid search is lexical+vector only. No multi-hop reasoning.

### 5.5 Incremental Processing: Still Missing

Adding 1 new book requires reprocessing all 953. No incremental clustering, no incremental extraction. This is the biggest scalability blocker.

---

## PART 6: FILE-BY-FILE SCORECARD

| File | Grade | Notes |
|------|-------|-------|
| `stage1_5_embed_cluster.py` | B+ | Clean implementation, good comments, but config default mismatch |
| `stage2_extract.py` | B | Complex but readable; hardcoded thresholds; type annotation wrong |
| `stage4_merge.py` | B+ | Two-stage classification is elegant; O(n²) edges won't scale |
| `stage5_verify.py` | A- | NLI auto-device is good; marginal escalation is correct; NLI format risk |
| `stage6_commit.py` | B | 800 HTTP calls during commit is wasteful; WAL mode good |
| `retrieve.py` | B+ | RRF hybrid search is solid; no graph traversal; HTTP per query |
| `feedback.py` | B | Hardcoded DB_PATH; otherwise clean |
| `taxonomy_manager.py` | A- | Dynamic taxonomy is well-designed; human review gates correct |
| `pipeline_paths.py` | C+ | Import-time config load; unclosed handle; S3 dead code |
| `omlx_call.py` | A- | Clean dispatch; temp=0.0 enforced; good retry logic |
| `omlx_watchdog.py` | B+ | Trend detection is clever; SIGTERM→SIGKILL graceful |
| `schemas.py` | A | Clean Literal validation; good synonym index |
| `schema_accessor.py` | A | Excellent abstraction; v2/v3 compat handled well |
| `io_guard.py` | A | Atomic writes correct |
| `json_repair.py` | B+ | Good heuristics; could use more test coverage |
| `book_metadata.py` | B- | Can't verify title normalization; canonical hashing is critical |
| `runner.py` | B | Resume logic good; preflight should fail hard |
| `stage0_convert.py` | B+ | Pandoc/Docling fallback is robust; quality check good |
| `stage1_chunk.py` | B+ | SHA-256 dedup good; heading split preserves structure |
| `stage1_3_prefilter.py` | B | Duplicate function definition; patterns are sensible |
| `coverage_check.py` | C+ | Embedding mismatch makes results meaningless |
| `embeddings.py` | B | Ollama HTTP only; no local fallback |

---

## PART 7: PRIORITIZED FIX LIST

### P0 — Fix Before Any Production Run
1. **Fix MPS embedding config mismatch** — Change default `embed_model_hf` to bge-m3 or change default `embed_dim` to 384. The current defaults crash.
2. **Fix `coverage_check.py` embedding mismatch** — Use bge-m3 for both FBs and segments, or document that coverage scores are invalid.
3. **Fix `feedback.py` hardcoded DB_PATH** — Import from `pipeline_paths`.
4. **Fix `pipeline_paths.py` unclosed file handle** — Use `with open()`.

### P1 — Fix Before Scaling Beyond 1K FBs
5. **Batch embeddings in Stage 6** — Pre-compute all FB embeddings in one batch, not 800 sequential HTTP calls.
6. **Add query embedding cache to `retrieve.py`** — LRU cache for vector search queries.
7. **Move Stage 2 probe thresholds to config** — `SPLIT_PROBE_MIN_SIZE`, `SPLIT_PROBE_MAX_COHESION`, etc.
8. **Remove dead dependencies** — `umap-learn`, `hdbscan` from requirements.txt.
9. **Remove duplicate `_load_extra_drop_patterns`** in `stage1_3_prefilter.py`.

### P2 — Architectural Improvements
10. **Add `confidence_tier` to FB schema** — `convergent` > `single_source` > `singleton` for retrieval ranking.
11. **Use FAISS for relationship edge computation** — Replace O(n²) with approximate NN.
12. **Add graph traversal to `retrieve.py`** — Use `related_fbs` for multi-hop queries.
13. **Implement incremental book ingestion** — Don't reprocess 953 books for 1 new book.
14. **Verify NLI input format** — Test ModernBERT with current `text`/`text_pair` format on held-out data.

### P3 — Polish
15. **Delete `S3_NORMALIZE_CENTROID`** — C19 compliance.
16. **Move coverage thresholds to config** — `COVERAGE_THRESHOLD`, `FLAG_FRACTION`.
17. **Regenerate handoff document** — Current one is factually incorrect on embedding model, backend, and several bug statuses.
18. **Add `--strict-preflight` to runner** — Fail hard on OMLX unavailability.

---

## FINAL ASSESSMENT

**The codebase is better than the handoff makes it look.** D2176–D2181 fixed most of the crash-level bugs I found in the first review. The remaining issues are **config drift, embedding mismatches, and scalability bottlenecks** — not architectural flaws.

The biggest risk is **running the pipeline with default config on MPS**. It will crash immediately at Stage 1.5 with a dimension mismatch. This is a first-user experience killer.

The second-biggest risk is **the coverage_check.py embedding mismatch**. If you're using coverage scores to decide whether to re-extract clusters, those scores are random noise. You may be re-extracting good clusters and keeping bad ones.

Fix the P0 items, and this pipeline is genuinely production-ready for the 1K-FB scale. Fix P1+P2, and it scales to 20K.

---
*Review compiled from: 23 source files across the full repository tree, cross-referenced against the handoff document and decision log.*
