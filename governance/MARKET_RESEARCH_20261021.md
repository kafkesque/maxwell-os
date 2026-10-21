# MARKET_RESEARCH_20261021 — Agentic RAG + retrieval (video audit + literature sweep)

Date: 2026-10-21. Source: Marfil Draws "Vector Databases Are Dead. Use This Instead"
(https://www.youtube.com/watch?v=qGZq19fykxU) + DuckDuckGo sweep of the agentic-RAG /
RAG-engineering literature (2025–2026).

## The video in one line
A vector-DB vendor (turbopuffer) announced it is demoting the vector index from the center of
its architecture to "one tool in a box" beside keyword search + filters. The video audits the
three proposed successors (agentic search, live MCP connectors, compiled markdown wiki) against
benchmarks and papers, and lands on: **the vector DB is NOT dead**; hybrid (BM25 + vector) +
rerank is the price/quality sweet spot; and the single highest-leverage change is **"put keyword
search in the agent's hands" — count the hops, then pick the tool.**

## Claims extracted (ALL vendor-adjacent; none reproduced locally → hypothesis until a receipt, D-3036)
- **Agentic search** — PipesHub "Frames" (824 Q / 12,441 Wikipedia articles): agent 92.7% vs best
  fixed pipeline 78.9% (oracle 93.0, memory-only 64.9). Gap widens on 5+-hop questions (pipeline
  62% vs agent 90%). Cost ~3x per question; median latency LOWER (22s vs 27s) but 1/20 tail 134s+
  vs 54s; 7% of questions need 5+ calls, eat 37% of spend, still 70% right.
- **BM25 beats vectors on internal corpora** — Enterprise RAG Bench (synthetic 500k-doc tech
  company, GPT-5.4 answering): BM25 68.8% vs vector 51.4%; even on 125 "semantic" Qs deliberately
  tilted toward vectors: 44.8% vs 32.8. Cause: embeddings trained on public text never saw internal
  acronyms / codenames / ticket IDs. ("A customer ID wants exact characters, not its soulmate.")
- **"BM25 wins at scale"** (Qwen3.6-27B reader): agent + BM25 tool = +14.4 pts over plain BM25 at
  ~1/9 the tokens of a raw-file agent → **an agent works ON TOP of ranked search, not in place of it.**
- **Compiled markdown "LLM wiki"** — build ~100x tokens, per-query ~21x tokens; never pays back
  (Cochran study). Its prior citation advantage was a 1,500-char scoring bug (corrected Oct 2).
- **Vectors still win** where meaning is vague (BrowseComp-Plus). pgvector <10M vectors = cheaper
  on Postgres than a separate system.

## Verdict against Maxwell OS (grounded reads: pipeline/retrieve.py, pipeline/rerank.py,
## config/pipeline_config.yaml — 2026-10-21)
- **ADAPT (already present — the video VALIDATES, no rip-and-replace).** `retrieve.py` already
  ships Keyword / FTS5 / Vector(sqlite-vec) / Hybrid(RRF, D2176) / Graph(BFS, D2205 P1) /
  Agentic(critique loop, D2205 P0); `rerank.py` = bge-reranker-v2-m3 (S2, gated OFF C28).
  This is the video's end-state; Maxwell is at/above the 2026 retrieval frontier.
- **The video's "exact characters vs soulmate" = D-3118 dual identity.** Lexical SHA-256 token key
  (Phase A, shipped) + embedding cosine divergence (Phase B, OPEN). Independent confirmation that
  BOTH are required and neither alone is sufficient. Phase B is elevated, not replaced.
- **REFERENCE (watch, no action):** ColBERT late-interaction (ColBERTv2/PLAID, ColPali/ColQwen) as a
  future higher-recall retrieval leg (30x storage → C28 opt-in). PipesHub Frames + Enterprise RAG
  Bench as candidate red-loop eval harnesses (would need local reproduction).
- **DEFER:** hop-count routing classifier (serving is secondary to the extraction pipeline today);
  live MCP connectors (irrelevant to sovereign local corpus); pgvector (sqlite-vec already in use).
- **CAUTION:** Cochran "wiki never pays back" confirms the convergent-FB store must stay a VERIFIED
  extraction OUTPUT (DeBERTa NLI gate) — never a precompiled retrieval substitute.

## Receipts
- Transcript: /tmp/vid_qGZq19fykxU.en.vtt (yt-dlp, 2026-10-21).
- Local reads: pipeline/retrieve.py (6 modes), pipeline/rerank.py (S2 gated C28),
  config/pipeline_config.yaml (method: vector, D-2724; rerank.present).


## Video 2 — Karpathy "99% Use AI & LLMs Wrong" (beamnxw, 2026-10-15, 2h) — CONFIRMATION ONLY, no new build
- **Not a RAG-technique video** (transcript: 0 hits for retrieval/embedding/vector). It is the LLM mental
  model: the model = a lossy "zip of the internet" (knowledge cutoff from pre-training) + a persona (post-training);
  the context window = working memory, directly accessible tokens.
- **The one RAG-relevant claim (REFERENCE-grade):** too many tokens in working memory DISTRACTS the model and
  DECREASES sampling accuracy. First-principles justification for Maxwell's convergent-FB store = VERIFIED
  extraction OUTPUT injected selectively — never a raw corpus dump. Same conclusion as the turbopuffer
  Cochran "wiki never pays back" caution.
- **Search / tool-use = "the most useful tool"** (~144 mentions). Independently confirms the already-shipped
  hybrid Keyword/FTS5/Vector/RRF + Agentic critique loop (retrieve.py). No new technique to adopt.
- **Vibe coding / agentic composer** — general agentic-IDE framing, not knowledge-pipeline-specific.
- **Verdict:** CONFIRMATION ONLY. ADAPT nothing (already present); REFERENCE the context-hygiene framing;
  DEFER nothing. Lower leverage than Video 1 (which carried concrete BM25-vs-vector benchmark numbers).
- Transcript: /tmp/vid_7YEHs2SMaVQ.en.vtt (yt-dlp, 2026-10-21).
