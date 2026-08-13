"""pipeline/recall_measure.py — Golden-set recall measurement (D2307).

Authority: D2165 (principle-recall benchmark), D2307 (recall measurement blindspot).
Constitution: C12 (no hardcoding), C17 (type hints), C18 (docstrings).

Closes the audit blindspot: "Recall measurement" was never computed end-to-end.
This module measures how many of the 73 golden-set principles the pipeline
actually recovers in a real S2 (or downstream) run — the yield metric that
v2.0 lacked (14 FBs / 852 books was never measured against ground truth).

Matching is name-based (normalized token overlap) because:
  - FB names are short, distinctive, and human-adjudicated in the golden set.
  - Evidence passages in golden are verbatim, but S2 output paraphrases them
    (D2227) — so evidence matching would under-count recall for a reason that
    is not a true miss.
  - Name overlap is deterministic (R7: temp=0.0) and cheap (no LLM call).

Usage:
    python3 pipeline/recall_measure.py --golden config/golden/stage2_fewshot_convergent.yaml \
        --output stage2_extract/latest/output.jsonl
    python3 pipeline/recall_measure.py --golden ... --output ... --tier GOLD-A --verbose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GOLDEN = PROJECT_ROOT / "config" / "golden" / "stage2_fewshot_convergent.yaml"

# D2307: name-match threshold — config-driven default; overridable via CLI (C12).
with open(PROJECT_ROOT / "config" / "pipeline_config.yaml") as _rcf:
    _RECALL_CFG = yaml.safe_load(_rcf) or {}
DEFAULT_MATCH_THRESHOLD: float = float(_RECALL_CFG.get("recall", {}).get("match_threshold", 0.55))


def norm_text(text: str) -> str:
    """Normalize text for fuzzy comparison: lowercase, strip punctuation/whitespace."""
    text = str(text or "")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def token_overlap(a: str, b: str) -> float:
    """Jaccard token overlap between two strings (0.0–1.0).

    Used for name matching — a short, distinctive FB name like
    "Asymmetric Dominance Decoy" should match "Decoy Effect" only weakly
    (~0.2), but match "Asymmetric Dominance Effect" strongly (~0.67).
    """
    ta = set(norm_text(a).split())
    tb = set(norm_text(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def load_golden(golden_path: Path) -> list[dict]:
    """Load golden examples with their expected FB name(s).

    Returns:
        List of dicts: {id, tier, should_extract, names: [str, ...]}.
        For 1:N examples, `names` holds multiple expected FB names.
    """
    with open(golden_path) as f:
        data = yaml.safe_load(f)

    out: list[dict] = []
    for ex in data.get("examples", []):
        ef = ex.get("expected_fb", {})
        fbs: list[dict] = ef if isinstance(ef, list) else [ef]
        names: list[str] = []
        for fb in fbs:
            if isinstance(fb, dict) and fb.get("name"):
                names.append(fb["name"])
        out.append({
            "id": ex.get("id", "?"),
            "tier": ex.get("tier", "GOLD-A"),
            "should_extract": bool(ex.get("should_extract", False)),
            "names": names,
        })
    return out


def load_pipeline_output(output_path: Path) -> list[dict]:
    """Load pipeline FB records (JSONL) or a single JSON list."""
    if not output_path.exists():
        return []

    if output_path.suffix == ".jsonl":
        records: list[dict] = []
        with open(output_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records

    with open(output_path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Some stage outputs are {run_id: [...]} or {"fbs": [...]}
        for key in ("fbs", "results", "output"):
            if isinstance(data.get(key), list):
                return data[key]
        return []
    return []


def compute_recall(
    golden: list[dict],
    pipeline_fbs: list[dict],
    *,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
    tier: str | None = None,
) -> dict[str, Any]:
    """Compute recall of golden principles against pipeline output.

    Recall = (golden positives whose name matches ≥1 pipeline FB) / (golden positives).

    Args:
        golden: List from load_golden().
        pipeline_fbs: List of FB dicts from pipeline output (each must have `name`).
        threshold: Name-overlap threshold for a "match" (0.0–1.0).
        tier: If set, restrict recall to one tier (GOLD-A / GOLD-B / CHALLENGE).

    Returns:
        Dict with recall, precision, f1, counts, and per-tier breakdown.
    """
    pipeline_names: list[str] = [fb.get("name", "") for fb in pipeline_fbs if fb.get("name")]

    if tier:
        golden = [g for g in golden if g.get("tier") == tier]

    positives = [g for g in golden if g.get("should_extract")]
    negatives = [g for g in golden if not g.get("should_extract")]

    tp = 0          # golden positive recovered
    fn = 0          # golden positive missed
    matched_ids: list[str] = []
    missed_ids: list[str] = []

    for g in positives:
        best = 0.0
        for pname in pipeline_names:
            for gname in g["names"]:
                best = max(best, token_overlap(gname, pname))
        if best >= threshold:
            tp += 1
            matched_ids.append(g["id"])
        else:
            fn += 1
            missed_ids.append(g["id"])

    # Precision: of pipeline FBs, how many match a golden positive.
    # (A conservative floor — a pipeline FB counts as a true positive only if
    # it matches a golden name. This is approximate; see module docstring.)
    matched_pipeline = 0
    for pname in pipeline_names:
        for g in positives:
            for gname in g["names"]:
                if token_overlap(gname, pname) >= threshold:
                    matched_pipeline += 1
                    break
            else:
                continue
            break

    total_pipeline = len(pipeline_names)
    precision = (matched_pipeline / total_pipeline) if total_pipeline else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    # Per-tier recall breakdown (for D2286 tier-aware evaluation)
    tier_breakdown: dict[str, dict[str, Any]] = {}
    for t in ("GOLD-A", "GOLD-B", "CHALLENGE"):
        subset = [g for g in positives if g.get("tier") == t]
        if not subset:
            continue
        tier_tp = 0
        for g in subset:
            best = 0.0
            for pname in pipeline_names:
                for gname in g["names"]:
                    best = max(best, token_overlap(gname, pname))
            if best >= threshold:
                tier_tp += 1
        tier_breakdown[t] = {
            "total": len(subset),
            "recovered": tier_tp,
            "recall": tier_tp / len(subset),
        }

    return {
        "threshold": threshold,
        "tier_filter": tier,
        "golden_positives": tp + fn,
        "golden_negatives": len(negatives),
        "pipeline_fbs": total_pipeline,
        "true_positive": tp,
        "false_negative": fn,
        "matched_pipeline": matched_pipeline,
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "f1": round(f1, 4),
        "matched_ids": matched_ids,
        "missed_ids": missed_ids,
        "tier_breakdown": tier_breakdown,
    }


def print_report(result: dict[str, Any], verbose: bool = False) -> None:
    """Print a human-readable recall report."""
    print("\n── Recall Measurement (D2307) ──")
    print(f"  Threshold: {result['threshold']}  |  Tier filter: {result.get('tier_filter') or 'ALL'}")
    print(f"  Golden positives:  {result['golden_positives']}")
    print(f"  Pipeline FBs:      {result['pipeline_fbs']}")
    print("  ────────────────────────────────")
    print(f"  RECALL:    {result['recall']:.3f}  ({result['true_positive']}/{result['golden_positives']} recovered)")
    print(f"  PRECISION: {result['precision']:.3f}  ({result['matched_pipeline']}/{result['pipeline_fbs']} pipeline FBs matched)")
    print(f"  F1:        {result['f1']:.3f}")

    print("\n  Per-tier recall (D2286):")
    for t, b in result["tier_breakdown"].items():
        print(f"    {t:10s}: {b['recall']:.3f}  ({b['recovered']}/{b['total']})")

    if verbose and result["missed_ids"]:
        print(f"\n  Missed golden IDs ({len(result['missed_ids'])}):")
        for mid in result["missed_ids"]:
            print(f"    - {mid}")


def main() -> None:
    """CLI entry point for recall measurement."""
    parser = argparse.ArgumentParser(
        description="Measure golden-set recall of pipeline output (D2307)"
    )
    parser.add_argument("--golden", type=str, default=str(DEFAULT_GOLDEN),
                        help=f"Golden set YAML (default: {DEFAULT_GOLDEN})")
    parser.add_argument("--output", type=str, required=True,
                        help="Pipeline output JSONL/JSON (e.g. stage2_extract/latest/output.jsonl)")
    parser.add_argument("--tier", type=str, default=None, choices=["GOLD-A", "GOLD-B", "CHALLENGE"],
                        help="Restrict recall to one tier")
    parser.add_argument("--threshold", type=float, default=DEFAULT_MATCH_THRESHOLD,
                        help=f"Name-overlap match threshold (default: {DEFAULT_MATCH_THRESHOLD})")
    parser.add_argument("--verbose", action="store_true", help="List missed golden IDs")
    args = parser.parse_args()

    golden = load_golden(Path(args.golden))
    pipeline_fbs = load_pipeline_output(Path(args.output))

    if not golden:
        print(f"❌ No golden examples loaded from {args.golden}")
        sys.exit(1)
    if not pipeline_fbs:
        print(f"⚠️  No pipeline FBs loaded from {args.output} — recall = 0.0")

    result = compute_recall(
        golden, pipeline_fbs, threshold=args.threshold, tier=args.tier
    )
    print_report(result, verbose=args.verbose)


if __name__ == "__main__":
    main()
