#!/usr/bin/env python3
"""Guard: enforce a SINGLE canonical install per inference stack (D2455/D2456).

Root cause of the 2026-08-24 "two-version clusterfuck": TWO installs of the same
server (GUI app vs homebrew formula) both claimed the same port and both rewrote
the same config file. This hit OMLX first (homebrew 0.5.1 vs app 0.6.2), then the
audit found the IDENTICAL pattern in Ollama (homebrew 0.30.0 vs app 0.32.15, its
launchd agent crash-looping on `bind: address already in use`).

This guard iterates EVERY service that declares a `single_source_guard` block in
config/pipeline_config.yaml (config-first, C12) and fails loudly (exit 1) if ANY
of the following regresses for ANY stack:
  1. A second (homebrew/duplicate) binary reappears.
  2. A stale launchd agent is loaded OR its plist file reappears in
     ~/Library/LaunchAgents (the re-infection vector).
  3. The stack's port is not owned by exactly one process.

Adding a new stack = adding its `single_source_guard` block to config. No code
change needed (future-tax-free).

Exit codes:
  0  single-source invariant holds for all stacks
  1  violation detected (fail loudly, per C16 no-silent-errors)
  2  config misconfigured
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - diagnostic path
    yaml = None  # type: ignore[assignment]


_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_guarded_stacks() -> dict[str, dict[str, Any]]:
    """Return {stack_name: merged_guard_cfg} for every service with a guard block."""
    if yaml is None:
        print("❌ PyYAML unavailable — cannot read config", file=sys.stderr)
        sys.exit(2)
    cfg_path = _PROJECT_ROOT / "config" / "pipeline_config.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    services = (cfg.get("services", {}) or {})
    stacks: dict[str, dict[str, Any]] = {}
    for name, svc in services.items():
        if not isinstance(svc, dict):
            continue
        guard = svc.get("single_source_guard")
        if not guard:
            continue
        merged = dict(guard)
        merged["port"] = svc.get("port")
        merged["host"] = svc.get("host", "localhost")
        stacks[name] = merged
    if not stacks:
        print("❌ no services declare `single_source_guard` in pipeline_config.yaml", file=sys.stderr)
        sys.exit(2)
    return stacks


def _expand(path: str) -> Path:
    """Expand ~ and user-relative paths."""
    return Path(path).expanduser()


def _resolves_to_homebrew_install(path: Path) -> bool:
    """Return True if `path` (a symlink, resolved) points into a Cellar/opt install.

    The app writes its OWN shim (e.g. /opt/homebrew/bin/omlx -> ~/.omlx/bin/omlx ->
    omlx-cli), so a bare existence check is a false positive. A real homebrew
    re-install makes the shim resolve into /opt/homebrew/Cellar/* or /opt/homebrew/opt/*.
    """
    try:
        resolved = path.resolve(strict=False)
    except (OSError, RuntimeError):
        return False
    resolved_s = str(resolved)
    return ("/opt/homebrew/Cellar/" in resolved_s) or ("/opt/homebrew/opt/" in resolved_s)


def _check_stack(name: str, guard: dict[str, Any]) -> list[str]:
    """Return violations for one stack (binary, launchd, port)."""
    violations: list[str] = []
    tag = f"[{name}]"

    canonical = _expand(guard.get("canonical_app", ""))
    if canonical and not canonical.exists():
        violations.append(f"{tag} canonical app missing: {canonical}")

    # 1) Unambiguous homebrew formula markers (Cellar/opt) — must not exist.
    for b in guard.get("forbidden_bins", []):
        p = _expand(b)
        if p.exists() or p.is_symlink():
            violations.append(f"{tag} forbidden homebrew install present: {b}")

    # 2) Ambiguous shim paths — flag ONLY if they resolve into a homebrew install
    #    (the app's own shim resolves elsewhere and is legitimate).
    for b in guard.get("shim_paths", []):
        p = _expand(b)
        if (p.exists() or p.is_symlink()) and _resolves_to_homebrew_install(p):
            violations.append(f"{tag} shim resolves to homebrew install: {b} -> {p.resolve(strict=False)}")

    labels = guard.get("forbidden_launchd_labels", [])
    agents_dir = _expand(guard.get("launch_agents_dir", "~/Library/LaunchAgents"))
    try:
        listed = subprocess.run(
            ["launchctl", "list"], capture_output=True, text=True, timeout=15
        ).stdout
    except (OSError, subprocess.TimeoutExpired) as exc:
        violations.append(f"{tag} launchctl list failed: {exc}")
        listed = ""
    for label in labels:
        # Exact whole-field match: `label in listed` was a substring test, so
        # `com.maxwell.omlx` falsely matched the legit `com.maxwell.omlx-api-key`
        # (one-shot OMLX_API_KEY setenv agent). Match the label as the last
        # whitespace-delimited column of a `launchctl list` line.
        if re.search(rf"(?m)(?:^|\s){re.escape(label)}\s*$", listed):
            violations.append(f"{tag} stale launchd agent LOADED: {label}")
        plist = agents_dir / f"{label}.plist"
        if plist.exists():
            violations.append(f"{tag} stale launchd plist present: {plist}")

    port = guard.get("port")
    if port is not None:
        try:
            out = subprocess.run(
                ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
                capture_output=True, text=True, timeout=15,
            ).stdout
        except (OSError, subprocess.TimeoutExpired) as exc:
            violations.append(f"{tag} lsof failed on port {port}: {exc}")
            out = ""
        lines = [ln for ln in out.splitlines() if ln.strip() and "COMMAND" not in ln]
        if len(lines) == 0:
            violations.append(f"{tag} port {port}: no listener (server down)")
        elif len(lines) > 1:
            owners = {ln.split()[0] for ln in lines if ln.split()}
            violations.append(f"{tag} port {port}: {len(lines)} listeners ({owners}) — conflict")

    return violations


def run_guard() -> tuple[bool, list[str]]:
    """Run all checks across all guarded stacks. Returns (ok, violations)."""
    stacks = _load_guarded_stacks()
    violations: list[str] = []
    for name, guard in stacks.items():
        violations += _check_stack(name, guard)
    return (len(violations) == 0), violations


def main() -> int:
    """CLI entry point."""
    ok, violations = run_guard()
    if ok:
        stacks = ", ".join(_load_guarded_stacks())
        print(f"✅ Single-source invariant holds for all stacks: {stacks}")
        return 0
    print("❌ Stack single-source guard FAILED:", file=sys.stderr)
    for v in violations:
        print(f"   - {v}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
