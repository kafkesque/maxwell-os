#!/usr/bin/env python3
"""scripts/r2_ab_harness.py — R2 hypothesis-construction A/B harness (D-284, 2026-09-20).

Decides, by MEASUREMENT not fiat, which R2 NLI hypothesis construction is a usable
content_type METER. BUG-305 showed the current "definition" arm emits ~100% CONTRA
on the principle class (hypothesis = the category meta-definition, which a specific
instance never entails). This harness ranks three arms:

  A  drop_ct     — no NLI on content_type (roles decided by Mechanism A); NLI retained
                   for discipline/domains. Not scorable as a CT meter → reported N/A.
  B  definition  — hypothesis = the label's closed-menu definition (r5 override first).
                   The current D-281 design, known-broken (BUG-305).
  C  paraphrase  — hypothesis = a paraphraseable content-claim per role.

Meter-quality metric (NOT label accuracy): over human-labeled reference rows,
  false_contra = P(contra >= 0.5 | hypothesis is the HUMAN's label)  — LOW is good
  entail_rate  = P(entail dominant | hypothesis is the human's label) — HIGH is signal
  wrong_contra = P(contra >= 0.5 | hypothesis is a WRONG role)        — HIGH is signal

A good meter has LOW false_contra AND HIGH wrong_contra. BUG-305 = false_contra ~1.0.

Read-only. Writes a JSON report (crash-safe, C6).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402

from pipeline.closed_menu import render_closed_menu  # noqa: E402
from pipeline.io_guard import safe_write  # noqa: E402
from pipeline.pipeline_paths import S5_NLI_MAX_PREMISE_CHARS  # noqa: E402

_R5 = _ROOT / "config" / "r5_slot_repair.yaml"
_SHEET = _ROOT / "governance" / "SINGLE_CODER_CEILING_SHEET_20260920.csv"
_OUT = _ROOT / "governance" / "r2_ab_harness_20260920.json"
_CONTRA = 0.5

def _load_paraphrase() -> dict[str, str]:
    """Load the per-role NLI paraphrase content-claims (D-284 arm C) from config.

    Single source with scripts/definition_nli_verify.py — config/content_types.yaml
    `nli_paraphrase`, never a second hardcoded copy (C12).
    """
    ct_path = _ROOT / "config" / "content_types.yaml"
    doc = yaml.safe_load(open(ct_path, encoding="utf-8")) or {}
    return {k: str(v).strip() for k, v in (doc.get("nli_paraphrase") or {}).items()}


def _norm(v: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(v or "").lower())


def _norm_ct(raw: str) -> str | None:
    n = _norm(raw)
    if not n:
        return None
    m = {
        "principle": "principle",
        "processtemplate": "process_template",
        "processinstance": "process_instance",
        "toolinstruction": "tool_instruction",
        "growthedge": "growth_edge",
        "noisedrop": "noise_drop",
        "quarantine": "quarantine",
    }
    return m.get(n)


def _load_r5() -> dict[str, dict[str, str]]:
    if not _R5.exists():
        return {}
    doc = yaml.safe_load(open(_R5, encoding="utf-8")) or {}
    out: dict[str, dict[str, str]] = {}
    for sec in ("content_type", "discipline"):
        out[sec] = {}
        for label, e in (doc.get(sec) or {}).items():
            if isinstance(e, dict) and e.get("definition"):
                out[sec][label] = e["definition"].strip()
    return out


def _menu_def(menu: dict, axis: str, label: str) -> str | None:
    key = "content_types" if axis == "content_type" else "disciplines"
    for e in menu.get(key, []):
        if e.get("value") == label:
            return (e.get("definition") or e.get("description") or "").strip() or None
    return None


def _defn_for(menu: dict, r5: dict, axis: str, label: str) -> str | None:
    if not label or label in ("emerging", "none"):
        return None
    return r5.get(axis, {}).get(label) or _menu_def(menu, axis, label)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(_SHEET))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--output", default=str(_OUT))
    args = ap.parse_args()

    menu = render_closed_menu()
    r5 = _load_r5()
    para = _load_paraphrase()

    rows = []
    with open(args.input, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ct = _norm_ct(r.get("CT (1-7)"))
            if ct:
                rows.append({"item_id": r["item_id"], "definition": r["DEFINITION"], "ct": ct})
    if args.limit:
        rows = rows[: args.limit]

    from pipeline.stage5_verify import _nli_pair_scores

    def sc(prem, hyp):
        e, n, c = _nli_pair_scores(prem, hyp, raise_on_error=True)
        return float(e), float(n), float(c)

    arms = {}
    # ---- Arm B: definition ----
    b = {"rows": [], "false_contra": 0, "n": 0, "entail": 0, "neutral": 0}
    # ---- Arm C: paraphrase ----
    c = {"rows": [], "false_contra": 0, "n": 0, "entail": 0, "neutral": 0}
    # ---- wrong-probe: principle vs tool_instruction (clearly wrong) ----
    wrong = {"definition": {"contra": 0, "n": 0}, "paraphrase": {"contra": 0, "n": 0}}

    for row in rows:
        prem = (row["definition"] or "")[:S5_NLI_MAX_PREMISE_CHARS]
        if not prem:
            continue
        lab = row["ct"]

        defn = _defn_for(menu, r5, "content_type", lab)
        if defn:
            e, n, cont = sc(prem, defn)
            b["n"] += 1
            b["false_contra"] += int(cont >= _CONTRA)
            b["entail"] += int(e >= n and e >= cont)
            b["neutral"] += int(n >= e and n >= cont)
            b["rows"].append({"item_id": row["item_id"], "ct": lab, "e": round(e, 3), "n": round(n, 3), "c": round(cont, 3)})

        pct = para.get(lab)
        if pct:
            e, n, cont = sc(prem, pct)
            c["n"] += 1
            c["false_contra"] += int(cont >= _CONTRA)
            c["entail"] += int(e >= n and e >= cont)
            c["neutral"] += int(n >= e and n >= cont)
            c["rows"].append({"item_id": row["item_id"], "ct": lab, "e": round(e, 3), "n": round(n, 3), "c": round(cont, 3)})

        # wrong-probe: only principle rows vs tool_instruction (a role a principle is NOT)
        if lab == "principle":
            wd = _defn_for(menu, r5, "content_type", "tool_instruction")
            if wd:
                _, _, cont = sc(prem, wd)
                wrong["definition"]["n"] += 1
                wrong["definition"]["contra"] += int(cont >= _CONTRA)
            if para.get("tool_instruction"):
                _, _, cont = sc(prem, para["tool_instruction"])
                wrong["paraphrase"]["n"] += 1
                wrong["paraphrase"]["contra"] += int(cont >= _CONTRA)

    def _rate(d, k):
        return round(d[k] / d["n"], 3) if d["n"] else None

    report = {
        "schema_version": "1.0",
        "decision": "D-284",
        "reference": args.input,
        "n_rows_scored": len(rows),
        "contra_threshold": _CONTRA,
        "arms": {
            "B_definition": {
                "n": b["n"], "false_contra": _rate(b, "false_contra"),
                "entail_rate": _rate(b, "entail"), "neutral_rate": _rate(b, "neutral"),
            },
            "C_paraphrase": {
                "n": c["n"], "false_contra": _rate(c, "false_contra"),
                "entail_rate": _rate(c, "entail"), "neutral_rate": _rate(c, "neutral"),
            },
        },
        "wrong_probe_principle_vs_tool_instruction": {
            "definition": {"contra": wrong["definition"]["contra"], "n": wrong["definition"]["n"]},
            "paraphrase": {"contra": wrong["paraphrase"]["contra"], "n": wrong["paraphrase"]["n"]},
        },
    }
    safe_write(Path(args.output), json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    print(f"=== R2 A/B harness ({len(rows)} rows, contra>={_CONTRA}) ===")
    for arm, d in report["arms"].items():
        print(f"[{arm}] n={d['n']}  false_contra={d['false_contra']}  entail={d['entail_rate']}  neutral={d['neutral_rate']}")
    wp = report["wrong_probe_principle_vs_tool_instruction"]
    print(f"[wrong-probe: principle vs tool_instruction] definition contra={wp['definition']['contra']}/{wp['definition']['n']}  "
          f"paraphrase contra={wp['paraphrase']['contra']}/{wp['paraphrase']['n']}")
    print(f"   -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
