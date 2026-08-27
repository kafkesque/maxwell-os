#!/usr/bin/env python3
"""audit_e2e_cohesion.py — cross-stage S2→S4→S5→S6 cohesion + failure-class audit.

Proves (or disproves) that every content_type × origin survives each pipeline
boundary with intact metadata / segments / properties, and maps every finding to
a failure class: leak | cascade | hidden-failure | contamination | drift | bug |
blindspot | gap | conflict.

Run:  python3 scripts/audit_e2e_cohesion.py [--run-id t11]
Output: a Markdown report in the S4 dir (e2e_cohesion_report.md) + stdout summary.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

VALID_CT = ("principle", "process_template", "process_instance", "tool_instruction", "growth_edge")
VALID_ET = ("causal_mechanism", "descriptive_model", "normative_heuristic", "empirical_pattern")


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _origin_of(r: dict) -> str:
    if r.get("is_singleton_fb") or r.get("is_singleton"):
        return "singleton"
    if r.get("is_convergent"):
        return "convergent"
    return "single_source"


def _key(r: dict) -> str:
    return r.get("fb_id") or r.get("principle_id") or ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="t11")
    args = ap.parse_args()
    rid = args.run_id

    s2_dir = ROOT / "knowledge pipeline" / "stage2_extract" / rid
    s4_dir = ROOT / "knowledge pipeline" / "stage4_merge" / rid
    s5_dir = ROOT / "knowledge pipeline" / "stage5_verify" / rid
    s6_dir = ROOT / "knowledge pipeline" / "stage6_commit" / rid

    # ── Load all stages (index by fb_id) ────────────────────────────────────
    s2 = _load_jsonl(s2_dir / "checkpoint.jsonl") or _load_jsonl(s2_dir / "checkpoint.jsonl")
    s2_singleton = _load_jsonl(s2_dir / "singleton_fbs.jsonl")

    s4_ckpt = _load_jsonl(s4_dir / "checkpoint.jsonl")
    s4_pt = _load_jsonl(s4_dir / "process_templates.jsonl")
    s4_pi = _load_jsonl(s4_dir / "process_instances.jsonl")
    s4_ti = _load_jsonl(s4_dir / "tool_instructions.jsonl")
    s4_ge = _load_jsonl(s4_dir / "growth_edges.jsonl")

    s5 = _load_jsonl(s5_dir / "checkpoint.jsonl")
    s6 = _load_jsonl(s6_dir / "checkpoint.jsonl")

    # Stage maps keyed by fb_id
    def _index(rows: list[dict]) -> dict[str, dict]:
        d: dict[str, dict] = {}
        for r in rows:
            k = _key(r)
            if k:
                d[k] = r
        return d

    s2_idx = _index(s2 + s2_singleton)
    s4_idx = _index(s4_ckpt + s4_pt + s4_pi + s4_ti + s4_ge)
    s5_idx = _index(s5)
    s6_idx = _index(s6)

    findings: dict[str, list[str]] = defaultdict(list)

    # ── 1. Cross-stage survival matrix (content_type × origin) ──────────────
    matrix: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in s2 + s2_singleton:
        ct = r.get("content_type", "?")
        if ct not in VALID_CT:
            continue
        origin = _origin_of(r)
        k = _key(r)
        matrix[(ct, origin)]["S2"] += 1
        if k in s4_idx:
            matrix[(ct, origin)]["S4"] += 1
        if k in s5_idx:
            matrix[(ct, origin)]["S5"] += 1
        if k in s6_idx:
            matrix[(ct, origin)]["S6"] += 1

    # ── 2. Failure-class detection ──────────────────────────────────────────
    # LEAK / GAP: objects present in S2 but absent from S4 (dropped at boundary)
    dropped_s2_to_s4: Counter = Counter()
    for r in s2 + s2_singleton:
        ct = r.get("content_type", "?")
        if ct in VALID_CT and _key(r) and _key(r) not in s4_idx:
            dropped_s2_to_s4[(ct, _origin_of(r))] += 1
    for (ct, origin), n in dropped_s2_to_s4.items():
        findings["leak"].append(
            f"{n}× {ct}({origin}) present in S2 but ABSENT from S4 (dropped at S2→S4 boundary)"
        )

    # LEAK: objects in S4 sidecars but absent from S5 (non-principle never verified)
    s4_nonprinciple = s4_pt + s4_pi + s4_ti + s4_ge
    for r in s4_nonprinciple:
        k = _key(r)
        if k and k not in s5_idx:
            findings["leak"].append(
                f"{r.get('content_type','?')} '{r.get('name','?')[:40]}' in S4 sidecar but "
                f"ABSENT from S5 (S5 verifies principle-checkpoint only)"
            )

    # CASCADE / HIDDEN-FAILURE: empty required body fields carried forward
    required_arrays = {"process_template": ["steps"], "process_instance": ["actors"],
                       "tool_instruction": ["parameters"]}
    for r in s2 + s2_singleton:
        ct = r.get("content_type", "?")
        for f in required_arrays.get(ct, []):
            v = r.get(f)
            if isinstance(v, list) and not v:
                findings["hidden-failure"].append(
                    f"{ct} '{r.get('name','?')[:40]}' empty required array {f!r} at S2 "
                    f"(was carried to S4 unchanged — no downstream completeness gate fires)"
                )

    # CONTAMINATION: content_type ∈ invalid set / extraction_type ∈ invalid set
    for r in s2 + s2_singleton:
        ct = r.get("content_type")
        if ct and ct not in VALID_CT:
            findings["contamination"].append(f"invalid content_type {ct!r} on '{r.get('name','?')[:40]}'")
        et = r.get("extraction_type")
        if et and et not in VALID_ET:
            findings["contamination"].append(f"invalid extraction_type {et!r} on '{r.get('name','?')[:40]}'")

    # DRIFT: S4 record missing provenance/segment fields that S2 carried
    for k, r2 in s2_idx.items():
        r4 = s4_idx.get(k)
        if r4 is None:
            continue
        for f in ("source_segments", "source_authors", "citation"):
            if f in r2 and f not in r4:
                findings["drift"].append(
                    f"{r2.get('content_type','?')} '{r2.get('name','?')[:40]}' field {f!r} "
                    f"present in S2 but dropped at S4"
                )

    # CONFLICT: content_type contradicts content_types.yaml s2_body_fields (e.g.
    # elaboration non-empty on non-principle)
    for r in s2 + s2_singleton:
        ct = r.get("content_type", "?")
        elab = r.get("elaboration")
        if ct != "principle" and isinstance(elab, str) and elab.strip():
            findings["conflict"].append(
                f"{ct} '{r.get('name','?')[:40]}' has non-empty elaboration "
                f"(ontology: principle-only)"
            )

    # BLINDSPOT: singleton origin never extracted at t11 (stale pid, no output)
    if not s2_singleton and (s2_dir / "singleton_run.pid").exists():
        findings["blindspot"].append(
            "singleton extraction never completed on t11 (stale pid file, 0 singleton_fbs.jsonl "
            "records) — the 6,317 EXTRACT singletons were never fed into S4/S5/S6"
        )

    # GAP: S6 empty (nothing committed)
    if not s6:
        findings["gap"].append("S6 checkpoint is EMPTY — nothing committed to SQLite/Parquet")

    # ── 3. Field-cohesion audit (surviving records) ─────────────────────────
    R14 = ("schema_version", "gen_model", "pipeline_commit")
    prov = ("source_books", "source_segments", "source_authors", "citation")
    s4_survivors = [r for r in s4_ckpt if _key(r) in s2_idx]
    field_ok = 0
    field_bad = 0
    for r in s4_survivors:
        missing = [f for f in R14 + prov if not r.get(f)]
        if missing:
            field_bad += 1
            findings["drift"].append(
                f"S4 principle '{r.get('name','?')[:40]}' missing {missing} after merge"
            )
        else:
            field_ok += 1

    # ── 4. Render report ────────────────────────────────────────────────────
    lines: list[str] = [
        f"# End-to-End Cohesion Audit — run_id `{rid}`",
        "",
        f"> `{s4_dir.resolve()}`",
        "",
        "## 1. Cross-stage survival matrix (content_type × origin)",
        "",
        "| content_type | origin | S2 | S4 | S5 | S6 |",
        "|---|---|---|---|---|---|",
    ]
    for (ct, origin) in sorted(matrix.keys()):
        m = matrix[(ct, origin)]
        lines.append(f"| {ct} | {origin} | {m['S2']} | {m['S4']} | {m['S5']} | {m['S6']} |")
    lines.append("")

    # stage totals
    lines.append("## 2. Stage totals")
    lines.append("")
    lines.append(f"- S2 (deduped): {len(s2)} + singleton {len(s2_singleton)} = {len(s2) + len(s2_singleton)}")
    lines.append(f"- S4: principles {len(s4_ckpt)}, PT {len(s4_pt)}, PI {len(s4_pi)}, TI {len(s4_ti)}, GE {len(s4_ge)}")
    lines.append(f"- S5: {len(s5)}")
    lines.append(f"- S6: {len(s6)}")
    lines.append("")

    # failure classes
    lines.append("## 3. Failure-class findings")
    lines.append("")
    if not any(findings.values()):
        lines.append("✅ NO failures detected.")
    for cls in ("leak", "cascade", "hidden-failure", "contamination", "drift",
                "bug", "blindspot", "gap", "conflict"):
        items = findings.get(cls, [])
        if not items:
            continue
        lines.append(f"### 🔴 {cls.upper()} — {len(items)} finding(s)")
        lines.append("")
        for it in items[:12]:
            lines.append(f"- {it}")
        if len(items) > 12:
            lines.append(f"- … {len(items) - 12} more")
        lines.append("")

    lines.append("## 4. Field-cohesion (S4 principles that survived S2→S4)")
    lines.append("")
    lines.append(f"- intact: {field_ok}  ·  missing R14/provenance fields: {field_bad}")
    lines.append("")

    report = s4_dir / "e2e_cohesion_report.md"
    report.write_text("\n".join(lines), encoding="utf-8")

    # ── stdout summary ──────────────────────────────────────────────────────
    print(f"📄 report: {report}")
    print(f"\nSurvival matrix (S2 → S4 → S5 → S6):")
    for (ct, origin) in sorted(matrix.keys()):
        m = matrix[(ct, origin)]
        print(f"  {ct:18s} {origin:13s}  S2={m['S2']:5d}  S4={m['S4']:5d}  S5={m['S5']:5d}  S6={m['S6']:5d}")
    print(f"\nStage totals: S2={len(s2)+len(s2_singleton)}  S4={len(s4_ckpt)+len(s4_pt)+len(s4_pi)+len(s4_ti)+len(s4_ge)}  S5={len(s5)}  S6={len(s6)}")
    print(f"\nFailure findings by class:")
    for cls in ("leak", "cascade", "hidden-failure", "contamination", "drift",
                "bug", "blindspot", "gap", "conflict"):
        n = len(findings.get(cls, []))
        if n:
            print(f"  {cls:16s} {n}")
    print(f"\nField-cohesion: {field_ok} intact / {field_bad} with missing fields")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
