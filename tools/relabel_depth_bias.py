#!/usr/bin/env python3
"""Depth-bias relabel adjudication — 3-model cross-family vote (D2362 follow-on).

The 50-FB production verify (s4_depth_d2359_gptoss_production_verify.json)
shows an ASYMMETRIC depth bias: 13 FBs gold="domain" that GPT-OSS classifies
"cross-domain" vs 1 in reverse. Those 13 sit in inherently cross-disciplinary
fields (behavioral economics, HCI, social psychology) — so the GOLD label is
likely wrong, not the model.

This tool runs a 3-family vote (GEN_MODEL/qwen + S4_DEPTH_MODEL/gemma +
VERIFY_MODEL/gpt-oss) through the PRODUCTION classify_depth_focused() path and
emits a flag list for human rubber-stamp. It does NOT mutate the golden set
(ground-truth changes are a human decision).

C12: model names from pipeline_paths (config); disputed set from the committed
verify JSON (data, not code). Adjudication-only — not a production classifier.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

VERIFY_JSON = PROJECT_ROOT / "governance" / "s4_depth_d2359_gptoss_production_verify.json"
OUT_JSON = PROJECT_ROOT / "governance" / "depth_bias_relabel_vote.json"


def load_disputed() -> list[dict]:
    """Load golden FBs whose benchmark pred != gold, matched by name."""
    import yaml
    from pipeline.pipeline_paths import S2_GOLDEN_PATH

    verify = json.loads(VERIFY_JSON.read_text())
    disputed_names = {r["name"] for r in verify["rows"] if r["pred"] != r["gold"]}

    with open(PROJECT_ROOT / S2_GOLDEN_PATH) as f:
        d = yaml.safe_load(f)

    out = []
    for ex in d["examples"]:
        fb = ex.get("expected_fb", {})
        if not isinstance(fb, dict) or not fb:
            continue
        if fb.get("name") in disputed_names:
            out.append({
                "golden_id": ex.get("id", "?"),
                "name": fb.get("name", ""),
                "definition": fb.get("definition", ""),
                "mechanism": fb.get("mechanism", ""),
                "boundary": fb.get("boundary", ""),
                "consequence": fb.get("consequence", ""),
                "gold_depth": fb.get("depth", ""),
            })
    return out


def classify(fb: dict, model: str) -> tuple[str, str | None]:
    from pipeline.stage4_merged_call import classify_depth_focused
    try:
        pred = classify_depth_focused(fb, model=model, max_tokens=1024)
        return pred, None
    except Exception as e:
        return "FAIL", f"{type(e).__name__}: {e}"


def main() -> int:
    from pipeline.pipeline_paths import GEN_MODEL, S4_DEPTH_MODEL, VERIFY_MODEL

    models = {"qwen": GEN_MODEL, "gemma": S4_DEPTH_MODEL, "gptoss": VERIFY_MODEL}
    disputed = load_disputed()

    print("Depth-bias relabel adjudication — 3-model cross-family vote")
    print(f"disputed FBs: {len(disputed)}")
    print(f"models: {json.dumps(models, indent=2)}")
    print("=" * 78)

    results = []
    for fb in disputed:
        votes = {}
        for tag, model in models.items():
            pred, err = classify(fb, model)
            votes[tag] = {"pred": pred, "err": err}
        tally = Counter(v["pred"] for v in votes.values() if v["pred"] != "FAIL")
        winner = tally.most_common(1)[0][0] if tally else None
        relabel = winner is not None and winner != fb["gold_depth"] and tally[winner] >= 2
        row = {
            "id": fb["golden_id"],
            "name": fb["name"],
            "gold": fb["gold_depth"],
            "votes": {k: v["pred"] for k, v in votes.items()},
            "tally": dict(tally),
            "recommend": winner if relabel else None,
        }
        results.append(row)
        print(f"  {fb['golden_id']:<10} gold={fb['gold_depth']:<12} "
              f"qwen={votes['qwen']['pred']:<12} gemma={votes['gemma']['pred']:<12} "
              f"gptoss={votes['gptoss']['pred']:<12} -> "
              f"{'RELABLE -> ' + winner if relabel else 'keep'}")
        print(f"      {fb['name']}")

    relabel_count = sum(1 for r in results if r["recommend"])
    print("=" * 78)
    print(f"recommend relabel: {relabel_count}/{len(results)}")
    json.dump(results, open(OUT_JSON, "w"), indent=2)
    print(f"flag list -> {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
