#!/usr/bin/env python3
"""e2e_proof.py — controlled live S2→S4→S5 run on a representative sample.

Proves (or disproves) that the CURRENT pipeline code carries every object type
through S2→S4→S5 with intact metadata (R14 stamps), segments, and properties —
and exposes exactly where non-principle types dead-end (S5 verifies principles only).

Sample: 1 record per (content_type × origin) where it exists in S2 t11.
Stages a fresh S2 checkpoint, runs S4 (live OMLX classification), runs S5 (DeBERTa NLI).
Traces each fb_id S2→S4→S5 and renders an examinable Markdown report.

Usage: python3 scripts/e2e_proof.py [--run-id e2e_proof]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

VALID_CT = ("principle", "process_template", "process_instance", "tool_instruction", "growth_edge")


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
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


def _origin(r: dict) -> str:
    if r.get("is_singleton_fb") or r.get("is_singleton"):
        return "singleton"
    if r.get("is_convergent"):
        return "convergent"
    return "single_source"


def _key(r: dict) -> str:
    return r.get("fb_id") or r.get("principle_id") or ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="e2e_proof")
    args = ap.parse_args()
    rid = args.run_id

    import pipeline.pipeline_paths as pp
    import pipeline.stage4_merge as s4m

    # ── 1. Pick representatives ─────────────────────────────────────────────
    s2_all = _load_jsonl(pp.S2_DIR / "t11" / "checkpoint.jsonl")
    picks: dict[tuple[str, str], dict] = {}
    for r in s2_all:
        ct = r.get("content_type")
        if ct not in VALID_CT:
            continue
        o = _origin(r)
        picks.setdefault((ct, o), r)

    # singleton origin: S2 t11 has none (extraction never completed). Pull from
    # the smoke singleton output if available, else note the gap.
    singleton_rows = _load_jsonl(pp.S2_DIR / "smoke_matrix_5x3b" / "singleton_fbs.jsonl")
    for r in singleton_rows:
        ct = r.get("content_type")
        if ct in VALID_CT:
            picks.setdefault((ct, "singleton"), r)

    # ── 2. Stage fresh S2 checkpoint ────────────────────────────────────────
    s2_dir = pp.S2_DIR / rid
    s4_dir = pp.S4_DIR / rid
    s5_dir = pp.S5_DIR / rid
    s2_dir.mkdir(parents=True, exist_ok=True)
    s4_dir.mkdir(parents=True, exist_ok=True)
    s5_dir.mkdir(parents=True, exist_ok=True)

    sample = list(picks.values())
    ckpt = s2_dir / "checkpoint.jsonl"
    ckpt.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in sample), encoding="utf-8")
    print(f"📂 Staged {len(sample)} representative S2 records → {ckpt}")

    # ── 3. Point S4 at our staged S2 + fresh S4 output ─────────────────────
    s4m.STAGE2_CHECKPOINT = ckpt
    s4m.STAGE4_CHECKPOINT = s4_dir / "checkpoint.jsonl"
    s4m.CHECKPOINT_DIR = s4_dir
    # sidecar outputs derive from STAGE4_CHECKPOINT.parent — they are set below
    # via module attrs (S4_*_OUTPUT are filenames, resolved against parent).
    s4m.S4_GE_OUTPUT = "growth_edges.jsonl"
    s4m.S4_PT_OUTPUT = "process_templates.jsonl"
    s4m.S4_PI_OUTPUT = "process_instances.jsonl"
    s4m.S4_TI_OUTPUT = "tool_instructions.jsonl"

    # ── 4. Run S4 (live OMLX classification) ────────────────────────────────
    print("\n🧩 === S4 MERGE (live) ===\n")
    s4m.run_stage4()

    # ── 5. Point S5 at our fresh S4 + run (DeBERTa NLI) ─────────────────────
    import pipeline.stage5_verify as s5v
    s5v.STAGE4_CHECKPOINT = s4_dir / "checkpoint.jsonl"
    s5v.STAGE4_5_CHECKPOINT = s4_dir / "checkpoint_enriched.jsonl"  # won't exist
    s5v.STAGE5_CHECKPOINT = s5_dir / "checkpoint.jsonl"
    s5v.CHECKPOINT_DIR = s5_dir
    print("\n🧩 === S5 VERIFY (live) ===\n")
    try:
        s5v.run_stage5()
    except SystemExit:
        pass

    # ── 6. Trace each representative S2→S4→S5 ───────────────────────────────
    s4_ckpt = _load_jsonl(s4_dir / "checkpoint.jsonl")
    s4_side = (_load_jsonl(s4_dir / "process_templates.jsonl")
               + _load_jsonl(s4_dir / "process_instances.jsonl")
               + _load_jsonl(s4_dir / "tool_instructions.jsonl")
               + _load_jsonl(s4_dir / "growth_edges.jsonl"))
    s5_rows = _load_jsonl(s5_dir / "checkpoint.jsonl")

    s4_idx = {_key(r): r for r in s4_ckpt + s4_side}
    s5_idx = {_key(r): r for r in s5_rows}

    R14 = ("schema_version", "gen_model", "pipeline_commit")
    PROV = ("source_books", "source_segments", "source_authors", "citation")

    lines = [f"# E2E Proof — S2→S4→S5 (run_id `{rid}`)", "",
             f"> sample = {len(sample)} representatives · `{s4_dir.resolve()}`", "",
             "| content_type | origin | S2 | S4 | S4 fields intact | S5 | S5 status |", 
             "|---|---|---|---|---|---|---|"]
    for (ct, o) in sorted(picks.keys()):
        r = picks[(ct, o)]
        k = _key(r)
        in_s4 = k in s4_idx
        in_s5 = k in s5_idx
        # field integrity at S4
        r4 = s4_idx.get(k)
        if r4 is None:
            integrity = "—"
        else:
            missing = [f for f in R14 + PROV if not r4.get(f)]
            integrity = "✅ intact" if not missing else f"❌ missing {missing}"
        status = s5_idx[k].get("status", "?") if in_s5 else "—"
        lines.append(f"| {ct} | {o} | ✅ | {'✅' if in_s4 else '❌ DROPPED'} | {integrity} | {'✅' if in_s5 else '—'} | {status} |")
    lines.append("")

    lines.append("## Field-cohesion summary (S4 survivors)")
    lines.append("")
    intact = sum(1 for r in s4_ckpt if all(r.get(f) for f in R14 + PROV))
    lines.append(f"- S4 principles with intact R14 stamps + provenance: **{intact}/{len(s4_ckpt)}**")
    lines.append(f"- S4 sidecars routed: {len(s4_side)} (PT/PI/TI/GE) — **S5 does NOT verify these** (principle-only)")
    lines.append(f"- S5 verified principles: {len(s5_rows)}")
    lines.append("")

    report = s4_dir / "e2e_proof_report.md"
    report.write_text("\n".join(lines), encoding="utf-8")

    print("\n" + "\n".join(lines))
    print(f"\n📄 report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
