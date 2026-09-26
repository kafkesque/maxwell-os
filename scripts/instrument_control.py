#!/usr/bin/env python3
"""instrument_control.py - no instrument may DECIDE until its error is measured on a sealed control (D-400).

WHY (RC-5). An instrument that has never been shown a control has only its own confidence as evidence of its
quality. This module computes the CONFUSION MATRIX of a declared instrument against a known-answer control and
records it with the digests of BOTH sides, so a later reader can tell whether the number still describes the
artifacts it was measured over. Every number it emits goes through the D-404 envelope (measure.py), so no number
travels without its ruler.

The meter itself is validated first (selftest): a scorer that has never been shown a known answer is a scorer
whose arithmetic is unverified.

CLI: --selftest | --score <instrument-id> | --report
Exit: 0 ok | 1 the instrument fails its declared floor | 2 owner-owed (BUG-457 convention).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import handoff  # noqa: E402
from lib.measure import emit_metric  # noqa: E402
from lib import artifact_encoding  # noqa: E402 - D-2646: the decode rule has ONE home

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "config" / "instrument_controls.yaml"


def config() -> dict:
    """Read config/instrument_controls.yaml. Fail closed: no declaration means no control (C16)."""
    if not CONFIG.exists():
        raise SystemExit("FAIL-CLOSED: config/instrument_controls.yaml is absent - an instrument registry "
                         "with no declaration cannot decide anything")
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}


def instrument(iid: str) -> dict:
    """Return the declared instrument record, or exit loudly: an undeclared instrument has no control."""
    for spec in config().get("instruments") or []:
        if str(spec.get("id")) == iid:
            return spec
    raise SystemExit("FAIL-CLOSED: instrument " + iid + " is not declared in config/instrument_controls.yaml")


def read_csv(path: Path) -> list[dict]:
    """Read a CSV into dicts with the exact bytes on disk (no normalisation: the digest IS the claim)."""
    if not path.exists():
        raise SystemExit("FAIL-CLOSED: " + str(path) + " is absent - a control over a missing artifact is "
                         "not a measurement")
    text = artifact_encoding.open_artifact(path, REPO).read()  # D-2646/BUG-516: declared encoding, not a preference
    return list(csv.DictReader(io.StringIO(text)))


def confusion(tp: int, fp: int, fn: int, tn: int) -> dict:
    """The full confusion matrix and its derived rates. Guarded: an empty class is reported, never divided."""
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": round(prec, 4), "recall": round(rec, 4),
            "f1": round(f1, 4), "accuracy": round((tp + tn) / max(tp + tn + fp + fn, 1), 4)}


def score(iid: str) -> int:
    """Measure one declared instrument on its control and append the record. Returns the tri-state code."""
    spec = instrument(iid)
    ctl = spec.get("control") or {}
    if not ctl.get("sealed"):
        print("  owner_owed  " + iid + ": no SEALED control - " + str(ctl.get("owed") or "").strip()[:200])
        return 2
    icfg = yaml.safe_load((REPO / str(spec["instrument_config"])).read_text(encoding="utf-8")) or {}
    cohort = icfg.get("cohort") or {}
    pos = {str(x) for x in cohort.get(str(spec["positive_ids"])) or []}
    neg = {str(x) for x in cohort.get(str(spec["negative_ids"])) or []}
    rows = read_csv(REPO / str(spec["predictions"]))
    pcol, icol, pv = str(spec["prediction_column"]), str(spec["id_column"]), str(spec["positive_value"])
    tp = sum(1 for r in rows if r[icol] in pos and str(r.get(pcol, "")).strip() == pv)
    fn = sum(1 for r in rows if r[icol] in pos and str(r.get(pcol, "")).strip() != pv)
    tn = sum(1 for r in rows if r[icol] in neg and str(r.get(pcol, "")).strip() != pv)
    fp = sum(1 for r in rows if r[icol] in neg and str(r.get(pcol, "")).strip() == pv)
    m = confusion(tp, fp, fn, tn)
    floor = spec.get("floor") or {}
    fails = [k + ": " + str(m[k.replace("min_", "")]) + " < " + str(v)
             for k, v in floor.items() if m.get(k.replace("min_", ""), 0.0) < float(v)]
    pred_sha = handoff.sha256_file(REPO / str(spec["predictions"]))
    rec = {"schema_version": "1.0", "decided": "D-400", "instrument": iid, "decides": spec.get("decides"),
           "control": {"sealed": True, "n": len(rows), "n_positives": len(pos), "n_negatives": len(neg),
                       "answer_withheld_from": ctl.get("answer_withheld_from"),
                       "withheld_field": ctl.get("withheld_field"),
                       "predictions_sha16": pred_sha[:16],
                       "ruler": spec["instrument_config"],
                       "ruler_sha16": handoff.sha256_file(REPO / str(spec["instrument_config"]))[:16]},
           "matrix": m, "floor": floor, "floor_failures": fails, "code_sha": handoff.code_sha(),
           "stamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    jp = REPO / str(config()["journal"])
    jp.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(jp.parent), prefix=".ic_", suffix=".jsonl")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(jp.read_text(encoding="utf-8") if jp.exists() else "")
            fh.write(json.dumps(rec, sort_keys=True) + chr(10))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, jp)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    emit_metric(iid + "_f1", float(m["f1"]), population="the declared control cohort of " + iid + " ("
                + str(len(pos)) + " positives, " + str(len(neg)) + " negatives)", denominator=len(rows),
                ruler=str(spec["instrument_config"]), note="sealed control, predictions " + pred_sha[:16])
    print("  " + iid + " vs its SEALED control (n=" + str(len(rows)) + ", " + str(len(pos)) + " positives)")
    print("      tp=" + str(m["tp"]) + " fp=" + str(m["fp"]) + " fn=" + str(m["fn"]) + " tn=" + str(m["tn"])
          + "  precision=" + str(m["precision"]) + " recall=" + str(m["recall"]) + " f1=" + str(m["f1"]))
    if fails:
        print("      FAIL floor: " + "; ".join(fails))
        return 1
    print("      ok floor: " + json.dumps(floor))
    return 0


def report() -> int:
    """Print every declared instrument and whether a control exists for it. Owner-owed when one is missing."""
    cfg = config()
    n_ctl = 0
    for spec in cfg.get("instruments") or []:
        ctl = spec.get("control") or {}
        state = "sealed_control" if ctl.get("sealed") else "owe_control"
        n_ctl += 1 if ctl.get("sealed") else 0
        print("  " + state.ljust(14) + "  " + str(spec.get("id")) + ": decides " + str(spec.get("decides")))
        if not ctl.get("sealed"):
            print("                  owed: " + str(ctl.get("owed") or "").strip()[:160].replace(chr(10), " "))
        rec = spec.get("record")
        if rec and (REPO / str(rec)).exists():
            data = json.loads((REPO / str(rec)).read_text(encoding="utf-8"))
            print("                  unsealed baseline " + str(rec) + ": macro_f1="
                  + str(data.get("macro_f1_depth")) + " (sealed: false)")
    n = len(cfg.get("instruments") or [])
    print("  " + str(n_ctl) + " of " + str(n) + " declared instrument(s) hold a SEALED control")
    return 0 if n_ctl else 2


def selftest() -> int:
    """Known-answer control for the METER (RC-5): a perfect predictor and a random one must score exactly."""
    perfect = confusion(4, 0, 0, 7)
    randomish = confusion(2, 2, 2, 5)
    ok = (perfect["precision"] == 1.0 and perfect["recall"] == 1.0 and perfect["f1"] == 1.0
          and randomish["precision"] == 0.5 and randomish["accuracy"] == round(7 / 11, 4))
    if not ok:
        print("FAIL instrument_control selftest: the confusion arithmetic is wrong - the meter is broken")
        return 1
    print("ok instrument_control selftest: perfect scorer scores 1.0, 2/2-of-4 scorer scores 0.5 "
          "(the meter is validated before it decides)")
    return 0


def main() -> int:
    """CLI: --selftest, --score <id>, or --report."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--score", default="")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.score:
        return score(a.score)
    return report()


if __name__ == "__main__":
    sys.exit(main())
