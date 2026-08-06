#!/usr/bin/env python3
"""
stage1_3_prefilter.py — Regex/heuristic pre-filter: drop structural garbage before S2.
========================================================================================
Authority: D2080, D2086 | CONSTITUTION.md §3 (runs between Stage 1 and Stage 2)

Purpose: Drop obviously non-principle segments (TOC, copyright, bibliographies,
captions, navigation) before they cost an LLM call. Zero false negatives on
principle-bearing text. Runs at ~100K segments/sec. No ML model. No dependencies.

Config: pipeline_config.yaml → stage1_3 section. All thresholds configurable.

Input:  Stage 1 checkpoint (chunks.jsonl)
Output: Filtered checkpoint → same path (in-place overwrite when --in-place)

Usage:
    python3 pipeline/stage1_3_prefilter.py            # dry-run: show what would be dropped
    python3 pipeline/stage1_3_prefilter.py --in-place  # actually filter
    python3 pipeline/stage1_3_prefilter.py --min-len 30  # custom threshold
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import (
    S13_CITE_DENSITY,
    S13_MIN_LEN,
    STAGE1_CHECKPOINT,
)

# ── Patterns configurable via pipeline_config.yaml → stage1_3 section ──
# Environment overrides: MAXWELL_S13_MIN_LEN, MAXWELL_S13_CITE_DENSITY

S13_MIN_LEN_VAL = S13_MIN_LEN
S13_CITE_DENSITY_VAL = S13_CITE_DENSITY

DROP_PATTERNS = [
    # Structural / front-matter
    (r'^(Table of Contents|Contents|Index|Bibliography|References|Acknowledgments|Appendix|Preface|Foreword|Glossary)', re.I),
    # Copyright
    (r'^Copyright\s*[©©]\s*\d{4}', re.I),
    (r'^All rights reserved', re.I),
    # Chapter/section headers
    (r'^(Chapter\s+\d+|Section\s+\d+\.\d+|Part\s+[IVX]+)', re.I),
    # Citation-only lines
    (r'^\[\d+\]\s+\w+,\s+\w+\s*[\(\.]', re.I),
    # Figure/table captions
    (r'^(Figure\s+\d+|Table\s+\d+|Exhibit\s+\d+)\s*[:\.\-—]', re.I),
    # Page numbers / headers
    (r'^\d{1,4}\s*$', re.I),
    # URLs alone
    (r'^https?://\S+$', re.I),
    # Repeating characters (decorative)
    (r'^[=\-—–\*]{10,}\s*$', re.I),
]

# D2137: config-driven boilerplate patterns (C12). Cached at module level so
# BOTH the __main__ script instance and the imported module instance get
# identical patterns (script-vs-import double-loading otherwise desyncs them).
def _load_extra_drop_patterns():
    from pathlib import Path

    import yaml as _yaml
    _cfg_path = Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"
    try:
        with open(_cfg_path) as _f:
            _cfg = _yaml.safe_load(_f)
        pats = (_cfg.get("stage1_3", {}) or {}).get("drop_patterns_extra", []) or []
        # ".*" prefix gives search semantics (re.match is anchored at pos 0)
        return [(r".*" + re.escape(p), re.I) for p in pats if p and p.strip()]
    except Exception:
        return []

_EXTRA_DROP_PATTERNS = _load_extra_drop_patterns()

# Causal/definitional/procedural markers — if NONE are present, likely not a principle.
# These are HEURISTIC — they don't guarantee a principle, just indicate possibility.
CAUSAL_MARKERS = {
    "causes", "produces", "leads to", "results in", "because", "since",
    "therefore", "thus", "consequently", "as a result", "due to",
    "the reason", "explains why", "drives", "enables", "prevents",
}
DEFINITIONAL_MARKERS = {
    "is defined as", "refers to", "means", "consists of", "is a",
    "are the", "can be understood as", "in other words", "that is",
}
PROCEDURAL_MARKERS = {
    "first", "second", "third", "then", "finally", "step",
    "to achieve", "in order to", "the process", "the method",
}


def should_drop_heuristic(text: str, min_len: int = None,
                          cite_density: float = None) -> tuple[bool, str]:
    """Determine if a segment should be dropped before reaching the LLM.

    Args:
        text: Segment text.
        min_len: Minimum character length for a potentially valid segment.
        cite_density: If > this fraction of lines are citations, drop.

    Returns:
        (drop: bool, reason: str)
    """
    text = text.strip()

    if min_len is None:
        min_len = S13_MIN_LEN_VAL
    if cite_density is None:
        cite_density = S13_CITE_DENSITY_VAL

    # Too short to contain a principle
    if len(text) < min_len:
        return True, f"too_short ({len(text)} chars < {min_len})"

    # Match against structural patterns
    for pattern, flags in _EXTRA_DROP_PATTERNS:  # D2137 boilerplate (search semantics)
        if re.match(pattern, text, flags):
            return True, f"structural_match: {pattern[:40]}"
    for pattern, flags in DROP_PATTERNS:
        if isinstance(flags, int):
            if re.match(pattern, text, flags):
                return True, f"structural_match: {pattern[:40]}"
        else:
            if re.match(pattern, text):
                return True, f"structural_match: {pattern[:40]}"

    # Citation density: if >60% of lines are citations, drop
    lines = text.split('\n')
    if len(lines) > 2:
        cite_lines = sum(1 for l in lines if re.match(r'^\s*\[\d+\]', l))
        if cite_lines / len(lines) > cite_density:
            return True, f"cite_density ({cite_lines}/{len(lines)} = {cite_lines/len(lines):.0%} > {cite_density:.0%})"

    return False, ""


def has_principle_markers(text: str) -> bool:
    """Check if text contains causal, definitional, or procedural markers.

    NOT used for dropping — used for reporting only. A segment without markers
    could still contain a principle. This is a heuristic, not a gate.
    """
    text_lower = text.lower()
    has_causal = any(m in text_lower for m in CAUSAL_MARKERS)
    has_def = any(m in text_lower for m in DEFINITIONAL_MARKERS)
    has_proc = any(m in text_lower for m in PROCEDURAL_MARKERS)
    return has_causal or has_def or has_proc


def run_prefilter(in_place: bool = False, min_len: int = None,
                  cite_density: float = None) -> dict:
    """Run regex pre-filter on Stage 1 segments.

    Args:
        in_place: If True, overwrite the original checkpoint.
        min_len: Minimum segment length.
        cite_density: Citation density threshold.

    Returns:
        Stats dict: {total, kept, dropped, reasons_map}
    """
    if not STAGE1_CHECKPOINT.exists():
        print("❌ Stage 1 checkpoint not found. Run stage1_chunk.py first.")
        sys.exit(1)

    segments = []
    with open(STAGE1_CHECKPOINT) as f:
        for line in f:
            line = line.strip()
            if line:
                segments.append(json.loads(line))

    kept = []
    dropped = []
    reasons: dict[str, int] = {}
    no_markers_kept = 0

    for seg in segments:
        text = seg.get("text", "")
        drop, reason = should_drop_heuristic(text, min_len, cite_density)

        if drop:
            dropped.append(seg)
            reasons[reason] = reasons.get(reason, 0) + 1
        else:
            kept.append(seg)
            if not has_principle_markers(text):
                no_markers_kept += 1

    drop_pct = len(dropped) / len(segments) * 100 if segments else 0

    print(f"🔍 Stage 1.3: Regex Pre-Filter — {len(segments)} segments")
    print(f"   min_len={min_len} | cite_density={cite_density:.0%}")
    print(f"{'='*60}")
    print(f"   ✅ Kept:    {len(kept):>6} ({100-drop_pct:.1f}%)")
    print(f"   🗑️  Dropped: {len(dropped):>6} ({drop_pct:.1f}%)")
    if no_markers_kept:
        print(f"   ⚠️  Kept without markers: {no_markers_kept} (may contain non-obvious principles)")
    print("\n   Drop reasons:")
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"     {reason:40s} {count:>5}")

    if in_place and dropped:
        # Backup original
        backup_path = STAGE1_CHECKPOINT.parent / f"{STAGE1_CHECKPOINT.name}.prefilter_backup"
        import shutil
        shutil.copy2(STAGE1_CHECKPOINT, backup_path)
        print(f"\n   💾 Backup: {backup_path}")

        # Write filtered
        from pipeline.io_guard import safe_write
        safe_write(
            STAGE1_CHECKPOINT,
            "\n".join(json.dumps(s, ensure_ascii=False) for s in kept) + "\n",
        )
        print(f"   ✅ Filtered checkpoint written: {STAGE1_CHECKPOINT}")

    # ── D2136: Write stage completion flag for runner resume ────────────
    from pipeline.pipeline_paths import S13_DIR, get_run_id
    flag_path = S13_DIR / get_run_id() / "checkpoint.jsonl"
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    flag_path.write_text(json.dumps({
        "completed": True,
        "total": len(segments),
        "kept": len(kept),
        "dropped": len(dropped),
    }) + "\n")

    if not in_place:
        print("\n   ℹ️  Dry run. Use --in-place to actually filter.")
        print(f"   ℹ️  This would save ~{drop_pct:.0f}% of S2 LLM calls.")

    return {
        "total": len(segments),
        "kept": len(kept),
        "dropped": len(dropped),
        "drop_pct": round(drop_pct, 1),
        "reasons": reasons,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Stage 1.3: Regex pre-filter (drop structural garbage before S2)"
    )
    parser.add_argument("--in-place", action="store_true",
                        help="Actually filter the checkpoint (default: dry-run)")
    parser.add_argument("--min-len", type=int, default=S13_MIN_LEN_VAL,
                        help=f"Minimum segment length (default: {S13_MIN_LEN_VAL})")
    parser.add_argument("--cite-density", type=float, default=S13_CITE_DENSITY_VAL,
                        help=f"Citation density threshold (default: {S13_CITE_DENSITY_VAL})")
    args = parser.parse_args()

    run_prefilter(
        in_place=args.in_place,
        min_len=args.min_len,
        cite_density=args.cite_density,
    )


if __name__ == "__main__":
    main()


# ── D2137: config-driven boilerplate drop patterns (C12) ────────────────────
# Publisher boilerplate was measured poisoning S1.5 clustering (391 segs/181 books,
# D2182: REMOVED duplicate _load_extra_drop_patterns (line 65 is authoritative).
# Maxwell R2 finding — second definition at line 274 shadowed the first.
# config/pipeline_config.yaml → stage1_3.drop_patterns_extra.

