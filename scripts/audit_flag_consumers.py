#!/usr/bin/env python3
"""scripts/audit_flag_consumers.py - make a flag that enforces nothing a RED (D-339).

Every stateful flag in ``config/*.yaml`` is a CLAIM. This check turns the claim into a
test with three failure modes:

1. STATE MISMATCH - the config value disagrees with what the cited decision requires
   (the C-1 / C-2 class: a decision asserting protection, or a rejected experiment left on).
2. NO CONSUMER      - ``enabled: true`` and nothing in the declared consumer list even
   references the file, so the flag enforces nothing.
3. UNDECLARED       - a registered entry without consumers and without an ``exempt_reason``.

The decisions -> config link lives in ``config/flag_consumer_registry.yaml`` (C12: no value
is hardcoded here). Exit code 1 on any RED so ``just health`` fails loudly (C16).

Usage: python3 scripts/audit_flag_consumers.py [--quiet]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "config" / "flag_consumer_registry.yaml"
CONFIG_GLOB = "config/*.yaml"


def load_yaml(path: Path) -> Any:
    """Load a YAML document, exiting loudly if it cannot be parsed (C16)."""
    import yaml

    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - re-raised with the path for a readable failure
        raise SystemExit(f"{path}: YAML parse failure: {exc}")


def get_path(doc: Any, dotted: str) -> tuple[bool, Any]:
    """Resolve a dotted key path inside nested dicts; return (found, value)."""
    cur = doc
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def consumer_reads(consumer: str, config: Path) -> bool:
    """True when the consumer file references the config (by name or by stem)."""
    path = PROJECT_ROOT / consumer
    if not path.exists():
        return False
    body = path.read_text(encoding="utf-8", errors="ignore")
    return config.name in body or config.stem in body


def enabled_keys(doc: Any, prefix: str = "") -> list[str]:
    """Return dotted paths of every ``enabled``/``*_enabled`` boolean key under ``doc``.

    BUG-375: this scan used to emit the LEAF key only (``boundary_inject_enabled``) while the
    registry registers the full DOTTED path (``stage4.boundary_inject_enabled``), so a REGISTERED
    flag was ALSO reported as "unregistered" and the anonymous ``enabled`` keys were unactionable.
    Walk the parsed document so the registry and the scan share one naming convention.
    """
    out: list[str] = []
    if isinstance(doc, dict):
        for key, value in doc.items():
            dotted = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, bool) and (key == "enabled" or str(key).endswith("_enabled")):
                out.append(dotted)
            out.extend(enabled_keys(value, dotted))
    elif isinstance(doc, list):
        for i, value in enumerate(doc):
            out.extend(enabled_keys(value, f"{prefix}[{i}]"))
    return out


def scan_unregistered() -> list[str]:
    """Return dotted paths of every ``enabled``/``*_enabled`` key in config/*.yaml (BUG-375)."""
    found: list[str] = []
    for path in sorted(PROJECT_ROOT.glob(CONFIG_GLOB)):
        for dotted in enabled_keys(load_yaml(path)):
            found.append(f"{path.relative_to(PROJECT_ROOT)}::{dotted}")
    return sorted(set(found))


def run(quiet: bool = False) -> int:
    """Run the audit; return the process exit code (1 = at least one RED)."""
    registry = load_yaml(REGISTRY_PATH)
    entries = registry.get("flags", [])
    red: list[str] = []
    yellow: list[str] = []
    green = 0
    registered = set()

    for entry in entries:
        config = PROJECT_ROOT / entry["config"]
        dotted = entry["path"]
        registered.add(f"{entry['config']}::{dotted}")
        doc = load_yaml(config)
        found, actual = get_path(doc, dotted)
        if not found:
            red.append(f"{entry['config']}::{dotted} - path MISSING (registry/artifact mismatch, C16)")
            continue
        required = entry["required"]
        consumers = entry.get("consumers") or []
        decisions = ", ".join(entry.get("decisions", []))
        if bool(actual) != bool(required):
            red.append(f"{entry['config']}::{dotted} = {actual!r} but {decisions} requires "
                       f"{required!r} - STATE MISMATCH (a decision and the artifact disagree)")
            continue
        if bool(actual) and not consumers:
            red.append(f"{entry['config']}::{dotted} is ON with no consumer ({decisions})")
            continue
        dead = [c for c in consumers if not consumer_reads(c, config)]
        if dead:
            red.append(f"{entry['config']}::{dotted} declares consumer(s) that never read it: {dead}")
            continue
        if not consumers and not entry.get("exempt_reason"):
            red.append(f"{entry['config']}::{dotted} has no consumers and no exempt_reason")
            continue
        green += 1
        if not quiet:
            state = "ON " if actual else "off"
            why = entry.get("note", entry.get("exempt_reason", ""))
            print(f"  ok   {state} {entry['config']}::{dotted}  [{decisions}] {why}")

    for key in scan_unregistered():
        if key not in registered:
            yellow.append(key)

    # GUARD (BUG-375/BUG-372 class): the scan and the registry must share ONE path convention.
    # A REGISTERED flag reported as unregistered means the check itself is lying -> RED, not warn.
    self_broken = [k for k in yellow if k in registered]
    if self_broken:
        red.extend(f"{k} - REGISTERED but reported unregistered: scan/registry path convention "
                   f"drift (BUG-375 self-check)" for k in self_broken)
        yellow = [k for k in yellow if k not in registered]

    print(f"\nflag consumers: {green} verified, {len(red)} RED, {len(yellow)} unregistered flag(s)")
    for item in yellow:
        print(f"  warn unregistered: {item} (add it to {REGISTRY_PATH.relative_to(PROJECT_ROOT)})")
    for item in red:
        print(f"  RED  {item}")
    return 1 if red else 0


def main() -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true", help="print only failures and the summary")
    args = ap.parse_args()
    return run(quiet=args.quiet)


if __name__ == "__main__":
    sys.exit(main())
