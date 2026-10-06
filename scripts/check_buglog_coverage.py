#!/usr/bin/env python3
r"""Fail closed if a buglog heading names a bug that the status parser cannot see (BUG-428).

WHY: on 2026-09-24 the parser matched `^##\s+BUG-<id>` only, so BUG-426 (HIGH, OPEN) and BUG-427 sat in the
file, in the register's own directory, invisible to the register - and were therefore missing from the C15
count and from every handoff. The guard class that fails this way is worse than no guard.

This script reuses `HEADER_RE` from bug_status.py instead of re-typing it, so the two can never diverge.
Exit 1 naming every unparsed heading.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bug_status import BUGLOG, HEADER_RE  # noqa: E402  (single source of truth for the pattern)

HEADING_RE = re.compile(r"^#{1,6}\s+.*?BUG-\d+")
# A heading that ANNOTATES a bug is not a status event and must not be forced into one (an over-strict guard
# gets disabled, which is worse than no guard): CORRECTIONS/RECEIPTS/REFINEMENTS are append-only apparatus.
ANNOTATION_RE = re.compile(r"^#{1,6}\s+(CORRECTION|RECEIPT|REFINEMENT|VERIFICATION|NOTE|APPENDIX|ERRATUM)\b")


BLOCK_START_RE = re.compile(r"^(?:#{2,3}\s.*?BUG-\d+|\*\*BUG-\d+)")

# A summary `| BUG-NNN | ... |` table row (the tiered OPEN/CLOSED face at the top, and any append-only row).
TABLE_ROW_RE = re.compile(r"^\|\s*(BUG-\d+)\s*\|")


def control_slug(name: str) -> str:
    """The control's name as a marker a mutation can be SEEN to red through (D-2676 iv)."""
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def blocks(lines: list[str]) -> list[tuple[int, int, str]]:
    """Every BUG block as (start, end, text): a `^#{2,3}` status event or a `**BUG-...**` prose block."""
    out: list[tuple[int, int, str]] = []
    starts = [i for i, line in enumerate(lines) if BLOCK_START_RE.match(line)]
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        out.append((start, end, "".join(lines[start:end])))
    return out


def duplicate_block_problems(lines: list[str]) -> list[str]:
    """BUG-570: a block occurring TWICE with identical bytes is a COPY, and a copy is BLOAT.

    The comparison is over the BLOCK, never `occurrence -> end of file`: the latter is length-dependent (two
    copies can never satisfy it) and it REFUSED a true copy while claiming the bytes differed. Two DIFFERENT
    blocks are NOT a fault - a dedupe that cannot tell them apart would delete a fact (BUG-492, both directions).
    """
    groups: dict[str, list[tuple[int, int]]] = {}
    for start, end, text in blocks(lines):
        groups.setdefault(hashlib.sha256(text.encode("utf-8")).hexdigest(), []).append((start, end))
    problems: list[str] = []
    for digest, spans in sorted(groups.items()):
        if len(spans) > 1:
            where = ", ".join(str(s + 1) + "-" + str(e) for s, e in spans)
            problems.append("lines " + where + " are BYTE-IDENTICAL (sha256 " + digest[:12] + "): one is a COPY of "
                            "a fact already stated - delete it, and never compare an occurrence to EOF (BUG-570)")
    return problems


def table_rows_missing_heading(lines: list[str]) -> list[tuple[int, str]]:
    """BUG-657: a summary `| BUG-NNN |` table row with NO `## BUG-NNN` heading section is INVISIBLE to
    bug_status.py (HEADER_RE matches only headings), so it never enters the canonical register (C15 undercount).
    This is the REVERSE of the existing heading->parser check: every summary-table row must name a bug that ALSO
    has a heading section somewhere in the file."""
    heading_ids: set[str] = set()
    for line in lines:
        m = HEADER_RE.match(line)
        if m:
            heading_ids.add(m.group(1))
    missing: list[tuple[int, str]] = []
    for n, line in enumerate(lines, start=1):
        m = TABLE_ROW_RE.match(line)
        if m and m.group(1) not in heading_ids:
            missing.append((n, m.group(1)))
    return missing


def selftest() -> int:
    """Known-answer controls in BOTH directions: a COPY fires, two DIFFERENT blocks do not (BUG-492)."""
    same = ["**BUG-9001 STATUS (CLOSED).**\n", "the same body\n", "\n",
            "**BUG-9001 STATUS (CLOSED).**\n", "the same body\n", "\n"]
    differ = ["**BUG-9001 STATUS (CLOSED).**\n", "one body\n", "\n",
              "**BUG-9002 STATUS (OPEN).**\n", "another body\n", "\n"]
    rows = [
        ("a block that occurs TWICE byte-identically is a NAMED fault (the BUG-493 copy)",
         bool(duplicate_block_problems(same))),
        ("two DIFFERENT blocks are NOT a fault - a dedupe that cannot tell them apart deletes a fact",
         not duplicate_block_problems(differ)),
        ("a summary table row whose bug has NO heading section is a NAMED fault (BUG-657)",
         bool(table_rows_missing_heading(["| BUG-9001 | 2026-10-06 | body |\n"]))),
        ("a summary table row whose bug HAS a heading section is NOT a fault",
         not table_rows_missing_heading(["## BUG-9001 (OPEN, 2026-10-06) — x\n", "| BUG-9001 | 2026-10-06 | body |\n"])),
    ]
    for name, ok in rows:
        print(("  ok  " if ok else "  !!  ") + name)
    failed = [name for name, ok in rows if not ok]
    if failed:
        for name in failed:
            print("  FAIL selftest/" + control_slug(name))
        print("FAIL selftest: " + str(len(failed)) + " of " + str(len(rows)) + " known-answer control(s) did not fire")
        return 1
    print("ok buglog-coverage selftest: " + str(len(rows)) + "/" + str(len(rows)) + " known-answer control(s) fire")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Report any heading that names a bug id but is not a recognised status event, and any copied block."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()
    unparsed: list[tuple[int, str]] = []
    for n, line in enumerate(BUGLOG.read_text(encoding="utf-8").splitlines(), start=1):
        if HEADING_RE.match(line) and not HEADER_RE.match(line) and not ANNOTATION_RE.match(line):
            unparsed.append((n, line.strip()[:110]))
    if unparsed:
        print(f"FAIL buglog coverage: {len(unparsed)} heading(s) name a bug but are not parsed:")
        for n, line in unparsed:
            print(f"  line {n}: {line}")
        return 1
    text = BUGLOG.read_text(encoding="utf-8")
    text_lines = text.splitlines(keepends=True)
    duplicated = duplicate_block_problems(text_lines)
    if duplicated:
        print("FAIL buglog coverage: " + str(len(duplicated)) + " duplicated block(s):")
        for problem in duplicated:
            print("  " + problem)
        return 1
    missing_heading = table_rows_missing_heading(text_lines)
    if missing_heading:
        print(f"FAIL buglog coverage: {len(missing_heading)} summary table row(s) name a bug with no heading section "
              "(invisible to bug_status.py — BUG-657):")
        for n, bid in missing_heading:
            print(f"  line {n}: | {bid} |")
        return 1
    print("ok buglog coverage: every heading naming a bug id is parsed and no block is a byte-identical copy "
          "(" + str(len(blocks(text_lines))) + " block(s), " + BUGLOG.name + ")")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
