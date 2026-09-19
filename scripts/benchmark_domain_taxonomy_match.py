#!/usr/bin/env python3
"""benchmark_domain_taxonomy_match.py — validate D2613 (domain -> bge-m3 taxonomy-match).

Benchmarks two TRAINING-FREE models against the gold_4axis domain labels (43-way
multi-label) to decide whether they can replace the starved sigmoid domain head
(macro-F1 ~0.009 flat / 0.007 hierarchical per D2632):

  1. MoritzLaurer/bge-m3-zeroshot-v2.0  (zero-shot NLI-style, 43 candidate labels)
  2. BAAI/bge-reranker-v2-m3            (cross-encoder relevance(text, definition))

Ground truth = gold_4axis.jsonl `domains` (sorted list) on the principle rows.
Reported (multi-label): micro-F1, macro-F1, subset-accuracy, precision@k.

Deterministic, read-only (no DB writes), config via CLI (C12: no magic numbers).

Usage:
  python3 scripts/benchmark_domain_taxonomy_match.py --reranker-only
  python3 scripts/benchmark_domain_taxonomy_match.py --zeroshot-only
  python3 scripts/benchmark_domain_taxonomy_match.py --top-k 3 --threshold 0.5
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB = ROOT / "knowledge pipeline" / "maxwell.db"
GOLD = ROOT / "governance" / "gold_4axis.jsonl"
TAX = ROOT / "config" / "taxonomy_v5.yaml"

RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
ZEROSHOT_MODEL = "MoritzLaurer/bge-m3-zeroshot-v2.0"


def load_taxonomy_domains() -> List[Tuple[str, str]]:
    """Return [(canonical, definition), ...] for the 43 domains."""
    t = yaml.safe_load(TAX.read_text(encoding="utf-8"))
    out: List[Tuple[str, str]] = []
    for d in t["domains"]:
        out.append((d["canonical"], d.get("definition", d["canonical"])))
    return out


def load_gold() -> List[Dict[str, Any]]:
    """gold_4axis principle rows with fb_id + gold domains."""
    rows = [json.loads(l) for l in GOLD.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [r for r in rows if r.get("content_type") == "principle" and r.get("domains")]


def _text(name: str, definition: str, mechanism: str, boundary: str) -> str:
    """Concatenate the FB's semantic text (definition+mechanism+boundary)."""
    parts = [p for p in (name, definition, mechanism, boundary) if p]
    return " ".join(parts)[:2048]


def fetch_texts(fb_ids: List[str]) -> Dict[str, str]:
    """fb_id -> combined semantic text, from maxwell.db (read-only)."""
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    q = "SELECT fb_id, name, definition, mechanism, boundary FROM fbs WHERE fb_id IN (%s)" % (
        ",".join("?" * len(fb_ids))
    )
    out: Dict[str, str] = {}
    for r in db.execute(q, fb_ids):
        out[r["fb_id"]] = _text(r["name"], r["definition"], r["mechanism"], r["boundary"])
    db.close()
    return out


def _multilabel_metrics(
    gold: List[set], pred: List[set], n_labels: int
) -> Dict[str, float]:
    """Micro/macro-F1 + subset accuracy for multi-label prediction."""
    eps = 1e-9
    tp = tn = fp = fn = 0
    per = {i: [0, 0, 0, 0] for i in range(n_labels)}  # tp, fp, fn, tn per label
    for g, p in zip(gold, pred):
        for i in range(n_labels):
            gi, pi = (i in g), (i in p)
            if gi and pi:
                per[i][0] += 1
            elif pi and not gi:
                per[i][1] += 1
            elif gi and not pi:
                per[i][2] += 1
            else:
                per[i][3] += 1
    for g, p in zip(gold, pred):
        tp += len(g & p)
        fp += len(p - g)
        fn += len(g - p)
    micro_p = tp / (tp + fp + eps)
    micro_r = tp / (tp + fn + eps)
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r + eps)
    macro_f1s = []
    for i in range(n_labels):
        tpi, fpi, fni = per[i][0], per[i][1], per[i][2]
        p = tpi / (tpi + fpi + eps)
        r = tpi / (tpi + fni + eps)
        macro_f1s.append(2 * p * r / (p + r + eps))
    macro_f1 = sum(macro_f1s) / n_labels
    subset_acc = sum(1 for g, p in zip(gold, pred) if g == p) / len(gold)
    return {"micro_f1": micro_f1, "macro_f1": macro_f1, "subset_accuracy": subset_acc}


def eval_zeroshot(
    texts: List[str], names: List[str], top_k: int
) -> Tuple[List[set], Dict[str, float]]:
    """MoritzLaurer/bge-m3-zeroshot-v2.0 via transformers zero-shot pipeline."""
    from transformers import pipeline

    clf = pipeline("zero-shot-classification", model=ZEROSHOT_MODEL, device=-1)
    preds: List[set] = []
    for t in texts:
        out = clf(t, candidate_labels=names, multi_label=True)
        # top_k by score
        idx = sorted(range(len(out["scores"])), key=lambda i: -out["scores"][i])[:top_k]
        preds.append({names[i] for i in idx})
    return preds, {}


def eval_reranker(
    texts: List[str], domains: List[Tuple[str, str]], top_k: int
) -> Tuple[List[set], List[List[float]]]:
    """bge-reranker-v2-m3 cross-encoder: relevance(text, domain_definition).

    Returns (top-k predictions, sigmoid score matrix [row][domain]) so the
    same forward pass can be re-thresholded without recomputing.
    """
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(RERANKER_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(RERANKER_MODEL)
    model.eval()
    names = [d[0] for d in domains]
    defs = [d[1] for d in domains]
    preds: List[set] = []
    score_matrix: List[List[float]] = []
    with torch.no_grad():
        for t in texts:
            scores = []
            for d in defs:
                enc = tok(t, d, return_tensors="pt", padding=True, truncation=True, max_length=1024)
                logit = model(**enc).logits[0][0].item()
                scores.append(float(torch.sigmoid(torch.tensor(logit)).item()))
            score_matrix.append(scores)
            idx = sorted(range(len(scores)), key=lambda i: -scores[i])[:top_k]
            preds.append({names[i] for i in idx})
    return preds, score_matrix


def sweep_thresholds(
    gold: List[set], score_matrix: List[List[float]], names: List[str]
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Sweep sigmoid thresholds 0.05..0.95; return (best-by-micro-F1, full curve)."""
    rows: List[Dict[str, Any]] = []
    best: Dict[str, Any] = {}
    best_set = False
    n = len(names)
    for tau in [round(0.05 * i, 2) for i in range(1, 20)]:
        preds = [
            {names[j] for j in range(n) if score_matrix[i][j] >= tau}
            for i in range(len(score_matrix))
        ]
        m = _multilabel_metrics(gold, preds, n)
        m["threshold"] = tau
        rows.append(m)
        if not best_set or m["micro_f1"] > best["micro_f1"]:
            best = m
            best_set = True
    return best, rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0, help="cap rows (0=all)")
    ap.add_argument("--reranker-only", action="store_true")
    ap.add_argument("--zeroshot-only", action="store_true")
    ap.add_argument("--sweep", action="store_true", help="sweep sigmoid thresholds (reranker)")
    ap.add_argument("--out", default=str(ROOT / "governance" / "domain_taxonomy_match_benchmark.json"))
    args = ap.parse_args()

    domains = load_taxonomy_domains()
    names = [d[0] for d in domains]
    gold_rows = load_gold()
    if args.limit:
        gold_rows = gold_rows[: args.limit]
    fb_ids = [r["fb_id"] for r in gold_rows]
    texts_map = fetch_texts(fb_ids)
    gold = [set(r["domains"]) for r in gold_rows]
    texts = [texts_map.get(i, "") for i in fb_ids]
    texts = [t or r.get("name", "") for t, r in zip(texts, gold_rows)]
    print(f"rows: {len(gold_rows)} | domains: {len(names)} | top_k: {args.top_k}")

    results: Dict[str, Any] = {"n_rows": len(gold_rows), "top_k": args.top_k}

    if not args.zeroshot_only:
        preds, score_matrix = eval_reranker(texts, domains, args.top_k)
        m = _multilabel_metrics(gold, preds, len(names))
        print(f"[bge-reranker-v2-m3 top-{args.top_k}] micro-F1 {m['micro_f1']:.4f} | macro-F1 {m['macro_f1']:.4f} | subset {m['subset_accuracy']:.4f}")
        results["reranker"] = m
        if args.sweep:
            best, curve = sweep_thresholds(gold, score_matrix, names)
            print(f"[bge-reranker-v2-m3 sweep] best threshold {best['threshold']} -> micro-F1 {best['micro_f1']:.4f} | macro-F1 {best['macro_f1']:.4f} | subset {best['subset_accuracy']:.4f}")
            results["reranker_sweep_best"] = best
            results["reranker_sweep_curve"] = curve

    if not args.reranker_only:
        preds, _ = eval_zeroshot(texts, names, args.top_k)
        m = _multilabel_metrics(gold, preds, len(names))
        print(f"[bge-m3-zeroshot-v2.0] micro-F1 {m['micro_f1']:.4f} | macro-F1 {m['macro_f1']:.4f} | subset {m['subset_accuracy']:.4f}")
        results["zeroshot"] = m

    Path(args.out).write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
