#!/usr/bin/env python3
"""scripts/abstention_robustness.py - error bars + reference-drift check on the ratified abstention points (D-352).

Two questions the D-312/D-348/D-349 point estimates cannot answer on their own:
  1. Is the gain bigger than sampling noise on 116/150 rows? (paired bootstrap)
  2. Was it measured against the reference that is in force today? (D-347 re-score)

Read-only, deterministic, no LLM, no new inference. Writes JSON + MD (C6 atomic).
Exit 0 = reproduced and no interval problem; exit 2 = a finding (drift or a gain indistinguishable
from noise); exit 1 = a declared input is missing (C16).
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import yaml

_ROOT = Path(__file__).resolve().parent.parent
_CFG_PATH = _ROOT / "config" / "abstention_robustness.yaml"
sys.path.insert(0, str(_ROOT / "scripts"))
import r2_gate_measure as rgm  # noqa: E402  (D-348 canon + AUC, reused not re-implemented)


def write_atomic(path: Path, text: str) -> None:
    """C6 crash-safe write: tempfile -> fsync -> os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    with os.fdopen(fd, "w") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def load_cfg() -> dict:
    """Load the config and fail closed if a declared input is missing (C16)."""
    cfg = yaml.safe_load(_CFG_PATH.read_text(encoding='utf-8'))
    paths = [cfg[k] for k in ("calibration_artifact", "r2_artifact", "bakeoff_artifact")]
    paths += [v["path"] for v in cfg["references"].values()]
    for rel in paths:
        if not (_ROOT / rel).exists():
            raise SystemExit("missing declared input " + rel + " - refusing (C16)")
    return cfg


def read_table(rel: str) -> list[dict]:
    """Read a CSV artifact as a list of dict rows."""
    with (_ROOT / rel).open(newline="", encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def build_rows(cfg: dict) -> dict:
    """Assemble per-row (hit, score, reference) records for every axis x reference combination."""
    sheet = {rgm.norm_name(r["name"]): r for r in read_table(cfg["references"]["ruler_sheet_raw"]["path"])}
    cons = {rgm.norm_name(r["name"]): r for r in read_table(cfg["references"]["ruler_in_force"]["path"])}
    if not sheet or not cons:
        raise SystemExit("a declared reference table is empty - refusing (C16)")
    r2 = json.loads((_ROOT / cfg["r2_artifact"]).read_text(encoding='utf-8'))
    idx = {r["fb_id"]: r for r in r2["results"]}
    preds = json.loads((_ROOT / cfg["bakeoff_artifact"]).read_text(encoding='utf-8'))["arms"][cfg["bakeoff_arm"]]["predictions"]
    sheet_col = cfg["references"]["ruler_sheet_raw"]["discipline_column"]
    disc_col = cfg["references"]["ruler_in_force"]["discipline_column"]
    ct_col = cfg["references"]["ruler_in_force"]["content_type_column"]
    out: dict[tuple[str, str], list[dict]] = {}

    def add(key: tuple[str, str], rec: dict) -> None:
        out.setdefault(key, []).append(rec)

    for fb_id, (label, margin) in preds.items():
        rec = idx.get(fb_id)
        if rec is None:
            continue
        name = rgm.norm_name(rec["name"])
        s_row, c_row = sheet.get(name), cons.get(name)
        if s_row is None or c_row is None:
            continue
        leg = rgm.canon(s_row[sheet_col])
        if leg:
            add(("discipline", "ruler_sheet_raw"), {"hit": rgm.canon(label) == leg, "score": float(margin)})
        inf = rgm.canon(c_row[disc_col])
        if inf:
            add(("discipline", "ruler_in_force"), {"hit": rgm.canon(label) == inf, "score": float(margin)})
    for rec in idx.values():
        c_row = cons.get(rgm.norm_name(rec["name"]))
        if c_row is None:
            continue
        truth = rgm.canon(c_row[ct_col])
        labels = [L for L in rec["labels"] if L["axis"] == "content_type"]
        if not truth or not labels:
            continue
        add(("content_type", "ruler_in_force"),
            {"hit": any(rgm.canon(L["label"]) == truth for L in labels),
             "score": max(L["scores"]["entail"] for L in labels)})
    return out


def _err(hits: np.ndarray) -> float:
    """Error rate of a boolean hit vector."""
    return float(1.0 - hits.mean()) if hits.size else float("nan")


def _select(hit: np.ndarray, score: np.ndarray, abstain_rate: float) -> tuple[np.ndarray, np.ndarray]:
    """Split a (possibly resampled) set into (kept, abstained) by lowest score first."""
    drop = int(round(abstain_rate * hit.size))
    order = np.argsort(score, kind="stable")
    return order[drop:], order[:drop]


def curve(rows: list[dict], cfg: dict, grid_in: list[float]) -> dict:
    """Point estimates + paired bootstrap intervals for the base error and each abstain rate."""
    boot = cfg["bootstrap"]
    grid = [0.0] + sorted({round(float(g), 6) for g in grid_in})
    hit = np.array([1.0 if r["hit"] else 0.0 for r in rows])
    score = np.array([r["score"] for r in rows])
    n = hit.size
    rng = np.random.default_rng(boot["seed"])
    draws = rng.integers(0, n, (boot["n_boot"], n))
    lo, hi = 100 * boot["alpha"] / 2, 100 * (1 - boot["alpha"] / 2)
    out = {"n": int(n), "auc_margin_vs_correct": round(rgm._auc(
        [float(s) for s, h in zip(score, hit) if h == 1.0], [float(s) for s, h in zip(score, hit) if h == 0.0]), 4),
        "base_error": round(_err(hit), 4), "points": []}
    boot_auc = []
    for _ in range(boot["n_boot"]):
        pick = rng.integers(0, n, n)
        h, sc = hit[pick], score[pick]
        if 0 < h.sum() < n:
            boot_auc.append(rgm._auc([float(v) for v, k in zip(sc, h) if k == 1.0],
                                     [float(v) for v, k in zip(sc, h) if k == 0.0]))
    for rate in grid:
        keep, dumped = _select(hit, score, rate)
        pt_sel = _err(hit[keep])
        sels, dumps = [], []
        for draw in draws:
            h, s = hit[draw], score[draw]
            k, d = _select(h, s, rate)
            sels.append(_err(h[k]))
            dumps.append(_err(h[d]) if d.size else float("nan"))
        delta = (out["base_error"] - pt_sel) * 100
        d_boot = [(_err(hit[draw]) - s) * 100 for draw, s in zip(draws, sels)]
        out["points"].append({
            "abstain_rate": rate, "n_abstained": int(dumped.size), "n_kept": int(keep.size),
            "selective_error": round(pt_sel, 4),
            "selective_error_ci": [round(float(np.percentile(sels, lo)), 4), round(float(np.percentile(sels, hi)), 4)],
            "delta_vs_base_pp": round(delta, 2),
            "delta_vs_base_pp_ci": [round(float(np.percentile(d_boot, lo)), 2), round(float(np.percentile(d_boot, hi)), 2)],
            "prob_delta_gt_zero": round(float(np.mean([d > 0 for d in d_boot])), 4),
            "abstained_bucket_error": None if not dumped.size else round(_err(hit[dumped]), 4),
            "abstained_bucket_error_ci": None if not dumped.size else
                [round(float(np.nanpercentile(dumps, lo)), 4), round(float(np.nanpercentile(dumps, hi)), 4)],
        })
    out["auc_ci"] = [round(float(np.percentile(boot_auc, lo)), 4), round(float(np.percentile(boot_auc, hi)), 4)]
    return out


def main() -> int:
    """Run the robustness + drift check and write the artifact pair."""
    cfg = load_cfg()
    cal = json.loads((_ROOT / cfg["calibration_artifact"]).read_text(encoding='utf-8'))
    rows = build_rows(cfg)
    result = {"schema_version": "1.0", "decision": cfg["decision"],
              "calibration_artifact": cfg["calibration_artifact"], "bakeoff_artifact": cfg["bakeoff_artifact"],
              "bakeoff_arm": cfg["bakeoff_arm"], "bootstrap": cfg["bootstrap"],
              "abstain_grid": cfg["abstain_grid"], "qualifier": cfg["qualifier"], "combinations": {}}
    md = ["# Error bars and reference drift on the ratified abstention points (D-352)", "",
          "Paired bootstrap, " + str(cfg["bootstrap"]["n_boot"]) + " resamples, seed " + str(cfg["bootstrap"]["seed"])
          + ", " + str(int((1 - cfg["bootstrap"]["alpha"]) * 100)) + "% intervals. Operating points READ from "
          + cfg["calibration_artifact"] + ".", "",
          "References are NOT interchangeable: `ruler_sheet_raw` is what the D-312 curve was measured against;",
          "`ruler_in_force` (ANCHOR-3) is the only reference allowed to rank an arm today (D-347).", ""]
    findings = []
    for axis, spec in cfg["axes"].items():
        for ref in ("ruler_sheet_raw", "ruler_in_force"):
            key = (axis, ref)
            if key not in rows or len(rows[key]) < 30:
                continue
            grid = list(cfg["abstain_grid"]) + [_ratified_rate(cal, axis)]
            m = curve(rows[key], cfg, grid)
            m["operating_point_abstain_rate"] = _ratified_rate(cal, axis)
            result["combinations"][axis + "|" + ref] = m
            md += ["## " + axis + " | reference: " + ref, "",
                   "n=" + str(m["n"]) + ", base error " + str(m["base_error"]) + " ("
                   + str(m["base_error_ci"] if "base_error_ci" in m else "") + ")", "",
                   "AUC(margin vs correct) " + str(m["auc_margin_vs_correct"]) + m["auc_ci"].__str__(), "",
                   "| abstained | kept | selective error (95% CI) | delta (pp) [95% CI] | P(delta>0) | error in abstained bucket |",
                   "|---|---|---|---|---|---|"]
            for p in m["points"]:
                md.append("| " + str(int(p["abstain_rate"] * 100)) + "% | " + str(p["n_kept"]) + " | "
                          + str(p["selective_error"]) + " " + str(p["selective_error_ci"]) + " | "
                          + str(p["delta_vs_base_pp"]) + " " + str(p["delta_vs_base_pp_ci"]) + " | "
                          + str(p["prob_delta_gt_zero"]) + " | " + str(p["abstained_bucket_error"]) + " |")
            md.append("")
        prim = result["combinations"].get(axis + "|" + spec["primary_reference"])
        if prim:
            op = [p for p in prim["points"] if abs(p["abstain_rate"] - prim["operating_point_abstain_rate"]) < 1e-9]
            if op and op[0]["delta_vs_base_pp_ci"][0] <= 0:
                findings.append(axis + ": the ratified operating point's gain CI includes 0 on the ruler in force "
                                + str(op[0]["delta_vs_base_pp_ci"]))
            if op and op[0]["prob_delta_gt_zero"] < 0.95:
                findings.append(axis + ": P(gain>0) = " + str(op[0]["prob_delta_gt_zero"])
                                + " at the ratified operating point (<0.95)")
    legacy = result["combinations"].get("discipline|ruler_sheet_raw")
    check = cfg["reproduction_check"]
    reproduced = bool(legacy) and abs(legacy["base_error"] - check["discipline_base_error_legacy"]) <= check["tolerance"]
    result["reproduction"] = {"legacy_reference": "ruler_sheet_raw", "recorded_base_error": check["discipline_base_error_legacy"],
                              "rescored_base_error": None if not legacy else legacy["base_error"],
                              "tolerance": check["tolerance"], "reproduced": reproduced,
                              "recorded_n": 116, "rescored_n": None if not legacy else legacy["n"],
                              "reconcile_note": "0.4741 = 55/116 and the reconstructible superset is 61/122: the"
                                                " legacy denominator is a 116-row SUBSET whose 6 excluded rows were all incumbent"
                                                " errors, and the artifact that defines them is not on disk"}
    if not reproduced:
        findings.append("NOT REPRODUCIBLE: the ratified discipline base error "
                        + str(check["discipline_base_error_legacy"]) + " (n=116) cannot be reproduced on the legacy "
                        "reference. On every reconstructible subset the incumbent scores "
                        + str(None if not legacy else legacy["base_error"]) + " (n="
                        + str(None if not legacy else legacy["n"]) + "); the 116-row denominator needs 6 rows whose "
                        "identity is not recorded anywhere on disk, so the ratified curve was measured on a SUBSET of "
                        "the reference now in force. Re-ratify the discipline operating point on the ruler in force (D-347)")
    result["findings"] = findings
    md = [md[0], ""] + md[2:]
    md += ["## Findings", ""] + (["- " + f for f in findings] if findings else ["- none"]) + ["", cfg["qualifier"], ""]
    write_atomic(_ROOT / cfg["output_json"], json.dumps(result, indent=2) + chr(10))
    write_atomic(_ROOT / cfg["output_md"], chr(10).join(md))
    for key, m in result["combinations"].items():
        print(key, "n=", m["n"], "base=", m["base_error"], "auc=", m["auc_margin_vs_correct"], m["auc_ci"])
        for p in m["points"]:
            print("   abstain", int(p["abstain_rate"] * 100), "% kept", p["n_kept"], "sel_err", p["selective_error"],
                  p["selective_error_ci"], "delta_pp", p["delta_vs_base_pp"], p["delta_vs_base_pp_ci"],
                  "P(d>0)", p["prob_delta_gt_zero"], "abst_bucket", p["abstained_bucket_error"])
    print("reproduced_legacy:", reproduced, "| findings:", len(findings))
    for f in findings:
        print("  FINDING:", f)
    print("wrote", cfg["output_json"], cfg["output_md"])
    return 2 if findings else 0


def _ratified_rate(cal: dict, axis: str) -> float:
    """Read the ratified abstain rate for an axis from the calibration artifact (never retyped)."""
    op = cal["curves"][axis]["ratified_operating_point"]
    return float(op["abstain_rate"]) if "abstain_rate" in op else float(1.0 - op["retained_coverage"])


if __name__ == "__main__":
    raise SystemExit(main())
