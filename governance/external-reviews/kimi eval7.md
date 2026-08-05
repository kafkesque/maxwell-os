I'll read the handoff document and examine the repository code rigorously. Let me start by fetching the repo structure and key files.
I now have a comprehensive view of the codebase. Let me compile the rigorous, pragmatic review.
Here's the rigorous, pragmatic constructive review. I've examined every code file in the repo against the handoff document and flagged crash-level bugs, architectural mismatches, and hidden failure modes.

---

## TL;DR — The Headlines

**Verdict: B+ architecture, A+ ambition, C+ execution hygiene.**

The cluster-before-extract architecture (R-NN → Louvain → convergent extraction) is the **correct call** for quality over quantity. The verification stack (NLI + cross-family LLM) is peer-grade. But the codebase carries **technical debt from rapid iteration** — several crash-level bugs, latent data-corruption risks, and architectural mismatches between documented intent and implemented reality.

### The Single Most Important Finding

**You're at ~400:1 compression (323K segments → ~800 FBs), not 291:1.** The 2,804 singletons are essentially unprocessed noise. This is either radical quality curation or catastrophic under-extraction. `coverage_check.py` flags clusters with >30% under-covered segments — the latter is a real risk.

---

## P0 — Crash-Level Bugs (Fix Before Next Run)

| # | Bug | Location | Impact |
|---|-----|----------|--------|
| 1 | **`_process_cluster` returns `list[dict]` for multi-principle clusters, but annotation says `dict \| None`.** The caller does `fb.get("_null")` — if `fb` is a list, this crashes with `AttributeError`. | `stage2_extract.py` | **Crash** |
| 2 | **`ensure_dirs()` references `S3_DIR`, which was removed in D2120.** Calling it raises `NameError`. | `pipeline_paths.py` | **Crash** |
| 3 | **`pipeline_paths.py` loads config at import time with an unclosed file handle.** Malformed YAML crashes the entire pipeline at import, not runtime. | `pipeline_paths.py` | **Crash** |
| 4 | **`_call_mlx_json` passes `repair_fn=` to `parse_json_robust`.** If that function doesn't accept that kwarg, the MLX backend crashes on JSON repair. | `omlx_call.py` | **Crash** |

---

## P1 — Architectural Mismatches

### 1. Inconsistent Embedding Models = Semantic Misalignment
- **S1.5 clustering:** `bge-small-en-v1.5` (384d) via `sentence-transformers` on MPS
- **Relationship edges (S4):** `bge-m3` (1024d) via Ollama HTTP
- **Coverage check:** `bge-small-en-v1.5` via `sentence-transformers` on MPS

These are **different semantic spaces**. A "semantic_near" edge at cos≥0.80 in 1024d space does NOT mean the same thing as R-NN at cos≥0.75 in 384d space. **Pick one model and use it everywhere.**

### 2. Singletons Are Architecturally Broken
2,804 singletons get the same extraction prompt as convergent clusters, just shorter. But singletons are singletons **because they're semantically unique** — they may contain the most novel principles in the corpus. The `is_summary` gate (designed for multi-source synthesis) will reject most of them.

**Fix:** Treat singletons as speculative candidates with a dedicated extraction strategy, bypass the summary gate, and flag for human review.

### 3. Content Type Routing Is Invisible
The routing taxonomy (principle / process_template / growth_edge / tool_instruction / process_instance) is sound, but the Stage 2 prompt only shows **principle** golden examples. The LLM defaults to "principle" for everything. That's why you have ~800 FBs and near-zero PTs/PIs/GEs/TIs.

**Fix:** Add golden examples for each content type, or move routing to Stage 4.

### 4. K-Means Split Misalignment
- **S1.5** uses `faiss.Kmeans` for large-cluster splitting
- **S2** uses `sklearn.KMeans` on MPS for probe-based splitting

Different algorithms, different random states, different geometries. The S2 probe is an admission that S1.5 clustering failed — **fix it at S1.5** and remove the S2 probe.

---

## P2 — Algorithmic Issues

### Reciprocity Underreported by 2×
```python
reciprocity = reciprocal_edges / total_edges  # Wrong
```
`total_edges` counts directed edges. Each reciprocal pair appears twice. The correct formula:
```python
reciprocity = (2 * reciprocal_edges) / total_edges
```

### MinHash Is Word-Level (Not Semantic)
```python
for word in text.lower().split():
    mh.update(word.encode("utf-8"))
```
Two principles saying the same thing with different words ("Value-First Demonstration" vs "Demonstrate Value Before Asking") will **not** be deduplicated. Use 3-gram MinHash or embedding-based dedup.

### NLI on CPU = Slow
ModernBERT and DeBERTa run on `device=-1` (CPU). For 800 FBs × ~8 passages = 6,400 inferences, this is painful. Auto-detect MPS.

---

## P3 — Data Integrity Risks

### Checkpoint Race Condition
Stage 2 writes the checkpoint JSONL and the segids file **separately**. Crash between them = 5 duplicate FBs on resume. Use a single atomic write or a WAL log.

### `classification_errors` Scope Bug
```python
if "classification_errors" not in dir():
    classification_errors = 0
classification_errors += 1
```
`dir()` returns **local** names. This creates a local variable that shadows the outer counter. The outer counter **never increments**. Use `nonlocal`.

---

## P4 — Missing Capabilities (Future Tax)

| Missing | Why It Hurts |
|---------|-------------|
| **Incremental book ingestion** | Adding 1 book costs O(total corpus). For 953 books, reprocessing is expensive. |
| **Cross-run dedup (D2067)** | Every run starts from scratch. No persistent principle index. |
| **Graph traversal for retrieval** | `related_fbs` edges exist but are never used for multi-hop queries. |
| **Feedback loop** | `usage_count`, `feedback_score` in schema but never incremented. |
| **Dynamic taxonomy** | `taxonomy_manager.py` exists but doesn't actually modify canonical labels. |

---

## Recommendations — Prioritized

### P0 (Fix Before Next Run)
1. Fix `_process_cluster` return type mismatch
2. Fix `ensure_dirs()` S3_DIR NameError
3. Fix config loading in `pipeline_paths.py` (use `with open()`)
4. Add JSON Schema validation to all LLM outputs

### P1 (Fix Before Scale)
5. **Unify embedding model** across all stages (bge-small OR bge-m3, not both)
6. Move all hardcoded thresholds to config
7. Implement incremental book ingestion
8. Auto-detect MPS/CUDA for NLI

### P2 (Architectural)
9. Redesign singleton extraction as speculative candidates
10. Add graph traversal for multi-hop retrieval
11. Implement cross-run persistent dedup
12. Add usage feedback loop
13. Expose Louvain resolution parameter

### P3 (Polish)
14. Fix reciprocity calculation
15. Purge all dead Stage 3 references (C19 compliance)
16. Add non-principle golden examples
17. Calibrate NLI threshold on validation set

---

## Final Word

**The architecture is sound. The implementation needs hardening.** You're one focused bug-fix pass away from a reliable v3.1. The biggest risk isn't the algorithms — it's the **inconsistent embedding models** and the **singleton waste**. Fix those two, and the pipeline becomes genuinely competitive with commercial RAG systems.

The full review with line-level citations and code snippets:

**[Maxwell OS v3.0 External Review](sandbox:///mnt/agents/output/maxwell_os_v3_review_2026-08-05.md)**