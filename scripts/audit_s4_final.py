#!/usr/bin/env python3
"""audit_s4_final.py — deterministic pre-S5 forensic audit (default S4→S5 gate).

Runs on the FINAL checkpoint (post dedup + remap) BEFORE S5 consumes it. Fails
closed (exit non-zero) on ANY of:

  completeness   — all schema keys present + required fields non-empty.
  uniqueness     — fb_id unique + valid 64-hex; name unique (BUG-195 guard).
  ontology       — content_type / extraction_type / depth / discipline / domains
                   are all within the canonical value sets (D2323 + taxonomy).
  stamps         — schema_version / taxonomy_version / manifest_hash /
                   pipeline_commit / gen_model / classify_model single-valued.
  raw-preserve   — discipline=="emerging" ⇒ discipline_raw non-empty;
                   "emerging" ∈ domains ⇒ domains_raw non-empty (D2378/D2399).
  provenance     — source_clusters / source_segments / source_principle_ids
                   non-empty (S2→S4 carry-through, D2439/D2443).
  drift          — is_specialized == (depth == "specialized") (BUG-186/D2485).

The deterministic gate never calls an LLM (OMLX is saturated during S4); the
cross-family gemma classification spot-check is a separate, optional pass
(scripts/run_forensic_audit_parallel.py + /tmp/s4_focused_audit.py).

Usage:
    python3 scripts/audit_s4_final.py [--checkpoint PATH] [--json]
Exit codes:
    0  all checks pass
    1  at least one check failed (fail-closed — do NOT advance to S5)
    2  checkpoint missing/unreadable
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import load_jsonl
from pipeline.pipeline_paths import (
    STAGE4_5_CHECKPOINT, STAGE4_CHECKPOINT,
    S4_PT_OUTPUT, S4_PI_OUTPUT, S4_GE_OUTPUT, S4_TI_OUTPUT,
)
from pipeline.schemas import CANONICAL_DOMAINS, CANONICAL_DISCIPLINES

HEX64 = re.compile(r"^[0-9a-f]{64}$")

# D2323 two-axis ontology value sets (content_types.yaml + taxonomy_v5.yaml).
CONTENT_TYPES = {"principle", "process_template", "process_instance",
                 "tool_instruction", "growth_edge"}
EXTRACTION_TYPES = {"causal_mechanism", "descriptive_model",
                    "normative_heuristic", "empirical_pattern"}
DEPTHS = {"universal", "cross-domain", "domain", "specialized"}
MATCH_METHODS = {"exact", "synonym", "emerging_real", "emerging_unmapped", "alias"}

# Schema keys (D187/D2323). REQUIRED must be non-empty; NULLABLE may be null/[].
REQUIRED = {
    "fb_id", "name", "definition", "mechanism", "boundary", "consequence",
    "content_type", "extraction_type", "application", "failure_mode",
    "elaboration", "keywords", "domains", "discipline", "domains_raw",
    "discipline_raw", "depth", "is_specialized", "evidence", "context",
    "accessibility", "intimacy_boundary", "provenance", "is_convergent",
    "origin", "difficulty_level", "temporal_scope", "source_clusters",
    "source_books", "source_ids", "citation", "source_authors",
    "source_diversity", "primary_source", "source_principle_ids",
    "source_segments", "evidence_passages", "evidence_passages_shown",
    "source_text", "is_summary", "fb_version", "classification_status",
    "taxonomy_match_method", "schema_version", "gen_model", "classify_model",
    "pipeline_commit", "taxonomy_version", "manifest_hash", "pipeline_run_id",
    "created_at",
}
NULLABLE = {"classification_error", "classification_errors", "feedback_score",
            "jargon", "prerequisite_fbs", "procedural_skill", "usage_count",
            "feedback_count"}

# ── D2072/D2073 non-principle sidecars (co-located with the checkpoint) ──
# BUG-169/BUG-182: `body_incomplete: true` marks an "empty shell" — header +
# provenance fields present but the type-specific BODY is empty. These are
# gated by `commit_non_fb_types: false` so they never reach S6, but they ARE
# S4 output and must be swept here (not just the principle checkpoint).
# body_fields mirror `_empty_shell()` in scripts/fix_singleton_48_posthoc.py.
SIDECARS: list[tuple[str, str, list[str]]] = [
    ("process_template", S4_PT_OUTPUT,
     ["steps", "trigger", "prerequisite", "done_condition", "failure_mode"]),
    ("process_instance", S4_PI_OUTPUT,
     ["instance_text", "actors", "outcome_metric", "outcome_qualitative"]),
    ("tool_instruction", S4_TI_OUTPUT,
     ["parameters", "syntax"]),
    ("growth_edge", S4_GE_OUTPUT,
     ["body", "category", "actionable", "status", "priority"]),
]


def _nonempty(v) -> bool:
    """A value counts as filled unless it is None/""/empty-collection."""
    if v is None:
        return False
    if isinstance(v, str) and not v.strip():
        return False
    if isinstance(v, (list, dict, tuple)) and len(v) == 0:
        return False
    return True


def audit(fbs: list[dict]) -> list[str]:
    """Return a list of violation strings (empty == pass)."""
    errs: list[str] = []
    n = len(fbs)
    if n == 0:
        return ["checkpoint is empty (0 records)"]

    disc_canon = set(CANONICAL_DISCIPLINES)
    dom_canon = set(CANONICAL_DOMAINS)

    # ── completeness ──
    all_keys = REQUIRED | NULLABLE
    for i, fb in enumerate(fbs):
        missing = [k for k in all_keys if k not in fb]
        if missing:
            errs.append(f"record[{i}] missing keys: {missing}")
            break  # one sample is enough to fail; avoid 6k duplicate lines
        empty = [k for k in REQUIRED if not _nonempty(fb.get(k))]
        if empty:
            errs.append(f"record[{i}] empty required fields: {empty[:12]}")
            break

    # ── uniqueness ──
    ids = [fb.get("fb_id") for fb in fbs]
    bad_hex = [i for i, x in enumerate(ids) if not (isinstance(x, str) and HEX64.match(x))]
    if bad_hex:
        errs.append(f"{len(bad_hex)} records with invalid fb_id (non-64-hex): e.g. {ids[bad_hex[0]]!r}")
    dup_ids = len(ids) - len(set(ids))
    if dup_ids:
        errs.append(f"{dup_ids} duplicate fb_id (post-dedup collision remains)")
    names = [fb.get("name") for fb in fbs]
    dup_names = len(names) - len(set(names))
    if dup_names:
        errs.append(f"{dup_names} duplicate names (BUG-195 name-collision surface)")

    # ── ontology ──
    bad_ct = sum(1 for fb in fbs if fb.get("content_type") not in CONTENT_TYPES)
    if bad_ct: errs.append(f"{bad_ct} invalid content_type")
    bad_et = sum(1 for fb in fbs if fb.get("extraction_type") not in EXTRACTION_TYPES)
    if bad_et: errs.append(f"{bad_et} invalid extraction_type")
    bad_depth = sum(1 for fb in fbs if fb.get("depth") not in DEPTHS)
    if bad_depth: errs.append(f"{bad_depth} invalid depth")
    bad_disc = sum(1 for fb in fbs if fb.get("discipline") not in disc_canon)
    if bad_disc: errs.append(f"{bad_disc} discipline not in canonical set")
    bad_dom = sum(1 for fb in fbs for d in (fb.get("domains") or []) if d not in dom_canon)
    if bad_dom: errs.append(f"{bad_dom} domain entries not in canonical set")
    bad_mm = sum(1 for fb in fbs if fb.get("taxonomy_match_method") not in MATCH_METHODS)
    if bad_mm: errs.append(f"{bad_mm} invalid taxonomy_match_method")

    # ── stamps ──
    for key in ("schema_version", "taxonomy_version", "manifest_hash",
                "pipeline_commit", "gen_model", "classify_model"):
        vals = {fb.get(key) for fb in fbs}
        if len(vals) != 1:
            errs.append(f"stamp {key} not single-valued: {sorted(str(v) for v in vals)[:5]}")

    # ── raw-preserve ──
    n = sum(1 for fb in fbs
            if fb.get("discipline") == "emerging" and not _nonempty(fb.get("discipline_raw")))
    if n: errs.append(f"{n} records: discipline=='emerging' but discipline_raw empty (D2378)")
    n = sum(1 for fb in fbs
            if "emerging" in (fb.get("domains") or []) and not _nonempty(fb.get("domains_raw")))
    if n: errs.append(f"{n} records: 'emerging' in domains but domains_raw empty (D2378)")

    # ── provenance ──
    for key in ("source_clusters", "source_segments", "source_principle_ids"):
        n = sum(1 for fb in fbs if not _nonempty(fb.get(key)))
        if n: errs.append(f"{n} records with empty {key} (S2→S4 provenance dropped)")

    # ── drift (BUG-186 is_specialized derive) ──
    n = sum(1 for fb in fbs if fb.get("is_specialized") != (fb.get("depth") == "specialized"))
    if n: errs.append(f"{n} records: is_specialized != (depth=='specialized') drift (BUG-186)")

    return errs


def sweep_sidecars(parent: Path) -> dict:
    """Sweep the 4 non-principle sidecars for empty shells + ontology drift.

    Returns {content_type: {...}} with per-sidecar totals, body_incomplete
    counts/names, and ontology-misroute counts. A sidecar whose file does not
    exist is reported with ``missing_file: True`` (S4 may legitimately emit 0
    records of a type — only flagged if the file is absent AND S4 reported it).
    """
    report: dict = {}
    for ct, fname, body_fields in SIDECARS:
        p = parent / fname
        if not p.exists():
            report[ct] = {"path": str(p), "total": 0, "missing_file": True}
            continue
        recs = load_jsonl(p, context=f"sidecar {ct}")
        bi = [r for r in recs if r.get("body_incomplete")]
        wrong_ct = [r for r in recs if r.get("content_type") != ct]
        bad_et = [r for r in recs if r.get("extraction_type") not in EXTRACTION_TYPES]
        # confirm the body_incomplete flag is consistent with an actually-empty
        # body. NOTE: body fields are strings/lists/dicts/bools — truthiness
        # (not _nonempty) matches `_empty_shell()`, so `actionable=False` and
        # `parameters=[]` correctly read as EMPTY, not filled.
        inconsistent = [r for r in bi
                        if any(r.get(f) for f in body_fields)]
        report[ct] = {
            "path": str(p),
            "total": len(recs),
            "body_incomplete": len(bi),
            "body_incomplete_names": [r.get("name", "?") for r in bi],
            "flag_body_nonempty": len(inconsistent),
            "wrong_content_type": len(wrong_ct),
            "bad_extraction_type": len(bad_et),
        }
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="pre-S5 forensic audit (deterministic, fail-closed)")
    ap.add_argument("--checkpoint", type=Path, default=None,
                    help="checkpoint to audit (default: STAGE4_5_CHECKPOINT else STAGE4_CHECKPOINT)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict-sidecars", action="store_true",
                    help="escalate body_incomplete empty shells from WARN to FAIL "
                         "(default: WARN — sidecars are gated by commit_non_fb_types:false)")
    args = ap.parse_args()

    ckpt = args.checkpoint or (STAGE4_5_CHECKPOINT if STAGE4_5_CHECKPOINT.exists() else STAGE4_CHECKPOINT)
    if not ckpt.exists():
        msg = f"❌ audit checkpoint not found: {ckpt}"
        print(msg, file=sys.stderr)
        return 2

    fbs = load_jsonl(ckpt, context="pre-S5 forensic audit")
    errs = audit(fbs)

    # ── non-principle sidecar sweep (BUG-169/BUG-182 empty-shell visibility) ──
    sidecars = sweep_sidecars(ckpt.parent)
    sidecar_errs: list[str] = []
    total_bi = 0
    for ct, rep in sorted(sidecars.items()):
        if rep.get("missing_file"):
            continue  # S4 may legitimately emit 0 records of a type
        total_bi += rep["body_incomplete"]
        if rep["wrong_content_type"]:
            sidecar_errs.append(f"sidecar {ct}: {rep['wrong_content_type']} record(s) routed to wrong file")
        if rep["bad_extraction_type"]:
            sidecar_errs.append(f"sidecar {ct}: {rep['bad_extraction_type']} invalid extraction_type")
        if rep["flag_body_nonempty"]:
            sidecar_errs.append(f"sidecar {ct}: {rep['flag_body_nonempty']} body_incomplete flag with non-empty body")

    print("=" * 60)
    print("🔬 PRE-S5 FORENSIC AUDIT (deterministic)")
    print(f"   checkpoint: {ckpt}")
    print(f"   total FBs:  {len(fbs)}")
    print("-" * 60)
    if errs:
        for e in errs:
            print(f"   🛑 {e}")
    else:
        print("   ✅ completeness / uniqueness / ontology / stamps / raw-preserve")
        print("   ✅ provenance / drift — all PASS")
    print("-" * 60)
    print("   📦 NON-PRINCIPLE SIDECAR SWEEP (empty-shell / ontology)")
    for ct, rep in sorted(sidecars.items()):
        if rep.get("missing_file"):
            print(f"      · {ct:18s} — file absent (0 records emitted)")
            continue
        flag = "⚠️ " if rep["body_incomplete"] else "✅ "
        print(f"      {flag}{ct:17s} total={rep['total']:5d} "
              f"body_incomplete={rep['body_incomplete']:3d} "
              f"wrong_ct={rep['wrong_content_type']} bad_et={rep['bad_extraction_type']}")
        for nm in rep["body_incomplete_names"][:6]:
            print(f"           ↳ empty shell: {nm}")
        if rep["body_incomplete"] > 6:
            print(f"           ↳ … and {rep['body_incomplete'] - 6} more")
    print("=" * 60)

    if args.strict_sidecars and total_bi:
        sidecar_errs.append(f"{total_bi} body_incomplete empty shells (--strict-sidecars)")
    if sidecar_errs:
        for e in sidecar_errs:
            errs.append(e)

    if args.json:
        import json
        print(json.dumps({"checkpoint": str(ckpt), "total": len(fbs),
                          "violations": errs, "pass": not errs,
                          "sidecars": sidecars,
                          "body_incomplete_total": total_bi}))

    if errs:
        print(f"🛑 AUDIT FAILED — {len(errs)} violation(s). Do NOT advance to S5.", file=sys.stderr)
        return 1
    print("✅ Forensic audit passed — S5 may proceed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
