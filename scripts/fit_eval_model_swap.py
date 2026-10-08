#!/usr/bin/env python3
"""fit_eval_model_swap.py — head-to-head FIT eval of S4 classifier models (BUG-621/BUG-622, D-2767/D-2783).

WHAT IT MEASURES
----------------
The D-2767 (revised by D-2783) gate: a candidate S4 classifier model may replace
gpt-oss-20b (the classifier of record) ONLY IF it is BOTH faster AND its
Cohen-kappa vs the human-owner gold is >= the declared classifier-kappa bar
(D-2782) AND >= the baseline model's measured kappa. Measured on the TWO axes S4
classifies:
  * depth      — 207-row human depth anchor (universal / cross-domain / domain / specialized)
  * discipline — 204-row owner-finalized discipline anchor (62-way fine-grained menu)

STATISTIC (D-2611 — never bare accuracy on a skewed prior)
----------------------------------------------------------
Cohen's kappa (chance-corrected) is the gated figure; raw agreement is reported
alongside and never gates.

CLASSIFIER OF RECORD (D-2770)
----------------------------
Mirrors production EXACTLY: discipline = merged_cribs_classify →
map_to_canonical_with_fallback; depth = batch_depth_classify. Both accept a
`model` kwarg, so the ONLY thing this script changes is the model name. No
prompt drift, no new inference path.

MODELS (config-first, C12)
--------------------------
baseline + candidate + kappa bar read from stage4.swap_eval_*. Defaults match
D-2783 (baseline gpt-oss-20b-MXFP4-Q8, candidate Ornith-1.5-35B-A3B-REAP-19B —
already local, R5-clean). temp=0.0 is enforced by the shared OMLX call path (R7).

MODES
-----
  --limit N            run only the first N rows per axis (smoke)
  --skip-depth         skip the depth axis
  --skip-discipline    skip the discipline axis
  --models B,C         override baseline,candidate (comma-separated)
  --out path           write an R14-stamped JSON result

NOTE on "faster": the D-2767 gate cites tok/s, but the OMLX call path returns
text only (no usage tokens). Wall-clock per classification is the operationally
decisive figure and is reported per axis and per FB; the verdict uses wall-clock
total for the SAME work between models.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
for p in (str(REPO), str(SCRIPTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Reuse the production conformance-gate load/join + statistics (NO drift).
from discipline_conformance_gate import (  # noqa: E402
    cohen_kappa,
    load_anchor as load_discipline_anchor,
    per_class_metrics,
)
from depth_conformance_gate import load_anchor as load_depth_anchor  # noqa: E402

# C12: named constants are only fallbacks — real values come from config.
DEFAULT_BASELINE = "gpt-oss-20b-MXFP4-Q8"
DEFAULT_CANDIDATE = "Ornith-1.5-35B-A3B-REAP-19B"
DEFAULT_KAPPA_BAR = 0.7  # D-2782 classifier-kappa bar, declared pre-eval
DEPTH_ANCHOR = REPO / "governance" / "depth_anchor_conformance_20261002.json"
DISCIPLINE_ANCHOR = REPO / "governance" / "discipline_anchor_rederived_v8_20261007.json"


def load_config() -> tuple[str, str, float]:
    """Read swap-eval keys from stage4 config (C12); fall back with a C16 log."""
    try:
        import yaml

        cfg = yaml.safe_load((REPO / "config" / "pipeline_config.yaml").read_text(encoding="utf-8"))
        s4 = cfg.get("stage4", {})
        baseline = str(s4.get("swap_eval_baseline_model", DEFAULT_BASELINE))
        candidate = str(s4.get("swap_eval_candidate_model", DEFAULT_CANDIDATE))
        bar = float(s4.get("swap_eval_kappa_bar", DEFAULT_KAPPA_BAR))
        return baseline, candidate, bar
    except Exception as e:  # C16: surface, never silently default
        print(
            f"⚠️  swap-eval config unreadable ({type(e).__name__}: {e}) — "
            f"defaults baseline={DEFAULT_BASELINE} candidate={DEFAULT_CANDIDATE} bar={DEFAULT_KAPPA_BAR}",
            file=sys.stderr,
        )
        return DEFAULT_BASELINE, DEFAULT_CANDIDATE, DEFAULT_KAPPA_BAR


def _time_depth(examples: list[dict], model: str, batch_size: int) -> tuple[list[str], float]:
    from pipeline.stage4_merged_call import batch_depth_classify

    fb_data = [
        {
            "name": e["name"],
            "definition": e["definition"],
            "mechanism": e["mechanism"],
            "extraction_type": e.get("extraction_type", ""),
        }
        for e in examples
    ]
    t0 = time.time()
    preds = batch_depth_classify(fb_data, model=model, batch_size=batch_size)
    return preds, time.time() - t0


def _time_discipline(examples: list[dict], model: str) -> tuple[list[str], float]:
    from pipeline.stage4_merged_call import merged_cribs_classify
    from pipeline.stage4_merge import CANONICAL_DISCIPLINES, map_to_canonical_with_fallback
    from pipeline.schemas import get_synonym_index

    synonym_index = get_synonym_index("discipline")
    preds: list[str] = []
    t0 = time.time()
    for e in examples:
        fb = {
            "name": e["name"],
            "definition": e["definition"],
            "mechanism": e["mechanism"],
            "boundary": e["boundary"],
            "consequence": e.get("consequence", ""),
            "source_text": e.get("source_text", ""),
        }
        res = merged_cribs_classify(fb, model=model)
        if isinstance(res, list):
            res = res[0] if res else {}
        raw = res.get("discipline", "") if isinstance(res, dict) else ""
        preds.append(map_to_canonical_with_fallback(raw, "discipline", synonym_index, CANONICAL_DISCIPLINES))
    return preds, time.time() - t0


def _run_axis(
    examples: list[dict],
    model: str,
    gold_key: str,
    axis: str,
    batch_size: int,
) -> dict[str, Any]:
    n = len(examples)
    gold = [e[gold_key] for e in examples]
    if axis == "depth":
        preds, dt = _time_depth(examples, model, batch_size)
    else:
        preds, dt = _time_discipline(examples, model)
    kappa = cohen_kappa(gold, preds)
    acc = sum(1 for g, p in zip(gold, preds) if g == p) / n
    return {
        "axis": axis,
        "model": model,
        "n": n,
        "gold_distinct": len(set(gold)),
        "wall_seconds": round(dt, 2),
        "seconds_per_fb": round(dt / n, 3) if n else 0.0,
        "raw_agreement": round(acc, 4),
        "cohen_kappa": round(kappa, 4),
        "per_class": per_class_metrics(gold, preds),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--skip-depth", action="store_true")
    ap.add_argument("--skip-discipline", action="store_true")
    ap.add_argument("--models", default=None, help="baseline,candidate override")
    ap.add_argument("--out", default="", help="R14-stamped JSON result path")
    ap.add_argument("--batch-size", type=int, default=4)
    args = ap.parse_args()

    baseline, candidate, bar = load_config()
    if args.models:
        parts = args.models.split(",")
        if len(parts) != 2:
            raise SystemExit("--models must be BASELINE,CANDIDATE")
        baseline, candidate = parts[0].strip(), parts[1].strip()

    print(f"FIT eval — baseline={baseline}  candidate={candidate}  kappa_bar={bar} (D-2782)")
    print(f"  depth anchor:     {DEPTH_ANCHOR}")
    print(f"  discipline anchor: {DISCIPLINE_ANCHOR}")

    def _safe_run(examples, m, gold_key, axis):
        """Run one axis for one model; a schema failure is a RESULT, not a crash (C16)."""
        try:
            return _run_axis(examples, m, gold_key, axis, args.batch_size)
        except Exception as e:  # C16: surface the failure in the artifact, never hide it
            print(f"   SCHEMA-FAIL {type(e).__name__}: {str(e)[:160]}", flush=True)
            return {
                "axis": axis,
                "model": m,
                "n": len(examples),
                "gold_distinct": len(set(e[gold_key] for e in examples)),
                "wall_seconds": None,
                "seconds_per_fb": None,
                "raw_agreement": None,
                "cohen_kappa": None,
                "per_class": {},
                "error": f"{type(e).__name__}: {str(e)[:300]}",
            }

    results: list[dict[str, Any]] = []

    if not args.skip_depth:
        depth_ex = load_depth_anchor(str(DEPTH_ANCHOR))
        if args.limit is not None:
            depth_ex = depth_ex[: args.limit]
        for m in (baseline, candidate):
            print(f"\n── depth :: {m} (N={len(depth_ex)}) ──", flush=True)
            results.append(_safe_run(depth_ex, m, "depth_label", "depth"))

    if not args.skip_discipline:
        disc_ex = load_discipline_anchor(str(DISCIPLINE_ANCHOR))
        if args.limit is not None:
            disc_ex = disc_ex[: args.limit]
        for m in (baseline, candidate):
            print(f"\n── discipline :: {m} (N={len(disc_ex)}) ──", flush=True)
            results.append(_safe_run(disc_ex, m, "discipline", "discipline"))

    for r in results:
        if r.get("error"):
            continue
        print(f"  [{r['axis']}/{r['model']}] kappa={r['cohen_kappa']}  raw={r['raw_agreement']}  wall={r['wall_seconds']}s ({r['seconds_per_fb']}s/FB)")

    # Verdict per axis.
    by_axis: dict[str, dict[str, dict[str, Any]]] = {}
    for r in results:
        by_axis.setdefault(r["axis"], {})[r["model"]] = r

    print("\n════════ VERDICT (per axis) ════════")
    for axis, models in by_axis.items():
        b = models.get(baseline)
        c = models.get(candidate)
        if not b or not c:
            continue
        if b.get("error") or c.get("error"):
            print(f"  [{axis}] SCHEMA-FAIL — baseline={b.get('error')}  candidate={c.get('error')}")
            continue
        faster = c["wall_seconds"] < b["wall_seconds"]
        kappa_ok = c["cohen_kappa"] >= bar
        beats_baseline = c["cohen_kappa"] >= b["cohen_kappa"]
        passed = faster and kappa_ok and beats_baseline
        print(f"  [{axis}]")
        print(f"    baseline  kappa={b['cohen_kappa']}  wall={b['wall_seconds']}s")
        print(f"    candidate kappa={c['cohen_kappa']}  wall={c['wall_seconds']}s")
        print(f"    faster={faster}  kappa>=bar({bar})={kappa_ok}  >=baseline={beats_baseline}  -> {'PASS' if passed else 'FAIL'}")

    if args.out:
        from pipeline.pipeline_paths import PIPELINE_COMMIT, SCHEMA_VERSION

        out = {
            "schema_version": SCHEMA_VERSION,
            "gen_model": f"{baseline},{candidate}",
            "pipeline_commit": PIPELINE_COMMIT,
            "baseline": baseline,
            "candidate": candidate,
            "kappa_bar": bar,
            "results": results,
        }
        Path(args.out).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
