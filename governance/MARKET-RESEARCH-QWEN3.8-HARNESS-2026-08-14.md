# Market Research — Qwen3.8 MLX 4-bit + Local-LLM Agent Harness
> **Date:** 2026-08-14 | **Author:** goose (research) | **Status:** Research complete, awaiting decision
> **Trigger:** DeepSeek price increase anticipated; goose `delegate()` cannot properly drive local LLMs for coding/research/analysis.

---

## 1. Q1 — Is Qwen3.8 MLX 4-bit available?  ✅ YES

### 1.1 Verdict
**Confirmed available** via HuggingFace API (llmfit's local DB has not yet indexed Qwen3.8 — run `llmfit update` to refresh).

### 1.2 Model — Qwen3.8-27B (base)
- **Repo:** `Qwen/Qwen3.8-27B` — Apache-2.0, bf16 ≈ 55.59 GB (18 shards)
- **Family:** Qwen3.8 (successor to Qwen3.5/Qwen3.6), built on Qwen3.5 architecture
- **Type:** Dense 27B (NOT MoE) — native vision-language (image + video)
- **Architecture:** 64 layers, hidden 5120, vocab 248,320 (padded)
  - Hybrid: `16 × (3 × (Gated DeltaNet → FFN) → 1 × (Gated Attention → FFN))`
  - Gated DeltaNet (linear attention): 48 V heads / 16 QK heads, head dim 128
  - Gated Attention: 24 Q heads / 4 KV heads, head dim 256
  - MTP (Multi-Token Prediction) trained with multiple steps
- **Context:** 262,144 native → extensible to 1,000,000 (YaRN RoPE scaling)
- **Thinking control:** `reasoning_effort` tuning, `preserve_thinking` (retains reasoning trace across turns)
- **Agentic strengths:** strong autonomous planning, environment-feedback handling, long-horizon task completion (evaluated on SWE-bench Pro, DeepSWE 1.1, QwenSWEBench, RecreationBench)

### 1.3 4-bit MLX variants (verified on HF)
| Repo | Format | Notes |
|------|--------|-------|
| `lmstudio-community/Qwen3.8-27B-MLX-4bit` | MLX 4-bit | **16.08 GB** (3 shards) — recommended |
| `mlx-community/Qwen3.8-27B-4bit` | MLX 4-bit | community canonical |
| `mlx-community/Qwen3.8-27B-mxfp4` | MXFP4 (4-bit) | modern fp4 format |
| `mlx-community/Qwen3.8-27B-nvfp4` | NVFP4 (4-bit) | NVIDIA fp4 format |
| `mlx-community/Qwen3.8-27B-8bit` | 8-bit | ~27 GB |
| `mlx-community/Qwen3.8-27B-bf16` | bf16 | ~55 GB (raw) |
| `mlx-community/Qwen3.8-27B-mxfp8` | MXFP8 | 8-bit modern |

No dedicated "Coder" variant exists yet — Qwen3.8-27B is general-purpose with strong coding.

### 1.4 Hardware fit (M1 Max — 64 GB unified, 400 GB/s)
- 4-bit: **16 GB weights + ~4-6 GB KV cache ≈ 20-22 GB** → 32% of 64 GB ✅ Perfect
- 8-bit: ~27 GB + KV ≈ 34 GB → still fits ✅
- Estimated throughput (roofline @ 400 GB/s): **~12-18 tok/s** (4-bit, dense 27B)

### 1.5 Strategic fit vs current lineup
| Role | Current | Qwen3.8-27B-4bit delta |
|------|---------|------------------------|
| LONG_CONTEXT | Qwen3-Coder-30B-A3B (MoE, 3B active) | Dense 27B + 262K native → superior for long-context synthesis |
| HIGH_CAPABILITY | Qwen3-Coder-30B-A3B | 27B dense often beats 30B-A3B MoE on reasoning/agentic |
| Generator (R5) | Qwen3-Coder-30B-A3B | Cross-family constraint: if Qwen3.8 replaces generator, verifier family must change |

**Caveat (R5 Generator≠Verifier):** both current generator and Qwen3.8 are Qwen family. Introducing Qwen3.8 as generator keeps the verifier (gpt-oss / gemma / DeBERTa) cross-family — no R5 violation. But Qwen3.8 cannot ALSO be a verifier against a Qwen generator.

---

## 2. Q2 — Best TUI / agent harness for local-LLM orchestration

### 2.1 Root cause of goose's local delegation failure
- **BUG-063:** goose `delegate()` routes subagents through a Deno/TypeScript sandbox with **no filesystem access** → any local-LLM provider cannot read project files → file-analysis delegation fails silently. Workaround so far: ad-hoc `curl` / `pipeline/omlx_delegate.py`.
- **DELEGATE-001:** `custom_deepseek` provider has a `reasoning_content` passthrough bug (broken).
- **Working local path today:** OMLX server is already OpenAI-compatible at `http://localhost:11435/v1/chat/completions` (API key `sk-maxwell-local`). `pipeline/omlx_delegate.py` is the permanent file-grounded delegation fix (in-process, real FS access).

### 2.2 Harness landscape (ranked for THIS use case)

| Harness | Type | Local-LLM support | Best for | Verdict |
|---------|------|-------------------|----------|---------|
| **goose** (current) | TUI orchestrator | via OpenAI-compat gateway + MCP | orchestration, MCP glue | **Keep** — fix the delegate path |
| **Aider** | TUI coding agent | `--openai-api-base` → any endpoint (OMLX :11435, Ollama :11434) | everyday coding, architect/editor two-agent | **Adopt** for daily coding |
| **Open WebUI** | Web TUI | native Ollama + OpenAI-compat + pipelines + RAG + tools | research/analysis daily driver | **Adopt** for research |
| **smolagents** (HF) | code-first agent framework | native transformers/MLX/Ollama | Phase 2 skill orchestrator | **Adopt** (protocol-first) |
| **LangGraph** | orchestration framework | any LLM | multi-step pipeline orchestration | **Reconsider** (D2010 rejected LangChain, not LangGraph) |
| **OpenHands** | coding agent | local | heavy autonomous coding | Optional (resource-heavy) |
| **CrewAI / AutoGen** | multi-agent | local | role-based agent crews | Optional (heavier) |
| **llm** (Simon Willison) | CLI | many backends + plugins | quick scripting | **Adopt** as utility |

### 2.3 Recommendation (tiered, aligned to C21/C22/C25)

1. **Keep goose as the human-facing orchestrator** (C25: MCP-exposed knowledge is harness-agnostic). The fix is NOT to abandon goose but to stop using its broken `delegate()` provider path:
   - Expose ALL local models behind one **OpenAI-compatible gateway** (OMLX :11435 already does this).
   - Use **`pipeline/omlx_delegate.py`** as the canonical file-grounded delegation CLI (BUG-063 fix, already built).
2. **Aider** for everyday coding — point it at OMLX (`--openai-api-base http://localhost:11435/v1`).
3. **Open WebUI** for research/analysis/synthesis — local RAG + pipelines.
4. **smolagents (or LangGraph)** as the Phase 2 skill-orchestrator engine — code-first, local-MLX native, protocols-first (C21/C27).
5. **llm** CLI for quick one-shots and scripts.

### 2.4 Cost-effectiveness math
- Local: $0 marginal (C1) — OMLX at 12-18 tok/s for Qwen3.8-27B-4bit is "free".
- DeepSeek price increase: strengthens C1/C22 local-first default; frontier API stays opt-in only for non-verification roles.

---

## 3. Scaffolding plan (from here)

### A. Model layer
1. `llmfit update` — refresh local DB so Qwen3.8 is scoreable.
2. Download `lmstudio-community/Qwen3.8-27B-MLX-4bit` (16 GB) via OMLX/MLX.
3. Add to `config/pipeline_config.yaml` + `config/model_assignments.yaml`:
   - New role `AGENT_ORCHESTRATOR` / upgrade `LONG_CONTEXT` → Qwen3.8-27B-4bit.
   - Keep R5: verifier stays gpt-oss/gemma/DeBERTa (cross-family).

### B. Harness layer
1. Formalize `omlx_delegate.py` as the canonical delegation interface (document in AGENTS.md delegate rules).
2. Wire OMLX as an OpenAI-compatible provider for goose + Aider + Open WebUI.
3. Add MCP tools to `maxwell_mcp_server.py` for `run_pipeline`, `delegate_local` (expose omlx_delegate via MCP → C25).

### C. Knowledge pipeline (continue)
1. Unblock S4 speed (gpt-oss-20b classify ~3.5 FBs/min → 62h full-run) — batch/tune classifier.
2. Scale to 20+ books E2E (Q6).
3. Tier 2 quality calibration (golden set audit).

### D. Skill orchestrator (Phase 2)
1. Define `skill.md` standard + registry (C12 config-first).
2. Protocols first (C21/C27): InferenceProvider, StorageBackend, SkillExecutor.
3. Build orchestrator on smolagents/LangGraph with local models as workers.
4. Run projects: canary → golden → 5+ book E2E.

---

*Research sources: HuggingFace API (`Qwen/Qwen3.8-27B`, `lmstudio-community/*`, `mlx-community/*`), llmfit v1.1.6 hardware detection, local config (`config/model_assignments.yaml`, `agent/session_seed.yaml`, `pipeline/omlx_delegate.py`, `governance/buglog.md`).*
