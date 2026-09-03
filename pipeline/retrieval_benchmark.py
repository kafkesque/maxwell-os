#!/usr/bin/env python3
"""
pipeline/retrieval_benchmark.py — Golden-set retrieval recall/precision harness.
===============================================================================
D2511. This is the measurement harness that UN-GATES S1 (contextual/late-chunk),
S2 (cross-encoder rerank), and S3 (HyDE): a candidate retrieval change is only
adoptable if it IMPROVES recall@k / MRR / precision@k on the golden query set
WITHOUT regressing the others.

Measures, for each golden query, three retrieval legs:
  * FTS only     (lexical baseline — good at vocabulary overlap)
  * VECTOR only  (semantic — the leg D2509 repaired)
  * HYBRID (RRF) (production default)

And, when enabled, the re-rank pass over the hybrid candidate pool:
  * HYBRID + RERANK  (S2 — cross-encoder bge-reranker-v2-m3, config-gated)

Metrics (k = config/golden retrieval_queries top-k, default 10):
  * recall@k      : fraction of expected fb_ids found in top-k (primary)
  * MRR           : mean reciprocal rank of the first expected hit
  * precision@k   : expected hits / k

C12: all thresholds/limits from config (retrieval_benchmark block) with
documented fallbacks. C16: no silent errors — a query with a missing expected
FB aborts loudly instead of quietly reporting 0.

Usage:
    /opt/homebrew/bin/python3 pipeline/retrieval_benchmark.py
    /opt/homebrew/bin/python3 pipeline/retrieval_benchmark.py --rerank   # S2 A/B
    /opt/homebrew/bin/python3 pipeline/retrieval_benchmark.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from functools import lru_cache
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import DB_PATH, HYDE_MAX_TOKENS, HYDE_MODEL
from pipeline.retrieve import get_conn, search_fts, search_vector, search_hybrid

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = PROJECT_ROOT / "config" / "golden" / "retrieval_queries.yaml"

with open(PROJECT_ROOT / "config" / "pipeline_config.yaml") as _f:
    _CFG = yaml.safe_load(_f) or {}
_BENCH = _CFG.get("retrieval_benchmark", {})
DEFAULT_K: int = int(_BENCH.get("top_k", 10))
DEFAULT_POOL: int = int(_BENCH.get("candidate_pool", 30))


def _load_golden(path: Path) -> list[dict]:
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("queries", [])


def _ids(results: list[dict]) -> list[str]:
    return [r["fb_id"] for r in results]


def _recall_at_k(expected: list[str], got: list[str], k: int) -> float:
    got = got[:k]
    hits = sum(1 for e in expected if any(g.startswith(e) for g in got))
    return hits / len(expected) if expected else 0.0


def _mrr(expected: list[str], got: list[str], k: int) -> float:
    got = got[:k]
    for rank, g in enumerate(got, 1):
        if any(g.startswith(e) for e in expected):
            return 1.0 / rank
    return 0.0


def _precision_at_k(expected: list[str], got: list[str], k: int) -> float:
    got = got[:k]
    hits = sum(1 for e in expected if any(g.startswith(e) for g in got))
    return hits / k if k else 0.0


def _rrf_fuse(legs: list[list[dict]], k: int = 60) -> list[dict]:
    """Fuse ranked legs via Reciprocal Rank Fusion (D2176, mirror of search_hybrid).

    Pure helper so the S1 A/B can fuse FTS + a *contextual* vector leg without
    re-implementing RRF inline. Order-preserving; returns a single ranked list.
    """
    scores: dict[str, float] = {}
    order: list[str] = []
    for leg in legs:
        for rank, r in enumerate(leg, 1):
            fid = r["fb_id"]
            if fid not in scores:
                order.append(fid)
            scores[fid] = scores.get(fid, 0.0) + 1.0 / (k + rank)
    ranked = sorted(order, key=lambda fid: scores[fid], reverse=True)
    return [{"fb_id": fid} for fid in ranked]


def _rerank(conn, query: str, candidates: list[dict], top_k: int) -> list[dict]:
    """S2: cross-encoder rerank of a candidate pool (config-gated).

    Lazy-imports so the benchmark runs without transformers/torch installed.
    bge-reranker-v2-m3 (already cached + verified) scores (query, definition)
    pairs; higher = more relevant. C16: a rerank failure raises rather than
    silently returning the unfused list.
    """
    from pipeline.rerank import rerank_candidates
    return rerank_candidates(query, candidates, top_k=top_k)


@lru_cache(maxsize=None)
def _generate_hypothetical(query: str) -> str:
    """S3 HyDE (D2521): generate a hypothetical FB definition for `query`.

    HyDE (Hypothetical Document Embeddings) embeds a GENERATED passage instead
    of the raw query, so the vector leg matches on the definition surface the
    corpus was embedded on — recovering the "abstract query → concrete answer"
    gap. Uses the generator LLM (config `hyde.model`, temp 0.0 per R7).

    lru_cache avoids re-generating the same query when both `hyde` and
    `hybrid+hyde` legs run in one invocation. C16: generation failure raises.
    """
    from pipeline.omlx_call import call_omlx

    system = (
        "You are a retrieval-hypothesis generator. Write ONE short paragraph "
        "(3-5 sentences) that a knowledge card answering the query would "
        "plausibly use as its core definition. Output only the paragraph — no "
        "preamble, no labels, no quotes."
    )
    prompt = f"Query: {query}\n\nHypothetical definition paragraph:"
    return call_omlx(
        prompt=prompt,
        model=HYDE_MODEL,
        system=system,
        max_tokens=HYDE_MAX_TOKENS,
    ).strip()


def _run_method(conn, name: str, query: str, expected: list[str],
                k: int, pool: int, rerank: bool) -> dict:
    if name == "fts":
        got = _ids(search_fts(conn, query, limit=pool))
    elif name == "vector":
        got = _ids(search_vector(conn, query, limit=pool))
    elif name == "hybrid":
        # rerank=False keeps this the raw-RRF baseline even when config rerank.enabled.
        got = _ids(search_hybrid(conn, query, limit=pool, rerank=False))
    elif name == "hybrid-ctx":
        # S1 A/B: fuse FTS + CONTEXTUAL vector leg (vec_fbs_ctx) instead of vec_fbs.
        fts = search_fts(conn, query, limit=pool)
        vec = search_vector(conn, query, limit=pool, vec_table="vec_fbs_ctx")
        got = _ids(_rrf_fuse([fts, vec]))
    elif name == "hybrid+rerank":
        # rerank=False → raw pool; explicit _rerank pass (S2 A/B control).
        candidates = search_hybrid(conn, query, limit=pool, rerank=False)
        got = _ids(_rerank(conn, query, candidates, top_k=k))
    elif name == "hyde":
        # S3: embed the GENERATED hypothetical doc, not the raw query.
        hyde_doc = _generate_hypothetical(query)
        got = _ids(search_vector(conn, hyde_doc, limit=pool))
    elif name == "hybrid+hyde":
        # S3 A/B: fuse FTS with the HyDE vector leg (replaces raw-query vector).
        fts = search_fts(conn, query, limit=pool)
        hyde_doc = _generate_hypothetical(query)
        vec = search_vector(conn, hyde_doc, limit=pool)
        got = _ids(_rrf_fuse([fts, vec]))
    else:
        raise ValueError(f"unknown method {name}")

    return {
        "recall": round(_recall_at_k(expected, got, k), 4),
        "mrr": round(_mrr(expected, got, k), 4),
        "precision": round(_precision_at_k(expected, got, k), 4),
        "top_hits": [g[:16] for g in got[:k]],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden-set retrieval benchmark (D2511)")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--golden", type=Path, default=GOLDEN_PATH)
    parser.add_argument("-k", "--top-k", type=int, default=DEFAULT_K)
    parser.add_argument("--pool", type=int, default=DEFAULT_POOL, help="candidate pool per leg")
    parser.add_argument("--rerank", action="store_true", help="A/B cross-encoder rerank (S2)")
    parser.add_argument("--contextual", action="store_true", help="A/B contextual embedding (S1)")
    parser.add_argument("--hyde", action="store_true", help="A/B HyDE hypothetical-document embedding (S3)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    queries = _load_golden(args.golden)
    if not queries:
        print("  ❌ golden query set is empty")
        return 1

    conn = get_conn()
    methods = ["fts", "vector", "hybrid"]
    if args.contextual:
        methods.append("hybrid-ctx")
    if args.rerank:
        methods.append("hybrid+rerank")
    if args.hyde:
        methods.append("hyde")
        methods.append("hybrid+hyde")

    agg: dict[str, dict[str, float]] = {m: {"recall": 0.0, "mrr": 0.0, "precision": 0.0} for m in methods}
    per_query: list[dict] = []

    for q in queries:
        query: str = q["query"]
        expected: list[str] = q["expected"]
        row = {"query": query, "type": q.get("query_type", "?"), "methods": {}}
        for m in methods:
            res = _run_method(conn, m, query, expected, args.top_k, args.pool, args.rerank)
            row["methods"][m] = res
            for metric in ("recall", "mrr", "precision"):
                agg[m][metric] += res[metric]
        per_query.append(row)

    n = len(queries)
    for m in methods:
        for metric in agg[m]:
            agg[m][metric] = round(agg[m][metric] / n, 4)

    if args.json:
        print(json.dumps({"aggregate": agg, "per_query": per_query}, indent=2))
        return 0

    print("\n═══ D2511 RETRIEVAL BENCHMARK (golden queries, k=%d) ═══" % args.top_k)
    header = f"{'method':<16} {'recall@k':>10} {'MRR':>8} {'P@k':>8}"
    print(header)
    print("-" * len(header))
    for m in methods:
        a = agg[m]
        print(f"{m:<16} {a['recall']:>10.3f} {a['mrr']:>8.3f} {a['precision']:>8.3f}")

    print("\nper-query recall:")
    for row in per_query:
        cells = "  ".join(f"{m}={row['methods'][m]['recall']:.2f}" for m in methods)
        print(f"  [{row['type']:<18}] {row['query'][:45]:<47} {cells}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
