# MARKET RESEARCH — SOTA RAG / Knowledge-Layer Reference Case (2026-10-22)

> **Purpose:** a durable, citable reference set so Maxwell OS can be re-measured against the
> industry standard and best-available under-development solutions. This document is the
> ANCHOR for the 2026-10-22 scaffold audit (Question II); it is re-readable, not one-shot.
> **Citation discipline (D-3109):** every reference below was produced by a web search reading
> made on 2026-10-22 (DuckDuckGo `ddgs`); arXiv IDs / URLs / dates are cited. Nothing here is
> training-data prose — a claim without a cited reading is absent.
> **Scope layers:** (A) correctness/readiness metrics, (B) ingestion & extraction, (C) knowledge
> layer & retrieval, (D) agentic serving & skill orchestration. Each entry carries a
> **measurement hook** — the re-measurable reference point Maxwell is scored against.

---

## A. Correctness & Readiness Metrics (maps to the 3 "are we ready to test" questions)

| # | Reference | Defining contribution | Measurement hook (what Maxwell must show) |
|---|---|---|---|
| A1 | **ARES** — arXiv:2311.09476 (2023) | Automated RAG eval along context-relevance / answer-faithfulness / answer-relevance; judge calibrated against human labels rather than trusted blindly | Maxwell's judge (S5 NLI + LLM judge) is calibrated against a human anchor, not self-referential — already partially met by `judge_calibration` block in eval_integrity.yaml |
| A2 | **RAGChecker** (amazon-science) | Claim-level precision/recall that separates retriever error from generator error | A claim-level recall number: of the claims in the source, what fraction are captured as FBs? **Maxwell has NO semantic-recall golden today** → biggest gap |
| A3 | **RAGAS** | LLM-as-judge: faithfulness, answer relevance, context precision/recall | Faithfulness ≈ S5 NLI (exists). Context **recall** ≈ missing |
| A4 | **FaithJudge / ConsJudge** | Human-aligned hallucination leaderboards; judge training rather than assumption | Judge error-rate vs blind human (exists: content_type 0.353 / discipline 0.474 / extraction_type 0.283, eval_integrity) |
| A5 | **SemDeDup** — arXiv:2303.09540 (2023) | Embedding-based semantic dedup (pairs similar but not identical) | Dedup is semantic, not just exact SHA/FTS — Maxwell has SHA-256 + source_id + title/content dedup (config eval_integrity) but semantic near-dup at body level is partial |
| A6 | **Near-dup ingestion pipeline** (technologyonthe.net, 2026-10) | What to dedup, which technique catches which kind, threshold choice, keep citations consistent when collapsing | The 96 same-author echoes (audit_false_convergence, measured 2026-10-22) are exactly the class this reference targets |

## B. Ingestion & Extraction

| # | Reference | Defining contribution | Measurement hook |
|---|---|---|---|
| B1 | **Docling** (IBM) | Hybrid VLM + modular multi-model cascade for layout/table/reading-order | S0 already uses Docling (SOTA); keep |
| B2 | **MinerU** (OpenDataLab) | CJK / mixed-language / table-heavy PDFs (PaddleOCR) | If corpus gains CJK/technical PDFs, MinerU is the better S0 path (gap only if scope widens) |
| B3 | **Marker / Unstructured** | Fast markdown conversion; 1000+ page real-world benchmarks | S0 fallback (Pandoc) vs Marker for .md fidelity — worth a benchmark only |
| B4 | **Late Chunking** — Jina, arXiv:2409.04701 (2024) | Embed the whole doc, pool per-chunk spans AFTER full-document attention → chunks inherit cross-chunk context | Maxwell chunks S1 then embeds S1.5 (**early chunking**) → retrieval recall cost; late chunking / contextual retrieval is a SHOULD for S1.5 |
| B5 | **Contextual Retrieval** (Anthropic) | Prepend document context to each chunk before embedding | Same gap as B4 — cheaper than late chunking, pair it |

## C. Knowledge Layer & Retrieval

| # | Reference | Defining contribution | Measurement hook |
|---|---|---|---|
| C1 | **GraphRAG** (Microsoft) | Entity-centric KG + community/global summaries for thematic ("big picture") queries | Maxwell has graph **expansion** but not community/global summarization → thematic-question recall gap |
| C2 | **RAPTOR** | Hierarchical recursive summarization tree (abstractive) | Global-context alternative to C1; cheaper than full KG |
| C3 | **LightRAG** | Dual-level (entity + theme) retrieval; token/ latency-efficient vs GraphRAG | If Maxwell adds graph, LightRAG is the more sovereign-efficient reference (C1) |
| C4 | **"RAG vs GraphRAG" systematic eval** — arXiv:2502.11371 | Grounded evidence of WHEN graph beats flat RAG (not universal) | Gate any graph adoption on a measured delta, not fashion |
| C5 | **Hybrid BM25 + dense + RRF** | Lexical + semantic + reciprocal-rank fusion + rerank | Maxwell has FTS + vector + keyword + graph + rerank.py → **already hybrid**; verify RRF fusion + cross-encoder reranker is the live path |
| C6 | **Matryoshka** — arXiv:2205.13147 (2022) / **bge-m3** | Truncatable embeddings; multi-lingual + dense/sparse | Maxwell already uses bge-m3 512d Matryoshka → aligned, no gap |
| C7 | **Zep / Graphiti** | Temporal KG with **incremental** update (absorb new source without full rebuild) | Maxwell's re-anchor is a full re-run → incremental absorption is a known gap (register T-120 "ABSORPTION path") |

## D. Agentic Serving & Skill Orchestration

| # | Reference | Defining contribution | Measurement hook |
|---|---|---|---|
| D1 | **CRAG** — arXiv:2401.15884 (2024) | Retrieval evaluator grades docs (correct/incorrect/ambiguous) → corrective fallback | Maxwell's `retrieve-agentic` critique loop ≈ partial CRAG; the "grade-then-correct" step is a SHOULD. Web fallback conflicts with C22 sovereignty → opt-in only |
| D2 | **Self-RAG** — arXiv:2401.15884 family | Reflection tokens: grounding + usefulness self-check at generation | S5 NLI is a grounding check; a serve-time self-consistency (SelfCheckGPT-style) is a WORTH |
| D3 | **SelfCheckGPT** — arXiv:2303.08896 (2023) | Sampling-based black-box hallucination detection | WORTH: serve-time guard without external DB (sovereign) |
| D4 | **Vectara HHEM** | Factual-consistency NLI model (HHEM-2.1-Open open-sourced) | S5 DeBERTa-v3 NLI is the same class — benchmark S5 against HHEM-2.1-Open as a swap candidate only |
| D5 | **Claude Agent Skills / OpenAI Skills** | Filesystem skills with **progressive disclosure** (3-layer: metadata → SKILL.md → resources/scripts) | Maxwell exposes via MCP (C25) but has NO native skill registry/orchestrator → a SHOULD if "agent-agnostic skill serving" is the ambition |
| D6 | **Mem0 / Zep (memory layer)** | Session/ preference memory, temporal recall | Out of scope for a knowledge store, unless agent-session memory is in-scope (C22) |

---

## Audit verdict vs Maxwell scaffold (the gap map)

**Already at SOTA (no action):**
- Hybrid retrieval + reranking (C5, `retrieve-graph`/`rerank.py`)
- Matryoshka embeddings via bge-m3 (C6)
- Docling as S0 parser (B1)
- NLI fail-closed verification as the faithfulness rail (A3/D4 class)
- Human-anchored judge calibration + agreement floors (A1/A4)

**Partial (measured, needs closing):**
- Semantic dedup: 96 same-author echoes remain (A6 — measured 2026-10-22)
- Schema/provenance conformance: 455 hard gaps in non-principle types (stress_s2_exhaustive)
- Idempotency harness built + selftest green, but the real two-run `--all` has NOT been executed

**Gaps (blindspots, not yet built):**
1. **Semantic extraction recall** — no source→expected-FB golden, so "nothing lost" is unmeasurable (A2, RAGChecker). **Highest-leverage gap.**
2. **Late/contextual chunking** — early chunking loses cross-chunk context (B4/B5).
3. **Global/thematic retrieval** — no community/global summarization (C1/C2/C3).
4. **Incremental knowledge absorption** — re-anchor is full re-run (C7, T-120).
5. **Native skill registry** — MCP-exposed but no progressive-disclosure skill layer (D5).

**Not in scope / sovereign-tension (explicitly deferred):**
- CRAG web fallback, Mem0/Zep session memory, external judge swap (HHEM) — all gated by C22 local-first.

## How to re-measure Maxwell against this later
Each `measurement hook` column is a re-runnable check. The durable receipts: (1) run
`phase0_idempotency.py --all` for A-idempotency; (2) build the recall golden for A2; (3) run
`audit_false_convergence.py` + `stress_test_s2_exhaustive.py` after each pipeline change; (4)
bench S1.5 late-vs-early chunking on the retrieval golden (T-101).
