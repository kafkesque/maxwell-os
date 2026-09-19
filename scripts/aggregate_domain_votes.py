#!/usr/bin/env python3
"""aggregate_domain_votes.py — D2633 deterministic domain-aggregation (LLM-free).

Applies the USER-RULED domain-aggregation policy to a reliable-pair vote
checkpoint (discipline + domain votes with per-voter domain sets):

  POLICY (D2633, 2026-09-14 user ruling):
    discipline:  unanimous (both voters, same canonical) -> accepted; else contested.
    domains:     exact-set unanimous -> accepted as-is.
                 overlap (non-empty intersection) -> UNION of both voter sets
                   (sorted). The union ALWAYS includes DeepSeek's classification
                   (user: "plus what deepseek classifies").
                 disjoint (empty intersection) -> ABSTAIN (domains=[]).
                 any voter missing/errored -> ABSTAIN (never fabricate).

Read-only: consumes the stored votes, emits aggregated verdicts + a summary.
NO model calls, NO DB writes. Re-runnable (deterministic).

Usage:
  python3 scripts/aggregate_domain_votes.py \
      --checkpoint governance/discipline_domain_vote_checkpoint.jsonl \
      --out governance/p1_domain_aggregation.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.pipeline_paths import PIPELINE_COMMIT, SCHEMA_VERSION  # noqa: E402

DEFAULT_RELIABLE = ("deepseek-v4-pro", "Qwen3.8-27B-MLX-4bit")

# ── Peer-granularity guard (D-2637, 2026-09-16) ─────────────────────────────
# MEASURED BASIS (251 human-adjudicated rows, see
# governance/domain_aggregation_policy_v2.md): union is a PEER-ONLY operator.
# Against an over-labelling partner it destroys precision --
#   Qwen3.8-27B alone .......... domain F1 0.693  (mean |P| 2.08)
#   UNION with REAP-19B ........ 0.729 (+0.015)   (mean |P| 2.23, peer)
#   UNION with gpt-oss-20b ..... 0.589 (-0.105)   (mean |P| 4.09)
#   UNION with gemma-4-E4B ..... 0.513 (-0.180)   (mean |P| 3.60)
#   UNION with Qwen3-Coder ..... 0.474 (-0.217)   (mean |P| 6.06)
#   UNION across all 6 voters .. 0.398 (-0.295)
# Gold uses 2.54 domains/row. So: union ONLY when the two voters label at
# comparable granularity; otherwise ABSTAIN (fail-closed, D2610 philosophy)
# rather than fabricate a merged set that is measurably worse than either
# voter alone.
PEER_GRANULARITY_MAX_RATIO = 1.30  # max(mean|P|) / min(mean|P|) <= 1.30
PEER_F1_MAX_GAP = 0.10  # documented companion condition; needs ground truth,
# so it is enforceable only at eval time, not in this LLM-free aggregator.


def _load_checkpoint(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _voter_sets(row: Dict[str, Any]) -> Dict[str, Optional[Dict[str, Any]]]:
    votes = row.get("votes", {})
    out: Dict[str, Optional[Dict[str, Any]]] = {}
    for m in DEFAULT_RELIABLE:
        v = votes.get(m)
        if isinstance(v, dict) and "error" not in v:
            out[m] = v
        else:
            out[m] = None
    return out


def _granularity_profile(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Measure each voter's label granularity and decide if the pair is a peer pair.

    Returns mean domains-per-row for each reliable voter, their ratio, and whether
    union aggregation is permitted under PEER_GRANULARITY_MAX_RATIO.
    """
    sums: Dict[str, int] = {m: 0 for m in DEFAULT_RELIABLE}
    counts: Dict[str, int] = {m: 0 for m in DEFAULT_RELIABLE}
    for row in rows:
        vs = _voter_sets(row)
        for m in DEFAULT_RELIABLE:
            v = vs.get(m)
            if v is None:
                continue
            doms = v.get("domains") or []
            if doms:
                sums[m] += len(doms)
                counts[m] += 1

    means = {m: (sums[m] / counts[m] if counts[m] else 0.0) for m in DEFAULT_RELIABLE}
    positives = [v for v in means.values() if v > 0]
    ratio = (max(positives) / min(positives)) if len(positives) == len(DEFAULT_RELIABLE) else 0.0
    permitted = bool(ratio) and ratio <= PEER_GRANULARITY_MAX_RATIO
    return {
        "mean_domains_per_row": {m: round(means[m], 3) for m in DEFAULT_RELIABLE},
        "n_rows_per_voter": dict(counts),
        "granularity_ratio": round(ratio, 3),
        "max_allowed_ratio": PEER_GRANULARITY_MAX_RATIO,
        "union_permitted": permitted,
        "f1_gap_condition": (
            f"companion rule (<= {PEER_F1_MAX_GAP}) requires ground truth; "
            "verify at eval time -- see governance/domain_aggregation_policy_v2.md"
        ),
    }


def _aggregate_row(row: Dict[str, Any], union_permitted: bool = True) -> Dict[str, Any]:
    vs = _voter_sets(row)
    valid = [v for v in vs.values() if v is not None]

    disc_vals = [v.get("discipline") for v in valid if v.get("discipline")]
    disc_unanimous = len(disc_vals) == len(DEFAULT_RELIABLE) and len(set(disc_vals)) == 1

    dom_sets = [set(v.get("domains") or []) for v in valid]
    # both voters present AND both non-empty is required for a domain verdict
    both_nonempty = all(bool(s) for s in dom_sets) and len(dom_sets) == len(DEFAULT_RELIABLE)
    if both_nonempty:
        inter = set.intersection(*dom_sets)
        union = sorted(set.union(*dom_sets))
        if inter:
            if set(dom_sets[0]) == set(dom_sets[1]):
                dom_status = "exact"
                final_domains = sorted(dom_sets[0])
            elif union_permitted:
                dom_status = "union"
                final_domains = union
            else:
                # Non-peer voters: union would be measurably worse than either
                # voter alone. Abstain instead of fabricating a merged set.
                dom_status = "union_blocked_granularity"
                final_domains = []
        else:
            dom_status = "disjoint"
            final_domains = []
    else:
        dom_status = "abstain"
        final_domains = []
        inter = set()

    return {
        "fb_id": row["fb_id"],
        "name": row.get("name", ""),
        "discipline": disc_vals[0] if disc_unanimous else None,
        "discipline_status": "unanimous" if disc_unanimous else "contested",
        "domains": final_domains,
        "domain_status": dom_status,
        "deepseek_domains": sorted(vs[DEFAULT_RELIABLE[0]].get("domains") or [])
            if vs[DEFAULT_RELIABLE[0]] else [],
        "qwen_domains": sorted(vs[DEFAULT_RELIABLE[1]].get("domains") or [])
            if vs[DEFAULT_RELIABLE[1]] else [],
        "accept": disc_unanimous and bool(final_domains),
        "needs_review": not (disc_unanimous and bool(final_domains)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = _load_checkpoint(Path(args.checkpoint))
    profile = _granularity_profile(rows)
    union_permitted = bool(profile["union_permitted"])
    verdicts = [_aggregate_row(r, union_permitted=union_permitted) for r in rows]

    accept = sum(1 for v in verdicts if v["accept"])
    disc_unanimous = sum(1 for v in verdicts if v["discipline_status"] == "unanimous")
    contested = sum(1 for v in verdicts if v["discipline_status"] == "contested")
    dom_exact = sum(1 for v in verdicts if v["domain_status"] == "exact")
    dom_union = sum(1 for v in verdicts if v["domain_status"] == "union")
    dom_disjoint = sum(1 for v in verdicts if v["domain_status"] == "disjoint")
    dom_abstain = sum(1 for v in verdicts if v["domain_status"] == "abstain")
    dom_blocked = sum(1 for v in verdicts if v["domain_status"] == "union_blocked_granularity")

    result = {
        "checkpoint": args.checkpoint,
        "policy": (
            "D2633: discipline unanimous-else-contested; domains overlap->UNION "
            "(incl. DeepSeek), disjoint->abstain. D-2637: union additionally gated "
            "on PEER granularity (see peer_granularity) -- non-peer pairs abstain."
        ),
        "peer_granularity": profile,
        "n_rows": len(rows),
        "n_accept": accept,
        "n_disc_unanimous": disc_unanimous,
        "n_contested": contested,
        "domain_status_counts": {
            "exact": dom_exact, "union": dom_union,
            "disjoint": dom_disjoint, "abstain": dom_abstain,
            "union_blocked_granularity": dom_blocked,
        },
        "verdicts": verdicts,
        "schema_version": SCHEMA_VERSION,
        "gen_model": "aggregate_domain_votes.py (deterministic; no generation)",
        "pipeline_commit": PIPELINE_COMMIT,
    }

    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"rows: {len(rows)} | accept: {accept} | disc-unanimous: {disc_unanimous} | contested: {contested}")
    print(f"domains: exact {dom_exact} | union {dom_union} | disjoint {dom_disjoint} | abstain {dom_abstain}")
    print(
        "peer-granularity: "
        + ", ".join(f"{m}={profile['mean_domains_per_row'][m]}" for m in DEFAULT_RELIABLE)
        + f" | ratio {profile['granularity_ratio']} (max {profile['max_allowed_ratio']})"
        + f" | union_permitted={profile['union_permitted']}"
        + (f" | blocked {dom_blocked}" if dom_blocked else "")
    )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
