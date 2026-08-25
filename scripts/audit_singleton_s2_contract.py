#!/usr/bin/env python3
"""audit_singleton_s2_contract.py — validate LIVE S2 singleton FBs against
config/content_types.yaml (D2323/D2449/D2459).

Checks every record in a singleton S2 checkpoint against the AGREED S2
requirements in content_types.yaml:

  * METADATA — R14 stamps (schema_version/gen_model/pipeline_commit/
    pipeline_run_id/created_at) + provenance (source_books, source_cluster(s),
    source_segments, evidence_passages, citation, source_authors,
    source_diversity, primary_source)
  * SEGMENTS  — evidence_passages non-empty (1-5 verbatim quotes) +
    source_segments present; evidence_passages_shown present
  * PROPERTIES (body) — shared core_body (name/definition/mechanism/boundary/
    consequence) present + non-empty for EVERY content_type; elaboration
    PRINCIPLE-ONLY (non-empty ⇔ principle); per-type s2_body_fields all present
    (typed placeholders []/""/False allowed)
  * CLASSIFICATION — content_type ∈ 5 roles; extraction_type ∈ 4 forms;
    is_summary bool; content×extraction pairing reported (informational)

Usage:
  python3 scripts/audit_singleton_s2_contract.py \
      --checkpoint "knowledge pipeline/stage2_extract/t11/singleton_fbs.jsonl" \
      [--config config/content_types.yaml] [--json]

Exit 0 = all records conform; 1 = violations found.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ── Ontology (single source of truth: config/content_types.yaml — C12) ──────
SHARED_SKELETON = ["name", "definition", "mechanism", "boundary", "consequence"]
STAMPS = ["schema_version", "gen_model", "pipeline_commit", "pipeline_run_id", "created_at"]
PROVENANCE = ["source_books", "source_segments", "evidence_passages", "citation",
              "source_authors", "source_diversity", "primary_source"]
EXTRA_STAMPS = ["taxonomy_version", "manifest_hash"]


def _nonempty(v) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, dict)):
        return len(v) > 0
    return True


def load_ontology(config: Path) -> dict:
    import yaml
    with open(config) as f:
        return yaml.safe_load(f) or {}


def load_checkpoint(path: Path) -> list[dict]:
    if not path.exists():
        print(f"❌ checkpoint not found: {path}")
        sys.exit(1)
    raw = path.read_text(encoding="utf-8")
    try:
        return [json.loads(line) for line in raw.splitlines() if line.strip()]
    except json.JSONDecodeError:
        data = json.loads(raw)
        return data if isinstance(data, list) else [data]


# ── Per-record contract check ───────────────────────────────────────────────
def check_record(fb: dict, onto: dict) -> list[str]:
    """Return a list of violation strings (empty = conformant)."""
    v: list[str] = []

    # 1. Classification (Axis 1 + Axis 2 + gate flag)
    ct = str(fb.get("content_type") or "").strip()
    et = str(fb.get("extraction_type") or "").strip()
    valid_ct = set(onto.get("content_types", {}).keys())
    valid_et = set(onto.get("extraction_types", {}).keys())
    if ct not in valid_ct:
        v.append(f"content_type={ct!r} ∉ valid roles {sorted(valid_ct)}")
    if et not in valid_et:
        v.append(f"extraction_type={et!r} ∉ valid forms {sorted(valid_et)}")
    if not isinstance(fb.get("is_summary"), bool):
        v.append(f"is_summary={fb.get('is_summary')!r} not bool")

    # 2. Metadata — R14 stamps + provenance
    for k in STAMPS:
        if not fb.get(k):
            v.append(f"missing stamp: {k}")
    for k in EXTRA_STAMPS:
        if not fb.get(k):
            v.append(f"missing stamp: {k}")
    for k in PROVENANCE:
        if not _nonempty(fb.get(k)):
            v.append(f"missing provenance: {k}")
    if not _nonempty(fb.get("source_cluster")) and not _nonempty(fb.get("source_clusters")):
        v.append("missing source_cluster(s)")
    if not _nonempty(fb.get("source_ids")):
        v.append("missing provenance: source_ids")

    # 3. Segments — evidence passages (up to 5 verbatim quotes) + shown
    eps = fb.get("evidence_passages") or []
    if not isinstance(eps, list) or not eps:
        v.append("evidence_passages empty (needs ≥1 verbatim quote)")
    elif len(eps) > 5:
        v.append(f"evidence_passages {len(eps)} > 5 (contract: up to 5)")
    if not _nonempty(fb.get("evidence_passages_shown")):
        v.append("missing evidence_passages_shown")

    # 4. Shared core_body — present + non-empty for EVERY content type
    for k in SHARED_SKELETON:
        if not _nonempty(fb.get(k)):
            v.append(f"core_body '{k}' empty")

    # 5. elaboration PRINCIPLE-ONLY (D2448/D2452 — schema-guaranteed)
    elab = str(fb.get("elaboration") or "").strip()
    if ct == "principle" and not elab:
        v.append("principle elaboration empty (REQUIRED for principle)")
    elif ct != "principle" and elab:
        v.append(f"{ct} elaboration non-empty ({len(elab)} chars) — must be ''")

    # 6. Per-type s2_body_fields — all present (typed placeholders allowed)
    s2_fields = (onto.get("s2_body_fields") or {}).get(ct) or []
    for k in s2_fields:
        if k not in fb:
            v.append(f"{ct} missing s2_body_field: {k}")

    # 7. Singleton-path flags
    if fb.get("is_singleton_fb") is not True:
        v.append(f"is_singleton_fb={fb.get('is_singleton_fb')!r} not True (singleton path)")
    if fb.get("is_convergent") is not False:
        v.append(f"is_convergent={fb.get('is_convergent')!r} not False (singleton path)")

    return v


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint", type=Path, default=REPO_ROOT / "knowledge pipeline/stage2_extract/t11/singleton_fbs.jsonl")
    ap.add_argument("--config", type=Path, default=REPO_ROOT / "config/content_types.yaml")
    ap.add_argument("--json", action="store_true", help="machine-readable violations summary")
    args = ap.parse_args()

    onto = load_ontology(args.config)
    fbs = load_checkpoint(args.checkpoint)
    if not fbs:
        print("⚠️  checkpoint empty — nothing to audit")
        return 1

    ct_counts: Counter = Counter(f.get("content_type") or "?" for f in fbs)
    et_counts: Counter = Counter(f.get("extraction_type") or "?" for f in fbs)
    pairs: Counter = Counter((f.get("content_type"), f.get("extraction_type")) for f in fbs)

    violations: list[tuple[int, str, str]] = []  # (idx, fb_id_short, msg)
    per_rec: list[list[str]] = []
    for i, fb in enumerate(fbs):
        rec_v = check_record(fb, onto)
        per_rec.append(rec_v)
        for msg in rec_v:
            violations.append((i, str(fb.get("fb_id", "?"))[:12], msg))

    # ── Report ───────────────────────────────────────────────────────────────
    if not args.json:
        print(f"\n{'=' * 72}")
        print(f"SINGLETON S2 CONTRACT AUDIT — {args.checkpoint}")
        print(f"  records: {len(fbs)} | ontology: {args.config}")
        print(f"{'=' * 72}")
        print(f"\n▶ Classification — content_type (5 roles):")
        for ct, n in ct_counts.most_common():
            ok = "✅" if ct in onto.get("content_types", {}) else "❌"
            print(f"    {ok} {ct:22} {n:4}")
        print(f"\n▶ Classification — extraction_type (4 forms):")
        for et, n in et_counts.most_common():
            ok = "✅" if et in onto.get("extraction_types", {}) else "❌"
            print(f"    {ok} {et:22} {n:4}")
        print(f"\n▶ content_type × extraction_type pairs:")
        for (ct, et), n in pairs.most_common():
            default = (onto.get("content_to_extraction_type") or {}).get(ct, "")
            tag = "default-match" if et == default else ""
            print(f"    {ct:18} × {et:20} {n:4}  {tag}")

        print(f"\n▶ Violations by category:")
        cats: Counter = Counter()
        for _, _, msg in violations:
            head = msg.split(" ")[0].split("=")[0].strip("'")
            cats[head] += 1
        if not violations:
            print("    ✅ NONE — every record conforms")
        else:
            for cat, n in cats.most_common():
                print(f"    ❌ {cat}: {n}")

        if violations:
            print(f"\n▶ Sample violations (first 12):")
            for idx, fid, msg in violations[:12]:
                print(f"    [{idx}] {fid} — {msg}")

        print(f"\n{'=' * 72}")
        print("✅ ALL RECORDS CONFORM TO content_types.yaml" if not violations
              else f"❌ {len(violations)} VIOLATIONS across {len(fbs)} records")
        print(f"{'=' * 72}")
    else:
        print(json.dumps({
            "records": len(fbs),
            "violations": len(violations),
            "by_category": dict(cats := Counter(m.split(" ")[0].split("=")[0].strip("'") for _, _, m in violations)),
            "content_types": dict(ct_counts),
            "extraction_types": dict(et_counts),
            "content_x_extraction": {f"{a}|{b}": n for (a, b), n in pairs.items()},
        }, indent=1))

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
