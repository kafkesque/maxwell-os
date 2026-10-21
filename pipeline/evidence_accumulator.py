"""pipeline/evidence_accumulator.py — cross-run evidence accumulation (D-3117).

Matches committed FBs against the store by generation-invariant ``concept_key`` (D-3118
Phase A) and, for every group of 2+ distinct sources, accumulates monotonic evidence.

Grouping is by ``(concept_key, content_type)`` — a necessary-condition guard (BUG-959):
content_type is axis 1 = functional ROLE, so two rows sharing a concept_key but differing in
content_type are DISTINCT concepts and are never accumulated across types.

  source_ids       <- union (never shrinks)
  source_diversity <- len(union)
  body fields      <- field-wise monotonic fill (non-empty beats empty; never overwrite a
                      non-empty field; never concatenate)
  is_convergent    <- (source_diversity >= convergent_min_sources), PRINCIPLE-SCOPED behind
                      accumulate.is_convergent_scope (D-3117 scope refinement)

Body divergence (token Jaccard + SequenceMatcher, the D-2950 primitives) is COMPUTED AND
REPORTED — never a blocking reject. The D-3117 reconciliation measured that a hard body gate
would reject the exact cross-source re-appearance this layer exists to accumulate (Phase 0
receipt a6323a7: body survival 0%; all 5 live duplicate concept_keys are is_divergent).

Deterministic and LLM-free (D-343). Idempotent + monotonic at THIS layer only (extraction is
never idempotent, arXiv 2408.04667). Report mode (default) changes NOTHING and writes a JSONL
receipt; apply mode performs the monotonic update behind a C13 backup in a single transaction
(C6). Every flag/threshold loads from config/accumulate.yaml (C12); the in-file values are
fail-safe defaults only.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo idiom: runnable directly AND importable (C21)

from pipeline.dedup_identity import body_text, is_divergent, jaccard, seq_ratio, source_set
from pipeline.pipeline_paths import DB_PATH

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "accumulate.yaml"

_PRINCIPLE_SCOPE = "principle"


def _config() -> dict:
    """Load config/accumulate.yaml#accumulate, fail-closed (C12/C16)."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"evidence_accumulator: missing config {CONFIG_PATH} — fail-closed (C12/C16)")
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    block = data.get("accumulate")
    if not isinstance(block, dict):
        raise ValueError(f"evidence_accumulator: config {CONFIG_PATH} missing 'accumulate' block (C12)")
    return block


def _richer(values: list[Any]) -> str | None:
    """Deterministic 'richer' pick: the longest non-empty value; None if all empty.

    Never returns a concatenation and never a summary/noise copy — only a member's own value
    (D-3117). Longest-first is the deterministic proxy for 'more specific'.
    """
    non_empty = [str(v).strip() for v in values if v is not None and str(v).strip()]
    if not non_empty:
        return None
    return max(non_empty, key=len)


def _pairwise_metrics(members: list[dict]) -> list[dict]:
    """Pairwise (jaccard, seq_ratio) over the group body, in a stable order (D-3117 report)."""
    bodies = [body_text(m) for m in members]
    out: list[dict] = []
    for i in range(len(bodies)):
        for k in range(i + 1, len(bodies)):
            out.append({"pair": [i, k], "jaccard": round(jaccard(bodies[i], bodies[k]), 4),
                        "seq_ratio": round(seq_ratio(bodies[i], bodies[k]), 4)})
    return out


def _group_disposition(members: list[dict], cfg: dict) -> dict:
    """Compute the monotonic accumulation disposition for one concept_key group (no writes)."""
    union: set[str] = set()
    for m in members:
        union |= source_set(m.get("source_ids"))
    new_diversity = len(union)
    min_sources = int(cfg["convergent_min_sources"])
    scope = str(cfg.get("is_convergent_scope", _PRINCIPLE_SCOPE))
    content_type = members[0].get("content_type")
    eligible = new_diversity >= min_sources
    scope_ok = scope == "all" or content_type == _PRINCIPLE_SCOPE
    merge_fields: list[str] = list(cfg["merge_fields"])
    fills: dict[str, str | None] = {}
    for f in merge_fields:
        richer = _richer([m.get(f) for m in members])
        fills[f] = richer
    max_before = max((m.get("source_diversity") or 0) for m in members)
    growth = new_diversity > max_before
    would_fill = any(
        fills[f] is not None
        and any(not (m.get(f) and str(m.get(f)).strip()) for m in members)
        for f in merge_fields
    )
    return {
        "concept_key": members[0].get("concept_key"),
        "names": sorted({str(m.get("name", "")) for m in members if m.get("name")}),
        "content_type": content_type,
        "member_fb_ids": [m.get("fb_id") for m in members],
        "source_ids_union": sorted(union),
        "source_diversity_before": [m.get("source_diversity") for m in members],
        "source_diversity_after": new_diversity,
        "is_divergent": bool(is_divergent(members)),
        "pairwise": _pairwise_metrics(members),
        "would_flip_is_convergent": bool(eligible and scope_ok),
        "would_accumulate": bool(growth or would_fill),
        "scope": scope,
        "fills": fills,
    }


def _load_rows(conn: sqlite3.Connection, merge_fields: list[str]) -> list[dict]:
    cols = ["fb_id", "name", "content_type", "concept_key", "source_ids",
            "source_diversity", "is_convergent", "origin"] + [f for f in merge_fields if f not in
            ("fb_id", "name", "content_type", "concept_key", "source_ids", "source_diversity",
             "is_convergent", "origin")]
    quoted = ", ".join(f'"{c}"' for c in cols)
    rows = conn.execute(f"SELECT {quoted} FROM fbs WHERE concept_key IS NOT NULL").fetchall()
    return [dict(zip(cols, r)) for r in rows]


def _backup(conn: sqlite3.Connection) -> str:
    """C13 backup of the live store before any apply (crash-safe, online-backup API)."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = Path(str(DB_PATH) + f".bak_accumulate_{ts}")
    dest_conn = sqlite3.connect(str(dest))
    try:
        conn.backup(dest_conn)
    finally:
        dest_conn.close()
    return str(dest)


def _apply(conn: sqlite3.Connection, groups: list[tuple[tuple[str, str], list[dict]]], cfg: dict) -> int:
    """Monotonic apply: union source_ids + bump source_diversity + fill empty body fields only.

    D-2933 rule V: never overwrite a non-empty body field. Only source_ids/source_diversity
    and the principle-scoped is_convergent flip are touched on a member that already carries
    content. Runs in one transaction (C6); caller already backed up (C13).
    """
    min_sources = int(cfg["convergent_min_sources"])
    scope = str(cfg.get("is_convergent_scope", _PRINCIPLE_SCOPE))
    merge_fields: list[str] = list(cfg["merge_fields"])
    applied = 0
    for key, members in groups:
        disp = _group_disposition(members, cfg)
        union_json = json.dumps(disp["source_ids_union"])
        new_diversity = disp["source_diversity_after"]
        flip = disp["would_flip_is_convergent"]
        for m in members:
            updates = {"source_ids": union_json, "source_diversity": new_diversity}
            if flip and (scope == "all" or m.get("content_type") == _PRINCIPLE_SCOPE):
                updates["is_convergent"] = 1
            for f in merge_fields:
                richer = disp["fills"][f]
                if richer is not None and not (m.get(f) and str(m.get(f)).strip()):
                    updates[f] = richer
            sets = ", ".join(f'"{c}" = ?' for c in updates)
            conn.execute(f"UPDATE fbs SET {sets} WHERE fb_id = ?", [*updates.values(), m.get("fb_id")])
            applied += 1
    return applied


def run(mode: str, receipt_path: str, cfg: dict) -> list[dict]:
    """Run the accumulator; returns the receipt records (report mode) or [] (apply)."""
    merge_fields: list[str] = list(cfg["merge_fields"])
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.row_factory = sqlite3.Row
        rows = _load_rows(conn, merge_fields)
    finally:
        pass
    # Group by (concept_key, content_type) — the necessary-condition guard (BUG-959 / D-3118).
    # content_type is axis 1 = functional ROLE; two rows sharing a concept_key but differing in
    # content_type are DISTINCT concepts by definition and must never accumulate across types.
    # (The D-3118 Phase A key is name-derived and folds 'Poker As ...' / 'Poker ...' into one key;
    # the composite key stops that false merge from ever cross-filling body fields.)
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        groups.setdefault((r["concept_key"], r["content_type"]), []).append(dict(r))
    multi = {k: v for k, v in groups.items() if len(v) >= 2}
    receipt: list[dict] = []
    for key, members in multi.items():
        disp = _group_disposition(members, cfg)
        disp["_ts"] = datetime.now(timezone.utc).isoformat()
        disp["_mode"] = mode
        receipt.append(disp)
    # Surface cross-type collisions the guard SUPPRESSES (distinct concepts, never accumulated) —
    # these are the D-3118 Phase B embedding-divergence fixtures, reported for visibility only.
    by_ck: dict[str, set[str]] = {}
    for r in rows:
        by_ck.setdefault(r["concept_key"], set()).add(r["content_type"])
    cross_type = sorted(k for k, v in by_ck.items() if len(v) > 1)
    if cross_type:
        print(f"evidence_accumulator: cross-type collision(s) SUPPRESSED by content_type guard: "
              f"{len(cross_type)} concept_key(s) spanning >1 content_type")
    if mode == "apply" and receipt:
        _backup(conn)
        _apply(conn, list(multi.items()), cfg)
        conn.commit()
    elif mode == "report" and receipt:
        out = Path(receipt_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            for rec in receipt:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    conn.close()
    return receipt


def main(argv: list[str] | None = None) -> int:
    cfg = _config()
    ap = argparse.ArgumentParser(description="Cross-run evidence accumulation (D-3117).")
    ap.add_argument("--mode", choices=["report", "apply"], default=str(cfg["mode"]))
    ap.add_argument("--check", action="store_true", help="report mode + exit 1 when any group WOULD accumulate (red-loop probe)")
    ap.add_argument("--receipt", default=str(cfg["receipt_path"]))
    args = ap.parse_args(argv)
    receipt = run(args.mode, args.receipt, cfg)
    n = len(receipt)
    would = sum(1 for rec in receipt if rec["would_accumulate"])
    print(f"evidence_accumulator: mode={args.mode} groups={n} would_accumulate={would}")
    for rec in receipt:
        flag = "ACCUMULATE" if rec["would_accumulate"] else "no-op"
        print(f"  [{flag}] {rec['names'][:1]} ... diversity {rec['source_diversity_before']}->{rec['source_diversity_after']} "
              f"divergent={rec['is_divergent']} scope={rec['scope']} content_type={rec['content_type']}")
    if args.check:
        return 1 if would else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
