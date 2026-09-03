#!/usr/bin/env python3
"""D2511 — RRF keyword-leg pollution regression test.

BUG (found live during D2511 stress-testing): search_hybrid() always fused the
`search_keyword()` leg into the RRF score map, even when the caller passed NO
domain/discipline/depth filter. With no filter, search_keyword() returns
`ORDER BY borp_score DESC` — and with borp_score ≈ all 0.0 that collapses to
ROWID order, i.e. a CONSTANT list. The same ~100 FBs (e.g. "High Contrast
Visual Design") then received a fixed RRF bonus in EVERY query, diluting the
real FTS+vector signal and making hybrid WORSE than vector-only.

Fix (D2511): the metadata/keyword leg participates ONLY when the caller actually
supplies a domain/discipline/depth filter. Otherwise it contributes nothing.

This test proves the leg is gated by filter presence WITHOUT needing a live
sqlite-vec / Ollama / FTS5 corpus — it monkeypatches the three sub-search
functions and asserts search_hybrid only calls search_keyword when a filter is set.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pipeline.retrieve as retrieve


def _fake_results(ids: list[str]) -> list[dict]:
    return [{"fb_id": i} for i in ids]


def main() -> int:
    failures: list[str] = []

    def check(desc: str, cond: bool):
        if cond:
            print(f"  ✅ {desc}")
        else:
            failures.append(desc)
            print(f"  ❌ {desc}")

    calls: dict[str, int] = {"keyword": 0}

    def fake_fts(conn, query, limit=20, include_quarantine=False):
        return _fake_results(["fts_1", "fts_2"])

    def fake_vector(conn, query, limit=20, include_quarantine=False):
        return _fake_results(["vec_1", "vec_2"])

    def fake_keyword(conn, domain=None, discipline=None, depth=None, limit=20,
                     status="PASS", include_quarantine=False, exclude_summaries=True):
        calls["keyword"] += 1
        return _fake_results(["kw_1", "kw_2"])

    orig_fts = retrieve.search_fts
    orig_vec = retrieve.search_vector
    orig_kw = retrieve.search_keyword
    retrieve.search_fts = fake_fts
    retrieve.search_vector = fake_vector
    retrieve.search_keyword = fake_keyword
    try:
        # 1. NO filter → keyword leg must NOT be invoked
        calls["keyword"] = 0
        out = retrieve.search_hybrid(None, "some query", limit=5)
        check("no-filter: keyword leg NOT called", calls["keyword"] == 0)
        check("no-filter: results come from FTS+vector only",
              {r["fb_id"] for r in out} == {"fts_1", "fts_2", "vec_1", "vec_2"})

        # 2. WITH a domain filter → keyword leg MUST be invoked
        calls["keyword"] = 0
        out = retrieve.search_hybrid(None, "some query", domain="design", limit=5)
        check("domain-filter: keyword leg called", calls["keyword"] == 1)
        check("domain-filter: keyword results fused",
              "kw_1" in {r["fb_id"] for r in out})
    finally:
        retrieve.search_fts = orig_fts
        retrieve.search_vector = orig_vec
        retrieve.search_keyword = orig_kw

    if failures:
        print(f"\n  ❌ {len(failures)} failure(s):")
        for f in failures:
            print(f"     - {f}")
        return 1
    print("\n  ✅ all D2511 RRF keyword-leg checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
