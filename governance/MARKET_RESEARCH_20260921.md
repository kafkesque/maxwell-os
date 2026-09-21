# MARKET RESEARCH — 2026-09-21

> **CONTEXT (read `governance/CONTEXT_INDEX.md` first).** Companion report set for the
> **hardware-anchored optimisation program** on Apple M1 Max. Predecessor external-methods report:
> `governance/MARKET_RESEARCH_20260917.md` (A1–A12). This report covers the **runtime + agent layer**:
> macOS 27 "Golden Gate", oMLX 0.7 dev, goose, the "Jev" typed-decision clones, and only-cli/oc.
> Strategy + sequencing: `governance/STRATEGIC_PLAN_20260917.md` (phase plan lives in §F below).
> Constraints C1–C28: `CONSTITUTION.md`. **Do not restate a config value here — cite the path.**

**Hardware anchor (measured, 2026-09-21).** MacBookPro18,2 · Apple M1 Max · 64 GB unified memory ·
400 GB/s bandwidth · 10-core (8 P + 2 E) · macOS 27.0 Golden Gate (26A428) · oMLX.app **0.7.0.dev4**
(`defaults read /Applications/oMLX.app/.../CFBundleShortVersionString`).

**Question:** given this hardware, which of {macOS 27 Core AI, oMLX 0.7, goose, the Jev clones,
only-cli/oc} should Maxwell OS adapt, reference, or reject — and in what order — to maximise
speed / accuracy / cost / tool-calling, without violating C1 ($0 marginal), C2/C4 (no lock-in),
C3 (sovereignty)?

**Version discipline.** "oMLX 0.7" = the **server** (jundot/omlx v0.7.0.dev4); the underlying
framework is Apple **MLX 0.32.2** / **MLX-LM 0.31.3**. Do not conflate. All claims below were
verified live against GitHub / release tags / local plists on 2026-09-21.

---

## A. ADOPT — highest leverage first

### A1. Pin oMLX to `0.7.0.dev2` (or enable API-key auth on dev4) — the dev4 startup bug
**0.7.0.dev4** has a documented failure to start on externally-accessible servers when API-key
auth is disabled. Maxwell's `~/.omlx/settings.json` exposes `server_aliases` on 192.168.0.103 /
10.150.61.110 with no auth block ⇒ in the dev4 failure class. **Adopt:** pin to `0.7.0.dev2` until
RC, OR enable auth in `settings.json` (then the dev4 bug is sidestepped). **Decided by:** does the
server survive a cold launch with the external aliases present? **Cost:** $0. **Config:** add
`omlx.pinned_version` (see §F Phase 1a).

### A2. Enable Lightning MTP for the Qwen3-Coder adapters (S2 — the 90%-of-LLM-time stage)
oMLX 0.7 ships **Lightning MTP** (multi-token prediction): **+34–58% decode** on Qwen3.8-27B /
DeepSeek / GLM families. S2 (`stage2_extract.py`, Qwen3-Coder-30B-A3B-Instruct-MLX-4bit) is the
single heaviest LLM cost in the pipeline (D2460: MoE decodes ~50 tok/s, 10× below theoretical).
MTP is **lossless** (accepts the same greedy token sequence at temp=0.0 ⇒ R7-safe). **Adopt:** enable
the MTP drafter for the Qwen3 adapters; measure before/after decode rate on a frozen S2 batch.
**Decided by:** tokens/s and wall-clock on a fixed 100-cluster S2 slice.

### A3. oQ4e / oQe quantization A/B (S2 + S4) — instrumented, not vibes (A10)
oMLX 0.7 adds **oQ4e / oQe** (outlier-aware) quantization. Re-run the A10 instrument: accuracy
**and** per-item flip-rate vs the current 4-bit / MXFP4 weights, report intervals (A1). Target
S2 (Qwen3-Coder-4bit) and S4 (gpt-oss-20b-MXFP4-Q8). **Decided by:** flip-rate stays inside the
A10 interval at the lower memory footprint.

### A4. Re-test the D2460 prompt-cache thrash flags (S2/S4 — the highest-risk config)
**Live finding 2026-09-21:** `~/.omlx/settings.json` currently has `cache.enabled: true` **and**
`gdn_ssd_split_enabled: true` — the exact D2460 thrash flags that crashed decode to 4–7 tok/s.
`assert_omlx_no_cache` (D2463) is supposed to refuse this, but the D2455/D2456 GUI migration
relaunched it cache-on. oMLX 0.7's prompt cache is the *beneficial* feature **only** when it stays
in hot RAM; the SSD split is the killer. **Adopt:** assert no-cache (or hot-cache-only) preflight;
re-measure decode. **Decided by:** D2460 gate (cache.enabled=false ⇒ ~50 tok/s).

### A5. goose → oMLX provider: already wired; fix the active provider
The OpenAI-compatible provider **already exists** at `~/.config/goose/custom_providers/maxwell_omlx.json`
(engine `openai`, base_url `http://localhost:11435/v1`, api_key_env `OMLX_API_KEY`) and is referenced
in `~/.config/goose/config.yaml` (`providers.maxwell_omlx`, `GOOSE_PLANNER_PROVIDER: maxwell_omlx`).
**The bug is `active_provider: custom_deepseek`** — the DELEGATE-001 broken provider (reasoning_content
passthrough). **Adopt:** switch `active_provider` to `maxwell_omlx`; pin recipes `temperature: 0.0`
(R7) + `GOOSE_MODEL` to Qwen3-Coder for generation / gemma-4-E4B for review.

### A6. Typed-decision bake-off for S5 (ADAPT D-275c, do NOT adopt a Jev dependency)
Run a **benchmark** — not an integration — of the open MLX "Jev" reimplementations
(`mizorewww/laya-mlx` ModernBERT encoder + decision head, `bnsd55/jevmlx` restricted-softmax
schema-valid JSON, `Zefan-Cai/Open-Jev` LoRA + single scalar head) against the existing
DeBERTa-v3-large NLI verifier and a constant-answer baseline, on the frozen 150-row ruler blind
sheet. This is the D-275c "ADAPT the calibrated-decision + typed-abstention framing" made
falsifiable. **Decided by:** does any typed head beat DeBERTa NLI on the ruler at equal abstention?
See §F Phase 2 + `scripts/bakeoff_typed_decision.py`.

---

## B. REFERENCE — read, do not integrate yet

| Item | Why reference, not adopt |
|---|---|
| **only-cli/oc** (`github.com/only-cli/oc`, 509★, MIT) | token-efficient fetch/distill CLI (DuckDuckGo/Bing/Reddit/GitHub page-distill). It improves **input hygiene** for market research (raw fetch, no LLM), but does not synthesise. Name-collides with OpenShift `oc`. Use `oc`/trafilatura for **extraction** + SearXNG for **search** + local LLM for **synthesis**. C1/C3-clean ($0, local). |
| **macOS 27 Core AI / Foundation Models / AFM 3** | on-device ~3B (`SystemLanguageModel`, 8k ctx) + PrivateCloudCompute (32k) are **closed Swift APIs, no downloadable weights**. `MLXLanguageModel`/`CoreAILanguageModel` conformances are interesting for interop but the AFM weights violate C2/C3 as pipeline models. Watch the Foundation-Models Swift layer only. |
| **goose v2.0 RC + Agent Client Protocol (ACP)** | AAIF (Linux Foundation) donation moves goose to open governance; v2.0 RC and ACP are the eventual agent scaffold upgrade. Do not migrate mid-program; re-evaluate after the Phase 3 recipe wiring stabilises. |
| **daseinlabs/open-jev** (Gemma-3-4B one-pass option scoring) | unlicensed ⇒ **do not vendor**; useful only as a reading reference for one-pass option scoring. |
| **oMLX one-click 450k benchmark settings + Cluster v2** | benchmark presets are a free calibration reference; Cluster v2 is irrelevant on one M1 Max (no multi-machine). |

---

## C. REJECT (with reason, so it is not re-proposed)

- **TypeSafe System One / Jev as a pipeline dependency** — already REJECTED (D-275c); closed typed
  model, no text generation, $0.042/M input. ADAPT the framing only (A6).
- **macOS 27 on-device AFM models as pipeline S2/S4/S5 models** — closed Swift, weights not
  downloadable ⇒ C2/C3 violation. (The Foundation-Models interop layer is a future curiosity, not a lever.)
- **CED prefill (+74–79%) for Qwen3-Coder** — CED is the DeepSeek-V4.1 prefill path; no relevance to
  the Qwen3 MoE S2 adapter on this workload.
- **Cluster v2 distributed serving** — single 64 GB machine, no second host ⇒ zero gain.
- **NAX fused attention / per-GPU neural accelerator / M5-Ultra / M6** — hardware not present on M1 Max.
- **`custom_deepseek` goose provider** — DELEGATE-001 reasoning_content passthrough bug; use `maxwell_omlx`.
- **`com.block.goose` defaults domain (D2262/D3251 legacy)** — the live bundle id is
  **`com.electron.goose`** (verified via `defaults domains`); the old literal is stale.

---

## D. M1 Max — configurable vs hard limits

| Lever | Configurable? | Where |
|---|---|---|
| Decode rate (bandwidth-bound, 400 GB/s) | **Yes** — MTP (A2), quantization (A3), KV-cache quant | oMLX model settings |
| Prefill / TTFT (the binding constraint) | Partial — prompt caching (A4), `--prefill-step-size`, wired memory | oMLX settings / MLX-LM flags |
| KV cache in hot RAM vs SSD | **Yes** — disable `gdn_ssd_split_enabled` (A4) | `~/.omlx/settings.json` |
| Memory guard ceiling | Yes — `omlx_guard_ceiling` 55 GB / `run_wall_budget` 48 GB | config / memory_guard.py |
| Concurrent batches | Yes — `max_concurrent_requests` (currently 6; MoE serialises, D2460) | `~/.omlx/settings.json` |
| NAX fused attention | **No** — not on M1 Max (M5/M6 only) | hardware |
| Per-GPU neural accelerator | **No** | hardware |
| CED / Cluster v2 | **No relevance** | workload/hardware |
| Apple on-device AFM weights | **No** — closed Swift | policy (C2/C3) |

---

## E. Pipeline stage mapping (S0–S6)

- **S0 / S0.5 / S1 / S1.3** — no LLM-bound; unchanged. (S0.5 metadata uses a small LLM — benefits
  from gemma-4-E4B via the existing provider, no change needed.)
- **S1.5 embed (bge-m3)** — frozen, stable (A10 note). No change.
- **S2 extract (Qwen3-Coder-30B) — top priority.** MTP (A2) + oQ4e A/B (A3) + prompt-cache fix (A4).
- **S4 classify (gpt-oss-20b + gemma-E4B)** — oQ4e A/B (A3) + cache fix (A4).
- **S5 verify (DeBERTa-v3 NLI)** — typed-decision bake-off (A6) is the *only* accuracy lever here.
- **S6 commit** — no change.

---

## F. Strategic test plan (maximum leverage → sequencing)

- **Phase 0 — instrument + fix D3251.** Run `defaults write com.electron.goose NSWindowOcclusionDetectionEnabled -bool false`
  (the live bundle id; keeps the goose Electron renderer from stealing 2–3 M1 Max cores during long
  OMLX runs). Keep the window visible as the fallback.
- **Phase 1 — runtime.** (a) add `omlx.pinned_version` + MTP enablement to `config/pipeline_config.yaml`;
  (b) draft `scripts/bakeoff_typed_decision.py` for gemma-4-E4B review (R5); (c) switch goose
  `active_provider` off `custom_deepseek` → `maxwell_omlx`; (d) re-test the D2460 cache flags (A4).
- **Phase 2 — typed-decision bake-off** (A6) on the frozen 150-row ruler sheet vs DeBERTa NLI + constant.
- **Phase 3 — goose recipes** pin temp 0.0 / provider / model (R7, R5) for the delegate-routing map (§G).
- **Phase 4 — deferred:** speculative-draft training, KV-cache quant A/B, Foundation-Models interop
  (all watch-only until Phases 1–2 land).

---

## G. Local-LLM delegation routing (this optimisation work)

- **Write scripts** → Qwen3-Coder-30B (one-shot via curl; never multi-turn agentic — DELEGATE-002).
- **Code review / classification sanity / summarise WITH source** → gemma-4-E4B-it-MLX-4bit.
- **Summarise logs (WITH source text only)** → Phi-4-mini-instruct-8bit (never open-ended — BUG-053).
- **Judge / classifier** → gpt-oss-20b-MXFP4-Q8.
- **Open-ended / version / fact research** → shell/curl directly (never delegate).

---

## H. What this research does NOT establish

Version/feature claims are GitHub/release/plist-verified on 2026-09-21, but the MTP / oQ4e /
typed-decision gains are **unmeasured on this exact M1 Max** — Phases 1–2 exist to falsify them.
The `maxwell_omlx.json` provider schema is goose-v1.x; verify against goose-docs.ai before the
v2.0 RC migration. The Jev-clone benchmarks are title/README-level, not full weight audits.
