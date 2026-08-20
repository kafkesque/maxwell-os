# Session Handoff — 2026-08-20 (P0 + smoke/stress + MTP research + object-type showcase)

> **State:** P0 committed. Smoke-plumbing + stress PASS. Object-type showcase run on the
> production generator. Full S2 `--reprocess-gated` on t11 is the next blocking step.

## Committed this session
- **`4d7c9cf`** — P0/P1-5: discipline aliases (30) + promotions (4) → `config/taxonomy_v5.yaml`;
  `max_disciplines 71→75` in `config/pipeline_config.yaml`.
  - 30 raw→canonical discipline aliases (psychology/linguistics/marketing/economics/…).
  - 4 new canonical disciplines: `design thinking`, `product design`, `industrial design`, `information retrieval`
    (none collide with domains → D2422 disjointness holds).
  - Verified: 60/60 tests, disjointness 2/2, config-audit clean, golden hash unchanged.

## Research verdicts (verified — do NOT re-investigate)
- **MTP is NOT a speed lever on M1 Max.** MTPLX (native MTP speculative decoding) requires **M5 TensorOps**;
  M1 Max benefit minimal/none. Sources: `governance/SENIOR-DEV-VERDICT-2026-08-09.md`,
  `governance/NOT-YET-EVALUATED-RESEARCH.md` (feed.opml eval). mlx-lm v0.31.3 has generic speculative-decoding
  support (v0.31.2 fixed its output corruption), but that is draft-model speculative decoding, deferred in favor of OMLX.
- **No official `Qwen3.8-35B`.** The "35B-A3B" MoE family = `Qwen3.5-35B-A3B` / `Qwen3.6-35B-A3B` (3B active, same
  speed class as current). `Qwen3.8-27B` is **DENSE** (`qwen3_5` arch, ~12-18 tok/s) → slower than current
  `Qwen3-Coder-30B-A3B` (3B-active MoE). Only "Qwen3.8-35B" is an abliterated community distill (reject).
- **Generator stays `Qwen3-Coder-30B-A3B`** (coder-specialized for strict-JSON S2; cross-family R5 preserved).

## Validation this session
- `smoke-plumbing`: PASS (S0→S1.5 clean, 287 unique hashes, 0 dup, 0 fail).
- `stress`: ALL_PASS (config integrity, memory 13.9GB free, OMLX chat up to 5K chars, embeddings 35.3 seg/s @512d,
  FAISS, SQLite FTS5).
- `tools/sync_decisions.py`: fully synced (no new D-numbers this session).

## Object-type showcase (SINGLE_SOURCE_SYSTEM + production generator, temp=0.0)
| wanted | emitted content_type | verdict |
|---|---|---|
| principle | principle | ✅ |
| process_template | process_template | ✅ |
| process_instance | process_instance | ✅ |
| tool_instruction | tool_instruction | ✅ |
| growth_edge | **principle** | ❌ under-detected |

- **BUG-145 reconfirmed in raw output:** `extraction_type=tool_instruction` (ROLE leaked into FORM field).
  The D2417 `_repair_conflation` fixes it in-pipeline (showcase bypassed the repair by calling `call_llm` directly).
- **Growth-edge under-detection:** speculative/untested passages default to `principle` despite the prompt's
  `empirical_pattern → growth_edge` mapping rule — because golden few-shot is 100% principle. Confirms D2345
  non-type few-shot fork is required for reliable GE/PI extraction.

## Next (blocking, unchanged)
1. **Full S2 `--reprocess-gated` on t11** — recover ~9,842 gated clusters (~5,500–6,000 genuine objects).
2. S4 merge (new aliases active) → S5 verify → audit → S6 commit (quarantine-aware).
3. Post-T1.1: D2345 non-type pass; P2-1/2/3; D2399 taxonomy consolidate on full-corpus counts.
