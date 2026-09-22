#!/usr/bin/env python3
"""F-11 decision sheet: the ruler's 150 rows with human + two LLM coders side by side, for owner adjudication.

One row per ruler row, with the source text (DEFINITION/APPLICATION/MECHANISM) and the three coders'
labels per axis, plus a verdict class per axis and a 'DECIDE FIRST' rank that puts the rows where BOTH
independent coders agree against the human at the top (the cheapest ontology decisions).

Read-only: writes governance/F11_DECISION_SHEET_<date>.csv. Config-driven (config/f11_llm_coder.yaml).
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import yaml  # noqa: E402
from f11_llm_coder import _canon  # noqa: E402
from pipeline.io_guard import safe_write  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
AXES = [("content_type", "CT (1-7)"), ("discipline", "DISC (1-62)"), ("extraction_type", "FORM (1-4)")]
TEXT = ["DEFINITION", "APPLICATION", "MECHANISM"]


def _jsonl(path: pathlib.Path) -> dict[str, dict]:
    """Parse a coder answer file (bare JSONL; a .md extension is tolerated)."""
    out: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("{"):
            o = json.loads(line)
            out[str(o["item_id"])] = o
    return out


def main(argv: list[str]) -> int:
    """Write the decision sheet; argv = coder_a coder_b (JSONL paths)."""
    if len(argv) != 3:
        print("usage: f11_decision_sheet.py <coder_a.jsonl> <coder_b.jsonl>", file=sys.stderr)
        return 2
    cfg = yaml.safe_load((ROOT / "config/f11_llm_coder.yaml").read_text(encoding="utf-8"))
    al = {_canon(a["as_written"], {}): _canon(a["canonical"], {}) for a in cfg["declared_aliases"]}
    a, b = (_jsonl(pathlib.Path(p)) for p in argv[1:3])
    rows = list(csv.DictReader((ROOT / cfg["sheet"]).open(encoding="utf-8")))
    out: list[dict] = []
    for r in rows:
        i = r["item_id"]
        rec = {"item_id": i, "name": r.get("name", ""), "DECIDE": 99}
        for ax, col in AXES:
            h, am, bm = (_canon(r[col].strip(), al), _canon(a.get(i, {}).get(ax, ""), al), _canon(b.get(i, {}).get(ax, ""), al))
            rec[f"human_{ax[:4]}"], rec[f"a_{ax[:4]}"], rec[f"b_{ax[:4]}"] = h, am, bm
            rec[f"class_{ax[:4]}"] = ("human BLANK" if not h else "unanimous" if h == am == bm else
                                      "CONSENSUS vs human" if am == bm else
                                      "3-way" if h not in (am, bm) else "model split")
        cons = sum(1 for ax, _ in AXES if rec[f"class_{ax[:4]}"] == "CONSENSUS vs human")
        rec["DECIDE"] = 0 if cons >= 2 else 1 if cons == 1 else 2 if any(rec[f"class_{ax[:4]}"] == "model split" for ax, _ in AXES) else 3
        for t in TEXT:
            rec[t] = (r.get(t, "") or "")[:400]
        out.append(rec)
    out.sort(key=lambda x: (x["DECIDE"], x["item_id"]))
    cols = ["item_id", "name", "DECIDE", "class_cont", "human_cont", "a_cont", "b_cont", "class_disc",
            "human_disc", "a_disc", "b_disc", "class_extra", "human_extra", "a_extra", "b_extra"] + TEXT
    path = ROOT / f"governance/F11_DECISION_SHEET_{time.strftime('%Y%m%d')}.csv"
    buf = [",".join(cols)] + [",".join('"' + str(r.get(c, "")).replace('"', "'") + '"' for c in cols) for r in out]
    safe_write(path, "\n".join(buf) + "\n", force_shrink=True)
    need = sum(1 for r in out if r["DECIDE"] == 0)
    print(f"✅ {path.relative_to(ROOT)}  ({len(out)} rows)")
    print(f"   DECIDE=0 (>=2 axes where BOTH coders agree vs the human): {need} rows")
    print(f"   DECIDE=1: {sum(1 for r in out if r['DECIDE']==1)} | DECIDE=2: {sum(1 for r in out if r['DECIDE']==2)} | "
          f"DECIDE=3 (all axes unanimous): {sum(1 for r in out if r['DECIDE']==3)}")
    print(f"   human-blank rows (BUG-363): {sum(1 for r in out if any(r[f'class_{ax[:4]}']=='human BLANK' for ax,_ in AXES))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
