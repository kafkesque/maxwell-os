#!/usr/bin/env python3
"""scripts/r2_gate_measure.py — R2 definition-anchored NLI as a monotone precision gate (D-348).

Measures, on the frozen ruler, whether the R2 meter (existing artifact) separates
rows whose ASSIGNED label is wrong from rows whose assigned label is right, and
what an auto-demote gate would buy in precision at a given retained coverage.

Read-only. Deterministic. No LLM, no new inference. Writes JSON + MD (C6 atomic).
"""
from __future__ import annotations

import csv
import json
import os
import re
import tempfile
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parent.parent
_CFG_PATH = _ROOT / "config" / "r2_gate_measure.yaml"
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def canon(text: str) -> str:
    """Canonicalise a label or name for comparison (case/punctuation/underscore blind)."""
    return _NON_ALNUM.sub("", str(text).lower())


def norm_name(text: str) -> str:
    """Normalise an FB name for joining (unicode quotes folded, whitespace collapsed)."""
    return " ".join(str(text).lower().replace(chr(8217), chr(39)).split())


def load_rows(cfg: dict) -> tuple[list[dict], dict]:
    """Join the R2 artifact to the ruler by canonical name; fail closed below the floor."""
    r2 = json.loads((_ROOT / cfg["r2_artifact"]).read_text(encoding='utf-8'))
    index = {norm_name(r["name"]): r for r in r2["results"]}
    with (_ROOT / cfg["ruler_artifact"]).open(newline="", encoding='utf-8') as fh:
        ruler = list(csv.DictReader(fh))
    joined, unmatched = [], []
    for row in ruler:
        rec = index.get(norm_name(row["name"]))
        if rec is None:
            unmatched.append(row["item_id"])
        else:
            joined.append({"item_id": row["item_id"], "name": row["name"], "r2": rec, "truth": row})
    if unmatched:
        raise SystemExit(f"{len(unmatched)} ruler rows joined no R2 record - refusing (C16): {unmatched[:5]}")
    if len(joined) < cfg["min_joined_rows"]:
        raise SystemExit(f"only {len(joined)} joined rows < floor {cfg['min_joined_rows']} - refusing (C16)")
    return joined, r2


def axis_scores(rec: dict, axis: str, hyp: str) -> list[dict]:
    """Return the R2 scores for one axis, filtered to the declared hypothesis type."""
    return [L for L in rec["labels"] if L["axis"] == axis and L.get("hypothesis_type") == hyp]


def _auc(pos: list[float], neg: list[float]) -> float:
    """Rank-sum AUC: P(score_correct > score_wrong); 0.5 = no discrimination."""
    if not pos or not neg:
        return 0.5
    ranked = sorted([(s, 1) for s in pos] + [(s, 0) for s in neg])
    ranks, i = {}, 0
    while i < len(ranked):
        j = i
        while j + 1 < len(ranked) and ranked[j + 1][0] == ranked[i][0]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1
    r1 = sum(ranks[k] for k in range(len(ranked)) if ranked[k][1] == 1)
    n1, n0 = len(pos), len(neg)
    return (r1 - n1 * (n1 + 1) / 2) / (n1 * n0)


def measure(rows: list[dict], cfg: dict, axis: str, spec: dict) -> dict:
    """Per-axis: base error, gate flag quality, and the selective-risk (abstention) curve."""
    gate = cfg["gate"]
    scored, skipped = [], 0
    for j in rows:
        labels = axis_scores(j["r2"], axis, spec["hypothesis_type"])
        truth = canon(j["truth"][spec["truth_column"]])
        if not labels or not truth:
            skipped += 1
            continue
        support = max(L["scores"]["entail"] for L in labels)
        contra = max(L["scores"]["contra"] for L in labels)
        hit = any(canon(L["label"]) == truth for L in labels)
        scored.append({"item_id": j["item_id"], "hit": hit, "support": support, "contra": contra,
                       "flagged": contra >= gate["contra_threshold"] or support < gate["weak_entail"]})
    n = len(scored)
    base_err = sum(1 for r in scored if not r["hit"]) / n if n else 0.0
    flagged = [r for r in scored if r["flagged"]]
    unflagged = [r for r in scored if not r["flagged"]]
    curve = []
    ordered = sorted(scored, key=lambda r: -r["support"])
    for cov in cfg["coverage_grid"]:
        keep = ordered[: max(1, int(round(cov * n)))]
        err = sum(1 for r in keep if not r["hit"]) / len(keep)
        curve.append({"coverage": cov, "kept": len(keep), "selective_error": round(err, 4),
                      "delta_pp": round((err - base_err) * 100, 2)})
    hits = [r["support"] for r in scored if r["hit"]]
    miss = [r["support"] for r in scored if not r["hit"]]
    return {
        "n_scored": n, "n_skipped": skipped, "base_error": round(base_err, 4),
        "gate": {
            "n_flagged": len(flagged),
            "flag_rate": round(len(flagged) / n, 4) if n else None,
            "flagged_error": round(sum(1 for r in flagged if not r["hit"]) / len(flagged), 4) if flagged else None,
            "unflagged_error": round(sum(1 for r in unflagged if not r["hit"]) / len(unflagged), 4) if unflagged else None,
        },
        "separation": {"mean_support_correct": round(sum(hits) / len(hits), 4) if hits else None,
                       "mean_support_wrong": round(sum(miss) / len(miss), 4) if miss else None,
                       "auc_support_vs_correct": round(_auc(hits, miss), 4)},
        "selective_risk_curve": curve,
    }


def write_atomic(path: Path, text: str) -> None:
    """C6 crash-safe write: tempfile -> fsync -> os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    with os.fdopen(fd, "w") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def main() -> int:
    """Run the measurement and write the artifact pair."""
    cfg = yaml.safe_load(_CFG_PATH.read_text(encoding='utf-8'))
    rows, r2 = load_rows(cfg)
    result = {"schema_version": "1.0", "decision": cfg["decision"],
              "r2_artifact": cfg["r2_artifact"], "ruler_artifact": cfg["ruler_artifact"],
              "n_ruler_rows": len(rows), "n_r2_fbs": r2["n_fbs"],
              "unmeasurable_axes": {"extraction_type": "no R2 score exists for this axis (declared, not guessed)",
                                    "domains": "no ruler truth column exists (declared, not guessed)"},
              "gate_rule": cfg["gate"]["rule"], "qualifier": cfg["qualifier"], "axes": {}}
    md = ["# R2 definition-anchored NLI as a monotone precision gate (D-348)", "",
          "Reference: " + cfg["r2_artifact"] + " (" + str(r2["n_fbs"]) + " FBs, existing artifact, no new inference) x "
          + cfg["ruler_artifact"] + " (" + str(len(rows)) + " joined rows).", "",
          cfg["gate"]["rule"], ""]
    for axis, spec in cfg["axes"].items():
        m = measure(rows, cfg, axis, spec)
        result["axes"][axis] = m
        md += ["## " + axis, "",
               "n=" + str(m["n_scored"]) + " (skipped " + str(m["n_skipped"]) + ") base error "
               + str(m["base_error"]) + "; AUC(support vs correct) "
               + str(m["separation"]["auc_support_vs_correct"]) + "; mean support correct "
               + str(m["separation"]["mean_support_correct"]) + " vs wrong "
               + str(m["separation"]["mean_support_wrong"]), "",
               "gate: flag rate " + str(m["gate"]["flag_rate"]) + ", error on flagged "
               + str(m["gate"]["flagged_error"]) + " vs unflagged " + str(m["gate"]["unflagged_error"]), "",
               "| retained coverage | kept | selective error | delta vs base (pp) |", "|---|---|---|---|"]
        for c in m["selective_risk_curve"]:
            md.append("| " + str(c["coverage"]) + " | " + str(c["kept"]) + " | " + str(c["selective_error"])
                      + " | " + str(c["delta_pp"]) + " |")
        md.append("")
    md += ["## Declared unmeasurable", "",
           "- extraction_type: no R2 score exists for this axis. An operating point here may NOT be "
           "transplanted from another axis (ABSTENTION_DESIGN: role/axis specific).",
           "- domains: no ruler truth column exists.", "", cfg["qualifier"], ""]
    write_atomic(_ROOT / cfg["output_json"], json.dumps(result, indent=2) + chr(10))
    write_atomic(_ROOT / cfg["output_md"], chr(10).join(md))
    for axis, m in result["axes"].items():
        print(axis, "n=", m["n_scored"], "base=", m["base_error"], "auc=", m["separation"]["auc_support_vs_correct"],
              "flag_rate=", m["gate"]["flag_rate"], "flagged_err=", m["gate"]["flagged_error"],
              "unflagged_err=", m["gate"]["unflagged_error"])
        print("   curve:", [(c["coverage"], c["selective_error"]) for c in m["selective_risk_curve"]])
    print("wrote", cfg["output_json"], cfg["output_md"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
