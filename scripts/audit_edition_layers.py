#!/usr/bin/env python3
"""scripts/audit_edition_layers.py — the WORK / FILE / BODY layer census (D-2952, read-only).

WHY THIS EXISTS. D-2950 left one question open (edition supersession: does "newest edition
wins" reach the citation convention?) and the answer is a LAYER fact, not an opinion. This
script measures which layer an edition conflict actually lives in, so the ruling is evidence
rather than rhetoric — and so the ruling can be RE-CHECKED when the store changes instead of
being re-argued. It is deterministic and LLM-free (D-343 applies to identity/dedup: no model
may decide what counts as one work).

THE THREE LAYERS (one home each; documented here because this is the script that measures them):

  WORK  a concept-carrier. Identity = `source_ids`, and `compute_source_id` =
        SHA-256(normalize_author | normalize_title) where `normalize_title` DELIBERATELY
        strips subtitles so edition variants collapse (D2308 / D2315 / D2507). CONSEQUENCE,
        and the whole point of this census: **two editions of one work share ONE source_id**,
        by design. The store cannot see them as two sources.
  FILE  a text carrier. `source_authors[]` = {book, author, title, year}, at file granularity
        (sanitized display names, D2449). This is the ONLY place an edition conflict is visible.
  BODY  the FB's current statement — the body fields. Supersession moves the BODY layer only.

WHAT IT MEASURES (all read-only):
  1. work/file/year cross-tab — isolates the population where a work holds files of DIFFERENT
     years: `edition_pairs` (files>1 AND years>1 AND |source_ids| == 1) and the `boundary`
     (files>1 AND years>1 AND |source_ids| == 2, i.e. partially collapsed).
  2. carrier duplicates — the SAME edition carried by several files (`*_clean.md`, " (1)",
     z-library mirrors). Measured, because the absence of this defect is a CLAIM: D2176 routed
     `source_diversity` through canonical `source_ids`, not filenames. A zero here is the
     evidence that the claim still holds, and it stops a future agent from "fixing" a fixed
     defect (BUG-527 class).
  3. the `primary_source` reason census — how the origin attribution was actually decided
     (`earliest publication year (YYYY)` / `no year metadata; first source` / `single source`),
     plus how many rows VIOLATE the earliest-year rule. D-2952 asserts that convention is
     exactly honoured; this is the measurement behind the assertion.

USAGE
    python3 scripts/audit_edition_layers.py            # human-readable census
    python3 scripts/audit_edition_layers.py --json     # machine receipt (governance artefact)
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "knowledge pipeline" / "maxwell.db"

# A file name that is a DERIVATIVE of another file name (same edition, another carrier).
_CARRIER_NOISE = (
    (re.compile(r"\.md$"), ""),
    (re.compile(r"_clean$"), ""),
    (re.compile(r"\(z-library[^)]*\)"), ""),
    (re.compile(r"\(for true epub\)"), ""),
    # COPY MARKER ONLY — parenthesised, e.g. " (1)". Deliberately NOT `\s*\(?\d+\)?$`, which also
    # stripped a trailing number that may be PART OF THE TITLE: "Fahrenheit 451" -> "fahrenheit",
    # colliding with "Fahrenheit", and a wholly-numeric title reduced to the EMPTY key (so every
    # numeric title would collide with every other). Found by an R5 review of this file
    # (gemma-4-E4B-it-MLX-4bit, 2026-10-12); LATENT — 0 manifest instances measured on the
    # 7,640-row store (90 carrier rows before AND after the tightening), fixed so it cannot
    # manifest as the corpus grows.
    (re.compile(r"\(\d+\)$"), ""),
)


def carrier_key(name: str) -> str:
    """Collapse a source FILE name to its carrier key (strips clean/dup/mirror markers)."""
    text = str(name).lower()
    for pattern, repl in _CARRIER_NOISE:
        text = pattern.sub(repl, text)
    return re.sub(r"[^a-z0-9]", "", text)


def _json_load(value: object) -> object:
    """Parse a store cell that may be JSON TEXT, a list, or blank. Returns None if unparseable."""
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def _years(rows: object) -> set[int]:
    """Distinct integer years recorded across `source_authors` entries."""
    found: set[int] = set()
    for meta in rows if isinstance(rows, list) else []:
        try:
            found.add(int(str((meta or {}).get("year") or "").strip()))
        except (TypeError, ValueError):
            continue
    return found


def audit(con: sqlite3.Connection) -> dict:
    """Measure the three layers over the whole store. Pure reads; never writes."""
    cur = con.cursor()
    total = cur.execute("SELECT COUNT(*) FROM fbs").fetchone()[0]

    cross: collections.Counter = collections.Counter()
    edition_pairs: list[dict] = []
    carrier_rows = 0
    reasons: collections.Counter = collections.Counter()
    citation_violations = 0

    for fb_id, name, src_ids, src_authors, primary in cur.execute(
        "SELECT fb_id, name, source_ids, source_authors, primary_source FROM fbs"
    ):
        ids = _json_load(src_ids) or []
        files = _json_load(src_authors) or []
        # Normalize at the BOUNDARY so no downstream use needs a type guard (C19: no dead code;
        # C21: one home for the shape). A store cell may be JSON TEXT holding a list OR an object,
        # a real list, or blank.
        ids = ids if isinstance(ids, (list, tuple)) else []
        files = files if isinstance(files, list) else []
        n_ids = len(ids)
        n_files = len(files)
        years = _years(files)

        cross[(f"files>1={n_files > 1}", f"years>1={len(years) > 1}", f"source_ids={min(n_ids, 3)}")] += 1

        if n_files > 1 and len(years) > 1 and n_ids == 1:
            edition_pairs.append({
                "fb_id": fb_id,
                "name": name,
                "source_id": ids[0] if ids else None,
                "files": [
                    {"book": (m or {}).get("book"), "year": (m or {}).get("year")}
                    for m in files
                ],
            })

        if n_files > 1:
            seen = collections.Counter(carrier_key((m or {}).get("book", "")) for m in files)
            if any(count > 1 for count in seen.values()):
                carrier_rows += 1

        # citation convention (D-2952): earliest recorded year, tracked against the actual pick
        pdata = _json_load(primary) or {}
        reason = str((pdata or {}).get("reason") or "")
        reasons[re.sub(r"\(\d+\)", "(YYYY)", reason)] += 1
        if len(years) > 1 and reason.startswith("earliest publication year"):
            picked = str((pdata or {}).get("book") or "")
            picked_year = next(
                (int(str((m or {}).get("year")).strip())
                 for m in files
                 if carrier_key((m or {}).get("book", "")) == carrier_key(picked)),
                None,
            )
            if picked_year is not None and picked_year != min(years):
                citation_violations += 1

    return {
        "rows": total,
        "cross_tab": {"/".join(k): v for k, v in sorted(cross.items(), key=lambda x: -x[1])},
        "edition_pairs": len(edition_pairs),
        "boundary_files_multi_year_two_ids": sum(
            v for k, v in cross.items() if k == ("files>1=True", "years>1=True", "source_ids=2")
        ),
        "carrier_duplicate_rows": carrier_rows,
        "primary_source_reasons": dict(reasons),
        "citation_rule_violations": citation_violations,
        "samples": edition_pairs[:5],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="WORK/FILE/BODY layer census for edition supersession (D-2952).")
    ap.add_argument("--json", action="store_true", help="machine-readable receipt")
    ap.add_argument("--db", default=str(DB_PATH), help="store path (opened read-only)")
    args = ap.parse_args()

    con = sqlite3.connect(f"file:{Path(args.db).as_posix().replace(' ', '%20')}?mode=ro", uri=True)
    out = audit(con)
    con.close()

    if args.json:
        print(json.dumps(out, indent=2, default=str))
        return 0

    print(f"store rows: {out['rows']}")
    print("\nWORK/FILE/YEAR cross-tab (files>1 / years>1 / source_ids):")
    for key, count in out["cross_tab"].items():
        print(f"  {key:52} {count}")
    print(f"\nEDITION population (files>1 AND years>1 AND ONE source_id = editions collapsed): {out['edition_pairs']}")
    print(f"  boundary (files>1 AND years>1 AND 2 source_ids, partially collapsed): {out['boundary_files_multi_year_two_ids']}")
    print(f"CARRIER-DUPLICATE rows (same edition, several files in source_authors): {out['carrier_duplicate_rows']}")
    print(f"CITATION rule violations (picked year != min year): {out['citation_rule_violations']}")
    print("\nprimary_source reason census:")
    for reason, count in sorted(out["primary_source_reasons"].items(), key=lambda x: -x[1]):
        print(f"  {count:6}  {reason}")
    if out["samples"]:
        print("\nsamples (the edition pairs the store CANNOT tell apart — one work id):")
        for sample in out["samples"]:
            years = [f"{f['book']}={f['year']}" for f in sample["files"]]
            print(f"  {str(sample['name'])[:40]:42} sid={sample['source_id']}  {years}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
