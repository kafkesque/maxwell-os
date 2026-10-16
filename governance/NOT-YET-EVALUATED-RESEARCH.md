# Maxwell OS — Not-Yet-Evaluated Research Opportunities
> **Date:** 2026-08-09 | **Source:** feed.opml + senior RAG developer assessment
> **Status:** Fresh opportunities — none rejected, none tested

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
| **R-12** | Prompt caching | Cache system prompts across calls | S4 | ~500 tokens saved per FB | Depends on OMLX caching support. NOT verified. |
| **R-13** | Token-efficient prompt patterns | Systematic prompt optimization | All stages | 10-30% across pipeline | Requires per-stage analysis. |

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
