# Maxwell OS — Not-Yet-Evaluated Research Opportunities
> **Date:** 2026-08-09 (register opened) | **Last synced:** 2026-10-17 | **Source:** feed.opml + senior RAG developer assessment
> **Status:** A LIVE register: the P1–P3 rows below are candidates, and the DATED sections at the foot are the
> evaluations that have since been run (D-3038: what we reject we register, with its reason). A row whose
> "why deferred" has been ANSWERED by a measurement is re-cut in place rather than left standing — see R-12.

---

## 🔴 P1 — Implement Now (validated, low risk)

| # | Technology | What | Stage | Gain | Risk | Effort |
|---|-----------|------|-------|------|------|--------|
| **R-01** | Prompt trimming | Remove redundant CRIBS editing rules | S4 | 19% input tokens saved (233 chars) | ✅ NONE — same semantics | ✅ IMPLEMENTED |
| **R-02** | Structured JSON output | OMLX `response_format: json_object` | S2/S4/S5 | Fewer JSON repairs, faster parsing | ⚠️ Needs A/B test | 1h |
| **R-03** | llmfit preflight | Hardware-model fit check in `just preflight` | DevEx | Model selection quality | ✅ NONE — read-only | ✅ ADDED |

---

## 🟡 P2 — Benchmark Required

| # | Technology | What | Stage | Potential Gain | Current Status | Effort |
|---|-----------|------|-------|---------------|----------------|--------|
| **R-04** | USearch | SIMD NEON FAISS replacement | S1.5 clustering | 10x search speed | ⭐4,216 GH. Deferred T3.1. NEVER benchmarked on Maxwell corpus. | 3h |
| **R-05** | TurboVec integration | Quantized search accelerator | S1.5 k-NN, retrieval | 4-8x search speed | ✅ Installed (v0.8.0). NOT wired into pipeline. | 2h |
| **R-06** | LightRAG evaluation | Graph-based RAG, EMNLP2025 | FB retrieval | Better recall via graph traversal | ⭐37,713 GH. EMNLP2025 paper. NOT tested on Maxwell FB corpus. | 1d |
| **R-07** | Merged CRIBS+Classification | Single LLM call for both tasks | S4 | 73% token savings (2M tokens/S4 run) | ⚠️ Needs A/B quality test first | 3h |

---

## 🔵 P3 — Research / Monitor

| # | Technology | What | Stage | Why Deferred |
|---|-----------|------|-------|-------------|
| **R-08** | LEANN | 97% storage savings RAG | FB retrieval | MLsys2026. Needs benchmarking on M1 Max. |
| **R-09** | memvid | Agent memory layer (serverless) | Agent harness | ⭐15,901. Knowledge graph support. Evaluated for Maxwell agent, not pipeline. |
| **R-10** | zvec | Alibaba embedded vector DB | Persistent vectors | ⭐14,942. HNSW, embedded. May replace FAISS for storage. |
| **R-11** | SiliconScope | Apple Silicon native monitor | System diagnostics | ⭐802. ANE/Memory-bandwidth tracking. Diagnostic only. |
| **R-12** | Prompt caching | Cache system prompts across calls | S4 | ~500 tokens saved per FB | ✅ **ANSWERED 2026-10-16 (BUG-872): the cache is LIVE and was never disproven** — byte-identical 2,616-token prefix, gemma-4-E4B cold 6.90 s → warm 0.16–0.39 s, `cached 2613/2616`, **25.01x** against a declared 5.0x bar, confirmed independently by `agent_context_probe --prefill-ab`. Two corrections the measurement forced: the cache is **PER-MODEL** (`cached = 0` on both Orniths), and the binding constraint is **PREFIX STABILITY**, not prefill throughput — one byte changed at the head converts a 0.16 s turn back into a 6.90 s one. The `2,000-token comparable floor` this row's stage relied on is **DISPROVEN** (gpt-oss-20b-Q8: 71.3 tok/s @ 2,677 vs 210 tok/s @ 50,082). |
| **R-13** | Token-efficient prompt patterns | Systematic prompt optimization | All stages | 10-30% across pipeline | Requires per-stage analysis. |
| **R-14** | Recursive Flint (40B-A2.5B MoE coding model) | Coding-agent MoE; 39.8B total / ~2.5B active, 256 experts (6+1 shared), 262K ctx, sliding-window 513 | Pipeline generator / agent loop | **Both target runtimes EXIST and are measured fast** (Ollama 87–115 tok/s on M5 Pro 64GB 4-bit; MLX conversion in `mlx-community/flint-mixed-3-4bit`) | ❌ **NOT ADOPTED 2026-10-25** — four blockers, each measured: (1) operating point is **temp 1.0 / top-p 0.95 / top-k 20**, a direct conflict with R7 (temp=0.0 on all generation scripts); (2) **tool calls fail without a constrained-decoding grammar** (41/85 failed in OpenCode with a community MLX build; 0/50 after adding a grammar — mlx-lm/OMLX has no grammar path); (3) Recursive's own fast engine `rec` (1.4–2.6× llama.cpp) **requires an M4 Pro/M5 Pro/M5 Max + ≥48 GB — this box is an M1 Max**; (4) community quality is **behind Qwen3.6-35B-A3B** and it **overthinks** (20K+ reasoning tokens). Full receipt below. |
| **R-15** | Underdog Saluki 27B 1.0 (ConwayResearch) | 2-bit **IQ2-mix** requant of **Qwen3.8-27B** (base `ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF`), Apache-2.0, weight file **7.89 GB**, thinking switchable per request, optional vision add-on (`mmproj`, 0.6–0.9 GB) | Tool-calling / agent-loop **only** — never pipeline generation, classification or verification | **Ollama: YES, MLX: NO.** Ollama is supported through the card's own `ollama create` recipe and is stated as tested ("Ollama 0.40.4 on Apple silicon: chat, thinking and tool calling work"). MLX has **no** build: 9 hub repos match `saluki` and **none** is MLX; the bf16 dequant (`rty813/…-bf16`) exists but re-quantising it to MLX 4-bit returns the base model already served at 4-bit, because Saluki's whole contribution **is** the GGUF IQ2 recipe | ⏸️ **REFUSED TO DOWNLOAD 2026-10-25 — LANE LEFT OPEN, NOT CLOSED.** Five measured reasons: (1) **engine-ROLE-bound** (CORRECTED 2026-10-25 — see the correction block at the end of this section): Ollama **is** installed and running on this box (v0.40.11); its declared role is the **embedder**, while the generation pool is OMLX-only, so a generation role for it is a new role on a stack whose lifecycle is not governed as a generation engine; (2) **2-bit costs the axis Maxwell is most exposed on** (card's own: MuSR 67.5 vs 79.6, AIME 2025 79.2 vs 96.7, MBPP+ 78.0 vs 83.9); (3) the headline **88-vs-84 is the VENDOR's own 120-task set**, and the card concedes "120 tasks is a modest test", "a few tasks of any gap is run-to-run variation" and "about a fifth of parallel-call replies have small formatting slips"; (4) it **duplicates a served model** (`Qwen3.8-27B-MLX-4bit`, 15 GB measured) at LOWER precision, so D-3009's pool rule would demand a RETIREMENT to seat it; (5) **the instrument cannot see the claimed effect** — T-187's two-step fixture DOES grade argument values and name-drift, but on ONE fixture, and a 1-task instrument cannot resolve a 3-point gap on 120 tasks. **Its one genuine merit, recorded so it is not lost: it is temp-0-native** (card: thinking off, temperature 0 for tool calls), so unlike Flint (R-14) it does **NOT** conflict with R7. Full receipt below. |

---

## ❌ Already Evaluated & Rejected

| Technology | Why Rejected | Source |
|-----------|-------------|--------|
| Cloud burst (GPT-4o-mini) | C1/C3 violation | Kimi |
| LangChain/LlamaIndex | C2 vendor lock-in | D2010 |
| Microsoft GraphRAG | Cloud-native | D2118 |
| LanceDB/DuckDB | SQLite adequate (C5) | D2048 |
| Dagster/Prefect | PipelineRunner <300 LOC | D2061 |
| Full Pydantic migration | Schema accessors sufficient | D2120 |
| Leiden algorithm | Louvain adequate. Revisit at scale. | Kimi |
| OpenFActScore | Overengineered | Kimi |
| Self-RAG training | C1 + R7 temp=0.0 | D2205 |
| CRAG web search | C3 sovereignty | D2205 |
| ColBERT late interaction | M1 Max memory | D2205 |
| Multi-agent swarm | 39-70% coordination tax | D2205 |
| Neo4j graph database | C3 external service | D2205 |
| Rapid-MLX | HF network cache issue (C1/C3 violation) | feed.opml eval |
| MTPLX | M5 TensorOps required, M1 benefit minimal | feed.opml eval |
| CIDER | INT8 TensorOps only on M5+ | feed.opml eval |

---

## Implementation Log

| Date | Item | Action |
|------|------|--------|
| 2026-08-09 | R-01 (Prompt trimming) | ✅ IMPLEMENTED — 233 chars removed from CRIBS_ENRICHMENT_SYSTEM (19%) |
| 2026-10-16 | First-party import resolution (BUG-875) | ✅ IMPLEMENTED — NOT a research candidate but a rail this register's "is it drift-proof?" column kept asking for: `config/repo_integrity.yaml#import_resolution` + `scripts/check_repo_integrity.py` (RAIL 0) now DERIVE every first-party top-level name from disk and fail closed when one resolves OUTSIDE the tree, naming the capturing distribution. 3 new two-sided known-answer controls (17 → 20). Measured RED naming `skillopt-0.1.0`, then GREEN. |
| 2026-10-17 | Harness session-surface staleness (BUG-873 limb b) | ✅ **MEASURED — it RETIRES a candidate, not adds one.** `sessions.extension_data` in `~/.local/share/goose/sessions/sessions.db` is the surface a session was GIVEN and is enabled-only (verified: `pdfreader: enabled:false` is absent from it). Session `20261012_1` (born 10-12 11:22 local, still written 10-16 23:32) carries NO youtube extension and says so in its own reasoning; every session born from 10-13 11:31 does. The 13:16 write is NOT the enabling — the `extensions:` block is byte-identical to the 10-15 21:08 backup and 13:16 changed `GOOSE_THINKING_EFFORT` only. ⇒ **a config write is not live until a NEW session starts.** Constraint for any rail: `enabled_extensions.v0` exists only for sessions born from 10-13, older blobs record the surface NOT AT ALL, and substring search inside them is contaminated by todo prose. |
| 2026-10-17 | Grounded `ask` (knowledge layer as everyday advisory) | ⬜ **GAP MEASURED, NOT YET CLOSED.** The corpus is queryable (7,640 FBs, FTS + sqlite-vec in the DECLARED `knowledge pipeline/maxwell.db`), but `just ask` runs `pipeline/oneshot_ask.py` — a BARE one-shot call (imports `OMLX_API_KEY` only: no DB, no retriever). Until `ask` retrieves, cites and refuses when the corpus is silent, no everyday decision can be grounded in the knowledge layer. |
| 2026-08-09 | R-03 (llmfit preflight) | ✅ ADDED to just preflight |
| 2026-08-09 | R-02 (Structured JSON) | ⬜ PENDING A/B test |
| 2026-08-09 | R-07 (Merged CRIBS+Classify) | ⬜ PENDING A/B test |


---

## Exhaustive competitor / alternative sweep for "make Maxwell OS engineering faster, less hallucinatory, more accurate" (OWNER-APPROVED 2026-09-26; home widened by widening_log entry 14)

**Scope (the owner's definition):** everyday Maxwell OS engineering - fixing bugs, writing rails/scripts,
engineering the pipeline's *code*, skill orchestration. NOT the pipeline's own inference quality (that stays
open only if a change PROVABLY raises quality).

**The question this sweep answers:** is there an EXISTING solution that improves it, and if so which one.
**Decision rule applied to every row (the house gates, not preference):** a RAIL beats a MODEL for accuracy
(deterministic > probabilistic for anything a rail can decide); C1 $0 marginal; C3 sovereign/local;
C2/C4 no single closed model family, no vendor lock-in; C21 swappable behind a protocol; C25 agent-agnostic;
prefer ALREADY-INSTALLED over a new dependency. Evidence tiers are marked, because a recalled claim is not a
measurement: **[M]** measured on this machine | **[D]** read from disk/config/repo metadata | **[K]** engineering
knowledge, NOT verified here (must be verified before adoption).

| # | Class / candidate | Verdict | Tier + why |
|---|---|---|---|
| 1 | **Grammar / structured decoding** - `outlines` + `pydantic` present; Ollama 0.34.2 `format: <json schema>`; `xgrammar` ABSENT | **ADOPT (first)** | [M] dependencies measured present. The single biggest accuracy/tool-calling lever for the S4/menu-routing chores, and it costs no new dependency. `xgrammar` only if benchmarked. |
| 2 | **Prefix/prompt caching + speculative decoding** - `mlx_lm.generate --prompt-cache-file`; draft-model speculation | **ADOPT behind a config flag** | [M] the capability exists in the installed `mlx_lm`; the 1.5-2.5x speedup itself is [K] LITERATURE, NOT measured here - adopt behind a flag, then measure on the eval rail (row 10). |
| 3 | **Typed-decision / verifier arms** - laya-mlx, CLM (Contrastive-LM/CLM, CLM-8B), Jev-class heads | **WATCH-LIST, not adopt** | [D] `config/bakeoff_laya.yaml` role=labeler, phase_a=feasibility, `imports_in_production_code:false`; the arm is a STUB (`arm_typed_head()` raises NotImplementedError) so it has never produced a number. [D] CLM is the same lineage: a typed decision head over a CALLER-SUPPLIED criteria vocabulary; an 8B Qwen3 encoder served by vllm = no Metal/MLX path (breaks C1/C3), repo 3 days old, self-reported benchmarks. Its real claim is VERIFIER on agentic coding - which is row 9's loop, and it is still gated by D-300 + Phase B (D-317). |
| 4 | **Verification COVERAGE (NLI)** - DeBERTa-v3-large, fail-closed | **EXTEND COVERAGE** | [D] "less hallucinatory" in a pipeline is coverage of verification, not model IQ. Swapping the verifier is C2/C4 risk; extending what it covers is free and monotone. |
| 5 | **Agent frameworks** - LangGraph, CrewAI, AutoGen, OpenAI Agents SDK, smolagents | **REJECT** | [D] goose + MCP already provide the loop and the tool surface (C25); a framework would be a second orchestration home (the D-2646 one-home rule) plus future tax (C27). |
| 6 | **Hosted workspaces** - Notion (the notion.site link), cloud agent platforms | **REJECT** | [M] HTTP 200, `<title>Notion</title>` - a marketing/workspace page, not a model or library; and hosted = C3/C1/C2 violations by construction. |
| 7 | **Local inference servers** - OMLX (incumbent) vs vLLM vs llama.cpp vs Ollama | **KEEP OMLX** | [D] Metal/MLX-native, already serving the generator; moving would trade a $0 sovereign stack for a portability claim Maxwell does not need. |
| 8 | **Deterministic codegen scaffolds** - libcst / ast-grep / `ast` + templates instead of asking a model to patch a script | **ADOPT as method** | [K] this is the house rule already ("the fix must be a rail, not a prompt") mechanized; needs one installed-check before use. |
| 9 | **Agentic-coding eval harnesses** - SWE-bench Verified, Terminal-Bench, DeepSWE, plus CLM's claimed 87.6/81.6 | **ADOPT as METHOD, not as a leaderboard** | [K] the harness idea is right and the numbers are self-reported; what matters is row 10. |
| 10 | **A per-capability EVAL SET for everyday engineering** (30-50 golden tasks: a rail to fix, a config to edit, a bug to root-cause) | **THE MISSING PREREQUISITE - ADOPT FIRST AFTER row 1** | [M] ABSENT on disk. Without it "faster / more accurate / less hallucinatory" is UNMEASURABLE, and every claim in rows 2, 3, 8, 9 is unfalsifiable. This is the acceptance test for everything else in this table. |
| 11 | **Prompt-optimization tooling** - DSPy, guidance, LMQL; `promptfoo` (present, 1 owed artifact) | **DEFER to row 10** | [D] promptfoo config is an open debt; compiling prompts without an eval set optimizes nothing measurable. |
| 12 | **Observability** - Langfuse / Phoenix (hosted) vs the local `METRICS.jsonl` + measure --gaps | **REJECT hosted / KEEP local** | [D] 321 metric records with floor/ruler/denominator already carry what an external tool would add, locally. |
| 13 | **Static enforcement for the fleet** - pyright/mypy/ruff gate on C17's "type hints on all signatures" | **CANDIDATE (cheap, verifiable)** | [D] C17 is a DECLARED rule with no rail enforcing it - the BUG-492 shape ("a rule in a message is not a rule"). A repo-wide type gate is deterministic and would catch the sentinel-default class of defect that hit BUG-535 in-flight. |
| 14 | **Recurrence detection over the buglog/decisions** - cluster root causes so a FAMILY cannot be fixed one member at a time | **CANDIDATE (the anti-treadmill lever)** | [M] BUG-526/528/531/533/536 are ONE family ("enforcement by name, not identity; an abort hides its successors") and were fixed as five separate incidents. A rail that names the family at the second occurrence is the cheapest available protection against going in circles. |

**Honest limit of this register:** rows are CLASSIFIED and the decision rule is fixed; the [M]/[D] rows were
verified on this machine, and the [K] rows are explicitly marked as NOT verified here - a per-candidate web
sweep (current alternatives, licenses, benchmark provenance, and whether a candidate duplicates an installed
capability) is the REMAINING WORK, not a claim made here. Retrying the entry shape that was recorded as a
NEGATIVE RESULT (a reconciliation entry pointing at a JSON/markdown register) is forbidden (BUG-534).

**Not adopted, and why (one line each):** CLM = 8B + vllm, no Metal path, 3-day-old self-reported benchmarks,
gated by D-300/Phase B -> WATCH. laya-mlx = labeler head, zero scaffolding surface, arm never run -> WATCH.
Notion = hosted workspace -> REJECT. Apple FM = see `config/apple_fm.yaml` (enabled:false, arms:[]) -> GATED
ON MEASUREMENT, verdict in the buglog's BUG-538 discussion; it is an ARM for schema-shaped chores, never a
generator (C2/C4) and never a verifier (S5 stays DeBERTa, D2298).

---

## 🧩 REA Reverse-Engineering Targets (closed-source only — open source is read directly)

Decision (2026-10-13): REA is for CLOSED artifacts where source is unavailable. For open-source
targets (LlamaIndex, Instructor, Docling, RAGChecker/Ragas/BGE-M3, Argilla, RAGFlow, DSPy) read
the repo directly — REA would return decompiled/minified approximations WORSE than the source.

| Tier | Target | REA entry | Feature to mine -> Maxwell |
|------|--------|-----------|----------------------------|
| MUST | DEVONthink 3 (native macOS) | native + Apple bundle anatomy | related-document ranking ("See Also"/"Classify") -> replaces dead borp_score |
| MUST | Cursor (Electron) | analyze-javascript/electron | semantic code-search + derived codebase index (+12.5% acc) -> scout-lane derived index |
| SHOULD | Notion (Electron client) | analyze-javascript | retrieval/index surface (partial; server core inaccessible) |
| NOT WORTH | Glean / Perplexity / Elicit / Consensus | web JS bundle only | server-side engine inaccessible -> use blogs/whitepapers |

Open-source targets are QUEUED (P4, after P0-P3): LlamaIndex content+config cache invalidation,
Instructor typed response contract, Docling layout/table order-aware recovery, RAGChecker/Ragas/
BGE-M3 retrieval-quality baseline.


## FRONTEND/AGENT-DESIGN TOOLS ASSESSED 2026-10-13 (owner-asked) - REFERENCE ONLY, not adoptable

| repo | what it is | verdict for Maxwell OS |
|---|---|---|
| pbakaus/impeccable | design guidance skill for AI coding agents: 1 skill, 24 commands, live browser iteration, **59 deterministic detector rules** for AI-generated frontend design | **NOT ADAPTABLE** (Maxwell OS has no UI surface). Two MECHANISMS borrowed into specs/README.md: a durable product-truth file read before any change, and a BOUNDED set of deterministic detectors with the LLM layer strictly advisory |
| shadcn-ui/lint | agent-first linter for Tailwind design systems: you declare what is allowed, and a violation explains the problem and SUGGESTS a fix derived from your own components and theme | **NOT ADAPTABLE** (React/Svelte/Vue design systems). One MECHANISM borrowed: every failure must NAME ITS DERIVED REMEDY, not merely fail - now rule 5 of the spec/test sandbox |

Both are recorded here so the question is answered ONCE instead of re-asked per session, and both are referenced
from specs/README.md (the sandbox charter) where the borrowed mechanisms are stated as rules.


## OWNER'S DESKTOP INDEX ASSESSED 2026-10-16 (owner-asked) — REFERENCE ONLY, NO CONSUMER

| tool | what it is (MEASURED on this machine) | verdict for Maxwell OS |
|---|---|---|
| DigUp 0.6.1 (com.abdurrahim.DigUp, ARahim3/DigUp) | an on-device semantic search panel (hotkey + LSUIElement) over the owner's chosen folders; embeddinggemma-2-Q8_0 GGUF (309,855,456 B) + a multi-modal projector (554,821,024 B) on llama.cpp b11461; index.sqlite ~242 MB + a separate code index; word and meaning lanes answering in ~120-640 ms, first query after a 7.5 s model load; Sparkle auto-update ON | **ACCEPTED AS THE OWNER'S FRONT DOOR, NO CONSUMER IN THE OS.** Nothing in the scaffold, the tools, the skill orchestration or the knowledge pipeline reads it: it exposes no callable interface, its version floats with its own auto-update, and its index is derived, un-stamped and unreproducible (BUG-868, D-3052). Its MODEL is a hashable GGUF and is recorded as REACHABLE for a future multi-modal arm ONLY as its own declared vector space — never mixed into bge-m3's store or dimension. REFUSED explicitly: an agent-facing wrapper, an MCP surface over the GUI, an index-of-the-corpus read from it, and any placement decision informed by its meaning search (D-2898: a topic is never decided by a model or a heuristic; BUG-864). |

The admission plan (`governance/ADMISSION_PLAN_<date>.md`, D-3051) is built to be worked FROM this panel: 244
candidate works and 1,741 pen files need the owner's own eye, and describing a book is how a human finds it.
Recorded here, in the register and in D-3052, so the question is answered ONCE instead of re-asked per session.

REACH RE-OPENED FOR THE RECORD (D-3054): DigUp 0.6.1 stays ACCEPTED AS THE OWNER'S FRONT DOOR / NO
CONSUMER IN THE OS. The re-open condition is written as a PIN and not a hope: a declared CLI or MCP
surface whose binary AND index are BOTH hashable, plus ONE NAMED consumer that calls it. Until all
three exist, no arm of the OS may depend on it - an unpinned surface cannot be a dependency (D-3052),
the same fault as an unpinned value (BUG-869), one layer out.

---

## EVALUATED 2026-10-16 — three candidates put to the test (D-3038: what we reject we register)

### 1. AnyJev (`nokia-applied-research/AnyJev`) — REVISED 2026-10-16: **REFUSED for labeller/classifier lanes.** The ORDER-ROTATION PROBE is adopted as a control; the METHOD is not.
- **REVISION REASON:** the first reading of this entry was written from the repo README and its public
  leaderboard placement. An INDEPENDENT third-party test was then READ (not skimmed): "Nokia Just Released a
  Free Jev Alternative (AnyJev)", Better Stack, video `hJz7zi17mXA`, transcript obtained via the
  `youtubetranscript` extension. A README is a claim; an adversarial replication is evidence. The claim did not
  survive contact with the replication, and the register is corrected before anything was installed.
- **WHAT THE INDEPENDENT TEST MEASURED** (Qwen ~8B on a MacBook, L0 vs the hosted Jev vs raw readout):
  * **order-flip rate: raw = 4% (20/500 headlines changed answer when the two options were SWAPPED);
    L0 = 0.** Position bias is REAL and dramatic in the raw readout (one headline read 1% satire with one
    ordering and 99.8% with the reverse); L0 returned the same answer both ways. **This is the one claim that
    replicated, and it replicated completely.**
  * **accuracy: Jev ~12 points MORE accurate than AnyJev.** AnyJev does not catch up to the purpose-built
    decision model.
  * **sequential round (one item at a time, so `content_free_prior` is forced): AnyJev 60%, raw 80%, Jev 90%.
    AnyJev LOST.**
  * **the failure mode, and it is the one that disqualifies it here: removing a lean OVERSHOOTS when the MIX of
    answers changes.** With an even 50/50 mix the content-free correction TRADED AWAY satire answers the raw
    model had RIGHT and won back none (66.6%, two points below its own point estimate). The correction is
    estimated FROM THE BATCH, so the ruler moves with the corpus.
  * **calibration: L0's error is 0.3, essentially the same as raw.** The docs say so themselves: L0 removes
    BIAS, not calibration. 87% of raw answers arrived at >=99% confidence and were wrong on 30% of those. The
    levels that DO calibrate need a few hundred LABELLED examples - which contradicts "no training" for the
    mode worth having.
- **WHY THAT IS DISQUALIFYING FOR US, ontologically rather than by taste.** A debiaser whose correction is
  estimated from the batch makes the DECISION DEPEND ON THE CORPUS MIX. Maxwell OS's standing rule is
  drift-proof, do-not-mutate: a labeller whose answer changes when the surrounding batch changes is a labeller
  that DRIFTS BY CONSTRUCTION. It cannot sit under an eval-integrity floor, and it cannot be an S2/S4
  classifier on the current labels (session_seed `do_not`: no provenance column exists). And a probability that
  is not calibrated cannot be used where a floor is expressed in pp.
- **WHAT IS ADOPTED (token, not tool): THE ORDER-ROTATION PROBE.** Permute the option order, ask again, count
  flips. It needs no model swap, no new dependency and no licence - and the independent test shows it catches a
  real defect that ours could not see: raw readouts flip on 4% of items. NO MAXWELL OS RAIL MEASURES THIS TODAY.
  Registered as a candidate control against the S3/S4 classification path.
- **Status: REFUSED as a labeller for governed lanes. Not installed. `pip install anyjev` is NOT a step.**
- **What it actually is:** a training-free READOUT/PROTOCOL layer that turns an EXISTING local model into typed
  decisions with real probabilities (`state`/`question`/`options` -> `answer`, `probs`, `route`). It is not a
  labeler and not a generator: it WRAPS a model we already serve. Apache-2.0, Python, `pip install anyjev`,
  runs on transformers / in-process vLLM / `vllm serve`. arXiv report 2610.00831. Its own self-distilled
  models ("Tacit", 1.7B-9B, one forward pass per decision) are a separate download.
- **Community evidence cited (a CLAIM, not a control):** order-flip rate 0.230 -> 0.073 and accuracy
  0.747 -> 0.803, auto-decidable at 5% risk 7.7% -> 46.3% (Qwen3-8B, BANKING77-20, raw readout vs L0); the
  training-free L0 Decider on UNCHANGED Gemma-4-31B scores 60.22 on the public Decision Index 0.3
  (5th of 149 entries, 2026-10-12). Numbers measured on THEIR benchmark, not on Maxwell OS's frozen ruler.
- **Why it is NOT "better or worse than Laya":** the two objects do not answer the same question. Laya is a
  benchmark-only ARBITRATION arm (`config/bakeoff_laya.yaml`: role `labeler`, `enabled: false`, bar D-300
  ">=5.0 absolute pp error-rate gain on the frozen ruler at equal-or-lower abstention", Phase B blocked on
  F-11 second coder, `imports_in_production_code: false`). AnyJev is a readout over whatever model we already
  run, and could WRAP Laya. Comparing their headline numbers would be comparing a ruler to a reading.
- **The one thing here that is NEW to us, and it is not the accuracy figure:** Maxwell OS has NO rail that
  measures whether a label SURVIVES A PERMUTATION OF ITS OPTIONS. An order-flip rate is exactly the
  drift/stability control the standing rules ask for and none of our 60+ checks implement. The 5%-risk
  auto-decidable share is the same abstention axis D-300's bar is phrased in.
- **Condition to proceed (fail-closed, same ruler):** enter as a SECOND ARM of the existing laya bakeoff -
  same frozen ruler, same D-300 adoption bar, same single-coder caveat (F-11) - never on community numbers.
  Revisions must be PINNED (D-382/R14). Engine friction to weigh: transformers/vLLM-oriented, NOT MLX-native,
  while this host's local stack is MLX.
- **Status: registered as a candidate arm + one candidate new rail (order-flip control). Nothing installed.**

### 2. `desert-ant-labs/title` — REFUSED on three independent grounds.
- **(a) Licence.** Card: `license: other` / `license_name: desert-ant-labs-source-available-1.0` /
  `license_link: https://license.desertant.com/1.0` — SOURCE-AVAILABLE, not open source. It cannot enter a
  $0-marginal, sovereign, no-lock-in stack (C1/C2/C3); D-322's treatment of a checkpoint with an advisory-only
  licence is the precedent.
- **(b) Task mismatch.** It "suggests a title and description for any text" — GENERATION. Maxwell OS's title
  NORMALISATION is DETERMINISTIC (`pipeline/book_metadata.py#normalize_title`: NFKC->NFKD, combining marks
  stripped, `_SPACE_SUBTITLE_SPLIT`), and D-2898 forbids a model from deciding a canonical/topic. Replacing a
  deterministic normaliser with a generator would be a REGRESSION of an already-decided rule.
- **(c) No control.** 10 likes / ~29.9k downloads / 2026-08, 286 MB (`GraniteMoeHybridForCausalLM`), no
  Maxwell OS measurement. A floating release is not a dependency (D-382/R14).
- **Status: REFUSED. Do not re-propose without a licence change AND a deterministic-interface argument.**

### 3. `divinetribe/Hermes-4-14B-abliterated-4bit-mlx` — REFUSED for every GOVERNED lane.
- **Licence is fine** (apache-2.0) — the refusal is not about licence. It is about provenance and purpose.
- **(a) Provenance is one ungoverned hop deep.** `base_model: Babsie/Hermes-4-14B-BF16-abliterated` (itself
  already abliterated), derived from NousResearch Hermes-4-14B (a Qwen3-14B derivative). The upstream that
  released THESE weights never published them; R14 requires every persistent object to be stamped with its
  `gen_model`, and a weight edit with no release note cannot be stamped.
- **(b) Its defining edit removes a REFUSAL DIRECTION** (tags: `abliterated`, `uncensored`). The lanes it was
  proposed for — verification, classification, fail-closed gates — exist TO REFUSE (S5/D2298). A lane whose
  job is refusing must not run a model edited to refuse less.
- **(c) Redundant against the declared roster.** Tool calling / one-shot already has
  `AGENT_TOOL_SHORT_ONESHOT -> Qwen3-Coder-30B-A3B-Instruct-MLX-4bit`; classification has
  `CLASSIFIER_S4 -> gpt-oss-20b-MXFP4-Q8`. A 14B dense 4-bit adds a new `harness_roles` entry, a parity
  check and a bench, and buys nothing the roster lacks. 5 likes / 1,078 downloads / 2026-05.
- **Status: REFUSED for governed lanes. Not installed. If ever wanted for OFF-LANE drafting, that is a
  separate proposal with its own reason — an off-lane use does not license an on-lane one.**

| 2026-10-17 | Sub-agent loop, per model (D-2549/T-131) | ✅ **MEASURED - and it RETIRES a claim.** `scripts/measure_subagent_loop.py`: one fixed 3-call tool loop, same generated fixture, temperature 0.0, every SERVED model, budget read from `ratified.knobs.per_turn_budget_s` (90 s). **7/8 PASS**; Phi-4-mini FAILS with 0 tool calls (answers from memory - BUG-053 on a loop). Two `never_for` strings in model_assignments.yaml were false as written and are corrected. ⇒ "only gemma can drive a loop" is RETIRED. |
| 2026-10-17 | Plugin/MCP market sweep (the register's named REMAINING WORK) | ✅ **ANSWERED** by `governance/evidence/PLUGIN_SURVEY_20261017.md` (23 searches, each third-party claim with its URL, aligned against 19 already-REJECTED items so nothing is re-proposed). ADOPT ruff+mypy as the C17 rail; TRIAL ripwire (pinned, read-only) against the measured excerpt weakness; REFUSE the conversion/ebook/memory plugin classes as second homes. |
| 2026-10-17 | Extension residency / extension rot (owner's question) | ✅ **DECIDED - D-3056.** `config/extension_profiles.yaml` classifies all 26 declared extensions (10 always / 8 on_demand / 8 never, totality enforced as a FAULT not a silence); `scripts/measure_extension_cost.py` measures what residence costs by spawning each server (37 stdio tool schemas = 31,636 B ≈ 7,909 tok/request); `scripts/goose_profile.py --check` compares policy to live state (0 agree / 1 fault / 2 owner-owed; 9 resident against policy today). The switch is the harness's own `--no-profile`, measured two-sided. |  |
| 2026-10-17 | Plugin verdicts (the row above, converted) | ✅ **REGISTERED - D-3057.** The survey is now a register of verdicts: ADOPT ruff+mypy rails and mcp-read-pdf (repaired, on_demand); TRIAL ripwire pinned/read-only against the measured excerpt truncation; REFUSE document-conversion, ebook/bibliography, byte-equality dedup, filesystem watch and second-home memory/SQL surfaces. The gap found is WIRING (`just ask` grounding), not a download. |  |
| 2026-10-17 | Local tool-calling roster (owner's question) | ✅ **DECIDED - D-3058, with one test still owed.** "Only gemma can tool-call" is RETIRED by the D-2549 measurement (7/8 served models drove a 3-call loop). Two candidates named and NEITHER promoted: MiniCPM5-2B (fastest, 131k) and Ornith-1.5-9B (262k). Qwen3.5-9B has no measured use and its name is retired everywhere; llmfit's top pick (DeepSeek-R1-0528-Qwen3-8B) is REFUSED - a hardware-fit score is not a loop measurement. T-187 owes the two-step/two-tool discrimination. |  |
| 2026-10-17 | llmfit's capability tags vs a MEASURED loop (the owner's "market research with llmfit") | ❌ **THE TAGS ARE INVERTED ON THIS ROSTER.** llmfit 0.9.38 carries 5,103 models and tags 1,259 `tool_use`, but of the models this machine SERVES only ONE carries the tag: Qwen3-Coder-30B-A3B (the SLOWEST loop driver measured, 79.9 s, DELEGATE-002). `gemma-4-E4B` is tagged `caps=[]` and `MiniCPM5` is tagged `caps=[]` - the two fastest models that actually completed the 3-call loop (14.3 s and 2.1 s). Filtering `tool_use` and <=16B outside merges/repacks returns TEN entries, every one a `tiny-random`/testing repo. Its top recommendation (DeepSeek-R1-0528-Qwen3-8B, score 95.3) is a hardware-FIT score at an 8,192-token estimate. ⇒ llmfit is usable as a HARDWARE-FIT oracle and NOT as a capability oracle; D-3058 stands, and T-187 is the only instrument that can rank a loop. |  || 2026-10-17 | llmfit's capability tags vs a MEASURED loop (CORRECTION of the row above) | ⚠️ **THE CLAIM WAS TOO STRONG; THE CONCLUSION SURVIVES.** The tag is PER-REPO and a quantisation DROPS it: `google/gemma-4-E4B-it` carries `['vision','tool_use']` while six quantised variants - including the served `MLX-4bit` - carry `caps=[]`. So "gemma-4-E4B is tagged caps=[]" was true only of the variant, and "MiniCPM5 is tagged caps=[]" was an ABSENCE misread as a tag: MiniCPM5 is not in the catalogue at all. ALSO MEASURED: FOUR of the eight served models are absent from llmfit entirely (MiniCPM5-2B, Ornith-1.5-9B, Ornith-1.5-35B-A3B, Qwen3.8-27B), so the fit oracle covers HALF this roster. What survives unchanged: on the repos this machine serves, the only `tool_use` tag belongs to the SLOWEST loop driver (Qwen3-Coder-30B, 79.9 s). ⇒ llmfit remains a FIT oracle, not a capability oracle - now with its coverage and its tag mechanics stated. D-3061. | temp/llmfit_fit.json |
| 2026-10-17 | Qwen3-Coder-class models faster/better at tool use, and "is there a capability oracle" | ✅ **DECIDED (D-3061): DOWNLOAD NOTHING THIS CYCLE, and the oracle question is answered by a declared ladder.** (a) No drop-in FASTER model exists in this class on this hardware: Qwen3-30B-A3B-Instruct-2507 is the same 30.5B MoE shape and llmfit estimates the IDENTICAL 59.3 tok/s at its 8192-token cap - while the model it would replace measured 79.9 s for a 3-call loop. Speed comes from the SHAPE (3B active), which we already own, and the models that beat it on a loop (MiniCPM5-2B 2.1 s, Ornith-9B 11.5 s) are already served. (b) The catalogue's own top-50 of `tool_use` + fits + <=40B is 32 distinct families in 50 rows, 20 distillation repos, and FIVE quantisations of the same #1 (DeepSeek-R1-0528-Qwen3-8B) - a REASONER, the worst loop shape, since it spends tokens before a tool call. A duplicate-inflated, distill-inflated, reasoner-topped ranking is not a shortlist. (c) The only real upgrade path is QUALITY at equal speed: Qwen3-30B-A3B-Instruct-2507 publishes BFCL-v3 65.1 and tau2-retail 57.0 with long-context retention 89.1 avg at 128k vs 76.9 for the old 30B-A3B - a candidate, gated on T-187 and priced at 30.5 GB. (d) ORACLES: only `measure_subagent_loop` gates a promotion; llmfit is fit-only; BFCL / tau2-bench / SWE-bench-Verified are PRIORS. Refused as evidence: parameter count, catalogue tags, card prose, vendor demos, estimated_tps-as-loop-time. | config/model_oracles.yaml; governance/evidence/LLM_CANDIDATE_20261017_Qwen__Qwen3-30B-A3B-Instruct-2507.json |
| 2026-10-17 | Session/extension model — mid-session profile switching vs task-labelled sessions (owner's question) | ✅ **ANSWERED BY ONE MEASURED ASYMMETRY, not by preference.** The two switches are not equivalent: `enabled:` is read at BIRTH (BUG-873 limb b, proven from `sessions.db`), and the only runtime switch (`extensionmanager.manage_extensions`) advertises **`disable` + `install`** — it can SHED a tool, never GAIN one. So mid-session switching is a ONE-WAY DOOR and cannot be the primary mechanism: **the act labels the session and the profile is chosen at birth**, which is what `config/extension_profiles.yaml` already declares (workshop / research / documents / recall / web / sandbox / everything, plus delegate profiles review / sweep / extract). Continuity is not lost, because this OS's memory is the REGISTERS AND RECEIPTS (`memory` is always resident, `chatrecall` is on-demand, and the handoff/decision/bug registers are the durable record — D-3036), and a NEW session is cheap when its opening bytes are stable (25.01x prefix cache, BUG-872). ONE lever left, now declared: `core` (the `always` set alone) — switching the default frees **5,633 tok/request** (filesystem 3,727 + gitmcp-mcp 1,906, both duplicating `developer.shell`), and it is an OWNER act because it edits the harness home and takes effect in the NEXT session. |
| 2026-10-17 | "2507" — what the D-3061 row actually names, and what it is NOT | ⬜ **CLARIFIED; STILL NOT A PURCHASE.** The candidate is **Qwen3-30B-A3B-Instruct-2507** — the *Instruct* MoE, a DIFFERENT model from the generator this pipeline runs (**Qwen3-Coder-30B-A3B-Instruct-MLX-4bit**); "2507" is a release-date suffix, not a version of the coder. Its numbers (BFCL-v3 **65.1**, τ²-retail **57.0**, long-context retention **89.1 avg @128k** vs **76.9** for the older 30B-A3B) are EXTERNAL published priors — `machine_truthful: false` in `config/model_oracles.yaml`, i.e. they may decide what is worth DOWNLOADING and may never gate a promotion. The claim is **quality at equal speed**, not more speed: the shape is the same 3B-active MoE and llmfit estimates the IDENTICAL **59.3 tok/s** at its 8192-token cap. **30.5 GB** is the priced fit, not a purchase, and nothing was downloaded this cycle. The gate is T-187's two-step/two-tool fixture — a single 3-call read does not rank a model. |
| 2026-10-17 | pstack (cursor/plugins) + its explainer video — "adapt, reference or integrate?" | ⬜ **REFERENCE + PARTIAL ADAPT; REFUSED AS A BUNDLE.** pstack is 54 skills / 23 playbooks / 2 agents / 24 principles, MIT, manifest on the `agent-plugins.org` (Open Plugins) schema. MEASURED: installing it wholesale adds **2,676 description tokens to EVERY request** (54 frontmatter descriptions; 48,269 tokens of content on demand) — half the extension tax just removed, for skills that would then need keeping in sync with our own decisions. Four ideas are worth porting as OUR OWN single skills: `prove-it-works` (demonstrate an artefact, never assert it), `benchmark-checklist` (vet a number: limiter, repeats, end-to-end — this is D-3061's ladder in plain words), `deslop`/`unslop` (C12/C19/C20 as a procedure), `interrogate` (N models try to break a diff — R5 done properly). REFUSED: the `poteto-mode` 23-playbook router (a second routing surface beside `resolve_route`/`capability_registry` = two homes for one decision), and the Cursor-specific fleet (C25). The YouTube link is the same artefact, not a source. | governance/HANDOFF_20261016_LANES_AND_MEASUREMENT.md#1f
| 2026-10-17 | "can llmfit check ALL HuggingFace models, and is there anything better — including in OMLX?" | ✅ **NO, IT CANNOT, AND THE HARNESS ALREADY HAS THE BETTER DISCOVERY TOOL (used for the first time 2026-10-17).** llmfit is a FIT oracle over a bundled catalogue (5,103 models, `llmfit update` refreshes it) plus `hf-search` — **GGUF only**, i.e. the format this machine does NOT serve. Its roster coverage is 4/8 and its `estimated_tps` is an 8,192-token-cap model (D-3061). `goose local-models search "<query>"` returns LIVE HuggingFace results for **GGUF *and* MLX**; MEASURED: 8 MLX repos for "Qwen3-30B-A3B MLX 4bit", including `Qwen3-30B-A3B-Instruct-2507-MLX-4bit` (lmstudio-community) and `mlx-community/Qwen3-30B-A3B-Instruct-2507-4bit` — the D-3061 candidate IS available in MLX 4bit; nothing downloaded. Caveat from the tool's own output: `MLX support was not compiled in`, so it can FIND MLX but `local-models download` is GGUF-only (a fetch stays `hf`/`huggingface-cli`). OMLX itself is a SERVING surface (`/v1/models` max_model_len, `~/.omlx/model_settings.json`, `stats.json#total_requests`) and knows nothing about HuggingFace. ⇒ discovery has an owner now; the ladder is unchanged: discover → FIT → PRIOR → **MEASURE THE LOOP** (the only gate). | `goose local-models search`; config/model_oracles.yaml
| 2026-10-17 | goose's own plugin + hook surfaces — are they useful for extension profiles? | ✅ **YES, AND ONE OF THEM IS THE TRIGGER T-190 SAID WAS MISSING.** (a) PLUGINS: `plugin.json` + `skills/` + `hooks/hooks.json`, formats Open Plugins or Gemini extensions, discovered from `~/.agents/plugins/`, installed with `goose plugin install <git-url>` (`--auto-update` rate-limited), disabled via `disabledPlugins` in `~/.config/goose/settings.json`. A plugin is a DISTRIBUTION container — worth it only for anything we intend to share; it grants no residency. (b) HOOKS: `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PreToolUseResult`, `PostToolUse`, `PostToolUseFailure`, `BeforeReadFile`, `AfterFileEdit`, `BeforeShellExecution`, `AfterShellExecution` — with `on_failure` policy and payload on stdin. **`SessionStart` is the birth receipt, and `PreToolUse`/`PostToolUse` are the toggle receipt** T-190 owes (the toggle is model-driven, so the trigger must be the tool call, not a config diff). NOT YET BUILT: the hooks themselves. | `goose-docs.ai/docs/guides/context-engineering/plugins`, `/hooks`; `goose plugin --help`
| 2026-10-17 | "who picks the extension profile — the LLM/agent, or me by hand? do I keep one session per profile?" — cross-examined against Claude Code, Gemini CLI and the tool-retrieval literature | ✅ **NOBODY PICKS: THE SYSTEM RESOLVES, AND SPECIALISATION MOVES TO WORKERS (D-3065).** Peer evidence, READ not recalled: Anthropic's Agent Skills preload only `name` + `description` and read the body on demand (progressive disclosure); Anthropic's engineering posts state that loading all tool definitions upfront is what "overloads the context window" and that agents scale by NOT doing so (Sep 11 2025 / Nov 04 2025); Claude Code's own docs say each subagent runs "in its own context window with a custom system prompt, **specific tool access**, and independent permissions", that Claude delegates by matching the subagent's DESCRIPTION, and that it WARNS when non-builtin subagent descriptions exceed **15,000 tokens** (measured text, docs.claude.com/en/docs/claude-code/sub-agents). Gemini CLI's `extensions` are a distribution/install surface (`gemini extensions list/install`) — the same lesson as goose plugins: packaging ≠ residency. The academic line is consistent and is about RETRIEVAL rather than static sets — arXiv 2025-03-03 "Retrieval Models Aren't Tool-Savvy: Benchmarking Tool Retrieval for LLMs", plus 2026 set-level and budget-aware tool-retrieval work — i.e. picking the right tools per task is a studied problem, which is exactly why a HAND-MAINTAINED profile list is the wrong owner. ⚠️ NOT VERIFIED THIS SITTING: Codex's `config.toml` profile mechanism (the config doc fetch returned nothing), so it is cited as evidence neither way. ⇒ Confirms D-3065: deterministic resolution at birth, a `core`-cheap default, delegation for depth. The peer gap we do NOT close yet is true progressive disclosure — MCP tool schemas are static per session in goose, so `core` + delegate is our faithful approximation. | docs.claude.com/en/docs/claude-code/sub-agents; anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills; anthropic.com/engineering/code-execution-with-mcp; export.arxiv.org |
| 2026-10-17 | THE CANDIDATE REGISTER — "is there a HuggingFace model worth fast-tracking for the agent workload, and what decides between them?" (owner's question, after DELEGATE-002 was retired) | ⬜ **SIX NAMED, NONE PROMOTED, ONE INSTRUMENT OWED — and the instrument, not the roster, is the blocker (T-187).** Every entry carries a STATE and the reason it has it; none carries a slot. **(1) Qwen3-30B-A3B-Instruct-2507** — 30.5 GB, the same 3B-active MoE shape the pipeline already runs, so its claim is QUALITY AT EQUAL SPEED, not more speed: published BFCL-v3 65.1 / τ²-retail 57.0 / long-context retention 89.1 avg @128k vs 76.9 (PRIORS, `machine_truthful: false`). Available in MLX 4-bit (lmstudio-community + mlx-community seen 2026-10-17); reach: AWQ 213,667 downloads, MLX builds 20,277 + 12,861 — reach is not evidence. NOT the coder: "2507" is a release suffix. **UNMEASURED.** **(2) Devstral-Small-2-24B-Instruct-2512** — 15.1 GB dense, agentic-CODING lineage (SWE-bench), MLX 4-bit 11,130 downloads. Its lane, if any, is code work and review, never the pipeline generator (a dense 24B is outside the 3B-active cost model). **UNMEASURED.** **(3) Hermes-4-14B** — function-calling tuned, but the only MLX build found is an ABLITERATED derivative one ungoverned hop deep (upstream a Qwen3-14B derivative): a provenance that cannot be stated is not admissible into a stamped lane. **REFUSED.** **(4) granite-4.0-h-small** — ~5 GB, 185 downloads, no published loop numbers: present because it is CHEAP TO MEASURE, not because it is promising. **UNMEASURED.** **(5) GLM-4.5-Air** — 106B, outside the ~24 GB delegate budget, so it cannot be measured on this machine at all: a candidate that cannot be measured is not a candidate. **REFUSED.** **(6) "only gemma can do multi-turn"** — already REFUTED by D-3058 (7/8 drove a 3-call loop) and retired in this register's D-3058 row. **WHAT DECIDES BETWEEN THEM IS NOT A BENCHMARK AND NOT A DOWNLOAD COUNT:** `scripts/measure_subagent_loop.py`'s TWO-STEP / TWO-TOOL fixture — two tools with a DISTRACTOR, two DEPENDENT steps, an expected answer only the second tool's output can produce, the same served set, and a receipt carrying TTFT and DECODE RATE per step (T-187). A single trivial read ranks nothing: it passed a 2B model. Until that fixture lands, `AGENT_LOOP_FAST` / `AGENT_LOOP_WORKHORSE` stay undeclared and nothing is downloaded (D-3061). | config/model_oracles.yaml; governance/evidence/LLM_CANDIDATE_20261017_Qwen__Qwen3-30B-A3B-Instruct-2507.json; config/task_register.yaml#T-187 |

| 2026-10-18 | Reference sweep (owner's list): NCM, HybridAgent, Mercury, OpenAI reasoning guide — "adapt, reference or ignore?" | ✅ **ALL FOUR ASSESSED — ZERO ADOPTED, TWO TRACKED, ONE KNOB MIRRORED, ONE REFUSED.** **(1) NCM** (arxiv 2610.14162, `HazyResearch/ncm`) — **TRACK ONLY, not adopt.** No measured applicability to Maxwell's cluster-before-extract (S1.5) or convergent-FB (S2) lanes; revisit only if the FB-retrieval lane shows a measured recall gap, never on the paper's own numbers. **(2) HybridAgent** (arxiv 2610.18861, `togethercomputer/HybridAgent`) — **TRACK ONLY.** A cloud-oriented agent scaffold; on-lane use conflicts C1/C3 (sovereignty); nothing to port that D-3065 doesn't already own. **(3) Mercury** (inceptionlabs.ai, introducing-mercury) — **REFUSED as a dependency.** Speed-only headline, closed weights + cloud, conflicts C1/C3; no deterministic or ontology value. **(4) OpenAI reasoning guide** (developers.openai.com, api-mode=responses, `reasoning`) — **MIRROR THE KNOB, NOT THE VENDOR.** `reasoning_effort` (low/medium/high) is the same dial Maxwell already owns as R7 `temp=0.0` + per-lane model routing (D-2549/D-3058); the guide is advisory for *how to budget thinking per task*, never a dependency or an on-lane surface. | arxiv.org/abs/2610.14162; arxiv.org/abs/2610.18861; inceptionlabs.ai; developers.openai.com |
| 2026-10-18 | Two YouTube videos (transcript-first via the YouTube Transcript extension, now the DEFAULT for video assessment) | ✅ **ONE TRACK (directly relevant), ONE ADVISORY (non-transferable specifics).** **(1) `KZdY2a5IbOw` — "OMLX + Splash: Run MLX LLMs 5x Faster on a Mac" (Joe Maddalone).** OMLX 0.7.1-RC1 serves **Splash (Inko AI) as an external engine** → ~5x decode on the *standard* MLX Qwen3.6-35B-A3B (no custom model), via a **Dflash-2 companion draft model** (`use_external_engine=Splash` + the draft model downloaded). **TRACK: directly relevant** because Maxwell serves through OMLX (`maxwell_omlx`); this is a SERVING-SPEED optimization, not an ontology change. Action owed (advisory, NOT now): pin OMLX ≥0.7.1 stable and re-benchmark the served generator's decode when it lands — same model family, no C1/C2/C3 cost. **(2) `h_KqS4GtU3I` — "How I Got Frontier Performance on 16GB VRAM (Qwen 3.8 27B)" (Kai).** The benchmark-vs-card gap is ONE template line: `reasoning_effort=medium` receives **no instruction** (the chat template only writes text for `low` and `x-high`), so most guides silently drop ~6 Artificial-Analysis points; `x-high` is the leaderboard default. Transferable lessons (already Maxwell's shape): *treat reasoning effort as a DIAL not a fixed setting*, and *multi-token prediction is where most of the speed comes from*. **ADVISORY only**: the 16GB-NVIDIA specifics (Swift 1.5 overthinking reduction, 8-bit vs 4-bit KV-cache sizing, 250k-token windows) do **not** transfer to Maxwell's Apple-Silicon/MLX stack. | youtube KZdY2a5IbOw; youtube h_KqS4GtU3I |
| 2026-10-19 | Non-autoregressive generation family — DELTA on the owner's list (Meta LCM, DiffusionGemma 26B-A4B-it, LLaDA/ORL 2.1 mini, RTX-50 bandwidth); NCM + Mercury were already TRACK/REFUSED 2026-10-18 | ✅ **SAME FAMILY AS NCM — CONCEPT ON-TARGET, ZERO ARTIFACT RUNNABLE TODAY.** The whole family trades a little quality for a lot of decode speed via parallel / non-autoregressive generation — which is EXACTLY Maxwell's #1 measured inefficiency (delegate decode latency: Qwen3-Coder 79.9 s / 3-call loop, D-3058; cold-load TTFT 42–134 s). But the serving stack (OMLX/MLX) is autoregressive-only, and every member needs a bespoke non-AR sampler — none exists in evidence. **(1) Meta LCM** (2412.08821) — **REFERENCE.** Concept/sentence-level granularity in SONAR embedding space is the closest published analogue to Maxwell's cluster-before-extract FB granularity (S1.5), but it is an embedding-space research model with no local serving path and no MLX port. **(2) DiffusionGemma 26B-A4B-it** (google/diffusiongemma-26B-A4B-it) — **THE ONE CONCRETE OPEN-WEIGHTS CANDIDATE** (Apache 2.0; 25.2B total / 3.8B active MoE = the same 3.8B-active budget shape as the Qwen3-Coder-30B-A3B generator). **GATED, NOT ADOPTED:** (a) it is a discrete-DIFFUSION decoder (256-token canvas, EB sampler) — no OMLX/MLX serving path is confirmed; (b) its OWN card shows quality a STEP DOWN from the AR Gemma 4 26B A4B (MMLU-Pro 77.6 vs 82.6, AIME 69.1 vs 88.3, Tau2 56.2 vs 68.2) — the speed buys the drop, and Maxwell will not swap quality for speed on the generator/verifier lanes; (c) no MLX port confirmed. It enters the SAME gate as the candidate-register row above (T-187 two-step/two-tool loop + an MLX/OMLX non-AR serving path + a red-loop speed receipt vs the AR generator). **(3) LLaDA / ORL 2.1 mini** — **TRACK.** Masking-based large-language diffusion, same family; the mini variant is plausibly budget-sized, but no MLX port is confirmed and the gate is identical. **(4) RTX-50 memory bandwidth** — **NOT RELEVANT.** Maxwell serves Apple-Silicon MLX, not CUDA; a GDDR7 bandwidth table is a C24/C26 hardware-adaptive data point for a hypothetical CUDA future, never a decision now. ⇒ Nothing downloaded this cycle; the family is TRACKED as the most promising DECODE-SPEED direction, gated on a non-AR serving path + T-187 (D-3061). | arxiv.org/abs/2412.08821; huggingface.co/google/diffusiongemma-26B-A4B-it; blog.google/…/diffusion-gemma-faster-text-generation; en.wikipedia.org/wiki/GeForce_RTX_50_series |


---

## SCATTERED RESEARCH — CONSOLIDATED INDEX (2026-10-18, owner-asked aggregation)

> The owner asked "did you aggregate all tracked research potential developments from all archive and old
> project folders worth keeping?" Answer: the dated evaluation rows above were kept in this register, but the
> OLDER per-topic research docs lived scattered across `governance/`, `research/` and `governance/frontier_audit/`.
> This index is the aggregation: ONE line per scattered doc — its date, its verdict, and the pointer to the full
> receipt — so the question "what did we research, and what did we decide" is answered once, here, and never
> re-asked per session. Full docs are NOT copied in: a pointer preserves the receipt without bloat (C28).

| Doc | Date | Verdict (one line) | Full receipt |
|-----|------|--------------------|--------------|
| MARKET-RESEARCH-2026-08-09 | 2026-08-09 | Speed/accuracy sweep: continuous batching (4-8x), KV-cache prefix sharing, pipeline parallelism, merge CRIBS+classify → mostly folded into R-01/R-02/R-07 and the rejected table. | `governance/MARKET-RESEARCH-2026-08-09.md` |
| MARKET-RESEARCH-QWEN3.8-HARNESS | 2026-08-14 | Qwen3.8-27B MLX-4bit available (16.08 GB); harness landscape → KEEP goose, adopt Aider/Open WebUI/smolagents as daily drivers. | `governance/MARKET-RESEARCH-QWEN3.8-HARNESS-2026-08-14.md` |
| S4_MODEL_RESEARCH | 2026-08-30 | **Q4 vs Q8 A/B (measured, live OMLX): Q4 is 2.8× SLOWER and 31 pp LESS accurate (62.5% vs 93.8%). Keep `gpt-oss-20b-MXFP4-Q8`; no last-month model beats it.** | `governance/S4_MODEL_RESEARCH_2026-08-30.md` |
| RETRIEVAL-RESEARCH | 2026-09-02 | Retrieval stack (FTS5 + sqlite-vec + RRF + graph BFS) verified live; USearch/TurboVec/LightRAG/ColBERT/GraphRAG/RAPTOR/zvec/memvid all deferred with reason → already in R-04..R-13 + rejected table. | `governance/RETRIEVAL-RESEARCH-2026-09-02.md` |
| MARKET_RESEARCH_20260917 | 2026-09-17 | 12 method candidates (A1-A12): statistical stop-rules (2607.08522), Krippendorff's α over gold_4axis, judge datasheets (2606.15610), harness sensitivity (2605.26731), RAGChecker/Ragas recall decomposition, Argilla annotation, contamination audit (2502.14425), response normalisation, quant A/B instrument (2609.18005), DSPy re-open discipline, ImpossibleRubrics. **ADOPT as PATTERNS, not dependencies.** | `governance/MARKET_RESEARCH_20260917.md` |
| MARKET_RESEARCH_20260921 | 2026-09-21 | oMLX pin dev2 (dev4 startup bug), Lightning MTP for S2, oQ4e quant A/B, prompt-cache thrash flags (`cache.enabled:true` AND `gdn_ssd_split`), `active_provider:custom_deepseek` bug (DELEGATE-001). | `governance/MARKET_RESEARCH_20260921.md` |
| MARKET_RESEARCH_20260922 | 2026-09-22 | Engine eval: **KEEP oMLX** (only M1 engine); REJECT `splash` (M3+ gate); REJECT `turbo-fieldfare` (single model); REFERENCE `mlx-dspark` (self-calibration methodology). | `governance/MARKET_RESEARCH_20260922.md` |
| MARKET_RESEARCH_20260922_M1 | 2026-09-22 | **mlx-dspark RUNS on M1 but speculative decode is a NET LOSS (0.55–0.93×). D-332: community benchmarks outrank vendor claims.** | `governance/MARKET_RESEARCH_20260922_M1.md` |
| MARKET_RESEARCH_20260922_PIPELINE | 2026-09-22 | `nano-graphrag` MUST-REFERENCE (local graph store), LightRAG ADAPT, `fastembed-rs` reranker SHOULD, CoALA/ReAct/Reflexion as formal orchestration basis. | `governance/MARKET_RESEARCH_20260922_PIPELINE.md` |
| MARKET_RESEARCH_ONTOLOGY | 2026-09-19 | **The ontology candidates (R1-R20), the deepest scattered doc: R1 entailment/definition-anchored classification ADOPT; R3 BCTTv1 ADOPT as template; R4 inter-annotator agreement gate ADOPT; R5 label-error detection ADOPT; R6 OntoClean ADAPT; R8 SHACL ADOPT (already 60% built); R10 selective classification ADOPT; R12 PROV-O ADAPT; R13 truth discovery ADAPT; R15 QuRating ADOPT; R16 FineWeb ADOPT; R17 Saracevic relevance REFERENCE; R19 constrained clustering DEFER; R20 weak supervision DEFER.** | `governance/MARKET_RESEARCH_ONTOLOGY_20260919.md` |
| MARKET_RESEARCH_TOOL_BENCHMARK | 2026-10-06 | Knowledge-layer tool stack: `yt-dlp` acquire, `mlx-whisper` transcribe, Docling+Pandoc convert, OpenKB read-only benchmark (copy its lint rules, never a dependency). | `governance/MARKET_RESEARCH_TOOL_BENCHMARK_20261006.md` |
| MARKET_RESEARCH_20261002 | 2026-10-02 | D-2767 S4 recommendation; D-2768 **Splash is model-scoped, NOT a general GGUF runner** (Splash A/B moot); D-2771 Prism Ternary Bonsai 2 not worth testing. | `governance/MARKET_RESEARCH_20261002.md` |
| MARKET_RESEARCH_20261015 | 2026-10-15 | Delegation axis: engines (Magnitude → worth a slot, not a migration; TensorFold/PMetal/vllm-swift WATCH); models (Ternary-Bonsai-2 REFUSE fork-loader, Ornith-1.5-35B WATCH no-license, Qwen3.8-35B-A3B REFUSE 71.9 GB, LFM2.5-24B-A2B WATCH non-OSI, embeddinggemma-2 high-risk swap); harness = C25 front-end. | `governance/MARKET_RESEARCH_20261015.md` |
| RESEARCH_RUNNER | 2026-10-15 | Infrastructure, not a candidate: `pipeline/research_run.py` ends "child subagent cancelled by a new message" (6/7 lost); BUG-811 filed. | `governance/RESEARCH_RUNNER_20261015.md` |
| CHUNKING_RESEARCH (frontier_audit) | 2026-09-29 | **KEEP the current chunker** (no rip-and-replace); re-chunk verification WORKS. | `governance/frontier_audit/CHUNKING_RESEARCH_20260929.md` |
| PRIMITIVES_DEPLOYMENT_RESEARCH | 2026-10-12 | Knowledge-layer primitives: current direction is AHEAD of the 2026 frontier; target = a per-turn primitives context compiler; BUG-712 is architectural, not wiring. | `research/PRIMITIVES_DEPLOYMENT_RESEARCH_20261012.md` |
| SURGICAL_KNOWLEDGE_EXTRACTION | 2026-10-10 | Surgical on-demand extraction: ReAct/Toolformer decomposition, multimodal (video/audio/image) extraction, streaming feeds. | `research/SURGICAL_KNOWLEDGE_EXTRACTION_20261010.md` |
| TAXONOMY_EVOLUTION_TOOLING | 2026-10-04 | Drift/label-promotion tooling: River, Evidently, PSI, cleanlab (challenger audit), pySHACL, weak supervision (Snorkel); **blocking prerequisite: `menu_hash` NULL on 7,995/7,995 rows — drift across menu versions is undefined until backfilled.** | `research/TAXONOMY_EVOLUTION_TOOLING_20261004.md` |
| COLLABORATION_CONTINUITY_CORTEX | 2026-10-12 | 3-tier continuity (session-side / repo-side / context compiler) — drift-proof project memory. | `research/COLLABORATION_CONTINUITY_CORTEX_20261012.md` |
| D-B_PARAPHRASE_PATH_SPEC | 2026-10-11 | Design spec (BUG-705 recall fix), not research. | `research/D-B_PARAPHRASE_PATH_SPEC_20261011.md` |
| LAYER2_RETRIEVAL_CONTRACT | 2026-10-11 | Design spec (Layer-2 retrieval contract), not research. | `research/LAYER2_RETRIEVAL_CONTRACT_20261011.md` |
| STATE_MACHINES_GUARDRAILS | 2026-10-12 | State machines as the determinism backbone — RECOMMENDATION (owner gate), formalizes an existing pattern, no new dependency. | `research/STATE_MACHINES_GUARDRAILS_20261012.md` |
| VERIFIER_MODEL_SURVEY | 2026-10-12 | Verifier model survey — S5 stays DeBERTa (D2298). | `governance/VERIFIER_MODEL_SURVEY_20261012.md` |
| REPRESENTABILITY_SWEEP | 2026-09-23 | Representability sweep over the corpus. | `governance/REPRESENTABILITY_SWEEP_20260923.md` |
| cleanlab_label_audit / nli_label_audit | 2026-10-xx | Label-audit runs (cleanlab challenger + NLI audit). | `governance/cleanlab_label_audit.md`, `governance/nli_label_audit.md` |
| BORP_FEEDBACK_ASSESSMENT | 2026-10-13 | BORP feedback assessment. | `governance/BORP_FEEDBACK_ASSESSMENT_20261013.md` |
| INTAKE_ASSESSMENT | 2026-10-14 | Intake/curator assessment. | `governance/INTAKE_ASSESSMENT_20261014.md` |
| MARKET_RESEARCH_20261021 | 2026-10-21 | Agentic-RAG video audit (turbopuffer "RIP vector DB"): **MAXWELL ALREADY AT FRONTIER** (Keyword/FTS5/Vector/Hybrid-RRF/Graph/Agentic all shipped in retrieve.py); D-3118 dual-identity (lexical + embedding) independently confirmed; REFERENCE ColBERT late-interaction + Frames/Enterprise-RAG-Bench as eval harnesses; DEFER hop-count routing. | `governance/MARKET_RESEARCH_20261021.md` |
| MARKET_RESEARCH_20261021_KARPATHY | 2026-10-21 | Karpathy "99% use AI wrong" (beamnxw): **CONFIRMATION ONLY** — context-window=working-memory + distraction-degrades-accuracy validates selective verified-extraction injection; search/tool-use = "most useful tool" (already shipped). REFERENCE context-hygiene framing; no new technique. | `governance/MARKET_RESEARCH_20261021.md` |

**Net of the aggregation:** 27 scattered research docs indexed in one place. The two genuinely-NEW candidate families
that were NOT yet reflected in this register's P1/P2/P3 rows are (a) the **ontology R1-R20 set** and (b) the
**taxonomy-evolution tooling** (River/Evidently/cleanlab/pySHACL/weak-supervision). Both are now named here with their
receipts; neither is promoted to a numbered row because their adoption gates are decisions (SHACL is the only one
already 60% built — `config/taxonomy_shacl.ttl`), not research. No new dependency is implied by this index; it is a
recall map, not a purchase order.


---

## 2026-10-25 — EVALUATION: Recursive Flint (R-14) — MLX/OMLX vs Ollama availability, and the verdict

**The question asked:** is `RecursiveSI/flint` available for the MLX / OMLX inference engine, or can it be as fast in
Ollama? Every line below is a reading taken 2026-10-25; nothing is from memory (D-3109).

### 1. What the model IS (from the repository, not the tag metadata)

`config.json` → `architectures: ["FlintForCausalLM"]`, **`model_type: "flint"`** — a CUSTOM architecture, not a
Llama/Qwen shape. 49 layers (2 dense + 47 MoE), 256 routed experts (6 selected + 1 always-active shared), sliding
window **513**, 14 full-attention layers with **no positional encoding** (`no_rope_layer_indices`), per-head QK
RMSNorm + **learned per-head attention sinks**, `router_score_function: sigmoid`, `softmax_type: learnable`,
vocab 150,144, ctx 262,144. BF16 = 39,785,287,456 params / 79.6 GB in 15 shards. License Apache-2.0.

The model card says, verbatim: *"Flint runs on one B300 or H200 GPU per replica with the SGLang kit in `sglang/`.
**Transformers modeling code is not included yet.**"* and *"Quantized variants are prepared separately for NVIDIA
and Apple Silicon runtimes."* Note the trap: the HF repo metadata says `library_name: transformers` /
`AutoModelForCausalLM`, but **no `modeling_flint.py` is in the repo** — the tag is an autoloader alias, not shipped
code. Claiming "it has Transformers support" from the tag alone would be a false reading.

### 2. MLX / OMLX — available, but NOT through the engine installed here

- **`mlx-lm` has first-class Flint support**: `mlx_lm/models/flint.py` exists at HEAD; the PR *"Recursive Flint model
  support"* merged **2026-10-21**; a further perf PR (*"Skip fully masked key tiles in Flint sliding-window prefill"*)
  is **still OPEN (2026-10-24)** — i.e. the support is real but still stabilising.
- **A validated MLX conversion exists**: `mlx-community/flint-mixed-3-4bit` (lastModified 2026-10-22, 768 downloads) —
  mixed 3/4-bit (3-bit on the expert `switch_mlp` matrices, 8-bit embed), 4 shards, ships `eval_kl.py` (a KL-divergence
  quality check, not just a convert-and-hope). Plus community MLX builds (`pgmharikrishnan/Flint-MLX-Serve-*`,
  `dima6312/...-MLX-4bit`).
- **BUT the engine in this repo cannot load it today.** MEASURED: `/usr/local/bin/python3` carries **mlx-lm 0.31.3**,
  and `flint` is **NOT** in its 118 model modules (`import mlx_lm.models; 'flint' in …` → False). PyPI latest is
  **0.32.2**. So OMLX would need an mlx-lm upgrade (0.31.3 → ≥0.32.x) before `flint` resolves at all.
- **The fast MLX path is Recursive's own engine `rec`**, and it is hardware-gated: `rec` claims **1.4–2.6× llama.cpp
  throughput on M4 Pro**, but its stated requirements are *"Apple Silicon Mac with an **M4 Pro, M5 Pro, or M5 Max**"*
  and *"At least **48 GB** unified memory"*, and it is *"optimized for **single-session** usage"*. **This machine is an
  Apple M1 Max, 64 GB** — the M1 Max is not in `rec`'s supported list, and single-session-only excludes a multi-model
  pipeline anyway.

### 3. Ollama — YES, measured, and it is already the fastest *simple* path

Official GGUF ships from Recursive (`RecursiveSI/flint-int4-gguf`, `flint-nvfp4-gguf`) and upstream support exists
(`ggml-org/Flint-GGUF`). Community numbers, quoted with their source:

| Reading | Hardware / runtime | Number | Source |
|---|---|---|---|
| Short prompt | M5 Pro Mac mini 64 GB, **Ollama 4-bit** | **115 tok/s** | HF discussion #15 (@pratikgx) |
| 20K-token codebase | same | read in 11 s, then **87 tok/s** writing | #15 / #8 (@pratikgx) |
| Full ctx, NVFP4 GGUF | RTX Pro 5000 48 GB, llama.cpp | ~26 GB VRAM, **~115 t/s** | #17 (@curiousily) |
| Memory fit | 4-bit | int4 MLX 22.6 GB → ~24 GB total; Q4_K_XL 25.1 → ~27 GB; Q3 fits 24 GB | #8 (@localllmrig) |

So **"as fast in Ollama?" → yes; 87–115 tok/s**, entirely local, on exactly this machine class (64 GB Apple Silicon).
MLX/`rec` would be *faster*, but not on an M1 Max and not multi-session.

### 4. The blockers that decide it (this is the part that matters)

1. **R7 conflict — the decisive one.** Recommended generation is **temperature 1.0, top-p 0.95, top-k 20**; the card
   even says the server applies these when a request omits them. Maxwell's IRON RULE **R7 = temp 0.0 on all
   generation scripts**. The pipeline's determinism/reproducibility rests on R7 (D-3143 re-mints a pin precisely
   because a *byte* move invalidates a certificate). Running Flint at 0.0 is off its trained operating point; running
   it at 1.0 breaks R7. Either way it cannot hold a pipeline generator/classifier role.
2. **Tool calling is the model's known weak spot and needs grammar constraints.** Measured in HF #11 (@Nav8ha):
   with `--grammar none`, Flint called a `read` tool with `path` instead of `filePath` on 2 of 3 seeds; in OpenCode
   with a 3-bit MLX build **41 of 85 tool calls failed**; adding a schema grammar + all four EOS stop tokens took it
   to **0 of 50 failures with no decode slowdown** (mlx-vlm PR #2571). HF #19: *"speed is impressive, but tool call is
   disaster."* HF #12: it re-plans repeatedly and inspects unrelated files instead of calling an already-supplied
   tool; rec's MLX server accepts `grammar:"flint"` + `max_tokens` but **not** `reasoning_effort` /
   `thinking_token_budget`, so the only lever is a hard output cap.
3. **Quality is below the incumbent it would replace.** HF #5/#18/@curiousily: *"still behind Qwen"*, *"Not even close
   to the Qwen 3.8 27B, it is alternative for Qwen 3.6 35B A3B"*, *"clumsy, uses a lot of tools … but it is fast"*,
   *"it feels more is needed"*. Harness-reported: Terminal-Bench 2.1 **54.9%**, SWE-bench Pro v2 **89.7%**, SWE-bench
   Verified **74.2%** (temp 1.0; web-retrieved solutions counted as failures).
4. **Overthinking.** HF #15: *"some runs used 20K+ reasoning tokens before writing any code"*; the only mitigation is
   `max_tokens`, which truncates rather than reduces thinking.

### 5. VERDICT — DO NOT DOWNLOAD. Registered as R-14 (P3 monitor), not adopted.

- **MLX/OMLX**: available in principle (mlx-lm `flint.py`, `mlx-community/flint-mixed-3-4bit`), **but not with today's
  engine** — it needs an mlx-lm upgrade **and** a grammar-constrained tool path that plain mlx-lm/OMLX does not have.
- **Ollama**: available and fast (87–115 tok/s), **but** Ollama's GGUF path has the same tool-call grammar dependency
  and cannot honour R7.
- **Not worth the ~23–25 GB** while it (a) violates R7 for any pipeline role, (b) is weaker than the models already
  serving, and (c) cannot run on the fastest engine (`rec`) on an M1 Max.

**RE-OPEN CONDITIONS (all must be re-measured, not assumed).** (a) A grammar-constrained tool-call path exists in
OMLX (or mlx-vlm PR #2571-equivalent lands in mlx-lm), AND the sliding-window-prefill PR closes. (b) A **temp=0.0**
reading on Maxwell's OWN eval set beats the incumbent for the specific role proposed — otherwise the role would need
to be one that does not require R7 determinism. (c) If the hardware moves to an M4/M5 Pro/Max with ≥48 GB, `rec`
becomes a candidate engine in its own right and should be evaluated separately from Flint. **Nothing is downloaded or
promoted before (a) and (b) both speak (D-3058/D-3036).**

---

## 2026-10-25 — EVALUATION: Underdog Saluki 27B 1.0 (R-15) — Ollama/MLX availability, and whether it beats the local tool-calling roster

**The question asked.** "Can Underdog Saluki be found in Ollama or MLX, and is it worth using for tool calling if it is
better than any current local tool-calling LLM?"

### 1. WHAT IT ACTUALLY IS (read off the hub, not recalled)

`ConwayResearch/Underdog-Saluki-27B-1.0` — `library_name: gguf`, `pipeline_tag: text-generation`, `license:
apache-2.0`, created 2026-10-08, last modified 2026-10-15, **549,535 downloads / 622 likes**. Three weight-adjacent
files only: `Underdog-Saluki-27B-1.0-IQ2-mix.gguf` (7.89 GB), and two optional `mmproj-…-{F16,Q8_0}.gguf` vision
projectors. Its tags are the claim under test: `tool-calling`, `function-calling`, `agents`, `2-bit`, `qwen3.8`.
Base models declared: `Qwen/Qwen3.8-27B` and `ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF` — i.e. a **quantized derivative
of the model this box already serves**, not a new model family.

### 2. THE AVAILABILITY ANSWER — two different answers, and the difference is decisive

| Runtime | Available? | Evidence |
|---|---|---|
| **Ollama** | **YES** | The card ships an `ollama create` recipe and states the test: *"Tested with Ollama 0.40.4 on Apple silicon: chat, thinking and tool calling work."* |
| **MLX / OMLX** | **NO** | `GET /api/models?search=saluki` returns **9** repos; every one is `gguf`, `transformers`, or `ninfer`. **Zero MLX.** The one `transformers` hit (`rty813/…-bf16`, 160 downloads) is a dequant, not a runtime |

**Why the MLX route is not merely "missing" but VALUE-DESTROYING.** Saluki's entire contribution is the **IQ2-mix
quantization recipe** — its reason for existing is that a 27B at ~2 bits keeps tool calling. To reach MLX you would
dequantise to bf16 and re-quantise to MLX 4-bit, which discards the recipe and reproduces **the base model this box
already serves at 4-bit (`Qwen3.8-27B-MLX-4bit`, 15 GB measured)**. So: in OMLX it is either impossible or pointless.
This is the opposite of Flint's shape (R-14), where MLX support existed and Ollama merely existed too.

### 3. THE TOOL-CALLING ANSWER — better than the local roster? **UNPROVEN, and the instrument is why**

Saluki's published numbers (vendor's own "Underdog Bench", 120 frozen BFCL-v4 tasks, thinking off, temperature 0):

| Model | Size | Passed / 120 |
|---|---|---|
| Underdog Saluki 27B 1.0 | 7.89 GB | **88** (73.3 %) |
| Qwen3.8-27B, full size | 54 GB | 84 (70.0 %) |
| Bonsai 2 | 5.95 GB | 70 |

A +4-task margin over its own full-size base. The card's own caveats are the strongest evidence against buying it:
*"120 tasks is a modest test, and a few tasks of any gap is run-to-run variation"*, *"about a fifth of parallel-call
replies have small formatting slips"*, *"clumsy"* is the shape community reviewers report. **A small formatting slip
in a tool call is precisely the failure class this OS refuses** — a malformed call is a governed write that
half-succeeds.

**Against the local roster, no comparison is possible today, and that is the finding.** Maxwell has never measured
tool-call **accuracy** for ANY served model. `scripts/measure_subagent_loop.py` (T-187) is the only instrument, and
it is honest but narrow: it grades that step 2's argument equals the seed-derived key (`grade_two_step`: *"lookup_token
keys … never used the seed-derived key"*), so it **does** catch wrong argument VALUES and therefore name-drift (the
Flint failure, `path` vs `filePath`). But it is **one fixture**. A one-task instrument cannot resolve a 3-point
difference on 120 tasks — the claimed effect size is below the instrument's resolution. So the honest sentence is:
**Saluki is not measurably better than the served roster, because nothing here measures tool-call accuracy at a
resolution that could say so.**

### 4. THE HIDDEN CONFLICT — what adopting it would actually cost (the future tax)

1. **A SECOND INFERENCE ENGINE.** Ollama is not installed on this machine (`command not found`); the declared engine
   is OMLX (`config/engine.yaml#name: omlx`, port 11435). Adopting Saluki means installing and living with a second
   engine. `pipeline/memory_guard.py` measures **host-wide** `psutil.virtual_memory().available`, so a second resident
   model is *not* invisible to the memory guard — that one cascade is genuinely contained. But the **lifecycle** is
   not: `pipeline/omlx_engine_guard.sh` manages OMLX only, so a second engine would have no boot guard, no
   adaptive eviction, and no retirement discipline (BUG-808: *"a name that lies"*).
2. **PROVENANCE LOSES ITS SUBJECT.** R14 stamps `gen_model` + `pipeline_commit`. The SAME model name served by TWO
   engines can produce different outputs (different quant, different sampler defaults, different template). The stamp
   would still resolve — but no longer re-produce. Under D-3034 (a declaration must RESOLVE) that is a degraded
   receipt, not a broken one — which is exactly the kind of quiet drift this OS exists to refuse.
3. **THE POOL RULE BITES.** D-3009: *"a DOWNLOAD is paired with a RETIREMENT when the pool is full."* Seating a
   2-bit copy of a model already resident at 4-bit means retiring the **better** copy for the **worse** one, to gain
   a tool-calling margin that is not measurable here.
4. **NO R7 CONFLICT — recorded because it is real.** The card's fast-tool-call setting is *thinking off, temperature 0*,
   which is **compatible** with the temp=0.0 iron rule. This is the one axis on which Saluki is strictly better
   positioned than Flint, and it is why the lane is left OPEN rather than closed.

### 5. VERDICT — DO NOT DOWNLOAD. Registered as R-15, §lane OPEN, model REFUSED.

- **Ollama**: works, and is the only route. **MLX/OMLX**: does not exist, and converting the bf16 dequant would
  reproduce a model already served — so there is nothing to gain on this engine.
- **Worth it for tool calling?** Not on today's evidence: the margin is a vendor self-measurement inside run-to-run
  noise, purchased with a 2-bit accuracy cut on the reasoning axis (MuSR −12.1, AIME −17.5), paid for with a second
  engine and a retirement of the 4-bit incumbent.
- **What would actually change the answer is an INSTRUMENT, not a download:** widen T-187 from one fixture to a
  task-family battery (distractor, parallel-call formatting, argument-NAME trap, enum-arg trap). That instrument is
  engine-agnostic and settles Saluki, Flint and every future candidate at **zero GB**.

**RE-OPEN CONDITIONS (all must be re-measured, never assumed).** (a) An MLX build of the **IQ2 recipe** (not a 4-bit
re-quant) appears, **or** OMLX gains a GGUF/llama.cpp route so the engine stays single. (b) T-187 widens to a
task-family battery **and** Saluki beats the best served model on it at temp=0. (c) A tool-calling role is declared
that does not sit in the governed-write path, so a "small formatting slip" cannot corrupt a store write. **Nothing is
downloaded or promoted before (a) and (b) both speak (D-3058/D-3036).** D-3009's earlier "REFUSE (no model_type: not
an MLX repack)" is hereby **confirmed and superseded in scope**: the observation stands, the refusal was scoped to the
resident pool, and this row is the wider question the owner asked (D-3038: what we reject we register, with reason).

### 6. CORRECTION (2026-10-25, measured after the first write-up) — the §4/§5 engine objection was WRONG, and it was wrong by the very bug this session fixed

**What I claimed and what is true.** The first write-up of §4/§5 said *"Ollama is not even installed here —
`command not found`"* and priced adoption as *"installing a second engine"*. That was **FALSE**, and it was produced by
exactly the defect BUG-1000 names: I probed with a bare `ollama` name, which is resolved by PATH ORDER, and this
shell's PATH did not contain `/usr/local/bin`. Measured properly:

- `curl -s http://127.0.0.1:11434/api/version` → `{"version":"0.40.11"}`
- `/usr/local/bin/ollama -> /Applications/Ollama.app/Contents/Resources/ollama` (installed, 71.9 MB binary)
- `python3 pipeline/status.py` → `Services: OMLX ✅ | Ollama ✅`, `Versions: OMLX 0.7.2 | Ollama 0.40.11`
- `python3 scripts/guard_stacks_single_source.py` → `✅ Single-source invariant holds for all stacks: ollama, omlx`

So Ollama is not a hypothetical second engine: it is an **already-installed, already-running, already-declared stack**
whose single-source invariant the repository already guards. A bare-name probe answered a question about a SERVICE
using a fact about a shell — the identical shape as `python3` answering a question about an interpreter. **The lesson
is general and is the reason this correction is recorded rather than quietly edited: on this box, "not found" is a
claim about PATH, not about existence, and it must never be written down as the latter.**

**What the correction does to the verdict — one blocker weakens, none fall.** The objection is no longer "a new
engine must be installed"; it is **"a new ROLE on an existing engine whose lifecycle is not governed for it"**:

- The engine POOL is OMLX's: `/health` reports `engine_pool {model_count: 8, loaded_count: 2, final_ceiling:
  46822972304, current_model_memory: 16959830621}`. A model resident **in Ollama** is invisible to that pool's
  accounting and its adaptive eviction — the *host* memory guard (`psutil.available`) would see the bytes, but the
  thing that decides WHICH model to evict would not. That is the cascade, and it is sharper than the original claim,
  not softer.
- Ollama's declared role is the **embedder** (`bge-m3`, 512d — D2190/D2196/D2202). Promoting it to a generation role
  is a role change on a shared stack, which needs its own decision, not a download.
- Blockers (2) 2-bit accuracy, (3) vendor self-benchmark inside run-to-run noise, (4) duplicate-of-a-served-model at
  lower precision, and (5) instrument resolution are **untouched** by this correction.

**Verdict unchanged: DO NOT DOWNLOAD.** R-15 stays §lane-OPEN, model-REFUSED, and re-open condition (a) is now
narrower and more honest: it is not "get an MLX build" alone, it is **"declare a governed generation role for the
Ollama stack (its own pool accounting and eviction), AND widen T-187 past one fixture, AND beat the served roster on
it at temp=0"**. Until all three speak, a 7.89 GB 2-bit duplicate of a model already served at 4-bit buys a margin
this machine cannot measure.
| 2026-10-25 | **"gated on T-187" — the gate in five rows above now resolves to NOTHING, and this row says what replaced it** (found while re-deriving the declared next steps) | ⬜ **CORRECTED, NOTHING IN THE ROWS ABOVE IS RETRACTED. T-187 is CLOSED (state done, 2026-10-19)** — `scripts/measure_subagent_loop.py#run_two_step_model` landed, the full served-set run was recorded (`temp/subagent_loop_two_step_full_20261019.json`), and the promotion it gated was made by **D-3104** (AGENT_LOOP_SHORT = gpt-oss-20b-MXFP4-Q8). So every sentence above that says a candidate is "gated on T-187" is naming a referent that no longer exists (D-3034: a declaration must RESOLVE). What those rows were actually waiting for is the thing T-187 deliberately did not build: **one fixture ADMITS a model to a role, a BATTERY RANKS one.** R-15's own recorded limit is the proof — a 1-task instrument cannot resolve a 3-point gap on 120 tasks — and it is why `AGENT_LOOP_FAST` / `AGENT_LOOP_WORKHORSE` are still undeclared. **REPLACEMENT GATE: `config/task_register.yaml#T-199` (registered 2026-10-25, mover pipeline)** — four fixtures beyond the two-step one (distractor, parallel-call formatting, argument-NAME trap, enum-argument trap), each with a derived expected answer and a known-answer control, and promotion refused until a candidate beats the incumbent across the whole battery at temperature 0. **Nothing is downloaded to run it:** the served roster is the first population, 0 GB. The verdicts in the rows above are unchanged — R-14 (Flint) stays REFUSED for its temp-conflict with R7, R-15 (Saluki) stays §lane-OPEN / model-REFUSED on five measured reasons of which the instrument is only the fifth, and D-3061's "download nothing this cycle" stands on its own argument. | `config/task_register.yaml#T-199`; `config/task_register.yaml#T-187`; D-3058; D-3104 |
| 2026-10-25 | **R-15 (Saluki): its re-open condition (b) now RESOLVES — the BATTERY exists and four served models pass it 4/4 — so the "instrument cannot see the claim" objection is retired; what it must now beat is measured** | ⏸️ **STILL REFUSED, on the two conditions that did not move.** The gate this row was waiting on was T-199, and T-199 is CLOSED the same day (D-3148): `scripts/measure_subagent_loop.py --battery` ran the whole served roster at temperature 0.0 — 8 models × 4 fixtures, 32 rows, `governance/evidence/LOOP_BATTERY_20261025.json`, **0 GB downloaded**. Four models passed 4/4 with WARM turns of **1.5 s (MiniCPM5-2B), 7.3 s (Ornith-35B), 14.7 s (Ornith-9B) and 15.8 s (Qwen3.8-27B)**; nothing on this roster failed a fixture except Phi-4-mini (0/4, the BUG-053 shape again) and gemma (distractor only). So the honest sentence is no longer "the effect is below the instrument's resolution" — it is "**Saluki would have to beat a 4/4 roster at 1.5–15.8 s warm, on this exact battery, at 2 bits, and its vendor margin (+4 tasks of 120 over its own base) does not survive that comparison being made at all**". Unchanged and still decisive: (a) **no MLX build of the IQ2 recipe** exists (9 hub repos, zero MLX) and dequantising to MLX 4-bit reproduces the 4-bit base already served; (c) **Ollama has no governed GENERATION role** — its declared role is the embedder, and a model resident there is invisible to the OMLX pool's accounting and adaptive eviction. The lane stays OPEN, the model stays REFUSED, and re-measuring it is now cheap instead of impossible: download nothing, run the battery. | `config/task_register.yaml#T-199`; D-3148; `governance/evidence/LOOP_BATTERY_20261025.json` |

---

## 2026-10-25 — CORRECTION TO R-14 (Flint): the row was RIGHT and the agent's SUMMARY of it was WRONG. Four propositions, four readings, never again one sentence.

**What was said, and what is true.** The agent told the owner *"Flint is not available in oMLX."* The owner answered with
two names — **`flint-Optiq-4bit`** and **`flint mixed 3 4bit`** — and asked how future market research would be enforced.
**Both names are real upstream.** The R-14 row above already said so verbatim ("Both target runtimes **EXIST** and are
measured fast", "a validated MLX conversion exists: `mlx-community/flint-mixed-3-4bit`"). The agent therefore **contradicted
its own register from recollection** — the drift was in the summary, not in the record. That distinction is the whole point
of this correction: a register that is right cannot defend itself against a reader who does not read it.

**THE FOUR PROPOSITIONS.** One sentence fused them; each has its own reading, and only P4 is false. Durable receipt:
`governance/evidence/MODEL_AVAILABILITY_FLINT_20261025.json`.

| # | proposition | verdict | the reading that decides it |
|---|---|---|---|
| **P1** | `mlx-community/flint-mixed-3-4bit` **exists upstream** | ✅ **TRUE** | `curl -sS 'https://huggingface.co/api/models?search=flint&limit=100'` → repo present, **dl 1166**; probe → `fetch=OK`, **17.84 GB**, `model_type=flint`, created 2026-10-22, apache-2.0 |
| **P2** | `mlx-community/flint-OptiQ-4bit` **exists upstream** (the owner's name) | ✅ **TRUE** | same read → repo present, **dl 138**, **27.48 GB**, created **2026-10-24** (one day old when the owner named it) |
| **P3** | the **bytes** are on THIS machine | ❌ **FALSE — a name without bytes** | `du -sh ~/.cache/huggingface/hub/models--mlx-community--flint-mixed-3-4bit` → **12 K**, and `find` over it returns exactly two files: `blobs/cf7c7f09…` (the README) and `refs/main`. **No weights.** For scale, same command: `clef-4bit` 8.2 G, `MiniCPM5-2B-MLX` 1.3 G. `flint-OptiQ-4bit` is present in **none** of `~/.omlx/models`, `~/.cache/huggingface/hub`, `~/.lmstudio/models`, `~/models`, `~/Downloads`, `~/Documents`, `/Volumes` |
| **P4** | oMLX can **serve** either today | ❌ **FALSE — measured twice** | (a) the engine's own oracle: **`ARCH_UNSUPPORTED` for BOTH**, *"model_type=flint has no module in the engine's mlx_lm build"* (`mlx_lm 0.31.4.dev132`, **134 architectures**); (b) the bundle itself: 135 files under `mlx_lm/models/`, **no `flint.py`**. `~/.omlx/models` holds 8 served models, flint not among them |

**P3 and P4 are NOT existence claims, and P1/P2 are NOT servability claims.** R-14's four blockers are all P4-class
(operating point, grammar path, `rec` hardware, quality) plus one adoption cost — none of them ever said the models do not
exist. The project already owned the correct vocabulary and the agent did not use it: `MARKET_RESEARCH_20261015.md:88`
distinguishes *"Already on disk (bytes), NOT yet served"*, and **BUG-808** records the **inverse** failure ("an entry that
reads as on disk is not on disk"). BUG-808 and this event are **one defect**: collapsing a multi-state availability
ontology into a binary.

**TWO SECONDARY CORRECTIONS TO R-14 (both from live reads, neither changing the verdict).**
1. R-14 says *"`flint` is **NOT** in its **118** model modules"*. Live oracle: **134** architectures. The number is stale;
   a row carrying a count the instrument contradicts had not been re-measured, which is exactly the condition in which a
   verdict silently outlives its evidence.
2. R-14 presents the runtime absence as final. The distance is now **one upgrade**: upstream `mlx-lm` gained
   `mlx_lm/models/flint.py` on **2026-10-21**, so the engine at `0.31.4.dev132` is **below** the `>=0.32.x` that would
   resolve `flint`. P4 is therefore false **at this engine version**, not false in principle — and it becomes
   `LOADABLE_CANDIDATE` the moment the engine's mlx_lm moves, which is precisely what **T-200** (the oMLX A/B) is holding.

**WHY AN INSTRUMENT ALREADY ANSWERED THIS, AND WHY THAT IS THE ENFORCEMENT.**
`python3 pipeline/model_loadability_probe.py <repo>` is **TIER-A, needs no download, runs in ~2 s**, and answers in the
engine's own runtime with the vocabulary this question needs: `LOADABLE_CANDIDATE / ARCH_UNSUPPORTED /
NEEDS_FORK_RUNTIME / NO_MLX_WEIGHTS / EMPTY_REPO`, with TIER-B for the post-download fact. **The honest read was cheaper
than the recollection.** That is the principle earned here and registered as **D-3151**: *a discipline that costs more
than its shortcut will not be kept — so the fix for research drift is not a promise to be careful, it is making the
truthful read the cheapest action available, and making a verdict without it REFUSE.*

**The rail that follows from it (one home, no fourth instrument).** `config/engine.yaml#candidates.refused` is now the
**machine-readable refusal register** (D-3038, *what we reject we register*, applied to models), and
`python3 scripts/check_model_claims.py` refuses any refusal whose verdict does not RESOLVE to an engine reading. A
refusal recorded only as a sentence is a recollection; a refusal recorded as a repo id plus a resolvable probe verdict is
evidence (D-3034). Nothing is downloaded and no candidate is re-opened by this correction: **R-14's refusal stands
unchanged** — it is its *reason* that is now stated exactly.
