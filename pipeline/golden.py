#!/usr/bin/env python3
"""
pipeline/golden.py — golden-anchor resolver (D-2939, label vs pointer).
==========================================================================
WHY
---
config/golden/retrieval_queries.yaml pins `expected` fb_ids. An fb_id is a CONTENT
HASH of the verified input (D-2898), so every corpus reprocess mints new ids: a
hand-signed golden set rots in one pass. Measured 2026-10-11 (BUG-710): 0/30 golden
ids AND 0/30 golden NAMES were re-anchorable after rechunk-v4 — the harness then
reported recall@k = 0.000, which measured the GOLDEN SET, not retrieval.

THE SEPARATION (this module is the whole fix)
-------------------------------------------
  LABEL   = the query + the human-readable NAME of the correct answer.
            Owner-owned. Stable across a reprocess. The thing a human can judge.
  POINTER = the current fb_id of that NAME. MECHANICAL, run-scoped, recomputable.
            Not something an owner can or should sign.

D-2898 is unchanged: no agent mints a LABEL. This module mints POINTERS ONLY.

RAILS (C16 — fail loud; never let an unreturnable anchor print as recall 0)
--------------------------------------------------------------------------
  * name -> 0 rows in the serving scope  => UNRESOLVED (reported)
  * name -> >1 row                       => AMBIGUOUS  (refused, never guessed)
  * a query whose anchor cannot be resolved is EXCLUDED from the denominator and
    the exclusion is printed.

C12: serving scope + anchor mode come from config/serving. No LLM. No network.
No store writes. Deterministic.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.pipeline_paths import CANONICAL_RUN, required, required_mapping  # noqa: E402

_CFG_PATH = PROJECT_ROOT / "config" / "pipeline_config.yaml"
_CFG_HOME = str(_CFG_PATH.relative_to(_CFG_PATH.parent.parent))  # D-2982: derived, never a second copy
with open(_CFG_PATH, encoding='utf-8') as _f:
    _CFG: dict = yaml.safe_load(_f) or {}
# D-2982 (C16/D-2644): the serving block is DECLARED. A missing block must be an ERROR - the old
# `_CFG.get("serving", {})` read an EMPTY anchoring contract instead, so golden.py would silently
# stop honouring every rule below it (fail-OPEN on a gate, the BUG-504 class).
_SERVING: dict = required_mapping(_CFG, "serving", where=_CFG_HOME)
# D-2939: `name_then_id` = prefer the owner-approved NAME, keep `expected` ids as a
# legacy fallback. `id` = legacy behaviour (ids only, BUG-710 rail applies).
ANCHOR_MODE: str = str(required(_SERVING, "golden_anchor_mode", where=_CFG_HOME))
REQUIRE_RESOLVABLE: bool = bool(required(_SERVING, "require_resolvable_goldens", where=_CFG_HOME))
GOLDEN_PATH: Path = PROJECT_ROOT / "config" / "golden" / "retrieval_queries.yaml"


def load_golden(path: Path) -> list[dict]:
    """Load the golden query list from YAML."""
    with open(path, encoding='utf-8') as f:
        return (yaml.safe_load(f) or {}).get("queries", [])


def resolve_name(conn, name: str, serving_scope: str = "canonical_run",
                 canonical_run: str | None = None) -> tuple[str | None, str, int]:
    """Resolve an owner-approved answer NAME to its current fb_id.

    Returns (fb_id | None, why, n_matches). n_matches > 1 is AMBIGUOUS and is
    refused rather than guessed (C16): two rows sharing a name means the name is
    not a label, and silently taking the first would be a coin flip.
    """
    run = canonical_run or CANONICAL_RUN
    where = "lower(name) = lower(?) AND status = 'PASS'"
    params: list = [name]
    if serving_scope == "canonical_run":
        where += " AND pipeline_run_id = ?"
        params.append(run)
    rows = conn.execute(f"SELECT fb_id, pipeline_run_id FROM fbs WHERE {where}", tuple(params)).fetchall()
    if not rows:
        return None, f"no PASS row named {name!r} in scope {serving_scope}", 0
    if len(rows) > 1:
        return None, f"AMBIGUOUS: {len(rows)} PASS rows share the name in scope {serving_scope}", len(rows)
    return rows[0]["fb_id"], "resolved", len(rows)


def resolve_golden_anchors(conn, queries: list[dict],
                           serving_scope: str = "canonical_run") -> tuple[list[dict], dict]:
    """Resolve every `expected_names` entry in place; drop queries with no anchor.

    Returns (kept_queries, report). Mutates a COPY of each query, never the input.

    `kept_queries` entries always carry a non-empty `expected` list, so downstream
    consumers never KeyError and never divide by an unresolvable anchor.
    """
    report: dict = {
        "anchor_mode": ANCHOR_MODE, "serving_scope": serving_scope,
        "canonical_run": CANONICAL_RUN, "resolved": [], "unresolved": [],
        "ambiguous": [], "excluded_queries": [],
    }
    kept: list[dict] = []
    for q in queries:
        q2 = dict(q)
        ids: list[str] = []
        names: list[str] = list(q.get("expected_names") or [])
        if ANCHOR_MODE == "name_then_id" and names:
            for nm in names:
                fid, why, n = resolve_name(conn, nm, serving_scope)
                if fid:
                    ids.append(fid)
                    report["resolved"].append({"query": q.get("query", ""), "name": nm, "fb_id": fid})
                else:
                    bucket = "ambiguous" if n > 1 else "unresolved"
                    report[bucket].append({"query": q.get("query", ""), "name": nm, "why": why, "n": n})
        ids.extend(list(q.get("expected") or []))
        if ids:
            q2["expected"] = list(dict.fromkeys(ids))
            kept.append(q2)
        else:
            report["excluded_queries"].append({"query": q.get("query", ""), "names": names})
    return kept, report


def sample_self_retrieval(conn, n: int, order: str = "fb_id",
                          canonical_run: str | None = None) -> list[dict]:
    """Deterministic sample of served PASS principle rows (label-free slice).

    No gold label is minted and no owner gate is crossed (D-2898 governs LABELS;
    this slice has none). `order` is config-owned so the sample is reproducible
    (C12/C20: no unrecorded randomness).
    """
    run = canonical_run or CANONICAL_RUN
    rows = conn.execute(
        "SELECT fb_id, name, definition FROM fbs "
        "WHERE pipeline_run_id = ? AND status = 'PASS' AND content_type = 'principle' "
        "AND length(name) > 10 AND length(coalesce(definition, '')) > 80 "
        f"ORDER BY {order} LIMIT ?",
        (run, int(n)),
    ).fetchall()
    return [{"fb_id": r["fb_id"], "name": r["name"], "definition": r["definition"]} for r in rows]


def main() -> int:
    """CLI: --check prints the anchor resolution report without touching the store."""
    ap = argparse.ArgumentParser(description="Golden-anchor resolver (D-2939)")
    ap.add_argument("--golden", type=Path, default=GOLDEN_PATH)
    ap.add_argument("--serving-scope", default="canonical_run", choices=["canonical_run", "all_runs"])
    args = ap.parse_args()
    from pipeline.retrieve import get_conn  # local import: keeps this module import-light
    conn = get_conn()
    queries = load_golden(args.golden)
    kept, report = resolve_golden_anchors(conn, queries, args.serving_scope)
    print("═══ GOLDEN ANCHOR RESOLUTION (D-2939) ═══")
    print(f"anchor mode      : {report['anchor_mode']}")
    print(f"serving scope    : {report['serving_scope']} (canonical run = {report['canonical_run']})")
    print(f"queries in file  : {len(queries)}")
    print(f"measurable       : {len(kept)}")
    print(f"resolved names   : {len(report['resolved'])}")
    print(f"unresolved names : {len(report['unresolved'])}")
    print(f"ambiguous names  : {len(report['ambiguous'])}")
    for r in report["unresolved"]:
        print(f"   ✗ {r['name'][:52]!r} <- {r['query'][:40]}")
    for r in report["ambiguous"]:
        print(f"   ⚠ {r['name'][:52]!r} ({r['n']} rows) <- {r['query'][:40]}")
    if REQUIRE_RESOLVABLE and not kept:
        print("   ❌ nothing measurable (C16)")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
