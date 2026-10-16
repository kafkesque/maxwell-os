# Maxwell OS v3.0 — Agent Loader
> **Loads at session start.** Points to CONSTITUTION.md (single source of truth).
> **v3.0:** Updated 2026-07-26 (cluster-before-extract, C12 enhanced, D2116 feeds).

<maxwell_os agent_version="3.0">

<!-- IRON RULES — NEVER break -->
<iron_rules>
- $0 marginal cost — all generation on local hardware (C1)
- Sovereign — all data and compute remain local (C3)
- No vendor lock-in — open formats, multiple model families (C2, C4)
- temp=0.0 on all generation scripts (R7)
- Generator ≠ Verifier — different model family for each (R5)
- Every persistent object stamped: schema_version, gen_model, pipeline_commit (R14)
- NEVER hardcode ANY value — paths, thresholds, model names, magic numbers → config/*.yaml (C12)
- ⚠️ C12 REVIEW-RULE: Before accepting any LLM/agent output, scan for hardcoded strings. Reject and re-prompt if found (C12d)
- Config-first default: if a value CAN be configurable, it MUST be in YAML. No excuses. (C12c)
- Crash-safe writes: tempfile → fsync → os.replace (C6)
- NEVER delete pipeline output — use pipeline/safe_delete.py (R-D410)
- Backups after batch writes: bash pipeline/backup_guardian.sh (C13)
- Buglog: 5+ unresolved → append to all handoffs (C15)
- No silent errors — except clauses must log AND raise (C16)
- AUTO-LOG BUGS: log to governance/buglog.md immediately upon discovery — never defer
- Type hints on all function signatures (C17)
- Docstrings on all functions >5 lines (C18)
- No dead code — _OLD files → archive/, no __pycache__ in repo (C19)
- No magic numbers — extract to named constants or YAML config (C20)
- Swappable Infrastructure — every component behind a protocol/abstraction (C21)
- Hybrid Sovereignty — local-first, API opt-in explicit (C22)
- Resilient by Design — survives component failures without data loss (C23)
- Hardware-Adaptive — auto-detect RAM, degrade gracefully (C24)
- Agent-Agnostic — expose via MCP, no agent-specific coupling (C25)
- Cross-Platform — psutil + pathlib, target macOS/Linux/Windows (C26)
- Zero Future Tax — protocols first, feature flags, no dead ends (C27)
- Quality-Tiered — lightweight default, bloat is opt-in (C28)
</iron_rules>

<!-- WORKING RULES — how a SERIOUS ACT is done. Each one is a decision, and each one was measured first. -->
<working_rules>
- A DECLARATION MUST RESOLVE (D-3034). A value that merely MENTIONS a thing declares nothing; only a RESOLUTION confers ownership - an entry whose realpath lands inside it, a value that IS the reference, a path that EXISTS. Before accepting any bucket, class or count, ask what RESOLVED it; a register whose values are SENTENCES declares no bytes.
- COMMAND FORM DECIDES WHAT IT REQUIRES (BUG-842/T-146). A declared command written as a BARE path must be executable; the 'python3 <path>' form needs no bit. Never mass-chmod 562 files to make a promise true - declare the form you actually run and let scripts/resolve_route.py --check refuse the rest.
- AN OPEN OWNER-LANE ROW IS A PROPOSAL, NOT AN APPROVAL. mover: owner + state: open = "registered, awaiting YOUR word" (D-3035 sitting). An approval flips mover to pipeline IN THE REGISTER (the face is DERIVED from it, so editing the face changes nothing); a deferral is RECORDED as deferred, never left to look like a pending question.
- A THEORY NEEDS A RED LOOP FIRST (D-3036). No hypothesis may be formed before ONE named command exists, already run once, that goes RED on this bug and GREEN when it is fixed. Phases are GATES; every guess stays labelled a hypothesis until a receipt speaks. For an intermittent bug the target is a debuggable REPRODUCTION RATE, not a clean repro.
- AN ACT THAT LEAVES NO TRACE DID NOT HAPPEN (D-3036/BUG-844). A delegated or detached run declares its budget, its purpose and the exact files it MAY write BEFORE it starts; an artifact it claimed but did not leave is a NAMED fault. Peek is session-scoped evidence, not a record - the RECORD is T-168's journal: declare the run with 'python3 scripts/delegate_journal.py start --purpose ... --model ... --may-write <path|none> --budget-s N' BEFORE the call and close it with 'end --id <id> --state <done|failed|cancelled> --artifact <path>'; 'status' names every open run past its budget (rc 2), and a 'done' whose artifact is absent is REFUSED rather than recorded.
- WHAT WE REJECT WE REGISTER (D-3038). A rejected idea is recorded WITH ITS REASON so it cannot be re-proposed; an accepted negative ("we deliberately do NOT do X, and here is why") is a first-class decision, not a silence.
</working_rules>

<!-- BOOT SEQUENCE -->
<boot>
1. Read CONSTITUTION.md
2. Load agent/session_seed.yaml
3. Run: python3 pipeline/omlx_watchdog.py --pre-stage
4. Run: just health
5. Run: python3 pipeline/status.py
</boot>

<!-- KNOWLEDGE SOURCES -->
<knowledge_sources>
- CONSTITUTION.md (single source of truth, v3.0)
- DECISION-LOG.md (all architectural decisions D2000-D2487)
- MASTER-TASK-REGISTER.md (task tracker)
- config/decisions.yaml (auto-synced decision registry — 475 decisions)
- governance/buglog.md (live bug register)
- governance/aggregated_remaining_tasks.md (prioritized task register)
- governance/folder_protocol.md (file creation rules)
- agent/session_seed.yaml (session config)
- feed.opml (technology feed sources for weekly research)
- governance/CONTEXT_INDEX.md (RECALL MAP - read first when resuming: where everything lives,
  which claims are superseded, and the HUMAN GATE REGISTER)
- governance/SEQUENCE_STATUS_20260917.md (execution tracker + human gates)
- governance/FORENSIC_AUDIT_20260917.md (F-01..F-16) | governance/MARKET_RESEARCH_20260917.md (A1..A12)
- governance/PRIORITY_DECISION_20260917.md | governance/STRATEGIC_PLAN_20260917.md
- config/eval_integrity.yaml (floors + provenance tier vocabulary)
</knowledge_sources>

<!-- PIPELINE — 8-stage v3.0 (CONSTITUTION §2) -->
<pipeline>
  stage0_convert.py    → EPUB/PDF → MD (Pandoc/Docling)
  stage0_5_extract_metadata.py → MD → author/title (LLM)
  stage1_chunk.py      → MD → segments + SHA-256 dedup
  stage1_3_prefilter.py → regex pre-filter (D2080)
  stage1_5_embed_cluster.py → FAISS cosine + source diversity (cluster-before-extract)
  stage2_extract.py    → Clusters → convergent FBs (Qwen3-Coder, R5)
  # stage3_cluster.py  → REMOVED (D2120/D2198) — HDBSCAN dedup replaced by cluster-before-extract
  stage4_merge.py      → FBs → classified + formatted
  stage5_verify.py     → DeBERTa-v3-large NLI only (fail-closed, D2298)
  stage6_commit.py     → SQLite (sqlite-vec) + Parquet export
</pipeline>

<!-- DELEGATE RULES (DELEGATE-001 workaround verified 2026-07-26) -->
<delegate_rules>
- ALWAYS specify provider and model: delegate({provider: "maxwell_omlx", model: "..."})
- ⚠️ DELEGATION STATUS (2026-07-26, CONFIRMED):
  - ✅ gemma-4-E4B-it-MLX-4bit: CONFIRMED working. 0.48s response. Use for: code review, summarization, classification.
  - ⚠️ Qwen3-Coder-30B-A3B-Instruct-MLX-4bit: SINGLE-SHOT code gen ONLY (via curl/one-shot). Do NOT delegate multi-turn agentic tasks — decode collapses monotonically (~6.8→0.4 tok/s) as agent context grows, responses shrink to ~50-token stubs (DELEGATE-002, 2026-08-28).
  - ⚠️ Phi-4-mini-instruct-8bit: HALLUCINATES on open-ended research (BUG-053). Only for summarization WITH source text.
  - ❌ NEVER use custom_deepseek: reasoning_content passthrough bug (DELEGATE-001).
  - For research/fact-finding: use shell/curl directly. Do NOT delegate open-ended research.
- DELEGATION ROUTING (D2549 — task-type → right local LLM; ALWAYS route by this map):
  - Deterministic data-repair (SQL/scripts: T-311, kind-swap, FTS rebuild): EXECUTE directly (LLM-free). But delegate CODE REVIEW of any NEW repair script to gemma-4-E4B-it-MLX-4bit BEFORE --apply (R5: generator ≠ verifier).
  - Code review / classification sanity / summarization WITH source → gemma-4-E4B-it-MLX-4bit (CONFIRMED working; verified 2026-09-04 approving the T-311 script).
  - S4 discipline/domain classification → gpt-oss-20b-MXFP4-Q8 (OMLX classifier; batch via subprocess, NOT a delegate).
  - Promotion (emerging→canonical, discipline/domain) → deterministic `match_to_canonical` + owner-gate; NEVER an LLM (D-2898, `no_llm_canonical_promotion:true`). gpt-oss-20b is ADVISORY-ONLY for promotion (its proposal is never auto-applied).
  - Single-shot code generation → Qwen3-Coder-30B (curl one-shot ONLY — never multi-turn).
  - Summarization WITH source text → Phi-4-mini-instruct-8bit (never open-ended; BUG-053).
  - Open-ended research/fact-finding → shell/curl directly (NEVER delegate).
- Memory budget labels (THREE distinct concepts — do not conflate, D2496):
  - `delegate_model_budget` = ~24GB of 64GB — total for all delegate-served models combined (this file)
  - `omlx_guard_ceiling`  = 55GB — OMLX server memory-guard ceiling (D1804/D2208)
  - `run_wall_budget`     = 48GB — user hard wall for a pipeline run (memory_guard.py uses dynamic psutil.available, min_free_gb=8)
- Pipeline parallelism: use subprocess (pipeline/parallel.py), NOT delegates
</delegate_rules>

<!-- MODELS (CONSTITUTION §2 v3.0) -->
<models>
  Generator:    Qwen3-Coder-30B-A3B-Instruct-MLX-4bit (OMLX)
  Classifier:   gpt-oss-20b-MXFP4-Q8 (OMLX, S4 — D2249)
  Probe:        Phi-4-mini-instruct-8bit (OMLX, S2 fast probe — D2319; NOT an S5 verifier, D2298)
  Embeddings:   bge-m3 (Ollama, 512d Matryoshka)
  NLI:          MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli (local, D2298)
</models>

<!-- PROTECTED FILES — never overwrite -->
<protected>
  CONSTITUTION.md, DECISION-LOG.md, MASTER-TASK-REGISTER.md
  AGENTS.md, .env, config/*.yaml, governance/*.md
</protected>

</maxwell_os>