#!/usr/bin/env python3
"""build_active_learning_sample.py — D2615 S4 active-learning stratification.

Why this exists
===============
The D2612 joint vote produced 7,966 rows; 2,729 of them are `needs_review` —
honest abstains where DeepSeek-v4-pro and Qwen3.8-27B disagreed on content_type
or depth. D2610/D2612 correctly refused to coin-flip, so no label was fabricated.

Bulk-manual-reviewing all 2,729 is the expensive anti-pattern active learning
exists to avoid (Settles). Instead this script:

  1. Stratifies the 2,729 by `(axis, disagreement_pair)` — the uncertainty
     clusters (e.g. depth `domain<->cross-domain` 827 rows; content_type
     `noise_drop<->principle` 1,148 rows).
  2. Allocates a boundary-focused sample (target_sample_size) across strata
     with a per-stratum floor (min_per_stratum) to protect the long tail,
     then distributes the remainder proportionally (largest-remainder method,
     deterministic).
  3. Emits (a) the sampled rows as a human adjudication form + JSONL ledger,
     (b) the remainder as a persistent abstain review queue, (c) a report.

Deterministic (fixed seed); vote-only (never mutates the checkpoint or DB);
C6 atomic writes via pipeline.io_guard.

Usage
=====
    python3 scripts/build_active_learning_sample.py
    python3 scripts/build_active_learning_sample.py --config config/s4_active_learning.yaml
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.io_guard import safe_write, safe_write_jsonl  # noqa: E402
from pipeline.pipeline_paths import PIPELINE_COMMIT, SCHEMA_VERSION  # noqa: E402

# ── C20 named constants ──────────────────────────────────────────────────────
ABSTAIN_VALUES: Tuple[str, ...] = ("", None, "(abstain)")
PRINCIPLE: str = "principle"
GEN_MODEL: str = "active-learning sampler (deterministic; no generation)"
PIPELINE_COMMIT_LABEL: str = PIPELINE_COMMIT or "v3.0-D2485"


def _load_checkpoint(path: Path) -> List[Dict[str, Any]]:
    """Load the vote checkpoint (one JSON object per line, fail-closed)."""
    from pipeline.io_guard import load_jsonl

    rows = load_jsonl(path, context="joint vote checkpoint")
    # Dedupe by fb_id (last-wins matches _load_checkpoint in the vote builder).
    by_id: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
    for r in rows:
        by_id[r["fb_id"]] = r
    return list(by_id.values())


def _is_abstain(v: Any) -> bool:
    return v in ABSTAIN_VALUES


def _stratum_key(axis: str, pair: Tuple[Any, Any]) -> str:
    """Human-readable, sort-stable stratum key: `depth|cross-domain<->domain`."""
    a, b = str(pair[0]), str(pair[1])
    lo, hi = sorted([a, b])
    return f"{axis}|{lo}<->{hi}"


def _voter_pair(votes: Dict[str, Any], axis: str, voters: List[str]) -> Tuple[Any, Any]:
    """Return (voter0, voter1) raw values for an axis."""
    return tuple(votes.get(v, {}).get(axis) for v in voters)


def _partition(
    rows: List[Dict[str, Any]], voters: List[str]
) -> Dict[str, List[Dict[str, Any]]]:
    """Split needs_review rows into strata keyed by (axis, disagreement-pair)."""
    strata: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        ct = r.get("content_type")
        if _is_abstain(ct):
            axis = "content_type"
            pair = _voter_pair(r["votes"], "content_type", voters)
            r = dict(r); r["_review_axis"] = axis; r["_pair"] = pair
        elif ct == PRINCIPLE and _is_abstain(r.get("depth")):
            axis = "depth"
            pair = _voter_pair(r["votes"], "depth", voters)
            r = dict(r); r["_review_axis"] = axis; r["_pair"] = pair
        else:
            continue  # not needs_review — ignore
        key = _stratum_key(axis, pair)
        strata.setdefault(key, []).append(r)
    return strata


def _allocate(
    strata: Dict[str, List[Dict[str, Any]]], total: int, floor: int
) -> Dict[str, int]:
    """Allocate `total` across strata: per-stratum floor + largest-remainder."""
    n = len(strata)
    if n == 0:
        return {}
    eff_floor = min(floor, total // n)
    counts = {k: len(v) for k, v in strata.items()}
    alloc: Dict[str, int] = {k: eff_floor for k in strata}
    remaining = total - n * eff_floor
    if remaining > 0:
        total_count = sum(counts.values())
        quotas = {k: counts[k] / total_count * remaining for k in counts}
        base = {k: int(quotas[k]) for k in quotas}
        # largest-remainder tie-break, deterministic
        order = sorted(
            quotas, key=lambda k: (quotas[k] - int(quotas[k]), k), reverse=True
        )
        leftover = remaining - sum(base.values())
        for i in range(leftover):
            base[order[i % n]] += 1
        for k in alloc:
            alloc[k] += base[k]
    # never exceed available
    return {k: min(alloc[k], counts[k]) for k in alloc}


def _sample_rows(
    strata: Dict[str, List[Dict[str, Any]]], alloc: Dict[str, int], seed: int
) -> List[Dict[str, Any]]:
    """Deterministic sample of `alloc[k]` rows per stratum."""
    rng = random.Random(seed)
    picked: List[Dict[str, Any]] = []
    for key in sorted(alloc):
        rows = sorted(strata[key], key=lambda r: r["fb_id"])
        rng.shuffle(rows)
        picked.extend(rows[: alloc[key]])
    return sorted(picked, key=lambda r: r["fb_id"])


def _sample_record(r: Dict[str, Any], voters: List[str]) -> Dict[str, Any]:
    """R14-stamped ledger record for one sampled row (human verdicts empty)."""
    axis = r["_review_axis"]
    a, b = r["_pair"]
    proposals = {voters[0]: a, voters[1]: b}
    rec: Dict[str, Any] = {
        "fb_id": r["fb_id"],
        "name": r.get("name", ""),
        "definition": r.get("definition", ""),
        "mechanism": r.get("mechanism", ""),
        "boundary": r.get("boundary", ""),
        "review_axis": axis,
        "disagreement_pair": sorted([str(a), str(b)]),
        "proposals": proposals,
        "human": {"content_type": None, "depth": None},
        "schema_version": SCHEMA_VERSION,
        "gen_model": GEN_MODEL,
        "pipeline_commit": PIPELINE_COMMIT_LABEL,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if axis == "depth":
        rec["confirmed_content_type"] = PRINCIPLE
    return rec


def _queue_record(r: Dict[str, Any], voters: List[str]) -> Dict[str, Any]:
    """Lean review-queue record (full text stays in the checkpoint/DB)."""
    axis = r["_review_axis"]
    a, b = r["_pair"]
    return {
        "fb_id": r["fb_id"],
        "name": r.get("name", ""),
        "review_axis": axis,
        "disagreement_pair": sorted([str(a), str(b)]),
        "proposals": {voters[0]: a, voters[1]: b},
        "status": "abstain_review_queue",
        "schema_version": SCHEMA_VERSION,
        "pipeline_commit": PIPELINE_COMMIT_LABEL,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _render_form(
    sample: List[Dict[str, Any]],
    strata_counts: Dict[str, int],
    voters: List[str],
) -> str:
    """Human-readable adjudication form (mirrors the Phase-0 surface)."""
    lines: List[str] = [
        "# S4 Active-Learning Adjudication Form (D2615)",
        "",
        "> **Purpose:** human-adjudicate a boundary-focused sample of the 2,729",
        "> `needs_review` rows (honest abstains where the reliable pair disagreed).",
        "> Neither proposal is authoritative — CONFIRM one, or OVERRIDE with the",
        "> correct label. The remaining rows stay abstain in the review queue.",
        "",
        f"**Sample size:** {len(sample)}  |  **Strata:** {len(strata_counts)}",
        "",
        f"**Proposal columns:** A = `{voters[0]}` · B = `{voters[1]}`",
        "",
        "**Disagreement-pair strata (row counts):**",
    ]
    for key in sorted(strata_counts):
        lines.append(f"- `{key}` — {strata_counts[key]}")
    lines.append("")
    lines.append("**Axes:** `content_type` (7-way) · `depth` (4-way, principle-only)")
    lines.append("")
    lines.append("---")
    lines.append("")

    for rec in sample:
        axis = rec["review_axis"]
        a, b = rec["disagreement_pair"]
        va, vb = rec["proposals"][voters[0]], rec["proposals"][voters[1]]
        lines.append(f"## {rec['name']}  `[{axis} · {a} ↔ {b}]`")
        lines.append("")
        lines.append(f"**Definition:** {rec['definition']}")
        lines.append("")
        if rec.get("mechanism"):
            lines.append(f"**Mechanism:** {rec['mechanism']}")
            lines.append("")
        if rec.get("boundary"):
            lines.append(f"**Boundary:** {rec['boundary']}")
            lines.append("")
        lines.append("| Axis | proposal A | proposal B | Human: CONFIRM / OVERRIDE |")
        lines.append("|---|---|---|---|")
        lines.append(
            f"| `{axis}` | `{va}` | `{vb}` | [ ] A / [ ] B / [ ] override: ____ |"
        )
        lines.append("")
        lines.append(f"`fb_id:` `{rec['fb_id']}`")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="D2615 S4 active-learning sampler")
    parser.add_argument(
        "--config",
        default=str(ROOT / "config" / "s4_active_learning.yaml"),
        help="Path to config YAML (default: config/s4_active_learning.yaml)",
    )
    args = parser.parse_args(argv)

    cfg_path = Path(args.config)
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

    checkpoint = Path(cfg["checkpoint"])
    if not checkpoint.is_absolute():
        checkpoint = ROOT / checkpoint
    voters: List[str] = list(cfg["reliable_voters"])
    target = int(cfg["target_sample_size"])
    floor = int(cfg["min_per_stratum"])
    seed = int(cfg["seed"])

    rows = _load_checkpoint(checkpoint)
    needs_review = [r for r in rows if r.get("needs_review")]

    strata = _partition(needs_review, voters)
    strata_counts = {k: len(v) for k, v in strata.items()}

    alloc = _allocate(strata, target, floor)
    sample_rows = _sample_rows(strata, alloc, seed)

    sample_records = [_sample_record(r, voters) for r in sample_rows]
    sampled_ids = {r["fb_id"] for r in sample_rows}
    queue_records = [
        _queue_record(r, voters)
        for key in sorted(strata)
        for r in sorted(strata[key], key=lambda x: x["fb_id"])
        if r["fb_id"] not in sampled_ids
    ]

    report: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "gen_model": GEN_MODEL,
        "pipeline_commit": PIPELINE_COMMIT_LABEL,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_rows": len(rows),
        "needs_review": len(needs_review),
        "strata": {k: {"count": strata_counts[k], "sampled": alloc[k]} for k in sorted(strata_counts)},
        "sample_size": len(sample_records),
        "review_queue_size": len(queue_records),
        "target_sample_size": target,
        "min_per_stratum": floor,
        "seed": seed,
    }

    out = {k: (ROOT / v if not Path(v).is_absolute() else Path(v)) for k, v in cfg["outputs"].items()}
    safe_write_jsonl(out["sample_jsonl"], sample_records)
    safe_write_jsonl(out["review_queue"], queue_records)
    safe_write(out["sample_form"], _render_form(sample_records, strata_counts, voters))
    safe_write(out["report"], json.dumps(report, ensure_ascii=False, indent=2))

    print(f"needs_review total : {len(needs_review)}")
    print(f"strata             : {len(strata_counts)}")
    print(f"sampled (adjudicate): {len(sample_records)}")
    print(f"review queue       : {len(queue_records)}")
    print("\nStrata -> sampled/total:")
    for k in sorted(strata_counts):
        print(f"  {k:42s} {alloc[k]:3d}/{strata_counts[k]}")
    print(f"\nWrote: {out['sample_jsonl'].name}, {out['sample_form'].name}, "
          f"{out['review_queue'].name}, {out['report'].name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
