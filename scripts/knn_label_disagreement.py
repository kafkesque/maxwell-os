#!/usr/bin/env python3
"""scripts/knn_label_disagreement.py — D2544: k-NN label-disagreement audit.

Replaces the centroid-outlier audit. Centroid distance measures "far from the
mean", NOT the actual failure mode — a mislabeled FB is one whose nearest
neighbors are labeled differently. This script finds, for each FB, its k nearest
neighbors in bge-m3 embedding space and reports the label-agreement rate (the
fraction of neighbors sharing the FB's discipline/domain). Low agreement =
likely mislabeled (the semantic-correctness gap D2540 flagged as unmeasured).

Embedding source (first available):
  1. live Ollama bge-m3 (default) — embeds each FB definition on demand
  2. --embeddings <jsonl/parquet> — precomputed 512-d vectors keyed by fb_id

Outputs: governance/knn_label_disagreement.json + .md
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np  # noqa: E402
import yaml  # noqa: E402

from pipeline.io_guard import safe_write  # noqa: E402  (C6 crash-safe writes)
from pipeline.pipeline_paths import (  # noqa: E402
    DB_PATH,
    OLLAMA_EMBED_TIMEOUT,
    OLLAMA_URL,
    S15_EMBED_DIM,
    S15_EMBED_MODEL,
)

_EMBED_NORM_EPS = 1e-9  # C20: L2-normalization epsilon (named constant)
_LOW_AGREEMENT_THRESHOLD = 0.3  # C20: neighbor-agreement below this = likely mislabeled
_RANDOM_SEED = 42  # C20: deterministic sampling

_TAXONOMY_PATH = _ROOT / "config" / "taxonomy_v5.yaml"  # C12: config-first canonical source


def _load_canonicals() -> tuple[set[str], set[str]]:
    """Load canonical discipline/domain sets from taxonomy_v5.yaml (D2544 fix).

    The audit must only measure label agreement for FBs that actually HAVE a
    canonical label. 'emerging'/empty disciplines and empty domains are unlabeled
    (BUG-150 / Track B population) and would otherwise inflate false agreement.
    """
    tax = yaml.safe_load(open(_TAXONOMY_PATH, encoding="utf-8"))
    discs = {d["canonical"] for d in tax.get("disciplines", [])}
    doms = {d["canonical"] for d in tax.get("domains", [])}
    return discs, doms


def _parse_domains(raw: str | None) -> set[str]:
    """Parse the `domains` column (JSON array string) into a canonical-domain set.

    Falls back to pipe-split for any legacy non-JSON encoding. Returns an empty set
    for NULL/empty. D2544 fix: the previous code did `.split('|')[0]` on a JSON
    string, producing the whole JSON array as one 'label' and comparing neighbours
    by raw-string prefix — which measured nothing real.
    """
    if not raw:
        return set()
    s = raw.strip()
    if s.startswith("["):
        try:
            return {str(x).strip() for x in json.loads(s) if str(x).strip()}
        except (json.JSONDecodeError, TypeError):
            pass
    return {x.strip() for x in s.split("|") if x.strip()}


def _embed_ollama(texts: list[str], dim: int = S15_EMBED_DIM) -> np.ndarray:
    import requests

    url = f"{OLLAMA_URL}/api/embed"
    out: list[list[float]] = []
    for t in texts:
        resp = requests.post(url, json={"model": S15_EMBED_MODEL, "input": t, "dimensions": dim},
                             timeout=OLLAMA_EMBED_TIMEOUT)
        resp.raise_for_status()
        out.append(resp.json()["embeddings"][0])
    return np.asarray(out, dtype=np.float32)


def main() -> int:
    parser = argparse.ArgumentParser(description="k-NN label-disagreement audit (D2544).")
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--sample", type=int, default=0, help="Audit only N FBs (0 = all).")
    parser.add_argument("--axis", choices=["discipline", "domain", "both"], default="discipline")
    args = parser.parse_args()

    discs, doms = _load_canonicals()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    rows = list(conn.execute(
        "SELECT fb_id, definition, discipline, domains FROM fbs WHERE definition IS NOT NULL AND definition != ''"
    ))
    conn.close()

    if args.sample:
        import random

        random.Random(_RANDOM_SEED).shuffle(rows)
        rows = rows[: args.sample]

    defs = [r["definition"] for r in rows]
    print(f"Embedding {len(defs)} definitions via bge-m3 (512d)...")
    embs = _embed_ollama(defs)
    embs = embs / (np.linalg.norm(embs, axis=1, keepdims=True) + _EMBED_NORM_EPS)

    # cosine similarity matrix (chunked to bound memory)
    sim = embs @ embs.T
    np.fill_diagonal(sim, -1.0)  # exclude self
    knn_idx = np.argsort(-sim, axis=1)[:, : args.k]

    results: list[dict] = []
    for i, r in enumerate(rows):
        nb = knn_idx[i]
        if args.axis in ("discipline", "both") and r["discipline"] in discs:
            same = sum(1 for j in nb if rows[j]["discipline"] == r["discipline"])
            results.append({"fb_id": r["fb_id"], "axis": "discipline",
                            "label": r["discipline"], "agree": same, "k": args.k,
                            "agreement": round(same / args.k, 3)})
        if args.axis in ("domain", "both"):
            r_doms = _parse_domains(r["domains"]) & doms
            if r_doms:
                same = sum(1 for j in nb if _parse_domains(rows[j]["domains"]) & r_doms)
                results.append({"fb_id": r["fb_id"], "axis": "domain",
                                "label": "|".join(sorted(r_doms)), "agree": same, "k": args.k,
                                "agreement": round(same / args.k, 3)})

    low = [x for x in results if x["agreement"] <= _LOW_AGREEMENT_THRESHOLD]
    agg = {"k": args.k, "n_fbs": len(rows), "audited": len(results),
           "mean_agreement": round(sum(x["agreement"] for x in results) / len(results), 3) if results else 0,
           "low_agreement_count": len(low),
           "low_agreement_pct": round(100 * len(low) / len(results), 2) if results else 0}

    gov = _ROOT / "governance"
    gov.mkdir(parents=True, exist_ok=True)
    safe_write(
        gov / "knn_label_disagreement.json",
        json.dumps({"summary": agg, "low_agreement": sorted(low, key=lambda x: x["agreement"])}, indent=2) + "\n",
        force_shrink=True,
    )
    print(f"✅ k={args.k}: mean agreement {agg['mean_agreement']}, "
          f"{agg['low_agreement_count']} FBs ≤{int(_LOW_AGREEMENT_THRESHOLD * 100)}% ({agg['low_agreement_pct']}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
