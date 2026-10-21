"""pipeline/revert_bug959.py — BUG-959 Part A revert + D-3036 red-loop probe.

The D-3117 evidence_accumulator grouped by ``concept_key`` ONLY and filled empty body fields
across content_types. BUG-959 (Poker): the process_template 'Poker Decision-Making Framework'
row had its empty ``application``/``elaboration`` filled from the principle 'Poker As
Decision-making Framework' row — a false concept_key merge (both names fold to the same
D-3118 Phase A key because the key drops the stopword 'as' and sorts tokens).

Part A (this script): reconcile the affected rows' body fields back to the pre-accumulation
C13 backup. Crash-safe C6 (single transaction); the backup is the ground truth and is read-only
here. Deterministic and LLM-free (D-343). Field set loads from config/accumulate.yaml#merge_fields
(C12, ONE home — never restated).

``--check`` is the D-3036 red-loop probe for the WHOLE bug (A+B):
  RED   (exit 1) = a cross-content_type contamination exists — two rows sharing a concept_key
                   but differing in content_type ALSO share a non-empty body-field value (the
                   BUG-959 empty-field-fill shape).
  GREEN (exit 0) = no such contamination.
Run ``--check`` BEFORE the revert (captures RED) and AFTER (captures GREEN).
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # repo idiom: runnable directly AND importable (C21)

from pipeline.pipeline_paths import DB_PATH  # noqa: E402  (C12/C21: the ONE home for the DB path)

CONFIG_PATH = ROOT / "config" / "accumulate.yaml"

# The BUG-959 colliding key (measured 2026-10-21). A CLI default, NOT a code path (the
# --check probe scans the WHOLE store; only the targeted reconcile defaults to this key).
POKER_KEY = "ccf192e8551bc8b5dd658bb6f1fce848681bed2ca6ecfa8d904362afb3928e70"

_IDENTITY_COLS = ["source_ids", "source_diversity", "is_convergent"]


def _merge_fields() -> list[str]:
    """Load accumulate.merge_fields (C12) — the 7 CRIBS body fields, never restated here."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"revert_bug959: missing config {CONFIG_PATH} (C16)")
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    fields = data.get("accumulate", {}).get("merge_fields", [])
    if not fields:
        raise ValueError(f"revert_bug959: accumulate.merge_fields empty in {CONFIG_PATH} (C16)")
    return [str(f) for f in fields]


def detect_cross_type_contamination(conn: sqlite3.Connection, merge_fields: list[str]) -> list[tuple[str, str]]:
    """Red-loop probe: cross-type rows sharing a non-empty body-field value (the BUG-959 shape)."""
    cols = ["concept_key", "content_type"] + merge_fields
    quoted = ", ".join(f'"{c}"' for c in cols)
    rows = conn.execute(f"SELECT {quoted} FROM fbs WHERE concept_key IS NOT NULL").fetchall()
    by_ck: dict[str, list[sqlite3.Row]] = {}
    for r in rows:
        by_ck.setdefault(r["concept_key"], []).append(r)
    hits: list[tuple[str, str]] = []
    for ck, members in by_ck.items():
        if len({m["content_type"] for m in members}) <= 1:
            continue
        for f in merge_fields:
            vals = [str(m[f]).strip() for m in members if m[f] is not None and str(m[f]).strip()]
            if len(vals) >= 2 and len(set(vals)) == 1:
                hits.append((ck, f))
    return hits


def reconcile(conn: sqlite3.Connection, backup_path: Path, concept_key: str,
              merge_fields: list[str]) -> int:
    """Restore the target group's body/identity columns to the backup values (atomic)."""
    cols = merge_fields + _IDENTITY_COLS
    fb_ids = [r["fb_id"] for r in
              conn.execute("SELECT fb_id FROM fbs WHERE concept_key = ?", (concept_key,)).fetchall()]
    if not fb_ids:
        raise ValueError(f"revert_bug959: no rows for concept_key {concept_key} (C16)")
    bk = sqlite3.connect(str(backup_path))
    bk.row_factory = sqlite3.Row
    sel = ", ".join(f'"{c}"' for c in cols)
    changed = 0
    try:
        conn.execute("BEGIN IMMEDIATE")
        for fb_id in fb_ids:
            b = bk.execute(f"SELECT {sel} FROM fbs WHERE fb_id = ?", (fb_id,)).fetchone()
            if b is None:
                raise ValueError(f"revert_bug959: fb_id {fb_id} absent from backup {backup_path} (C16)")
            live = conn.execute(f"SELECT {sel} FROM fbs WHERE fb_id = ?", (fb_id,)).fetchone()
            updates = {c: b[c] for c in cols if live[c] != b[c]}
            if updates:
                sets = ", ".join(f'"{c}" = ?' for c in updates)
                conn.execute(f"UPDATE fbs SET {sets} WHERE fb_id = ?", [*updates.values(), fb_id])
                changed += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        bk.close()
    return changed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="BUG-959 Part A revert from the C13 backup.")
    ap.add_argument("--check", action="store_true",
                    help="red-loop probe only (exit 1 = cross-type contamination present)")
    ap.add_argument("--concept-key", default=POKER_KEY,
                    help="concept_key to reconcile (default: the BUG-959 Poker key)")
    ap.add_argument("--backup", default="knowledge pipeline/maxwell.db.bak_accumulate_20261021_143827",
                    help="C13 backup (pre-accumulation ground truth)")
    args = ap.parse_args(argv)

    merge_fields = _merge_fields()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        hits = detect_cross_type_contamination(conn, merge_fields)
        print(f"revert_bug959: cross-type contamination fields = {len(hits)}")
        for ck, f in hits:
            print(f"  [RED] concept_key={ck[:16]}... field={f}")
        if args.check:
            return 1 if hits else 0
        backup = Path(args.backup)
        if not backup.exists():
            raise FileNotFoundError(f"revert_bug959: backup not found: {backup} (C16)")
        changed = reconcile(conn, backup, args.concept_key, merge_fields)
        print(f"revert_bug959: reconciled {changed} row(s) for concept_key={args.concept_key[:16]}... from {backup.name}")
        after = detect_cross_type_contamination(conn, merge_fields)
        print(f"revert_bug959: cross-type contamination fields AFTER revert = {len(after)}")
        return 1 if after else 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
