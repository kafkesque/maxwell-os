#!/usr/bin/env python3
"""The ONE writer for the serving gate (D274a / G17 / D274h).

Re-derives `status` from the verification record and persists a typed
`s5_reason`, replacing the label-derived gate (apply_phase1_finalize.py:18 set
status = PASS iff content_type == 'principle').

Rule (config/serving_gate.yaml): status = PASS iff the `factual` check passed
(NLI ENTAIL-majority and no mechanism/evidence/classification failure), else
QUARANTINE. Measured effect: serving set 4,745 -> 3,310 (de-serves 1,941 rows,
restores 506 verified rows). Deletes nothing (R-D410).

Safety:
  - C13: consistent DB backup (SQLite .backup) BEFORE any write.
  - C6:  single transaction; rolls back on any failure.
  - Idempotent: skips rows already at target (status AND s5_reason).
  - R14:  manifest with schema_version / gen_model / pipeline_commit / created_at.
  - CI invariant: status=PASS implies factual.passed and reason not negative.

Usage:
    python3 scripts/apply_serving_gate.py            # dry-run (--check)
    python3 scripts/apply_serving_gate.py --apply     # back up + add column + write
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.serving_gate import (  # noqa: E402
    assert_invariant,
    derive_status,
    load_config,
)
from pipeline.stamp import get_pipeline_commit  # noqa: E402

DB_PATH = ROOT / "knowledge pipeline" / "maxwell.db"
MANIFEST = ROOT / "governance" / "serving_gate_manifest.jsonl"
REPORT = ROOT / "governance" / "serving_gate_20260919.md"

SCHEMA_VERSION = "3.0"
GEN_MODEL = "deterministic"  # re-derivation from the verification record — no model


def _column_exists(conn: sqlite3.Connection, name: str) -> bool:
    cols = [r[1] for r in conn.execute("PRAGMA table_info(fbs)").fetchall()]
    return name in cols


def _backup() -> Path:
    """Consistent SQLite backup via the online backup API (handles WAL)."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = DB_PATH.with_name(f"maxwell.db.bak_{ts}_pre_serving_gate")
    src = sqlite3.connect(DB_PATH)
    try:
        dst = sqlite3.connect(bak)
        with dst:
            src.backup(dst)
        dst.close()
    finally:
        src.close()
    return bak


def _load_rows(conn: sqlite3.Connection) -> list[dict]:
    has_reason = _column_exists(conn, "s5_reason")
    has_dup = _column_exists(conn, "duplicate_of")
    reason_col = "s5_reason" if has_reason else "NULL AS s5_reason"
    dup_col = "duplicate_of" if has_dup else "NULL AS duplicate_of"
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        f"SELECT fb_id, status, verification_results, {reason_col}, {dup_col} FROM fbs"
    ).fetchall()
    return [dict(r) for r in rows]


def _plan(rows: list[dict]) -> tuple[list[dict], Counter, Counter, Counter]:
    cfg = load_config()
    changes: list[dict] = []
    before = Counter(r["status"] for r in rows)
    after = Counter(before)
    reason_dist = Counter()

    for r in rows:
        target_status, target_reason = derive_status(
            r["verification_results"], cfg, duplicate_of=r.get("duplicate_of")
        )
        assert_invariant(target_status, r["verification_results"], target_reason, cfg)
        cur_status = r["status"] or ""
        cur_reason = r.get("s5_reason") or ""
        reason_dist[target_reason] += 1

        if cur_status != target_status:
            after[cur_status] -= 1
            after[target_status] += 1
        if cur_status == target_status and cur_reason == target_reason:
            continue  # already at target — idempotent skip

        changes.append({
            "fb_id": r["fb_id"],
            "old_status": cur_status,
            "new_status": target_status,
            "old_s5_reason": cur_reason,
            "new_s5_reason": target_reason,
        })

    return changes, before, after, reason_dist


def _apply(changes: list[dict]) -> Path:
    bak = _backup()
    print(f"  🔒 C13 backup: {bak}")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("BEGIN IMMEDIATE")
        if not _column_exists(conn, "s5_reason"):
            conn.execute("ALTER TABLE fbs ADD COLUMN s5_reason TEXT")
        for c in changes:
            conn.execute(
                "UPDATE fbs SET status=?, s5_reason=? WHERE fb_id=?",
                (c["new_status"], c["new_s5_reason"], c["fb_id"]),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"❌ apply failed, rolled back (DB intact): {e}", file=sys.stderr)
        raise
    conn.close()

    now = datetime.now(timezone.utc).isoformat()
    commit = get_pipeline_commit()
    records = [
        {**c,
         "schema_version": SCHEMA_VERSION,
         "gen_model": GEN_MODEL,
         "pipeline_commit": commit,
         "created_at": now,
         "source": "config/serving_gate.yaml (D274a)"}
        for c in changes
    ]
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    conn = sqlite3.connect(DB_PATH)
    ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
    conn.close()
    print(f"  ✅ integrity_check: {ok}")
    return bak


def _write_report(before: Counter, after: Counter, reason_dist: Counter, n: int,
                  de_served: int, restored: int, bak: Path | None) -> None:
    lines = [
        "# Serving gate — 0a / G17 (D274a) — before/after snapshot",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"DB: `knowledge pipeline/maxwell.db` ({n} rows)",
        f"Backup: `{bak.name if bak else '(dry-run — no backup)'}`",
        "",
        "## Status distribution",
        "",
        "| status | before | after |",
        "|---|---|---|",
        *[f"| {s} | {before[s]} | {after[s]} |" for s in sorted(set(before) | set(after))],
        "",
        f"- de-served (PASS → QUARANTINE): **{de_served}**",
        f"- restored (QUARANTINE → PASS): **{restored}**",
        "",
        "## Typed s5_reason distribution (after)",
        "",
        "| reason | rows |",
        "|---|---|",
        *[f"| {r} | {c} |" for r, c in sorted(reason_dist.items(), key=lambda kv: -kv[1])],
        "",
        "Rule: status = PASS iff `verification_results[factual].passed`, else QUARANTINE.",
        "CI invariant: PASS ⟹ factual.passed and reason ∉ {contra, no_evidence, mech_fail, vacuous, evidence_contaminated}.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Serving gate: status := f(verification record) (D274a)")
    ap.add_argument("--apply", action="store_true", help="back up + add s5_reason + write (default: dry-run)")
    args = ap.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    rows = _load_rows(conn)
    conn.close()

    changes, before, after, reason_dist = _plan(rows)
    de_served = sum(1 for c in changes if c["old_status"] == "PASS" and c["new_status"] == "QUARANTINE")
    restored = sum(1 for c in changes if c["old_status"] == "QUARANTINE" and c["new_status"] == "PASS")

    print("🧭 Serving gate (D274a / G17) — status := f(verification record)")
    print(f"   rows: {len(rows)} | to write (status or s5_reason change): {len(changes)}")
    print(f"   before: PASS {before['PASS']} | QUARANTINE {before['QUARANTINE']}")
    print(f"   after : PASS {after['PASS']} | QUARANTINE {after['QUARANTINE']}")
    print(f"   de-served (PASS→QUARANTINE): {de_served} | restored (QUARANTINE→PASS): {restored}")
    print(f"   s5_reason dist: {dict(reason_dist)}")

    if not changes:
        print("   ✅ nothing to do.")
        return 0

    if not args.apply:
        print("\n   (dry-run) pass --apply to back up + add s5_reason + write.")
        return 0

    bak = _apply(changes)
    _write_report(before, after, reason_dist, len(rows), de_served, restored, bak)
    print(f"   ✅ applied {len(changes)} writes. Manifest: {MANIFEST}")
    print(f"   📄 report: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
