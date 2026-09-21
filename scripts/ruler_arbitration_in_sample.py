"""ANCHOR-1 arbitration analysis (D-306): can two complementary labelers beat the incumbent?

Reads the frozen bake-off artifact (per-row label + margin per arm) and the frozen ruler truth,
then evaluates arbitration rules that combine the incumbent verifier (pairwise) with the LLM labeler
(qwen3coder). Config-first: arm names come from config/eval_integrity.yaml (bakeoff.report).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "governance" / "bakeoff_typed_decision_20260921.json"
FROZEN = ROOT / "governance" / "anchor1_frozen_20260920.json"
OUT = ROOT / "governance" / "ruler_arbitration_in_sample_20260921.json"


def load_truth() -> dict[str, str]:
    """Human discipline labels, keyed by fb_id (frozen ruler key, not the adjudication sheet)."""
    rows = json.loads(FROZEN.read_text(encoding="utf-8")).get("rows") or []
    return {r["fb_id"]: (r.get("human") or {}).get("disc") for r in rows if r.get("fb_id")}


def pct_rank(margins: dict[str, float]) -> dict[str, float]:
    """Map raw margins to within-arm rank percentiles so arms with different scales compare fairly."""
    vals = sorted(margins.values())
    if not vals:
        return {}
    span = (len(vals) - 1) or 1
    ranks = {v: i / span for i, v in enumerate(vals)}
    return {k: ranks[v] for k, v in margins.items()}


def main() -> int:
    """Print agreement coverage and error of each arbitration rule over the frozen truth rows."""
    art = json.loads(ART.read_text(encoding="utf-8"))
    truth = load_truth()
    arms = {a: {k: v for k, v in (d.get("predictions") or {}).items()} for a, d in art["arms"].items()}
    inc, llm = "pairwise", "qwen3coder"
    if inc not in arms or llm not in arms:
        print("MISSING ARM: need %s and %s" % (inc, llm), file=sys.stderr)
        return 2
    ip = pct_rank({k: v[1] for k, v in arms[inc].items() if v and v[1] is not None})
    lp = pct_rank({k: v[1] for k, v in arms[llm].items() if v and v[1] is not None})
    # only rows carrying a human label may enter an error count (an unlabelled row cannot be "wrong")
    rows = [k for k in truth if truth.get(k) and k in arms[inc] and k in arms[llm]]
    stats = {"n": len(rows), "agree": 0, "err_disagree_to_incumbent": 0, "err_disagree_to_human": 0,
             "err_conf_weighted": 0, "err_disagree_conf_llm_wins": 0, "both_wrong": 0, "either_wrong": 0}
    for k in rows:
        ref = truth[k]
        pl, pm = arms[inc][k][0], ip.get(k, 0.0)
        ql, qm = arms[llm][k][0], lp.get(k, 0.0)
        stats["either_wrong"] += int(pl != ref or ql != ref)
        stats["both_wrong"] += int(pl != ref and ql != ref)
        if pl == ql:
            stats["agree"] += 1
            stats["err_disagree_to_incumbent"] += int(pl != ref)
            stats["err_disagree_to_human"] += int(pl != ref)
            stats["err_conf_weighted"] += int(pl != ref)
            stats["err_disagree_conf_llm_wins"] += int(pl != ref)
        else:
            stats["err_disagree_to_incumbent"] += int(pl != ref)
            stats["err_conf_weighted"] += int((ql if qm > pm else pl) != ref)
            stats["err_disagree_conf_llm_wins"] += int((ql if qm >= 0.5 else pl) != ref)
    n = stats["n"] or 1
    print("rows=%d agreement=%.1f%% incumbent_err=%.3f" % (n, 100.0 * stats["agree"] / n,
          stats["err_disagree_to_incumbent"] / n))
    print("either_labeler_wrong=%d both_wrong=%d (headroom=%d)" % (stats["either_wrong"],
          stats["both_wrong"], stats["either_wrong"] - stats["both_wrong"]))
    print("rule R2 (agree->accept, disagree->human): decided=%d err=%.3f human_queue=%d" % (
        stats["agree"], stats["err_disagree_to_human"] / n, n - stats["agree"]))
    print("rule R3 (agree->accept, disagree->higher-confidence arm): err=%.3f" % (
        stats["err_conf_weighted"] / n,))
    print("rule R4 (agree->accept, disagree->LLM if conf>=0.5 else incumbent): err=%.3f" % (
        stats["err_disagree_conf_llm_wins"] / n,))
    OUT.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
