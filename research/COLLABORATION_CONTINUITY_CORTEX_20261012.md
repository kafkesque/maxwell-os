# Collaboration Continuity Cortex — drift-proof, correlation-aware project memory

**Date:** 2026-10-12 · **Author:** goose (orchestrator) · **Scope:** meta-infrastructure for the Maxwell OS collaboration itself.

## Verdict (one line)
This is **not a pivot — it is a completion.** The request ("a knowledge graph of Maxwell OS that detects correlation and evolves after each query; keep uncommitted decisions fully aware; nothing lost") is the **A1 context-compiler + A2 logical-form graph** adoptions already recommended for the *retrieval* layer, applied one layer up to the *governance/session* layer. Maxwell's existing instinct (stamped, append-only, typed registers) is ~80% of the design; the missing 20% is a **correlation index** + a **deterministic context compiler**.

## Research: existing methods / tools / repos

| Source | What it is | Verdict |
|---|---|---|
| **Graphiti (Zep)** | Temporal knowledge graphs for AI agents — nodes/edges that *evolve over time*, queried per-turn. | **ADOPT as design reference** (not dependency — sovereign/local C3). This is literally "knowledge graph that evolves after each query." |
| **Letta / MemGPT** | Stateful agents with a memory hierarchy (core / recall / archival); "learn from experience and improve with use." | **ADOPT as pattern** — maps 1:1 onto the four-tier memory taxonomy already in-repo (2603.07670). |
| **Mem0** | Persistent long-term memory layer for coding agents (has a Claude Code integration). | **REFERENCE** — proves "memory for agent workflows" is a solved category, but adds an external dependency Maxwell does not need. |
| Context Engineering (Anthropic 2507.13334) | Smallest set of high-signal tokens maximizing outcome. | **ADOPT** — this is the context compiler's contract. |
| KAG (2409.13731) | Logical-form-guided reasoning; LLM-friendly knowledge representation. | **ADOPT** — typed edges (implements/blocks/caused-by/contradicts) are the "logical form" of the graph. |
| Library Drift (2605.19576) | LLM-authored skills +0.0pp vs human-curated +16.2pp. | **CONFIRMS** owner-gated promotion (D-2898). |
| Tool-Drift (2605.24941) | Long-term memory silently biases tool selection. | **CONSTRAINS** trust ledger = rank signal w/ interval, never hard gate. |
| Ontology-guided GraphRAG (2511.05991) | Human-owned ontology + chunk info ≈90% vs LLM-authored ontologies underperform. | **CONFIRMS** D-2924 closed human-owned vocabulary. |

## Design — three tiers, loss-proof

**Tier 0 — session-side (goose primitives, survive compaction)**
- `Todo.todoWrite` = the durable "current frontier": uncommitted decisions, open owner-gates, ordered next steps.
- `Memory.rememberMemory` (tagged) = stable cross-session facts: delegation routing (D-2549), axis ontology, root-cause findings.
- `Chatrecall.chatrecall` = search past sessions for cross-turn correlation.

**Tier 1 — repo-side sovereign (single source of truth, C3)**
- Existing registers stay authoritative: `buglog.md`, `config/decisions.yaml`, `MASTER-TASK-REGISTER.md`, `MUTATION_JOURNAL.jsonl`, `CONTEXT_INDEX.md`.
- **NEW:** `governance/correlation_graph.jsonl` — append-only, R14-stamped, nodes = {bug, decision, task, finding, query, primitive, file}, edges = {implements, blocks, caused-by, supersedes, relates-to, owner-gates, requires, contradicts}.

**Tier 2 — context compiler (deterministic)**
- `scripts/continuity_context.py`: given a focus (new question / entity), emit the minimal high-signal context pack (top-k neighbors + open uncommitted decisions).
- LLM is **advisory-only** for correlation proposals, never auto-applied (D-2898 `no_llm_canonical_promotion`).

## Why this is drift-proof
- Append-only + stamped (R14) ⇒ every finding has provenance, nothing silently overwrites.
- Typed edges ⇒ correlation is explicit and queryable, not implicit in prose.
- Two-tier persistence (goose + repo) ⇒ survives compaction AND repo loss.
- Context compiler ⇒ minimal tokens to re-establish intent after a derailment (Context Engineering).

## Minimal implementation (queued — unblocked, additive)
1. `governance/correlation_graph.jsonl` (nodes + edges, append-only stamped) — new decision id to be minted.
2. `scripts/continuity_context.py` (deterministic compiler; code-review delegated to gemma-4-E4B per D-2549).
3. Wire into `just health` / boot so it is always current.

## Anti-derailment protocol (how a new question is absorbed without losing the thread)
1. Any new question → first append it as a `query` node + `relates-to` edges to the graph (so intent is never dropped).
2. The orchestrator (goose/deepseek) re-asserts the **Todo frontier** (uncommitted decisions + next steps) before answering.
3. If the question is open-ended research → shell/curl/Fetch directly (NEVER delegated to Phi-4, BUG-053). If it needs code → Qwen3-Coder one-shot; if review → gemma-4-E4B.
