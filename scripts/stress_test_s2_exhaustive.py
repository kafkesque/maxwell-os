#!/usr/bin/env python3
"""stress_test_s2_exhaustive.py — exhaust ALL S2 records against content_types.yaml.

Unlike `audit_diverse_smoke.py` (which *samples* ~12 per cell), this stress test
audits EVERY record in the two real S2 corpora — singleton_fbs.final.jsonl and
checkpoint.deduped.jsonl (single-source + convergent) — bucketed by
(origin × content_type), and cross-examines each against the FULL content_types.yaml
contract:

  * S2 schema      — shared core_body (name/definition/mechanism/boundary/consequence),
                     elaboration PRINCIPLE-ONLY, per-type s2_body_fields (steps/actors/
                     parameters/outcome_metric/…), and classification labels
                     (content_type / extraction_type / is_summary / route).  [audit_s2]
  * R14 stamps     — schema_version / gen_model / pipeline_commit / pipeline_run_id /
                     created_at.                                              [audit_s4]
  * provenance     — source_books / source_segments / source_authors / citation.

It also renders a DIVERSE visual sample per cell (conforming + non-conforming) so the
reviewer can eyeball the actual objects, not just counters. Deterministic (seeded),
no LLM, no network, read-only.

Output (new folder — never overwrites pipeline output, R-D410):
  stage4_merge/stress_s2_exhaustive/
    conformance_report.md   — per-cell exhaustive stats + gap-type counts
    visual.md               — rendered samples for human examination
    samples/*.jsonl         — the sampled records backing visual.md

Usage:
    python3 scripts/stress_test_s2_exhaustive.py [--samples-per-cell 5] [--seed 42]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from audit_content_type_contract import audit_s2, audit_s4, _load_ontology  # noqa: E402

SINGLETON = REPO_ROOT / "knowledge pipeline" / "stage2_extract" / "t11" / "singleton_fbs.final.jsonl"
DEDUP = REPO_ROOT / "knowledge pipeline" / "stage2_extract" / "t11" / "checkpoint.deduped.jsonl"
OUT_DIR = REPO_ROOT / "knowledge pipeline" / "stage4_merge" / "stress_s2_exhaustive"

CONTENT_TYPES = ("principle", "process_template", "process_instance", "tool_instruction", "growth_edge")
ORIGINS = ("convergent", "single_source", "singleton")

# per-type body fields for visual rendering (mirrors config/content_types.yaml s2_body_fields)
_SHARED = ("definition", "mechanism", "boundary", "consequence", "elaboration")
_TYPE_BODY = {
    "principle": (),
    "process_template": ("trigger", "prerequisite", "steps", "done_condition", "failure_mode"),
    "process_instance": ("instance_text", "actors", "outcome_metric", "outcome_qualitative", "domain_context"),
    "tool_instruction": ("tool_name", "platform", "description", "syntax", "parameters", "output", "example", "caveats"),
    "growth_edge": ("body", "category", "actionable", "status", "priority"),
}


def _load_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _origin_of(rec: dict) -> str:
    if rec.get("is_singleton_fb") is True:
        return "singleton"
    if rec.get("is_convergent") is True:
        return "convergent"
    return "single_source"


def _s(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return str(v).strip()


def _render_record(idx: int, rec: dict, origin: str, tag: str, issues: list[str]) -> list[str]:
    lines = [f"### {idx}. {_s(rec.get('name')) or '(unnamed)'}  `[{origin}]` `[{tag}]`"]
    ct = _s(rec.get("content_type"))
    et = _s(rec.get("extraction_type"))
    lines.append("")
    lines.append(f"- **content_type:** {ct}  ·  **extraction_type:** {et}  ·  **is_summary:** {_s(rec.get('is_summary'))}")
    lines.append(f"- **gen_model:** {_s(rec.get('gen_model'))}  ·  **schema:** {_s(rec.get('schema_version'))}  ·  **commit:** {_s(rec.get('pipeline_commit'))}")
    lines.append(f"- **sources:** {len(rec.get('source_books') or [])} books / {len(rec.get('source_ids') or [])} ids")
    if issues:
        lines.append(f"- **⚠️ issues:** {'; '.join(i.replace('DEFERRED(enum) ', '') for i in issues)}")
    lines.append("")
    for f in _SHARED + _TYPE_BODY.get(ct, ()):
        v = _s(rec.get(f))
        if v:
            lines.append(f"**{f}:** {v}")
            lines.append("")
    lines.append("---")
    lines.append("")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--samples-per-cell", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    onto = _load_ontology()
    rng = random.Random(args.seed)

    singleton = _load_jsonl(SINGLETON)
    dedup = _load_jsonl(DEDUP)

    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for rec in singleton + dedup:
        ct = rec.get("content_type") or "principle"
        buckets[(_origin_of(rec), ct)].append(rec)

    report: list[str] = []
    visual: list[str] = ["# S2 Exhaustive Stress Test — Visual Samples", "",
                         f"> {len(singleton)} singleton + {len(dedup)} single-source/convergent records, "
                         f"bucketed by (origin × content_type), audited against content_types.yaml.", ""]
    samples_dir = OUT_DIR / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    total_ok = True
    grand_total = 0
    grand_gaps = Counter()

    for origin in ORIGINS:
        for ct in CONTENT_TYPES:
            pool = buckets.get((origin, ct), [])
            if not pool:
                continue
            grand_total += len(pool)
            cell_ok = 0
            s2_gaps: Counter = Counter()
            stamp_gaps: Counter = Counter()
            prov_gaps: Counter = Counter()
            conforming: list[dict] = []
            nonconforming: list[tuple[dict, list[str]]] = []

            for rec in pool:
                issues: list[str] = []
                audit_s2(rec, ct, onto, issues)

                # R14 stamps + provenance — S2-appropriate check (NOT audit_s4, which
                # assumes S4-merged output and requires plural `source_clusters` that S2
                # single-origin records legitimately emit as singular `source_cluster`).
                stamp_issues: list[str] = []
                for f in onto.get("metadata", {}).get("stamps", []):
                    v = rec.get(f)
                    if v is None or (isinstance(v, str) and not v.strip()):
                        stamp_issues.append(f"missing/empty stamp:{f}")
                prov_issues: list[str] = []
                for f in ("source_books", "source_segments", "source_authors", "citation"):
                    if f not in rec:
                        prov_issues.append(f"missing provenance:{f}")
                if "source_cluster" not in rec and "source_clusters" not in rec:
                    prov_issues.append("missing provenance:source_cluster(s)")
                if ct == "principle":
                    for f in ("source_diversity", "primary_source"):
                        if f not in rec:
                            prov_issues.append(f"missing provenance:{f}")

                if issues:
                    for i in issues:
                        s2_gaps[i] += 1
                    nonconforming.append((rec, issues))
                elif stamp_issues or prov_issues:
                    all_iss = stamp_issues + prov_issues
                    nonconforming.append((rec, all_iss))
                    for i in stamp_issues:
                        stamp_gaps[i] += 1
                    for i in prov_issues:
                        prov_gaps[i] += 1
                else:
                    cell_ok += 1
                    conforming.append(rec)

            hard_gaps = sum(s2_gaps.values()) + sum(stamp_gaps.values()) + sum(prov_gaps.values())
            if hard_gaps:
                total_ok = False
                for i, n in s2_gaps.items():
                    grand_gaps[i] += n
                for i, n in stamp_gaps.items():
                    grand_gaps[i] += n
                for i, n in prov_gaps.items():
                    grand_gaps[i] += n

            report.append(f"## {origin} × {ct}  —  {len(pool)} records, {cell_ok} conform, {hard_gaps} gaps")
            if s2_gaps:
                for i, n in s2_gaps.most_common():
                    report.append(f"  - {n:>4d}  {i}")
            if stamp_gaps:
                for i, n in stamp_gaps.most_common():
                    report.append(f"  - {n:>4d}  {i}")
            if prov_gaps:
                for i, n in prov_gaps.most_common():
                    report.append(f"  - {n:>4d}  {i}")

            # Visual samples: balance conforming + non-conforming.
            k = args.samples_per_cell
            rng.shuffle(conforming)
            sample = conforming[:k // 2 + 1]
            for rec, issues in nonconforming[:k - len(sample)]:
                sample.append(rec)
            sample_records: list[dict] = []
            cell_visual: list[str] = [f"## {origin} × {ct} ({len(pool)} records)", ""]
            for i, rec in enumerate(sample, 1):
                tag = "OK" if rec in conforming else "GAP"
                iss = [] if tag == "OK" else next((ii for r, ii in nonconforming if r is rec), [])
                cell_visual.extend(_render_record(i, rec, origin, tag, iss))
                sample_records.append(rec)
            visual.extend(cell_visual)
            with open(samples_dir / f"{origin}__{ct}.jsonl", "w", encoding="utf-8") as f:
                f.write("\n".join(json.dumps(r, ensure_ascii=False) for r in sample_records) + "\n")

    # Summary
    report.insert(0, "# S2 Exhaustive Conformance Report\n")
    report.insert(1, f"> {grand_total} total records across all (origin × content_type) cells.\n")
    report.insert(2, f"> **{'✅ ALL CONFORM' if total_ok else '❌ GAPS FOUND'}** — "
                     f"{sum(grand_gaps.values())} total hard gaps.\n")
    if grand_gaps:
        report.insert(3, "\n## Gap-type totals (all cells)\n")
        for i, n in grand_gaps.most_common():
            report.insert(4, f"  - {n:>4d}  {i}\n")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "conformance_report.md").write_text("\n".join(report), encoding="utf-8")
    (OUT_DIR / "visual.md").write_text("\n".join(visual), encoding="utf-8")
    print(f"WROTE {OUT_DIR / 'conformance_report.md'}")
    print(f"WROTE {OUT_DIR / 'visual.md'}")
    print(f"WROTE {len(list(samples_dir.glob('*.jsonl')))} sample files in {samples_dir}")
    print(f"\n{'>'*60}\n{chr(10).join(report[:25])}")
    return 0 if total_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
