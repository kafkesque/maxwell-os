#!/usr/bin/env python3
"""Bake-off REPORT layer: validity guards, error-set complementarity, D-300 deploy verdict.

Read-only. Metrics are RECOMPUTED locally from each arm's per-row predictions and printed next to
the harness's own numbers (independent cross-check). A degenerate arm (abstains on nearly everything,
or reproduces the baseline error set exactly) is reported INVALID - never as a tie or a win.
"""
import argparse, importlib.util, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _harness():
    spec = importlib.util.spec_from_file_location("bk", ROOT / "scripts" / "bakeoff_typed_decision.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _label(p):
    """Normalise a stored prediction: None | str | [label, score] -> (label, score|None)."""
    if p is None:
        return None, None
    if isinstance(p, (list, tuple)):
        return (p[0], p[1] if len(p) > 1 else None) if p else (None, None)
    return p, None


def score(preds: dict, rows: list, truth: dict) -> dict:
    """Locally recomputed metrics for one arm (decided rows only; abstention is legitimate)."""
    n = err = abst = 0
    errset = set()
    for r in rows:
        fb = r["fb_id"]
        if fb not in truth:
            continue
        n += 1
        lab, score_ = _label(preds.get(fb))
        if lab is None:
            abst += 1
            continue
        if lab != truth[fb]:
            err += 1
            errset.add(fb)
    decided = n - abst
    return {"n": n, "decided": decided, "abstain_rate": (abst / n if n else 0.0),
            "error_rate": (err / decided if decided else None), "errors": err, "errset": errset}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default="governance/bakeoff_typed_decision_20260921.json")
    args = ap.parse_args()

    bk = _harness()
    cfg = bk.load_config()
    rep = cfg["report"]
    rows, truth = bk.load_rows(cfg, int(cfg["limit"]))

    art = json.loads((ROOT / args.artifact).read_text(encoding="utf-8"))
    preds = {name: (a.get("predictions") or {}) for name, a in art["arms"].items()}
    harness_err = {name: a.get("error_rate") for name, a in art["arms"].items()}

    base_name = rep["constant_arm"]
    if base_name not in preds or not preds[base_name]:
        fn = bk.ARMS.get(base_name) if hasattr(bk, "ARMS") else None
        out = fn(rows, truth, cfg=cfg) if fn else {}
        preds[base_name] = out.get("predictions", out) if isinstance(out, dict) else {}
        harness_err[base_name] = out.get("error_rate") if isinstance(out, dict) else None

    print("arm            n   decided  abstain  err(local)  err(harness)  validity")
    m = {}
    for name, pr in preds.items():
        s = score(pr, rows, truth)
        m[name] = s
        bad = []
        if s["n"] and s["decided"] / s["n"] < float(rep["min_decided_ratio"]):
            bad.append("abstains>%.0f%%" % (100 * (1 - float(rep["min_decided_ratio"]))))
        print("%-14s %3d  %7d  %6.1f%%  %10s  %12s  %s" % (
            name, s["n"], s["decided"], 100 * s["abstain_rate"],
            "n/a" if s["error_rate"] is None else "%.3f" % s["error_rate"],
            "n/a" if harness_err.get(name) is None else "%.3f" % harness_err[name],
            ",".join(bad) if bad else "ok"))

    base = m.get(base_name, {}).get("errset", set())
    print("\ncomplementarity vs %s (error-set Jaccard; 0=disjoint errors, 1=identical):" % base_name)
    for name, s in m.items():
        if not base:
            print("  %-14s n/a (baseline error set is empty - no baseline to compare)" % name)
            continue
        j = len(s["errset"] & base) / max(1, len(s["errset"] | base))
        tag = "  <= DEGENERATE (identical error set)" if s["errset"] == base else ""
        print("  %-14s %.3f (n_err=%d)%s" % (name, j, len(s["errset"]), tag))

    print("\ncalibrated-abstention sweep (abstain the lowest-margin rows; error among decided):")
    for name, pr in preds.items():
        pairs = []
        for r in rows:
            fb = r["fb_id"]
            if fb not in truth:
                continue
            lab, sc = _label(pr.get(fb))
            if lab is None or sc is None:
                continue
            pairs.append((float(sc), lab == truth[fb]))
        if not pairs:
            print("  %-14s n/a (arm stores no per-row margin)" % name)
            continue
        pairs.sort(reverse=True)
        curve = []
        for frac in rep["abstain_sweep"]:
            keep = pairs[:max(1, int(round(len(pairs) * (1 - float(frac)))))]
            err = sum(1 for _s, ok in keep if not ok) / len(keep)
            curve.append("abstain %3.0f%% -> decided %3d err %.3f" % (100 * float(frac), len(keep), err))
        print("  %-14s %s" % (name, " | ".join(curve)))

    # BUG-322: v1 compared every arm to the CONSTANT floor, so the incumbent itself "passed". The
    # deployed configuration is the reference; constant is only the triviality floor (D-300 v2).
    if rep.get("incumbent_arm") and rep["incumbent_arm"] not in m:
        print("\nWARNING: incumbent '" + str(rep["incumbent_arm"]) + "' absent from this artifact"
              " - verdicts below are NOT COMPARABLE (re-run it first)")
    ref_name = rep["incumbent_arm"] if rep.get("incumbent_arm") in m else base_name
    print("\nD-300 deploy rule (>= %.1f pp vs incumbent '%s'; '%s' is only the triviality floor):" % (
        float(rep["min_error_gain_pp"]), ref_name, base_name))
    b = m.get(ref_name, {})
    for name, s in m.items():
        if name in (ref_name, base_name):
            continue
        if s["error_rate"] is None or (s["n"] and s["decided"] / s["n"] < float(rep["min_decided_ratio"])):
            print("  %-14s REJECT/INVALID (insufficient decided rows -> comparison vacuous)" % name)
            continue
        gain = (b["error_rate"] - s["error_rate"]) * 100 if b["error_rate"] is not None else None
        print("  %-14s gain %s pp -> %s" % (name, "n/a" if gain is None else "%.1f" % gain,
              "ADOPT" if (gain is not None and gain >= float(rep["min_error_gain_pp"])) else "REJECT"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
