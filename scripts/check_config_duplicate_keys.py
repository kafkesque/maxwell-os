#!/usr/bin/env python3
"""scripts/check_config_duplicate_keys.py — fail loudly on duplicate keys in config (BUG-730).

WHY THIS EXISTS. PyYAML's `safe_load` and Python's `json.load` both keep the LAST duplicate key
and raise nothing. A second top-level block therefore does not ADD to a mapping — it REPLACES it.
That happened for real on 2026-10-12: a `reroute:` block was appended to `config/content_types.yaml`
while the file already had a `reroute:` mapping higher up, so `reroute.ti_to_pt_keywords` silently
became empty, `TI_TO_PT_KEYWORDS` became `()`, and the entire `tool_instruction -> process_template`
routing tier went DEAD — measured as 10 moves disappearing from the router diff, with no error,
no warning and no failing test. It was caught by a DIFF, which is luck.

That is the C16 class (no silent errors) applied to the CONFIG SURFACE: every governed threshold,
vocabulary and flag in this repo is loaded from config/, so one duplicate key can disable a rule
that a whole decision depends on while every rail stays green.

WHAT IT CHECKS:
  * every `config/**/*.yaml` — duplicate keys at ANY nesting depth (last-wins is silent);
  * every `config/**/*.json` — same defect, same silence.
It does NOT validate values, types or intent; other rails own that. This one answers a single
question: can any file here silently LOSE a key that was written into it?

Exit: 0 clean | 1 duplicate(s) found | 2 could not scan.
Usage: python3 scripts/check_config_duplicate_keys.py [--quiet] [--paths config ...]
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATHS: tuple[str, ...] = ("config",)


class _DuplicateKeyError(ValueError):
    """Raised with the offending key(s) and 1-based line number."""


class _StrictLoader(yaml.SafeLoader):
    """A SafeLoader that REFUSES duplicate mapping keys instead of letting the last one win."""


def _construct_mapping(loader: _StrictLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    """Build a mapping, failing on any key that appears twice in the SAME block."""
    keys: list[str] = []
    for key_node, _ in node.value:
        try:
            keys.append(str(loader.construct_object(key_node, deep=True)))
        except yaml.YAMLError:
            keys.append("<unhashable>")
    duplicates = [key for key, count in collections.Counter(keys).items() if count > 1]
    if duplicates:
        raise _DuplicateKeyError(
            f"duplicate key(s) {duplicates} at line {node.start_mark.line + 1}"
        )
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


_StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def _json_pairs(pairs: list[tuple[str, Any]]) -> dict:
    """`object_pairs_hook` that raises on a duplicate JSON key."""
    keys = [key for key, _ in pairs]
    duplicates = [key for key, count in collections.Counter(keys).items() if count > 1]
    if duplicates:
        raise _DuplicateKeyError(f"duplicate key(s) {duplicates}")
    return dict(pairs)


def check_file(path: Path) -> list[str]:
    """Return the faults for ONE config file (empty list = clean).

    Args:
        path: A .yaml/.yml or .json file.

    Returns:
        Human-readable fault strings.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"UNREADABLE: {exc}"]
    try:
        if path.suffix in (".yaml", ".yml"):
            yaml.load(text, Loader=_StrictLoader)
        elif path.suffix == ".json":
            json.loads(text, object_pairs_hook=_json_pairs)
        else:
            return []
    except _DuplicateKeyError as exc:
        return [f"DUPLICATE-KEY: {exc}"]
    except yaml.YAMLError as exc:
        return [f"YAML-ERROR: {str(exc)[:160]}"]
    except json.JSONDecodeError as exc:
        return [f"JSON-ERROR: {str(exc)[:160]}"]
    return []


_SELFTEST_DUPLICATE_YAML = "a:\n  x: 1\na:\n  z: 2\n"
_SELFTEST_CLEAN_YAML = "a:\n  x: 1\nb:\n  z: 2\n"
_SELFTEST_DUPLICATE_JSON = '{"a": 1, "a": 2}'


def _selftest() -> int:
    """Known-answer controls (BUG-492): the detector must be SEEN to fire AND to stay quiet.

    A control nothing runs is a comment, so this rail ships with three: a duplicate YAML key, a
    clean YAML mapping, and a duplicate JSON key.

    Returns:
        0 when every control behaves, 1 otherwise.
    """
    import tempfile

    checks: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        duplicate_yaml = root / "dup.yaml"
        duplicate_yaml.write_text(_SELFTEST_DUPLICATE_YAML, encoding="utf-8")
        clean_yaml = root / "clean.yaml"
        clean_yaml.write_text(_SELFTEST_CLEAN_YAML, encoding="utf-8")
        duplicate_json = root / "dup.json"
        duplicate_json.write_text(_SELFTEST_DUPLICATE_JSON, encoding="utf-8")
        checks.append(("a duplicate YAML key IS reported", bool(check_file(duplicate_yaml))))
        checks.append(("a clean YAML mapping is NOT reported", not check_file(clean_yaml)))
        checks.append(("a duplicate JSON key IS reported", bool(check_file(duplicate_json))))

    for label, ok in checks:
        print(f"  {'✅' if ok else '❌'} {label}")
    misbehaved = [label for label, ok in checks if not ok]
    if misbehaved:
        print(f"FAIL duplicate-keys selftest: {len(misbehaved)} control(s) misbehaved: {misbehaved}")
        return 1
    print(f"✅ duplicate-keys selftest: {len(checks)} controls behaved (fires on duplicates, quiet on clean).")
    return 0


def discover(paths: tuple[str, ...]) -> list[Path]:
    """Every .yaml/.yml/.json under the given roots, sorted for a stable report."""
    found: list[Path] = []
    for raw in paths:
        root = (ROOT / raw) if not Path(raw).is_absolute() else Path(raw)
        if root.is_file():
            found.append(root)
            continue
        for pattern in ("**/*.yaml", "**/*.yml", "**/*.json"):
            found.extend(sorted(root.glob(pattern)))
    return sorted({p for p in found if p.is_file()})


def main() -> int:
    ap = argparse.ArgumentParser(description="Fail on duplicate keys in config YAML/JSON (BUG-730).")
    ap.add_argument("--paths", nargs="+", default=list(DEFAULT_PATHS), help="roots to scan (default: config)")
    ap.add_argument("--quiet", action="store_true", help="print only the verdict line")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls (BUG-492): the detector must be SEEN to fire")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    files = discover(tuple(args.paths))
    if not files:
        print(f"FAIL duplicate-keys: nothing to scan under {args.paths} — refusing to pass vacuously (C16).")
        return 2

    faulty: dict[Path, list[str]] = {}
    for path in files:
        faults = check_file(path)
        if faults:
            faulty[path] = faults

    for path, faults in faulty.items():
        for fault in faults:
            print(f"  ❌ {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}: {fault}")

    if faulty:
        print(f"\nFAIL duplicate-keys: {len(faulty)} of {len(files)} file(s) can SILENTLY lose a key.")
        print("A duplicate key does not add to a mapping — it REPLACES the earlier one (BUG-730).")
        return 1
    if not args.quiet:
        print(f"✅ duplicate-keys: {len(files)} config file(s) scanned, no duplicate keys — no key can be lost silently.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
