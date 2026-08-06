# D2205 — RAG Architecture Roadmap: 4-Model Synthesis & Adaptation
> **Date:** 2026-08-06
> **Status:** ACTIVE — Implementation roadmap
> **Source:** Cross-examination of Kimi, DeepSeek, Qwen, ChatGPT eval13 + direct codebase verification
> **Scope:** Retrieval layer, graph engineering, loop engineering, mesh engineering
> **Predecessors:** D2195-D2204 (immediate fixes), D2120 (cluster-before-extract), D2130 (feedback system), D2176 (RRF hybrid search)
> **Constitution anchors:** C1 ($0 marginal cost), C3 (sovereign), C21 (swappable infrastructure), C25 (agent-agnostic/MCP)

---

## EXECUTIVE SUMMARY

Four independent model families (Kimi/Moonshot, DeepSeek, Qwen, ChatGPT/OpenAI) converged on the same architectural verdict. This document captures the **verified, grounded, Maxwell-adapted** implementation plan that emerged from cross-examining every evaluator claim against the `main` branch codebase.

**Thesis:** Maxwell's ingestion pipeline (Stages 0-6) is best-in-class for sovereign knowledge extraction. The retrieval layer runs 2023-vintage architecture. Four targeted additions — all adapted to Maxwell's M1 Max/64GB/$0-marginal-cost constraints — close the gap.

---

## PART I: CROSS-EXAMINATION METHODOLOGY

Every evaluator claim was checked against:
- `pipeline/retrieve.py` (397 lines) — confirmed: 0 references to `related_fbs`, `contradicts_fbs`, `prerequisite_fbs`
- `pipeline/schemas.py` (902 lines) — confirmed: graph fields defined at lines 557-569, never queried
- `pipeline/feedback.py` (256 lines) — confirmed: post-hoc ratings only, no in-loop critique
- All 59 `pipeline/*.py` files — confirmed: 0 references to "MCP" or "mcp"
- `config/pipeline_config.yaml` — confirmed: `faiss_threshold: 0.75` vs `session_seed.yaml` `threshold: 0.70` mismatch
- `AGENTS.md` — confirmed: still says "9-stage" despite Stage 3 removal
- 1,077-line `buglog.md` — 8 open items including BUG-001 (empty pass loop), BUG-053 (Phi-4 hallucination)

**Claims rejected after code verification:** UMAP/HDBSCAN still in requirements (false — removed), zero-vector LLM fallback (partly outdated — D2196 added quarantine), "0 lines of orchestration" (misleading — 59 pipeline files exist; gap is agentic retrieval loop, not orchestration).

---

## PART II: ADAPTED IMPLEMENTATION PLAN

### P0 — Agentic Retrieval Loop (Week 1)

**What:** Iterative retrieval with structured critique and iteration budget.
**Why:** Single highest-impact change per line of code. Reuses existing infrastructure.
**Grounded in:** Self-RAG (ICLR 2024), CRAG (Google DeepMind 2024), Agentic RAG Survey (2026).
**Adapted for Maxwell:** No web search fallback (C3 violation). No tree-decoding (R7: temp=0.0). No training (C1).

#### Implementation Detail

**New file:** `pipeline/retrieval_evaluator.py`

```python
"""
retrieval_evaluator.py — CRAG-style retrieval quality evaluation.
===============================================================
Authority: D2205 (2026-08-06 RAG Architecture Roadmap)
Uses: Phi-4-mini (local, sovereign, already available)
Adapted: No web search fallback → alternative retrieval paths instead
         No tree-decoding → deterministic scoring only (temp=0.0 per R7)
"""

from dataclasses import dataclass, field
from typing import Literal

@dataclass
class CritiqueResult:
    """Structured critique of retrieval quality."""
    retrieval_quality: Literal["CORRECT", "PARTIAL", "INCORRECT", "CONTRADICTORY"]
    answered_aspects: list[str]
    missing_aspects: list[str]
    contradictions_found: list[dict]  # [{fb_a, fb_b, topic}]
    proposed_next_query: str | None
    confidence: float  # 0.0–1.0
    should_continue: bool
    rationale: str


def evaluate_retrieval(
    query: str,
    fbs: list[dict],
    model_provider: str = "maxwell_omlx",
    model_name: str = "phi-4-mini-instruct-8bit",
) -> CritiqueResult:
    """
    Classify retrieval quality and propose corrective action.

    Classification rules (CRAG pattern, adapted):
    - CORRECT: All FBs directly relevant, no gaps
    - PARTIAL: Some FBs relevant but aspects missing
    - INCORRECT: FBs irrelevant to query intent
    - CONTRADICTORY: FBs contain internal contradictions

    Adaptation from CRAG:
    - "Incorrect → web search" replaced with "Incorrect → broader retrieval / query reformulation"
    - "Ambiguous" merged into PARTIAL with explicit missing_aspects

    NOTE on BUG-053: Phi-4-mini HALLUCINATES on open-ended research.
    This function uses it for CLASSIFICATION of provided text (FBs), not
    open-ended generation. The source text (FBs + query) is always provided.

    Returns CritiqueResult with structured scores.
    """
    # Build evaluation prompt from fbs and query
    prompt = _build_critique_prompt(query, fbs)
    response = _call_model(prompt, model_provider, model_name)
    result = _parse_critique_json(response)
    _validated = _validate_critique(result, query, fbs)
    return _validated


def _build_critique_prompt(query: str, fbs: list[dict]) -> str:
    """Build structured critique prompt with FB summaries."""
    fb_summaries = []
    for fb in fbs[:15]:  # Evaluate top-15
        fb_summaries.append(
            f"FB-{fb.get('fb_id','?')}: {fb.get('name','')[:200]}\n"
            f"  Domain: {fb.get('domains','')}\n"
            f"  Definition: {fb.get('definition','')[:300]}"
        )
    return f"""EVALUATE retrieval quality for: "{query}"

Retrieved Foundation Blocks:
{chr(10).join(fb_summaries)}

Output JSON:
{{
  "retrieval_quality": "CORRECT|PARTIAL|INCORRECT|CONTRADICTORY",
  "answered_aspects": ["aspect 1", "aspect 2"],
  "missing_aspects": ["aspect A", "aspect B"],
  "contradictions_found": [{{"fb_a": "FB-001", "fb_b": "FB-045", "topic": "..."}}],
  "proposed_next_query": "refined query or null",
  "confidence": 0.0-1.0,
  "should_continue": true/false,
  "rationale": "one sentence"
}}"""


def _parse_critique_json(response: str) -> dict:
    """Parse LLM response into CritiqueResult fields."""
    import json
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        # D2205 fallback: if JSON parse fails, treat as PARTIAL
        return {
            "retrieval_quality": "PARTIAL",
            "answered_aspects": [],
            "missing_aspects": ["json_parse_failed"],
            "contradictions_found": [],
            "proposed_next_query": None,
            "confidence": 0.3,
            "should_continue": True,
            "rationale": "JSON parse failed — assuming partial retrieval"
        }
    return data


def _validate_critique(result: dict, query: str, fbs: list[dict]) -> CritiqueResult:
    """Validate and coerce critique output to CritiqueResult."""
    valid_qualities = {"CORRECT", "PARTIAL", "INCORRECT", "CONTRADICTORY"}
    quality = result.get("retrieval_quality", "PARTIAL")
    if quality not in valid_qualities:
        quality = "PARTIAL"
    return CritiqueResult(
        retrieval_quality=quality,
        answered_aspects=result.get("answered_aspects", []),
        missing_aspects=result.get("missing_aspects", []),
        contradictions_found=result.get("contradictions_found", []),
        proposed_next_query=result.get("proposed_next_query"),
        confidence=float(result.get("confidence", 0.5)),
        should_continue=bool(result.get("should_continue", True)),
        rationale=str(result.get("rationale", "")),
    )
```

**Modified file:** `pipeline/retrieve.py` — add `agentic_search()` function

```python
# Add after existing search_hybrid() function (line ~250)

@dataclass
class EvidencePack:
    """D2205: Typed evidence package for agentic retrieval.
    
    Carries query, retrieved FBs, critique results, and iteration metadata.
    Every component consumes/produces this object instead of passing 
    arbitrary strings around — reduces agentic hallucination.
    """
    query: str
    fbs: list[dict]
    critique: "CritiqueResult | None" = None
    iterations: int = 1
    exhausted: bool = False


def agentic_search(
    conn: sqlite3.Connection,
    query: str,
    max_iterations: int = 3,
    confidence_threshold: float = 0.85,
    limit: int = 20,
    exclude_summaries: bool = True,
    domain: str | None = None,
) -> EvidencePack:
    """D2205: Agentic retrieval with structured critique and iteration budget.

    Stop conditions (in priority order):
    1. confidence >= confidence_threshold → return
    2. retrieval_quality == "CORRECT" → return
    3. iteration == max_iterations → return with exhausted=True
    4. retrieval_quality == "INCORRECT" → fallback to broader search, then return

    Adapted from Self-RAG + CRAG:
    - No web search fallback (sovereign constraint C3)
    - No tree-decoding / beam search (temp=0.0 constraint R7)
    - No training required (C1: $0 marginal cost)
    
    Iteration budget: 3 rounds maximum (Agentic RAG 2026 best practice).
    Token overhead: ~3× single-shot cost on partial queries, ~1× on correct.
    """
    from pipeline.retrieval_evaluator import evaluate_retrieval, CritiqueResult

    current_query = query
    all_fbs: dict[str, dict] = {}  # Deduplicate across iterations
    
    for i in range(max_iterations):
        # 1. Retrieve
        results = search_hybrid(
            conn, current_query,
            limit=limit,
            exclude_summaries=exclude_summaries,
            domain=domain,
        )
        
        # Track FBs across iterations (dedup by fb_id)
        for fb in results:
            fid = fb.get("fb_id", fb.get("id", ""))
            if fid:
                all_fbs[fid] = fb
        
        # 2. Critique
        critique: CritiqueResult = evaluate_retrieval(query, list(all_fbs.values()))
        
        # 3. Decide
        if critique.confidence >= confidence_threshold:
            # Good enough — return
            return EvidencePack(
                query=query,
                fbs=list(all_fbs.values()),
                critique=critique,
                iterations=i + 1,
            )
        
        if critique.retrieval_quality == "CORRECT":
            return EvidencePack(
                query=query,
                fbs=list(all_fbs.values()),
                critique=critique,
                iterations=i + 1,
            )
        
        if critique.retrieval_quality == "INCORRECT":
            # Broaden search: drop domain filter, increase limit
            if domain:
                results = search_hybrid(conn, current_query, limit=limit * 2)
                return EvidencePack(
                    query=query,
                    fbs=results,
                    critique=critique,
                    iterations=i + 1,
                    exhausted=True,
                )
            # No domain filter to drop — return what we have
            return EvidencePack(
                query=query,
                fbs=list(all_fbs.values()),
                critique=critique,
                iterations=i + 1,
                exhausted=True,
            )
        
        # 4. Continue: refine query
        if critique.proposed_next_query and i < max_iterations - 1:
            current_query = critique.proposed_next_query
        # else: will exit loop and return with exhausted=True
    
    # Exhausted iteration budget
    return EvidencePack(
        query=query,
        fbs=list(all_fbs.values()),
        critique=critique,
        iterations=max_iterations,
        exhausted=True,
    )
```

**CLI addition to `retrieve.py` main():**

```python
# Add --agentic flag
parser.add_argument("--agentic", action="store_true",
                    help="D2205: Use agentic retrieval with critique loop")
# In main():
if args.agentic:
    pack = agentic_search(conn, args.query or args.hybrid, 
                         domain=args.domain, limit=args.limit)
    print(f"Iterations: {pack.iterations}, Exhausted: {pack.exhausted}")
    if pack.critique:
        print(f"Quality: {pack.critique.retrieval_quality}, "
              f"Confidence: {pack.critique.confidence:.2f}")
```

**Effort:** 1.5 days
**Dependencies:** None (reuses existing `retrieve.py`, `providers/base.py`, Phi-4-mini)
**Risk:** BUG-053 (Phi-4 hallucination on open-ended tasks) — mitigated because evaluator classifies provided text, not generates open-ended research.
**Memory impact:** Negligible (Phi-4-mini already loaded; critique prompt ~2K tokens)
**Verification:** Run against existing golden set (25 examples) — measure whether agentic search finds FBs that single-shot misses. Target: ≥15% recall improvement on multi-aspect queries.

---

### P1 — Graph Traversal Layer (Week 1-2)

**What:** Activate `related_fbs`, `contradicts_fbs`, `prerequisite_fbs` for query-time graph expansion.
**Why:** Data exists but is never queried. Zero new dependencies. Immediate differentiation.
**Grounded in:** HippoRAG2 (PPR, 2025), FalkorDB GraphRAG-SDK (5-path retrieval, 2026), WildGraphBench (2026).
**Adapted for Maxwell:** No external graph DB (SQLite adjacency list + in-memory BFS). No Neo4j (C1 cost, C3 sovereignty). No Cypher (overengineered for current scale).

#### Implementation Detail

**New method in `pipeline/retrieve.py`:**

```python
def graph_expand(
    conn: sqlite3.Connection,
    fb_ids: list[str],
    hops: int = 2,
    include_contradictions: bool = True,
    include_prerequisites: bool = True,
) -> dict[str, dict]:
    """D2205: BFS graph expansion over SQLite adjacency list.

    Traverses related_fbs (undirected), contradicts_fbs (bidirectional warning),
    and prerequisite_fbs (directed dependency) edges stored in the fbs table.

    No external graph DB. No Cypher. Pure SQLite + in-memory BFS.

    Returns:
        {
            fb_id: {
                "related": [list of related FB dicts],
                "contradicts": [list of contradicting FB dicts],
                "prerequisites": [list of prerequisite FB dicts],
            }
        }

    Memory: O(V+E) for BFS frontier. Typical: 20 seed FBs × 2 hops 
            ≈ 100-200 FBs in memory. Negligible on 64GB.
    """
    import json
    from collections import deque

    visited: set[str] = set(fb_ids)
    frontier = deque(fb_ids)
    result: dict[str, dict] = {fid: {"related": [], "contradicts": [], "prerequisites": []} 
                                for fid in fb_ids}
    current_hop = 0

    while frontier and current_hop < hops:
        level_size = len(frontier)
        for _ in range(level_size):
            current_id = frontier.popleft()

            # Fetch edges from DB
            row = conn.execute(
                """SELECT fb_id, related_fbs, contradicts_fbs, prerequisite_fbs
                   FROM fbs WHERE fb_id = ?""",
                (current_id,)
            ).fetchone()

            if not row:
                continue

            # Expand related_fbs
            if row["related_fbs"]:
                try:
                    related = json.loads(row["related_fbs"]) if isinstance(row["related_fbs"], str) else row["related_fbs"]
                except json.JSONDecodeError:
                    related = []
                for rel in related:
                    rel_id = rel.get("fb_id") if isinstance(rel, dict) else rel
                    if rel_id and rel_id not in visited:
                        visited.add(rel_id)
                        frontier.append(rel_id)
                        if current_id not in result:
                            result[current_id] = {"related": [], "contradicts": [], "prerequisites": []}
                        result[current_id]["related"].append(rel)

            # Expand contradicts_fbs (bidirectional warning)
            if include_contradictions and row["contradicts_fbs"]:
                try:
                    contradicts = json.loads(row["contradicts_fbs"]) if isinstance(row["contradicts_fbs"], str) else row["contradicts_fbs"]
                except json.JSONDecodeError:
                    contradicts = []
                for cid in contradicts:
                    if cid and cid not in visited:
                        visited.add(cid)
                        frontier.append(cid)
                        if current_id not in result:
                            result[current_id] = {"related": [], "contradicts": [], "prerequisites": []}
                        result[current_id]["contradicts"].append(cid)

                        # Fetch contradicting FB details
                        crow = conn.execute(
                            "SELECT fb_id, name, definition FROM fbs WHERE fb_id = ?",
                            (cid,)
                        ).fetchone()
                        if crow:
                            result[cid] = {"related": [], "contradicts": [current_id], "prerequisites": []}

            # Expand prerequisite_fbs (directed — only fetch upstream)
            if include_prerequisites and row["prerequisite_fbs"]:
                try:
                    prereqs = json.loads(row["prerequisite_fbs"]) if isinstance(row["prerequisite_fbs"], str) else row["prerequisite_fbs"]
                except json.JSONDecodeError:
                    prereqs = []
                for pid in prereqs:
                    if pid and pid not in visited:
                        visited.add(pid)
                        frontier.append(pid)
                        if current_id not in result:
                            result[current_id] = {"related": [], "contradicts": [], "prerequisites": []}
                        result[current_id]["prerequisites"].append(pid)

                        # Fetch prerequisite FB details
                        prow = conn.execute(
                            "SELECT fb_id, name, definition FROM fbs WHERE fb_id = ?",
                            (pid,)
                        ).fetchone()
                        if prow:
                            result[pid] = {"related": [], "contradicts": [], "prerequisites": []}

        current_hop += 1

    return result


def graph_aware_search(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20,
    graph_hops: int = 2,
    domain: str | None = None,
) -> list[dict]:
    """D2205: Hybrid search + graph expansion pipeline.

    Pipeline:
    1. search_hybrid → top-N seed FBs
    2. graph_expand → 1-2 hop neighbors
    3. Deduplicate by fb_id
    4. Rerank by: borp_score × feedback_score × (1.0 / graph_distance)
    5. Return top-k

    Result: Retrieves FBs that are semantically close AND structurally connected,
    not just semantically close. Surfaces contradictions alongside support.
    """
    # 1. Seed retrieval
    seeds = search_hybrid(conn, query, limit=limit, domain=domain)
    seed_ids = [s.get("fb_id", s.get("id", "")) for s in seeds if s.get("fb_id") or s.get("id")]

    # 2. Graph expansion
    graph = graph_expand(conn, seed_ids, hops=graph_hops)

    # 3. Collect all unique FBs
    all_fb_ids = set(seed_ids)
    for fid, edges in graph.items():
        all_fb_ids.add(fid)
        for rel in edges.get("related", []):
            rid = rel.get("fb_id") if isinstance(rel, dict) else rel
            if rid:
                all_fb_ids.add(rid)
        for cid in edges.get("contradicts", []):
            all_fb_ids.add(cid)
        for pid in edges.get("prerequisites", []):
            all_fb_ids.add(pid)

    # 4. Fetch all FBs with scores
    placeholders = ",".join("?" * len(all_fb_ids))
    rows = conn.execute(
        f"""SELECT *, 
            COALESCE(borp_score, 0.5) as borp,
            COALESCE(feedback_score, 0.5) as feedback
            FROM fbs 
            WHERE fb_id IN ({placeholders})
            AND (classification_status IS NULL OR classification_status != 'FAILED')
            ORDER BY borp DESC, feedback DESC""",
        list(all_fb_ids)
    ).fetchall()

    results = [dict(r) for r in rows]

    # 5. Attach graph metadata
    for fb in results:
        fid = fb.get("fb_id", "")
        if fid in graph:
            fb["_graph"] = graph[fid]
            fb["_is_seed"] = fid in seed_ids

    return results
```

**Effort:** 1.5 days
**Dependencies:** FBs must have `related_fbs`, `contradicts_fbs`, `prerequisite_fbs` populated (Stage 4 merge populates these)
**Risk:** Low. Read-only BFS over existing data. No writes. Memory bounded by BFS frontier size.
**Memory impact:** ~100-200 FBs × ~2KB each = ~400KB. Negligible.
**Verification:** Query retention test — for 10 complex queries, compare graph_aware_search vs search_hybrid. Target: ≥3 additional relevant FBs found via graph expansion per query.

---

### P2 — MCP Server (Week 2)

**What:** Expose Maxwell FB store as MCP server so any MCP-native agent can query it.
**Why:** Immediate integration with Goose, Claude Code, Cursor, Open WebUI. No custom agent harness needed.
**Grounded in:** MCP protocol (Anthropic 2024, adopted by OpenAI/Google/Microsoft), A2A (Google 2025).
**Adapted for Maxwell:** 3 tools only (not 10+). Stateless server. Read-only path only (execution logging is write path — gated behind authentication for now).

#### Implementation Detail

**New file:** `maxwell_mcp_server.py` (project root)

```python
#!/usr/bin/env python3
"""
maxwell_mcp_server.py — Maxwell OS MCP Knowledge Server
=========================================================
Authority: D2205 (2026-08-06 RAG Architecture Roadmap)
Protocol: MCP (Model Context Protocol) — Anthropic 2024
Constitution: C25 (agent-agnostic, MCP exposure)

Exposes Maxwell's FB knowledge store as 3 MCP tools:
  1. query_knowledge — hybrid + graph-aware search
  2. get_fb_detail — full FB with evidence, contradictions, prerequisites
  3. get_fb_reliability — execution history and trust scores

Usage:
    # Register with Claude Desktop:
    # claude_desktop_config.json → { "mcpServers": { "maxwell": { "command": "python3", "args": ["maxwell_mcp_server.py"] } } }
    
    # Or with Goose:
    # goose session start --extensions mcp -- maxwell_mcp_server.py

Design decisions (D2205):
    - Stateless: no session storage. Each call is independent.
    - Read-only v1: execution logging deferred to v2 (needs auth/sandbox).
    - SQLite readonly connection: crash-safe, no concurrent write conflicts.
    - No external dependencies beyond Python stdlib + mcp SDK.
"""

import json
import sqlite3
from pathlib import Path

# MCP SDK
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Maxwell internal
from pipeline.pipeline_paths import DB_PATH
from pipeline.retrieve import search_hybrid, graph_aware_search

# ── Server setup ──────────────────────────────────────────────────
server = Server("maxwell-os-knowledge")


def _get_readonly_conn() -> sqlite3.Connection:
    """Get crash-safe readonly connection."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Maxwell DB not found: {DB_PATH}")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ── Tool 1: query_knowledge ────────────────────────────────────────

@server.tool()
async def query_knowledge(
    query: str,
    domain: str | None = None,
    depth: str | None = None,
    graph_aware: bool = True,
    include_contradictions: bool = True,
    limit: int = 10,
) -> list[TextContent]:
    """Search Maxwell's knowledge graph for Foundation Blocks matching a query.

    Uses hybrid retrieval (FTS5 + vector + keyword → RRF fusion) with 
    optional graph expansion (related FBs, contradictions, prerequisites).

    Args:
        query: Natural language search query
        domain: Optional domain filter (e.g., "pricing", "strategy", "ai & agents")
        depth: Optional depth filter ("universal", "domain", "contextual")
        graph_aware: Enable graph expansion for connected FBs
        include_contradictions: Surface contradicting FBs for balanced view
        limit: Maximum results (1-50)

    Returns:
        Ranked list of FBs with fb_id, name, definition, domains, borp_score, 
        feedback_score, and (if graph_aware) graph relationship metadata.
    """
    conn = _get_readonly_conn()
    try:
        if graph_aware:
            results = graph_aware_search(
                conn, query, limit=limit, domain=domain
            )
        else:
            results = search_hybrid(
                conn, query, limit=limit, domain=domain
            )

        # Format for agent consumption
        output = []
        for i, fb in enumerate(results[:limit]):
            entry = {
                "rank": i + 1,
                "fb_id": fb.get("fb_id", fb.get("id", "")),
                "name": fb.get("name", ""),
                "definition": fb.get("definition", "")[:500],
                "domains": fb.get("domains", ""),
                "depth": fb.get("depth", ""),
                "borp_score": fb.get("borp_score"),
                "feedback_score": fb.get("feedback_score"),
            }
            if graph_aware and "_graph" in fb:
                g = fb["_graph"]
                if g.get("contradicts"):
                    entry["⚠️_contradicted_by"] = g["contradicts"]
                if g.get("prerequisites"):
                    entry["📋_prerequisites"] = g["prerequisites"]
                if g.get("related"):
                    entry["🔗_related"] = [r.get("fb_id") if isinstance(r, dict) else r for r in g["related"][:5]]
            output.append(entry)

        return [TextContent(
            type="text",
            text=json.dumps({
                "query": query,
                "total_results": len(output),
                "graph_aware": graph_aware,
                "contradictions_included": include_contradictions,
                "results": output,
            }, indent=2)
        )]
    finally:
        conn.close()


# ── Tool 2: get_fb_detail ──────────────────────────────────────────

@server.tool()
async def get_fb_detail(
    fb_id: str,
    include_evidence: bool = True,
    include_graph: bool = True,
) -> list[TextContent]:
    """Get complete details for a specific Foundation Block.

    Returns full FB record including evidence passages, source books,
    verification results, and graph relationships.

    Args:
        fb_id: Foundation Block ID (e.g., "FB-042")
        include_evidence: Include source evidence passages
        include_graph: Include related/contradicting/prerequisite FBs

    Returns:
        Full FB record with all requested detail levels.
    """
    conn = _get_readonly_conn()
    try:
        row = conn.execute(
            "SELECT * FROM fbs WHERE fb_id = ?", (fb_id,)
        ).fetchone()
        
        if not row:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"FB not found: {fb_id}"})
            )]
        
        fb = dict(row)
        
        # Clean up for agent consumption
        output = {
            "fb_id": fb.get("fb_id"),
            "name": fb.get("name"),
            "definition": fb.get("definition"),
            "domains": fb.get("domains"),
            "discipline": fb.get("discipline"),
            "depth": fb.get("depth"),
            "status": fb.get("status"),
            "classification_status": fb.get("classification_status"),
            "borp_score": fb.get("borp_score"),
            "confidence_score": fb.get("confidence_score"),
            "feedback_score": fb.get("feedback_score"),
            "feedback_count": fb.get("feedback_count"),
            "usage_count": fb.get("usage_count"),
            "source_books": fb.get("source_books", []),
            "keywords": fb.get("keywords", []),
        }
        
        if include_evidence:
            output["evidence_passages"] = fb.get("evidence_passages_shown", 
                                                   fb.get("evidence_passages", []))
            output["verification_results"] = fb.get("verification_results")
        
        if include_graph:
            output["related_fbs"] = fb.get("related_fbs", [])
            output["contradicts_fbs"] = fb.get("contradicts_fbs", [])
            output["prerequisite_fbs"] = fb.get("prerequisite_fbs", [])
            output["procedural_skill"] = fb.get("procedural_skill")
        
        return [TextContent(
            type="text",
            text=json.dumps(output, indent=2, default=str)
        )]
    finally:
        conn.close()


# ── Tool 3: get_fb_reliability ──────────────────────────────────────

@server.tool()
async def get_fb_reliability(
    fb_id: str,
) -> list[TextContent]:
    """Get execution reliability history for a Foundation Block.

    Returns feedback statistics, execution outcomes, and trust metrics.
    This is Maxwell's differentiating feature: execution-based reliability.

    Args:
        fb_id: Foundation Block ID

    Returns:
        Reliability metrics including feedback score, usage count,
        retrieval history, and (when available) execution outcomes.
    """
    conn = _get_readonly_conn()
    try:
        from pipeline.feedback import get_fb_feedback_stats
        stats = get_fb_feedback_stats(fb_id, DB_PATH)
        
        # Also get the FB's basic trust metrics
        row = conn.execute(
            "SELECT fb_id, name, borp_score, confidence_score, "
            "feedback_score, feedback_count, usage_count, "
            "last_retrieved_at, status, classification_status "
            "FROM fbs WHERE fb_id = ?",
            (fb_id,)
        ).fetchone()
        
        if not row:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"FB not found: {fb_id}"})
            )]
        
        fb = dict(row)
        output = {
            "fb_id": fb.get("fb_id"),
            "name": fb.get("name"),
            "trust_metrics": {
                "borp_score": fb.get("borp_score"),
                "confidence_score": fb.get("confidence_score"),
                "feedback_score": fb.get("feedback_score"),
                "feedback_count": fb.get("feedback_count"),
                "usage_count": fb.get("usage_count"),
                "last_retrieved_at": fb.get("last_retrieved_at"),
                "status": fb.get("status"),
                "classification_status": fb.get("classification_status"),
            },
            "feedback_history": stats,
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(output, indent=2, default=str)
        )]
    finally:
        conn.close()


# ── Server lifecycle ────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Register tools with MCP client."""
    return [
        Tool(
            name="query_knowledge",
            description="Search Maxwell's knowledge graph for Foundation Blocks. Supports hybrid retrieval with optional graph expansion for related/contradicting FBs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language search query"},
                    "domain": {"type": "string", "description": "Optional domain filter"},
                    "depth": {"type": "string", "enum": ["universal", "domain", "contextual"]},
                    "graph_aware": {"type": "boolean", "default": True},
                    "include_contradictions": {"type": "boolean", "default": True},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_fb_detail",
            description="Get complete details for a specific Foundation Block including evidence, verification results, and graph relationships.",
            inputSchema={
                "type": "object",
                "properties": {
                    "fb_id": {"type": "string", "description": "Foundation Block ID (e.g., FB-042)"},
                    "include_evidence": {"type": "boolean", "default": True},
                    "include_graph": {"type": "boolean", "default": True},
                },
                "required": ["fb_id"],
            },
        ),
        Tool(
            name="get_fb_reliability",
            description="Get execution reliability history for a Foundation Block — Maxwell's differentiating feature.",
            inputSchema={
                "type": "object",
                "properties": {
                    "fb_id": {"type": "string", "description": "Foundation Block ID"},
                },
                "required": ["fb_id"],
            },
        ),
    ]


# ── Entry point ─────────────────────────────────────────────────────

async def main() -> None:
    """Run Maxwell MCP server via stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

**Effort:** 1 day
**Dependencies:** `mcp` Python SDK (`pip install mcp`), existing `retrieve.py` and `feedback.py`
**Risk:** Low. Read-only. SQLite readonly mode. No state mutation.
**Verification:** Register with Goose, query "what are the key principles about pricing strategy?" — should return ranked FBs.

---

### P3 — Evidence Pack & Two-Axis Epistemic Model (Week 2-3)

**What:** Replace single `confidence_score` with two-axis model: Evidence axis (source support, independence, contradiction) + Execution axis (trials, success rate, context similarity).
**Why:** Current scalar `confidence_score` masks whether confidence comes from evidence or execution. These are qualitatively different.
**Grounded in:** FActScore (2023), Trust-RAG Compass (2026), ChatGPT's atomic claim decomposition.
**Adapted for Maxwell:** No training required. Schema addition only. Backward compatible (old `confidence_score` derivable from evidence axis).

#### Schema Addition

**New columns in `fbs` table (via migration):**

```sql
-- D2205: Two-axis epistemic model
ALTER TABLE fbs ADD COLUMN evidence_support REAL;         -- 0.0-1.0 source support
ALTER TABLE fbs ADD COLUMN evidence_independence REAL;     -- 0.0-1.0 source independence
ALTER TABLE fbs ADD COLUMN evidence_contradiction REAL;    -- 0.0-1.0 contradiction level
ALTER TABLE fbs ADD COLUMN evidence_coverage REAL;         -- 0.0-1.0 claim coverage
ALTER TABLE fbs ADD COLUMN execution_trials INTEGER DEFAULT 0;
ALTER TABLE fbs ADD COLUMN execution_successes INTEGER DEFAULT 0;
ALTER TABLE fbs ADD COLUMN execution_context_similarity REAL;  -- 0.0-1.0
ALTER TABLE fbs ADD COLUMN epistemic_state TEXT DEFAULT 'corroborated';
    -- One of: corroborated, partially_supported, contested, source_supported,
    --          unresolved, contradicted, execution_tested, retired
```

**Migration script:** `pipeline/migrate_D2205_epistemic.py`

```python
"""
migrate_D2205_epistemic.py — Add two-axis epistemic model columns.
===============================================================
Authority: D2205 (2026-08-06)
Crash-safe: tempfile → fsync → os.replace (C6)
"""

def migrate(conn: sqlite3.Connection) -> None:
    """Add D2205 epistemic model columns. Idempotent."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(fbs)")}
    
    columns = {
        "evidence_support": "REAL",
        "evidence_independence": "REAL", 
        "evidence_contradiction": "REAL",
        "evidence_coverage": "REAL",
        "execution_trials": "INTEGER DEFAULT 0",
        "execution_successes": "INTEGER DEFAULT 0",
        "execution_context_similarity": "REAL",
        "epistemic_state": "TEXT DEFAULT 'corroborated'",
    }
    
    for col_name, col_type in columns.items():
        if col_name not in existing:
            conn.execute(f"ALTER TABLE fbs ADD COLUMN {col_name} {col_type}")
    
    # Backfill from existing data
    conn.execute("""
        UPDATE fbs SET 
            evidence_support = COALESCE(borp_score, 0.5),
            evidence_independence = 0.5,
            evidence_contradiction = 0.0,
            evidence_coverage = 0.5,
            execution_trials = COALESCE(feedback_count, 0),
            execution_successes = CAST(COALESCE(feedback_count, 0) * COALESCE(feedback_score, 0.5) AS INTEGER)
        WHERE evidence_support IS NULL
    """)
    conn.commit()
```

**EvidencePack dataclass (add to `pipeline/retrieve.py`):**

```python
@dataclass
class EvidenceScore:
    """D2205: Evidence axis — what sources tell us."""
    support: float             # 0.0-1.0 source support strength
    independence: float        # 0.0-1.0 source independence (corrected for citation chains)
    contradiction: float       # 0.0-1.0 contradiction level
    coverage: float            # 0.0-1.0 claim coverage completeness

@dataclass
class ExecutionScore:
    """D2205: Execution axis — what empirical outcomes tell us."""
    trials: int                # Total execution attempts
    successes: int             # Successful outcomes
    success_rate: float        # successes / trials (with Beta prior for small N)
    context_similarity: float  # 0.0-1.0 how similar current context is to execution contexts
    posterior_mean: float      # Bayesian posterior mean with Beta(1,1) prior

@dataclass
class EvidencePack:
    """D2205: Complete evidence package for agent consumption.
    
    Replaces arbitrary string passing between components.
    Every Maxwell component consumes/produces this object.
    """
    query: str
    fbs: list[dict]
    critique: "CritiqueResult | None" = None
    evidence_axis: EvidenceScore | None = None
    execution_axis: ExecutionScore | None = None
    iterations: int = 1
    exhausted: bool = False
    contradictions_surfaced: list[dict] = field(default_factory=list)
    source_independence_graph: dict = field(default_factory=dict)
```

**Effort:** 2 days (schema migration + migration script + EvidencePack integration)
**Dependencies:** P0 (CritiqueResult) and P1 (graph_expand) provide input data
**Risk:** Low. Additive schema change. Backward compatible.
**Verification:** After migration, `PRAGMA table_info(fbs)` shows new columns. EvidencePack round-trips through retrieve → critique → format.

---

## PART III: WHAT WAS REJECTED (AND WHY)

These proposals from evaluators were considered but REJECTED for Maxwell's constraints:

| Proposal | Evaluator | Rejection Reason |
|:---------|:----------|:-----------------|
| Full Self-RAG with reflection tokens | Kimi | Requires training special model (C1 violation). temp=0.0 blocks beam search (R7). |
| CRAG web search fallback | Kimi, DeepSeek | Data leaves machine (C3 violation). Replaced with broader local retrieval. |
| ColBERT late interaction | ChatGPT §22 | Memory-prohibitive on M1 Max with other models loaded. Token-level embeddings × 100 candidates = GBs. |
| Full RAPTOR hierarchy on all chunks | ChatGPT §5, Qwen §2A | 564 min already for flat embedding. Recursive summarization = weeks on M1 Max. |
| vllm-mlx migration | Kimi §5.4 | "1 day" estimate is unrealistic. Production MLX serving migration is 1-2 weeks of integration testing. Deferred to P4. |
| Multi-agent swarm | Rejected by all 4 | Coordination tax 39-70% (Google Research). M1 Max memory budget cannot support 5+ agents × models. |
| Neo4j graph database | DeepSeek, Kimi | External service (C3). SQLite adjacency list sufficient for current scale (4K-6K FBs). |
| LangChain/LlamaIndex dependency | ChatGPT §43 | Violates "no vendor lock-in" (C2). Maxwell's pipeline is already cleaner. |
| Training a custom model | Kimi | Violates C1 ($0 marginal cost) and requires GPU cluster. |
| Replace NLI with LLM-as-judge | DeepSeek §4.1 | Too expensive at scale (LLM call per FB). Keep NLI for triage, LLM for escalation. |

---

## PART IV: DEPENDENCY GRAPH

```
P0 (Agentic Retrieval) ─────────────────┐
  └─ requires: retrieve.py, providers/  │
     base.py, Phi-4-mini                │
                                        ├──→ P3 (Evidence Pack)
P1 (Graph Traversal) ───────────────────┤
  └─ requires: schemas.py fields        │
     populated by S4 merge              │
                                        │
P2 (MCP Server) ────────────────────────┘
  └─ requires: P0 + P1 for full
     functionality, but can deploy
     with search_hybrid only first

P3 (Evidence Pack) ─────────────────────
  └─ requires: P0 (CritiqueResult) + 
     P1 (graph data)
```

**Parallelizable:** P0 and P1 can be built simultaneously. P2 can start with basic search_hybrid and add graph-aware once P1 lands. P3 integrates P0+P1 outputs.

---

## PART V: VERIFICATION PLAN

Each phase has a specific, measurable gate:

### P0 Gate
```bash
# Run agentic search on 10 golden queries
python3 pipeline/retrieve.py --agentic "what are the key principles of pricing strategy?"
# Expected: ≥2 iterations for complex queries, 1 for simple
# Expected: critique JSON in output with answered_aspects, missing_aspects
# Gate: agentic search finds ≥15% more relevant FBs than single-shot on multi-aspect queries
```

### P1 Gate
```bash
# Compare graph-aware vs flat search
python3 pipeline/retrieve.py --graph-aware "how does systems thinking apply to organizations?"
# Expected: _graph field in results showing related/contradicts/prerequisites
# Expected: contradiction FBs surfaced when query is controversial
# Gate: graph expansion adds ≥3 relevant FBs per complex query
```

### P2 Gate
```bash
# Register with Goose or Claude Desktop
# Query: "what does maxwell know about feedback loops?"
# Expected: Ranked FB list with scores
# Gate: Goose can successfully call all 3 tools
```

### P3 Gate
```bash
# After migration
python3 -c "
import sqlite3
conn = sqlite3.connect('data/knowledge_base.db')
cols = [r[1] for r in conn.execute('PRAGMA table_info(fbs)')]
assert 'evidence_support' in cols
assert 'epistemic_state' in cols
print('D2205 migration verified')
"
```

---

## PART VI: TOTAL EFFORT ESTIMATE

| Phase | Task | Effort | Cumulative |
|:------|:-----|:-------|:-----------|
| P0 | Retrieval evaluator + critique + agentic loop | 1.5 days | 1.5 days |
| P1 | Graph traversal layer (graph_expand + graph_aware_search) | 1.5 days | 3.0 days |
| P2 | MCP server (3 tools) | 1.0 day | 4.0 days |
| P3 | Two-axis epistemic model + EvidencePack + migration | 2.0 days | 6.0 days |
| — | Integration testing + golden set validation | 1.0 day | 7.0 days |
| **Total** | | **7 days** | |

---

## CROSS-REFERENCES

| ID | Document |
|:---|:---------|
| D2120 | Stage 3 removal (cluster-before-extract) |
| D2130 | Feedback system (post-hoc ratings) |
| D2176 | RRF hybrid search |
| D2195 | Cross-examination ultimate verdict |
| D2196 | Zero-vector EmbeddingQuarantineError |
| D2197-D2204 | Immediate fixes (session_seed, AGENTS, model_assign, lockfile, etc.) |
| BUG-053 | Phi-4-mini hallucinates on open-ended research |
| CONSTITUTION.md §2.3 | Retrieval architecture |
| CONSTITUTION.md §C1, C3, C25 | Sovereign, $0 cost, MCP exposure constraints |
