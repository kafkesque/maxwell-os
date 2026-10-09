# MARKET RESEARCH — 2026-10-06 — Knowledge-Layer Tool Stack Benchmark (re-log)

> **Status:** advisory (research-only). No pipeline wiring done. Supersedes nothing.
> **Provenance:** this record re-logs a prior-session assessment (`maxwell-knowledge-layer-tool-benchmark-2026-10-06`)
> whose original ephemeral output was never persisted to governance. It is now a governance artifact so the
> recommendation is not lost. Machine: Apple M1 Max (Apple7 GPU), 64 GB, Metal 4.

## 0. Scope

Selecting the acquisition/transcription/conversion/compilation/graph tooling for the two future lanes
(media/image embedding lane + real-time market-research scout lane), under the iron rules: $0 marginal cost
(C1), sovereign local compute (C3), no vendor lock-in (C2/C4), open formats.

## 1. Stack picks (verbatim intent, spelling normalized)

| Function | Pick | Note |
|---|---|---|
| **Acquire** | `yt-dlp` directly | Agent-reach only for X/Reddit, behind a flag. Cookie scraping = ToS risk, never default-on. |
| **Transcribe** | `mlx-whisper` | Apple Silicon MLX, MIT. Parakeet / WhisperX only after testing on Maxwell's own audio. |
| **Convert** | Docling + Pandoc | Avoid MinerU / Marker (heavier, more moving parts). |
| **Compile** | OpenKB as **read-only benchmark, not a dependency** | Copy its lint rules + Pratiyush/llmwiki's 4-factor confidence formula. None of the surveyed tools ingest video/social natively; none count independent scores. |
| **Graph** | Anytype stays the graph | LightRAG optional, as a **derived retrieval index over FBs** (never the source of truth). |
| **Convergence** | build in-house | — |

## 2. The two lanes (prototype targets, both in `scratch/` first)

- **S0 image patch (Docling) + `embeddinggemma-2` multimodal lane** — prototype in scratch.
- **Scout lane** — derived, **non-FB index** (does not mutate the FB ontology; a separate derived surface).
- **Embedding images/videos/links in FBs** — additive `media[]` + `source_locator` fields; never re-chunks or
  re-classifies existing FBs; does not change the axis ontology.

## 3. Dependencies on prior decisions

- Splash inference engine is **moot** for the current model roster (D-2768): model-scoped DFlash2 drafts only.
- Prism Ternary Bonsai 2 is **not** an S4/S2 candidate (D-2771).
- S4 classifier candidates (Mistral-Small-3.1-24B / Gemma-3-12b) remain **unswapped** pending the D-2767
  head-to-head fit eval (see `D2767_CB_CLASSIFICATION_RECOMMENDATION_20261009.md`).
