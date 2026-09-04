#!/usr/bin/env python3
"""
maxwell_mcp_server.py — Maxwell OS MCP Knowledge Server
=========================================================
Authority: D2205 P2 (2026-08-06 RAG Architecture Roadmap)
Protocol: MCP (Model Context Protocol) — Anthropic 2024
Constitution: C25 (Agent-Agnostic, MCP exposure), C3 (sovereign),
              C1 ($0 marginal cost), C12 (no hardcoding)

Exposes Maxwell's FB knowledge store via MCP with 3 tools:
  1. query_knowledge — Hybrid + graph-aware + agentic search
  2. get_fb_detail — Full FB with evidence, contradictions, prerequisites
  3. get_fb_reliability — Execution history and trust metrics

Usage:
    # Direct mode (stdio transport for MCP clients):
    python3 maxwell_mcp_server.py

    # Register with Claude Desktop:
    # { "mcpServers": { "maxwell": {
    #     "command": "python3",
    #     "args": ["maxwell_mcp_server.py"]
    # }}}

    # Test connectivity:
    python3 maxwell_mcp_server.py --test
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

# Maxwell internal
sys.path.insert(0, str(Path(__file__).resolve().parent))
PROJECT_ROOT: Path = Path(__file__).resolve().parent  # BUG-220-MCP: containment root for delegate_local file guard
from pipeline.pipeline_paths import (
    DB_PATH,
    MCP_DELEGATE_ALLOW_ABSOLUTE_PATHS,
    MCP_DELEGATE_ALLOWED_MODELS,
    MCP_DELEGATE_MAX_FILES,
    MCP_DELEGATE_MAX_SYSTEM_CHARS,
)
from pipeline.retrieve import search_hybrid, graph_aware_search, agentic_search, EvidencePack
from pipeline.feedback import get_fb_feedback_stats
from pipeline.omlx_delegate import delegate_omlx  # BUG-063: file-grounded local delegation (C25)

# MCP SDK
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# ── Helpers ────────────────────────────────────────────────────────────

def _get_readonly_conn() -> sqlite3.Connection:
    """Get crash-safe readonly connection to Maxwell DB."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Maxwell DB not found: {DB_PATH}\n"
            f"Run the pipeline first: just smoke"
        )
    conn: sqlite3.Connection = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro", uri=True
    )
    conn.row_factory = sqlite3.Row
    return conn


def _fb_to_dict(row: sqlite3.Row | dict) -> dict:
    """Convert DB row to clean dict, stripping internal fields."""
    if isinstance(row, dict):
        d = dict(row)
    else:
        d = dict(row)
    for k in list(d.keys()):
        if k.startswith("_"):
            del d[k]
    return d


# ── Tools ──────────────────────────────────────────────────────────────

async def _tool_query_knowledge(args: dict) -> list[TextContent]:
    """Search Maxwell's knowledge graph for Foundation Blocks."""
    query: str = str(args.get("query", ""))
    domain: str | None = args.get("domain")
    depth: str | None = args.get("depth")
    graph_aware: bool = bool(args.get("graph_aware", True))
    agentic: bool = bool(args.get("agentic", False))
    limit: int = min(int(args.get("limit", 10)), 50)

    conn: sqlite3.Connection = _get_readonly_conn()
    try:
        if agentic:
            pack: EvidencePack = agentic_search(
                conn, query, limit=limit, domain=domain, depth=depth,
                graph_aware=graph_aware,
            )
            results: list[dict] = pack.fbs
            agentic_meta: dict = {
                "iterations": pack.iterations,
                "exhausted": pack.exhausted,
                "total_fbs_found": pack.total_fbs_found,
            }
        elif graph_aware:
            results = graph_aware_search(
                conn, query, limit=limit, domain=domain, depth=depth,
            )
            agentic_meta = {}
        else:
            results = search_hybrid(
                conn, query, limit=limit, domain=domain, depth=depth,
            )
            agentic_meta = {}

        output: list[dict] = []
        for i, fb in enumerate(results[:limit]):
            entry: dict = {
                "rank": i + 1,
                "fb_id": fb.get("fb_id", fb.get("id", "")),
                "name": fb.get("name", ""),
                "definition": str(fb.get("definition", ""))[:500],
                "domains": fb.get("domains", ""),
                "depth": fb.get("depth", ""),
                "discipline": fb.get("discipline", ""),
                "borp_score": fb.get("borp_score"),
                "feedback_score": fb.get("feedback_score"),
                "confidence_score": fb.get("confidence_score"),
            }
            if graph_aware and "_graph" in fb:
                g = fb["_graph"]
                if g.get("contradicts"):
                    entry["contradicted_by"] = g["contradicts"]
                if g.get("prerequisites"):
                    entry["prerequisites"] = g["prerequisites"]
                if g.get("related"):
                    entry["related"] = [
                        r.get("fb_id") if isinstance(r, dict) else str(r)
                        for r in g["related"][:5]
                    ]
                entry["is_seed"] = fb.get("_is_seed", False)
            output.append(entry)

        response: dict = {
            "query": query,
            "total_results": len(output),
            "graph_aware": graph_aware,
            "agentic": agentic,
            "results": output,
        }
        if agentic_meta:
            response["agentic_meta"] = agentic_meta

        return [TextContent(type="text", text=json.dumps(response, indent=2, default=str))]
    finally:
        conn.close()


async def _tool_get_fb_detail(args: dict) -> list[TextContent]:
    """Get complete details for a specific Foundation Block."""
    fb_id: str = str(args.get("fb_id", ""))
    include_evidence: bool = bool(args.get("include_evidence", True))
    include_graph: bool = bool(args.get("include_graph", True))

    conn: sqlite3.Connection = _get_readonly_conn()
    try:
        row = conn.execute("SELECT * FROM fbs WHERE fb_id = ?", (fb_id,)).fetchone()
        if not row:
            return [TextContent(type="text", text=json.dumps({"error": f"FB not found: {fb_id}"}))]

        fb: dict = _fb_to_dict(row)
        output: dict[str, Any] = {
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
            "procedural_skill": fb.get("procedural_skill"),
            "fb_version": fb.get("fb_version"),
            "created_at": str(fb.get("created_at", "")),
        }

        if include_evidence:
            evidence = fb.get("evidence_passages_shown") or fb.get("evidence_passages")
            output["evidence_passages"] = evidence
            output["verification_results"] = fb.get("verification_results")
            output["source_clusters"] = fb.get("source_clusters", [])

        if include_graph:
            for field in ["related_fbs", "contradicts_fbs", "prerequisite_fbs"]:
                val = fb.get(field)
                if isinstance(val, str):
                    try:
                        val = json.loads(val)
                    except json.JSONDecodeError:
                        pass
                output[field] = val

        return [TextContent(type="text", text=json.dumps(output, indent=2, default=str))]
    finally:
        conn.close()


async def _tool_get_fb_reliability(args: dict) -> list[TextContent]:
    """Get execution reliability history for a Foundation Block."""
    fb_id: str = str(args.get("fb_id", ""))

    conn: sqlite3.Connection = _get_readonly_conn()
    try:
        stats: dict = get_fb_feedback_stats(fb_id, DB_PATH)
        row = conn.execute(
            """SELECT fb_id, name, borp_score, confidence_score,
               feedback_score, feedback_count, usage_count,
               last_retrieved_at, status, classification_status
               FROM fbs WHERE fb_id = ?""",
            (fb_id,),
        ).fetchone()

        if not row:
            return [TextContent(type="text", text=json.dumps({"error": f"FB not found: {fb_id}"}))]

        fb: dict = _fb_to_dict(row)
        output: dict[str, Any] = {
            "fb_id": fb.get("fb_id"),
            "name": fb.get("name"),
            "trust_metrics": {
                "borp_score": fb.get("borp_score"),
                "confidence_score": fb.get("confidence_score"),
                "feedback_score": fb.get("feedback_score"),
                "feedback_count": fb.get("feedback_count") or 0,
                "usage_count": fb.get("usage_count") or 0,
                "last_retrieved_at": str(fb.get("last_retrieved_at", "")),
                "status": fb.get("status"),
                "classification_status": fb.get("classification_status"),
            },
            "feedback_history": stats,
        }
        return [TextContent(type="text", text=json.dumps(output, indent=2, default=str))]
    finally:
        conn.close()


async def _tool_delegate_local(args: dict) -> list[TextContent]:
    """Delegate a file-grounded task to a local OMLX model (BUG-063 fix).

    Reads the named files with REAL filesystem access (unlike the
    Deno-sandboxed `delegate()` tool) and sends them with `prompt` to a
    local model. Exposes Maxwell's local inference via MCP (C25).

    BUG-220-MCP guard: restricts the model/system/files surface — no arbitrary
    remote model name, no path escape beyond PROJECT_ROOT, bounded system prompt
    and file count (C25 agent-agnostic + C22 hybrid-sovereignty fail-closed).
    """
    prompt: str = str(args.get("prompt", ""))
    if not prompt:
        return [TextContent(type="text", text=json.dumps({"error": "prompt is required"}))]

    # ── BUG-220-MCP: model allowlist (reject arbitrary/remote model names) ──
    model: str | None = str(args.get("model")) if args.get("model") else None
    if model and MCP_DELEGATE_ALLOWED_MODELS and model not in MCP_DELEGATE_ALLOWED_MODELS:
        return [TextContent(type="text", text=json.dumps({
            "error": f"model '{model}' is not in the delegate_local allowlist",
        }))]

    # ── BUG-220-MCP: system-prompt length bound ──
    system: str | None = str(args.get("system")) if args.get("system") else None
    if system and len(system) > MCP_DELEGATE_MAX_SYSTEM_CHARS:
        return [TextContent(type="text", text=json.dumps({
            "error": f"system prompt exceeds {MCP_DELEGATE_MAX_SYSTEM_CHARS} chars",
        }))]

    files: list[str] = [str(f) for f in (args.get("files") or [])]
    if len(files) > MCP_DELEGATE_MAX_FILES:
        return [TextContent(type="text", text=json.dumps({
            "error": f"too many files ({len(files)} > {MCP_DELEGATE_MAX_FILES})",
        }))]

    # ── BUG-220-MCP: path-containment guard (no read outside PROJECT_ROOT) ──
    _root: Path = PROJECT_ROOT.resolve()
    _resolved: list[str] = []
    for f in files:
        p = Path(f)
        if p.is_absolute() and not MCP_DELEGATE_ALLOW_ABSOLUTE_PATHS:
            return [TextContent(type="text", text=json.dumps({
                "error": f"absolute path not allowed: '{f}'",
            }))]
        _abs = p if p.is_absolute() else (_root / p)
        try:
            _abs.resolve().relative_to(_root)
        except ValueError:
            return [TextContent(type="text", text=json.dumps({
                "error": f"file '{f}' escapes project root",
            }))]
        _resolved.append(str(_abs.resolve()))
    files = _resolved

    kwargs: dict[str, Any] = {"files": files}
    if model:
        kwargs["model"] = model
    if system:
        kwargs["system"] = system
    if args.get("as_json"):
        kwargs["as_json"] = bool(args["as_json"])

    try:
        result: str = await asyncio.to_thread(delegate_omlx, prompt, **kwargs)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        return [TextContent(type="text", text=json.dumps({"error": str(exc)}))]

    return [TextContent(type="text", text=result)]


# ── Tool registry ──────────────────────────────────────────────────────

TOOLS: list[Tool] = [
    Tool(
        name="query_knowledge",
        description=(
            "Search Maxwell's knowledge graph for Foundation Blocks. "
            "Supports hybrid retrieval (FTS5 + vector + keyword) with "
            "optional graph expansion for related/contradicting FBs and "
            "agentic critique loop for iterative retrieval."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "domain": {"type": "string", "description": "Optional domain filter (e.g., 'pricing')"},
                "depth": {"type": "string", "enum": ["universal", "cross-domain", "domain", "specialized"]},
                "graph_aware": {"type": "boolean", "default": True, "description": "Enable graph expansion"},
                "agentic": {"type": "boolean", "default": False, "description": "Enable iterative critique loop"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="get_fb_detail",
        description=(
            "Get complete details for a Foundation Block including "
            "evidence passages, source books, verification results, "
            "and graph relationships."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "fb_id": {"type": "string", "description": "Foundation Block ID (e.g., 'FB-042')"},
                "include_evidence": {"type": "boolean", "default": True},
                "include_graph": {"type": "boolean", "default": True},
            },
            "required": ["fb_id"],
        },
    ),
    Tool(
        name="get_fb_reliability",
        description=(
            "Get execution reliability history for a Foundation Block. "
            "Maxwell's differentiating feature: empirical reliability from real outcomes."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "fb_id": {"type": "string", "description": "Foundation Block ID"},
            },
            "required": ["fb_id"],
        },
    ),
    Tool(
        name="delegate_local",
        description=(
            "Delegate a file-grounded task to a local OMLX model. Reads the "
            "named files with real filesystem access and sends them with the "
            "prompt to a local model (BUG-063 fix: avoids the Deno-sandboxed "
            "delegate() tool that cannot read project files)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Instruction/question for the model"},
                "files": {"type": "array", "items": {"type": "string"}, "description": "Optional file paths to inject as context"},
                "model": {"type": "string", "description": "Optional OMLX model name (default: generator from config)"},
                "system": {"type": "string", "description": "Optional system message"},
                "as_json": {"type": "boolean", "default": False, "description": "Parse the response as JSON"},
            },
            "required": ["prompt"],
        },
    ),
]

TOOL_HANDLERS: dict[str, Any] = {
    "query_knowledge": _tool_query_knowledge,
    "get_fb_detail": _tool_get_fb_detail,
    "get_fb_reliability": _tool_get_fb_reliability,
    "delegate_local": _tool_delegate_local,
}


# ── Server ─────────────────────────────────────────────────────────────

server: Server = Server("maxwell-os-knowledge")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Register tools with MCP client."""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Dispatch tool calls to handlers."""
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
    try:
        return await handler(arguments)
    except Exception as exc:
        return [TextContent(type="text", text=json.dumps({
            "error": str(exc), "tool": name
        }))]


# ── Entry point ────────────────────────────────────────────────────────

async def _run_server() -> None:
    """Run Maxwell MCP server via stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """Entry point with test mode support."""
    if "--test" in sys.argv:
        _run_test()
    else:
        asyncio.run(_run_server())


def _run_test() -> None:
    """Quick connectivity test — verifies DB exists and tools are registered."""
    print("=== Maxwell MCP Server — Connectivity Test ===\n")

    if not DB_PATH.exists():
        print(f"❌ DB not found: {DB_PATH}")
        print("   Run the pipeline first: just smoke")
        sys.exit(1)
    print(f"✅ DB found: {DB_PATH}")

    for tool in TOOLS:
        name: str = tool.name
        registered: bool = name in TOOL_HANDLERS
        status: str = "✅" if registered else "❌"
        print(f"{status} Tool '{name}' registered")

    conn: sqlite3.Connection = _get_readonly_conn()
    count = conn.execute("SELECT COUNT(*) as cnt FROM fbs").fetchone()
    print(f"✅ FBs in DB: {count['cnt']}")

    graph_cols = conn.execute(
        "SELECT COUNT(*) as cnt FROM fbs WHERE related_fbs IS NOT NULL"
    ).fetchone()
    print(f"✅ FBs with graph edges: {graph_cols['cnt']}")
    conn.close()

    print("\n✅ All checks passed.")
    print("   Register with Claude Desktop or Goose:")
    print("   { 'mcpServers': { 'maxwell': {")
    print("       'command': 'python3',")
    print("       'args': ['maxwell_mcp_server.py']")
    print("   } } }")


if __name__ == "__main__":
    main()
