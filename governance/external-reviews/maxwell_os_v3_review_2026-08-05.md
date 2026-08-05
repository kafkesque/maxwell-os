# MAXWELL OS v3.0 — EXTERNAL RAG ENGINEER REVIEW
## Roundtable Handoff | 2026-08-05

---

## EXECUTIVE SUMMARY

**Verdict: B+ architecture with A+ ambition, C+ execution hygiene.**

The pipeline represents a genuinely sophisticated attempt at sovereign knowledge extraction. The cluster-before-extract architecture (D2120) is the correct call for quality over quantity. The verification stack (NLI + cross-family LLM) is peer-grade. However, the codebase carries significant technical debt from rapid iteration, latent data-corruption risks, and several architectural mismatches between documented intent and implemented reality.

**Critical finding: The pipeline has ~800 FBs from 323K segments. That's a 400:1 compression. The handoff worries about 291:1 — but the real number is worse because 2,804 singletons are largely unprocessed noise. This is either radical quality curation or catastrophic under-extraction. The coverage_check.py suggests the latter is a real risk.**

---

## 1. ARCHITECTURE & DESIGN

### 1.1 Cluster-Before-Extract: Correct but Fragile

**What's right:**
- R-NN + Louvain (D2168) fixes the transitive bridge effect. The mathematical reasoning in the code comments is sound.
- Source-diversity gating (>=2 canonical books) prevents echo-chamber extraction.
- The principle discovery gate (D2163) with Phi-4-mini probe + k-means split is clever and addresses the core risk of multi-principle clusters.

**What's wrong:**

**A) The 291:1 compression is too aggressive for heterogeneous corpora.**
- 953 books spanning design, business, systems thinking, AI, semiotics, and personal development. These domains have genuinely different vocabularies for similar concepts. FAISS at cos>=0.75 on 384d bge-small will NOT distinguish "visual hierarchy in graphic design" from "information architecture in UX" from "attention mechanisms in neural networks." All three are about "organizing information to guide attention" — but they are NOT the same principle.
- **Evidence:** The handoff admits "Under-extraction: MODERATE" risk. coverage_check.py flags clusters with >30% under-covered segments. If you're seeing flagged clusters, the compression IS destroying distinct principles.

**B) The singleton handling is architecturally broken.**
- 2,804 singletons (unclustered segments) are processed with the SAME extraction prompt as convergent clusters, just with `SINGLETON_SYSTEM` (shorter). But singletons are singletons BECAUSE they are semantically unique. They may contain the most novel principles in the corpus — the ones that appear in only one book because they're genuinely new ideas.
- **Current behavior:** Singletons get 1 segment, 2000-char truncation, no cross-source synthesis. The LLM has no context to determine if this is a principle or a passing example. The gate will reject most as "no extractable principle."
- **Recommendation:** Singletons need a DIFFERENT extraction strategy — not "extract principle from one passage" but "extract candidate principle and flag for human review." They should bypass the `is_summary` gate (which is designed for multi-source synthesis) and go straight to a "speculative" epistemic status.

**C) The k-means split in stage1_5 uses faiss.Kmeans, but stage2's split_cluster_by_kmeans uses sklearn.KMeans on MPS.**
- These are DIFFERENT algorithms with different initialization, convergence, and random state handling. A cluster split at S1.5 will not match a cluster split at S2. This creates misalignment: S1.5 says "this is one cluster" but S2's probe says "split it." The S2 split then operates on raw segments, not the S1.5 embeddings, so the geometry changes.
- **Fix:** Use the SAME embedding model and SAME clustering algorithm for both stages. Or better: do ALL splitting at S1.5 and remove the S2 probe entirely. The probe is an admission that S1.5 clustering failed — fix it at S1.5.

### 1.2 The Missing Stage: Relationship Graph Construction

**BUG-059 (embeddings.py missing) is marked OPEN.** The file now EXISTS (I read it), but:
- `compute_fb_relationships()` in stage4_merge.py calls `embed_texts_bge_m3()` from `pipeline.embeddings`, which NOW exists.
- BUT: `embed_texts_bge_m3()` uses Ollama HTTP endpoint with bge-m3 (1024d), while S1.5 uses sentence-transformers with bge-small (384d) on MPS.
- The relationship edges compute cosine similarity on 1024d embeddings, but the clusters were built on 384d embeddings. These are DIFFERENT semantic spaces. A "semantic_near" edge at cos>=0.80 in 1024d space does NOT mean the same thing as R-NN at cos>=0.75 in 384d space.
- **Risk:** False relationship edges. Two FBs may be "near" in bge-m3 space but genuinely unrelated in bge-small space (or vice versa).
- **Fix:** Use the SAME embedding model for clustering AND relationship edges. Either upgrade S1.5 to bge-m3 (cost: ~2x slower) or downgrade relationship edges to bge-small (cost: less discriminative but consistent).

### 1.3 Content Type Routing: Good Taxonomy, Weak Enforcement

The routing table (D2150) is sound:
- causal_mechanism -> principle
- empirical_pattern -> growth_edge
- normative_heuristic(method) -> process_template
- tool-specific -> tool_instruction
- case study -> process_instance

**But:** Stage 2's `SYSTEM_PROMPT` asks the LLM to classify `content_type` and `extraction_type`, but the prompt gives NO examples of the non-principle types. The golden few-shot only shows principles. The LLM will default to "principle" for everything because that's the only demonstrated output.
- **Evidence:** The handoff notes "19,438->6,500->~800 FBs" — but where are the PTs, PIs, GEs, TIs? If the routing worked, you'd have hundreds of non-principle objects. The fact that you have ~800 FBs suggests the routing is either not working or the LLM is defaulting to "principle" for everything.
- **Fix:** Add golden examples for EACH content type to the few-shot. Or remove the routing from Stage 2 and do it in Stage 4 (which already has the infrastructure for PT/PI/GE/TI separation).

---

## 2. CODE QUALITY & ENGINEERING

### 2.1 C12 (No Hardcoding): VIOLATED IN CRITICAL PATHS

The CONSTITUTION makes C12 a hard rule. But:

**A) `pipeline_paths.py` loads config at MODULE IMPORT TIME:**
```python
_CFG = yaml.safe_load(open(Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"))
```
- This runs when the module is imported. If the YAML is malformed, the entire pipeline crashes at import time, not at runtime.
- The file handle is never explicitly closed (relying on GC).
- **Fix:** Lazy-load config in a function, or use `with open(...)` context manager.

**B) `S3_NORMALIZE_CENTROID = True` in pipeline_paths.py (line ~170):**
- Stage 3 was REMOVED in D2120. This constant is DEAD CODE. But it's still there, confusing future maintainers.
- **Fix:** Delete it. C19 says "No dead code."

**C) `ensure_dirs()` references `S3_DIR`:**
```python
def ensure_dirs():
    for d in [S0_DIR,S1_DIR,S13_DIR,S15_DIR,S2_DIR,S3_DIR,S4_DIR,S5_DIR,S6_DIR,ARCHIVE_DIR,BOOKS_DIR]:
```
- `S3_DIR` is referenced but was removed from the module-level definitions. This will raise NameError if `ensure_dirs()` is ever called.
- **Fix:** Remove S3_DIR from the list.

**D) `stage2_extract.py` has hardcoded constants not in config:**
```python
MAX_CLUSTER_SAMPLES: int = 15  # Not in pipeline_config.yaml
SPLIT_PROBE_MIN_SIZE: int = 20  # Hardcoded, not config-driven
SPLIT_PROBE_MAX_COHESION: float = 0.85  # Hardcoded
SPLIT_KMEANS_RANDOM_STATE: int = 42  # Hardcoded
```
- These are critical tuning parameters. They should be in config.

**E) `coverage_check.py` hardcodes COVERAGE_THRESHOLD and FLAG_FRACTION:**
```python
COVERAGE_THRESHOLD = 0.50
FLAG_FRACTION = 0.30
```
- Not in config. Not overridable via CLI (only --threshold is, but not --flag-fraction).

### 2.2 Error Handling: Inconsistent Fail-Closed vs Fail-Open

The pipeline CLAIMS "fail-closed" (D2093) but IMPLEMENTS mixed semantics:

**A) Stage 5 NLI check returns `passed=True` for NEUTRAL results:**
```python
elif nli_entail_score >= 0.5:  # Mixed/neutral
    passed = True
    nli_score = 0.4  # Below 0.5 threshold -> triggers LLM escalation
```
- `passed=True` but `nli_score=0.4`. The caller sees "passed" but the score triggers escalation. This is confusing.
- **Fix:** Return `passed=None` or `passed="MARGINAL"` for neutral. Don't conflate boolean pass/fail with score-based escalation.

**B) Stage 2 `_process_cluster` returns different types:**
```python
def _process_cluster(cluster: dict) -> dict | None:
    # ...
    if len(principles) > 1:
        fbs = []
        for principle in principles:
            fb = _build_fb_from_result(principle, cluster, evidence_passages, cid)
            if fb:
                fbs.append(fb)
        return fbs if fbs else None  # Returns LIST, not dict!
    return _build_fb_from_result(principles[0], cluster, evidence_passages, cid)
```
- The return type annotation says `dict | None`, but it returns `list[dict] | None` for multi-principle clusters.
- The caller in the ThreadPoolExecutor loop does `fb = future.result()` and then checks `fb.get("_null")`. If `fb` is a list, this will crash with AttributeError.
- **Fix:** Unify the return type. Either always return a list (even for single FBs) or handle the list case in the caller.

**C) `omlx_call.py` has a bug in `_call_mlx_json`:**
```python
def _call_mlx_json(prompt, model, system, max_tokens):
    raw = _call_mlx(prompt, model, system, max_tokens)
    return parse_json_robust(raw, repair_fn=repair_json)
```
- But `parse_json_robust` signature may not accept `repair_fn` as a keyword arg (depends on json_repair.py implementation, which I can't see). If it doesn't, this crashes.

### 2.3 Type Safety: Annotations Exist, But Are Often Wrong

**A) `stage2_extract.py` — `_build_fb_from_result` references undefined variables:**
```python
def _build_fb_from_result(result, cluster, evidence_passages, cid):
    # ...
    book_count = cluster.get("source_diversity", ...)
    is_conv = cluster.get("is_convergent", False)
```
- `_build_fb_from_result` is a nested function inside `run_stage2`, but it's defined AFTER `_process_cluster` which calls it. In Python, this works due to closure scoping, but `is_conv` and `book_count` are NOT parameters — they're captured from the enclosing scope. This is fragile and confusing.
- **Fix:** Pass `is_conv` and `book_count` as explicit parameters.

**B) `stage4_merge.py` — `classification_errors` variable scope bug:**
```python
if "classification_errors" not in dir():
    classification_errors = 0
classification_errors += 1
```
- This is a hack. `classification_errors` is defined in the enclosing scope of `run_stage4`. The `if "classification_errors" not in dir():` check is trying to handle the case where the exception path doesn't have access to the variable. But `dir()` without arguments returns local names — this is checking if `classification_errors` is a LOCAL, not if it exists in the enclosing scope. If it doesn't exist locally, it creates a LOCAL that shadows the outer one. The outer counter never increments.
- **Fix:** Declare `classification_errors` as `nonlocal` inside the loop, or restructure to avoid nested scopes.

---

## 3. ALGORITHMIC CORRECTNESS

### 3.1 FAISS R-NN + Louvain: Mathematically Sound, Practically Questionable

**The algorithm is correct:** R-NN edges + Louvain community detection avoids transitive chaining. The implementation in `stage1_5_embed_cluster.py` is clean.

**But there are issues:**

**A) `faiss.Kmeans` for large cluster splitting uses `niter=20` and `seed=42`:**
- FAISS k-means is NOT deterministic across different FAISS versions or platforms, even with the same seed, because it uses OpenMP parallelism with non-deterministic reduction order.
- **Risk:** Re-running S1.5 on the same data may produce different clusters. This breaks reproducibility (R14).
- **Fix:** Set `niter=20` is fine, but document that exact cluster membership may vary. Or use sklearn KMeans with `algorithm="lloyd"` (deterministic) instead of FAISS k-means.

**B) Louvain resolution parameter is not exposed:**
- `networkx.algorithms.community.louvain_communities` defaults to `resolution=1.0`. This controls granularity. Higher resolution = more communities (smaller clusters). For a 953-book corpus with diverse domains, `resolution=1.0` may be too coarse.
- **Fix:** Make resolution configurable. Test values between 0.5 (fewer, larger clusters) and 2.0 (more, smaller clusters).

**C) The reciprocity calculation is wrong:**
```python
for i in range(n):
    for j in neighbor_sets[i]:
        total_edges += 1
        if i in neighbor_sets[j] and i < j:
            G.add_edge(i, j)
            reciprocal_edges += 1
```
- `total_edges` counts ALL directed edges (including self-loops? No, j != i is guaranteed). But reciprocity should be `reciprocal_edges / (total_edges / 2)` because each reciprocal pair is counted twice in `total_edges` (once as i->j, once as j->i).
- Current: `reciprocity = reciprocal_edges / total_edges`. This underreports reciprocity by 2x.
- **Fix:** `reciprocity = (2 * reciprocal_edges) / total_edges` for undirected reciprocity rate.

### 3.2 MinHash Deduplication: Word-Level, Not Semantic

```python
def make_minhash(text, num_perm=S2_MINHASH_NUM_PERM):
    mh = MinHash(num_perm=num_perm)
    for word in text.lower().split():
        mh.update(word.encode("utf-8"))
    return mh
```
- This is a WORD-level MinHash. Two principles that say the same thing with different words will NOT be detected as duplicates.
- Example: "Value-First Demonstration" vs "Demonstrate Value Before Asking" — same principle, different wording. Word-level MinHash will miss this.
- **Fix:** Use sentence-transformer embeddings for semantic dedup, or at least 3-gram MinHash. Word-level is too coarse for principle deduplication.

### 3.3 NLI Verification: Directionally Correct, But Fragile

**A) NLI models are loaded on CPU (`device=-1`):**
- ModernBERT and DeBERTa are running on CPU. For 800 FBs x 8 passages = 6,400 NLI inferences, this is slow.
- MPS (Apple Silicon GPU) is available and would be 5-10x faster.
- **Fix:** Auto-detect MPS/CUDA and use GPU if available.

**B) The NLI prompt format may be wrong for some models:**
```python
result = nli({"text": source, "text_pair": claim})
```
- Different NLI models expect different input formats. `tasksource/ModernBERT-base-nli` was trained on MNLI format: `premise` + `hypothesis`. The `text` + `text_pair` format is a HuggingFace pipeline convention, but some models expect explicit `premise`/`hypothesis` keys.
- **Fix:** Verify ModernBERT's expected input format. The pipeline abstraction may not handle all models correctly.

**C) NLI threshold of 0.6 for entailment is low:**
- MNLI models often assign high scores to neutral pairs. 0.6 may produce false positives.
- **Recommendation:** Increase to 0.75 or use a calibrated threshold based on a held-out validation set.

---

## 4. DATA INTEGRITY & SAFETY

### 4.1 The Resume/Checkpoint System Has a Race Condition

```python
# In stage2_extract.py:
if completed % 5 == 0:
    safe_write(STAGE2_CHECKPOINT, ...)
    # Atomic segids
    segids_tmp = tempfile.NamedTemporaryFile(...)
    try:
        json.dump(list(processed_ids), segids_tmp)
        segids_tmp.flush()
        os.fsync(segids_tmp.fileno())
        segids_tmp.close()
        os.replace(segids_tmp.name, segids_file)
    except Exception:
        if os.path.exists(segids_tmp.name):
            os.unlink(segids_tmp.name)
```
- The checkpoint and segids file are written SEPARATELY. If the process crashes between `safe_write` and `os.replace`, the checkpoint will have 5 more FBs than the segids file knows about. On resume, those 5 FBs will be re-extracted, causing duplicates.
- **Fix:** Write BOTH files atomically in a single transaction. Or better: include processed_ids IN the checkpoint file itself (as a header or separate JSONL stream).

### 4.2 `safe_write` in `io_guard.py` (not shown, but implied):**
- The pattern `tempfile -> fsync -> os.replace` is correct for single files. But Maxwell writes MANY interdependent files (checkpoint, segids, metadata). There's no atomicity across files.
- **Risk:** Inconsistent state after crash.
- **Fix:** Use a SQLite database or a WAL log for checkpoint state, not multiple files.

### 4.3 Version Gate (D2176) Has a Circular Dependency Risk

```python
def _check_version_consistency():
    version_yaml_path = Path("config/version.yaml")
    pipeline_config_path = Path("config/pipeline_config.yaml")
```
- These paths are hardcoded relative to CWD. If the pipeline is run from a different directory, the files won't be found and the gate is silently skipped.
- **Fix:** Use `PROJECT_ROOT / "config/version.yaml"`.

### 4.4 The `book_metadata.py` Module Is a Black Box

`stage2_extract.py` imports from `pipeline.book_metadata`:
```python
from pipeline.book_metadata import resolve_source_ids, build_citation, resolve_book_metadata, select_primary_source
```
- I couldn't read this file. But the logic for "canonical source identity" (SHA-256 of author|title) is critical for BORP correctness.
- **Risk:** If two different editions of the same book have different titles (e.g., "The Design of Everyday Things" vs "The Design of Everyday Things: Revised Edition"), they will be treated as different sources. This INFLATES source diversity falsely.
- **Recommendation:** Normalize titles (remove subtitles, edition info) before hashing.

---

## 5. PERFORMANCE & SCALABILITY

### 5.1 Embedding is the Bottleneck

- S1.5: 323K segments x 384d = ~500MB of embeddings. FAISS IndexFlatIP is exact search — O(n^2) memory for the full distance matrix in the worst case, but FAISS uses optimized BLAS. Should be fine.
- However, `faiss.IndexFlatIP` on 323K vectors with k=50 means 323K x 50 = 16M distance computations. Each is a dot product of 384-dim vectors. On CPU this is ~1-2 seconds. On MPS it's faster. The handoff says cluster time is fast.
- **Real bottleneck:** `sentence_transformers` encoding at 45 seg/s = 323K / 45 = ~2 hours. The handoff notes BUG-056: docs say "~5 min" but reality is 106 min. This is a 20x documentation error.
- **Fix:** Use batch_size=256 or 512 instead of 128. MPS can handle larger batches. Or use ONNX Runtime for sentence-transformers (2-3x speedup).

### 5.2 Stage 2 Parallelism is Limited

- ThreadPoolExecutor(3) with 3 workers. Each LLM call takes ~4-9 seconds. So throughput is ~0.33 calls/s per worker x 3 = 1 call/s.
- For 1,110 clusters: 1,110 / 1 = ~18 minutes. But with retries, failures, and multi-principle clusters, it's probably 30-45 minutes.
- **But:** The OMLX server may be the real bottleneck. If it's single-threaded, 3 parallel workers may not help.
- **Fix:** Measure OMLX throughput. If it's <3 concurrent requests, reduce workers to match. If it's higher, increase workers.

### 5.3 Stage 4 Relationship Edges Are O(n^2)

```python
for i in range(n):
    for j in range(i + 1, n):
        # ...
```
- For 800 FBs, this is 800x799/2 = 319,600 comparisons. With embedding computation, this is fine.
- But if FB count grows to 10,000 (the original target), this is 50M comparisons. Still manageable in Python with numpy, but getting slow.
- **Fix:** Use FAISS for approximate nearest neighbors instead of brute-force O(n^2).

---

## 6. MISSING CAPABILITIES & FUTURE TAX

### 6.1 No Cross-Run Deduplication (D2067 Mentioned But Not Implemented)

The handoff mentions "Cross-run incremental extraction — persistent principle index + LSH dedup across runs" (D2067). But I see NO evidence of this in the code:
- No persistent principle index.
- No cross-run LSH.
- Each run starts from scratch.
- **Future tax:** Every full re-run re-extracts from 323K segments. With 953 books, this is expensive. If you add 50 new books, you shouldn't re-process the old 903.

### 6.2 No Graph Overlay for Multi-Hop Retrieval

The handoff asks: "Are there any pipeline stages missing? (Graph overlay? Relationship edges? Multi-hop retrieval?)"
- Relationship edges exist (domain_overlap, discipline_overlap, source_crossover, semantic_near).
- But there's NO graph traversal for retrieval. The edges are stored in `related_fbs` but never used for multi-hop reasoning.
- **Future tax:** When you query "What principles about visual hierarchy are corroborated by Tufte AND supported by cognitive science?" — you need graph traversal. Currently, you'd need manual joins.

### 6.3 No Feedback Loop

The schema has `usage_count`, `feedback_score`, `feedback_count` — but I see NO code that increments these. The pipeline is write-once, read-many with no learning from usage.
- **Future tax:** As the corpus grows, the most useful FBs won't be distinguished from the least useful.

### 6.4 No Incremental Book Ingestion

If you add 1 new book:
1. Re-chunk ALL books (S1)
2. Re-embed ALL segments (S1.5)
3. Re-cluster ALL segments (S1.5)
4. Re-extract from ALL clusters (S2)
5. Re-classify ALL FBs (S4)
6. Re-verify ALL FBs (S5)
7. Re-commit ALL FBs (S6)

This is O(total corpus) per new book. For 953 books, adding 1 more costs the same as processing 954.
- **Fix:** Implement incremental clustering. New segments only need to be added to the FAISS index and checked for R-NN edges. Existing clusters don't change unless a new segment joins them.

### 6.5 The Taxonomy is Static

D2066 mentions "dynamic canonical taxonomy — raw labels dethrone canonical when outnumbered." But `taxonomy_manager.py` is only called in Stage 6 post-commit. There's no evidence it actually modifies the canonical taxonomy.
- **Risk:** The taxonomy drifts from the actual content. New domains (e.g., "agentic AI") won't be added unless manually curated.

---

## 7. SECURITY & OPERATIONAL RISKS

### 7.1 OMLX Single Point of Failure

The handoff flags this as HIGH severity. All LLM calls go through one OMLX server on localhost:8079 (or 11435 per config). If it crashes:
- Stage 2 halts.
- Stage 4 halts.
- Stage 5 deep check halts.
- **Mitigation:** The watchdog exists but doesn't provide redundancy. Consider running TWO OMLX instances on different ports with a simple round-robin fallback.

### 7.2 API Key is Hardcoded in Config

```yaml
omlx:
  api_key: sk-maxwell-local
```
- This is fine for local-only, but if OMLX ever exposes to LAN, this is a security risk.
- **Fix:** Load from environment variable with config fallback.

### 7.3 No Input Sanitization on LLM Outputs

The pipeline parses JSON from LLM outputs and directly uses it:
```python
result = call_omlx_json(prompt, ...)
name = result.get("name", "")
```
- If the LLM returns malicious JSON (unlikely with local models, but possible with prompt injection from book content), this could crash the pipeline or corrupt data.
- **Fix:** JSON Schema validation before using LLM output. Pydantic models exist in the codebase (schemas.py) — use them.

---

## 8. SPECIFIC FILE-BY-FILE ISSUES

| File | Issue | Severity |
|------|-------|----------|
| `pipeline_paths.py` | `S3_DIR` referenced in `ensure_dirs()` but undefined | HIGH (crash) |
| `pipeline_paths.py` | Config loaded at import time, file handle not closed | MEDIUM |
| `pipeline_paths.py` | `S3_NORMALIZE_CENTROID` dead code | LOW |
| `stage2_extract.py` | `_process_cluster` returns `list` vs `dict` type mismatch | HIGH (crash) |
| `stage2_extract.py` | `_build_fb_from_result` captures `is_conv` from outer scope | MEDIUM |
| `stage2_extract.py` | Hardcoded probe thresholds (20, 0.85) | MEDIUM |
| `stage2_extract.py` | Multi-principle return not handled in caller loop | HIGH (crash) |
| `stage1_5_embed_cluster.py` | Reciprocity calculation underreports by 2x | LOW |
| `stage1_5_embed_cluster.py` | FAISS k-means non-deterministic across runs | MEDIUM |
| `stage4_merge.py` | `classification_errors` scope bug with `dir()` | MEDIUM |
| `stage4_merge.py` | `compute_fb_relationships` uses different embed model than S1.5 | MEDIUM |
| `stage5_verify.py` | NLI models on CPU instead of MPS | MEDIUM |
| `stage5_verify.py` | NLI threshold 0.6 may be too permissive | LOW |
| `stage6_commit.py` | `s3_original_domain` column added via migration — dead code | LOW |
| `embeddings.py` | Uses Ollama HTTP, not MPS — inconsistent with S1.5 | MEDIUM |
| `coverage_check.py` | Hardcoded thresholds, no config integration | LOW |
| `omlx_call.py` | `_call_mlx_json` may pass invalid kwarg to `parse_json_robust` | MEDIUM |
| `runner.py` | Preflight check warns but continues on failure | LOW |

---

## 9. RECOMMENDATIONS (PRIORITIZED)

### P0 — Fix Before Next Run
1. **Fix `_process_cluster` return type** — unify to always return `dict | None`, or handle list in caller.
2. **Fix `ensure_dirs()` S3_DIR NameError** — remove dead reference.
3. **Fix `pipeline_paths.py` config loading** — use `with open()` and lazy loading.
4. **Add JSON Schema validation** to all LLM outputs before using them.

### P1 — Fix Before Scale
5. **Use consistent embedding model** across S1.5, relationship edges, and coverage check. Either all bge-small (384d) or all bge-m3 (1024d).
6. **Move all hardcoded thresholds to config** — probe sizes, MinHash params, NLI thresholds, coverage thresholds.
7. **Implement incremental book ingestion** — don't re-process the entire corpus for one new book.
8. **Fix NLI device selection** — auto-detect MPS/CUDA.

### P2 — Architectural Improvements
9. **Redesign singleton extraction** — treat as speculative candidates, not failed principles.
10. **Add graph traversal for retrieval** — use `related_fbs` for multi-hop queries.
11. **Implement cross-run dedup** (D2067) — persistent LSH index.
12. **Add feedback loop** — track usage_count and feedback_score in retrieval layer.
13. **Expose Louvain resolution parameter** — tune for corpus diversity.

### P3 — Quality of Life
14. **Fix reciprocity calculation** — correct the 2x underreport.
15. **Remove all dead Stage 3 references** — C19 compliance.
16. **Add golden examples for non-principle content types** — fix routing.
17. **Calibrate NLI threshold** — use validation set, not default 0.6.

---

## 10. FINAL ASSESSMENT

**Strengths:**
- The cluster-before-extract architecture is the right choice for quality.
- R-NN + Louvain is a mathematically sound clustering approach.
- Cross-family verification (Qwen -> Phi -> Gemma) is rigorous.
- The config-first philosophy (C12) is mostly adhered to.
- Source diversity gating prevents echo-chamber effects.

**Weaknesses:**
- The 400:1 compression ratio is aggressive. Coverage gaps are real.
- Singleton handling wastes 2,804 potentially unique principles.
- Inconsistent embedding models create semantic misalignment.
- Several crash-level bugs exist in the current code (type mismatches, NameError).
- No incremental processing — every run is full reprocessing.
- The taxonomy and classification system is under-tested (7 golden examples for 953 books).

**Overall:** This is a solid v3.0 that needs a v3.1 focused on **robustness, consistency, and incremental processing** before scaling to the full 20K FB target. The architecture is sound; the implementation needs hardening.

---
*Review compiled from: CONSTITUTION.md, runner.py, stage1_5_embed_cluster.py, stage2_extract.py, stage4_merge.py, stage5_verify.py, stage6_commit.py, pipeline_paths.py, omlx_call.py, embeddings.py, coverage_check.py, pipeline_config.yaml*
