#!/usr/bin/env python3
"""measure_extension_cost.py - THE RESIDENCY COST OF AN EXTENSION, MEASURED (extension rot, T-186/D-3056).

WHY THIS EXISTS. "Turn an extension off when it is not needed" is a sentence until the cost of leaving it on is a
NUMBER. Two costs are paid for every extension that is RESIDENT, and they are paid in different currencies:

  1. MEMORY  - a stdio extension is a PROCESS (in practice two: the `uvx`/`npx` shim plus its interpreter). It is
     resident for the whole session whether or not one of its tools is ever called.
  2. CONTEXT - every tool an extension declares is shipped to the model WITH EVERY REQUEST as a schema. This is
     the cost that does not show up in `ps` and the one that actually degrades a session: it is paid per turn, it
     inflates prefill, and it competes with the corpus for the window.

Neither number can be quoted from a README. This script reads the ONE home of the extension commands
(config/agent_context.yaml#homes.harness_config), spawns each ENABLED stdio extension exactly as the harness
would, asks it for `tools/list`, and measures the exact byte size of the schema it would ship. Bytes -> tokens is
reported with the divisor NAMED (BYTES_PER_TOKEN), never as a silent constant.

PLATFORM / BUILTIN EXTENSIONS ARE NOT SUBPROCESSES. They are reported with `schema_bytes: null` and
`measured: false` - an absent reading is ABSENT, not zero (D-2957/C16). Their tool COUNT is quoted only from a
receipt that declares the same config digest; otherwise it too is absent.

WHAT IT REFUSES (fail closed, C16):
  * a home that does not exist or does not parse;
  * an enabled stdio extension with no `cmd` (a declaration that does not RESOLVE, D-3034);
  * a measurement whose closest reading is silence - a server that started but listed ZERO tools is reported
    `tools: 0` and `verdict: ZERO-TOOLS`, which is the shape of BUG-873 and must never be read as healthy.

Usage:
  python3 scripts/measure_extension_cost.py                 # table
  python3 scripts/measure_extension_cost.py --json PATH     # receipt (default: governance/evidence/)
  python3 scripts/measure_extension_cost.py --selftest
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import pathlib
import sys
import time
from typing import Any

REPO = pathlib.Path(__file__).resolve().parents[1]
AGENT_CONTEXT = REPO / "config" / "agent_context.yaml"
FLIP_WRITER = REPO / "agent" / "adapters" / "goose" / "apply_provider_flip.py"

#: Bytes per token used ONLY to make two orders of magnitude comparable. English JSON schema text tokenises at
#: roughly 3.5-4.2 bytes/token on the tokenisers this machine serves; 4 is the conservative middle and is PRINTED
#: beside every number it produces, so no reader has to guess which divisor was used.
BYTES_PER_TOKEN = 4

#: Per-server ceiling. A server that has not answered `tools/list` in this long is reported TIMEOUT - a slow
#: extension is a cost too, and the receipt must be able to say so rather than hang the sweep.
SERVER_TIMEOUT_S = 45.0


def declared_home() -> pathlib.Path:
    """The harness config path, RESOLVED from its one declared home (C21: one resolver, never a second one).

    Raises:
        SystemExit: when the declaration is absent or unreadable - a FATAL, never a default (C16/D-2644).
    """
    spec = importlib.util.spec_from_file_location("_provider_flip", FLIP_WRITER)
    if spec is None or spec.loader is None:
        raise SystemExit(f"FATAL: cannot load the declared resolver from {FLIP_WRITER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.declared_home()


def _yaml(path: pathlib.Path) -> dict[str, Any]:
    """Parse a YAML file into a dict, or fail closed.

    Args:
        path: the file to parse.

    Returns:
        The parsed mapping (empty when the file is empty).

    Raises:
        SystemExit: when the file is missing or unparseable.
    """
    import yaml

    if not path.exists():
        raise SystemExit(f"FATAL: {path} does not exist - the residency cost has no subject")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise SystemExit(f"FATAL: {path} is not a mapping")
    return data


def _merged_env(declared: Any) -> dict[str, str] | None:
    """Build the environment a server would be started with: the ambient one plus the declared overlay.

    Args:
        declared: the extension's `env` mapping from the harness config, or None.

    Returns:
        The merged environment, or None when the extension declares none (inherit).
    """
    if not declared:
        return None
    merged = dict(os.environ)
    merged.update({str(k): str(v) for k, v in dict(declared).items()})
    return merged


def _schema_bytes(tools: Any) -> int:
    """The exact byte size of the tool list as the harness would carry it.

    Args:
        tools: the `list_tools()` result's `.tools` sequence of pydantic models.

    Returns:
        UTF-8 byte count of the JSON rendering - the number the context is charged.
    """
    rendered = [
        t.model_dump(mode="json") if hasattr(t, "model_dump") else dict(t) for t in tools
    ]
    return len(json.dumps(rendered, ensure_ascii=False).encode("utf-8"))


async def _probe_stdio(name: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Start one stdio extension, list its tools, and measure what it would cost.

    Args:
        name: the extension's name as the harness config declares it.
        cfg: its block from that config (`cmd`, `args`, optional `env`).

    Returns:
        A receipt row. Never raises: a failure is a MEASURED verdict, not an exception (C16 keeps it visible).
    """
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    started = time.monotonic()
    row: dict[str, Any] = {"name": name, "type": "stdio", "measured": False}
    cmd = cfg.get("cmd")
    if not cmd:
        row.update(verdict="NO-CMD", error="the declaration names no cmd (D-3034: it does not resolve)")
        return row
    args = [str(a) for a in (cfg.get("args") or [])]
    params = StdioServerParameters(command=str(cmd), args=args, env=_merged_env(cfg.get("env")))

    async def _inner() -> dict[str, Any]:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
                tools = list(listed.tools)
                size = _schema_bytes(tools)
                return {
                    "tools": len(tools),
                    "schema_bytes": size,
                    "tokens_est": round(size / BYTES_PER_TOKEN),
                    "first_tools": [t.name for t in tools[:5]],
                }

    try:
        payload = await asyncio.wait_for(_inner(), timeout=SERVER_TIMEOUT_S)
        row.update(payload)
        row["measured"] = True
        row["verdict"] = "ZERO-TOOLS" if payload["tools"] == 0 else "OK"
    except TimeoutError:
        row.update(verdict="TIMEOUT", error=f"no tools/list within {SERVER_TIMEOUT_S}s")
    except Exception as exc:  # noqa: BLE001 - the receipt must carry the reason, not die on it
        row.update(verdict="DEAD", error=f"{type(exc).__name__}: {exc}")
    row["wall_s"] = round(time.monotonic() - started, 1)
    return row


def _resident_rss_mb() -> dict[str, float]:
    """RSS of every live process whose command line names an extension's command.

    Returns:
        A mapping command-name -> megabytes. This is a POINT-IN-TIME reading of THIS machine's live session, so it
        is reported as context, never as a declared fact.
    """
    out: dict[str, float] = {}
    try:
        import psutil
    except ImportError:
        return out
    for proc in psutil.process_iter(["cmdline", "memory_info"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if not cmdline:
                continue
            text = " ".join(cmdline)
            if "mcp-server" not in text and "mcp-youtube" not in text and "mcp-read-pdf" not in text:
                continue
            key = next((c for c in cmdline if "mcp" in c), cmdline[0])
            out[key] = round(out.get(key, 0.0) + proc.info["memory_info"].rss / (1024 * 1024), 1)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return out


def sweep() -> dict[str, Any]:
    """Measure every DECLARED extension the harness config names, enabled or not, and total the residents.

    Returns:
        The receipt: one row per extension plus the totals an owner needs to choose a profile.
    """
    home = declared_home()
    config = _yaml(home)
    extensions = config.get("extensions") or {}
    if not isinstance(extensions, dict) or not extensions:
        raise SystemExit(f"FATAL: {home} declares no extensions - there is nothing to measure")

    stdio_rows = asyncio.run(
        _gather([
            (name, cfg) for name, cfg in extensions.items()
            if isinstance(cfg, dict) and cfg.get("type") == "stdio"
        ])
    )
    rows: list[dict[str, Any]] = []
    for name, cfg in extensions.items():
        if not isinstance(cfg, dict):
            continue
        enabled = bool(cfg.get("enabled"))
        if cfg.get("type") == "stdio":
            row = stdio_rows.pop(name)
        else:
            row = {
                "name": name,
                "type": str(cfg.get("type")),
                "measured": False,
                "tools": None,
                "schema_bytes": None,
                "verdict": "NOT-A-SUBPROCESS",
                "note": "platform/builtin: no process and no separable tools/list - schema bytes ABSENT, not zero (D-2957)",
            }
        row["enabled"] = enabled
        row["cmd"] = cfg.get("cmd")
        row["args"] = cfg.get("args")
        rows.append(row)

    resident = [r for r in rows if r["enabled"]]
    measured_resident = [r for r in resident if r.get("measured")]
    return {
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "home": str(home),
        "bytes_per_token": BYTES_PER_TOKEN,
        "server_timeout_s": SERVER_TIMEOUT_S,
        "rows": rows,
        "totals": {
            "declared": len(rows),
            "enabled": len(resident),
            "enabled_stdio_measured": len(measured_resident),
            "enabled_tools_measured": sum(int(r["tools"] or 0) for r in measured_resident),
            "enabled_schema_bytes_measured": sum(int(r["schema_bytes"] or 0) for r in measured_resident),
            "enabled_tokens_est_measured": sum(int(r.get("tokens_est") or 0) for r in measured_resident),
        },
        "live_rss_mb": _resident_rss_mb(),
    }


async def _gather(pairs: list[tuple[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    """Probe several extensions CONCURRENTLY (a serial sweep pays every server's start twice over).

    Args:
        pairs: (name, config block) for each stdio extension.

    Returns:
        name -> receipt row.
    """
    results = await asyncio.gather(*[_probe_stdio(n, c) for n, c in pairs])
    return {n: r for (n, _), r in zip(pairs, results, strict=True)}


def _selftest() -> int:
    """Known-answer controls: the arithmetic and the refusals must be decided by the code, not by a live server.

    Returns:
        0 when every control holds, 1 otherwise.
    """
    controls: list[tuple[str, bool]] = []

    class _Tool:
        def __init__(self, name: str, description: str) -> None:
            self._d = {"name": name, "description": description, "inputSchema": {"type": "object"}}

        def model_dump(self, mode: str = "json") -> dict[str, Any]:
            return self._d

    size = _schema_bytes([_Tool("read_file", "read")])
    controls.append(("a schema's bytes are the bytes of its JSON rendering",
                     size == len(json.dumps([{"name": "read_file", "description": "read",
                                              "inputSchema": {"type": "object"}}],
                                            ensure_ascii=False).encode("utf-8"))))
    controls.append(("an empty tool list costs the empty-array rendering (2 B), never silently 0",
                     _schema_bytes([]) == 2))
    controls.append(("bytes/token is declared, not assumed", isinstance(BYTES_PER_TOKEN, int) and BYTES_PER_TOKEN > 0))
    controls.append(("a declared env overlay keeps the ambient environment",
                     _merged_env({"A": "1"}) is not None and "PATH" in (_merged_env({"A": "1"}) or {})))
    controls.append(("no declared env inherits as None", _merged_env(None) is None))

    async def _no_cmd() -> dict[str, Any]:
        return await _probe_stdio("ghost", {"type": "stdio"})

    controls.append(("a stdio extension with no cmd is reported NO-CMD, never spawned",
                     asyncio.run(_no_cmd())["verdict"] == "NO-CMD"))

    for label, ok in controls:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
    passed = sum(1 for _, ok in controls if ok)
    print(f"selftest: {passed}/{len(controls)}")
    return 0 if passed == len(controls) else 1


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: CLI arguments (default: sys.argv[1:]).

    Returns:
        0 on a completed sweep, 1 on a failed control.
    """
    parser = argparse.ArgumentParser(description="measure what a resident extension costs")
    parser.add_argument("--json", dest="json_path", help="write the receipt here")
    parser.add_argument("--selftest", action="store_true", help="known-answer controls only")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()

    receipt = sweep()
    for row in receipt["rows"]:
        flag = "*" if row["enabled"] else " "
        tools = "—" if row.get("tools") is None else row["tools"]
        toks = "—" if row.get("tokens_est") is None else row["tokens_est"]
        print(f"{flag} {row['name']:20} {row['type']:9} tools={str(tools):>3} tokens≈{str(toks):>6} "
              f"{row['verdict']:18} {str(row.get('error') or row.get('note') or '')[:70]}")
    t = receipt["totals"]
    print(f"\nRESIDENT: {t['enabled']} extension(s); stdio measured {t['enabled_stdio_measured']} -> "
          f"{t['enabled_tools_measured']} tool schema(s) = {t['enabled_schema_bytes_measured']} B "
          f"≈ {t['enabled_tokens_est_measured']} tokens PER REQUEST (÷{BYTES_PER_TOKEN})")
    if receipt["live_rss_mb"]:
        print("live RSS now: " + ", ".join(f"{k.split('/')[-1]}={v}MB" for k, v in receipt["live_rss_mb"].items()))

    if args.json_path:
        out = pathlib.Path(args.json_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"receipt: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
