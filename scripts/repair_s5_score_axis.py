#!/usr/bin/env python3
"""repair_s5_score_axis.py - BUG-745/D-2970: re-derive the S5 score axis from the store's OWN record.

WHY THIS EXISTS
---------------
stage6's verification-scoped write (D-2933 rule V) carried only ONE half of the SCORE AXIS
(`needs_human_review`) in `stage6.s5_owned_columns`, so the D-2822 re-verification
(or-entail + AND-no-contra @ 0.5) rewrote verification_results / status / s5_reason /
epistemic_status on all 6,591 rows and left the CONFIDENCE of 2,247 of them computed by the
SUPERSEDED majority@0.1 aggregation. `confidence_score` and `needs_human_review` are ONE rule with
two outputs (pipeline/serving_gate.py::derive_conf_and_review, BUG-502) - so the store was holding a
value its own verification record does not derive. That is the D274h class of defect, on the score
axis, and it is MEASURED, not suspected: the stored confidence is byte-identical on 6,591/6,591 rows
between the Oct-9 store and HEAD while `factual.passed` flipped on exactly those 2,247
(scripts/check_s5_score_axis.py is the rail that found it).

The CONFIG half is fixed (D-2970: both halves are written again, and the stage6 preflight now refuses
a scope that carries only part of a declared axis). This script is the DATA half: it makes the stored
corpus agree with the records it already holds.

THE RULE IT APPLIES (no rule is minted here)
--------------------------------------------
The value comes from the ONE home - pipeline/serving_gate.py::derive_conf_and_review over
(pipeline/stage5_verify.py::_check_enrichment_quality, the stored ISOR, the stored record).
DETERMINISTIC and LLM-FREE (C1/D-343): nothing in this path is a judgement, a prediction or a model
call, so the repair cannot drift from the value a re-verification would have written.

POPULATION (D-2960/D-2942 - a role is scoped to a DECLARED, MEASURED population)
--------------------------------------------------------------------------------
* roles that CARRY a factual claim (the complement of serving_gate.content_types_without_factual_claim):
  re-derive, and repair only what differs. This is the committed corpus.
* roles with NO factual claim: the score axis is ABSENT BY DESIGN (D-2942/D-2957) - confidence NULL,
  needs_human_review false. Never written here. A VALUE on such a role is REPORTED as a violation,
  because it is an unmeasured claim, not a repair job.

SAFETY
------
C13: a SQLite `.backup` BEFORE the first write, named in the receipt.
C6 : ONE transaction (BEGIN IMMEDIATE); the post-state is RE-DERIVED INSIDE it and the transaction is
     COMMITTED only when the re-derivation is clean - otherwise ROLLBACK and exit 1.
C16: an unevaluable row is never written and never silently skipped; it is counted and named.
R14: a receipt carrying the counts, the backup, the deriver identity and the pipeline commit.

Usage:
    python3 scripts/repair_s5_score_axis.py             # --check: read-only report (default)
    python3 scripts/repair_s5_score_axis.py --apply     # back up + write + verify (one transaction)
    python3 scripts/repair_s5_score_axis.py --selftest  # known-answer controls only
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import DB_PATH, S6_S5_AXIS_COLUMNS  # noqa: E402
from pipeline.serving_gate import (  # noqa: E402
    content_types_without_factual_claim,
    derive_conf_and_review,
)
from pipeline.stage5_verify import _check_enrichment_quality  # noqa: E402

REPO: Path = Path(__file__).resolve().parent.parent
BACKUP_DIR: Path = REPO / "backups"
RECEIPT: Path = REPO / "governance" / "evidence" / "s5_score_axis_repair_receipt.json"
SCHEMA_VERSION: str = "1.0"
PREFIX: str = "repair-s5-score-axis"
EXIT_OK: int = 0
EXIT_DEFECT: int = 1
TOLERANCE: float = 1e-9  # the rail's own comparison tolerance (scripts/check_s5_score_axis.py)

# The two columns this repair owns = the DECLARED score axis (config stage6.s5_axis_columns). A
# script that repairs an axis must not name its own members: if the declaration changes, this raises
# at import instead of repairing the wrong pair (C12/C16).
_AXIS: tuple[str, ...] = tuple(S6_S5_AXIS_COLUMNS.get("score_axis", ()))
CONF_COL: str = "confidence_score"
REVIEW_COL: str = "needs_human_review"
if CONF_COL not in _AXIS or REVIEW_COL not in _AXIS:
    raise RuntimeError(
        f"{PREFIX}: the declared score_axis {_AXIS!r} does not carry both {CONF_COL!r} and "
        f"{REVIEW_COL!r} - refusing to repair an axis it cannot name (D-2970/BUG-745, C16)"
    )


def derive_axis(row: dict[str, Any]) -> tuple[float, bool] | None:
    """Re-derive the stored row's score axis through the ONE home, or None when it is unevaluable.

    Args:
        row: the stored row (ALL columns - a column subset makes the enrichment check read empty
            fields and invent a defect, which is why the rail reads the full row too).

    Returns:
        (confidence, needs_human_review), or None when the record carries no factual/mechanism check.
    """
    try:
        results = json.loads(row.get("verification_results") or "[]")
    except (TypeError, ValueError):
        return None
    factual = next((x for x in results if x.get("check_name") == "factual"), None)
    mech = next((x.get("score") for x in results if x.get("check_name") == "mechanism_quality"), None)
    if factual is None or mech is None:
        return None
    isor = row.get("isor")
    isor = json.loads(isor) if isinstance(isor, str) else (isor or {})
    _ok, enrich, _detail = _check_enrichment_quality(dict(row))
    return derive_conf_and_review(bool(factual.get("passed")), float(mech), float(enrich), isor)


def classify(rows: list[dict[str, Any]], roles_without_claim: frozenset[str]) -> dict[str, list[dict[str, Any]]]:
    """Sort every stored row into the repair's buckets (no write, no model call).

    Args:
        rows: every stored row.
        roles_without_claim: the DECLARED roles that carry no factual claim (serving_gate).

    Returns:
        {'stale': [...], 'ok': [...], 'no_claim_ok': [...], 'no_claim_value': [...], 'unevaluable': [...]}
        where a 'stale' entry carries the stored and the derived values plus the per-column diff.
    """
    buckets: dict[str, list[dict[str, Any]]] = {
        "stale": [], "ok": [], "no_claim_ok": [], "no_claim_value": [], "unevaluable": [],
    }
    for row in rows:
        derived = derive_axis(row)
        role = str(row.get("content_type") or "")
        if derived is None:
            if role in roles_without_claim:
                present = {c: row.get(c) for c in (CONF_COL, REVIEW_COL)}
                has_value = present[CONF_COL] is not None or bool(present[REVIEW_COL])
                bucket = "no_claim_value" if has_value else "no_claim_ok"
                buckets[bucket].append({"fb_id": str(row.get("fb_id")), "role": role, "stored": present})
            else:
                buckets["unevaluable"].append({"fb_id": str(row.get("fb_id")), "role": role})
            continue
        conf, review = derived
        stored_conf = row.get(CONF_COL)
        stored_review = bool(row.get(REVIEW_COL))
        conf_moved = stored_conf is None or abs(float(stored_conf) - conf) > TOLERANCE
        review_moved = stored_review != review
        if conf_moved or review_moved:
            buckets["stale"].append({
                "fb_id": str(row.get("fb_id")),
                "stored": {CONF_COL: stored_conf, REVIEW_COL: stored_review},
                "derived": {CONF_COL: conf, REVIEW_COL: review},
                "moved": [c for c, m in ((CONF_COL, conf_moved), (REVIEW_COL, review_moved)) if m],
            })
        else:
            buckets["ok"].append({"fb_id": str(row.get("fb_id"))})
    return buckets


def load_rows(con: sqlite3.Connection) -> list[dict[str, Any]]:
    """Read every stored row (the full row: the derivation needs more than the axis columns)."""
    con.row_factory = sqlite3.Row
    return [dict(r) for r in con.execute("SELECT * FROM fbs")]


def report(buckets: dict[str, list[dict[str, Any]]]) -> None:
    """Print the measured buckets. OWED work and repairable work are printed apart, never summed."""
    print(f"{PREFIX}: " + " | ".join(f"{k} {len(v)}" for k, v in sorted(buckets.items())))
    moved: Counter[str] = Counter()
    for entry in buckets["stale"]:
        for column in entry["moved"]:
            moved[column] += 1
    if moved:
        print(f"  repairable (re-derivable from the row's own record): {dict(moved)}")
        for entry in buckets["stale"][:5]:
            print(f"    e.g. {entry['fb_id'][:12]}: stored {entry['stored']} -> derived {entry['derived']}")
    if buckets["no_claim_value"]:
        print("  OWED, NOT repairable - a role with no factual claim must carry an ABSENT axis (D-2957):")
        for entry in buckets["no_claim_value"][:5]:
            print(f"    {entry['fb_id'][:12]} role={entry['role']!r} stores {entry['stored']}")
    if buckets["unevaluable"]:
        print("  OWED, NOT repairable - a claim-carrying role with no verification record (the rail names it too):")
        for entry in buckets["unevaluable"][:5]:
            print(f"    {entry['fb_id'][:12]} role={entry['role']!r}")


def backup(db_path: Path) -> Path:
    """C13: a consistent SQLite .backup before the first write. Returns the backup path."""
    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    dest = BACKUP_DIR / f"{Path(db_path).name}.bak_{stamp}_pre_s5_score_axis_repair"
    src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return dest


def run_apply(db_path: Path, buckets: dict[str, list[dict[str, Any]]]) -> int:
    """Write the re-derived axis in ONE transaction, re-derive the post-state, then commit.

    The post-state is verified INSIDE the transaction: a commit is only reachable when every row has
    become self-consistent, so no failure can leave a half-repaired store behind (C6/C16).
    """
    if not buckets["stale"]:
        print(f"{PREFIX}: nothing stale - the store already derives from its own records (no write)")
        return EXIT_OK
    backup_path = backup(db_path)
    print(f"{PREFIX}: C13 backup {backup_path.relative_to(REPO)}")
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    written = 0
    try:
        con.execute("BEGIN IMMEDIATE")
        for entry in buckets["stale"]:
            derived = entry["derived"]
            con.execute(
                f"UPDATE fbs SET {CONF_COL} = ?, {REVIEW_COL} = ? WHERE fb_id = ?",
                (derived[CONF_COL], 1 if derived[REVIEW_COL] else 0, entry["fb_id"]),
            )
            written += 1
        # Post-state verification: re-read the rows just written through the SAME derivation.
        targets = [e["fb_id"] for e in buckets["stale"]]
        residual: list[str] = []
        for i in range(0, len(targets), 400):
            part = targets[i:i + 400]
            sql = f"SELECT * FROM fbs WHERE fb_id IN ({','.join('?' * len(part))})"
            for row in con.execute(sql, part):
                row = dict(row)
                derived = derive_axis(row)
                if derived is None:
                    residual.append(str(row[CONF_COL])[:12] + ": unevaluable after the write")
                    continue
                conf, review = derived
                if abs(float(row[CONF_COL]) - conf) > TOLERANCE or bool(row[REVIEW_COL]) != review:
                    residual.append(f"{str(row['fb_id'])[:12]}: {row[CONF_COL]} != {conf}")
        if residual:
            con.rollback()
            print(f"{PREFIX}: FAIL - the post-state does not derive (rollback, 0 rows written): {residual[:5]}")
            return EXIT_DEFECT
        con.commit()
    except Exception:  # noqa: BLE001 - any failure must roll the whole repair back (C6)
        con.rollback()
        raise
    finally:
        con.close()
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "gen_model": "deterministic",  # C1/D-343: no model call in this path
        "pipeline_commit": _pipeline_commit(),
        "created_at": datetime.now(UTC).isoformat(),
        "bug": "BUG-745",
        "decision": "D-2970",
        "db": str(db_path),
        "backup": str(backup_path),
        "deriver": "pipeline/serving_gate.py::derive_conf_and_review",
        "enrichment_deriver": "pipeline/stage5_verify.py::_check_enrichment_quality",
        "rows_written": written,
        "columns_moved": dict(Counter(c for e in buckets["stale"] for c in e["moved"])),
        "post_state_verified": True,
        "role_set_home": "pipeline/serving_gate.py::content_types_without_factual_claim",
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"{PREFIX}: wrote {written} row(s); post-state re-derived clean; receipt {RECEIPT.relative_to(REPO)}")
    return EXIT_OK


def _pipeline_commit() -> str:
    """R14: the commit the repair ran at, when git can answer (empty string when it cannot)."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:  # noqa: BLE001 - a missing git is not a reason to refuse a repair
        return ""


def selftest() -> int:
    """Drive the classifier with known answers before it is allowed to touch the store (BUG-492)."""
    no_claim = sorted(content_types_without_factual_claim())[0]
    factual = {"check_name": "factual", "passed": True, "score": 0.9, "detail": "d" * 60}
    mech = {"check_name": "mechanism_quality", "passed": True, "score": 1.0, "detail": "d"}
    body = {
        "application": "a" * 60, "failure_mode": "b" * 60, "definition": "c" * 60, "boundary": "d" * 60,
        "isor": json.dumps({"score": 0.667, "rating": "moderate"}),
        "verification_results": json.dumps([mech, factual]),
        "needs_human_review": False,
    }
    derived = derive_axis({**body, "confidence_score": 0.0})
    assert derived is not None, "the control fixture must be evaluable"
    good = {**body, "confidence_score": derived[0], "needs_human_review": derived[1]}
    stale = {**body, "confidence_score": round(derived[0] + 0.01, 4), "needs_human_review": derived[1]}
    cases: list[tuple[str, list[dict[str, Any]], str, int]] = [
        ("a row that already derives its own score axis is not touched", [good], "ok", 1),
        ("a row whose stored confidence disagrees with its record is STALE", [stale], "stale", 1),
        ("a claim-carrying row with no verification record is UNEVALUABLE, never repaired",
         [{**body, "verification_results": json.dumps([]), "confidence_score": None}], "unevaluable", 1),
        ("a role with no factual claim + the declared ABSENT axis is left alone",
         [{"content_type": no_claim, "verification_results": json.dumps([]), "confidence_score": None,
           "needs_human_review": False}], "no_claim_ok", 1),
        ("a role with no factual claim that STORES a score is a violation, not a repair",
         [{"content_type": no_claim, "verification_results": json.dumps([]), "confidence_score": 0.9,
           "needs_human_review": False}], "no_claim_value", 1),
        ("a stale human-review flag is repaired WITH the confidence (one axis, two outputs)",
         [{**body, "confidence_score": derived[0], "needs_human_review": not derived[1]}], "stale", 1),
    ]
    bad: list[str] = []
    for label, rows, bucket, count in cases:
        buckets = classify([dict(r) for r in rows], content_types_without_factual_claim())
        if len(buckets[bucket]) != count:
            bad.append(f"{label}: expected {bucket}={count}, got {dict((k, len(v)) for k, v in buckets.items())}")
        if bucket != "stale" and buckets["stale"]:
            bad.append(f"{label}: an unexpected STALE row appeared - the classifier is not conservative")
    if bad:
        for line in bad:
            print(f"FAIL {PREFIX} selftest: {line}")
        return EXIT_DEFECT
    print(f"ok {PREFIX} --selftest: {len(cases)}/{len(cases)} known-answer control(s) fire")
    return EXIT_OK


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="back up, write and verify (otherwise read-only)")
    parser.add_argument("--selftest", action="store_true", help="run the known-answer controls only")
    args = parser.parse_args()
    if args.selftest:
        return selftest()

    db_path = Path(DB_PATH)
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        buckets = classify(load_rows(con), content_types_without_factual_claim())
    finally:
        con.close()
    report(buckets)
    if args.apply:
        return run_apply(db_path, buckets)
    if buckets["stale"]:
        print(f"{PREFIX}: FAIL - {len(buckets['stale'])} row(s) hold a score axis their own record does not "
              f"derive; run with --apply to re-derive them (deterministic, C13-backed, one transaction)")
        return EXIT_DEFECT
    if buckets["no_claim_value"] or buckets["unevaluable"]:
        print(f"{PREFIX}: FAIL - the store is self-consistent, but {len(buckets['no_claim_value'])} row(s) carry "
              f"an axis their role declares ABSENT and {len(buckets['unevaluable'])} claim-carrying row(s) have "
              f"no record at all; neither is repairable by re-derivation (both are OWED, named above)")
        return EXIT_DEFECT
    print(f"{PREFIX}: ok - every stored row derives its own score axis ({len(buckets['ok']) + len(buckets['no_claim_ok'])} row(s))")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
