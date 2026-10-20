#!/usr/bin/env python3
"""build_reanchor_candidates.py — semantic candidates for the BUG-956 re-anchor (D-3116 option 1).

WHY. The 208-row bridge ruler joins the store by CONTENT NAME (collapse_whitespace, D-2658). After the
corpus was re-segmented into the single canonical run rechunk-v4-20260929 (7,640 fbs), 195 of the 208
anchor labels no longer byte-match ANY store name, so `build_anchor_store_bridge.py` re-derives to DRIFT
(195 UNDECLARED unresolved). A mechanical nearest-name re-key would corrupt the anchor (best word-overlap
Jaccard ~0.14 = the WRONG concepts), so option 1 is an OWNER blind-sheet re-adjudication: for each dangling
concept, the owner rules which store row now carries that concept. This script makes that ruling FEASIBLE
by ranking the store's 7,640 names against each dangling label by bge-m3 cosine (512d Matryoshka) and
emitting a fillable sheet. The ranking is ADVISORY ONLY — it never picks (R5 / D-2898: no LLM auto-applies
a promotion; the owner's ruling is authoritative).

WHAT IT PRODUCES. `governance/ANCHOR_208_REANCHOR_CANDIDATES_<date>.csv` — one row per dangling concept:
(item_id, ruler_name, best_cos, then cand1..K as name/fb_id/cos triplets, then blank owner_ruling_fb_id and
owner_ruling_note). The owner fills owner_ruling_fb_id with a chosen candidate's fb_id, or NONE (no store
row carries the concept any longer), and may leave a note. This script writes NO store value and never edits
the ruler — it only RANKS.

FAIL-VISIBLE. The embedding service is `pipeline.embeddings.embed_texts_bge_m3` (C12: model + endpoint from
config). A missing endpoint raises; the script exits non-zero rather than emitting a half-ranked sheet.
Crash-safe write (C6).

Usage:
    python3 scripts/build_reanchor_candidates.py [--top-k 5]
"""
from __future__ import annotations

import argparse
import csv
import os
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from pipeline.embeddings import embed_texts_bge_m3  # noqa: E402

REGISTRY = ROOT / "config" / "anchor_family.yaml"
TOP_K = 5


def _collapse(value: str) -> str:
    """collapse_whitespace — the SAME normalization the store bridge declares (D-2658)."""
    return " ".join((value or "").split()).casefold()


def load_config() -> dict:
    """Return the store_bridge block (C12: no path or rule lives in this file)."""
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    cfg = (data or {}).get("store_bridge")
    if not isinstance(cfg, dict):
        raise SystemExit(f"{REGISTRY} carries no store_bridge block")
    return cfg


def read_ruler(cfg: dict) -> list[dict[str, str]]:
    """Read the 208-row bridge ruler (utf-8-sig, the declared encoding)."""
    with open(ROOT / cfg["ruler_sheet"], newline="", encoding=cfg["ruler_encoding"]) as fh:
        return [r for r in csv.DictReader(fh) if (r.get(cfg["item_key"]) or "").strip()]


def read_store(cfg: dict) -> tuple[list[str], dict[str, str]]:
    """Return (store_raw_names, fb_id_of_name). READ-ONLY over the live corpus."""
    con = sqlite3.connect(f"file:{ROOT / cfg['store']}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    names: list[str] = []
    fb_of_name: dict[str, str] = {}
    try:
        sql = f'SELECT {cfg["store_key"]}, {cfg["store_name_column"]} FROM {cfg["store_table"]}'
        for r in con.execute(sql):
            fid = str(r[cfg["store_key"]]).strip()
            raw = str(r[cfg["store_name_column"]] or "").strip()
            if not raw:
                continue
            names.append(raw)
            fb_of_name.setdefault(raw, fid)  # first fb_id wins for display; dup count reported separately
    finally:
        con.close()
    return names, fb_of_name


def build(cfg: dict, top_k: int) -> tuple[list[dict[str, str]], dict[str, int], list[str]]:
    """Return (rows, dup_name_counts, problems): the fillable candidate sheet + diagnostics."""
    ruler = read_ruler(cfg)
    store_names, fb_of_name = read_store(cfg)

    # Dangling = a ruler label with no collapse_whitespace match in the store name index.
    store_index: dict[str, list[str]] = {}
    for raw in store_names:
        store_index.setdefault(_collapse(raw), []).append(raw)
    dangling = [r for r in ruler if not store_index.get(_collapse((r.get("name") or "").strip()))]

    dup_name_counts = {raw: 0 for raw in store_names}
    for raw in store_names:
        dup_name_counts[raw] += 1

    if not dangling:
        return [], dup_name_counts, ["no dangling rows found (the bridge would already be clean)"]

    # Dedup store names for embedding (a duplicated name embeds once), keep the mapping for display.
    uniq = sorted({raw for raw in store_names})
    uniq_index = {raw: i for i, raw in enumerate(uniq)}

    print(f"embedding {len(dangling)} dangling labels + {len(uniq)} unique store names (bge-m3) ...",
          file=sys.stderr)
    store_embs = embed_texts_bge_m3(uniq)
    label_embs = embed_texts_bge_m3([(r.get("name") or "").strip() for r in dangling])
    # embed_texts_bge_m3 returns L2-normalised rows, so dot product == cosine.

    sims = label_embs @ store_embs.T  # (D x U) cosine matrix
    order = np.argsort(-sims, axis=1)[:, :top_k]  # per row, top_k indices, descending

    rows: list[dict[str, str]] = []
    for d, r in enumerate(dangling):
        item = (r.get(cfg["item_key"]) or "").strip()
        name = (r.get("name") or "").strip()
        row: dict[str, str] = {"item_id": item, "ruler_name": name}
        best = float(sims[d, order[d, 0]])
        row["best_cos"] = f"{best:.3f}"
        for k in range(top_k):
            u = int(order[d, k])
            cname = uniq[u]
            cid = fb_of_name[cname]
            cos = float(sims[d, u])
            if dup_name_counts[cname] > 1:
                cname = f"{cname} [x{dup_name_counts[cname]}]"
            row[f"cand{k + 1}_name"] = cname
            row[f"cand{k + 1}_fb_id"] = cid
            row[f"cand{k + 1}_cos"] = f"{cos:.3f}"
        row["owner_ruling_fb_id"] = ""
        row["owner_ruling_note"] = ""
        rows.append(row)

    return rows, dup_name_counts, []


def write_csv(path: Path, rows: list[dict[str, str]], top_k: int) -> None:
    """Crash-safe write (C6): tempfile -> fsync -> os.replace."""
    fieldnames = ["item_id", "ruler_name", "best_cos"]
    for k in range(1, top_k + 1):
        fieldnames += [f"cand{k}_name", f"cand{k}_fb_id", f"cand{k}_cos"]
    fieldnames += ["owner_ruling_fb_id", "owner_ruling_note"]
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".reanchor_candidates_", suffix=".tmp")
    try:
        with open(fd, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description="semantic re-anchor candidates (BUG-956 option 1)")
    ap.add_argument("--top-k", type=int, default=TOP_K, help="candidates per dangling concept")
    args = ap.parse_args()

    cfg = load_config()
    rows, dup_counts, problems = build(cfg, args.top_k)
    if problems:
        raise SystemExit("FAIL-CLOSED: " + "; ".join(problems))

    out = ROOT / "governance" / f"ANCHOR_208_REANCHOR_CANDIDATES_{datetime.now():%Y%m%d}.csv"
    write_csv(out, rows, args.top_k)

    bests = np.array([float(r["best_cos"]) for r in rows])
    dup_names = [n for n, c in dup_counts.items() if c > 1]
    print(f"wrote {out.name}: {len(rows)} dangling concepts x {args.top_k} candidates")
    print(f"best_cos distribution: >=0.8 {int((bests >= 0.8).sum())} | "
          f"0.7-0.8 {int(((bests >= 0.7) & (bests < 0.8)).sum())} | "
          f"0.6-0.7 {int(((bests >= 0.6) & (bests < 0.7)).sum())} | "
          f"0.5-0.6 {int(((bests >= 0.5) & (bests < 0.6)).sum())} | "
          f"<0.5 {int((bests < 0.5).sum())}")
    print(f"store names duplicated across fbs: {len(dup_names)} (marked [xN] in candidates; "
          f"a duplicated chosen name stays AMBIGUOUS to the bridge, D-2658)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
