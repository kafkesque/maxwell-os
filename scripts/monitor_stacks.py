#!/usr/bin/env python3
"""Unified stack monitor — ONE panel for all inference stacks (D2456).

Answers the "monitor all moving stacks from one place" requirement. For every
service in config/pipeline_config.yaml, reports:
  - status (UP/DOWN via health check)
  - running version (authoritative endpoint / binary)
  - min_version pin (config) + drift verdict (PASS / DRIFT / UNKNOWN)
  - single-source guard verdict (exactly one install, no stale launchd agents)

Adding a new stack = adding its `services.<name>` block + `single_source_guard`.
No code change needed (future-tax-free). Exit 1 if any stack is down, drifting,
or violating the single-source invariant (fail loudly, C16).

Exit codes:
  0  all stacks healthy, current, single-source
  1  any stack DOWN / DRIFT / single-source violation
  2  config misconfigured
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import requests
    import yaml
except ImportError:  # pragma: no cover - diagnostic path
    requests = None  # type: ignore[assignment]
    yaml = None  # type: ignore[assignment]


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


def _load_services() -> dict[str, dict[str, Any]]:
    """Load all services from pipeline_config.yaml."""
    if yaml is None:
        print("❌ PyYAML/requests unavailable", file=sys.stderr)
        sys.exit(2)
    cfg_path = _PROJECT_ROOT / "config" / "pipeline_config.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    services = (cfg.get("services", {}) or {})
    return {k: v for k, v in services.items() if isinstance(v, dict)}


def _get_version(name: str, cfg: dict[str, Any]) -> tuple[bool, str | None]:
    """Return (up, version) using the proven per-stack probes.

    OMLX `/health` does NOT return a version field — `get_omlx_version()` falls
    back to the binary `--version`. Ollama `/api/version` returns it directly.
    """
    if name == "omlx":
        try:
            from pipeline.omlx_call import check_omlx_health, get_omlx_version
            up = check_omlx_health()
            return (up, get_omlx_version() if up else None)
        except Exception:
            return (False, None)
    if name == "ollama":
        try:
            from pipeline.status import check_ollama_health, get_ollama_version
            up = check_ollama_health()
            return (up, get_ollama_version() if up else None)
        except Exception:
            return (False, None)
    # Generic fallback for future stacks
    host = cfg.get("host", "localhost")
    port = cfg.get("port")
    if port is None or requests is None:
        return (False, None)
    try:
        r = requests.get(f"http://{host}:{port}/health", timeout=6)
        if r.status_code != 200:
            return (False, None)
        return (True, r.json().get("version"))
    except Exception:
        return (False, None)


def _verdict(version: str | None, min_version: str | None) -> str:
    """DRIFT if version < min_version, PASS if >=, UNKNOWN if unverifiable."""
    if version is None:
        return "UNKNOWN"
    if not min_version:
        return "PASS"
    try:
        v = tuple(int(x) for x in version.split(".")[:3] if x.isdigit())
        m = tuple(int(x) for x in min_version.split(".")[:3] if x.isdigit())
    except ValueError:
        return "UNKNOWN"
    if not v or not m:
        return "UNKNOWN"
    # Pad for comparison
    while len(v) < len(m):
        v = v + (0,)
    while len(m) < len(v):
        m = m + (0,)
    return "PASS" if v >= m else "DRIFT"


def _health_path(name: str, cfg: dict[str, Any]) -> str:
    """Health endpoint path per stack (Ollama uses /api/version, OMLX uses /health)."""
    if name == "ollama":
        return "/api/version"
    return "/health"


def main() -> int:
    """CLI entry point."""
    services = _load_services()
    if not services:
        print("❌ no services in pipeline_config.yaml", file=sys.stderr)
        sys.exit(2)

    # Single-source guard first (fails loud)
    guard = subprocess.run(
        [sys.executable, str(_PROJECT_ROOT / "scripts" / "guard_stacks_single_source.py")],
        capture_output=True, text=True, timeout=60,
    )
    guard_ok = guard.returncode == 0

    print("═" * 58)
    print("  Maxwell OS — Inference Stack Monitor (one panel)")
    print("═" * 58)
    overall = True
    for name, cfg in services.items():
        if cfg.get("port") is None:
            continue
        up, version = _get_version(name, cfg)
        verdict = _verdict(version, cfg.get("min_version"))
        if not up or verdict == "DRIFT":
            overall = False
        icon = "✅" if up else "❌"
        drift = "✅" if verdict == "PASS" else ("🔶 DRIFT" if verdict == "DRIFT" else "❓")
        print(f"  {name:10s} {icon}  v{version or '?'}  (min {cfg.get('min_version', '-')})  {drift}")

    print("─" * 58)
    print(f"  Single-source guard: {'✅ PASS' if guard_ok else '❌ FAIL'}")
    print("═" * 58)
    if not guard_ok:
        print(guard.stdout, end="")
        print(guard.stderr, end="", file=sys.stderr)

    return 0 if (overall and guard_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
