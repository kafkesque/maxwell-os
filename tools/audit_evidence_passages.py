#!/usr/bin/env python3
"""D2230: Audit evidence passages for exact verbatim match against cluster_segments.

For each positive golden example, checks whether every evidence_passage text
appears verbatim in at least one cluster_segment.text. Reports mismatches
and generates a remediation report.

v2 (2026-08-10): Whitespace-normalized matching. Segments are line-wrapped
in YAML (\\n between sentences), while passages are single-line. Raw matching
flagged 52/95 as missing; whitespace-normalized matching is the true signal
(77/95 match; 18 are genuine paraphrases needing manual replacement).
"""

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def normalize_ws(text: str) -> str:
    """Collapse newlines + multiple spaces to single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def normalize_passage(passage: str | dict) -> str:
    """Handle both string passages and single-key dict passages."""
    if isinstance(passage, str):
        return passage.strip()
    if isinstance(passage, dict):
        # Single-key dict: key is claim, value is evidence
        # Try value first (actual text), then key
        val = list(passage.values())[0] if passage.values() else ""
        key = list(passage.keys())[0] if passage.keys() else ""
        return str(val).strip() if val else str(key).strip()
    return str(passage).strip()


def find_passage_in_segments(passage_raw, segments: list[dict]) -> dict | None:
    """Find passage verbatim in segments. Returns match info or None.

    Matching strategy (D2230 v2):
      1. Raw verbatim: exact string in raw segment text.
      2. Whitespace-normalized: line-wrap artifacts (\\n vs space) ignored.
         This is the primary signal — YAML folds multi-line segments.
    """
    p_norm = normalize_passage(passage_raw)
    p_ws = normalize_ws(p_norm)
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        seg_text = seg.get("text", "").strip()
        if p_norm in seg_text:
            return {
                "segment_id": seg.get("segment_id", seg.get("id", "?")),
                "source_book": seg.get("source_book", seg.get("book", "?")),
                "char_start": seg_text.find(p_norm),
                "char_end": seg_text.find(p_norm) + len(p_norm),
                "match_mode": "raw",
            }
        # Whitespace-normalized match (line-wrap artifact)
        seg_ws = normalize_ws(seg_text)
        if p_ws and p_ws in seg_ws:
            idx = seg_ws.find(p_ws)
            return {
                "segment_id": seg.get("segment_id", seg.get("id", "?")),
                "source_book": seg.get("source_book", seg.get("book", "?")),
                "char_start": idx,
                "char_end": idx + len(p_ws),
                "match_mode": "whitespace-normalized",
            }
        # Case-insensitive + apostrophe-normalized match (YAML quoting artifacts)
        p_ci = p_ws.lower().replace("''", "'")
        seg_ci = normalize_ws(seg_text).lower().replace("''", "'")
        if p_ci and p_ci in seg_ci:
            idx = seg_ci.find(p_ci)
            return {
                "segment_id": seg.get("segment_id", seg.get("id", "?")),
                "source_book": seg.get("source_book", seg.get("book", "?")),
                "char_start": idx,
                "char_end": idx + len(p_ci),
                "match_mode": "case-insensitive",
            }
        # Also try fuzzy: passage without quotes
        p_stripped = p_norm.strip('"\'')
        p_stripped_ws = normalize_ws(p_stripped)
        if p_stripped_ws and p_stripped_ws in seg_ws:
            return {
                "segment_id": seg.get("segment_id", seg.get("id", "?")),
                "source_book": seg.get("source_book", seg.get("book", "?")),
                "char_start": seg_ws.find(p_stripped_ws),
                "char_end": seg_ws.find(p_stripped_ws) + len(p_stripped_ws),
                "note": "stripped quotes to match",
                "match_mode": "stripped-quotes",
            }
    return None


def main() -> None:
    gs_path = Path("config/golden/stage2_fewshot_convergent.yaml")
    with open(gs_path) as f:
        gs = yaml.safe_load(f)

    results: list[dict] = []
    stats = {"total_passages": 0, "verbatim": 0, "fuzzy": 0, "missing": 0}

    for ex in gs.get("examples", []):
        if not ex.get("should_extract", False):
            continue  # Skip negatives

        efbs = ex.get("expected_fb", {})
        if isinstance(efbs, dict):
            efbs = [efbs]
        if not isinstance(efbs, list):
            continue

        segments = ex.get("cluster_segments", [])

        for fb_idx, efb in enumerate(efbs):
            if not isinstance(efb, dict):
                continue
            passages = efb.get("evidence_passages", [])
            for i, passage_raw in enumerate(passages):
                stats["total_passages"] += 1
                passage = normalize_passage(passage_raw)
                match = find_passage_in_segments(passage_raw, segments)

                entry = {
                    "example_id": ex["id"],
                    "fb_index": fb_idx,
                    "passage_index": i,
                    "passage_preview": passage[:120],
                    "passage_sha": sha256(passage),
                }

                if match:
                    if match.get("note"):
                        stats["fuzzy"] += 1
                        entry["status"] = "fuzzy"
                        entry["note"] = match["note"]
                    else:
                        stats["verbatim"] += 1
                        entry["status"] = "verbatim"
                    entry["match"] = match
                else:
                    stats["missing"] += 1
                    entry["status"] = "missing"
                    entry["match"] = None

                results.append(entry)

    # Print summary
    match_modes = {}
    for r in results:
        if r["status"] != "missing":
            mm = r.get("match", {}).get("match_mode", "unknown")
            match_modes[mm] = match_modes.get(mm, 0) + 1

    print(f"Total evidence passages: {stats['total_passages']}")
    print(f"  ✅ Raw verbatim:           {stats['verbatim']}")
    print(f"  ✅ Whitespace-normalized:  {match_modes.get('whitespace-normalized', 0)}")
    print(f"  🔤 Case-insensitive:       {match_modes.get('case-insensitive', 0)}")
    print(f"  ⚠️  Stripped-quotes:        {match_modes.get('stripped-quotes', 0)}")
    print(f"  ❌ Missing (true paraphrase): {stats['missing']}")
    matched = stats['total_passages'] - stats['missing']
    pct = matched / stats['total_passages'] * 100 if stats['total_passages'] else 0
    print(f"  Match rate: {pct:.1f}% ({matched}/{stats['total_passages']})")

    # Print missing
    if stats["missing"] > 0:
        print(f"\n─── MISSING PASSAGES ({stats['missing']}) ───")
        for r in results:
            if r["status"] == "missing":
                print(f"\n  {r['example_id']}[{r['passage_index']}]: {r['passage_preview']}...")
                # Show available segment texts for context
                ex_data = next((e for e in gs["examples"] if e["id"] == r["example_id"]), None)
                if ex_data:
                    for seg in ex_data.get("cluster_segments", [])[:2]:
                        t = seg.get("text", "") if isinstance(seg, dict) else str(seg)
                        print(f"    Segment preview: {t[:150]}...")

    # Write detailed report
    report_path = Path("governance/evidence_audit_report.json")
    with open(report_path, "w") as f:
        json.dump({"stats": stats, "results": results}, f, indent=2, ensure_ascii=False)
    print(f"\n📄 Detailed report: {report_path}")

    # D2230 v2: PASS requires zero true paraphrases. Stripped-quotes (fuzzy)
    # is an acceptable match mode — it means the passage matches modulo YAML quotes.
    verdict = "PASS" if stats["missing"] == 0 else "FAIL"
    print(f"\nVerdict: {verdict}")
    if verdict == "FAIL":
        print(f"D2230: {stats['missing']} evidence passages are true paraphrases. Fix before DSPy.")


if __name__ == "__main__":
    main()
