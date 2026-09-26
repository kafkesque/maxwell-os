#!/usr/bin/env python3
"""scripts/prepare_single_coder_sheet.py — Step 2: single-coder ceiling sheet (D-280).

The classifier's accuracy ceiling is human-vs-human κ on the same closed menu
(D-277: report agreement-with-human-κ, never "100%"). To bound that ceiling we
need a SECOND independent human pass on a subset of ANCHOR-1, blind to the first
reviewer's labels. This script selects a deterministic 30-row stratified sample
and writes a clean sheet with the label columns BLANKED for the second coder.

Stratification: cover every RE-DERIVE slot (the slots whose human κ matters most
for R5) — the five discipline slots (design psychology 5, cultural studies 4,
risk management 4, behavioral economics 4, decision making 4 = 21 rows) plus a
seeded 9-row draw from the two content-type RE-DERIVE slots (quarantine /
process_template) whose discipline is not already in the sample.

The second coder MUST NOT see the first reviewer's labels (they are blanked) and
MUST use the same D-275b content-type decision procedure + 61-menu discipline +
4-menu FORM. κ(human1, human2) over these 30 rows is the human ceiling.

Read-only w.r.t. the DB and the source CSV. Crash-safe write (C6).
"""
from __future__ import annotations

import csv
import os
import random
import sys
import tempfile
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from lib import artifact_encoding  # noqa: E402 - D-2646: the decode rule has ONE home

_ROOT = Path(__file__).resolve().parent.parent
_SRC_CSV = _ROOT / "governance" / "RULER_BLIND_SHEET_20260917.csv"
_OUT_CSV = _ROOT / "governance" / "SINGLE_CODER_CEILING_SHEET_20260920.csv"

_REDERIVE_DISC = (
    "design psychology",
    "cultural studies",
    "risk management",
    "behavioral economics",
    "decision making",
)
_REDERIVE_CT = ("quarantine", "process_template")
_TARGET_N = 30
_SEED = 20260920

# Columns preserved from the blind sheet (content the coder classifies FROM) and
# the three blank label columns the coder fills. Labels + confidences + notes +
# first reviewer identity are stripped so the pass is blind.
_OUT_FIELDNAMES = [
    "item_id",
    "name",
    "DEFINITION",
    "APPLICATION",
    "MECHANISM",
    "BOUNDARY",
    "SOURCE EXCERPT",
    "CT (1-7)",
    "DISC (1-62)",
    "FORM (1-4)",
    "note_codes",
    "reviewer",
    "date",
]


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _crash_safe_write(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.writelines(lines)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _load_rows() -> list[dict]:
    with artifact_encoding.open_artifact(_SRC_CSV, REPO) as f:
        reader = csv.DictReader(f)
        return [dict(r) for r in reader if (r.get("item_id") or "").strip()]


def _select(rows: list[dict]) -> list[dict]:
    rng = random.Random(_SEED)

    # 1. all rows in the five RE-DERIVE discipline slots (by the HUMAN label).
    disc_pool: list[dict] = []
    for r in rows:
        if _norm(r.get("DISC (1-62)", "")) in {_norm(d) for d in _REDERIVE_DISC}:
            disc_pool.append(r)

    chosen: list[dict] = []
    seen_ids: set[str] = set()
    for r in disc_pool:
        rid = r["item_id"]
        if rid not in seen_ids:
            chosen.append(r)
            seen_ids.add(rid)

    # 2. fill to TARGET_N from the CT RE-DERIVE slots (quarantine/process_template),
    #    whose discipline is NOT already chosen — deterministic seeded shuffle.
    ct_pool = [
        r
        for r in rows
        if _norm(r.get("CT (1-7)", "")) in {_norm(c) for c in _REDERIVE_CT}
        and r["item_id"] not in seen_ids
    ]
    rng.shuffle(ct_pool)
    for r in ct_pool:
        if len(chosen) >= _TARGET_N:
            break
        chosen.append(r)
        seen_ids.add(r["item_id"])

    # 3. if still short (should not happen: 21 + 9 == 30), top up with a seeded
    #    draw from the remaining rows so the sheet is always exactly TARGET_N.
    if len(chosen) < _TARGET_N:
        remainder = [r for r in rows if r["item_id"] not in seen_ids]
        rng.shuffle(remainder)
        for r in remainder:
            if len(chosen) >= _TARGET_N:
                break
            chosen.append(r)
            seen_ids.add(r["item_id"])

    chosen.sort(key=lambda r: r["item_id"])
    return chosen[: _TARGET_N]


def _emit(rows: list[dict]) -> list[str]:
    from io import StringIO

    buf = StringIO()
    w = csv.DictWriter(buf, fieldnames=_OUT_FIELDNAMES, lineterminator="\r\n")
    w.writeheader()
    for r in rows:
        w.writerow(
            {
                "item_id": r.get("item_id", ""),
                "name": r.get("name", ""),
                "DEFINITION": r.get("DEFINITION", ""),
                "APPLICATION": r.get("APPLICATION", ""),
                "MECHANISM": r.get("MECHANISM", ""),
                "BOUNDARY": r.get("BOUNDARY", ""),
                "SOURCE EXCERPT": r.get("SOURCE EXCERPT", ""),
                # label columns BLANK — the second coder fills these blind
                "CT (1-7)": "",
                "DISC (1-62)": "",
                "FORM (1-4)": "",
                "note_codes": "",
                "reviewer": "",
                "date": "",
            }
        )
    return [buf.getvalue()]


def main() -> int:
    rows = _load_rows()
    if len(rows) < _TARGET_N:
        print(f"❌ source sheet has {len(rows)} rows < {_TARGET_N}", file=sys.stderr)
        return 1

    chosen = _select(rows)
    coverage: dict[str, int] = {}
    for r in chosen:
        coverage[_norm(r.get("DISC (1-62)", ""))] = coverage.get(_norm(r.get("DISC (1-62)", "")), 0) + 1

    text = _emit(chosen)[0]
    _crash_safe_write(_OUT_CSV, [text])

    print(f"✅ single-coder ceiling sheet: {len(chosen)} rows -> {_OUT_CSV.name}")
    print(f"   RE-DERIVE discipline coverage: { {k: v for k, v in coverage.items() if k in _REDERIVE_DISC} }")
    print(f"   CT coverage (quarantine/process_template): "
          f"{sum(1 for r in chosen if _norm(r.get('CT (1-7)','')) in {_norm(c) for c in _REDERIVE_CT})}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
