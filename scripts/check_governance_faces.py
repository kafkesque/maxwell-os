#!/usr/bin/env python3
"""check_governance_faces.py - the governance Markdown FACES must not contradict the machine register (BUG-588/D-2692).

WHY (the SEVENTH rail). The first six rails watch the machine register against its OWN re-derivation. The
hand-edited Markdown faces (DECISION-LOG.md, MASTER-TASK-REGISTER.md) restate derived facts as prose, and those
restatements are what drifted (BUG-625/BUG-626 marked OPEN while the register said RESOLVED; a header restated
"145 OPEN / 220 CLOSED / 365" while the register said 132/234/366). A count restated in prose is stale the moment
it is written (BUG-588); a header may not RESTATE a count (D-2692). This rail compares the faces' CURRENT-STATE
claims to the authoritative registers and fails closed on contradiction.

Scope discipline (why it will not false-positive on append-only history): only TWO surfaces are checked -
  (1) bug-status TABLE rows ``| BUG-<id> | <STATUS> |`` anywhere in the faces (bug status is binary and fully
      derivable from governance/bug_status.json, so a row that disagrees is drift, not history);
  (2) census restatements in the HEADER BLOCK ONLY (the first lines above the first tiered ``## <icon>``
      section), where the CURRENT census lives. Historical entries in the DONE sections are append-only snapshots
      that were true when written and are never re-checked.

Exit: 0 all faces agree with the registers | 1 a face contradicts a register (fail closed).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUG_STATUS = REPO / "governance" / "bug_status.json"
DECISIONS_SUMMARY = REPO / "config" / "decisions_summary.json"
FACES = (REPO / "DECISION-LOG.md", REPO / "MASTER-TASK-REGISTER.md")

# BUG status words must resolve consistently with scripts/bug_status.py (the register's own parser).
CLOSE_WORDS = ("RESOLVED", "CLOSED", "FIXED", "INVALID", "RETRACTED")
OPEN_WORDS = ("OPEN", "REOPEN", "REGRESS", "RECURRED", "UNRESOLVED", "UNFIXED", "PARTIAL")
NEGATED_CLOSE = ("UNRESOLVED", "UNFIXED", "NOT RESOLVED", "NOT FIXED", "STILL OPEN", "NOT CLOSED")

BUG_ROW_RE = re.compile(r"^\|\s*BUG-(\d+)\s*\|\s*([^|]+?)\s*\|")
# A tiered section header opens the body of append-only history; the header block is above the FIRST one.
TIER_RE = re.compile(r"^##\s+[🔴🟠🟡🟢⚪✅]")
CENSUS_RE = re.compile(r"(\d+)\s+(?:OPEN|open)\s*/\s*(\d+)\s+(?:CLOSED|closed)\s*/\s*(\d+)")
DECISIONS_RE = re.compile(r"\bdecisions\s+(\d+)\b")


def status_word(w: str) -> str | None:
    """Map a table STATUS cell to 'open' or 'closed', or None if it names no status word (fail-safe: no
    closure claim is not a closure, C16 - matches scripts/bug_status.py's rule)."""
    u = w.upper()
    for neg in NEGATED_CLOSE:
        if neg in u:
            return "open"
    if any(c in u for c in CLOSE_WORDS):
        return "closed"
    if any(o in u for o in OPEN_WORDS):
        return "open"
    return None


def load_registers() -> tuple[dict, dict]:
    """Return (bug_status, decisions_summary) - a missing register is a defect, not an empty config."""
    if not BUG_STATUS.exists():
        raise SystemExit("FAIL-CLOSED: governance/bug_status.json missing - run scripts/bug_status.py first")
    if not DECISIONS_SUMMARY.exists():
        raise SystemExit("FAIL-CLOSED: config/decisions_summary.json missing - run scripts/recompute_decision_summary.py")
    bug = json.loads(BUG_STATUS.read_text(encoding="utf-8"))
    dec = json.loads(DECISIONS_SUMMARY.read_text(encoding="utf-8"))
    return bug, dec


def bug_closed_set(bug: dict) -> set[int]:
    """The set of BUG ids the register says are CLOSED (both the list and the dict entries)."""
    out: set[int] = set()
    for item in bug.get("closed", []):
        if isinstance(item, dict):
            sid = item.get("id")
        else:
            sid = item
        m = re.match(r"BUG-(\d+)", str(sid))
        if m:
            out.add(int(m.group(1)))
    return out


def bug_known_ids(bug: dict) -> set[int]:
    """Every BUG id the register knows about (open + closed)."""
    out: set[int] = set()
    for item in list(bug.get("open", [])) + list(bug.get("closed", [])):
        sid = item.get("id") if isinstance(item, dict) else item
        m = re.match(r"BUG-(\d+)", str(sid))
        if m:
            out.add(int(m.group(1)))
    return out


def header_block(path: Path) -> list[str]:
    """The lines above the first tiered section - where the CURRENT census lives."""
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    for line in lines:
        if TIER_RE.match(line):
            break
        out.append(line)
    return out


def check_bug_rows(path: Path, closed: set[int], known: set[int]) -> list[str]:
    """Every ``| BUG-<id> | <STATUS> |`` row must agree with the register."""
    problems: list[str] = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        m = BUG_ROW_RE.match(line)
        if not m:
            continue
        bid = int(m.group(1))
        claimed = status_word(m.group(2))
        if bid not in known:
            problems.append(f"{path.name}:{n} names BUG-{bid} which the register does not carry (unknown id)")
            continue
        if claimed is None:
            continue  # no status word in the cell -> no claim -> nothing to contradict
        actual = "closed" if bid in closed else "open"
        if claimed != actual:
            problems.append(
                f"{path.name}:{n} claims BUG-{bid} is {claimed.upper()} but the register says {actual.upper()}")
    return problems


def check_header_census(path: Path, bug: dict, dec: dict) -> list[str]:
    """The LAST census restatement in the header block must equal the register (no restatement = no drift)."""
    problems: list[str] = []
    block = header_block(path)
    open_n, closed_n, total_ids = bug["open_n"], bug["closed_n"], bug["total_ids"]
    total_dec = dec.get("total_decisions") or dec.get("total")

    last_census: tuple[int, int, int] | None = None
    last_census_line = 0
    for n, line in enumerate(block, start=1):
        m = CENSUS_RE.search(line)
        if m:
            last_census = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            last_census_line = n
    if last_census is not None and last_census != (open_n, closed_n, total_ids):
        problems.append(
            f"{path.name}:{last_census_line} restates census {last_census[0]}/{last_census[1]}/{last_census[2]} "
            f"but the register says {open_n}/{closed_n}/{total_ids}")

    last_dec: int | None = None
    last_dec_line = 0
    for n, line in enumerate(block, start=1):
        m = DECISIONS_RE.search(line)
        if m:
            last_dec = int(m.group(1))
            last_dec_line = n
    if last_dec is not None and total_dec is not None and last_dec != int(total_dec):
        problems.append(
            f"{path.name}:{last_dec_line} restates decisions {last_dec} but the register says {total_dec}")
    return problems


def selftest() -> int:
    """Known-answer controls in BOTH directions (a control nothing runs is a comment, BUG-492)."""
    rows = [
        ("a CLOSED claim on an OPEN bug must fire",
         status_word("RESOLVED") == "closed" and status_word("OPEN") == "open"),
        ("a negated status word forces OPEN (BUG-429 family)",
         status_word("UNRESOLVED") == "open" and status_word("PARTIAL") == "open"),
        ("an unlabelled cell makes no claim",
         status_word("some prose with no status") is None),
    ]
    for name, ok in rows:
        print(("  ok  " if ok else "  !!  ") + name)
    failed = [name for name, ok in rows if not ok]
    if failed:
        print("FAIL selftest: " + str(len(failed)) + " of " + str(len(rows)) + " control(s) did not fire")
        return 1
    print("ok governance-faces selftest: " + str(len(rows)) + "/" + str(len(rows)) + " control(s) fire")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()
    bug, dec = load_registers()
    closed = bug_closed_set(bug)
    known = bug_known_ids(bug)
    problems: list[str] = []
    for face in FACES:
        if not face.exists():
            problems.append(f"{face.name}: missing face (cannot check what is not there)")
            continue
        problems.extend(check_bug_rows(face, closed, known))
        problems.extend(check_header_census(face, bug, dec))
    if problems:
        print("FAIL governance-faces: " + str(len(problems)) + " face(s) contradict the register:")
        for p in problems:
            print("  " + p)
        return 1
    print("ok governance-faces: bug-status table rows and header census agree with the register "
          "(" + str(len(FACES)) + " face(s), " + str(len(known)) + " bug ids)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
