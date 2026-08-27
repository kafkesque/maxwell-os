#!/usr/bin/env python3
"""audit_content_type_contract.py — verify every content type meets the agreed
schema (metadata + properties + segments) in config/content_types.yaml (D2449).

Two contracts are checked:
  * S2 contract  — what stage2_extract must emit per content_type:
      shared core_body (name/definition), the principle-only skeleton
      (mechanism/boundary/consequence — REQUIRED non-empty for principle,
      OPTIONAL for PT/PI/GE/TI per D2475),
      elaboration PRINCIPLE-ONLY (non-empty for principle, empty for PT/PI/GE/TI),
      the per-type `s2_body_fields`, and classification labels
      (content_type ∈ 5 roles, extraction_type ∈ 4 forms, is_summary, route).
  * S4 contract  — what stage4_merge must persist per content_type:
      R14 stamps, classification (domains/discipline/depth/evidence + raw),
      provenance (source_books/source_clusters/source_segments/source_authors/
      citation/primary_source/source_diversity), versioning (fb_version),
      and runtime counters.

Everything is read from config/content_types.yaml — nothing re-declared (C12).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"

# ── Ontology load ───────────────────────────────────────────────────────────
def _load_ontology() -> dict:
    import yaml
    with open(CONFIG_DIR / "content_types.yaml") as f:
        return yaml.safe_load(f) or {}


def _nonempty(v) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return True


# D2475: shared vs principle-only body cardinality is sourced from
# content_types.yaml (C12 config-first) — nothing re-declared here. Fallbacks
# mirror the YAML for resilience if the key is ever renamed/dropped.
_SHARED_BODY_FALLBACK = ["name", "definition"]
_PRINCIPLE_ONLY_FALLBACK = ["mechanism", "boundary", "consequence"]


def _shared_body(onto: dict) -> list[str]:
    return [str(f) for f in onto.get("shared_body", _SHARED_BODY_FALLBACK)]


def _principle_only_body(onto: dict) -> list[str]:
    return [str(f) for f in onto.get("principle_only_body", _PRINCIPLE_ONLY_FALLBACK)]


# ── Loaders ─────────────────────────────────────────────────────────────────
def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8")
    # Support BOTH strict JSONL (one compact object per line) and pretty-printed
    # JSON (objects spanning lines) — the smoke scripts wrote pretty-printed.
    try:
        return [json.loads(line) for line in raw.splitlines() if line.strip()]
    except json.JSONDecodeError:
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
        except json.JSONDecodeError:
            return []


def _content_type_of(rec: dict) -> str:
    return (rec.get("content_type") or "principle").strip() or "principle"


# ── Auditors ────────────────────────────────────────────────────────────────
# Array fields that MUST be non-empty for the content type to be meaningful
# (the "segments" of the object). String fields may be legitimately empty when
# the passage does not provide them (D2448 prompt note).
REQUIRED_NONEMPTY_ARRAYS: dict[str, list[str]] = {
    "process_template": ["steps"],
    "process_instance": ["actors"],
    "tool_instruction": ["parameters"],
}


def audit_s2(rec: dict, ct: str, onto: dict, issues: list[str]) -> None:
    for f in _shared_body(onto):
        if f not in rec or not _nonempty(rec.get(f)):
            issues.append(f"missing/empty shared:{f}")

    # D2475: mechanism/boundary/consequence are PRINCIPLE-ONLY — required non-empty
    # only for principle; OPTIONAL (may be absent/empty) for PT/PI/TI/GE.
    if ct == "principle":
        for f in _principle_only_body(onto):
            if f not in rec or not _nonempty(rec.get(f)):
                issues.append(f"missing/empty principle-only:{f}")

    # elaboration PRINCIPLE-ONLY (D2448)
    elab = rec.get("elaboration")
    if ct == "principle":
        if not _nonempty(elab):
            issues.append("elaboration empty (principle REQUIRED)")
    else:
        if _nonempty(elab):
            issues.append(f"elaboration non-empty on {ct} (must be empty)")

    # per-type s2_body_fields — presence is required; only arrays must be non-empty
    for f in onto.get("s2_body_fields", {}).get(ct, []):
        if f not in rec:
            issues.append(f"missing s2_body_field:{f}")
        elif f in REQUIRED_NONEMPTY_ARRAYS.get(ct, []) and not _nonempty(rec.get(f)):
            issues.append(f"empty array s2_body_field:{f}")

    # classification labels
    content_type = rec.get("content_type")
    if content_type not in onto.get("content_types", {}):
        issues.append(f"invalid content_type:{content_type!r}")
    extraction_type = rec.get("extraction_type")
    if extraction_type not in onto.get("extraction_types", {}):
        issues.append(f"invalid extraction_type:{extraction_type!r}")
    if "is_summary" in rec and not isinstance(rec.get("is_summary"), bool):
        issues.append("is_summary not bool")
    route = rec.get("route")
    if route not in ("FB", "NULL"):
        issues.append(f"invalid route:{route!r}")


def audit_s4(rec: dict, ct: str, onto: dict, issues: list[str]) -> None:
    """S4 contract. Structural (stamps + provenance) applies to ALL types.

    Classification/discovery/versioning/runtime enrichment applies to `principle`
    only today; non-principle sidecars are intentionally NOT enriched yet
    (BUG-170 commit-frontier B→A, deferred per D2448) — so those are reported as
    a separate `deferred` note, not a structural failure.
    """
    # R14 stamps — all types
    for f in onto.get("metadata", {}).get("stamps", []):
        if f not in rec or not _nonempty(rec.get(f)):
            issues.append(f"missing/empty stamp:{f}")
    # provenance — all types. Non-principle sidecars carry `source_cluster`
    # (singular S2 origin); merged principles carry `source_clusters` (plural).
    for f in ("source_books", "source_segments", "source_authors", "citation"):
        if f not in rec:
            issues.append(f"missing provenance:{f}")
    if ct == "principle":
        for f in ("source_clusters", "source_diversity", "primary_source"):
            if f not in rec:
                issues.append(f"missing provenance:{f}")
        for f in ("domains", "discipline", "depth", "evidence", "classify_model"):
            if f not in rec or not _nonempty(rec.get(f)):
                issues.append(f"missing/empty classification:{f}")
        if "fb_version" not in rec:
            issues.append("missing versioning:fb_version")
        for f in ("usage_count", "feedback_score", "feedback_count"):
            if f not in rec:
                issues.append(f"missing runtime:{f}")
    else:
        # BUG-170 deferred enrichment — note, don't fail
        for f in ("domains", "discipline", "depth", "evidence", "fb_version"):
            if f not in rec:
                issues.append(f"DEFERRED(enum) missing:{f}")


# ── Report helpers ──────────────────────────────────────────────────────────
def _report(label: str, results: dict[str, list[str]]) -> bool:
    print(f"\n=== {label} ===")
    ok = True
    for ct in sorted(results):
        issues = results[ct]
        hard = [i for i in issues if "DEFERRED" not in i]
        deferred = [i for i in issues if "DEFERRED" in i]
        if not hard and not deferred:
            print(f"  ✅ {ct:18s} — conforms")
            continue
        if hard:
            ok = False
            print(f"  ❌ {ct:18s} — {len(hard)} structural issue(s):")
            for i in hard[:8]:
                print(f"        • {i}")
        if deferred:
            print(f"  ⚠️  {ct:18s} — {len(deferred)} deferred (BUG-170, known):")
            for i in deferred[:4]:
                print(f"        • {i.replace('DEFERRED(enum) ', '')}")
    if ok and not any(
        i for v in results.values() for i in v if "DEFERRED" not in i
    ):
        print("  ✅ no structural gaps (deferred enrichment noted above)")
    return ok


def audit_golden(onto: dict) -> tuple[dict[str, list[str]], bool]:
    """Audit the single-source golden set's expected_fb (S2 ground truth)."""
    import yaml
    golden = yaml.safe_load(open(CONFIG_DIR / "golden" / "stage2_fewshot_single_source.yaml"))
    results: dict[str, list[str]] = {}
    for ex in golden["examples"]:
        if not ex.get("should_extract"):
            continue
        fb = ex["expected_fb"]
        ct = _content_type_of(fb)
        issues: list[str] = []
        audit_s2(fb, ct, onto, issues)
        if issues:
            results.setdefault(ct, []).extend([f"{ex['id']}: {i}" for i in issues])
    ok = not results
    return results, ok


def audit_s4_dir(in_dir: Path, onto: dict) -> tuple[dict[str, list[str]], bool]:
    results: dict[str, list[str]] = {}
    sidecars = {
        "checkpoint.jsonl": "principle",
        "process_templates.jsonl": "process_template",
        "process_instances.jsonl": "process_instance",
        "tool_instructions.jsonl": "tool_instruction",
        "growth_edges.jsonl": "growth_edge",
    }
    for fn, default_ct in sidecars.items():
        for rec in _load_jsonl(in_dir / fn):
            ct = _content_type_of(rec) if rec.get("content_type") else default_ct
            issues: list[str] = []
            audit_s4(rec, ct, onto, issues)
            if issues:
                results.setdefault(ct, []).extend(
                    [f"{rec.get('name', rec.get('fb_id', '?'))[:30]}: {i}" for i in issues]
                )
    ok = not results
    return results, ok


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Audit content-type schema contract (D2449).")
    ap.add_argument("--s4-dir", type=Path, default=None, help="S4 output dir (optional)")
    args = ap.parse_args()

    onto = _load_ontology()
    all_ok = True

    g_results, g_ok = audit_golden(onto)
    all_ok = _report("GOLDEN SET (S2 contract — ground truth)", g_results) and all_ok

    if args.s4_dir:
        s4_results, s4_ok = audit_s4_dir(args.s4_dir, onto)
        all_ok = _report(f"S4 OUTPUT ({args.s4_dir})", s4_results) and all_ok

    print()
    print("✅ ALL CONTENT TYPES CONFORM" if all_ok else "❌ CONFORMANCE GAPS FOUND")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
