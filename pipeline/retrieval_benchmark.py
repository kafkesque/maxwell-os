#!/usr/bin/env python3
"""
pipeline/retrieval_benchmark.py — Golden-set retrieval recall/precision harness.
===============================================================================
D2511. This is the measurement harness that UN-GATES S1 (contextual/late-chunk),
S2 (cross-encoder rerank), and S3 (HyDE): a candidate retrieval change is only
adoptable if it IMPROVES recall@k / MRR / precision@k on the golden query set
WITHOUT regressing the others.

Measures, for each golden query, the SERVED path and its A/B controls:
  * PRODUCTION   (the dispatcher, D-2724/D-2980 - what serving actually returns) [reference]
  * FTS only     (lexical baseline — good at vocabulary overlap)
  * VECTOR only  (semantic — the leg D2509 repaired)
  * HYBRID (RRF) (the superseded fusion path, kept as a control)

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

from pipeline.pipeline_paths import CANONICAL_RUN, DB_PATH, HYDE_MAX_TOKENS, HYDE_MODEL
from pipeline.retrieve import (  # noqa: E402  D-2980: search() = the SERVED path; the rest are A/B controls
    _rerank_pool_size,
    get_conn,
    search,
    search_fts,
    search_hybrid,
    search_vector,
)
# D-2939: owner-approved NAMES -> current fb_ids (the pointer is mechanical).
from pipeline.golden import resolve_golden_anchors, sample_self_retrieval  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = PROJECT_ROOT / "config" / "golden" / "retrieval_queries.yaml"

with open(PROJECT_ROOT / "config" / "pipeline_config.yaml") as _f:
    _CFG = yaml.safe_load(_f) or {}
_BENCH = _CFG.get("retrieval_benchmark", {})
_SERVING: dict = _CFG.get("serving", {})
DEFAULT_K: int = int(_BENCH.get("top_k", 10))
DEFAULT_POOL: int = int(_BENCH.get("candidate_pool", 0))
# D-2980: the measured method set. "production" is the dispatcher (what serving returns);
# the rest are A/B controls. Order = reference first.
DEFAULT_METHODS: list[str] = ["production", "fts", "vector", "hybrid"]
# D-2936: the scope a golden id must live in to be measurable at all.
DEFAULT_SERVING_SCOPE: str = str(_SERVING.get("index_scope", "canonical_run"))
# C16/BUG-710: never report a recall number for a golden the harness cannot resolve.
_REQUIRE_RESOLVABLE: bool = bool(_SERVING.get("require_resolvable_goldens", True))


def _load_golden(path: Path) -> list[dict]:
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("queries", [])


def _resolvability(conn, queries: list[dict], serving_scope: str) -> dict:
    """C16 precondition: can each golden id be returned by the SERVING path at all?

    BUG-710: this harness reported recall@k = 0.000 for 30/30 goldens and it was
    read as a retrieval-quality regression. It was not: every golden fb_id belonged
    to the superseded t11 run, while serving is pinned to CANONICAL_RUN (D-2881), so
    the expected ids were STRUCTURALLY unreturnable. A benchmark that cannot fail
    loud about that is worse than no benchmark — it inverts the signal.

    For every expected id this reports:
      * found          : the id exists in the store at all
      * run            : the pipeline_run_id it belongs to
      * in_scope       : run == CANONICAL_RUN when serving_scope == "canonical_run"
      * status         : PASS / QUARANTINE (QUARANTINE is filtered out of serving
                         unless include_quarantine is set, so it is also unreturnable)
      * measurable     : in_scope AND status == 'PASS'
    """
    rows: list[dict] = []
    for q in queries:
        for expected in q.get("expected", []):
            hit = conn.execute(
                "SELECT fb_id, pipeline_run_id, status, name FROM fbs WHERE fb_id LIKE ? LIMIT 1",
                (expected + "%",),
            ).fetchone()
            if hit is None:
                rows.append({"query": q.get("query", ""), "expected": expected, "found": False,
                             "run": None, "in_scope": False, "status": None, "name": None, "measurable": False})
                continue
            in_scope = serving_scope != "canonical_run" or hit["pipeline_run_id"] == CANONICAL_RUN
            rows.append({
                "query": q.get("query", ""), "expected": expected, "found": True,
                "run": hit["pipeline_run_id"], "in_scope": in_scope, "status": hit["status"],
                "name": hit["name"], "measurable": bool(in_scope and hit["status"] == "PASS"),
            })
    meas = sum(1 for r in rows if r["measurable"])
    return {
        "serving_scope": serving_scope,
        "canonical_run": CANONICAL_RUN,
        "total": len(rows),
        "measurable": meas,
        "unreturnable": len(rows) - meas,
        "rows": rows,
    }


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
    if name == "production":
        # D-2980: EXACTLY what serving does - the dispatcher with its config-selected method,
        # its own pool policy (_rerank_pool_size) and its rerank gate. Every other leg is an
        # A/B control; this is the REFERENCE row (BUG-710: the harness could not bench it).
        got = _ids(search(conn, query, limit=k))
    elif name == "fts":
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
    elif name == "vector+rerank":
        # D-2723: rerank over the PURE VECTOR pool (no RRF fusion). Forensic gap:
        # hybrid-RRF recall (0.833) < vector (0.900) — RRF fusion is recall-negative.
        # This leg isolates whether rerank on the un-fused vector pool recovers the
        # best of both: vector recall + cross-encoder MRR.
        candidates = search_vector(conn, query, limit=pool)
        got = _ids(_rerank(conn, query, candidates, top_k=k))
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


def _run_self_retrieval(conn, args) -> int:
    """D-2940 — the LABEL-FREE slice: query every sampled FB by its own NAME.

    Why this exists: every recall number in this harness needs an owner-signed
    golden, and goldens rot on each reprocess (BUG-710/D-2939), so for months the
    only true statement available was "no baseline exists". This slice mints NO
    label (D-2898 governs LABELS, and there are none here), so it is not
    owner-gated and it is always runnable.

    What it measures: "can the stack find an object it already holds" — index
    health and leg ordering, isolated from question-answering ability.

    What it does NOT measure (guard against slope): a FB name is a LEXICAL query,
    so FTS flatters itself here and this number must never be quoted as retrieval
    quality for abstract questions. It is a REGRESSION rail for the semantic slice.
    """
    sc: dict = _BENCH.get("self_retrieval", {}) or {}
    n: int = args.self_retrieval or int(sc.get("sample", 30))
    legs: list[str] = list(sc.get("legs", ["fts", "vector", "hybrid"]))
    rows = sample_self_retrieval(conn, n, order=str(sc.get("order", "fb_id")))
    if not rows:
        print("  ❌ self-retrieval sample is empty (C16)")
        return 2

    agg: dict[str, dict[str, float]] = {lg: {"recall": 0.0, "mrr": 0.0} for lg in legs}
    for r in rows:
        for lg in legs:
            res = _run_method(conn, lg, r["name"], [r["fb_id"]], args.top_k, pool, True)
            agg[lg]["recall"] += res["recall"]
            agg[lg]["mrr"] += res["mrr"]
    m: int = len(rows)
    for lg in legs:
        agg[lg]["recall"] = round(agg[lg]["recall"] / m, 4)
        agg[lg]["mrr"] = round(agg[lg]["mrr"] / m, 4)

    payload = {
        "slice": "self-retrieval (label-free)", "sample": m, "k": args.top_k,
        "canonical_run": CANONICAL_RUN, "aggregate": agg,
        "caveat": "name queries are lexical; FTS is flattered. Regression rail only.",
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"\n═══ D-2940 LABEL-FREE SLICE — self-retrieval (k={args.top_k}, n={m}) ═══")
    print(f"  run={CANONICAL_RUN}  query = the FB's own NAME, correct = itself")
    print(f"{'leg':<16} {'recall@k':>10} {'MRR':>8}")
    print("-" * 36)
    for lg in legs:
        print(f"{lg:<16} {agg[lg]['recall']:>10.3f} {agg[lg]['mrr']:>8.3f}")
    print("\n  ⚠  lexical proxy: it must never be quoted as retrieval quality for")
    print("     abstract questions. It is the always-available regression rail.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden-set retrieval benchmark (D2511)")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--golden", type=Path, default=GOLDEN_PATH)
    parser.add_argument("-k", "--top-k", type=int, default=DEFAULT_K)
    parser.add_argument("--pool", type=int, default=DEFAULT_POOL,
                        help="candidate pool per leg; 0 (default) = DERIVE from serving.pool, "
                             "which is the SERVED path's own policy (D-2980)")
    parser.add_argument("--rerank", action="store_true", help="A/B cross-encoder rerank (S2)")
    parser.add_argument("--contextual", action="store_true", help="A/B contextual embedding (S1)")
    parser.add_argument("--hyde", action="store_true", help="A/B HyDE hypothetical-document embedding (S3)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--serving-scope", default=DEFAULT_SERVING_SCOPE,
                        choices=["canonical_run", "all_runs"],
                        help="scope a golden id must live in to be measurable (config serving.index_scope)")
    parser.add_argument("--allow-unresolvable", action="store_true",
                        help="C16 override: report metrics even when goldens are outside the serving scope (diagnostic only)")
    parser.add_argument("--self-retrieval", nargs="?", const=0, type=int, default=None,
                        help="D-2940 label-free slice: query each sampled FB by its own NAME. "
                             "Mints no gold label, so it needs no owner gate; it is a REGRESSION rail, "
                             "not a substitute for the semantic golden slice (a name query is lexical).")
    args = parser.parse_args()

    # D-2980: the A/B legs must be built at the SERVED pool width, not a literal, or they
    # measure a different function than the one production calls.
    pool: int = args.pool if args.pool else _rerank_pool_size(args.top_k)

    queries = _load_golden(args.golden)
    if not queries:
        print("  ❌ golden query set is empty")
        return 1

    conn = get_conn()

    if args.self_retrieval is not None:
        return _run_self_retrieval(conn, args)

    # D-2939 (label vs pointer): an owner approves a NAME, not a content hash.
    # Resolve expected_names -> ids in the serving scope so the anchor survives a
    # corpus reprocess. An unresolvable name is EXCLUDED from the denominator and
    # reported — never scored 0 (BUG-710: a 0.000 recall on a structurally
    # unreturnable anchor measures the GOLDEN SET, not retrieval).
    queries, anchor_report = resolve_golden_anchors(conn, queries, args.serving_scope)
    for _u in anchor_report["unresolved"]:
        print(f"  ⚠️  golden anchor UNRESOLVED {_u['name']!r} ({_u['why']}) <- {_u['query'][:40]}")
    for _a in anchor_report["ambiguous"]:
        print(f"  ⚠️  golden anchor AMBIGUOUS  {_a['name']!r} ({_a['n']} rows) <- {_a['query'][:40]}")
    if anchor_report["excluded_queries"]:
        print(f"  ⚠️  {len(anchor_report['excluded_queries'])} golden query(ies) EXCLUDED from the "
              f"denominator (no resolvable anchor — BUG-710)")
    if not queries:
        print("  ❌ every golden query was excluded — nothing measurable (C16)")
        return 2

    # D-2936 / BUG-710: refuse to emit a recall number for unreturnable goldens.
    resolution = _resolvability(conn, queries, args.serving_scope)
    if resolution["unreturnable"]:
        print(f"\n  ❌ GOLDEN RESOLVABILITY FAILED (C16, BUG-710)")
        print(f"     serving scope: {resolution['serving_scope']} (canonical run = {resolution['canonical_run']})")
        print(f"     measurable goldens: {resolution['measurable']}/{resolution['total']}")
        for r in resolution["rows"]:
            if not r["measurable"]:
                where = f"run={r['run']} status={r['status']}" if r["found"] else "NOT IN STORE"
                print(f"       ✗ {r['expected']}  {where}  ({(r['name'] or '')[:40]})  <- {r['query'][:44]}")
        print("     A 0.000 recall on these ids measures the GOLDEN SET, not retrieval.")
        print("     Fix: re-anchor the goldens to the served run (scripts/reanchor_retrieval_goldens.py),")
        print("     or pass --allow-unresolvable for a diagnostic run, or --serving-scope all_runs.")
        if _REQUIRE_RESOLVABLE and not args.allow_unresolvable:
            return 2

    methods = list(DEFAULT_METHODS)
    if args.contextual:
        methods.append("hybrid-ctx")
    if args.rerank:
        methods.append("hybrid+rerank")
        methods.append("vector+rerank")
    if args.hyde:
        methods.append("hyde")
        methods.append("hybrid+hyde")

    agg: dict[str, dict[str, float]] = {m: {"recall": 0.0, "mrr": 0.0, "precision": 0.0} for m in methods}
    per_query: list[dict] = []

    for q in queries:
        query: str = q["query"]
        expected: list[str] = q.get("expected", [])
        row = {"query": query, "type": q.get("query_type", "?"), "methods": {}}
        for m in methods:
            res = _run_method(conn, m, query, expected, args.top_k, pool, args.rerank)
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

    print("\n═══ D2511 RETRIEVAL BENCHMARK (golden queries, k=%d, pool=%d) ═══" % (args.top_k, pool))
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
