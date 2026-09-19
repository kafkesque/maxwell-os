#!/usr/bin/env python3
"""g3_review.py — interactive terminal walkthrough for the G3 judge-calibration sheet.

WHY THIS EXISTS (2026-09-17). `governance/JUDGE_CALIBRATION_SHEET_20260917.csv` holds full
definitions inside cells, so reading it in a spreadsheet means scrolling sideways through
multi-line blobs and the items become unintelligible. This walks **one item at a time**, prints the
material the way a human actually reads it, validates the answer against the sheet's own
`allowed_answer` column, and writes answers back **crash-safely** (C6).

PROTOCOL (freeze before starting — `governance/HUMAN_GATE_RUBRIC_20260917.md`):
  * answer **BLIND**: run no model and open no prior `*_qwen38` artifact until the sheet is done;
  * `allowed_answer` is read FROM THE SHEET and never restated here (C12);
  * `HUMAN_confidence_0to1` describes the QUESTION, not the answerer. A low value is a finding,
    not a failure — low-confidence rows are never dropped from the headline accuracy.

Usage:
  python3 scripts/g3_review.py --status      # progress + current tally
  python3 scripts/g3_review.py               # walk the unanswered rows
  python3 scripts/g3_review.py --redo        # re-answer rows that already have a verdict
  python3 scripts/g3_review.py --task T3_content_type
"""
from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHEET = ROOT / "governance" / "JUDGE_CALIBRATION_SHEET_20260917.csv"
ANSWER_FIELDS = ("HUMAN_VERDICT", "HUMAN_confidence_0to1", "HUMAN_note_codes", "reviewer_date")
BLOCK_FIELDS = (
    ("object_1_name", "OBJECT 1"),
    ("object_1_definition", "  definition"),
    ("object_1_application", "  application"),
    ("object_2_name", "OBJECT 2"),
    ("object_2_definition", "  definition"),
    ("object_2_application", "  application"),
    ("object_3_name", "OBJECT 3"),
    ("object_3_definition", "  definition"),
    ("other_members_in_group", "OTHER MEMBERS"),
    ("source_text_excerpt", "SOURCE TEXT"),
    ("claimed_labels", "CLAIMED LABELS"),
)
WIDTH_FALLBACK = 100
CONFIDENCE_HINT = "confidence 0-1 (1.0 certain .. 0.0 cannot judge) or 's' to skip"
NOTE_HINT = "note codes (AMBIG/TAXONOMY/SOURCE/MULTI/TRUNCATED/OK), max 2, blank = decisive"


def _width() -> int:
    """Return the usable terminal width, clamped to a readable range."""
    return max(70, min(140, shutil.get_terminal_size((WIDTH_FALLBACK, 24)).columns))


def _wrap(text: str, indent: str = "    ") -> str:
    """Wrap a long cell to the terminal width so a definition is readable, not scrolled."""
    body = " ".join(str(text or "").split())
    return textwrap.fill(body, width=_width(), initial_indent=indent, subsequent_indent=indent)


def load_rows() -> list[dict[str, str]]:
    """Read the calibration sheet, raising if it is missing or has no rows."""
    if not SHEET.exists():
        raise SystemExit("sheet not found: " + str(SHEET))
    with SHEET.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit("sheet is empty: " + str(SHEET))
    return rows


def save_rows(rows: list[dict[str, str]]) -> None:
    """Write the sheet crash-safely: tempfile -> fsync -> os.replace (C6)."""
    fields = list(rows[0].keys())
    fd, tmp = tempfile.mkstemp(dir=str(SHEET.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, SHEET)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def answered(row: dict[str, str]) -> bool:
    """True when the row already carries a human verdict."""
    return bool((row.get("HUMAN_VERDICT") or "").strip())


def show_status(rows: list[dict[str, str]]) -> None:
    """Print progress per task and the tally of verdicts so far."""
    per: dict[str, list[int]] = {}
    tally: dict[str, int] = {}
    for row in rows:
        done, total = per.setdefault(row["task"], [0, 0])
        per[row["task"]] = [done + (1 if answered(row) else 0), total + 1]
        if answered(row):
            value = row["HUMAN_VERDICT"].strip()
            tally[value] = tally.get(value, 0) + 1
    print("G3 progress")
    for task, (done, total) in sorted(per.items()):
        print("  " + task.ljust(20) + str(done) + "/" + str(total))
    low = sum(1 for row in rows
              if (row.get("HUMAN_confidence_0to1") or "").strip() not in ("",)
              and _as_float(row.get("HUMAN_confidence_0to1")) < 0.6)
    print("  verdicts: " + (", ".join(k + "=" + str(v) for k, v in sorted(tally.items())) or "(none)"))
    print("  rows scored below 0.6 confidence: " + str(low)
          + "  (reported, never dropped from the headline accuracy)")


def _as_float(value: str | None) -> float:
    """Parse a confidence cell, returning 1.0 when it is absent or malformed."""
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 1.0


def show_item(row: dict[str, str], index: int, total: int) -> None:
    """Render one calibration item as a readable block."""
    line = "-" * _width()
    print("\n" + line)
    print("  " + row["task"] + "   " + str(index) + "/" + str(total)
          + "   [enter=skip   q=quit&save   ?=help]")
    print(line)
    if (row.get("what_to_compare") or "").strip():
        print("  ITEM:     " + row["what_to_compare"])
    print("  QUESTION: " + row["QUESTION"])
    print("  ANSWER:   " + row["allowed_answer"])
    print()
    for field, label in BLOCK_FIELDS:
        value = (row.get(field) or "").strip()
        if not value:
            continue
        if field == "object_1_name" or field.endswith("_name"):
            print("  " + label + ": \"" + value + "\"")
        elif field == "claimed_labels":
            print("  " + label + ": " + value)
        else:
            print("  " + label + ":")
            print(_wrap(value))
    print()


def ask(prompt: str) -> str:
    """Read one line from the user, returning '' on EOF so a pipe cannot hang the walkthrough."""
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def _help() -> None:
    """Print the in-walkthrough reminder of the protocol and the answer vocabulary."""
    print("""
  Allowed verdict: exactly one value from the ANSWER line (lowercase), or 's' to skip.
  Confidence: describes the QUESTION, not you.  1.0 certain / 0.8 confident / 0.6 leaning /
    0.4 genuinely split / 0.2 guess / 0.0 cannot judge from the given input.
  Codes: AMBIG / TAXONOMY / SOURCE / MULTI / TRUNCATED / OK  (max 2, blank is fine)
  If your answer is NOT in the allowed set: give your closest value and add TAXONOMY —
    that is a finding about the ontology, not a mistake on your part.
  Blind: no model runs until the sheet is complete.
""")


def run(rows: list[dict[str, str]], only_task: str, redo: bool) -> int:
    """Walk the sheet one item at a time, saving after every answer."""
    queue = [r for r in rows
             if (not only_task or r["task"] == only_task) and (redo or not answered(r))]
    if not queue:
        show_status(rows)
        print("\nNothing to do — every matching row already has a verdict (use --redo to change).")
        return 0
    print("Answering " + str(len(queue)) + " item(s). Answers are saved after each one.")
    for position, row in enumerate(queue, 1):
        allowed = [a.strip() for a in row["allowed_answer"].split("/") if a.strip()]
        while True:
            show_item(row, position, len(queue))
            verdict = ask("  verdict > ")
            if verdict in ("q", "quit"):
                print("\nsaved.")
                return 0
            if verdict == "?":
                _help()
                continue
            if verdict in ("", "s", "skip"):
                print("  skipped.")
                break
            if verdict.lower() not in [a.lower() for a in allowed]:
                print("  '" + verdict + "' is not in the answer set: " + " | ".join(allowed))
                continue
            row["HUMAN_VERDICT"] = verdict.lower()
            print("  " + CONFIDENCE_HINT)
            conf = ask("  confidence > ")
            if conf.lower() not in ("", "s", "skip"):
                row["HUMAN_confidence_0to1"] = conf
            print("  " + NOTE_HINT)
            note = ask("  notes > ")
            if note.lower() not in ("", "s", "skip"):
                row["HUMAN_note_codes"] = note
            print("  reviewer/date (e.g. barn 2026-09-17)")
            who = ask("  > ")
            if who:
                row["reviewer_date"] = who
            save_rows(rows)
            print("  saved.")
            break
    show_status(rows)
    return 0


def main() -> int:
    """Entry point: status, or walk the (un)answered rows."""
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", default="", help="restrict to one task, e.g. T1_dedup")
    ap.add_argument("--redo", action="store_true", help="re-answer rows that already have a verdict")
    ap.add_argument("--status", action="store_true", help="print progress and exit")
    args = ap.parse_args()

    rows = load_rows()
    if args.status:
        show_status(rows)
        return 0
    return run(rows, args.task, args.redo)


if __name__ == "__main__":
    raise SystemExit(main())
