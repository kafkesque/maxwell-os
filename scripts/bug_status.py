#!/usr/bin/env python3
"""Derive a MACHINE-READABLE bug status index from governance/buglog.md (C15 enforcement).

WHY: C15 ("5+ unresolved -> append to every handoff") was unenforceable because the register is prose.
Session 9 found the hand-maintained C15 count wrong: it claimed 17 unresolved while BUG-311/313 carried
RESOLVED headers, and BUG-311 has since REGRESSED. A count nobody can recompute is a count nobody should
quote (BUG-342). This script re-derives it from the file itself, in file order.

Status rule: a "## BUG-<id>" header is a status EVENT and the LAST one wins, except that a later CLOSED
event cannot un-close a REOPEN. Keywords: RESOLVED/CLOSED/FIXED/INVALID/RETRACTED -> closed;
REOPEN/REGRESS/RECURRED -> open; anything else -> open (no closure claim is not a closure).

THE STATUS SLOT IS A POSITION AT A HEADER BOUNDARY, NEVER PROSE (BUG-572, MEASURED 2026-09-27). Only four
positions may decide a bug's status - the LEADING parenthetical, the FIRST segment before the first colon, the
FIRST WORD after that colon, and the TRAILING parenthetical - and a status word in the TITLE may not. The
substring fallback ("read the whole header") is GONE: it read a bug's status off a word in a sentence about the
bug, which is how the duplicate BUG-493 block read CLOSED and how BUG-419/BUG-570 were misread. Alternatives
were measured over 422 heading events and REFUSED: a blanket "everything before the first colon" slot flips 8
events (it destroys the legal trailing slot) and a paren-only slot flips 3 (it ignores a real post-colon FIXED).

Usage:  python3 scripts/bug_status.py            (re-derive the register)
        python3 scripts/bug_status.py --selftest (the known-answer controls, touching nothing else)
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
# BUG-633 (2026-10-04): "OPEN" is deliberately NOT a close word (an absent close-claim is OPEN, C16
# fail-safe), but it IS a recognised claim in the LEADING-parenthetical slot: "(OPEN, ...)" is a
# declaration that the bug is open and must bind before prose fall-through.
OPEN_WORDS = ("OPEN",)
# BUG-429 (2026-09-24): "UNRESOLVED" CONTAINS "RESOLVED", so `### BUG-426 (HIGH, OPEN - UNRESOLVED)` was
# classified CLOSED - a HIGH, explicitly-unresolved bug auto-retired by substring. Same degeneracy class as
# BUG-347 (PARTIAL FIXED), second occurrence. A negated status word is checked FIRST and forces OPEN, which is
# the fail-safe direction: an open bug that is really closed costs a look; a closed bug that is really open
# costs the work being silently abandoned.
NEGATED_WORDS = ("UNRESOLVED", "UNFIXED", "NOT RESOLVED", "NOT FIXED", "STILL OPEN", "NOT CLOSED")
QQ = chr(34) + chr(8220) + chr(8221) + chr(39)
QUOTE_RE = re.compile("[" + QQ + "][^" + QQ + "]*[" + QQ + "]")
PAREN_RE = re.compile("[(]([^)]*)[)]")
# BUG-634 (2026-10-04): a fenced code block delimiter at column 0. A header QUOTED inside a repro fence is
# documentation, not a status event, so scan() masks fenced regions instead of parsing them.
FENCE_RE = re.compile(r"^(`{3,}|~{3,})")


def status_slot(rest: str) -> str:
    """
    Return only the header STATUS SLOT (BUG-350/BUG-572), never the prose title.

    The slot is a POSITION AT A HEADER BOUNDARY and prose in between may NOT decide. The candidates, in order:

      1. the LEADING parenthetical, directly after the bug id - "(MED, FIXED 2026-09-21) ..." - and it is
         AUTHORITATIVE: an explicit "(OPEN, ...)" binds as OPEN here and blocks prose fall-through (BUG-633);
      2. the FIRST segment, before the first colon - "MED - FIXED 2026-09-21: ...";
      3. the FIRST WORD after that colon - how a header writes "UPDATE 2026-09-23: FIXED code-side ...";
      4. the TRAILING parenthetical - "... (HIGH, fixed 2026-09-21)".

    Quoted spans are dropped, so a title that merely quotes a status word cannot decide it. When NO candidate
    names a status word the slot is EMPTY and the event is OPEN: an unlabelled header makes no closure claim, and
    no closure claim is not a closure (C16 fail-safe - an open bug that is really closed costs a look; a closed
    bug that is really open costs the work being silently abandoned).
    """
    m = PAREN_RE.match(rest)
    pre, sep, post = rest.partition(chr(58))
    # BUG-633: the LEADING parenthetical is the authoritative slot. It may carry an explicit OPEN claim,
    # which must bind HERE and block the candidate-2 fall-through that let trailing prose
    # ("... fixed for S2 only") retire a live bug whose slot read "(OPEN, ...)".
    if m:
        lead = QUOTE_RE.sub(chr(32), m.group(1)).strip()
        if any(w in lead.upper() for w in STATUS_WORDS + OPEN_WORDS):
            return lead
    cands: list[str] = [pre]
    if sep and post.strip():
        cands.append(post.split()[0])
    trailing = PAREN_RE.findall(rest)
    if trailing:
        cands.append(trailing[-1])
    for cand in cands:
        clean = QUOTE_RE.sub(chr(32), cand).strip()
        if any(w in clean.upper() for w in STATUS_WORDS):
            return clean
    return ""


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


# BUG-572 (D-2689): the slot rule's KNOWN-ANSWER CONTROLS. Each case is a LIVE header (or the exact shape of
# one) and the status it must read. The FIRST three are the defect itself - a status word in a TITLE that the
# header is merely describing - and each of them read CLOSED before this rule: a closed bug whose fix nobody
# had done. The rest are the SHAPES THAT MUST NOT MOVE (a fix that tightens one direction must not lose the
# legal slot in another); the alternatives measured on 2026-09-27 broke exactly these.
SLOT_CASES: tuple[tuple[str, str, str], ...] = (
    ("the_title_may_not_decide",
     "(OPEN, LOW): the duplicate BUG-493 CLOSED block is NOT byte-identical (the earlier claim was FALSE)", "open"),
    ("a_noun_in_the_title_may_not_decide",
     "(LOW, OPEN 2026-09-23) - bug_status.json is schema-ASYMMETRIC: open is a list of objects, closed is a list "
     "of plain id strings", "open"),
    ("a_clause_about_the_incident_may_not_decide",
     "UPDATE (2026-09-26): the INCIDENT is closed by construction; the RAIL is still OWED", "open"),
    ("a_filename_in_the_title_may_not_decide",
     "\u2014 R2 verification provenance gap: r5 override set is unstamped; closed_menu.py has a dead constant "
     "(HIGH, 2026-09-20)", "open"),
    ("the_trailing_slot_still_decides",
     "No degenerate-arm guard: a collapsed arm could be read as a tie (HIGH, fixed 2026-09-21)", "closed"),
    ("the_trailing_slot_still_decides_a_quote",
     "Name collision: two different human instruments both called \"ANCHOR-1\" (MED, FIXED 2026-09-21)", "closed"),
    ("the_trailing_slot_still_decides_a_path",
     "decision numbering collision: DECISION-LOG.md leads config/decisions.yaml by 3 (FIXED, 2026-09-23)", "closed"),
    ("a_status_named_after_the_colon_still_decides",
     "(MED) - UPDATE 2026-09-23: FIXED code-side (the export re-run is an owner gate)", "closed"),
    ("the_leading_slot_outranks_the_title",
     "(MED \u2014 FIXED 2026-09-21): the C15 classifier treated \"PARTIALLY FIXED\" as CLOSED", "closed"),
    ("an_explicit_open_leading_slot_outranks_trailing_prose",
     "(OPEN, 2026-10-04) \u2014 the D2496 gate CANNOT DISTINGUISH a declared failure "
     "(the BUG-609 class, fixed for S2 only)", "open"),
)


def slot_faults() -> list[str]:
    """Every live header shape the slot rule must read a given way; the first fault names itself (BUG-572)."""
    faults: list[str] = []
    for name, text, want in SLOT_CASES:
        got = classify(status_slot(text))
        if got != want:
            faults.append("FAIL selftest/" + name + ": " + repr(text[:52]) + " reads " + got + ", expected " + want)
    return faults


def self_test() -> int:
    """Assert the classifier's registered edge cases before its output is trusted (BUG-347/BUG-572).

    Returns how many KNOWN-ANSWER CONTROLS fired (C20: a count is REPORTED, never hardcoded), so a caller can see
    that the controls RAN and not merely that nothing was printed.
    """
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
    faults = slot_faults()
    if faults:
        raise SystemExit("FAIL-CLOSED (C16): " + faults[0] + " (BUG-572: a status word in a header's TITLE may "
                         "not decide a bug's status)")
    # BUG-634: a header QUOTED inside a fenced repro block is documentation, not a status event.
    fence_fixture = [
        "## BUG-900 (CLOSED, 2026-10-04) — the real header",
        "```",
        "## BUG-900 (REOPEN, 2026-10-04) — quoted in a repro, must not re-open",
        "```",
    ]
    fence_scanned = scan(fence_fixture)
    if len(fence_scanned["BUG-900"]["events"]) != 1 or fence_scanned["BUG-900"]["status"] != "closed":
        raise SystemExit("FAIL-CLOSED (BUG-634): a fenced header quoted in a repro was parsed as a status event")
    return len(cases) + len(SLOT_CASES) + 1


def scan(text_lines: list[str]) -> dict[str, dict]:
    """Fold header events, in file order, into one status per bug id.

    BUG-634: fenced code blocks are masked. A header QUOTED inside a repro fence is documentation,
    not a status event, so fence-delimited lines never match HEADER_RE.
    """
    bugs: dict[str, dict] = {}
    fence_char: str | None = None
    fence_width: int = 0
    for i, line in enumerate(text_lines, start=1):
        fm = FENCE_RE.match(line)
        if fm:
            marker = fm.group(1)
            ch, w = marker[0], len(marker)
            if fence_char is None:
                fence_char, fence_width = ch, w
            elif ch == fence_char and w >= fence_width:
                fence_char, fence_width = None, 0
            continue
        if fence_char is not None:
            continue  # inside a fenced block — a quoted header here is not an event
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true",
                    help="the known-answer controls only: no log is read and no artifact is written")
    ap.add_argument("--json-out")
    ap.add_argument("--md-out")
    args = ap.parse_args()
    controls = self_test()
    if args.selftest:
        print("ok selftest: bug_status " + str(controls) + " known-answer control(s) fire (BUG-347/429/572)")
        return 0
    outs = declared_outputs()   # the defaults ARE the declared artifact paths - one home (D-2646)
    json_out = args.json_out or outs[".json"]
    md_out = args.md_out or outs[".md"]
    bugs = scan(BUGLOG.read_text(encoding="utf-8").splitlines())
    open_ids = sorted((b for b in bugs.values() if b["status"] == "open"), key=lambda b: int(b["id"][4:]))
    closed_ids = sorted((b for b in bugs.values() if b["status"] == "closed"), key=lambda b: int(b["id"][4:]))
    payload = {"schema_version": "1.0", "source": "governance/buglog.md",
               "parser": "scripts/bug_status.py", "total_ids": len(bugs), "open_n": len(open_ids),
               "closed_n": len(closed_ids), "c15_threshold": C15_THRESHOLD,
               "c15_must_append_to_handoffs": len(open_ids) >= C15_THRESHOLD,
               "open": [{"id": b["id"], "title": b["title"], "events": len(b["events"])} for b in open_ids],
               "closed": [b["id"] for b in closed_ids]}
    emit(REPO / json_out, json.dumps(payload, indent=2) + "\n")
    rows = ["| id | title (last header) | events |", "|---|---|---|"]
    rows += ["| " + b["id"] + " | " + str(b["title"]) + " | " + str(len(b["events"])) + " |" for b in open_ids]
    head = ["# Bug status index (mechanical, re-derived)", "",
            "Re-derive with `python3 scripts/bug_status.py` (source: `governance/buglog.md`).", "",
            "**" + str(payload["open_n"]) + " open** / " + str(payload["closed_n"]) + " closed of " + str(payload["total_ids"]) + " ids.",
            "C15 append-to-handoffs required: **" + str(payload["c15_must_append_to_handoffs"]) + "** (threshold " + str(C15_THRESHOLD) + ").", ""]
    emit(REPO / md_out, "\n".join(head + rows) + "\n")
    print("OPEN " + str(payload["open_n"]) + " / CLOSED " + str(payload["closed_n"]) + " of " + str(payload["total_ids"]))
    print("open ids: " + ", ".join(b["id"] for b in open_ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
