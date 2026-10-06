#!/usr/bin/env python3
"""check_domain_cardinality.py — BUG-631 READER-limb: re-measure the committed store for per-FB domain-cardinality violations.

WHY THIS EXISTS (BUG-631, D-2838). ``pipeline_config.yaml`` declares ``max_domains_per_fb: 5``, but the value
was DETECTED ("Too many domains") and NOT ENFORCED: the write-path salvage dropped only NON-canonical labels, so a
row carrying 6-7 VALID domains was written unchanged (52 FBs, every one ``classification_status=CLEAN``). D-2838
landed the WRITER-limb (``_enforce_domain_cardinality`` in ``pipeline/stage4_merge.py``) that truncates
deterministically at the cap and degrades CLEAN -> FALLBACK so a truncated row is never indistinguishable from a
compliant one. This is the READER-limb: it re-measures the COMMITTED store (``DB_PATH``, the authoritative
``knowledge pipeline/maxwell.db``) and reports every FB whose canonical ``domains`` JSON array exceeds the cap.
D-2838's BUG-631 stays OPEN until this re-measure runs and the historical over-cap FBs are re-derived.

THE RULE (one rule, one home):
  * count the canonical ``domains`` array per FB. ``domains_raw`` is the PRE-canonical classifier input, NOT the
    committed classification, and is deliberately NOT counted (counting it would double-report the same defect);
  * an FB with ``len(domains) > max_domains_per_fb`` is OVER-CAP and is REPORTED (never silently tolerated);
  * exit non-zero when any over-cap FB is found, so the reader doubles as a fail-closed gate in ``just health``;
  * a ``domains`` cell that is not a JSON array of strings is a PARSE-DEFECT, reported separately and never
    conflated with an over-cap count (C16: a mis-parse must not read as a clean zero).

BOUNDARY: reads the authoritative store only (``DB_PATH``, env ``db_path`` override). A consumer pointed at a
stale store (``data/maxwell.db``) is a BUG-524 hazard that ``check_store_authority.py`` already fails; this reader
trusts the declared authoritative path and does not re-walk the store register.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import safe_write  # C6: crash-safe writes (tempfile -> fsync -> replace)
from pipeline.pipeline_paths import DB_PATH, MAX_DOMAINS_PER_FB  # C12: single config source

EXIT_CLEAN, EXIT_DRIFT, EXIT_OWED = 0, 1, 2
SCHEMA_VERSION = "1.0"
DOMAINS_COL = "domains"
FB_ID_COL = "fb_id"
STATUS_COL = "classification_status"


def count_domains(cell: str | None) -> tuple[int, str | None]:
    """Parse one ``domains`` cell and return ``(count, defect_reason_or_None)``.

    A well-formed cell is a JSON array of strings (the canonical committed classification). A defect is any
    cell that is neither NULL/empty (zero domains) nor a JSON array of strings — the mis-parse is NAMED, not
    silently counted as zero (C16).
    """
    if cell is None:
        return 0, None
    text = cell.strip()
    if text == "":
        return 0, None
    try:
        parsed: Any = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        return 0, f"not JSON: {exc}"
    if not isinstance(parsed, list):
        return 0, f"not a list: {type(parsed).__name__}"
    if not all(isinstance(item, str) for item in parsed):
        return 0, "list contains non-string item(s)"
    return len(parsed), None


def measure_store(db_path: Path, max_domains: int) -> dict[str, Any]:
    """Read the committed store and return the cardinality measurement.

    Returns a mapping with ``total_fbs``, ``over_cap`` (list of FB dicts), and ``parse_defects`` (list of
    ``{fb_id, reason}``). Pure of CLI concerns so the control test can drive it against a synthetic store.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"authoritative store not found: {db_path}")

    over_cap: list[dict[str, Any]] = []
    parse_defects: list[dict[str, str]] = []
    total = 0

    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            f"SELECT {FB_ID_COL}, {DOMAINS_COL}, {STATUS_COL} FROM fbs"
        )
        for row in cur:
            total += 1
            fb_id = row[FB_ID_COL] or ""
            status = row[STATUS_COL] or ""
            count, defect = count_domains(row[DOMAINS_COL])
            if defect is not None:
                parse_defects.append({"fb_id": fb_id, "reason": defect})
                continue
            if count > max_domains:
                over_cap.append(
                    {
                        "fb_id": fb_id,
                        "domain_count": count,
                        "classification_status": status,
                    }
                )
    finally:
        conn.close()

    return {
        "total_fbs": total,
        "over_cap": over_cap,
        "parse_defects": parse_defects,
    }


def build_receipt(measurement: dict[str, Any], db_path: Path, max_domains: int) -> dict[str, Any]:
    """Assemble the machine-readable receipt for a run (all fields provenance-stamped, D-274d spirit)."""
    over_cap = measurement["over_cap"]
    return {
        "schema_version": SCHEMA_VERSION,
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "db_path": str(db_path),
        "max_domains_per_fb": max_domains,
        "total_fbs": measurement["total_fbs"],
        "over_cap_count": len(over_cap),
        "over_cap": over_cap,
        "parse_defect_count": len(measurement["parse_defects"]),
        "parse_defects": measurement["parse_defects"],
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry: measure, write an optional receipt (C6), and return the fail-closed exit code."""
    parser = argparse.ArgumentParser(
        description="BUG-631 reader-limb: re-measure the committed store for per-FB domain-cardinality violations."
    )
    parser.add_argument(
        "--json",
        metavar="PATH",
        default=None,
        help="write a machine-readable receipt to PATH (C6 crash-safe); omitted -> stdout only",
    )
    parser.add_argument(
        "--max-domains",
        type=int,
        default=None,
        help="override the cap (config-first default from pipeline_config.max_domains_per_fb)",
    )
    args = parser.parse_args(argv)

    max_domains = args.max_domains if args.max_domains is not None else MAX_DOMAINS_PER_FB
    if max_domains < 1:
        print(f"FAIL-CLOSED: max-domains must be >= 1, got {max_domains}", file=sys.stderr)
        return EXIT_OWED

    try:
        measurement = measure_store(DB_PATH, max_domains)
    except (FileNotFoundError, sqlite3.Error) as exc:  # C16: log AND exit non-zero, never a silent empty
        print(f"FAIL-CLOSED: cannot read authoritative store {DB_PATH}: {exc}", file=sys.stderr)
        return EXIT_OWED

    receipt = build_receipt(measurement, DB_PATH, max_domains)

    print(
        f"domain-cardinality: {receipt['over_cap_count']} over-cap FB(s) of "
        f"{receipt['total_fbs']} total (cap={max_domains}); "
        f"{receipt['parse_defect_count']} parse-defect cell(s)"
    )
    for fb in receipt["over_cap"]:
        print(
            f"  OVER-CAP {fb['fb_id']}: {fb['domain_count']} domains, "
            f"status={fb['classification_status']}"
        )
    for defect in receipt["parse_defects"]:
        print(f"  PARSE-DEFECT {defect['fb_id']}: {defect['reason']}")

    if args.json:
        safe_write(Path(args.json), json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        print(f"receipt written: {args.json}")

    if receipt["parse_defect_count"] > 0:
        return EXIT_OWED  # a mis-parse is a measurement failure, never a clean pass
    if receipt["over_cap_count"] > 0:
        return EXIT_DRIFT  # over-cap FBs found -> the historical re-derivation is still owed
    return EXIT_CLEAN


if __name__ == "__main__":
    raise SystemExit(main())
