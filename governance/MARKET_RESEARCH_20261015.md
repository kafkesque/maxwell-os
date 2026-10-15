# MARKET RESEARCH — 2026-10-15 (the DELEGATION axis: engines, models, harnesses, intake)

> **Read `governance/CONTEXT_INDEX.md` first.** Homes this file must NOT restate (C12/D-2646): the contract
> and the candidate set -> `config/agent_context.yaml`; the preflight cell -> `config/bench_preflight.yaml`;
> the intake policy -> `config/curator_intake.yaml`; defects -> `governance/buglog.md`. **Cite the path, never the value.**
>
> **SUPERSEDES (in part):** the *engine* rows of `governance/MARKET_RESEARCH_20260922_M1.md` and the verdict list
> inside `feed.opml` (both carried forward below, none overturned); the candidate rows of
> `config/agent_context.yaml#candidates_20261015` (see `#candidates_20261015b` for what changed).
> **Does NOT supersede** `governance/MARKET_RESEARCH_ONTOLOGY_20260919.md` (its claims are untouched).

## Method, and its limits (stated before any claim)

Live today, read-only: GitHub **search** API (9 queries) and search-returned repo rows; the HuggingFace
**models** + **tree** APIs (30+ family searches, trending, MLX-filtered, `createdAt` sweep over 300
repos); `llmfit` 0.9.38 (`recommend`, `fit`, `search`, `system`); raw README/`LICENSE`/`.gitmodules`
fetches; `docs.magnitude.dev/**.md` (llms.txt-indexed) — and **one measurement of our own** (see the bench row below).

**THREE LIMITS, DECLARED.** (1) The GitHub **core** API rate-limited mid-run (60 req/h unauthenticated,
no token in the environment): 48 of 67 repo-detail reads are ABSENT, not negative — the engine table's
star/issue/licence columns are **unverified for those rows**, and Qwen3.8-era repos are exactly the ones
whose numbers I could not re-read. (2) A download count, a star count and a community ranking are
**popularity**, not capability and not speed. (3) Everything below is **title/metadata-level** unless it
says MEASURED, and every MEASURED row carries where it was measured.

---

## A. Inference engines on THIS machine (M1 Max, 64 GB unified, 400 GB/s — `llmfit --json system`)

The axis that decides is unchanged from T-132: **decode is unconstrained; the bill is PREFILL**, and prefill
is a function of prompt SIZE and of POOL STATE (BUG-801, BUG-803). An engine that wins this axis wins by
raising prefill throughput and by not thrashing the pool — not by adding models.

| engine | what it is (verified today) | verdict for Maxwell OS |
|---|---|---|
| **oMLX** (jundot/omlx, Apache-2.0, 22.8k★, pushed 2026-10-15) | OUR baseline. Menu-bar app + `~/.omlx/bin/omlx` shim, continuous batching, **tiered KV cache: hot in-memory + cold SSD, persisted ACROSS context changes** (upstream README, read today) | **BASELINE HOLDS.** The upstream README also proves F6/BUG-792 is a *configuration* question, not a capability question: `~/.omlx/settings.json#cache.enabled` is `false` here while upstream advertises the feature. Installed **0.7.0** vs upstream releases (could not read today: rate limit) -> **version gap UNMEASURED, must be closed before any engine decision (T-134)** |
| **Magnitude** (magnitudedev/magnitude, **Apache-2.0**, Rust/Bun, 6.7k★, pushed today) | "Tunes its kernels on your hardware" — autotunes per model/chip at download (~1 min, output-preserving), **2x faster than Ollama claimed**, Apple Silicon/NVIDIA/AMD/CPU. Serves **OpenAI-compatible `127.0.0.1:10100/inference/v1`** AND **Anthropic-compatible `/inference/anthropic`**, `GET /health`, local calls need no key. One-click agent connections: **Pi, OpenCode, Hermes, OpenClaw, Codex, Claude Code, Oh My Pi, Cline**. `magnitude server setup` = boot service, survives logout, self-updating. Submodules: `magnitudedev/llama-cpp-rs`, `magnitudedev/tilelang` (branch `magnitude`) | **WORTH A DECLARED SLOT, NOT A MIGRATION.** It is the only candidate that (a) tunes for OUR chip, (b) speaks BOTH API dialects (so Claude Code/Codex-shaped harnesses can point at it), (c) ships a boot service, (d) Apache-2.0. **UNVERIFIED and decisive:** whether it can serve **our exact model set** (upstream: "we write optimized kernels for the most popular families"; we need Qwen3-Coder-30B-A3B, gpt-oss-20b-MXFP4, gemma-4-E4B, Phi-4-mini), whether it exposes **cache/prefill controls** comparable to `settings.json`, and whether a per-model tuned artifact is **reproducible offline** (C2/C4). It also has **no embeddings and no NLI role** — it cannot replace bge-m3 (Ollama) or the DeBERTa verifier. Admit only by the T-131 preflight, in the `agent_probe` slot first |
| **TensorFold** (ashhart/TensorFold, 1.3k★, created 2026-06-19) | **Zig** binary, Metal (Apple) and CUDA kernels directly, **no Python/MLX needed**; OpenAI **and** Anthropic Messages API on `:8080/v1`; `--parallel`, `--context`, `--temperature`, `--no-thinking`; homebrew formula; desktop workspace with "coding workers"; "Living Weights" experimental | **WATCH (young, single-author, created 4 months ago).** Its independence from Python/MLX is a real resilience property (C23) but a second engine = a second failure surface. No timed comparison exists on our models. Re-read in 60 days |
| **PMetal** (Epistates/pmetal, 328★, pushed yesterday) | "high-performance Apple Silicon framework for local LLM inference" | **WATCH.** Too little evidence to do more |
| **vllm-swift** (TheTom/vllm-swift, 274★, last push 2026-06-03) | vLLM Metal plugin on mlx-swift | **WATCH (stale, 4 months)** |
| **Rapid-MLX / MTPLX / CIDER / mlx-serve / AngelSpec / DFlash / DSpark / EAGLE-3 / splash / turbo-fieldfare / TinyChatEngine / LiteRT-LM** | Prior-session verdicts, carried in `feed.opml` (⭐ = promising, REJECT/REFERENCE/WATCH marked there) | **CARRIED FORWARD, NONE OVERTURNED.** `turbo-fieldfare` (a Gemma 4 26B-A4B single-model engine) is now MORE relevant, not less: the A4B is already on this disk (below). `mlx-dspark` = net LOSS on M1; `splash` = REJECT on M1 |

**The engine recommendation (senior, future-proof).** Keep oMLX as the *baseline and the only engine the
pipeline may assume*; put the engine behind the protocol C21 already demands, and admit a competitor ONLY
through a declared preflight in ONE slot. Two facts make this the cheap choice: the transport is already
OpenAI-compatible (so a swap is a base-URL change, not a rewrite), and BUG-802 (boot survival) is
**engine-independent work that pays off under every candidate**.

---

## B. Models — the last ~60 days, and what is actually worth downloading

**The shape rule, re-confirmed with a MEASURED proof.** This machine pays **bytes read per step** at
400 GB/s, so a small-**active** MoE beats a bigger dense model. MEASURED 2026-10-15: the 30B-A3B decodes
**faster** than the 4B dense at ~2.5x the weight bytes (`config/agent_context.yaml#measured_decode_20261015`).
Download shape = **A2B/A3B/A4B, big total**.

### Released in the last ~60 days, most downloaded (text classes only, HF API today)

| model | dl | likes | created | size/share | read |
|---|---|---|---|---|---|
| `prism-ml/Ternary-Bonsai-2-27B` (gguf 4.85M dl / **mlx-2bit 8.60 GB**, ctx 262144) | 4.85M | 2697 | 2026-09-16 | 2-bit ternary 27B in **8.6 GB** | the single most interesting **download** for the loop/probe role: ~half the bytes of a 4-bit 27B -> roughly double the decode, IF quality survives 2-bit ternary. **Needs a quality gate before any role** (no reading exists) |
| `ornith-ai/Ornith-1.5-9B` + `Ornith-1.5-35B-A3B` (GGUF + MLX 4/6/8-bit; **MLX-4bit 35B-A3B = 19.51 GB**, ctx 262144) | 5.01M / 3.71M | 540 / 511 | 2026-08-19 | A3B, servable | we already hold `Ornith-1.5-9B-MLX-8bit` + `Ornith-1.5-35B-A3B-REAP-19B`; the MLX-4bit 35B-A3B is the same shape as our 4-bit SKUs |
| `empero-ai/Qwen3.8-35B-A3B-Distill` | 998k | 211 | 2026-09-16 | **A3B** | the A3B shape carrying **Qwen3.8 lineage** — the most promising *second coding voice*; **llmfit's DB does not know it** and no MLX 4-bit repo was confirmed -> download only after a repo/format check |
| `deepseek-ai/DeepSeek-V4.1-Flash` | 1.24M | 4516 | 2026-09-10 | fp8-class, big | strong community signal; size/positioning must be read before any claim |
| `zai-org/GLM-5.3-Flash` (328 GB repo) + `GLM-5.3` | 6.53M / 1.80M | 2855 / 2223 | 2026-08-25 | too big at 4-bit | **NOT FOR THIS MACHINE** (GLM-4.7-Flash remains the GLM candidate that fits) |
| `LiquidAI/LFM2.5-24B-A2B` (47.9 GB repo, ctx 131072) | 6.3k | 343 | **2026-10-12** | **A2B** | new (3 days old), tiny downloads, strong shape. **WATCH 30 days** — newest A2B, unproven |
| `autotrust/JEV-35B` (pipeline `text-classification`, 71.9 GB) | 41.8k | 877 | 2026-10-11 | 35B | a *classifier* at 35B is interesting for S4 discipline/domain — **REJECT for now**: our S4 classifier is gpt-oss-20b at 12.1 GB and a 35B classifier costs the whole guard |
| `ConwayResearch/Underdog-Saluki-27B-1.0` (9.46 GB) | 344k | 473 | 2026-10-08 | 27B in 9.46 GB | same 2-bit-effect family as Ternary-Bonsai; **WATCH** |
| `google/embeddinggemma-2` (1.49 GB, ctx 262144, feature-extraction) | 144k | 2318 | 2026-09-14 | embedder | **the only trending model that touches our PIPELINE CORE** — and the highest-risk swap in this document: **every stored vector is in bge-m3 space**, so a new embedder invalidates the FAISS index, the store's `sqlite-vec` rows and every cluster in S1.5. **Do not swap casually**; it is a declared migration with a re-embed receipt, or it is nothing. First: an offline A/B on the S1.5 clustering that proves a better cluster |

**What to DELETE (the user's question, answered with the byte home checked — see BUG-804).** Deletion needs
a blob-aware census, because five of the eight served models read **0 B** in `~/.omlx/models` (they are
symlinks into `~/.cache/huggingface`, 165 GB). Ranked delete candidates, to be confirmed by that census:
`gemma-4-12B-it-qat-OptiQ-4bit` (worst non-27B decode MEASURED, and its role is covered by the 4B and the
A4B), `Qwen3.8-27B-MLX-4bit` (15 GB, worst loop bill by 6.6x — keep only if its PREFILL is fixed, BUG-793),
and the parked `_unloaded/` set (`DeepSeek-R1-0528-Qwen3-8B`, `Qwopus-GLM-18B`, `gemma-4-E2B` — the last
is redundant against the E4B). **Nothing is deleted this session** (an unverified inventory may not drive a delete).

**CORRECTION, MEASURED 2026-10-15 (same session, after the claim was first written):** both models sit in
the engine's parked directory (~/.omlx/_unloaded/) and are **NOT in the engine's served list** - /v1/models
returned 8 entries and neither of them is among them. "Already on disk" is therefore true about the BYTES
and false about the SERVICE: making either one preflightable is ONE declared act (move the directory back),
not zero acts. The bench run attempted the A4B by name and got no usable reading for exactly this reason -
filed as BUG-806, whose point is that the RAW error was not persisted, so the cause is INFERRED from the
served list and never proven from the receipt.

**Already on disk (bytes), NOT yet served:** `gemma-4-26B-A4B-it-OptiQ-4bit` and
`Qwen3.6-35B-A3B-4bit` sit in `~/.omlx/_unloaded/`. The "worth downloading" recommendation from the
previous session is **already downloaded** — the open item was never the download, it was the SLOT.

---

## C. The harness layer — what each one actually is, and what it is FOR here

Verified today (GitHub search, 2026-10-15): **OpenClaw** `openclaw/openclaw` (MIT, "any OS, any
platform"); **Pi** `earendil-works/pi` (MIT, "unified LLM API, agent loop, TUI, coding agent CLI");
**OpenCode** `anomalyco/opencode` (MIT, "the open source coding agent"); **DeepSeek Harness**
`deepseek-ai/deepseek-harness` (MIT, "everything is a plugin"); **Orca** `stablyai/orca` ("the ADE for
working with a **fleet of parallel agents**"); **Claude Code**, **Codex**, **Hermes** (all named as
Magnitude one-click connections today, docs.magnitude.dev/faq).

**The architectural answer (C25: agent-agnostic).** A harness is a **front-end**, and Maxwell OS must
never be coupled to one. Every harness in that list can be pointed at the local engine because the engine
speaks OpenAI (and now, if Magnitude is adopted, Anthropic) — so the choice of harness is the *owner's
ergonomics*, not an architectural variable. **What must stay harness-independent:** the pipeline (its own
stages), the ingest door, the owner gates, and every delegate's output check. A harness may *drive* the
pipeline through MCP/CLI; it may never *be* the pipeline.

**Where each is genuinely stronger, honestly:** parallel bug-fixing (block III) is the one place the
choice matters, and **Orca is the only one of the list whose stated purpose is a fleet of parallel
agents** — but a fleet multiplies the PARTITION problem, not the throughput problem: two agents on one
file is a conflict (see D-3001's sibling rule in `config/agent_context.yaml`), so the limiter is the
partition and the applier, never the harness count.

---

## D. The intake / curator stage — reference stack (block II)

Full design in `governance/CURATOR_INTAKE_20261015.md`; policy in `config/curator_intake.yaml`.
Verified-today references and their verdicts: **RSSHub** (route ANY site — X, Telegram, Substack — to
RSS; the one component that makes "one feed" possible without a bespoke scraper per platform; **ADOPT
route**), **FreshRSS / Miniflux / NetNewsWire** (self-hosted/desktop aggregators; **REFERENCE**),
**Folo** ("the AI RSS Reader", 39k★; **REFERENCE**), **fuxiaoai/tidings-rss** (curated, live-verified
OPML collections; **ADOPT as a seed list, never as truth**), `jacob-bd/openclaw-newsroom` (an
OpenClaw news-scanning pipeline over 5 sources; **REFERENCE** — proves the shape, and it is a
harness-coupled implementation, which C25 forbids for us), `renee-jia/latent-feed` (AI news ->
Obsidian; **REFERENCE**), **changedetection.io** (change detection on sources with no feed; **ADOPT
where a feed is absent**), **yt-dlp** + **youtube-transcript-api** (transcripts first; **ADOPT**),
**WhisperKit/faster-whisper** (ASR fallback for podcasts; **ADOPT as fallback**), **crawl4ai /
microsoft/markitdown** (HTML/PDF -> clean MD; **ADOPT**, feed S0), **Firecrawl/browser-use**
(**REFERENCE** — heavier, and their hosted paths violate C1/C3), **STORM** (report generation;
**REFERENCE**), **Fabric** (pattern library; **REFERENCE**), **karakeep/linkwarden** (bookmark + AI
tagging; **REFERENCE for UX, not for data**), and for the noise screen: **protectai/llm-guard** and
**protectai/deberta-v3-base-prompt-injection** (**ADOPT the idea immediately**: untrusted text is
SCREENED before any model is asked to treat it as content — prompt injection is the one attack that turns
an intake pipeline against its own store). Our own **DeBERTa-v3-large NLI** is the claim-level checker and
our **S4 classifier** is the discipline/domain router; the curator's relevancy model must be a THIRD,
independently measured thing.

**The one design rule that keeps the curator honest (and the reason it is a decision, not a feature):**
the noise filter is a **two-sided control**. A filter that drops 5% of alpha to remove 90% of slop is a
*decision the owner must be shown*, so the curator publishes its own precision/recall on a frozen golden
set, and **an item it drops is still COUNTED and REVERSIBLE** — a dropped item that can never be seen is
an invisible failure (the BUG-787 shape, in the intake).
