#!/usr/bin/env python3
"""Live smoke: 5 content types × 3 origins matrix (D2460).

Exercises GE/FB/TI/PT/PI across convergent, single-source, and singleton
clusters, runs S4 classification live on the combined batch, and renders a
human-examinable Markdown report (`visual.md`) so a reviewer can verify against
config/content_types.yaml that:

  * metadata (R14 stamps + provenance) is intact
  * segments (source_segments / evidence_passages) are intact
  * properties (type-specific s2 body fields) are intact
  * classification (content_type / extraction_type / domains / discipline /
    depth / evidence) is ontologically + pragmatically accurate

Structural reality (BUG-166): convergent clusters produce ONLY `principle` (FB)
— non-principle types are 99.9% single-source by construction. So the honest
matrix is:
    convergent      → FB
    single-source   → FB, PT, PI, TI, GE
    singleton       → FB, PT, PI, TI, GE

Usage:
    python3 scripts/smoke_matrix_5x3.py [--n-singletons 20] [--run-id smoke_matrix_5x3]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import pipeline_paths as pp  # noqa: E402

VALID_CT = {"principle", "process_template", "process_instance", "growth_edge", "tool_instruction"}
VALID_ET = {"causal_mechanism", "descriptive_model", "normative_heuristic", "empirical_pattern"}


def _load_jsonl(path: Path) -> list[dict]:
    txt = path.read_text(encoding="utf-8")
    try:
        return [json.loads(l) for l in txt.splitlines() if l.strip()]
    except json.JSONDecodeError:
        obj = json.loads(txt)
        return obj if isinstance(obj, list) else [obj]


def pick_representatives() -> dict[str, dict]:
    """One representative per (origin, content_type) from the real S2 checkpoint."""
    s2 = pp.S2_DIR / "t11" / "checkpoint.jsonl"
    rows = _load_jsonl(s2)
    picks: dict[str, dict] = {}
    for r in rows:
        ct = r.get("content_type")
        if ct not in VALID_CT:
            continue
        origin = "convergent" if r.get("is_convergent") else "single_source"
        key = f"{origin}:{ct}"
        if key not in picks:
            picks[key] = r
    return picks


def stage_s2_checkpoint(run_id: str, picks: dict[str, dict]) -> Path:
    """Write representative convergent + single-source FBs into a fresh S2 checkpoint."""
    s2_dir = pp.S2_DIR / run_id
    s2_dir.mkdir(parents=True, exist_ok=True)
    ckpt = s2_dir / "checkpoint.jsonl"
    rows = list(picks.values())
    ckpt.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"📂 Staged {len(rows)} S2 records (convergent + single-source) → {ckpt}")
    return ckpt


def stage_singletons(run_id: str, n: int) -> Path:
    """Spread-sample n EXTRACT singletons (from the REAL singletons.jsonl which
    carries `segment_ids`) into a fresh S1.5 dir, gated by the prefilter verdicts.

    NOTE: singletons.prefiltered.jsonl is verdict-only (no segment_ids) — the S2
    singleton pass reads `segment_ids` from singletons.jsonl and `verdict` from the
    prefiltered file. Staging from the prefiltered file alone yields 0 viable.
    """
    real_src = pp.S15_DIR / "t11" / "singletons.jsonl"
    pref_src = pp.S15_DIR / "t11" / "singletons.prefiltered.jsonl"
    real = _load_jsonl(real_src)
    pref = {r["cluster_id"]: r for r in _load_jsonl(pref_src) if r.get("verdict") == "EXTRACT"}

    # keep only EXTRACT singletons that also have segment_ids in the real file
    extract = [r for r in real if r.get("cluster_id") in pref and r.get("segment_ids")]
    # spread-sample across the EXTRACT list for maximum topical diversity
    idxs = {int(i * (len(extract) - 1) / max(n - 1, 1)) for i in range(n)} if len(extract) >= n else set(range(len(extract)))
    idxs = sorted(idxs)
    sample = [extract[i] for i in idxs]

    out_dir = pp.S15_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "singletons.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in sample), encoding="utf-8")
    # matching prefiltered file (EXTRACT verdicts only) so the gated path passes
    pref_out = out_dir / "singletons.prefiltered.jsonl"
    pref_out.write_text("".join(json.dumps(pref[r["cluster_id"]], ensure_ascii=False) + "\n" for r in sample), encoding="utf-8")
    print(f"📂 Staged {len(sample)} EXTRACT singletons (with segment_ids) → {out}")
    return out


def patch_paths(run_id: str) -> None:
    """Point pipeline_paths + stage4_merge at the per-run smoke dirs."""
    s2_dir = pp.S2_DIR / run_id
    s4_dir = pp.S4_DIR / run_id
    s2_dir.mkdir(parents=True, exist_ok=True)
    s4_dir.mkdir(parents=True, exist_ok=True)

    pp.STAGE1_5_SINGLETONS = pp.S15_DIR / run_id / "singletons.jsonl"
    pp.STAGE1_5_SINGLETONS_PREFILTERED = pp.S15_DIR / run_id / "singletons.prefiltered.jsonl"
    pp.STAGE2_SINGLETON_OUTPUT = s2_dir / "singleton_fbs.jsonl"
    pp.S2_SINGLETON_PREFILTER_ENABLED = True

    import pipeline.stage4_merge as s4m
    s4m.STAGE2_CHECKPOINT = s2_dir / "checkpoint.jsonl"
    s4m.STAGE4_CHECKPOINT = s4_dir / "checkpoint.jsonl"
    s4m.CHECKPOINT_DIR = s4_dir


# ── Rendering ─────────────────────────────────────────────────────────────
_SHARED = ("definition", "mechanism", "boundary", "consequence")
_TYPE_BODY = {
    "principle": ("application", "failure_mode", "elaboration", "jargon"),
    "process_template": ("trigger", "prerequisite", "steps", "done_condition", "failure_mode"),
    "process_instance": ("instance_text", "actors", "outcome_metric", "outcome_qualitative", "domain_context"),
    "tool_instruction": ("tool_name", "platform", "description", "syntax", "parameters", "output", "example", "caveats"),
    "growth_edge": ("body", "category", "actionable", "status", "priority"),
}
_META = ("schema_version", "gen_model", "pipeline_commit", "pipeline_run_id", "created_at")
_PROV = ("source_books", "source_clusters", "source_segments", "evidence_passages", "citation", "source_authors", "source_diversity", "primary_source")
_CLS = ("content_type", "extraction_type", "is_summary", "domains", "domains_raw", "discipline", "discipline_raw", "depth", "evidence")
_OTHER = ("keywords", "fb_version", "usage_count", "feedback_score", "feedback_count", "classification_status", "taxonomy_match_method")


def _s(v):
    if v is None:
        return "∅"
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return str(v).strip() or "∅"


def _origin_of(r: dict) -> str:
    # S4 sets `origin` authoritatively on principles; sidecars carry origin=None
    # but DO carry is_singleton_fb/is_convergent. Prefer `origin` when present.
    origin = r.get("origin")
    if origin in ("convergent", "single_source", "singleton"):
        return origin
    if r.get("is_singleton_fb") or r.get("is_singleton"):
        return "singleton"
    if r.get("is_convergent"):
        return "convergent"
    return "single_source"


def render(recs: list[dict], origin: str) -> list[str]:
    lines: list[str] = []
    for i, r in enumerate(recs, 1):
        ct = r.get("content_type", "?")
        et = r.get("extraction_type", "?")
        lines.append(f"### {origin} · {ct}")
        lines.append("")
        lines.append(f"- **name:** {_s(r.get('name'))}")
        lines.append(f"- **content_type:** `{ct}`  ·  **extraction_type:** `{et}`  ·  **is_summary:** {_s(r.get('is_summary'))}")
        lines.append(f"- **classification:** depth=`{_s(r.get('depth'))}`  ·  discipline=`{_s(r.get('discipline'))}` (raw `{_s(r.get('discipline_raw'))}`)  ·  domains={_s(r.get('domains'))} (raw {_s(r.get('domains_raw'))})  ·  evidence=`{_s(r.get('evidence'))}`  ·  status=`{_s(r.get('classification_status'))}`")
        lines.append("")
        for f in _SHARED + _TYPE_BODY.get(ct, ()):
            v = r.get(f)
            if v not in (None, "", [], {}):
                lines.append(f"- **{f}:** {_s(v)}")
        lines.append("")
        lines.append("- **metadata (R14 stamps):** " + "  ·  ".join(f"`{k}`={_s(r.get(k))}" for k in _META if r.get(k)))
        lines.append("- **provenance:** " + "  ·  ".join(f"`{k}`={_s(r.get(k))}" for k in _PROV if r.get(k) not in (None, "", [])))
        lines.append("- **other:** " + "  ·  ".join(f"`{k}`={_s(r.get(k))}" for k in _OTHER if r.get(k) not in (None, "", [])))
        lines.append("")
        lines.append("---")
        lines.append("")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-singletons", type=int, default=20)
    ap.add_argument("--run-id", default="smoke_matrix_5x3")
    ap.add_argument("--skip-singletons", action="store_true")
    args = ap.parse_args()

    run_id = args.run_id
    picks = pick_representatives()
    stage_s2_checkpoint(run_id, picks)

    if not args.skip_singletons:
        stage_singletons(run_id, args.n_singletons)

    patch_paths(run_id)

    # ── S2 singleton extraction (live) ──
    singleton_fbs: list[dict] = []
    if not args.skip_singletons:
        from pipeline.stage2_extract import process_singletons
        print("\n🧩 === S2 SINGLETON EXTRACTION (live OMLX) ===\n")
        singleton_fbs, extracted, nulls = process_singletons(provider="omlx", gate_enabled=True)
        print(f"\n🧩 S2 singleton pass: {extracted} FBs, {nulls} NULLs")

    # ── S4 (live) ──
    from pipeline.stage4_merge import run_stage4
    print("\n🧩 === S4 MERGE (live) ===\n")
    run_stage4()

    # ── Collect all S4 outputs ──
    s4_dir = pp.S4_DIR / run_id
    checkpoint_fbs = _load_jsonl(s4_dir / "checkpoint.jsonl") if (s4_dir / "checkpoint.jsonl").exists() else []
    sidecars: dict[str, list[dict]] = {}
    for fn in ("process_templates.jsonl", "process_instances.jsonl", "growth_edges.jsonl", "tool_instructions.jsonl"):
        sp = s4_dir / fn
        sidecars[fn] = _load_jsonl(sp) if sp.exists() else []

    # ── Render visual ──
    out: list[str] = [
        f"# Smoke Matrix 5×3 — Visual Examination",
        "",
        f"> `{s4_dir.resolve()}`  ·  run_id=`{run_id}`",
        "",
        "## Matrix coverage",
        "",
    ]
    # coverage table
    all_recs = checkpoint_fbs
    for recs in sidecars.values():
        all_recs.extend(recs)
    by = Counter()
    for r in all_recs:
        by[(r.get("content_type", "?"), _origin_of(r))] += 1
    out.append("| content_type | convergent | single_source | singleton |")
    out.append("|---|---|---|---|")
    for ct in ("principle", "process_template", "process_instance", "tool_instruction", "growth_edge"):
        out.append(f"| {ct} | {by.get((ct,'convergent'),0)} | {by.get((ct,'single_source'),0)} | {by.get((ct,'singleton'),0)} |")
    out.append("")

    # render by origin
    out.append("# Foundation Blocks (principle) — checkpoint")
    out.append("")
    # render each principle under its own origin (render() takes a single origin
    # label, so group them)
    for origin in ("convergent", "single_source", "singleton"):
        group = [r for r in checkpoint_fbs if r.get("content_type") == "principle" and _origin_of(r) == origin]
        if group:
            out.extend(render(group, origin))

    for title, fn, ct in (
        ("Process Templates", "process_templates.jsonl", "process_template"),
        ("Process Instances", "process_instances.jsonl", "process_instance"),
        ("Growth Edges", "growth_edges.jsonl", "growth_edge"),
        ("Tool Instructions", "tool_instructions.jsonl", "tool_instruction"),
    ):
        recs = sidecars[fn]
        if recs:
            out.append(f"# {title}")
            out.append("")
            for r in recs:
                out.extend(render([r], _origin_of(r)))

    visual = s4_dir / "visual.md"
    visual.write_text("\n".join(out), encoding="utf-8")
    print(f"\n📄 Visual report: {visual}")

    # ── Summary to stdout ──
    print("\n" + "=" * 70)
    print("MATRIX COVERAGE (content_type × origin)")
    print("=" * 70)
    for ct in ("principle", "process_template", "process_instance", "tool_instruction", "growth_edge"):
        print(f"  {ct:18} conv={by.get((ct,'convergent'),0)}  single={by.get((ct,'single_source'),0)}  singleton={by.get((ct,'singleton'),0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
