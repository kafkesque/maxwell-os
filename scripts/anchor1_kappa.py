#!/usr/bin/env python3
"""ANCHOR-1 per-axis kappa + disagreement/repair queue (R2 annotation vs pipeline labels).

Reads the human-annotated 60-row ANCHOR-1 adjudication sheet (discipline_verdict,
domains_verdict) and the pipeline-label key, then reports chance-corrected agreement
per axis (D-275a: report ERROR RATE / kappa, never "accuracy") plus a per-row repair queue.

Deterministic measurement script, no generation. Vocabulary + alias resolution come from
config/taxonomy_v5.yaml (C12: no hardcoded vocabulary).

Outputs:
  governance/anchor1_kappa_20260921.json   machine-readable (kappa, per-row verdicts, queue)
  governance/anchor1_kappa_20260921.md     human-readable summary + repair queue

Usage:
  python3 scripts/anchor1_kappa.py            # write artifacts
  python3 scripts/anchor1_kappa.py --check    # exit 1 if any human label is out-of-vocabulary
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHEET = ROOT / "governance" / "ANCHOR1_BLIND_SHEET_20260920.csv"
KEY = ROOT / "governance" / "ANCHOR1_KEY_20260920.json"
TAXONOMY = ROOT / "config" / "taxonomy_v5.yaml"
OUT_JSON = ROOT / "governance" / "anchor1_kappa_20260921.json"
OUT_MD = ROOT / "governance" / "anchor1_kappa_20260921.md"
AXES = ("discipline", "domains", "content_type")


def load_vocab() -> tuple[set[str], set[str], dict[str, str]]:
    """Return (disc canonicals, domain canonicals, taxonomy alias, DOMAIN-ONLY alias).

    The owner-approved surface-variant map (D-307) is domain-scoped on purpose: feeding it
    into the shared alias dict also rewrote DISCIPLINE tokens (BUG-325) and depressed the
    discipline kappa for a purely cosmetic reason.
    """
    import yaml

    tax = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))
    disc = {d["canonical"] for d in tax["disciplines"]}
    doms = {d["canonical"] for d in tax["domains"]}
    alias: dict[str, str] = {}
    for coll in (tax["disciplines"], tax["domains"]):
        for entry in coll:
            for raw in entry.get("raw") or []:
                alias[raw.strip().lower()] = entry["canonical"]
            alias[entry["canonical"].strip().lower()] = entry["canonical"]
    dom_alias = dict(alias)
    norm_path = ROOT / "config" / "normalization_map.yaml"
    if norm_path.exists():   # owner-approved surface variants (D-307), DOMAIN axis only (BUG-325)
        for raw, canon in (yaml.safe_load(norm_path.read_text(encoding="utf-8")).get("domains") or {}).items():
            dom_alias[str(raw).strip().strip('"').lower()] = canon
    return disc, doms, alias, dom_alias


def norm_token(value: str, alias: dict[str, str]) -> str:
    """Lowercase/strip a single label token and resolve it through the alias map."""
    tok = (value or "").strip().strip('"').strip().lower()
    return alias.get(tok, tok)


def read_sheet(path: Path) -> list[dict]:
    """Read the adjudication sheet; keep raw cells so typos stay auditable."""
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.reader(fh))[1:]
    out = []
    for r in rows:
        if not r or not r[0].strip():
            continue
        out.append({
            "row": int(r[0]), "fb_id": r[1].strip(),
            "disc_raw": r[4], "dom_raw": r[5], "ct_raw": r[6],
            "note": (r[7] if len(r) > 7 else "").strip(),
        })
    return out


def cohen_kappa(pairs: list[tuple]) -> dict:
    """Nominal Cohen's kappa over (human, pipeline) pairs; None-labelled pairs excluded."""
    n = len(pairs)
    if n == 0:
        return {"n": 0, "po": None, "pe": None, "kappa": None}
    po = sum(1 for a, b in pairs if a == b) / n
    ca, cb = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in set(ca) | set(cb))
    kappa = (po - pe) / (1 - pe) if pe < 1 else None
    return {"n": n, "po": round(po, 4), "pe": round(pe, 4),
            "kappa": round(kappa, 4) if kappa is not None else None,
            "error_rate": round(1 - po, 4), "agrees": sum(1 for a, b in pairs if a == b)}


def domain_metrics(rows: list[dict], dom_vocab: list[str]) -> dict:
    """Micro-binary kappa over the domain vocabulary plus set-level agreement stats."""
    n = len(rows)
    cells = n * len(dom_vocab)
    both = neither = hpos = ppos = 0
    per_domain: dict[str, dict] = {}
    for dom in dom_vocab:
        a = sum(1 for r in rows if dom in r["doms"])
        b = sum(1 for r in rows if dom in r["pipeline_domains"])
        ab = sum(1 for r in rows if dom in r["doms"] and dom in r["pipeline_domains"])
        nn = sum(1 for r in rows if dom not in r["doms"] and dom not in r["pipeline_domains"])
        hpos += a
        ppos += b
        both += ab
        neither += nn
        if a or b:
            po_ = (ab + nn) / n
            ca, cb = a / n, b / n
            pe_ = ca * cb + (1 - ca) * (1 - cb)
            per_domain[dom] = {"human": a, "pipeline": b, "both": ab,
                               "kappa": round((po_ - pe_) / (1 - pe_), 3) if pe_ < 1 else None}
    po_m = (both + neither) / cells
    pe_m = (hpos / cells) * (ppos / cells) + (1 - hpos / cells) * (1 - ppos / cells)
    jac = [len(r["doms"] & r["pipeline_domains"]) / max(1, len(r["doms"] | r["pipeline_domains"]))
           for r in rows]
    return {
        "micro_kappa": round((po_m - pe_m) / (1 - pe_m), 4),
        "micro_po": round(po_m, 4), "micro_pe": round(pe_m, 4),
        "human_positives": hpos, "pipeline_positives": ppos, "both": both,
        "jaccard_micro": round(both / max(1, hpos + ppos - both), 4),
        "mean_jaccard": round(statistics.mean(jac), 4),
        "exact_set_match": sum(1 for r in rows if r["doms"] == r["pipeline_domains"]),
        "active_domains": len(per_domain),
        "macro_kappa_active": round(statistics.mean(v["kappa"] for v in per_domain.values()
                                                    if v["kappa"] is not None), 4),
        "per_domain": dict(sorted(per_domain.items(), key=lambda kv: -kv[1]["human"])),
    }


def main() -> int:
    """Compute per-axis agreement, write artifacts, print the headline block."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if a human label is out-of-vocabulary")
    args = ap.parse_args()

    disc_vocab, dom_vocab, alias, dom_alias = load_vocab()
    dom_list = sorted(dom_vocab)
    key = json.loads(KEY.read_text(encoding="utf-8"))["key"]
    sheet = read_sheet(SHEET)

    rows, invalid = [], []
    for r in sheet:
        disc = norm_token(r["disc_raw"], alias) or None
        doms = {norm_token(t, dom_alias) for t in r["dom_raw"].split(",") if t.strip().strip('"')}
        ct = norm_token(r["ct_raw"], {})
        p = key[r["fb_id"]]
        rows.append({"row": r["row"], "fb_id": r["fb_id"], "stratum": p["stratum"],
                     "max_contra": p.get("max_contra"), "disc": disc, "doms": doms, "ct": ct,
                     "pipeline_discipline": p["pipeline_discipline"],
                     "pipeline_domains": set(p["pipeline_domains"]),
                     "pipeline_content_type": p["pipeline_content_type"], "note": r["note"],
                     "raw": {"disc": r["disc_raw"], "doms": r["dom_raw"], "ct": r["ct_raw"]}})
        if disc and disc not in disc_vocab and disc not in ("emerging",):
            invalid.append({"row": r["row"], "axis": "discipline", "value": disc})
        for d in sorted(doms):
            if d not in dom_vocab and d not in ("emerging",):
                invalid.append({"row": r["row"], "axis": "domains", "value": d})

    report: dict = {"schema_version": "1.0", "sheet": "governance/" + SHEET.name,
                    "key": "governance/" + KEY.name, "n_rows": len(rows),
                    "out_of_vocab": invalid, "axes": {}}

    for axis in AXES:
        if axis == "domains":
            met = domain_metrics(rows, dom_list)
            for stratum in ("contra", "clean"):
                sub = [r for r in rows if r["stratum"] == stratum]
                sm = domain_metrics(sub, dom_list)
                met[stratum] = {k: v for k, v in sm.items() if k != "per_domain"}
            report["axes"][axis] = met
            continue
        def pick(r: dict, human: bool) -> str | None:
            if human:
                return r["disc"] if axis == "discipline" else r["ct"]
            return r["pipeline_discipline"] if axis == "discipline" else r["pipeline_content_type"]
        pairs = [(pick(r, True), pick(r, False)) for r in rows if pick(r, True) is not None]
        met = cohen_kappa(pairs)
        met["pipeline_distinct"] = len({b for _, b in pairs})
        met["human_distinct"] = len({a for a, _ in pairs})
        met["pipeline_marginal"] = dict(collections.Counter(b for _, b in pairs).most_common(8))
        met["human_marginal"] = dict(collections.Counter(a for a, _ in pairs).most_common(8))
        met["confusions"] = [{"human": a, "pipeline": b, "n": c} for (a, b), c in
                             collections.Counter((a, b) for a, b in pairs if a != b).most_common(10)]
        for stratum in ("contra", "clean"):
            sub = [(pick(r, True), pick(r, False)) for r in rows if r["stratum"] == stratum]
            met[stratum] = cohen_kappa([p for p in sub if p[0] is not None])
        report["axes"][axis] = met

    queue = []
    for r in rows:
        issues = []
        if r["disc"] and r["disc"] != r["pipeline_discipline"]:
            issues.append("discipline: human=" + str(r["disc"]) + " pipeline=" + str(r["pipeline_discipline"]))
        if r["doms"] != r["pipeline_domains"]:
            issues.append("domains: human_only=" + str(sorted(r["doms"] - r["pipeline_domains"])) +
                          " pipeline_only=" + str(sorted(r["pipeline_domains"] - r["doms"])))
        if issues:
            queue.append({"row": r["row"], "fb_id": r["fb_id"], "stratum": r["stratum"],
                          "max_contra": r["max_contra"], "issues": issues, "note": r["note"]})
    report["repair_queue"] = {"n": len(queue), "items": queue}

    OUT_JSON.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")

    a = report["axes"]
    lines = ["# ANCHOR-1 per-axis agreement (60-row R2 adjudication sheet)", "",
             "Sheet: " + report["sheet"] + "  vs  pipeline key: " + report["key"] +
             "  (n=" + str(report["n_rows"]) + ").",
             "D-275a: report chance-corrected agreement and error rate, never 'accuracy'.", "",
             "| axis | n | observed agree | error rate | Cohen kappa | contra kappa | clean kappa |",
             "|---|---|---|---|---|---|---|"]
    for axis in AXES:
        m = a[axis]
        if axis == "domains":
            lines.append("| domains (micro-binary, " + str(len(dom_list)) + " classes) | " +
                         str(report["n_rows"]) + " | " + str(m["micro_po"]) + " | " +
                         str(round(1 - m["micro_po"], 4)) + " | **" + str(m["micro_kappa"]) + "** | " +
                         str(m["contra"]["micro_kappa"]) + " | " + str(m["clean"]["micro_kappa"]) + " |")
        else:
            lines.append("| " + axis + " | " + str(m.get("n")) + " | " + str(m.get("po")) + " | " +
                         str(m.get("error_rate")) + " | **" + str(m.get("kappa")) + "** | " +
                         str(m.get("contra", {}).get("kappa")) + " | " + str(m.get("clean", {}).get("kappa")) + " |")
    d = a["domains"]
    lines += ["", "## Domain set agreement", "",
              "- mean Jaccard per row: **" + str(d["mean_jaccard"]) + "**; exact set match: **" +
              str(d["exact_set_match"]) + "/" + str(report["n_rows"]) + "**",
              "- human positives " + str(d["human_positives"]) + " vs pipeline " + str(d["pipeline_positives"]) +
              " (both " + str(d["both"]) + ")",
              "- macro kappa over " + str(d["active_domains"]) + " active domains: " + str(d["macro_kappa_active"]),
              "", "## Repair queue", "", str(len(queue)) + " rows disagree on at least one axis.", "",
              "| row | stratum | max_contra | issue |", "|---|---|---|---|"]
    for q in queue:
        lines.append("| " + str(q["row"]) + " | " + str(q["stratum"]) + " | " + str(q["max_contra"]) +
                     " | " + "; ".join(q["issues"]).replace("|", "/") + " |")
    if invalid:
        lines += ["", "## Out-of-vocabulary human tokens (normalisation debt)", ""] + \
                 ["- row " + str(i["row"]) + " [" + i["axis"] + "] '" + str(i["value"]) + "'" for i in invalid]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({k: {kk: vv for kk, vv in v.items() if not isinstance(vv, (dict, list))}
                      for k, v in a.items()}, indent=1))
    print("queue=" + str(len(queue)) + " out_of_vocab=" + str(len(invalid)) +
          " wrote " + OUT_JSON.name + " + " + OUT_MD.name)
    return 1 if (args.check and invalid) else 0


if __name__ == "__main__":
    raise SystemExit(main())
