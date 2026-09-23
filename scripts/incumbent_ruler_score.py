#!/usr/bin/env python3
"""scripts/incumbent_ruler_score.py - score the INCUMBENT store labels on the current ruler.

Answers one question: has the incumbent labeler been measured against the ruler as it
stands today, and how does that compare with the number quoted from ANCHOR-1?

Deterministic, no LLM (C1). Fail-closed (C16): refuses to publish a verdict if the ruler
shrinks below min_joined_rows, if a ruler row joins no FB, or if a reference column is
missing. C12: every path/column/axis/threshold lives in config/incumbent_ruler_score.yaml.
D-337: RELATIVE only. BUG-342: the stored reference is quoted, never re-derived.
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CFG_PATH = ROOT / "config" / "incumbent_ruler_score.yaml"
_CANON = re.compile(r"[^a-z0-9]+")


def load_cfg() -> dict:
    """Load the scoring configuration (C12)."""
    return yaml.safe_load(CFG_PATH.read_text())


def canon(text: str) -> str:
    """Canonicalise a label for comparison (snake_case, spaces and case are noise)."""
    return _CANON.sub("", str(text).lower())


def norm_name(text: str) -> str:
    """Normalise an item name so the ruler joins the store (same rule as the k-NN arm)."""
    return " ".join(str(text).lower().replace("\u2019", "'").split())


def load_store(cfg: dict) -> dict[str, dict]:
    """name -> {axis: raw label} from the fbs table (read-only)."""
    conn = sqlite3.connect(f"file:{ROOT / cfg['db']}?mode=ro", uri=True)
    axes = cfg["axes"]
    sel = ", ".join([cfg["join_key_store"]] + [cfg["store_column"].format(axis=a) for a in axes])
    out: dict[str, dict] = {}
    for row in conn.execute(f"SELECT {sel} FROM fbs"):
        if not row[0]:
            continue
        out[norm_name(row[0])] = {a: row[1 + i] for i, a in enumerate(axes)}
    conn.close()
    return out


def score_axis(cfg: dict, ruler: list[dict], store: dict[str, dict], axis: str) -> dict:
    """Agreement of the stored label with the previous and the current ruler reference."""
    prev_col = cfg["reference_previous_column"].format(axis=axis)
    cur_col = cfg["reference_current_column"].format(axis=axis)
    unmatched = missing_prev = missing_cur = 0
    hit_prev = hit_cur = n_prev = n_cur = 0
    for row in ruler:
        meta = store.get(norm_name(row.get(cfg["join_key_ruler"], "")))
        if meta is None:
            unmatched += 1
            continue
        got = meta.get(axis)
        prev = (row.get(prev_col) or "").strip()
        cur = (row.get(cur_col) or "").strip()
        if not prev:
            missing_prev += 1
        else:
            n_prev += 1
            hit_prev += int(canon(got) == canon(prev))
        if not cur:
            missing_cur += 1
        else:
            n_cur += 1
            hit_cur += int(canon(got) == canon(cur))
    if unmatched:
        raise SystemExit(f"{axis}: {unmatched} ruler rows joined no FB - refusing (C16)")
    if n_cur < cfg["min_joined_rows"]:
        raise SystemExit(f"{axis}: only {n_cur} scorable rows - refusing (C16)")
    return {
        "n_ruler": len(ruler),
        "n_scored_previous": n_prev,
        "n_scored_current": n_cur,
        "blank_previous": missing_prev,
        "blank_current": missing_cur,
        "agreement_previous_ruler": round(hit_prev / n_prev, 4) if n_prev else None,
        "agreement_current_ruler": round(hit_cur / n_cur, 4) if n_cur else None,
        "delta_current_minus_previous_pp": (
            round((hit_cur / n_cur - hit_prev / n_prev) * 100, 2) if n_prev and n_cur else None),
    }


def main() -> int:
    """CLI entry point."""
    cfg = load_cfg()
    ruler = list(csv.DictReader((ROOT / cfg["ruler"]).open(encoding="utf-8")))
    for col in (cfg["reference_previous_column"], cfg["reference_current_column"]):
        if col.format(axis=cfg["axes"][0]) not in ruler[0]:
            raise SystemExit(f"ruler is missing column {col} - refusing (C16)")
    store = load_store(cfg)
    out = {"schema_version": cfg["schema_version"], "decision": cfg["decision"],
           "ruler": cfg["ruler"], "n_ruler_rows": len(ruler), "n_store_rows": len(store),
           "axes": {a: score_axis(cfg, ruler, store, a) for a in cfg["axes"]},
           "incumbent_reference_quoted": cfg["incumbent_reference"],
           "qualifier": cfg["qualifier"]}
    (ROOT / cfg["output_json"]).write_text(json.dumps(out, indent=2))
    for axis, r in out["axes"].items():
        print(f"{axis:16s} prev={r['agreement_previous_ruler']} (n={r['n_scored_previous']})"
              f"  current={r['agreement_current_ruler']} (n={r['n_scored_current']})"
              f"  delta={r['delta_current_minus_previous_pp']} pp")
    print(f"written: {cfg['output_json']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
