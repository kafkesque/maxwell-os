#!/usr/bin/env python3
"""rederive_domain_cardinality.py — BUG-631 re-derivation: apply the D-2838 writer-limb to the historical over-cap FBs.

WHY THIS EXISTS (BUG-631, D-2838). ``pipeline_config.yaml`` declared ``max_domains_per_fb: 5`` at filing (now 7 via C12), but the value
was DETECTED ("Too many domains") and NOT ENFORCED on the post-commit paths that wrote the 52 historical FBs now
carrying 6-7 VALID domains (every one ``classification_status=CLEAN``). D-2838 landed the WRITER-limb
(``pipeline/stage4_merge._enforce_domain_cardinality``) that truncates deterministically at the cap and degrades
CLEAN -> FALLBACK so a truncated row is never indistinguishable from a compliant one. The READER-limb
(``scripts/check_domain_cardinality.py``) measures the committed store and reports those 52 over-cap FBs. This
script is the missing THIRD act: it RE-DERIVES the historical rows THROUGH the writer-limb so the committed store
converges with the contract, and ``check_domain_cardinality.py`` returns EXIT=0.

THE RULE (one rule, one home — D-2644). The truncation contract lives ONLY in
``pipeline/stage4_merge._enforce_domain_cardinality``. This script IMPORTS it; it never re-implements the
truncation/drop/degrade logic, so a re-derivation can never drift from the writer that enforces the same rule on
new rows. The reader-limb's ``count_domains`` parse is deliberately NOT reused here because this script needs the
list itself, not just its length; the JSON-array-of-strings shape is re-asserted inline (a parse-defect is named,
never silently counted, C16).

WHAT IT DOES, per over-cap FB (deterministic, LLM-free, idempotent):
  * ``domains``               -> truncated to the first ``max_domains_per_fb`` (model order preserved);
  * ``classification_status`` -> CLEAN -> FALLBACK (only CLEAN degrades, matching the writer-limb);
  * ``classification_error``  -> receipt appended: "domain cardinality N>M: truncated to cap (dropped [...])";
  * ``domains_raw``           -> UNTOUCHED (the pre-canonical classifier input is preserved verbatim);
  * every other column (stamps, provenance, source_*) is UNTOUCHED — this is a classification-contract
    repair, not a regeneration, so no R14 stamp is rewritten (a repair is not a re-generation).

Crash-safe (C6/C13): a transaction-consistent backup is taken via SQLite's online-backup API (``Connection.backup``
— NOT ``shutil.copy2``, which can capture a torn WAL state) before the first write; all updates then land in a
single transaction. Idempotent: a re-run finds 0 over-cap rows and writes nothing.

BOUNDARY: mutates the authoritative store (``DB_PATH``) only. It does NOT touch ``data/maxwell.db`` (the BUG-524
stale-store hazard ``check_store_authority.py`` already fails); it trusts ``pipeline.pipeline_paths.DB_PATH``.

Usage:
    python3 scripts/rederive_domain_cardinality.py              # dry-run (default): report, no writes
    python3 scripts/rederive_domain_cardinality.py --apply      # backup + single-txn write + re-measure
    python3 scripts/rederive_domain_cardinality.py --db PATH    # operate on a non-default store (tests)
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import DB_PATH, MAX_DOMAINS_PER_FB
from pipeline.stage4_merge import _enforce_domain_cardinality  # one rule, one home (D-2838)

EXIT_CLEAN = 0
EXIT_DRIFT = 1
EXIT_OWED = 2


def parse_domains(cell: str | None) -> list[str]:
    """Parse a canonical ``domains`` cell into a list of strings.

    NULL/empty -> ``[]`` (a FB with no committed domains). A non-JSON-array or a list with a non-string item is a
    PARSE-DEFECT and raises ``ValueError`` so the caller names it and aborts — never silently counts it as zero (C16).
    """
    if cell is None:
        return []
    text = cell.strip()
    if text == "":
        return []
    parsed: Any = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError(f"domains cell is not a JSON array: {type(parsed).__name__}")
    if not all(isinstance(item, str) for item in parsed):
        raise ValueError("domains cell contains a non-string item")
    return parsed


def select_over_cap(conn: sqlite3.Connection, max_domains: int) -> list[tuple[sqlite3.Row, list[str]]]:
    """Return ``(row, domains_list)`` for every FB whose canonical ``domains`` array exceeds the cap."""
    over_cap: list[tuple[sqlite3.Row, list[str]]] = []
    for row in conn.execute(
        "SELECT fb_id, domains, classification_status, classification_error FROM fbs"
    ):
        domains = parse_domains(row["domains"])
        if len(domains) > max_domains:
            over_cap.append((row, domains))
    return over_cap


def derive_fix(row: sqlite3.Row, domains: list[str], max_domains: int) -> tuple[list[str], dict[str, str]]:
    """Apply the writer-limb to one row; return ``(fixed_domains, mutated_class_data)``.

    ``class_data`` seeds ``classification_status``/``classification_error`` from the row so the writer-limb's
    CLEAN-only degradation and receipt-append semantics match exactly what a fresh S4 write would have produced.
    """
    class_data: dict[str, str] = {
        "classification_status": (row["classification_status"] or "CLEAN"),
        "classification_error": (row["classification_error"] or ""),
    }
    fixed = _enforce_domain_cardinality(domains, class_data, max_domains)
    return fixed, class_data


def backup_db(db: Path) -> Path:
    """Take a transaction-consistent backup via SQLite's online-backup API (C6/C13, not a torn shutil.copy2)."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = db.with_suffix(db.suffix + f".bak_redomain_cardinality_{stamp}")
    src = sqlite3.connect(str(db))
    try:
        dst = sqlite3.connect(str(backup))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return backup


def measure_after(conn: sqlite3.Connection, max_domains: int) -> int:
    """Re-count over-cap rows post-apply; returns the remaining count (used as the fail-closed verify)."""
    return len(select_over_cap(conn, max_domains))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="BUG-631 re-derivation: apply the D-2838 writer-limb to historical over-cap FBs."
    )
    parser.add_argument("--db", type=Path, default=DB_PATH, help="store to repair (config-first default: DB_PATH)")
    parser.add_argument("--apply", action="store_true", help="write the repair (default is dry-run, no writes)")
    parser.add_argument(
        "--max-domains",
        type=int,
        default=None,
        help="override the cap (config-first default: pipeline_config.max_domains_per_fb)",
    )
    args = parser.parse_args(argv)

    max_domains = args.max_domains if args.max_domains is not None else MAX_DOMAINS_PER_FB
    if max_domains < 1:
        print(f"FAIL-CLOSED: max-domains must be >= 1, got {max_domains}", file=sys.stderr)
        return EXIT_OWED

    if not args.db.exists():
        print(f"FAIL-CLOSED: authoritative store not found: {args.db}", file=sys.stderr)
        return EXIT_OWED

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row
    try:
        over_cap = select_over_cap(conn, max_domains)
        print(f"rederive-domain-cardinality: {len(over_cap)} over-cap FB(s) of cap {max_domains}")

        if not args.apply:
            for row, domains in over_cap:
                fixed, _ = derive_fix(row, domains, max_domains)
                dropped = domains[max_domains:]
                print(
                    f"  WOULD-FIX {row['fb_id']}: {len(domains)} -> {len(fixed)} domains, "
                    f"status {row['classification_status'] or 'CLEAN'} -> FALLBACK, "
                    f"dropped {dropped!r}"
                )
            print("  🔍 --dry-run: no writes (pass --apply to write)")
            return EXIT_DRIFT if over_cap else EXIT_CLEAN

        if not over_cap:
            print("  ✅ nothing to re-derive (idempotent)")
            return EXIT_CLEAN

        backup = backup_db(args.db)
        print(f"  💾 transaction-consistent backup -> {backup.name}")

        try:
            conn.execute("BEGIN")
            for row, domains in over_cap:
                fixed, class_data = derive_fix(row, domains, max_domains)
                conn.execute(
                    "UPDATE fbs SET domains = ?, classification_status = ?, classification_error = ? WHERE fb_id = ?",
                    (json.dumps(fixed), class_data["classification_status"], class_data["classification_error"], row["fb_id"]),
                )
            conn.commit()
        except Exception:  # noqa: BLE001 — C16: log AND roll back, never a silent partial write
            conn.rollback()
            raise

        remaining = measure_after(conn, max_domains)
        print(f"  ✅ {len(over_cap)} FB(s) re-derived through the D-2838 writer-limb")
        print(f"  ✅ re-measure: {remaining} over-cap FB(s) remaining (expect 0)")
        return EXIT_CLEAN if remaining == 0 else EXIT_DRIFT
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
