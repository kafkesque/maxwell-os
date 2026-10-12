#!/usr/bin/env python3
"""validate_taxonomy_partition.py — fail-closed MECE partition validator (D-2856 / D-NEXT-1).

The future-proofing guarantee (D-2855): every raw synonym maps to EXACTLY ONE (axis, id),
canonical labels are DISTINCT within and across axes, and every entry carries a stable opaque
`id`. This is the BUILD-TIME fail-closed validator that replaces reliance on the in-prompt
D2422 disjointness rules (BUG-630). A taxonomy that fails here MUST NOT be rendered into the
closed menu — the renderer's definition-anchored path would silently inherit the ambiguity.

Checks (exit 0 = clean, exit 1 = at least one violation):

  1. SHAPE      — disciplines/domains are non-empty lists of mappings with the required keys.
  2. OPAQUE ID  — every entry has a non-empty, unique `id` (stable across display renames).
  3. CANONICAL  — canonical labels are distinct WITHIN each axis and ACROSS axes (normalised).
  4. MECE       — every normalised raw synonym maps to exactly ONE (axis, id). Cross-axis
                 polysemy (BUG-630) and within-axis collisions are both violations.
  5. RAW HYGIENE— no duplicate or blank raw strings within a single entry's raw list.

Read-only. Config-first (C12): the only hardcoded values are the filename and the axis names.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "config" / "taxonomy.yaml"
AXES = ("disciplines", "domains")


def _norm(value: object) -> str:
    """Case + punctuation + whitespace insensitive normalisation (matches the runtime guard)."""
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def load_taxonomy(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def check_partition(tax: dict) -> list[str]:
    """Return every violation. Empty list == clean (MECE partition holds)."""
    problems: list[str] = []

    for axis in AXES:
        entries = tax.get(axis)
        if not isinstance(entries, list) or not entries:
            problems.append(f"{axis}: missing or empty — an empty answer space is a defect (C16)")
            continue
        for i, e in enumerate(entries):
            if not isinstance(e, dict):
                problems.append(f"{axis}[{i}]: not a mapping")
                continue
            for key in ("canonical", "raw", "definition", "group"):
                if key not in e:
                    problems.append(f"{axis}[{i}]: missing required key {key!r}")

    # Opaque ids: present, non-empty, unique across BOTH axes (a global namespace).
    seen_ids: dict[str, str] = {}
    for axis in AXES:
        for e in tax.get(axis, []):
            if not isinstance(e, dict):
                continue
            eid = str(e.get("id") or "").strip()
            canon = str(e.get("canonical") or "").strip()
            if not eid:
                problems.append(f"{axis} {canon!r}: missing opaque `id` (D-2855)")
            elif eid in seen_ids:
                problems.append(f"{axis} {canon!r}: id {eid!r} already used by {seen_ids[eid]!r}")
            else:
                seen_ids[eid] = f"{axis} {canon}"

    # Canonical distinctness (within + across axes), normalised.
    canon_index: dict[str, str] = {}
    for axis in AXES:
        for e in tax.get(axis, []):
            if not isinstance(e, dict):
                continue
            canon = str(e.get("canonical") or "").strip()
            key = _norm(canon)
            if not key:
                problems.append(f"{axis}: empty canonical label")
                continue
            if key in canon_index:
                problems.append(
                    f"canonical {canon!r} ({axis}) collides with {canon_index[key]!r} "
                    f"(normalised {key!r})")
            else:
                canon_index[key] = f"{axis} {canon}"

    # MECE partition + raw hygiene.
    raw_index: dict[str, list[str]] = {}
    for axis in AXES:
        for e in tax.get(axis, []):
            if not isinstance(e, dict):
                continue
            eid = str(e.get("id") or "?").strip()
            canon = str(e.get("canonical") or "?").strip()
            raw = e.get("raw")
            if not isinstance(raw, list):
                problems.append(f"{axis} {canon!r}: `raw` is not a list")
                continue
            seen_in_entry: dict[str, int] = {}
            for r in raw:
                rs = str(r).strip()
                if not rs:
                    problems.append(f"{axis} {canon!r}: blank raw synonym")
                    continue
                key = _norm(rs)
                if key in seen_in_entry:
                    problems.append(f"{axis} {canon!r}: duplicate raw synonym {rs!r} "
                                    f"({seen_in_entry[key] + 1}x)")
                seen_in_entry[key] = seen_in_entry.get(key, 0) + 1
                raw_index.setdefault(key, []).append(f"{axis}:{eid}:{canon}")

    for key, owners in raw_index.items():
        uniq = sorted(set(owners))
        if len(uniq) > 1:
            problems.append(
                f"MECE violation: raw synonym {key!r} maps to {len(uniq)} entries — "
                f"{'; '.join(uniq)}")

    return problems


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else DEFAULT_PATH
    if not path.exists():
        print(f"FAIL-CLOSED: taxonomy not found: {path}")
        return 1
    tax = load_taxonomy(path)
    problems = check_partition(tax)
    n_disc = len(tax.get("disciplines", []))
    n_dom = len(tax.get("domains", []))
    print(f"taxonomy: {path}")
    print(f"disciplines={n_disc} domains={n_dom} violations={len(problems)}")
    for p in problems:
        print("  - " + p)
    if problems:
        print(f"FAIL-CLOSED: {len(problems)} partition violation(s) — do not render the menu")
        return 1
    print("CLEAN: MECE partition holds (every raw synonym -> exactly one (axis, id))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
