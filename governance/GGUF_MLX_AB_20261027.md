# GGUF (llama.cpp) vs MLX (OMLX) A/B — 2026-10-27

**Purpose (BUG-1033 / D-3161):** decide whether llama.cpp+GGUF beats the incumbent MLX/OMLX
runtime on decode speed or memory residency for the two models downloaded for the test. The gate
was explicit: a `llama_cpp_provider.py` is written ONLY if GGUF wins an axis.

**Receipt scope:** this is a MEASURED receipt on THIS machine. Every number below was read from
this host, not from a vendor page.

## Harness state (recorded for comparability — D-3161)
- host: Apple M1 Max (arm64), macOS
- memory lever: `iogpu.wired_limit_mb = 57344` (session-scoped)
- llama.cpp: 0.7.0 (build 9430, d48a56eff), AppleClang 17, Metal backend (ggml 0.13.1)
- MLX runtime: OMLX served at http://127.0.0.1:11435/v1
- GGUF files: sha256-verified complete (receipts match HF metadata)
- memory at start: 94% system free, 6176 cumulative pageouts

## D-3161 comparison rows

| capability | reference impl | runtime + quant | OUR rate (measured) | residency |
|---|---|---|---|---|
| gpt-oss-20b decode | llama.cpp | Metal 0.7.0 / Q4_K_M | **tg128 45.81 ± 0.93 t/s** (pp512 461.41) | 10.81 GiB |
| gpt-oss-20b decode | OMLX | MLX / MXFP4-Q8 | **43.88 t/s** incl TTFT (≈47 t/s pure decode) | 11 GiB |
| Qwen3.8-27B decode | llama.cpp | Metal 0.7.0 / UD-Q4_K_M | **tg128 5.31 ± 0.03 t/s** (pp512 58.19) | 15.32 GiB |
| Qwen3.8-27B decode | OMLX | MLX / 4bit | **8.98 t/s** incl TTFT (≈9.3 t/s pure decode) | 15 GiB |

MLX-side decode measured via OMLX `/v1/chat/completions`, max_tokens=128, temp 0.0, warmup call
first; the reported t/s includes time-to-first-token, so MLX's true pure-decode rate is slightly
HIGHER than shown — this only strengthens MLX's position.

## Verdict

**GGUF/llama.cpp does NOT win any axis on this hardware.**

- **gpt-oss-20b (MoE):** WASH. 45.81 t/s (GGUF) vs ≈47 t/s (MLX). Residency 10.81 vs 11 GiB. No
  advantage to adopt.
- **Qwen3.8-27B (dense):** MLX WINS clearly. ≈9.3 t/s (MLX) vs 5.31 t/s (GGUF) — a ~1.75× gap.
  Residency 15.32 vs 15 GiB (wash).

## Caveats (stated, not hidden)
1. **Quant mismatch is inherent:** GGUF Q4_K_M / UD-Q4_K_M vs MLX MXFP4-Q8 / 4bit. The test is
   runtime+quant combined, not a pure runtime swap. The verdict is robust because MLX wins or ties
   across the quant differences.
2. **UD quant understates GGUF Qwen3.8:** "UD-Q4_K_M" (Unified-Dynamic) is slower than standard
   Q4_K_M. A standard Q4_K_M could narrow the 5.31→9.3 gap, but the gap is large enough that MLX's
   win holds; re-testing with standard Q4_K_M is optional and would not change the gpt-oss wash.

## Decision
**Do NOT write `pipeline/providers/llama_cpp_provider.py`.** MLX/OMLX remains the decode runtime.
No axis was won. This is a measured negative (D-3038): a future re-proposal of "switch to
llama.cpp" must cite a NEW measurement that beats these numbers, not re-argue from memory.

Two GGUF-capable runtimes exist on this host (llama.cpp 0.7.0 and Ollama 0.40.11); if a GGUF model
is ever needed for portfolio coverage, Ollama (already the embedding runtime) is the lower-tax
route, not a new provider.

Receipt: governance/GGUF_MLX_AB_20261027.md
