#!/usr/bin/env python3
"""Live smoke: S2 singleton extraction → S4 → render + field verification (D2448).

Samples a spread of singleton segments from S1.5, extracts them through the REAL
S2 singleton path (live OMLX, batched), runs S4 on the result, renders a visual
report, and verifies the D2448 prompt fixes + ontology conformance:

  * content_type ∈ 5 roles; extraction_type ∈ 4 forms (D2323)
  * elaboration == "" for non-principle types (BUG-173 fix)
  * parameters present (not None) for tool_instruction (BUG-169 fix)
  * S4 FB carries classification; non-principle sidecars carry type-specific body

Usage:
    python3 scripts/smoke_singleton_s2_s4.py [--n 10] [--run-id smoke_singleton_d2448]
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Patch pipeline_paths BEFORE importing pipeline modules, so the inline imports
# inside process_singletons()/load_stage2_fbs_via_clusters() resolve to smoke dirs.
from pipeline import pipeline_paths as pp  # noqa: E402
from pipeline.stage2_extract import load_segments  # noqa: E402

VALID_CONTENT_TYPES = {"principle", "process_template", "process_instance", "growth_edge", "tool_instruction"}
VALID_EXTRACTION_TYPES = {"causal_mechanism", "descriptive_model", "normative_heuristic", "empirical_pattern"}


def sample_singletons(n: int, run_id: str) -> Path:
    """Spread-sample n singletons from the real S1.5 file into the smoke dir."""
    src = pp.STAGE1_5_SINGLETONS
    lines = [l for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    total = len(lines)
    idxs = {int(i * (total - 1) / max(n - 1, 1)) for i in range(n)}
    # Prefer a couple of "technical" singletons (observed to be method/tool-like).
    for extra in (32000, 35000):
        if 0 <= extra < total:
            idxs.add(extra)
    idxs = sorted(idxs)

    out_dir = pp.S15_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    sample = out_dir / "singletons.jsonl"
    picked = [lines[i] for i in idxs]
    sample.write_text("\n".join(picked) + "\n", encoding="utf-8")
    print(f"📂 Sampled {len(picked)}/{total} singletons → {sample}")
    return sample


def patch_paths(run_id: str) -> dict[str, Path]:
    """Point only the smoke-relevant paths at a per-run dir (segments stay real)."""
    s2_dir = pp.S2_DIR / run_id
    s4_dir = pp.S4_DIR / run_id
    s2_dir.mkdir(parents=True, exist_ok=True)
    s4_dir.mkdir(parents=True, exist_ok=True)

    singleton_in = pp.S15_DIR / run_id / "singletons.jsonl"
    singleton_out = s2_dir / "singleton_fbs.jsonl"
    checkpoint_empty = s2_dir / "checkpoint.jsonl"
    s4_checkpoint = s4_dir / "checkpoint.jsonl"

    checkpoint_empty.write_text("", encoding="utf-8")  # valid empty JSONL

    # Inline-imported inside functions → patch the module attribute.
    pp.STAGE1_5_SINGLETONS = singleton_in
    pp.STAGE2_SINGLETON_OUTPUT = singleton_out

    # Module-level imported in stage4_merge → patch the consumer's attributes.
    import pipeline.stage4_merge as s4m
    s4m.STAGE2_CHECKPOINT = checkpoint_empty
    s4m.STAGE4_CHECKPOINT = s4_checkpoint
    s4m.CHECKPOINT_DIR = s4_dir

    return {"s2_singleton": singleton_out, "s4_checkpoint": s4_checkpoint, "s4_dir": s4_dir}


def verify(fb: dict, kind: str) -> list[str]:
    """Return non-conformance notes for one record (empty = clean)."""
    notes: list[str] = []
    ct = fb.get("content_type", "")
    et = fb.get("extraction_type", "")
    if ct not in VALID_CONTENT_TYPES:
        notes.append(f"content_type={ct!r} INVALID")
    if et and et not in VALID_EXTRACTION_TYPES:
        notes.append(f"extraction_type={et!r} INVALID")
    if ct in ("process_template", "process_instance", "growth_edge", "tool_instruction"):
        elab = (fb.get("elaboration") or "").strip()
        if elab:
            notes.append(f"elaboration non-empty ({len(elab)} chars) — expected '' for {ct}")
    if ct == "tool_instruction":
        if fb.get("parameters") is None:
            notes.append("parameters is None — REQUIRED for tool_instruction")
    if kind == "s4_fb":
        if not fb.get("domains"):
            notes.append("S4 FB missing domains (classification)")
        if fb.get("discipline") is None:
            notes.append("S4 FB missing discipline")
    return notes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--run-id", default="smoke_singleton_d2448")
    args = ap.parse_args()

    sample_singletons(args.n, args.run_id)
    paths = patch_paths(args.run_id)

    # ── S2 singleton extraction (live) ──
    from pipeline.stage2_extract import process_singletons
    print("\n🧩 === S2 SINGLETON EXTRACTION (live OMLX) ===\n")
    fbs, extracted, nulls = process_singletons(provider="omlx", gate_enabled=True)
    print(f"\n🧩 S2 singleton pass: {extracted} FBs, {nulls} NULLs")

    # ── S4 (live) ──
    from pipeline.stage4_merge import run_stage4
    print("\n🧩 === S4 MERGE (live) ===\n")
    run_stage4()

    # ── Render visual ──
    from scripts.render_s4_visual import main as render_main
    visual = paths["s4_dir"] / "visual.md"
    sys.argv = ["render", "--in-dir", str(paths["s4_dir"]), "--out", str(visual)]
    try:
        render_main()
    except SystemExit:
        pass

    # ── Verify S2 singleton output ──
    print("\n" + "=" * 70)
    print("VERIFICATION — S2 singleton FBs (content_type / extraction_type / elaboration / parameters)")
    print("=" * 70)
    s2_out = paths["s2_singleton"]
    if s2_out.exists():
        recs = [json.loads(l) for l in s2_out.read_text(encoding="utf-8").splitlines() if l.strip()]
        from collections import Counter
        cts = Counter(r.get("content_type", "?") for r in recs)
        print(f"   S2 singleton records: {len(recs)}  content_type: {dict(cts)}")
        for r in recs:
            notes = verify(r, "s2")
            flag = "✅" if not notes else "❌ " + "; ".join(notes)
            print(f"   [{r.get('content_type','?'):16}] {flag}  name={r.get('name','')[:40]!r}")
    else:
        print("   ❌ no S2 singleton output written")

    # ── Verify S4 output ──
    print("\n" + "=" * 70)
    print("VERIFICATION — S4 output (checkpoint FBs + sidecars)")
    print("=" * 70)
    s4_ckpt = paths["s4_checkpoint"]
    if s4_ckpt.exists():
        recs = [json.loads(l) for l in s4_ckpt.read_text(encoding="utf-8").splitlines() if l.strip()]
        from collections import Counter
        cts = Counter(r.get("content_type", "?") for r in recs)
        print(f"   S4 checkpoint FBs: {len(recs)}  content_type: {dict(cts)}")
        for r in recs:
            notes = verify(r, "s4_fb")
            flag = "✅" if not notes else "❌ " + "; ".join(notes)
            print(f"   [{r.get('content_type','?'):16}] {flag}  depth={r.get('depth','?')} discipline={r.get('discipline','?')}")
    for side in ("process_templates.jsonl", "process_instances.jsonl", "growth_edges.jsonl", "tool_instructions.jsonl"):
        sp = paths["s4_dir"] / side
        if sp.exists():
            recs = [json.loads(l) for l in sp.read_text(encoding="utf-8").splitlines() if l.strip()]
            if recs:
                print(f"   sidecar {side}: {len(recs)} record(s)")

    print(f"\n📄 Visual report: {visual}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
