#!/usr/bin/env python3
"""scripts/knn_arm_eval.py - rank a k-NN label arm against the incumbent on the frozen ruler.

D-337: RELATIVE only. D2575: k-NN measures representation separability, NOT label correctness,
so a win here is a licence to build a calibrated arm, never an accuracy claim. D-343 routed
discipline/domains to `classify` on exactly this representation; this script asks the next
question - does that representation BEAT the incumbent labeler on the ruler rows?

Fail-closed (C16): refuses to report if the vector store is inconsistent, if a ruler row maps to
no FB, or if a prediction is a tie (a tie is counted as a miss, never as a win).
"""
from __future__ import annotations

import csv
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
CFG_PATH = ROOT / "config" / "knn_arm.yaml"


def load_cfg() -> dict:
    """Load the arm configuration (C12: no path, k, axis or threshold is hardcoded)."""
    return yaml.safe_load(CFG_PATH.read_text())


def load_vectors(cfg: dict) -> tuple[list[int], np.ndarray]:
    """Rebuild the vec0 shadow storage into (fbs_rowids, L2-normalised matrix)."""
    conn = sqlite3.connect(f"file:{ROOT / cfg['db']}?mode=ro", uri=True)
    dim = cfg["dim"]
    cache: dict[int, np.ndarray] = {}

    def chunk_flat(cid: int) -> np.ndarray:
        """Load a shadow chunk once; chunk_offset indexes VECTORS inside it (not bytes)."""
        if cid not in cache:
            row = conn.execute(
                f"SELECT vectors FROM {cfg['vec_shadow_chunks']} WHERE rowid = ?", (cid,)).fetchone()
            if not row or not row[0]:
                raise SystemExit(f"shadow chunk {cid} unreadable - store inconsistent (C16)")
            cache[cid] = np.frombuffer(row[0], dtype=np.float32)
        return cache[cid]

    rowids, rows = [], []
    seen: set[int] = set()
    for rid, cid, off in conn.execute(
            f"SELECT rowid, chunk_id, chunk_offset FROM {cfg['vec_shadow_rowids']}"):
        if rid in seen:
            raise SystemExit(f"duplicate vec rowid {rid} - refusing to report (C16)")
        seen.add(rid)
        vec = chunk_flat(cid)[off * dim:(off + 1) * dim]
        if vec.size != dim:
            raise SystemExit(f"vector {rid} short in chunk {cid}@{off} - store inconsistent (C16)")
        rowids.append(rid)
        rows.append(vec)
    conn.close()
    mat = np.stack(rows).astype(np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    return rowids, mat / np.maximum(norms, 1e-12)


def load_meta(cfg: dict) -> dict[int, dict]:
    """rowid -> FB metadata for the ruler axes."""
    conn = sqlite3.connect(f"file:{ROOT / cfg['db']}?mode=ro", uri=True)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(fbs)")}
    name_col = "name" if "name" in cols else "title"
    wanted = ["rowid", "fb_id", name_col] + list(cfg["axes"])
    sel = ", ".join(wanted)
    meta = {r[0]: {"fb_id": r[1], "name": r[2], "labels": dict(zip(cfg["axes"], r[3:]))}
            for r in conn.execute(f"SELECT {sel} FROM fbs")}
    conn.close()
    return meta


def norm(text: str) -> str:
    """Normalise an item name for joining the ruler to the store."""
    return " ".join(str(text).lower().replace("’", "'").split())


def evaluate(cfg: dict, rowids: list[int], mat: np.ndarray, meta: dict[int, dict]) -> dict:
    """Compute k-NN agreement per axis on the ruler rows, with the constant baseline."""
    index = {rid: i for i, rid in enumerate(rowids)}
    by_name = {norm(m["name"]): rid for rid, m in meta.items() if m["name"]}
    ruler = list(csv.DictReader((ROOT / cfg["ruler"]).open()))
    k = cfg["k"]
    out: dict = {"n_ruler": len(ruler), "axes": {}, "qualifier": cfg["qualifier"]}
    for axis in cfg["axes"]:
        hit = miss = tie = unmatched = 0
        verdicts: list[str] = []
        for row in ruler:
            verdict = (row.get(cfg["ruler_verdict_column"].format(axis=axis)) or "").strip() \
                or (row.get(cfg["ruler_label_column"].format(axis=axis)) or "").strip()
            rid = by_name.get(norm(row.get("name", "")))
            if rid is None or rid not in index:
                unmatched += 1
                continue
            verdicts.append(verdict)
            i = index[rid]
            sims = mat @ mat[i]
            sims[i] = -2.0
            top = np.argpartition(-sims, k)[:k]
            votes = Counter(meta[rowids[j]]["labels"].get(axis) or "" for j in top)
            best = votes.most_common()
            if len(best) > 1 and best[0][1] == best[1][1]:
                tie += 1
                continue
            if best[0][0] == verdict:
                hit += 1
            else:
                miss += 1
        scored = hit + miss + tie
        if scored == 0:
            raise SystemExit(f"axis {axis}: no ruler row joined the store - refusing (C16)")
        const = Counter(v for v in verdicts if v).most_common(1)[0]
        knn = hit / scored
        inc = cfg["incumbent_agreement"][axis]
        out["axes"][axis] = {
            "n_scored": scored, "unmatched_ruler_rows": unmatched, "ties_counted_as_miss": tie,
            "knn_agreement": round(knn, 4),
            "constant_agreement": round(const[1] / scored, 4), "constant_label": const[0],
            "incumbent_agreement_stored": inc,
            "delta_vs_incumbent_pp": round((knn - inc) * 100, 2),
            "beats_incumbent": knn > inc,
        }
    return out


def main() -> int:
    """CLI entry point."""
    cfg = load_cfg()
    rowids, mat = load_vectors(cfg)
    meta = load_meta(cfg)
    if len(rowids) < cfg.get("min_rows", 1000):
        raise SystemExit("vector store too small - refusing (C16)")
    res = evaluate(cfg, rowids, mat, meta)
    res["store"] = {"vec_rows": len(rowids), "fbs_rows": len(meta), "dim": int(mat.shape[1]), "k": cfg["k"]}
    dest = ROOT / "governance" / "KNN_ARM_EVAL_20260923.json"
    dest.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    print(f"\nwritten: {dest.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
