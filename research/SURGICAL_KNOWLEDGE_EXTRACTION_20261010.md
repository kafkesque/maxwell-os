# Surgical Targeted Knowledge Extraction — Landscape, Research & Tooling (2026-10-10)

**Purpose.** New Maxwell OS capability: extract knowledge *surgically*, on demand, for any targeted
research topic — from **books (local) AND internet (video, blog, social media feeds, news feeds)** —
so Maxwell can act as a stronger research / analysis / advisory system. This is a *query-triggered*
pipeline (opposite of the batch 8-stage FBS pipeline), but shares its provenance/sovereignty ethos.

**Hard constraints (from CONSTITUTION).** $0 marginal cost (C1), local-first + API opt-in (C22),
no vendor lock-in (C2/C4), crash-safe writes (C6), generator ≠ verifier (R5), provenance stamping (R14),
swappable infra (C21), hardware-adaptive (C24). Everything below is filtered through that lens.

---

## 1. Retrieval / RAG research frontier (peer-reviewed, adapt these)

| Paper / Method | What it does | Why Maxwell should care |
|---|---|---|
| **Self-RAG** (Asai et al. 2023, arXiv:2310.11511) | LLM decides *when* to retrieve, and self-critiques its own generations (reflection tokens) | Generator self-critique before committing; maps to existing S5 verify ethos |
| **Corrective RAG (CRAG)** (Yan et al. 2024, arXiv:2401.15884) | Lightweight *retrieval evaluator* scores retrieved-doc quality → triggers web-search fallback when local docs are weak; decompose-then-recompose | **Directly solves the FTS-lexical-mismatch problem**; adds confidence-gated web fallback |
| **GraphRAG** (Microsoft, Edge et al. 2024, arXiv:2404.16130) | LLM builds entity/relation KG, community detection → global + local summaries | Multi-hop "how does X relate to Y across the corpus" |
| **LazyGraphRAG** (Microsoft, late 2024) | Same KG quality at ~0.1% of indexing tokens (lazy expansion) | Fits $0 marginal-cost / local-hardware budget |
| **LightRAG** (2024, arXiv:2410.05779) | Graph + dual-level retrieval (low/high level), very cheap, no heavy training | Best local-first GraphRAG for a 64GB box |
| **HippoRAG** (NeurIPS 2024, arXiv:2405.14831) | Hippocampal-indexing-inspired: LLM + KG + Personalized PageRank; up to +20% on multi-hop QA; 10–30× cheaper than iterative IRCoT | **Multi-hop memory integration** without iterative search cost; pairs with sqlite-vec |
| **HyDE** (Gao et al. 2022, arXiv:2212.10496) | Generate hypothetical doc embedding → retrieve against it (closes query↔doc lexical gap) | Fixes the "Roland Barthes vs skill orchestration" lexical false-positive class |
| **RAPTOR** (2023, arXiv:2401.18059) | Recursive tree summarization for long-doc abstraction | Book-chapter → principle rollup (feeds existing FBS convergence) |
| **ColBERT / ColBERTv2** (2020/2022, arXiv:2004.12832) | Late-interaction multi-vector retrieval | Better precision than single-vector for long tail; runs local |
| **Anthropic Contextual Retrieval** (2024 blog) | Chunk + contextual-prefix embedding, + rerank + BM25 | Proven recipe to lift retrieval precision on books |

**Agentic decomposition:** ReAct (arXiv:2210.03629), Toolformer (arXiv:2302.04761) — the
decompose→act→observe loop that drives "surgical" multi-step research. Gorilla (tool-calling APIs).

## 2. Web / browser research agents (grounded)

- **STORM** (Stanford, 2024, arXiv:2402.14207): multi-perspective question generation → retrieval →
  outline → full report. Blueprint for "advisory research report" output.
- **gpt-researcher** (Tavily-backed, open source): autonomous research agent → sourced report; uses
  search + scrape + rerank. Best reference implementation of the end-to-end loop.
- **WebVoyager / WebArena / Mind2Web**: browser agents for interactive web — heavier than Maxwell needs,
  but reference for *when* live navigation is required vs. static fetch.
- Search backends (API, opt-in per C22): Tavily, Exa, Brave Search, Serper, SearXNG (self-host → $0).

## 3. Multimodal extraction — video / audio / image

- **ASR**: Whisper / faster-whisper / whisper.cpp (local, $0) for video/audio → transcript.
- **Video retrieval**: yt-dlp → transcript + frame sampling → CLIP/BLIP embeddings + scene segmentation;
  index (transcript chunks + keyframes) into a multimodal store.
- **Reference**: Video-RAG surveys (2024–2025); Twelve Labs / FrameDB are API/vendor options (avoid per C4);
  local path = whisper.cpp + CLIP via ONNX/MLX + sqlite-vec for both text and image vectors.

## 4. Social media / news feeds (streaming + freshness)

- Feed ingestion already exists: `feed.opml` (RSS/Atom). Extend to: NER + entity-linking, dedup,
  **temporal/recency scoring** (freshness decays), source-reliability tier, and **stance/fact-check**
  pass before any claim is promoted.
- Key idea: **two-speed store** — a *ephemeral* fast ring (news/social, high churn) vs the *canonical*
  FBS store (books, low churn). Never let ephemeral claims silently overwrite canonical principles (R-D410).

## 5. Tooling / repos to integrate (local-first, $0 marginal cost)

| Need | Tool (local/open) | Note |
|---|---|---|
| Vector store | **sqlite-vec** (already in use) | single-file, local, proven |
| Embeddings | **bge-m3** (already in use) | multilingual + Matryoshka dims |
| LLM orchestrator | LlamaIndex / LangChain / **Haystack** | pick one; LlamaIndex has best ingest/query-engine coverage |
| Programmatic optimization | **DSPy** (Stanford) | compile/optimize retrieval+generation prompts deterministically (temp=0.0 friendly) |
| Lightweight GraphRAG | **LightRAG** | cheapest graph RAG, local |
| Web extraction | Trafilatura, Newspaper4k, **Firecrawl** (self-host), Crawl4AI | article→clean MD; Trafilatura is pure-Python $0 |
| Reader | Jina Reader (API) vs self-host | opt-in |
| Video | yt-dlp + whisper.cpp | local |
| Rerank | bge-reranker-base / Cohere (API opt-in) | bge local |
| Memory | Mem0 / Letta | long-horizon agent memory |
| Research agent | gpt-researcher (reference) | adapt loop, swap Tavily→SearXNG local |

## 6. Pragmatic recommendation for Maxwell OS (fit + next steps)

Build a **Stage R ("surgical research") sub-pipeline**, query-triggered, reusing existing primitives:

1. **Decompose** the research question into sub-queries + perspectives (ReAct / STORM-style).
2. **Route sources**: (a) local canonical KB (`retrieve.py` hybrid + HyDE + LightRAG multi-hop) →
   (b) local books not-yet-indexed → (c) web search (SearXNG local / Tavily opt-in) → (d) feeds/news →
   (e) video (yt-dlp+whisper). Default (a)+(b) local; (c)–(e) explicit opt-in per C22.
3. **Extract** clean text (Trafilatura/Newspaper4k/whisper) → chunk → bge-m3 embed → sqlite-vec.
4. **Verify**: CRAG-style retrieval evaluator scores evidence quality; weak local evidence triggers
   web fallback; Self-RAG reflection before any claim is committed. Reuse DeBERTa NLI (S5) for claims.
5. **Stamp provenance** (R14) on every extracted fact: source URL/feed/video + timestamp + gen_model +
   pipeline_commit; keep ephemeral claims separate from canonical FBS.
6. **Write crash-safe** (C6), never delete (R-D410), owner-gate promotion into canonical store.

This directly closes the *"why only 4 usable principles"* failure mode: the fix is not "ingest more
books" (138 mission-relevant AI/agentic books are already ingested) — it is **correct classification +
correct verification + query-time source routing**. Stage R makes the "surgical, whenever needed"
capability first-class without re-running the batch pipeline.
