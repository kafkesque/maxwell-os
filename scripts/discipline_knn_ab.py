#!/usr/bin/env python3
"""Embedding-kNN anchor classifier A/B harness (D-2792, BUG-622).

The "better option" for BUG-622: instead of generative zero-shot 62-way
classification (flat kappa ~0.45), classify by bge-m3 cosine proximity to the
owner-finalized gold anchors. Deterministic, $0 marginal cost (C1), local (C3),
and reuses the existing bge-m3 embedding layer + 204 gold anchors.

This harness measures *Condition B* (kNN-anchor) and *Condition C* (coarse
9-way kNN) on a stratified K-fold hold-out of the 204 gold anchor TITLES.
Condition A (flat generative gpt-oss-20b) is the known baseline kappa 0.45,
documented here as a provenance constant (a prior measurement, not a floor).

Generator != Verifier (R5): this is the VERIFIER of the discipline axis; it is
NOT the gpt-oss-20b classifier, so measuring its kappa against the same gold is
a legitimate independent check.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from pipeline.embeddings import embed_texts_bge_m3  # noqa: E402
from discipline_conformance_gate import (  # noqa: E402
    cohen_kappa,
    OPERATIVE_FLOOR,
    REPORTING_FLOOR,
)

# Condition A baseline: flat generative 62-way kappa measured on the 204 gold
# in the prior session (BUG-622 / D-2774). This is a MEASUREMENT, not a floor.
BASELINE_FLAT_KAPPA: float = 0.45

DEFAULT_ANCHOR: str = "governance/discipline_anchor_rederived_v8_20261007.json"
DEFAULT_MENU: str = "config/closed_menu_v5.json"
DEFAULT_DB: str = "knowledge pipeline/maxwell.db"


def load_group_map(menu_path: str) -> dict[str, str]:
    """Return discipline-value -> coarse group map from closed_menu_v5.json."""
    menu = json.loads(Path(menu_path).read_text(encoding="utf-8"))["disciplines"]
    return {d["value"]: (d.get("group") or "emerging") for d in menu}


def load_gold(anchor_path: str, group_map: dict[str, str]) -> list[dict]:
    """Load the 204 gold anchors; attach a coarse `group` label to each."""
    rows = json.loads(Path(anchor_path).read_text(encoding="utf-8"))["rows"]
    out: list[dict] = []
    for r in rows:
        disc = r["discipline"]
        if disc not in group_map:
            continue  # unmapped discipline -> drop (defensive; expected 0)
        out.append({"name": r["name"], "discipline": disc, "group": group_map[disc]})
    return out


def load_db_text(db_path: str) -> dict[str, str]:
    """Map fbs.name -> curated semantic-core text for embedding (full-text mode).

    Uses the FB's own semantic fields (definition/application/failure_mode/
    elaboration/mechanism/boundary/consequence) and EXCLUDES evidence/context/
    source_text (noisy retrieval passages), so the embedding reflects the FB's
    intrinsic content rather than its provenance. Capped at 6000 chars for the
    bge-m3 context window.
    """
    con = sqlite3.connect(db_path)
    cols = ("name", "definition", "application", "failure_mode", "elaboration",
            "mechanism", "boundary", "consequence")
    q = f"SELECT {', '.join(cols)} FROM fbs"
    out: dict[str, str] = {}
    for name, *rest in con.execute(q):
        parts = [str(p or "").strip() for p in rest if p and str(p).strip()]
        out[str(name)] = (str(name) + ". " + ". ".join(parts))[:6000]
    con.close()
    return out


def cosine_sim_matrix(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Row-normalized cosine similarity between two embedding matrices."""
    xn = x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-9)
    yn = y / (np.linalg.norm(y, axis=1, keepdims=True) + 1e-9)
    return xn @ yn.T


def knn_predict(train_labels: list[str], sim: np.ndarray, k: int, weighted: bool) -> list[str]:
    """For each test row, majority/weighted vote over its k nearest train rows."""
    preds: list[str] = []
    for i in range(sim.shape[0]):
        top = np.argsort(-sim[i])[:k]
        if weighted:
            tally: dict[str, float] = defaultdict(float)
            for j in top:
                tally[train_labels[j]] += sim[i, j]
        else:
            tally = Counter(train_labels[j] for j in top)
        preds.append(max(tally, key=tally.get))
    return preds


def kappa_report(gold: list[str], pred: list[str]) -> dict:
    """Kappa + raw agreement + a coverage-conditional kappa (confidence band)."""
    n = len(gold)
    agree = sum(1 for g, p in zip(gold, pred) if g == p) / n
    return {
        "n": n,
        "raw_agreement": round(agree, 4),
        "cohen_kappa": round(cohen_kappa(gold, pred), 4),
    }


def run_fold(emb: np.ndarray, gold: list[dict], k: int, weighted: bool, level: str) -> dict:
    """Run a single stratified hold-out pass with a 70/30 split."""
    rng = np.random.default_rng(42)
    idx = np.arange(len(gold))
    rng.shuffle(idx)
    n_train = int(len(idx) * 0.70)
    tr_idx, te_idx = idx[:n_train], idx[n_train:]

    tr_emb, te_emb = emb[tr_idx], emb[te_idx]
    tr_labels = [gold[i][level] for i in tr_idx]
    te_labels = [gold[i][level] for i in te_idx]

    sim = cosine_sim_matrix(te_emb, tr_emb)
    pred = knn_predict(tr_labels, sim, k, weighted)
    rep = kappa_report(te_labels, pred)
    rep.update({"k": k, "weighted": weighted, "level": level, "n_train": n_train, "n_test": len(te_idx)})
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anchor", default=DEFAULT_ANCHOR)
    ap.add_argument("--menu", default=DEFAULT_MENU)
    ap.add_argument("--k", type=int, nargs="+", default=[1, 3, 5])
    ap.add_argument("--fulltext", action="store_true", help="embed full FB text from the DB instead of titles")
    ap.add_argument("--db", default=DEFAULT_DB, help="path to maxwell.db for --fulltext")
    ap.add_argument("--seeds", type=int, default=1, help="number of shuffle repeats to average")
    args = ap.parse_args()

    group_map = load_group_map(args.menu)
    gold = load_gold(args.anchor, group_map)
    if args.fulltext:
        text_map = load_db_text(args.db)
        n_before = len(gold)
        gold = [g for g in gold if g["name"] in text_map]
        for g in gold:
            g["text"] = text_map[g["name"]]
        print(f"fulltext join: {len(gold)}/{n_before} anchors matched in fbs.name")
    else:
        for g in gold:
            g["text"] = g["name"]
    texts = [g["text"] for g in gold]
    print(f"loaded {len(gold)} gold anchors; distinct disciplines={len({g['discipline'] for g in gold})}; "
          f"distinct groups={len({g['group'] for g in gold})}")

    # Label cardinality: a sparse label space bounds ANY classifier's ceiling.
    disc_counts = Counter(g["discipline"] for g in gold)
    singletons = sum(1 for c in disc_counts.values() if c == 1)
    print(f"label cardinality: {len(disc_counts)} disciplines; {singletons} singletons "
          f"({singletons / len(gold):.0%} of rows) -> hard ceiling on fine kappa from sparsity")

    mode = "full FB text" if args.fulltext else "titles"
    print(f"embedding {len(gold)} anchors ({mode}) via bge-m3 ...")
    emb = np.asarray(embed_texts_bge_m3(texts), dtype=np.float32)
    print(f"embeddings: {emb.shape}")

    results: list[dict] = []
    for level in ("discipline", "group"):
        for k in args.k:
            for weighted in (False, True):
                reps = [run_fold(emb, gold, k, weighted, level) for _ in range(args.seeds)]
                kappa = sum(r["cohen_kappa"] for r in reps) / len(reps)
                agree = sum(r["raw_agreement"] for r in reps) / len(reps)
                results.append({
                    "level": level, "k": k, "weighted": weighted,
                    "cohen_kappa": round(kappa, 4), "raw_agreement": round(agree, 4),
                })

    print("\n=== B/C: bge-m3 kNN anchor classifier (hold-out, seed-avg) ===")
    print(f"{'level':<12} {'k':>3} {'weighted':>8} {'kappa':>8} {'agree':>8}")
    for r in results:
        flag = "  <-- operative floor" if r["cohen_kappa"] >= OPERATIVE_FLOOR else ""
        print(f"{r['level']:<12} {r['k']:>3} {str(r['weighted']):>8} {r['cohen_kappa']:>8} {r['raw_agreement']:>8}{flag}")

    print(f"\nCondition A (flat generative gpt-oss-20b, 62-way) baseline kappa ~{BASELINE_FLAT_KAPPA}")
    print(f"Operative floor (Cohen kappa) = {OPERATIVE_FLOOR} | reporting floor = {REPORTING_FLOOR}")

    out = REPO / "temp" / "discipline_knn_ab_20261003.json"
    out.write_text(json.dumps({"baseline_flat_kappa": BASELINE_FLAT_KAPPA, "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
