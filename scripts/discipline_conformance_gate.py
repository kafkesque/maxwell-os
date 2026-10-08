#!/usr/bin/env python3
"""discipline_conformance_gate.py — production S4 discipline classifier vs human-owner gold.

WHAT IT MEASURES
----------------
Conformance of the PRODUCTION S4 discipline labeler of record
(merged_cribs_classify → map_to_canonical_with_fallback, D2224/D2138,
gpt-oss-20b-MXFP4-Q8) against the human-owner discipline anchor
(governance/discipline_anchor_rederived_v8_20261007.json, 201 owner-finalized rows,
D-2868, superseding the D-2766 204-row conformance). NOTE (D-2770): the FIRST version of this gate measured
slim_batch_discipline_classify (the BUG-197/D2532 *emerging-row* re-classifier,
NOT the main S4 classifier) and compared RAW free-form strings without the
production remap — that under-measured the classifier-of-record and was WRONG.

STATISTIC (D-2611 — never bare accuracy on a skewed prior)
----------------------------------------------------------
The anchor is skewed (49 distinct disciplines), so raw agreement is dominated by
the majority class. The gate reports BOTH raw agreement (reported, never gated)
and Cohen's kappa (chance-corrected — the gated figure), plus per-class P/R/F1.

TEXT JOIN (deterministic, no LLM)
---------------------------------
The discipline anchor carries name+discipline but NOT the classifier's input fields.
This gate joins name/definition/mechanism/boundary/consequence/source_text from
maxwell.db fbs by content_name under collapse_whitespace at load time (mirrors
D-2658). Fail-closed if any row fails to join.

CLASSIFIER OF RECORD (D-2770)
----------------------------
The production main-S4 discipline labeler is merged_cribs_classify (full prompt
with the inline canonical label list) followed by map_to_canonical_with_fallback
(production remap: case-insensitive exact → synonym → opposite-axis guard). The
slim_batch_discipline_classify path is ONLY the BUG-197/D2532 emerging-row
re-classifier and is NOT what S4 commits use — measuring it here was the D-2770 bug.

MODES (mirrors depth_conformance_gate.py)
-----------------------------------------
  --dry-run   load + join + report counts + chance agreement; NO inference
  --selftest  verify cohen_kappa on fixed cases; NO inference
  --limit N   run only the first N anchor FBs (live smoke)
  --gate      exit 1 when kappa is below the operative floor
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from pipeline.anchor_menu_guard import assert_referee_menu_current  # noqa: E402

DEFAULT_ANCHOR = REPO / "governance" / "discipline_anchor_rederived_v8_20261007.json"
STORE = REPO / "knowledge pipeline" / "maxwell.db"
DEFAULT_MODEL = "gpt-oss-20b-MXFP4-Q8"  # classifier of record (stage4_merge.py D2249)
REPORTING_FLOOR = 0.667
OPERATIVE_FLOOR = 0.800


def _collapse(s: str) -> str:
    return " ".join((s or "").split())


def load_config() -> tuple[float, str, str, str]:
    """Read stage4 discipline conformance keys from config (C12).

    Returns (floor, path, model, gate_mode). D-2798: gate_mode is 'advisory'
    (discipline is NOT a routing facet, so --gate never fails closed) or 'hard'
    (legacy fail-closed at floor).
    """
    try:
        import yaml

        cfg = yaml.safe_load((REPO / "config" / "pipeline_config.yaml").read_text(encoding="utf-8"))
        s4 = cfg.get("stage4", {})
        floor = float(s4.get("discipline_conformance_kappa_floor", OPERATIVE_FLOOR))
        path = s4.get("discipline_anchor_path", str(DEFAULT_ANCHOR))
        model = s4.get("discipline_model", DEFAULT_MODEL)
        gate_mode = str(s4.get("discipline_gate_mode", "advisory")).strip().lower()
        if gate_mode not in ("advisory", "hard"):
            gate_mode = "advisory"
        return floor, path, model, gate_mode
    except Exception as e:  # C16: surface, never silently default
        print(f"⚠️  discipline conformance config unreadable ({type(e).__name__}: {e}) — defaults", file=sys.stderr)
        return OPERATIVE_FLOOR, str(DEFAULT_ANCHOR), DEFAULT_MODEL, "advisory"


def load_anchor(path: str) -> list[dict]:
    """Load 204 discipline rows and join text (definition/mechanism/boundary) from maxwell.db by name."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    # BUG-650 / D-2839: the discipline+domain axes are menu-derived and the 204-gold
    # was adjudicated against the PRE-D-2814 free-gen menu. Refuse kappa unless the
    # anchor is re-derived against menu v6 (D-2820) — a pre-D-2820 kappa is CIRCULAR.
    assert_referee_menu_current(doc, label=Path(path).name, axis="discipline")
    rows = doc.get("rows", [])
    if not rows:
        raise SystemExit(f"FAIL: discipline anchor has no rows: {path}")
    declared = doc.get("total")
    if declared is not None and len(rows) != int(declared):
        raise SystemExit(
            f"FAIL: discipline anchor drifted — {len(rows)} rows vs declared {declared} "
            f"(count-drift guard, BUG-624 class): {path}"
        )

    db = sqlite3.connect(str(STORE))
    cur = db.cursor()
    cur.execute("SELECT name, definition, mechanism, boundary, consequence, source_text FROM fbs")
    by_name = {_collapse(n): (d, m, b, c, s) for n, d, m, b, c, s in cur.fetchall()}
    db.close()

    out: list[dict] = []
    for r in rows:
        key = _collapse(r.get("name", ""))
        hit = by_name.get(key)
        if hit is None:
            raise SystemExit(f"FAIL: anchor row {r.get('item_id')} name not joinable to maxwell.db")
        definition, mechanism, boundary, consequence, source_text = hit
        out.append(
            {
                "item_id": r["item_id"],
                "name": r["name"],
                "definition": definition or "",
                "mechanism": mechanism or "",
                "boundary": boundary or "",
                "consequence": consequence or "",
                "source_text": source_text or "",
                "discipline": r["discipline"],
            }
        )
    return out


def cohen_kappa(gold: list[str], pred: list[str]) -> float:
    if len(gold) != len(pred) or not gold:
        raise ValueError("gold/pred must be non-empty and equal length")
    n = len(gold)
    po = sum(1 for g, p in zip(gold, pred) if g == p) / n
    labels = sorted(set(gold) | set(pred))
    pe = sum((gold.count(l) / n) * (pred.count(l) / n) for l in labels)
    denom = 1.0 - pe
    return (po - pe) / denom if abs(denom) > 1e-12 else 0.0


def per_class_metrics(gold: list[str], pred: list[str]) -> dict[str, dict[str, float]]:
    labels = sorted(set(gold) | set(pred))
    out: dict[str, dict[str, float]] = {}
    for l in labels:
        tp = sum(1 for g, p in zip(gold, pred) if g == l and p == l)
        fp = sum(1 for g, p in zip(gold, pred) if g != l and p == l)
        fn = sum(1 for g, p in zip(gold, pred) if g == l and p != l)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        out[l] = {"precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4), "n_gold": gold.count(l)}
    return out


def band(kappa: float) -> str:
    if kappa >= OPERATIVE_FLOOR:
        return "reliable (>= operative floor 0.800) — may gate"
    if kappa >= REPORTING_FLOOR:
        return "tentative (>= reporting floor 0.667) — reportable finding, licenses NO gate"
    return "below reporting floor — report the disagreement, decide nothing"


def run_inference(examples: list[dict], model: str, batch_size: int) -> list[str]:
    """Classify each FB with the production main-S4 path and remap to canonical.

    D-2770: this MUST mirror production exactly — merged_cribs_classify (full
    prompt, inline label list) then map_to_canonical_with_fallback (the same remap
    S4 commits). batch_size is retained for CLI/back-compat but the merged call is
    serial (batch is not applicable to the classifier-of-record).
    """
    from pipeline.stage4_merged_call import merged_cribs_classify
    from pipeline.stage4_merge import CANONICAL_DISCIPLINES, map_to_canonical_with_fallback
    from pipeline.schemas import get_synonym_index

    synonym_index = get_synonym_index("discipline")
    canonical: list[str] = []
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
        canonical.append(map_to_canonical_with_fallback(raw, "discipline", synonym_index, CANONICAL_DISCIPLINES))
    return canonical


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchor", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--batch-size", type=int, default=None)
    args = ap.parse_args()

    floor, cfg_path, model, gate_mode = load_config()
    anchor_path = args.anchor or cfg_path

    if args.selftest:
        cases = [
            (["a", "a", "b", "b"], ["a", "a", "b", "b"], 1.0, "perfect"),
            (["a", "a", "b", "b"], ["b", "b", "a", "a"], -1.0, "perfect-inverse"),
            (["a", "a", "a", "b"], ["a", "a", "a", "a"], 0.0, "majority-class-only"),
        ]
        ok = True
        for gold, pred, want, name in cases:
            got = round(cohen_kappa(gold, pred), 6)
            ok &= abs(got - want) <= 1e-6
            print(f"  {'OK' if abs(got - want) <= 1e-6 else 'FAIL'} {name}: cohen_kappa={got}")
        return 0 if ok else 1

    examples = load_anchor(anchor_path)
    if args.limit is not None:
        examples = examples[: args.limit]

    gold = [e["discipline"] for e in examples]
    print(f"discipline conformance anchor: {anchor_path}")
    print(f"  N = {len(examples)}   model = {model}")
    print(f"  gold distinct disciplines: {len(set(gold))}")
    print(f"  floor (kappa): {floor}  (reporting {REPORTING_FLOOR} / operative {OPERATIVE_FLOOR})  gate_mode={gate_mode}")

    if args.dry_run:
        majority = Counter(gold).most_common(1)[0][0]
        base = cohen_kappa(gold, [majority] * len(gold))
        print(f"  DRY-RUN (no inference): majority-class kappa baseline = {base:.4f}")
        print("  live run:  python3 scripts/discipline_conformance_gate.py [--gate] [--limit N]")
        return 0

    pred = run_inference(examples, model, args.batch_size or 4)
    kappa = cohen_kappa(gold, pred)
    acc = sum(1 for g, p in zip(gold, pred) if g == p) / len(gold)
    pc = per_class_metrics(gold, pred)

    print(f"  raw agreement (accuracy): {acc:.4f}   (reported, NOT gated)")
    print(f"  Cohen's kappa:            {kappa:.4f}   -> {band(kappa)}")
    print("  per-class (top gold counts):")
    for l in sorted(pc, key=lambda x: -pc[x]["n_gold"])[:10]:
        m = pc[l]
        print(f"    {l[:28]:<28} P={m['precision']} R={m['recall']} F1={m['f1']} (gold n={m['n_gold']})")

    if args.gate:
        if gate_mode == "advisory":
            # D-2798: discipline is ADVISORY-ONLY — it is NOT a routing facet, so its
            # quality NEVER fail-closes the pipeline. Report against the human ceiling
            # and exit 0 regardless of the floor (the floor is a reporting reference).
            print(f"ADVISORY (D-2798, gate_mode={gate_mode!r}): discipline is NOT a routing facet — "
                  f"kappa {kappa:.4f} reported only; NO fail-closed (floor {floor} is a reporting reference).")
            return 0
        if kappa < floor:
            print(f"FAIL-CLOSED: kappa {kappa:.4f} < operative floor {floor}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
