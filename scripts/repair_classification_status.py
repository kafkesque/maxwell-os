#!/usr/bin/env python3
"""repair_classification_status.py — T-122/D-2987: re-derive `classification_status` from the row's own `status`.

WHY THIS EXISTS
---------------
`classification_status` is 'CLEAN' on 7,648/7,648 canonical rows while the store's OWN `status`
column holds 3,136 QUARANTINE rows. Two statuses on one row is the D-2987 defect on the wire:
an agent reads 'CLEAN' and cannot see the quarantine (41% of the served truth). The column is
FALSE, not merely unvarying (config/store_columns.yaml `status: debt`).

The D2184 enum is CLEAN | FALLBACK | FAILED, and schemas.py already documents FAILED ==
"quarantined". This script re-derives the stored value from the row's OWN `status` — the
"row-level status the payload already carries" (config/served_fields.yaml#declared[classification_status],
owner word `keep-and-repair`, granted 2026-10-14 D-2994).

THE RULE IT APPLIES (no rule is minted here)
--------------------------------------------
    status=PASS        -> classification_status='CLEAN'     (trusted, canonical)
    status=FLAG        -> classification_status='FALLBACK'  (degraded, needs review)
    status=QUARANTINE  -> classification_status='FAILED'    (not trusted)
    any other status   -> fail-closed: counted + named, NEVER written (C16)

DETERMINISTIC and LLM-FREE (C1): no judgement, prediction or model call — a pure derivation from
the row's own status, so the repair cannot drift from what a re-verification would have written.

SCOPE (D-2881): the canonical run only (`pipeline_run_id = CANONICAL_RUN`). Non-canonical rows are
counted and reported, never written.

SAFETY
------
C13: a SQLite `.backup` BEFORE the first write, named in the receipt.
C6 : ONE transaction (BEGIN IMMEDIATE); the post-state is RE-DERIVED INSIDE it and COMMITTED only
     when the re-derivation is clean — otherwise ROLLBACK and exit 1.
C16: an unevaluable status is never written and never silently skipped; it is counted and named.
R14: a receipt carrying counts, the backup path, deriver identity and the pipeline commit.

Usage:
    python3 scripts/repair_classification_status.py             # --check: read-only report (default)
    python3 scripts/repair_classification_status.py --apply     # back up + write + verify (one transaction)
    python3 scripts/repair_classification_status.py --selftest  # known-answer controls only
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import CANONICAL_RUN, DB_PATH  # noqa: E402

REPO: Path = Path(__file__).resolve().parent.parent
BACKUP_DIR: Path = REPO / "backups"
RECEIPT: Path = REPO / "governance" / "evidence" / "classification_status_repair_receipt.json"
SCHEMA_VERSION: str = "1.0"
PREFIX: str = "repair-classification-status"
EXIT_OK: int = 0
EXIT_DEFECT: int = 1

# D2184 monotonic-trust mapping (PASS/FLAG/QUARANTINE -> CLEAN/FALLBACK/FAILED). The mapping is the
# WHOLE rule; a status outside it is refused rather than guessed (C16).
STATUS_TO_CLASSIFICATION: dict[str, str] = {
    "PASS": "CLEAN",
    "FLAG": "FALLBACK",
    "QUARANTINE": "FAILED",
}


def _conn(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def _backup(db_path: Path) -> Path:
    """C13: SQLite .backup to a stamped file BEFORE the first write."""
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"{db_path.name}.bak_classification_status_{stamp}"
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    src = _conn(db_path)
    dst = sqlite3.connect(dest)
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
    return dest


def _scan(db_path: Path) -> dict[str, Any]:
    """Read-only census: current classification_status per status, on the canonical run."""
    conn = _conn(db_path)
    cur = conn.execute(
        "SELECT status, classification_status, COUNT(*) FROM fbs "
        "WHERE pipeline_run_id = ? GROUP BY status, classification_status ORDER BY COUNT(*) DESC",
        (CANONICAL_RUN,),
    )
    cells = {f"{s}|{c}": n for s, c, n in cur.fetchall()}
    cur = conn.execute(
        "SELECT status, COUNT(*) FROM fbs WHERE pipeline_run_id = ? GROUP BY status",
        (CANONICAL_RUN,),
    )
    by_status = {s: n for s, n in cur.fetchall()}
    cur = conn.execute("SELECT COUNT(*) FROM fbs WHERE pipeline_run_id != ? OR pipeline_run_id IS NULL", (CANONICAL_RUN,))
    non_canonical = cur.fetchone()[0]
    conn.close()
    return {"cells": cells, "by_status": by_status, "non_canonical": non_canonical}


def _project(scan: dict[str, Any]) -> tuple[dict[str, int], list[str]]:
    """Project the D2184 mapping onto the census: (to_write, unevaluable_statuses)."""
    to_write: dict[str, int] = {}
    unevaluable: list[str] = []
    for status, n in scan["by_status"].items():
        target = STATUS_TO_CLASSIFICATION.get(status)
        if target is None:
            unevaluable.append(status)
            continue
        to_write[f"{status}->{target}"] = n
    return to_write, unevaluable


def _report(scan: dict[str, Any]) -> tuple[int, list[str]]:
    """Print the census; return (rows_changing, unevaluable) for a fail-closed --check.

    Rows whose classification_status ALREADY matches the D2184 target are no-ops. `rows_changing`
    counts only canonical-run cells that disagree; a non-canonical row is reported by `_scan`, never
    counted here (D-2881). `unevaluable` is a status value outside the declared D2184 mapping.
    """
    to_write, unevaluable = _project(scan)
    print(f"{PREFIX}: canonical run = {CANONICAL_RUN}")
    print("  current (status|classification_status) counts:")
    for cell, n in sorted(scan["cells"].items(), key=lambda kv: -kv[1]):
        print(f"    {cell:24s} {n}")
    print(f"  non-canonical rows (reported, never written): {scan['non_canonical']}")
    if unevaluable:
        print(f"  ❌ UNEVALUABLE status values (fail-closed, never written): {unevaluable}")
    print("  projected writes:")
    for k, n in sorted(to_write.items()):
        print(f"    {k:24s} {n}")
    # Rows whose classification_status ALREADY matches the D2184 target are no-ops; the
    # repair rewrites only the cells that currently disagree (C6: the re-derivation inside
    # the transaction proves the same count).
    rows_changing = sum(
        n
        for cell, n in scan["cells"].items()
        if "|" in cell
        and (status := cell.split("|", 1)[0]) in STATUS_TO_CLASSIFICATION
        and STATUS_TO_CLASSIFICATION[status] != cell.split("|", 1)[1]
    )
    if rows_changing:
        print(f"  → DIRTY: {rows_changing} row(s) will be rewritten")
    else:
        print("  → CLEAN: classification_status already matches status (no write)")
    return rows_changing, unevaluable


def _selftest() -> int:
    # Known-answer controls on the pure mapping (no DB needed).
    ok = STATUS_TO_CLASSIFICATION == {"PASS": "CLEAN", "FLAG": "FALLBACK", "QUARANTINE": "FAILED"}
    assert ok, "D2184 mapping drift"
    # fail-closed: an unknown status must not map.
    assert STATUS_TO_CLASSIFICATION.get("WAT") is None
    assert "WAT" not in STATUS_TO_CLASSIFICATION
    # scan projection: a census with only PASS/QUARANTINE projects exactly.
    scan = {"by_status": {"PASS": 4513, "QUARANTINE": 3136}, "cells": {}, "non_canonical": 1}
    to_write, unevaluable = _project(scan)
    assert to_write == {"PASS->CLEAN": 4513, "QUARANTINE->FAILED": 3136}, to_write
    assert unevaluable == [], unevaluable
    print(f"{PREFIX}: selftest 5/5 ok (mapping, fail-closed, projection)")
    return EXIT_OK


def _apply(db_path: Path) -> int:
    scan_before = _scan(db_path)
    to_write, unevaluable = _project(scan_before)
    if unevaluable:
        print(f"{PREFIX}: ❌ unevaluable status {unevaluable} — refusing to write (C16)")
        return EXIT_DEFECT
    if not to_write:
        print(f"{PREFIX}: nothing to write — already clean")
        return EXIT_OK

    backup = _backup(db_path)
    print(f"{PREFIX}: C13 backup written: {backup}")

    conn = _conn(db_path)
    changed = 0
    try:
        conn.execute("BEGIN IMMEDIATE")
        for status, target in STATUS_TO_CLASSIFICATION.items():
            cur = conn.execute(
                "UPDATE fbs SET classification_status = ? "
                "WHERE pipeline_run_id = ? AND status = ? AND classification_status != ?",
                (target, CANONICAL_RUN, status, target),
            )
            changed += cur.rowcount
        # C6: re-derive the post-state INSIDE the transaction; only commit if it matches projection.
        scan_after = {
            "cells": {}, "by_status": {}, "non_canonical": -1,
        }
        cur = conn.execute(
            "SELECT status, classification_status, COUNT(*) FROM fbs WHERE pipeline_run_id = ? "
            "GROUP BY status, classification_status",
            (CANONICAL_RUN,),
        )
        for s, c, n in cur.fetchall():
            scan_after["by_status"][s] = scan_after["by_status"].get(s, 0) + n
            expected = STATUS_TO_CLASSIFICATION.get(s)
            if expected is not None and c != expected:
                conn.execute("ROLLBACK")
                print(f"{PREFIX}: ❌ post-state {s}={c} (expected {expected}) — ROLLBACK (C6)")
                return EXIT_DEFECT
        conn.execute("COMMIT")
    except Exception as e:
        conn.execute("ROLLBACK")
        print(f"{PREFIX}: ❌ transaction failed, ROLLBACK: {type(e).__name__}: {e}")
        return EXIT_DEFECT
    finally:
        conn.close()

    scan_after_real = _scan(db_path)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "task": "T-122",
        "decision": "D-2994 (owner word keep-and-repair) / D-2987 (two-statuses defect)",
        "deriver": f"{PREFIX}.py",
        "mapping": STATUS_TO_CLASSIFICATION,
        "canonical_run": CANONICAL_RUN,
        "backup": str(backup),
        "before": scan_before,
        "rows_changed": changed,
        "after": scan_after_real,
        "unevaluable_refused": unevaluable,
        "pipeline_commit": _pipeline_commit(),
        "timestamp_utc": datetime.now(UTC).isoformat(),
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    tmp = RECEIPT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    tmp.replace(RECEIPT)
    print(f"{PREFIX}: {changed} rows rewritten; receipt: {RECEIPT}")
    print(f"  after: {scan_after_real['by_status']} classification_status distribution")
    return EXIT_OK


def _pipeline_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10, cwd=REPO
        )
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description="T-122 classification_status re-derivation")
    ap.add_argument("--check", action="store_true", help="read-only report (default)")
    ap.add_argument("--apply", action="store_true", help="back up + write + verify (one transaction)")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls only")
    ap.add_argument("--db", type=str, default=str(DB_PATH), help="override DB path")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"{PREFIX}: ❌ DB not found: {db_path}")
        return EXIT_DEFECT

    if args.apply:
        return _apply(db_path)

    # --check (default) is a fail-closed PARITY CHECK, not just a report: a canonical row whose
    # classification_status disagrees with its own status (D2184: FAILED == quarantined) is a WRONG
    # VALUE (the D-2987 defect recurring), so drift exits DEFECT (1). A non-canonical row is reported,
    # never written and never a failure (D-2881).
    scan = _scan(db_path)
    rows_changing, unevaluable = _report(scan)
    if unevaluable or rows_changing:
        print(f"{PREFIX}: ❌ {rows_changing} drifting row(s) / unevaluable {unevaluable} — fail-closed (C16)")
        return EXIT_DEFECT
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
