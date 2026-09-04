# MASTERPROMPT — Maxwell OS v3.0 Forensic Audit + Optimization Research

> **Hand this file, verbatim, to Claude (Anthropic) and ChatGPT (OpenAI) as a single self-contained brief.**
> Repo: `github.com/kafkesque/maxwell-os` (branch `main`). Do NOT re-derive state from memory — read the referenced files.

---

## 0. Persona & ground rules

You are a **senior RAG / systems / software / agentic engineer**. You are hired to audit a local-first knowledge-extraction pipeline and find what is suboptimal. Be pragmatic, not academic.

**Hard rules:**
- **Verify, don't assume.** Every claim must cite a file path, config key, or decision ID (`Dxxxx`). If a file contradicts a claim, the file wins.
- **Do not propose breaking changes without an explicit migration path.** This is a live production pipeline with ~450 tracked decisions.
- **Constraints you must respect** (from `CONSTITUTION.md`): `$0` marginal cost / all generation local (C1); sovereign, data+compute local (C3); no vendor lock-in (C2/C4); `temp=0.0` on all generation (R7); generator ≠ verifier, different model family (R5); every persistent object stamped `schema_version`/`gen_model`/`pipeline_commit` (R14); **no hardcoded values — config-first in `config/*.yaml`** (C12); crash-safe writes `tempfile → fsync → os.replace` (C6).
- **Priority order of goals:** (1) accuracy/quality of output, (2) cost saving, (3) speed. Never trade accuracy for speed.
- Be **SMART** in every recommendation: Specific, Measurable, Achievable, Relevant, Time-bound. Flag anything you *cannot verify* as UNVERIFIED rather than asserting it.

---

## 1. System overview (verified 2026-08-25)

Maxwell OS is an 8-stage local knowledge pipeline that turns EPUB/PDF books into a verified knowledge graph of "Foundation Blocks" (FBs).

**Pipeline stages** (see `pipeline/`):
| Stage | File | Function |
|---|---|---|
| S0 | `stage0_convert.py` | EPUB/PDF → Markdown (Pandoc/Docling) |
| S0.5 | `stage0_5_extract_metadata.py` | MD → author/title (LLM) |
| S1 | `stage1_chunk.py` | MD → segments + SHA-256 dedup |
| S1.3 | `stage1_3_prefilter.py` | regex pre-filter (D2080) |
| S1.5 | `stage1_5_embed_cluster.py` | FAISS cosine clustering + source diversity (cluster-before-extract) |
| S2 | `stage2_extract.py` | clusters → convergent FBs (Qwen3-Coder, R5) |
| S4 | `stage4_merge.py` | FBs → classified + formatted |
| S5 | `stage5_verify.py` | DeBERTa-v3-large NLI only (fail-closed, D2298) |
| S6 | `stage6_commit.py` | SQLite (sqlite-vec) + Parquet export |

**Model stack** (see `CONSTITUTION.md` §2 and `~/.omlx/model_settings.json`):
- **Generator (S2):** `Qwen3-Coder-30B-A3B-Instruct-MLX-4bit` via OMLX 0.6.2 — `model_type=qwen3_moe`, 128 experts / 8 active, vocab 151936.
- **Verifier (S4):** `gpt-oss-20b-MXFP4-Q8` via OMLX — `model_type=gpt_oss`, 20B MoE / 4 active, 24 layers, vocab 201088.
- **VerifierV2 (R5 cross-family):** `Phi-4-mini-instruct-8bit` (D2264).
- **Embeddings:** `bge-m3` (Ollama, 1024-dim).
- **NLI:** `MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli` (local, D2298).

**Ontology (D2323 — two orthogonal axes):**
- `content_type` = functional ROLE: `principle | process_template | process_instance | tool_instruction | growth_edge`.
- `extraction_type` = epistemic FORM: `causal_mechanism | descriptive_model | normative_heuristic | empirical_pattern`.
- **Convergent (multi-source) S2 emits `principle` only** (75/75 golden) — by design, form carried by `extraction_type`.
- **Single-source + singleton S2 emits any of the 5 roles** (multi-class).

**Governance (single source of truth):**
- `CONSTITUTION.md` — canonical rules.
- `DECISION-LOG.md` — append-only, newest-first, D2000–D2462.
- `config/decisions.yaml` — 448 decisions, auto-derived summary.
- `governance/buglog.md`, `governance/aggregated_remaining_tasks.md`, `governance/folder_protocol.md`, `governance/document_lifecycle.md`, `governance/decision_lifecycle.yaml`.

---

## 2. Recent revelations (last 2 sessions + current) — START FROM HERE

These are already-established findings. Do not re-litigate them; build on them.

1. **ETA was 3× under-estimated.** S2 singleton output is ~1,000 tokens/FB (3,983 serialized bytes), not ~300. Earlier "7.6h decode floor" used 300 → real floor ~25h. (See D2460.)
2. **oMLX cache is broken in this version.** Both `gdn_ssd_split_enabled` (paged-SSD) AND `hot_cache_only` (DRAM) thrash (`store_cache_main_dispatch` grows 1ms→300ms+). **Only `cache.enabled=false` (`--no-cache`) is safe.** This was lost once during the homebrew→GUI migration (D2455/D2456) and had to be re-applied (D2460).
3. **Golden few-shot is the dominant prefill cost.** The single-source golden (14 pos + 7 neg, ~24KB ≈ 6K tokens) is injected into EVERY S2 batch system prompt. With `--no-cache` it is re-prefilled ~1,525×. ~78% of each ~8.5K-token batch prompt. Reducing it = quality risk (deferred).
4. **MoE decode ceiling is structural.** Qwen3-Coder-30B decodes ~50 tok/s single / ~16 tok/s per-request under 3-way concurrency (128-expert sparse MoE serializes). Not a config issue. 6 workers degrade; 3 optimal.
5. **S2 singleton classification IS multi-class** (verified: 101 principle / 40 process_template / 34 tool_instruction / 1 process_instance in 176 FBs). "Default principle" applies to **convergent only** (D2323). S4 `_resolve_content_type` preserves explicit roles; does not override.
6. **S5 is principle-only by construction** (`load_stage4_fbs` reads `checkpoint.jsonl`, never the PT/PI/TI/GE sidecars). Non-principle types dead-end at S4. (D2458, BUG-165, "Path A".)
7. **S4 golden IS wired into prompts (D2454)** — `config/golden/stage4_golden.yaml` (7 examples, `meta.status: WIRED`) is injected via `pipeline/s4_golden.py` honoring `stage4.golden_inject_enabled: true`. (Prior "4 examples / not wired" note was pre-D2454 and is stale.)
8. **S4 is decode-bound**: gpt-oss-20b 20B MoE / 4 active experts, ~4-6h floor.
9. **oMLX speed levers already investigated** (see §6 exclusions): SpecPrefill (needs same-vocab draft, lossless in theory), dflash (needs trained draft — N/A), TurboQuant KV (conflicts with `--no-cache`), ANE prefill (kernels only for Qwen3.5/3.6/3.8, not `qwen3_moe`).
10. **BUG-175 fixed**: `author="string"` provenance contamination (Phi-4-mini hallucination) → sentinel validation + backfill (D2459).
11. **Single-source + singleton share the same golden** and are the same operation; they should be unified into ONE extractor (D2462, PLANNED — not yet implemented). Convergent stays separate.

---

## 3. Forensic audit — the mandate

Verify that the **inference stack**, the **pipeline**, the **configs**, and the **decisions** are all aligned. Hunt for: **gaps, conflicts, blindspots, mismatches, misalignments, hidden failures/errors, drift, contamination, leaks, bloat, future tax, and bottlenecks**.

### 3.1 Inference stack alignment
Audit `pipeline/omlx_call.py`, `pipeline/model_lazyload.py`, `pipeline/parallel.py`, and `~/.omlx/settings.json` + `~/.omlx/model_settings.json`. Check:
- Does the code's assumed model name/endpoint match what oMLX actually serves? Any hardcoded model strings violating C12?
- Is the `--no-cache` fix enforced in code, or does it rely on manual settings that the GUI can silently revert (as happened in D2460)?
- Are the delegate rules (`delegate_rules` in the agent loader: never `custom_deepseek`, never >1 heavy model concurrent) actually enforced in `tools/delegate_safe.py` (just delegate-check / delegate-fix — no preflight)?
- Is there a single source of truth for model routing, or are there competing decision trees (agent loader vs `pipeline/omlx_call.py` vs config)?

### 3.2 Pipeline + config + decision alignment
Cross-check `CONSTITUTION.md` ↔ `config/*.yaml` ↔ `pipeline/*.py` ↔ `DECISION-LOG.md` ↔ `config/decisions.yaml`:
- **Config drift:** every value the code reads must exist in YAML with a matching name. Find any magic numbers/strings still hardcoded in `pipeline/` (C12 violation).
- **Decision drift:** decisions in `DECISION-LOG.md` that are NOT in `config/decisions.yaml` (known example: D2461 is in the log but not the registry). List all such gaps.
- **Golden drift:** do the golden files (`config/golden/*.yaml`) match what the prompt-builders actually load? Are any examples silently dropped by `golden_*_max` caps (this already happened once — D2461, SS-POS-014)?
- **Schema drift:** do S2 output fields match what S4 consumes and what S6 commits? (R14 stamping, provenance fields, `content_type`/`extraction_type` enums.)
- **Stale artifacts:** S4/S5/S6 t11 outputs predate the latest S2 (BUG-165). Identify any other stage whose output is stale relative to its input.

### 3.3 Failure-mode sweep
For each stage, identify: silent error swallowing (C16: except clauses must log AND raise), missing checkpoint/resume, non-idempotent steps, unbounded memory/disk growth, race conditions under concurrency, and any place where a "success" verdict can be emitted without verification.

---

## 4. Improvement research (peer-reviewed / OSS better than current)

For each component below, determine whether a **better, existing, open-source** solution exists that is **compatible with Maxwell OS constraints** (macOS M-series, local, MLX/Ollama, $0). Only recommend if genuinely better AND verifiable.

- **Chunking (S1):** is the current SHA-256 dedup + segmenter optimal? Compare vs semantic chunking, recursive-structure-aware chunking, `langchain`/`LlamaIndex` splitters, `semchunk`, `chonkie`.
- **Clustering (S1.5):** current = FAISS cosine + cluster-before-extract. Compare vs HDBSCAN, UMAP+HDBSCAN, `sqlite-vec`, `usearch`, `qdrant` (local), BIRCH, and community-detection. Is cosine the right metric? Is the threshold config-driven?
- **Embeddings (S1.5):** `bge-m3` (1024-dim) — is there a better local embedding for book-length knowledge? (`bge-en-icl`, `gte-Qwen2`, `mxbai-embed-large`, `nomic-embed-text`.)
- **Extraction (S2):** is few-shot JSON-output prompting optimal? Compare vs constrained decoding (`xgrammar`/`outlines`/`guidance`, json schema), Pydantic-based structured output, and function-calling paths.
- **Verify (S5):** current = DeBERTa NLI only (D2298). Compare vs AlignScore, MiniCheck, RAGAS, LLM-as-judge, entailment-ratio scoring (this was flagged as D2440 — evaluate properly).
- **Commit (S6):** `sqlite-vec` + Parquet — is the schema optimal? Any vector-index alternative (`usearch`, `hnswlib`, `faiss` persistence)?

---

## 5. Market research per stage (S1.3, S1.5, S4–S5, S6)

For each stage, answer: **is the current solution fully optimized, or does a better existing solution exist** given Maxwell OS's configuration (M-series Mac, 64GB, MLX/Ollama local, bge-m3, DeBERTa) and requirements (sovereign, $0, R14 provenance, R5 cross-family)?

- **S1.3 pre-filter:** regex-only. Is there a cheap local classifier (fastText, SetFit, small transformer) that beats regex precision/recall without a GPU budget?
- **S1.5 clustering:** see §4. Specifically — does cluster-before-extract (D2094) hold up vs extract-then-cluster for this corpus?
- **S4–S5:** is a 20B MoE classifier + DeBERTa verifier the right pairing, or is there a leaner, equally-accurate local path?
- **S6:** is SQLite+Parquet the right persistence, or would a local graph/vector store (Neo4j, Qdrant, LanceDB) better serve downstream retrieval?

---

## 6. S2→S4 bottleneck — laser-focused

**EXCLUDE these (already investigated this session — do NOT re-research):**
- oMLX cache modes (`--no-cache` vs `hot_cache_only` vs SSD paging) → D2436/D2460.
- MoE decode ceiling / `max_workers` 3-vs-6 → D2459/D2460.
- Golden few-shot *reduction* (quality risk) → D2460.
- SpecPrefill / dflash / TurboQuant KV / ANE prefill / MTP → this session's oMLX 0.6.2 source audit.
- Engine swaps (Rapid-MLX, MTPLX, CIDER, mlx-serve) → `feed.opml` review this session.
- Dense-model swap (Qwen2.5-Coder-7B) → violates R5.
- gpt-oss-20b S4 decode-bound profiling → this session.

**FOCUS HERE — unexplored levers, rank by feasibility/quality-safety:**
1. **Prompt-level prefill reuse:** the golden is a fixed system prompt re-prefilled ~1,525×. Can the S2 code cache the golden's KV/prefix in-process (shared prefix across requests) without oMLX's broken cache? Is there an oMLX API for explicit prefix cache seeding?
2. **Batch construction:** how are 4-item batches assembled? Is there per-item redundant text (repeated instructions)? Can the system prompt be sent once and items as a continuation?
3. **Structured-output efficiency:** is the model emitting full JSON per item (bloated)? Would a compact schema (shorter keys, `xgrammar` constrained decoding) cut decode tokens without losing fields?
4. **S4 batching/concurrency:** same analysis for gpt-oss-20b (4 active experts, different optimal concurrency than 128-expert Qwen).
5. **Output-token reduction without quality loss:** which body fields are necessary vs derivable downstream (S4.5/D2345)?

Report each as feasible/viable/reliable + SMART, with a predicted % speedup and a quality-risk rating (none/low/high).

---

## 7. Cost reduction (DeepSeek price increased)

Maxwell OS is $0 local-first, but the model-routing decision tree has a cloud escalation path (DeepSeek V4 Pro, Step 5). DeepSeek's API price has increased. Research:
- Cheaper cloud alternatives for the *escalation-only* path (Qwen cloud, Groq, Together, Fireworks, OpenRouter, DeepInfra) — cost per 1M tokens for a ~30B-class model.
- Whether the escalation path is even necessary given local Qwen3-Coder-30B + gpt-oss-20b, or whether it can be retired entirely (pure local, C1/C3).
- Hybrid-sovereignty options (C22): local-first with explicit opt-in cloud, cheapest compliant provider.

---

## 8. Local-LLM delegation effectiveness (current bugs)

The operator delegates coding/research tasks to local LLMs via an agent harness. **Current known bugs to incorporate:**
- **DELEGATE-001:** `custom_deepseek` provider has a `reasoning_content` passthrough bug — never use it.
- **BUG-053:** `Phi-4-mini-instruct-8bit` hallucinates on open-ended research — only use it for summarization WITH source text.
- **Verified-working local models:** `gemma-4-E4B-it-MLX-4bit` (code review/summarize/classify), `Qwen3-Coder-30B-A3B-Instruct-MLX-4bit` (code gen). Memory budget ~24GB of 64GB for all models.
- **Concurrency:** never >1 heavy model concurrently; pipeline parallelism should use `pipeline/parallel.py` (subprocess), not delegates.

Research: how can tasks be delegated to local LLMs **more effectively** — optimal model→task routing given the bugs above, prompt patterns that avoid open-ended hallucination, and how to structure coding tasks so a small local model can complete them reliably (chunked diffs, explicit contracts, verify-loops).

---

## 9. Harness evaluation (goose vs PI vs DeepSeek vs coding harnesses)

Maxwell OS currently uses **goose** (this agent) for orchestration/delegation. The operator asks:
- Examine the **PI** harness and the **DeepSeek** harness (verify what these actually refer to — do not assume).
- Are there **better coding-agent harnesses than goose** — specifically better at **tool calling** and **local-LLM agentic orchestration**? Evaluate against: Aider, OpenHands (formerly OpenDevin), SWE-agent, Cline, Continue, and any others that are current as of your knowledge cutoff.
- Criteria: (a) local-LLM (MLX/Ollama) compatibility, (b) tool-calling reliability, (c) multi-step coding-task success rate, (d) cost (open-source, $0), (e) integration burden with an existing Python pipeline.
- Recommendation: can coding tasks be **outsourced** to a specialized harness while goose remains the pipeline orchestrator? What's the cleanest division of labor?

---

## 10. Dependency context (exact paths + keys — grep these, don't guess)

**Configs:**
- `config/pipeline_config.yaml` — `max_workers`, `golden_single_source_max`, `stage2.*`, `stage4.*`, `stage5.*`
- `config/content_types.yaml` — ontology (`content_types`, `extraction_types`, `route_to_content_type`, `s2_body_fields`)
- `config/filtering.yaml` — `code_markers`, prefilter rules
- `config/golden/stage2_fewshot_convergent.yaml` (322KB), `stage2_fewshot_single_source.yaml` (14+7), `stage4_golden.yaml` (4 examples)

**Pipeline code:**
- `pipeline/content_types.py` — ontology loader, `ROUTE_TO_CONTENT_TYPE`, `DEFAULT_CONTENT_TYPE="principle"`
- `pipeline/stage2_extract.py` — `process_singletons`, `run_stage2`, golden loaders, `--only-convergent/--only-single-source/--only-singletons`
- `pipeline/stage4_merge.py` — `_resolve_content_type` (D2128), `CRIBS_ENRICHMENT_SYSTEM`, prompt templates
- `pipeline/stage5_verify.py` — DeBERTa NLI (D2298)
- `pipeline/omlx_call.py`, `pipeline/model_lazyload.py`, `pipeline/parallel.py`, `pipeline/book_metadata.py` (`is_sentinel_author`)

**Inference:**
- `~/.omlx/settings.json` — `cache.enabled` (must be false), `hot_cache_only`, `gdn_ssd_split_enabled`
- `~/.omlx/model_settings.json` — `specprefill_enabled`, `turboquant_kv_enabled`, `qwen35_ane_prefill_enabled`, etc.

**Governance:**
- `CONSTITUTION.md`, `DECISION-LOG.md` (D2000–D2462), `config/decisions.yaml` (448), `governance/buglog.md`, `governance/aggregated_remaining_tasks.md`, `governance/s4_bottleneck_propositions.md`

**Key decisions to read first:** D2323 (ontology), D2128 (route→content_type), D2094 (cluster-before-extract), D2298 (DeBERTa-only), D2436+D2460 (cache), D2457 (TI-vs-PT), D2458 (E2E cohesion), D2459 (BUG-175), D2461 (golden drift), D2462 (single-source+singleton unification).

---

## Deliverable format

Return findings as a numbered list, each with: **[SEVERITY: critical/major/minor]** · **[CATEGORY: gap/conflict/blindspot/mismatch/misalignment/failure/drift/contamination/leak/bloat/future-tax/bottleneck/improvement]** · **file(s) + line/decision ID** · **one-line evidence** · **SMART recommendation with quality-risk rating**. End with a **prioritized action list** (top 10) ordered by impact on accuracy → cost → speed.
