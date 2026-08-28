#!/usr/bin/env python3
"""
mcp_doc_guard.py — Maxwell OS D824 Document-Protection MCP Server (v2.0)
========================================================================
Authority: D-D13 (rebuilt against v2.0 pipeline), R-D824 (never overwrite
           protected files), C6 (crash-safe writes), C25 (agent-agnostic MCP).

Replaces the retired v1 `tools/mcp_doc_guard.py` (which was a CLI interceptor,
NOT an MCP server, and exposed none of the advertised tools).

Exposes 4 tools matching the DocGuard extension description:
  1. check_protected(path)  -> is the file protected? returns policy or None
  2. safe_write(path, text) -> atomic write, refuses never_overwrite / append_only
  3. safe_append(path, text)-> fsync'd append, refuses never_overwrite
  4. safe_edit(path, old, new) -> guarded find/replace, refuses protected

Backed by the REAL v2.0 primitives:
  - pipeline/io_guard.safe_write  (atomic tempfile -> fsync -> os.replace + shrink guard)
  - pipeline/doc_guard.is_protected / PROTECTED_FILES / preflight / postflight

Usage:
    python3 mcp_doc_guard.py            # stdio MCP transport
    python3 mcp_doc_guard.py --test     # smoke test (no MCP loop)

Register with goose (config.yaml DocGuard extension):
    cmd: python3, args: [mcp_doc_guard.py], cwd: <maxwell os 2.0>
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Resolve pipeline primitives relative to this file's repo root (v2.0)
_REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPO_ROOT))

from pipeline.io_guard import safe_write as _atomic_write  # noqa: E402
from pipeline import doc_guard  # noqa: E402

# MCP SDK
from mcp.server import Server  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402
from mcp.types import Tool, TextContent  # noqa: E402

server: Server = Server("maxwell-docguard")


# ── Tool implementations ────────────────────────────────────────────────

def _policy_of(path: str) -> dict | None:
    """Return the D824 policy dict for a path, or None if unprotected."""
    return doc_guard.is_protected(path)


def _respond(ok: bool, **fields: Any) -> str:
    """Serialize a structured result for the MCP client."""
    return json.dumps({"ok": ok, **fields})


async def _tool_check_protected(args: dict[str, Any]) -> list[TextContent]:
    path = args.get("path", "")
    policy = _policy_of(path)
    if policy is None:
        return [TextContent(type="text", text=_respond(
            True, path=path, protected=False, policy=None,
            note="Not in D824 protected manifest. safe_write allowed."))]
    return [TextContent(type="text", text=_respond(
        True, path=path, protected=True, policy=policy))]


async def _tool_safe_write(args: dict[str, Any]) -> list[TextContent]:
    path = args.get("path", "")
    content = args.get("content", "")
    policy = _policy_of(path)
    if policy is not None:
        pol = policy.get("policy")
        if pol == "never_overwrite":
            return [TextContent(type="text", text=_respond(
                False, error=f"REFUSED: {path} is never_overwrite (D824). "
                             "No write permitted.", policy=policy))]
        if pol == "append_only":
            return [TextContent(type="text", text=_respond(
                False, error=f"REFUSED: {path} is append_only (D824). "
                             "Use safe_append instead of safe_write.", policy=policy))]
        # versioned (e.g. CONSTITUTION.md): allowed, but atomic + shrink-guarded
    try:
        _atomic_write(path, content)
    except ValueError as exc:  # shrink guard
        return [TextContent(type="text", text=_respond(
            False, error=f"BLOCKED: {exc}", policy=policy))]
    return [TextContent(type="text", text=_respond(
        True, path=path, policy=(policy or {}).get("policy"),
        note="Atomic write complete (tempfile -> fsync -> os.replace)."))]


async def _tool_safe_append(args: dict[str, Any]) -> list[TextContent]:
    path = args.get("path", "")
    content = args.get("content", "")
    policy = _policy_of(path)
    if policy is not None and policy.get("policy") == "never_overwrite":
        return [TextContent(type="text", text=_respond(
            False, error=f"REFUSED: {path} is never_overwrite (D824). "
                         "No append permitted.", policy=policy))]
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # True append (never rewrite) + fsync — C6 crash-safety for append-only files.
    with open(p, "ab") as f:
        f.write(content.encode("utf-8"))
        f.flush()
        os.fsync(f.fileno())
    return [TextContent(type="text", text=_respond(
        True, path=path, policy=(policy or {}).get("policy"),
        note="Append complete (fsync'd)."))]


async def _tool_safe_edit(args: dict[str, Any]) -> list[TextContent]:
    path = args.get("path", "")
    old = args.get("old", "")
    new = args.get("new", "")
    policy = _policy_of(path)
    if policy is not None:
        pol = policy.get("policy")
        if pol in ("never_overwrite", "append_only"):
            return [TextContent(type="text", text=_respond(
                False, error=f"REFUSED: {path} is {pol} (D824). "
                             "No in-place edit permitted.", policy=policy))]
    p = Path(path)
    if not p.exists():
        return [TextContent(type="text", text=_respond(
            False, error=f"{path} does not exist. safe_edit requires an existing file."))]
    text = p.read_text(encoding="utf-8")
    if old not in text:
        return [TextContent(type="text", text=_respond(
            False, error=f"old text not found in {path}; no change made."))]
    new_text = text.replace(old, new)
    try:
        _atomic_write(path, new_text)
    except ValueError as exc:  # shrink guard
        return [TextContent(type="text", text=_respond(
            False, error=f"BLOCKED: {exc}", policy=policy))]
    return [TextContent(type="text", text=_respond(
        True, path=path, policy=(policy or {}).get("policy"),
        note="Edit applied (atomic write)."))]


TOOL_HANDLERS = {
    "check_protected": _tool_check_protected,
    "safe_write": _tool_safe_write,
    "safe_append": _tool_safe_append,
    "safe_edit": _tool_safe_edit,
}

TOOLS: list[Tool] = [
    Tool(
        name="check_protected",
        description="Check whether a file is protected by D824. Returns the policy "
                    "(append_only / never_overwrite / versioned) or null if unprotected.",
        inputSchema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    ),
    Tool(
        name="safe_write",
        description="Atomically write a file (tempfile -> fsync -> os.replace) with a "
                    "shrink guard. Refuses to overwrite never_overwrite or append_only files.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    ),
    Tool(
        name="safe_append",
        description="Append content to a file (fsync'd append). Refuses never_overwrite files. "
                    "The correct tool for append_only files like DECISION-LOG.md.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    ),
    Tool(
        name="safe_edit",
        description="Guarded in-place find/replace on an existing file (atomic write, shrink "
                    "guard). Refuses never_overwrite and append_only files.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old": {"type": "string"},
                "new": {"type": "string"},
            },
            "required": ["path", "old", "new"],
        },
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Register tools with MCP client."""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Dispatch tool calls to handlers."""
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return [TextContent(type="text", text=_respond(
            False, error=f"Unknown tool: {name}"))]
    try:
        return await handler(arguments)
    except Exception as exc:  # noqa: BLE001 — surface, don't crash the loop
        return [TextContent(type="text", text=_respond(
            False, error=str(exc), tool=name))]


async def _run_server() -> None:
    """Run the MCP server via stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def _run_test() -> None:
    """Smoke test — verifies tools resolve against v2.0 primitives."""
    print("mcp_doc_guard.py — smoke test")
    print(f"  repo root: {_REPO_ROOT}")
    print(f"  tools: {sorted(TOOL_HANDLERS)}")

    constitution = str(_REPO_ROOT / "CONSTITUTION.md")
    policy = _policy_of(constitution)
    print(f"  check_protected(CONSTITUTION.md) -> {policy}")

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "scratch.txt"
        _atomic_write(str(f), "hello\n")
        with open(f, "ab") as fh:
            fh.write(b"world\n")
            fh.flush()
            os.fsync(fh.fileno())
        print(f"  atomic write + append OK: {f.read_text()!r}")

    print("  SMOKE TEST PASSED")


def main() -> None:
    if "--test" in sys.argv:
        _run_test()
    else:
        asyncio.run(_run_server())


if __name__ == "__main__":
    main()
