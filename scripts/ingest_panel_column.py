#!/usr/bin/env python3
"""Fill ONE declared panel column from ONE validated blind reply, and prove no other cell moved.

WHY THIS EXISTS (BUG-478, found by the 2026-09-25 forensic audit)
    The only declared ingester for a frontier reply, `scripts/cross_examine_anchor_axes.py::write_outputs`,
    opens governance/anchor_adjudication_workbook_20260924.csv with mode `"w"` and rebuilds it from the
    dispute set, then BLANKS every column in WORKBOOK_OWNER_COLS
    (["domains_final", "depth_final", "owner_note", "owner_date"]). Measured today: owner_depth is filled on
    148/148 rows and depth_final/domains_final carry the owner's adjudicated answers. Re-running that path to
    add the missing depth coder would therefore have DESTROYED the owner's cells and truncated the file to the
    dispute set - a data-loss path disguised as the documented way to complete a panel.
    So the path to complete a panel is: raw reply -> validate (parse_frontier_pack) -> THIS script.

WHAT IT GUARANTEES (each guarantee is asserted, not intended)
    1. It refuses unless `scripts/parse_frontier_pack.py` accepts the reply whole (menus closed, one block,
       exact header, non-empty evidence_quote).
    2. It writes exactly ONE column and REFUSES to write at all if any other cell would change. That rule is
       enforced by scripts/lib/write_guard.write_rows(mode="merge", owned_keys={that column}) over the WHOLE
       artifact, with a receipt in governance/MUTATION_JOURNAL.jsonl - not re-implemented here (D-401/I1).
       MEASURED 2026-09-25: the local copy of the rule also carried csv's DEFAULT lineterminator (CRLF), so it
       would have re-terminated all 149 lines of this LF-only workbook while reporting a one-cell edit.
    3. It refuses to overwrite an existing answer for a row (an ingest is not an edit), unless the existing
       value is byte-identical (idempotent re-run).
    4. tempfile -> fsync -> os.replace (C6) + a timestamped copy of the previous file (C13).
    5. Every declared value (workbook path, column map, id column, separator) comes from config (C12).

Usage:
    python3 scripts/ingest_panel_column.py --panel depth_axis_panel --coder raw_qwen38 --raw <file> [--apply]
    python3 scripts/ingest_panel_column.py --panel depth_axis_panel --coder raw_qwen38 --raw <file> --check
Exit: 0 ok (or in sync under --check) | 1 refused / drift | 3 declared gap (no such panel/coder)
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from lib import write_guard  # noqa: E402 - D-401/I1: the ownership invariant is ENFORCED, not restated
from lib import artifact_encoding  # noqa: E402 - D-2646: the decode rule has ONE home

FLOOR = REPO / "config" / "agreement_floor.yaml"
#: The writer name declared in config/artifact_ownership.yaml - DERIVED, so the receipt in
#: governance/MUTATION_JOURNAL.jsonl names the same writer the declaration does (never typed twice).
WRITER = Path(__file__).resolve().relative_to(REPO).as_posix()


class IngestError(RuntimeError):
    """A refused ingest. Never silent (C16)."""


def read_text(path: Path) -> str:
    """Decode with the repo's declared order."""
    # D-2646/BUG-516: the decode rule has ONE home. This is a delegating wrapper, not a second rule.
    return artifact_encoding.open_artifact(path, REPO).read()


def write_encoding_for(path: Path, text: str) -> str:
    """Return the ONE declared encoding that re-encodes `text` to the file's EXACT bytes, or refuse.

    A write must reproduce the bytes it read (C12/C6). Reading a workbook as utf-8-sig and writing it back as
    utf-8-sig ADDS a BOM the file never had: a whole-file change disguised as a one-cell edit - the same failure
    mode as csv's default CRLF lineterminator (BUG-478 by way of BUG-491c). So the encoding is not picked from a
    preference list, it is the codec that round-trips; if none does, nothing is written.
    """
    raw = path.read_bytes()
    # D-2646/BUG-516: the DECLARED encoding must reproduce the bytes; the round-trip rule has ONE home.
    enc = artifact_encoding.read_encoding(path, REPO)
    if text.encode(enc) == raw:
        return enc
    raise IngestError(f"{path.name}: the DECLARED encoding {enc!r} does not re-encode to the bytes on disk - "
                      f"refusing to write a human_authored artifact back in an encoding it was not read in")


def parse_reply(path: Path) -> dict[str, str]:
    """Read a validated reply's fenced CSV block as item_id -> depth token."""
    blocks = re.findall(r"```(?:csv)?\s*\n(.*?)```", read_text(path), re.S)
    if len(blocks) != 1:
        raise IngestError(f"{path.name}: expected exactly 1 fenced CSV block, found {len(blocks)}")
    rows = list(csv.DictReader(io.StringIO(blocks[0].strip())))
    out: dict[str, str] = {}
    for r in rows:
        i = (r.get("item_id") or "").strip()
        if not i:
            raise IngestError(f"{path.name}: a row has no item_id")
        if i in out:
            raise IngestError(f"{path.name}: duplicate item_id {i} - a chunked delivery must be disjoint")
        out[i] = (r.get("depth") or "").strip()
    return out


def main() -> int:
    """Validate the reply, merge exactly one column, and refuse on any other change."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--coder", required=True, help="the declared coder tag -> target column")
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true", help="verify the column already equals the reply; never writes")
    args = ap.parse_args()

    cfg = yaml.safe_load(FLOOR.read_text(encoding="utf-8"))
    panels = cfg.get("panels") or {}
    if args.panel not in panels:
        print(f"REFUSING: no declared panel {args.panel!r} in config/agreement_floor.yaml")
        return 3
    panel = panels[args.panel]
    ing = panel.get("ingest") or {}
    if not ing:
        print(f"REFUSING: panel {args.panel!r} declares no `ingest` block - the write path is not declared (C12)")
        return 3
    col = (ing.get("column_by_coder") or {}).get(args.coder)
    if not col:
        print(f"REFUSING: coder tag {args.coder!r} is not declared for {args.panel!r}: "
              f"{sorted((ing.get('column_by_coder') or {}))}")
        return 3
    if col not in panel["rater_columns"]:
        print(f"REFUSING: target column {col!r} is not a declared rater of {args.panel!r} - "
              "an ingest may not create a rater the panel does not know")
        return 1
    if not args.raw.exists():
        print(f"REFUSING: raw reply {args.raw} does not exist")
        return 1
    val = subprocess.run([sys.executable, str(REPO / "scripts" / "parse_frontier_pack.py"),
                          str(args.raw.parent)], capture_output=True, text=True, cwd=str(REPO))
    print(val.stdout.strip() or val.stderr.strip())
    if val.returncode != 0:
        print("REFUSING: the reply does not pass scripts/parse_frontier_pack.py - a rejected reply is not "
              "hand-fixed (C12d)")
        return 1

    wb = REPO / ing["workbook"]
    idc = ing.get("id_column", "item_id")
    vendor = read_text(wb)
    rows = list(csv.DictReader(io.StringIO(vendor)))
    fieldnames = list(rows[0].keys())
    if col not in fieldnames:
        print(f"REFUSING: {wb.name} has no column {col!r} - declare it first, do not append one implicitly")
        return 1
    reply = parse_reply(args.raw)

    existing = {r[idc]: (r.get(col) or "").strip() for r in rows if (r.get(idc) or "").strip()}
    clashes = [i for i, v in reply.items() if existing.get(i) and existing[i] != v]
    unknown = [i for i in reply if i not in existing]
    if clashes:
        print(f"REFUSING: {len(clashes)} row(s) already carry a {col} answer ({clashes[:5]}) - an ingest is "
              "not an edit; a superseding pass needs its own declaration")
        return 1
    if unknown:
        print(f"REFUSING: reply names {len(unknown)} item_id(s) not in {wb.name} ({unknown[:5]})")
        return 1

    new_rows = []
    for r in rows:
        r = dict(r)
        i = (r.get(idc) or "").strip()
        if i in reply and not (r.get(col) or "").strip():
            r[col] = reply[i]
        new_rows.append(r)

    # The off-target rule is NOT re-checked here: write_guard owns it over the whole artifact (D-401/I1). A
    # second copy of an invariant is a second home for a fact, and the copy that is not enforced is the copy
    # that drifts (BUG-491c).
    changed = sum(1 for old, new in zip(rows, new_rows) if (old.get(col) or "") != (new.get(col) or ""))
    filled_before = sum(1 for r in rows if (r.get(col) or "").strip())
    filled_after = sum(1 for r in new_rows if (r.get(col) or "").strip())
    print(f"{args.panel}: coder {args.coder} -> column {col}: {len(changed)} cell(s) to write; "
          f"fill {filled_before}/{len(rows)} -> {filled_after}/{len(rows)}")

    if args.check:
        if changed:
            print(f"DRIFT: {col} is not in sync with {args.raw.name} - run with --apply")
            return 1
        print(f"ok {col} equals {args.raw.name} ({filled_after}/{len(rows)} filled)")
        return 0
    if not args.apply:
        print("dry run (pass --apply to write)")
        return 0
    if not changed:
        print("ok nothing to write")
        return 0
    encoding = write_encoding_for(wb, vendor)
    rep = write_guard.write_rows(wb, new_rows, owned_keys={col}, writer=WRITER, id_column=idc,
                                 columns=fieldnames, encoding=encoding, lineterminator="\n",
                                 backup=True, journal=True)
    after = write_guard.read_rows(wb, encoding)
    print(f"ok wrote {wb.relative_to(REPO)}: column {col} now "
          f"{sum(1 for r in after if (r.get(col) or '').strip())}/{len(after)}; encoding={encoding} "
          f"touched={rep.touched} pre={rep.pre_sha16} post={rep.post_sha16} backup={rep.backup}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except IngestError as exc:
        print(f"FAIL ingest: {exc}")
        sys.exit(1)
