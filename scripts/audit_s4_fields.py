#!/usr/bin/env python3
"""audit_s4_fields.py — verify S4 output field completeness against the D2323 ontology.

Checks that every object-type-dependent segment (definition, application,
failure_mode, jargon, trigger, steps, done_condition, tool_name, syntax, etc.)
is present and non-empty where the content-type contract requires it.

C12: field requirements are read from config/content_types.yaml (single source
of truth), never re-declared here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"


def _load_ontology() -> dict:
    import yaml
    with open(CONFIG_DIR / "content_types.yaml") as f:
        return yaml.safe_load(f) or {}


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def _nonempty(v) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return v is not None


# D2323 ontology + D2475 + D2488: cardinality is read from content_types.yaml
# (single source of truth, C12) — NOT re-declared here. For `principle`:
#   shared_body             → REQUIRED non-empty (name, definition)
#   principle_only_body     → REQUIRED non-empty (mechanism, boundary, consequence)
#   principle_required_body → REQUIRED non-empty (application D2371, failure_mode
#                             D2488, elaboration) — S4 CRIBS, NOT optional.
#   principle_optional_body → OPTIONAL (jargon only, D2123 — omit if empty).
# Per-type non-principle extras come from s2_body_fields. Treating the ontology's
# `core_body` UNION as universal is the wrong model — it over-flags
# legitimately-empty fields on PT/PI/GE/TI.


def _cardinality(onto: dict) -> dict[str, list[str]]:
    """Return the body-field cardinality contract from content_types.yaml (C12)."""
    return {
        "shared": list(onto.get("shared_body", ["name", "definition"])),
        "principle_only": list(onto.get("principle_only_body", ["mechanism", "boundary", "consequence"])),
        "principle_required": list(onto.get("principle_required_body", ["application", "failure_mode", "elaboration"])),
        "principle_optional": list(onto.get("principle_optional_body", ["jargon"])),
    }


def _required_for(ct: str, s2_fields: dict, card: dict[str, list[str]]) -> list[str]:
    required = list(card["shared"]) + s2_fields.get(ct, [])
    if ct == "principle":
        required += card["principle_only"] + card["principle_required"]
    return required


def _optional_for(ct: str, card: dict[str, list[str]]) -> list[str]:
    return card["principle_optional"] if ct == "principle" else ["jargon"]


def audit_dir(in_dir: Path) -> dict:
    """Audit an S4 output dir (checkpoint.jsonl + PT/PI/GE/TI sidecars)."""
    onto = _load_ontology()
    s2_fields = onto.get("s2_body_fields", {})
    card = _cardinality(onto)

    results: dict[str, dict] = {}

    def _audit_rec(rec: dict, ct: str) -> None:
        results.setdefault(ct, {"n": 0, "missing": {}, "empty": {}, "optional_empty": {}})
        r = results[ct]
        r["n"] += 1
        for f in _required_for(ct, s2_fields, card):
            if f not in rec:
                r["missing"][f] = r["missing"].get(f, 0) + 1
            elif not _nonempty(rec.get(f)):
                r["empty"][f] = r["empty"].get(f, 0) + 1
        for f in _optional_for(ct, card):
            if f not in rec or not _nonempty(rec.get(f)):
                r["optional_empty"][f] = r["optional_empty"].get(f, 0) + 1

    # Main checkpoint = principles only
    for rec in _load_jsonl(in_dir / "checkpoint.jsonl"):
        _audit_rec(rec, rec.get("content_type", "principle"))

    # Sidecars
    sidecar_map = {
        "process_templates.jsonl": "process_template",
        "process_instances.jsonl": "process_instance",
        "tool_instructions.jsonl": "tool_instruction",
        "growth_edges.jsonl": "growth_edge",
    }
    for fn, ct in sidecar_map.items():
        for rec in _load_jsonl(in_dir / fn):
            _audit_rec(rec, ct)

    return results


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Audit S4 field completeness (D2440).")
    ap.add_argument("--in-dir", required=True, type=Path)
    args = ap.parse_args()

    results = audit_dir(args.in_dir)

    if not results:
        print(f"❌ No S4 output found in {args.in_dir}")
        return 1

    print(f"=== S4 field-completeness audit — {args.in_dir} ===\n")
    all_ok = True
    for ct in sorted(results):
        r = results[ct]
        issues = []
        for f, n in sorted(r["missing"].items()):
            issues.append(f"missing:{f}({n})")
        for f, n in sorted(r["empty"].items()):
            issues.append(f"empty:{f}({n})")
        opt = ", ".join(f"{f}({n},opt)" for f, n in sorted(r["optional_empty"].items()))
        status = "✅" if not issues else "⚠️"
        if issues:
            all_ok = False
        line = f"{status} {ct:18s} n={r['n']:3d}  {', '.join(issues) if issues else 'all required fields intact'}"
        if opt:
            line += f"  [optional-empty: {opt}]"
        print(line)

    print(f"\n{'✅ ALL CONTENT TYPES HAVE INTACT REQUIRED FIELDS' if all_ok else '⚠️ REQUIRED-FIELD GAPS FOUND — see above'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
