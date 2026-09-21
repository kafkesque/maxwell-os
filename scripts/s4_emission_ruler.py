#!/usr/bin/env python3
"""D-325 A/B: does the ruled boundary block move S4 EMISSION on the frozen ANCHOR-2 ruler?

Two arms over the same 60 frozen rows, same model (S4 classifier, temp 0.0):
  baseline  = merged CRIBS+classify prompt WITHOUT the boundary block
  treatment = the same prompt WITH the ruled block (config/boundary_discriminators.yaml)
Measures, per arm: how many rows actually EMIT a canonical discipline (emission), out-of-vocab
count, and canonical agreement vs the human verdict (error rate, never "accuracy" — R2/D-275a).
Writes governance/anchor2_s4_emission_20260921.json.

Usage:
  python3 scripts/s4_emission_ruler.py [--limit N]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402


def load_aliases() -> dict[str, str]:
    """Return raw/canonical surface → canonical discipline/domain map from the taxonomy."""
    tax = yaml.safe_load((ROOT / "config" / "taxonomy_v5.yaml").read_text(encoding="utf-8"))
    alias: dict[str, str] = {}
    for coll in (tax["disciplines"], tax["domains"]):
        for e in coll:
            for raw in e.get("raw") or []:
                alias[raw.strip().lower()] = e["canonical"]
            alias[e["canonical"].strip().lower()] = e["canonical"]
    return alias


def canon(alias: dict[str, str], value: str) -> str | None:
    """Return the canonical slot for a label, or None when it is empty/parked/out-of-vocab."""
    v = (value or "").strip().lower()
    if not v or v in ("emerging", "none", "null", "unknown"):
        return None
    return alias.get(v)


def classify(row: dict, arm: str, cfg: dict, aliases: dict[str, str]) -> dict:
    """Classify one ruler row under one arm and return the per-row record."""
    from pipeline.stage4_merged_call import merged_cribs_classify
    fb = {"name": row["name"], "definition": row["definition"]}
    rec = {"row": int(row["row"]), "name": row["name"], "arm": arm,
           "human_raw": row.get("discipline_verdict", ""),
           "human_canon": canon(aliases, row.get("discipline_verdict", ""))}
    t0 = time.time()
    try:
        res = merged_cribs_classify(fb, max_tokens=int(cfg["max_tokens"]),
                                   timeout=int(cfg["timeout"]), boundary=(arm == "treatment"))
    except Exception as e:  # C16: record the failure, never hide it
        rec.update({"error": f"{type(e).__name__}: {e}", "emitted_raw": None,
                    "emitted_canon": None, "latency_s": round(time.time() - t0, 2)})
        return rec
    if isinstance(res, list):
        res = res[0] if res else {}
    raw = str((res or {}).get("discipline") or "").strip()
    c = canon(aliases, raw)
    rec.update({"emitted_raw": raw, "emitted_canon": c,
                "oov": bool(raw) and c is None,
                "match": bool(c) and c == rec["human_canon"],
                "latency_s": round(time.time() - t0, 2)})
    return rec


def summarise(recs: list[dict], arm: str) -> dict:
    """Compute the emission/agreement summary for one arm."""
    rows = [r for r in recs if r["arm"] == arm]
    ok = [r for r in rows if "error" not in r]
    emitted = [r for r in ok if r.get("emitted_canon")]
    return {"arm": arm, "n": len(rows), "errors": len(rows) - len(ok),
            "emitted_n": len(emitted),
            "emission_pct": round(100 * len(emitted) / max(len(ok), 1), 1),
            "oov_n": sum(1 for r in ok if r.get("oov")),
            "match_n": sum(1 for r in ok if r.get("match")),
            "error_rate": round(1 - sum(1 for r in ok if r.get("match")) / max(len(ok), 1), 4),
            "median_latency_s": round(sorted(r["latency_s"] for r in rows)[len(rows) // 2], 2) if rows else None}


def main() -> int:
    """Run both arms and write the measurement artifact."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    cfg = yaml.safe_load((ROOT / "config" / "s4_emission_ruler.yaml").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((ROOT / cfg["sheet"]).open(encoding="utf-8")))
    if args.limit:
        rows = rows[: args.limit]
    aliases = load_aliases()
    jobs = [(r, arm) for arm in cfg["arms"] for r in rows]
    with ThreadPoolExecutor(max_workers=int(cfg["max_workers"])) as ex:
        recs = list(ex.map(lambda j: classify(j[0], j[1], cfg, aliases), jobs))
    out = {"schema_version": "1.0", "decision": "D-325", "n_rows": len(rows),
           "model": _model(), "menu_hash": cfg.get("menu_hash"),
           "boundary_rules_sha256": hashlib.sha256(
               (ROOT / "config" / "boundary_discriminators.yaml").read_bytes()).hexdigest(),
           "summaries": {arm: summarise(recs, arm) for arm in cfg["arms"]},
           "rows": recs}
    dest = ROOT / cfg["output"]
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, indent=1), encoding="utf-8")
    tmp.replace(dest)
    for arm, s in out["summaries"].items():
        print(f"{arm:9s} emitted {s['emitted_n']}/{s['n']} ({s['emission_pct']}%) "
              f"error_rate {s['error_rate']} oov {s['oov_n']} errors {s['errors']} "
              f"median {s['median_latency_s']}s")
    flips = {(r["row"]) for r in recs if r["arm"] == "baseline" and r.get("match")} ^ set()
    affected = [r for r in recs if r.get("human_canon") == "behavioral economics"]
    print("BE rows:", json.dumps([{k: r.get(k) for k in
          ("row", "name", "arm", "human_raw", "emitted_raw", "emitted_canon", "match")}
          for r in affected], indent=0)[:600])
    print("wrote", cfg["output"])
    return 0


def _model() -> str:
    """Return the configured S4 classifier model name (C12: from config)."""
    from pipeline.pipeline_paths import VERIFY_MODEL
    return VERIFY_MODEL


if __name__ == "__main__":
    raise SystemExit(main())
