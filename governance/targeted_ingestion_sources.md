# Targeted Ingestion — Source Map for the 9 CRITICAL Disciplines

> Generated 2026-09-10 (D2607-D: targeted ingestion). Cross-references the 9 CRITICAL
> starved disciplines against `feed.opml` to determine which sources can supply the
> convergent content the fine 61-way head needs. **Finding: `feed.opml` covers NONE of
> them** — it is entirely ML-infrastructure / vector-search / agent-engineering focused.

## The 9 CRITICAL disciplines (convergent ≤ 3)

| # | Discipline | Golden | Convergent | Shortfall |
|---|---|---|---|---|
| 1 | design psychology | 4 | 1 | 19 |
| 2 | ecology | 4 | 1 | 19 |
| 3 | game design | 3 | 2 | 18 |
| 4 | generative design | 5 | 2 | 18 |
| 5 | computational theory | 6 | 2 | 18 |
| 6 | robotics | 4 | 3 | 17 |
| 7 | computational physics & simulation | 4 | 3 | 17 |
| 8 | color theory | 5 | 3 | 17 |
| 9 | creative coding | 5 | 3 | 17 |

## feed.opml coverage vs. required sources

`feed.opml` currently has: GitHub topic feeds (vector search / FAISS / RAG / MLX /
Apple Silicon / speculative decoding), MLX inference-engine links, model-eval tools,
FAISS alternatives, 3 YouTube channels, 1 X.com source, and a system monitor.

**Zero of these produce convergent FB content for the 9 CRITICAL disciplines** — they
are all about *running* the pipeline, not the *domain knowledge* the classifier needs.

## Recommended new sources (arXiv RSS, local-friendly, added to feed.opml)

arXiv RSS is the lowest-friction, sovereign (C3), machine-ingestible (S0) source
aligned to the ingestion procedure. Mapping:

| Discipline | arXiv category | RSS URL |
|---|---|---|
| robotics | cs.RO (Robotics) | `https://rss.arxiv.org/rss/cs.RO` |
| computational theory | cs.CC (Complexity) + cs.DS + cs.FL | `https://rss.arxiv.org/rss/cs.CC` |
| computational physics & simulation | physics.comp-ph (Comp. Physics) | `https://rss.arxiv.org/rss/physics.comp-ph` |
| generative design | cs.GR (Graphics) + cs.CE (Comp. Eng.) | `https://rss.arxiv.org/rss/cs.GR` |
| creative coding | cs.HC (HCI) + cs.GR | `https://rss.arxiv.org/rss/cs.HC` |
| color theory | cs.CV (Color constancy / vision) | `https://rss.arxiv.org/rss/cs.CV` |
| game design | cs.HC (game HCI) + cs.AI | `https://rss.arxiv.org/rss/cs.HC` |
| design psychology | cs.HC (design/psychology) | `https://rss.arxiv.org/rss/cs.HC` |
| ecology | q-bio.PE (Populations & Evolution) | `https://rss.arxiv.org/rss/q-bio.PE` |
| generative design (2nd) | cs.CE (Comp. Engineering) | `https://rss.arxiv.org/rss/cs.CE` |

## How to ingest (unchanged from targeted_ingestion_plan.md)

1. Pull new items from the feeds above into the input corpus.
2. Run the pipeline (S0 convert → S1 chunk → S1.5 cluster → S2 extract) over ONLY the new sources.
3. Mine the new convergent FBs via `scripts/mine_classifier_golden.py` (stratified: min 10/max 30 per discipline).
4. Re-run `scripts/train_hierarchical_classifier.py` + measure the fine-head macro-F1 lift.

> **Note:** several CRITICAL disciplines (design psychology, color theory, creative coding,
> game design) are *practitioner* fields — arXiv is a weaker signal than curated
> practitioner sources (game-design blogs, design-pattern archives, creative-coding
> ecosystems). arXiv is the sovereign/low-friction first tranche; practitioner sources
> are the second tranche once S0→S2 is proven on the feed.
