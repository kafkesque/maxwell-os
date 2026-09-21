#!/usr/bin/env python3
"""Derive a MACHINE-READABLE bug status index from governance/buglog.md (C15 enforcement).

WHY: C15 ("5+ unresolved -> append to every handoff") was unenforceable because the register is prose.
Session 9 found the hand-maintained C15 count wrong: it claimed 17 unresolved while BUG-311/313 carried
RESOLVED headers, and BUG-311 has since REGRESSED. A count nobody can recompute is a count nobody should
quote (BUG-342). This script re-derives it from the file itself, in file order.

Status rule: a "## BUG-<id>" header is a status EVENT and the LAST one wins, except that a later CLOSED
event cannot un-close a REOPEN. Keywords: RESOLVED/CLOSED/FIXED/INVALID/RETRACTED -> closed;
REOPEN/REGRESS/RECURRED -> open; anything else -> open (no closure claim is not a closure).

Usage:  python3 scripts/bug_status.py
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUGLOG = REPO / "governance" / "buglog.md"
C15_THRESHOLD = 5
CLOSE_WORDS = ("RESOLVED", "CLOSED", "FIXED", "INVALID", "RETRACTED")
REOPEN_WORDS = ("REOPEN", "REGRESS", "RECURRED")
HEADER_RE = re.compile(r"^##\s+(BUG-\d+)\b[\s:—‑-]*(.*)$")


def classify(text: str) -> str:
    """Map a header line to one status EVENT."""
    up = text.upper()
    if any(w in up for w in REOPEN_WORDS):
        return "reopened"
    if any(w in up for w in CLOSE_WORDS):
        return "closed"
    return "open"


def scan(text_lines: list[str]) -> dict[str, dict]:
    """Fold header events, in file order, into one status per bug id."""
    bugs: dict[str, dict] = {}
    for i, line in enumerate(text_lines, start=1):
        m = HEADER_RE.match(line)
        if not m:
            continue
        bid, rest = m.group(1), m.group(2).strip()
        rec = bugs.setdefault(bid, {"id": bid, "status": "open", "events": [], "title": rest[:140], "line": i})
        event = classify(rest)
        rec["events"].append({"line": i, "event": event, "text": rest[:140]})
        if event == "closed" and rec["status"] == "open":
            rec["status"] = "closed"
        elif event == "reopened":
            rec["status"] = "open"
    return bugs


def main() -> int:
    """Re-derive the status index, write it, and state the C15 consequence."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default="governance/bug_status.json")
    ap.add_argument("--md-out", default="governance/bug_status.md")
    args = ap.parse_args()
    bugs = scan(BUGLOG.read_text(encoding="utf-8").splitlines())
    open_ids = sorted((b for b in bugs.values() if b["status"] == "open"), key=lambda b: int(b["id"][4:]))
    closed_ids = sorted((b for b in bugs.values() if b["status"] == "closed"), key=lambda b: int(b["id"][4:]))
    payload = {"schema_version": "1.0", "source": "governance/buglog.md",
               "parser": "scripts/bug_status.py", "total_ids": len(bugs), "open_n": len(open_ids),
               "closed_n": len(closed_ids), "c15_threshold": C15_THRESHOLD,
               "c15_must_append_to_handoffs": len(open_ids) >= C15_THRESHOLD,
               "open": [{"id": b["id"], "title": b["title"], "events": len(b["events"])} for b in open_ids],
               "closed": [b["id"] for b in closed_ids]}
    (REPO / args.json_out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    rows = ["| id | title (last header) | events |", "|---|---|---|"]
    rows += ["| " + b["id"] + " | " + str(b["title"]) + " | " + str(len(b["events"])) + " |" for b in open_ids]
    head = ["# Bug status index (mechanical, re-derived)", "",
            "Re-derive with `python3 scripts/bug_status.py` (source: `governance/buglog.md`).", "",
            "**" + str(payload["open_n"]) + " open** / " + str(payload["closed_n"]) + " closed of " + str(payload["total_ids"]) + " ids.",
            "C15 append-to-handoffs required: **" + str(payload["c15_must_append_to_handoffs"]) + "** (threshold " + str(C15_THRESHOLD) + ").", ""]
    (REPO / args.md_out).write_text("\n".join(head + rows) + "\n", encoding="utf-8")
    print("OPEN " + str(payload["open_n"]) + " / CLOSED " + str(payload["closed_n"]) + " of " + str(payload["total_ids"]))
    print("open ids: " + ", ".join(b["id"] for b in open_ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())