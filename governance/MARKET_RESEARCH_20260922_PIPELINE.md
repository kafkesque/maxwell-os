# Market Research — Knowledge Pipeline & Skill Orchestration (2026-09-22)

**Scope:** What tools / repos / developments / peer-reviewed work in the Maxwell OS *knowledge
pipeline* (S0–S6) and *skill orchestration* (goose recipes, MCP, subagents) space is worth
REFERENCE / ADAPT / INTEGRATE — filtered through C1–C28 (local-first, $0 marginal, sovereignty,
no lock-in, agent-agnostic MCP, zero bloat, swappable infra).

**Method:** GitHub topic sweeps (graphrag, structured-extraction, reranker, mcp-server, skill
orchestration) + canonical peer-reviewed landscape. Community-signal rule (D-332) applies: prefer
works that *measure on matching (Apple Silicon / local) hardware* over vendor claims.

> Do not restate a config value here — cite the path. Decisions: `config/decisions.yaml` (D-333),
> `DECISION-LOG.md`. Feed: `feed.opml`.

---

## A. Knowledge pipeline (S0–S6) — findings

### A1. GraphRAG — the dominant retrieval-quality lever (REFERENCE, one ADAPT candidate)

| Repo / work | Signal | Verdict |
|---|---|---|
| `microsoft/graphrag` (⭐36k) — "From Local to Global" (Edge et al., 2024, peer-reviewed) | Canonical graph-RAG. Entity/relation extraction → community summarization → global query. | **REFERENCE.** Azure/OpenAI-first = C2/C3 friction; heavy. |
| `HKUDS/LightRAG` (⭐39k, already in `feed.opml`) | Graph + vector hybrid, incremental, cheap. | **ADAPT** (already flagged: "FB retrieval quality via graph approach"). |
| `gusye1234/nano-graphrag` (⭐3.9k) | Lightweight, local, few-MB graph store, "GraphRAG in 100 lines". | **MUST-REFERENCE.** Best local-sovereignty fit (C1/C3) for an FB knowledge graph. |
| `Graphify-Labs/graphify` (⭐120k) | New dominant GraphRAG tool; high churn. | **WATCH.** Verify license/self-host cost vs C1/C2 before any adoption. |
| `DEEP-PolyU/Awesome-GraphRAG` (⭐2.6k) | Curated survey of the whole GraphRAG field. | **REFERENCE** (map, not a tool). |

**Peer-reviewed anchors (established, stable):** GraphRAG (Edge 2024), LightRAG (Guo 2024),
HippoRAG (Gutiérrez et al., NeurIPS 2024), RAPTOR (Sarthi 2024). These are the *retrieval-quality*
family Maxwell's S1.5→S6 would draw from if it adds a graph layer. **Mapping:** S1.5 (cluster-before-
extract) could gain a graph-entity index; S4 (merge) could gain cross-FB relation edges.

### A2. Reranking — highest-precision-per-dollar S1.5/S5 lever (SHOULD-REFERENCE)

- `anush008/fastembed-rs` (⭐1k, Rust + ONNX) — local cross-encoder/bge-reranker embeddings, no
  PyTorch, runs on Apple Silicon. **SHOULD-REFERENCE** for a local rerank step after bge-m3 retrieval
  (C1/C3-clean). Peer-reviewed basis: cross-encoder reranking (Nogueira & Cho, 2019) + ColBERT
  late-interaction (Khattab & Zaharia, 2020).
- Maxwell currently uses FAISS cosine + source diversity (S1.5). A rerank pass is a known
  precision win, not a speculative one — but it adds a model load; gate behind a measurement.

### A3. Structured extraction — already covered, one marginal watch

- oMLX `guided_grammar_enabled` (per-model, `~/.omlx/model_settings.json`) + `pipeline/json_fixer.py`
  already give Maxwell grammar-constrained JSON decode — the *local* equivalent of `instructor` /
  `outlines` (both PyTorch/OpenAI-centric, so **REFERENCE-only** under C1/C2).
- `jndiogo/sibila` (⭐55) — structured extraction tuned for *local* llama.cpp/Ollama models.
  **WATCH**, marginal: niche but the only local-first structured-extraction lib of note.
- Peer-reviewed: constrained/grammar-constrained decoding (Weng 2023 review; Outlines 2024).

### A4. Peer-reviewed "developments" worth a footnote (not adoption)

- **DSPy** (Khattab et al., 2023/2024) — programmatic prompt/pipeline optimization; already ADAPT-
  relevant for prompt tuning (see prior A11 "DSPy pinning"). **REFERENCE.**
- **"Lost in the Middle"** (Liu et al., 2023) — long-context position bias; relevant to S1.5 chunk
  ordering. **REFERENCE** (already implicit in source-diversity clustering).
- **Corrective/Self-RAG** (Asai et al., 2023/2024) — retrieval self-correction; overlaps with S5
  verification (DeBERTa NLI). **REFERENCE** only — S5 is already fail-closed.

---

## B. Skill orchestration (goose recipes / MCP / subagents) — findings

### B1. MCP ecosystem — REFERENCE (C25 already mandates agent-agnostic MCP)

- `github/github-mcp-server` (⭐33k), `upstash/context7` (⭐62k, docs-MCP), `ChromeDevTools/
  chrome-devtools-mcp` (⭐52k) — canonical MCP-server references for how Maxwell should expose its
  own pipeline as MCP tools (C25: expose via MCP, no agent-specific coupling). **REFERENCE.**
- Maxwell is **agent-agnostic by constitution** — do NOT couple to any agent framework.

### B2. Agent frameworks — REFERENCE (patterns), never INTEGRATE

- `LangGraph`, `CrewAI`, `AutoGen`, `smolagents` — all Python/cloud-heavy, most are
  OpenAI/anthropic-first. Under C25/C2/C3 these are **pattern references only** (state machines,
  role decomposition, handoffs), not dependencies.
- Peer-reviewed: **CoALA** (Sumers et al., 2024 — cognitive architecture for language agents),
  **ReAct** (Yao et al., 2023), **Reflexion** (Shinn et al., 2023), **Toolformer** (Schick et al.,
  2023). Maxwell's goose recipe/subagent model already instantiates CoALA-style
  memory→decision→action loops; cite CoALA as the formal basis.

### B3. goose skills/recipes — the `skill.md` standard (already researched prior turn)

- The emerging **skill.md** standard (Anthropic "Agent Skills" + IBM's skill.md) is the relevant
  *development* for Maxwell's recipe format — **ADAPT** the schema (frontmatter name/description +
  imperative instructions) if/when Maxwell recipes outgrow YAML. Not urgent.

### B4. Workflow automation — WATCH only

- `n8n-io/n8n` (⭐205k) — self-hosted workflow automation with AI-agent nodes. **WATCH** as an
  orchestration-UX reference, but Node/JS and its own runtime = misaligned with Maxwell's Python
  pipeline (C5 zero-bloat).

---

## C. Recommendation (MUST / SHOULD / COULD)

| Tier | Item | Action |
|---|---|---|
| **MUST-REFERENCE** | `nano-graphrag` + GraphRAG paper | Map an FB knowledge-graph layer onto S1.5/S4 if a graph layer is added. |
| **MUST-REFERENCE** | MCP server patterns (`github-mcp-server`, `context7`) | Ground Maxwell's C25 MCP exposure. |
| **SHOULD-REFERENCE** | `fastembed-rs` local reranker (+ cross-encoder/ColBERT) | Measure a rerank pass after bge-m3 retrieval for S1.5/S5 precision. |
| **SHOULD-REFERENCE** | CoALA + ReAct + Reflexion (peer-reviewed) | Formal basis for recipe/subagent orchestration; cite in docs. |
| **ADAPT** | `LightRAG` (already flagged) + `skill.md` schema | Graph retrieval + recipe format evolution. |
| **WATCH** | `Graphify` (churn), `sibila`, `n8n` | Re-evaluate before any adoption. |
| **REFERENCE-only** | `graphrag` (Azure-tied), `instructor`/`outlines`, LangGraph/CrewAI | Patterns; do not add as deps (C2/C5). |

**Net:** no knowledge-pipeline or skill-orchestration tool displaces Maxwell's current S0–S6 +
goose-recipe design. The two concrete *upside* moves are (1) a **local rerank pass** (fastembed-rs
class) and (2) a **lightweight graph index** (nano-graphrag class) — both bandwidth/quality-side,
both gated behind a measurement before integration, in the same spirit as D-332.
