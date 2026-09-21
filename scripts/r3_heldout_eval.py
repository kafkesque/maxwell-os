#!/usr/bin/env python3
"""R3 held-out evaluation (D-311 pre-registration): R1-R4 over the ANCHOR-1 held-out set.

R3 (from D-306) claims that combining the incumbent pairwise verifier with the LLM labeler beats the
incumbent. It was DERIVED on the 116 human-labelled ruler rows, so D-300 forbids adopting it there;
this script scores the pre-registered combine rules on the 58-row held-out set frozen in
`governance/ANCHOR2_HELDOUT_SET_20260921.json` (D-311) using the per-arm artifact produced by
`scripts/bakeoff_typed_decision.py --source anchor2`.

C12: every path, arm name, rule name, threshold and margin scale comes from
`config/eval_integrity.yaml` (bakeoff.arbitration / bakeoff.sources.<source>). Nothing is hardcoded.
D-275a: errors are reported as ERROR RATES, never as "accuracy".

Usage:
  python3 scripts/r3_heldout_eval.py                      # uses bakeoff.arbitration.source
  python3 scripts/r3_heldout_eval.py --source anchor2 --artifact governance/....json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "eval_integrity.yaml"
HARNESS = ROOT / "scripts" / "bakeoff_typed_decision.py"


def _load_harness():
    """Import the bake-off harness as a module so truth loading has ONE implementation (C21)."""
    spec = importlib.util.spec_from_file_location("bk", HARNESS)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def load_config() -> dict:
    """Read the bakeoff + arbitration blocks; fail loudly on a missing key (C16)."""
    import yaml

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["bakeoff"]
    for key in ("arbitration", "sources"):
        if key not in cfg:
            raise KeyError("config/eval_integrity.yaml bakeoff." + key + " is required")
    arb = cfg["arbitration"]
    for key in ("incumbent_arm", "challenger_arm", "margin_scale", "rules", "source",
                "r4_confidence_floor", "report"):
        if key not in arb:
            raise KeyError("bakeoff.arbitration." + key + " is required")
    return cfg


def pct_rank(margins: dict[str, float]) -> dict[str, float]:
    """Map raw margins to within-arm percent ranks so arms with different scales compare fairly."""
    vals = sorted(margins.values())
    if not vals:
        return {}
    span = (len(vals) - 1) or 1
    ranks = {v: i / span for i, v in enumerate(vals)}
    return {k: ranks[v] for k, v in margins.items()}


def _margin(row: object) -> float:
    """Margin of one stored prediction: [label, margin] (BUG-321) or a bare label (no margin)."""
    if isinstance(row, (list, tuple)) and len(row) > 1 and row[1] is not None:
        return float(row[1])
    return 0.0


def _label(row: object) -> str | None:
    """Label of one stored prediction; None means the arm abstained (never counted as an error)."""
    if isinstance(row, (list, tuple)):
        return row[0]
    return row


def evaluate(cfg: dict, source: str, artifact: Path) -> dict:
    """Score R1-R4 on the held-out rows and return the report payload (no writes here)."""
    bk = _load_harness()
    arb = cfg["arbitration"]
    src = bk.source_spec(cfg, source)
    rows, truth = bk.load_rows(cfg, int(src.get("limit") or 0), src)
    art = json.loads(artifact.read_text(encoding="utf-8"))
    if str(art.get("source") or bk.RULER_SOURCE) != src["name"]:
        raise ValueError("artifact source " + str(art.get("source")) + " != requested " + src["name"])
    arms = {a: (d.get("predictions") or {}) for a, d in (art.get("arms") or {}).items()}
    inc, chl = arb["incumbent_arm"], arb["challenger_arm"]
    for arm in (inc, chl):
        if arm not in arms:
            raise KeyError("artifact is missing arm " + arm + " (D-300: same rows, same menu)")
    scored = [r["fb_id"] for r in rows if r["fb_id"] in truth]
    ip = pct_rank({k: _margin(v) for k, v in arms[inc].items() if k in scored})
    cp = pct_rank({k: _margin(v) for k, v in arms[chl].items() if k in scored})
    n = len(scored)
    out: dict = {"n_scored": n, "incumbent_arm": inc, "challenger_arm": chl,
                 "margin_scale": arb["margin_scale"], "rules": {}, "arm_error": {}}
    for arm in (inc, chl):
        labels = [_label(arms[arm].get(k)) for k in scored]
        decided = [(k, l) for k, l in zip(scored, labels) if l is not None]
        errs = sum(1 for k, l in decided if truth[k] != l)
        out["arm_error"][arm] = {
            "decided": len(decided), "abstained": n - len(decided),
            "abstain_rate": round((n - len(decided)) / n, 4) if n else None,
            "errors": errs, "error_rate": round(errs / len(decided), 4) if decided else None,
            "abstain_reasons": {},
        }
    counts = {k: 0 for k in ("agree", "disagree", "both_wrong", "either_wrong")}
    rule_err: dict[str, int] = {k: 0 for k in arb["rules"]}
    rule_decided: dict[str, int] = {k: 0 for k in arb["rules"]}
    for k in scored:
        ref = truth[k]
        il, cl = _label(arms[inc].get(k)), _label(arms[chl].get(k))
        counts["both_wrong"] += int(il is not None and cl is not None and il != ref and cl != ref)
        counts["either_wrong"] += int((il is not None and il != ref) or (cl is not None and cl != ref))
        if il is not None and cl is not None and il == cl:
            counts["agree"] += 1
        else:
            counts["disagree"] += 1
        chosen: dict[str, str | None] = {}
        for name, kind in arb["rules"].items():
            if kind == "incumbent_only":
                chosen[name] = il
            elif kind == "agree_accept_disagree_human_queue":
                chosen[name] = il if (il is not None and il == cl) else None
            elif kind == "agree_accept_disagree_higher_margin":
                chosen[name] = (il if ip.get(k, 0.0) >= cp.get(k, 0.0) else cl) \
                    if il is not None and cl is not None else (il if il is not None else cl)
            elif kind == "agree_accept_disagree_challenger_if_conf_at_least_floor":
                if il is not None and cl is not None:
                    chosen[name] = cl if _margin(arms[chl].get(k)) >= arb["r4_confidence_floor"] else il
                else:
                    chosen[name] = il if il is not None else cl
            else:
                raise ValueError("unknown rule kind in config: " + kind)
        for name, lab in chosen.items():
            rule_decided[name] += int(lab is not None)
            rule_err[name] += int(lab is not None and lab != ref)
    inc_rate = out["arm_error"][inc]["error_rate"]
    for name in arb["rules"]:
        dec = rule_decided[name]
        rate = round(rule_err[name] / dec, 4) if dec else None
        out["rules"][name] = {
            "kind": arb["rules"][name], "decided": dec, "human_queue": n - dec,
            "queue_rate": round((n - dec) / n, 4) if n else None, "errors": rule_err[name],
            "error_rate": rate,
            "gain_vs_incumbent_pp": (round((inc_rate - rate) * 100.0, 2)
                                     if rate is not None and inc_rate is not None else None),
            "passes_min_decided_ratio": dec / n >= float(cfg["report"]["min_decided_ratio"]) if n else False,
        }
    out["counts"] = counts
    bar = float(cfg["report"]["min_error_gain_pp"])
    out["deploy_bar_pp"] = bar
    out["verdicts"] = {}
    for name, r in out["rules"].items():
        inc_abstain = out["arm_error"][inc]["abstain_rate"] or 0.0
        cand_abstain = r["queue_rate"] or 0.0
        ok = (r["gain_vs_incumbent_pp"] is not None and r["gain_vs_incumbent_pp"] >= bar
              and cand_abstain <= inc_abstain and r["passes_min_decided_ratio"])
        out["verdicts"][name] = "ADOPT-CANDIDATE" if ok else "REJECT"
    out["evidence"] = {
        "artifact": str(artifact.relative_to(ROOT)),
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "sheet_sha256": hashlib.sha256((ROOT / src["sheet"]).read_bytes()).hexdigest(),
        "key_sha256": hashlib.sha256((ROOT / src["key"]).read_bytes()).hexdigest(),
        "allowlist_file": src.get("row_allowlist_file"),
        "menu_hash": art.get("menu_hash"),
        "command_line": " ".join(sys.argv),
    }
    return out


def main() -> int:
    """Run the held-out evaluation, print the R1-R4 table and write the report artifact."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=None, help="label source (default: bakeoff.arbitration.source)")
    ap.add_argument("--artifact", default=None, help="arm artifact (default: that source's output)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    cfg = load_config()
    arb = cfg["arbitration"]
    source = args.source or arb["source"]
    src = cfg["sources"][source]
    artifact = ROOT / (args.artifact or src["output"])
    rep = evaluate(cfg, source, artifact)
    out_path = ROOT / (args.out or arb["report"])
    out_path.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print("held-out n=" + str(rep["n_scored"]) + " incumbent(" + rep["incumbent_arm"] + ") err=" +
          str(rep["arm_error"][rep["incumbent_arm"]]["error_rate"]) + " challenger err=" +
          str(rep["arm_error"][rep["challenger_arm"]]["error_rate"]))
    print("agree=" + str(rep["counts"]["agree"]) + " disagree=" + str(rep["counts"]["disagree"]) +
          " both_wrong=" + str(rep["counts"]["both_wrong"]) +
          " either_wrong=" + str(rep["counts"]["either_wrong"]))
    for name, r in rep["rules"].items():
        print("%s %-52s decided=%d queue=%d err=%s gain_pp=%s -> %s" % (
            name.upper(), r["kind"], r["decided"], r["human_queue"], r["error_rate"],
            r["gain_vs_incumbent_pp"], rep["verdicts"][name]))
    print("wrote " + str(out_path.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
