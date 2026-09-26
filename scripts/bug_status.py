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
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUGLOG = REPO / "governance" / "buglog.md"
OWNERSHIP = REPO / "config" / "artifact_ownership.yaml"
#: This script's identity as a declared writer_of_record (config/artifact_ownership.yaml, D-401).
WRITER = "scripts/bug_status.py"

# D-401/I1 (BUG-530): write_guard.write_document is the ONLY legal whole-document writer, so BOTH outputs of this
# generator are routed through it. The path insert is needed because this script runs as a direct invocation AND
# as a subprocess of scripts/check_bug_status.py, whose cwd and sys.path are its own.
sys.path.insert(0, str(REPO / "scripts"))
from lib import write_guard  # noqa: E402

C15_THRESHOLD = 5
CLOSE_WORDS = ("RESOLVED", "CLOSED", "FIXED", "INVALID", "RETRACTED")
REOPEN_WORDS = ("REOPEN", "REGRESS", "RECURRED")
# BUG-347 (2026-09-21): "PARTIALLY FIXED" contains the substring FIXED and was classified CLOSED,
# silently retiring a LIVE bug (BUG-333). A partial fix is an OPEN bug with progress attached.
PARTIAL_WORDS = ("PARTIAL", "MITIGATED", "IN PROGRESS")
STATUS_WORDS = CLOSE_WORDS + REOPEN_WORDS + PARTIAL_WORDS
# BUG-429 (2026-09-24): "UNRESOLVED" CONTAINS "RESOLVED", so `### BUG-426 (HIGH, OPEN - UNRESOLVED)` was
# classified CLOSED - a HIGH, explicitly-unresolved bug auto-retired by substring. Same degeneracy class as
# BUG-347 (PARTIAL FIXED), second occurrence. A negated status word is checked FIRST and forces OPEN, which is
# the fail-safe direction: an open bug that is really closed costs a look; a closed bug that is really open
# costs the work being silently abandoned.
NEGATED_WORDS = ("UNRESOLVED", "UNFIXED", "NOT RESOLVED", "NOT FIXED", "STILL OPEN", "NOT CLOSED")
QQ = chr(34) + chr(8220) + chr(8221) + chr(39)
QUOTE_RE = re.compile("[" + QQ + "][^" + QQ + "]*[" + QQ + "]")
PAREN_RE = re.compile("[(]([^)]*)[)]")


def status_slot(rest: str) -> str:
    """
    Return only the header STATUS SLOT (BUG-350), never the prose title.

    Order: the parenthetical after the bug id, then the text before the first colon.
    Quoted spans are dropped, so a title that merely quotes a status word cannot decide it.
    If no candidate names a status word the whole header is read, so an unlabelled header stays OPEN
    (no closure claim is not a closure).
    """
    m = PAREN_RE.match(rest)
    cands = ([m.group(1)] if m else []) + [rest.split(chr(58))[0], rest]
    for cand in cands:
        clean = QUOTE_RE.sub(chr(32), cand).strip()
        if any(w in clean.upper() for w in STATUS_WORDS):
            return clean
    return QUOTE_RE.sub(chr(32), rest).strip()


# BUG-350: status is read from status_slot(); a title that QUOTES a status word cannot decide.

HEADER_RE = re.compile(r"^#{2,3}\s+(BUG-\d+)\b[\s:—‑-]*(.*)$")
# BUG-428 (2026-09-24): the pattern was `^##\s+` - EXACTLY two hashes - so the two OPEN bugs written
# with three hashes (BUG-426 HIGH/UNRESOLVED, BUG-427 LOW) were silently absent from the machine
# register and therefore from the C15 count and every handoff. A parser must not be able to lose a bug.


def classify(text: str) -> str:
    """Classify one header event. Precedence: negated(open) > reopened > partial(open) > closed > open."""
    up = text.upper()
    if any(w in up for w in NEGATED_WORDS):
        return "open"
    if any(w in up for w in REOPEN_WORDS):
        return "reopened"
    if any(w in up for w in PARTIAL_WORDS):
        return "open"
    if any(w in up for w in CLOSE_WORDS):
        return "closed"
    return "open"


def self_test() -> None:
    """Assert the classifier's registered edge cases before its output is trusted (BUG-347)."""
    cases = {
        "MED - FIXED 2026-09-21": "closed",
        "HIGH - OPEN 2026-09-21": "open",
        "MED - PARTIALLY FIXED 2026-09-21": "open",
        "MED - FIXED, REGRESSED 2026-09-21": "reopened",
        "LOW - CLOSED INVALID": "closed",
        "MED - RESOLVED (cleaned up)": "closed",
        # BUG-429 shapes, taken from live headers:
        "HIGH, OPEN - UNRESOLVED": "open",
        "MED - UNFIXED 2026-09-24": "open",
        "LOW - NOT CLOSED, FIXED PENDING REVIEW": "open",
        # BUG-350 shapes, taken from live headers:
        "MED FIXED 2026-09-21): the C15 classifier treated PARTIALLY FIXED as CLOSED": "closed",
        "No degenerate-arm guard: a collapsed arm could be read as a tie (HIGH, fixed 2026-09-21)": "closed",
    }
    for text, want in cases.items():
        got = classify(status_slot(text))
        if got != want:
            raise SystemExit(f"FAIL-CLOSED: bug_status self-test {text!r} -> {got}, expected {want}")


def scan(text_lines: list[str]) -> dict[str, dict]:
    """Fold header events, in file order, into one status per bug id."""
    bugs: dict[str, dict] = {}
    for i, line in enumerate(text_lines, start=1):
        m = HEADER_RE.match(line)
        if not m:
            continue
        bid, rest = m.group(1), m.group(2).strip()
        rec = bugs.setdefault(bid, {"id": bid, "status": "open", "events": [], "title": rest[:140], "line": i})
        event = classify(status_slot(rest))
        rec["events"].append({"line": i, "event": event, "text": rest[:140]})
        if event == "closed" and rec["status"] == "open":
            rec["status"] = "closed"
        elif event == "reopened":
            rec["status"] = "open"
    return bugs


def declared_outputs() -> dict[str, str]:
    """
    This generator's outputs, read from the ONE ownership declaration (D-2646/C12) - never restated here.

    WHY NOT A LITERAL: "which files does this script write" is a DECLARED fact (config/artifact_ownership.yaml,
    D-401); a second copy of it inside this file would be the two-homes defect (D-2646), and the copy is the one
    that goes stale. Fail closed (C16): a generator that cannot read its own declaration cannot tell a GOVERNED
    write from a FOREIGN one, and that distinction is the whole of BUG-530.
    """
    import yaml  # lazy, matching scripts/lib/write_guard.py's own idiom (keeps this module's imports minimal)
    if not OWNERSHIP.exists():
        raise SystemExit("FAIL-CLOSED (BUG-530/D-401): " + str(OWNERSHIP) + " is absent - the declaration is the "
                         "only source for which files this generator owns, so its outputs cannot be classified")
    doc = yaml.safe_load(OWNERSHIP.read_text(encoding="utf-8")) or {}
    mine = [str(p) for p, spec in (doc.get("artifacts") or {}).items()
            if str((spec or {}).get("writer_of_record") or "") == WRITER]
    by_suffix = {Path(p).suffix: p for p in mine}
    missing = [s for s in (".json", ".md") if s not in by_suffix]
    if missing:
        raise SystemExit("FAIL-CLOSED (BUG-530): config/artifact_ownership.yaml declares no " + " / ".join(missing)
                         + " output for writer_of_record " + WRITER + " (declared: " + str(mine) + ")")
    return by_suffix


def emit(target: Path, text: str) -> None:
    """
    Write one output crash-safely (C6), routed through the guard when the target IS a declared artifact.

    THE ROUTING IS BY IDENTITY, NOT BY NAME (the BUG-528/BUG-531 class): the target is RESOLVED - symlinks and
    '..' collapsed - before it is compared with the resolved declared artifacts, so the dotted form
    './governance/../governance/bug_status.json' is the governed write it looks like. A string compare would let
    that form bypass the guard, which is the same defect shape as a rename bypassing a lock (BUG-528).
    A FOREIGN target (scripts/check_bug_status.py re-derives into a TEMP dir and byte-compares) goes through the
    SAME guard call: it is the only legal whole-document writer (D-401/I1), and using it keeps crash-safety as ONE
    implementation instead of a second local copy. Such a target is written with journal=False, because a mutation
    receipt for a file that is not an artifact would make the ledger read as if a declaration had been rewritten.
    """
    governed = {str((REPO / p).resolve()) for p in declared_outputs().values()}
    resolved = str(Path(target).resolve())
    write_guard.write_document(Path(target), text, writer=WRITER, owned_keys={write_guard.OWNED_ANY},
                               backup=False, journal=resolved in governed)


def main() -> int:
    """Re-derive the status index, write it, and state the C15 consequence."""
    self_test()
    ap = argparse.ArgumentParser()
    outs = declared_outputs()   # the defaults ARE the declared artifact paths - one home (D-2646)
    ap.add_argument("--json-out", default=outs[".json"])
    ap.add_argument("--md-out", default=outs[".md"])
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
    emit(REPO / args.json_out, json.dumps(payload, indent=2) + "\n")
    rows = ["| id | title (last header) | events |", "|---|---|---|"]
    rows += ["| " + b["id"] + " | " + str(b["title"]) + " | " + str(len(b["events"])) + " |" for b in open_ids]
    head = ["# Bug status index (mechanical, re-derived)", "",
            "Re-derive with `python3 scripts/bug_status.py` (source: `governance/buglog.md`).", "",
            "**" + str(payload["open_n"]) + " open** / " + str(payload["closed_n"]) + " closed of " + str(payload["total_ids"]) + " ids.",
            "C15 append-to-handoffs required: **" + str(payload["c15_must_append_to_handoffs"]) + "** (threshold " + str(C15_THRESHOLD) + ").", ""]
    emit(REPO / args.md_out, "\n".join(head + rows) + "\n")
    print("OPEN " + str(payload["open_n"]) + " / CLOSED " + str(payload["closed_n"]) + " of " + str(payload["total_ids"]))
    print("open ids: " + ", ".join(b["id"] for b in open_ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
