#!/usr/bin/env python3
"""check_governance_faces.py - the governance Markdown FACES must not contradict the machine register (BUG-588/D-2692).

WHY (the SEVENTH rail). The first six rails watch the machine register against its OWN re-derivation. The
hand-edited Markdown faces (DECISION-LOG.md, MASTER-TASK-REGISTER.md) restate derived facts as prose, and those
restatements are what drifted (BUG-625/BUG-626 marked OPEN while the register said RESOLVED; a header restated
"145 OPEN / 220 CLOSED / 365" while the register said 132/234/366). A count restated in prose is stale the moment
it is written (BUG-588); a header may not RESTATE a count (D-2692). This rail compares the faces' CURRENT-STATE
claims to the authoritative registers and fails closed on contradiction.

Scope discipline (why it will not false-positive on append-only history): FOUR surfaces are checked -
  (1) bug-status TABLE rows ``| BUG-<id> | <STATUS> |`` in the DECISION-LOG/MTR faces (bug status is binary and
      fully derivable from governance/bug_status.json, so a row that disagrees is drift, not history);
  (2) census restatements in the HEADER BLOCK ONLY (the first lines above the first tiered ``## <icon>``
      section) — the legacy 3-part ``N OPEN / N CLOSED / N`` form;
  (3) the LIVE census on a ``Register truth``/``Register:`` marker line ANYWHERE in the file (BUG-669: the live
      face moved inside a tiered section and switched to a 2-part ``N open / N closed`` form that the header
      scan never matched);
  (4) the buglog.md tiered tables (BUG-669): every ``| BUG-<id> |`` row sits in an OPEN tier and must be OPEN
      in the register. Historical entries in the DONE sections are append-only snapshots that were true when
      written and are never re-checked (they use bullets / ``## BUG-<id>`` prose headers, not table rows).

Exit: 0 all faces agree with the registers | 1 a face contradicts a register (fail closed).
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUG_STATUS = REPO / "governance" / "bug_status.json"
DECISIONS_SUMMARY = REPO / "config" / "decisions_summary.json"
FACES = (REPO / "DECISION-LOG.md", REPO / "MASTER-TASK-REGISTER.md")
# BUG-669: the buglog.md tiered tables are a live face too. Every ``| BUG-<id> |`` table row sits in an
# OPEN tier (🔴/🟠/🟡); the CLOSED tier uses bullets, so only the OPEN direction is table-checked.
BUGLOG_FACE = REPO / "governance" / "buglog.md"

# BUG status words must resolve consistently with scripts/bug_status.py (the register's own parser).
CLOSE_WORDS = ("RESOLVED", "CLOSED", "FIXED", "INVALID", "RETRACTED")
OPEN_WORDS = ("OPEN", "REOPEN", "REGRESS", "RECURRED", "UNRESOLVED", "UNFIXED", "PARTIAL")
NEGATED_CLOSE = ("UNRESOLVED", "UNFIXED", "NOT RESOLVED", "NOT FIXED", "STILL OPEN", "NOT CLOSED")

BUG_ROW_RE = re.compile(r"^\|\s*BUG-(\d+)\s*\|\s*([^|]+?)\s*\|")
# A tiered section header opens the body of append-only history; the header block is above the FIRST one.
TIER_RE = re.compile(r"^##\s+[🔴🟠🟡🟢⚪✅]")
CENSUS_RE = re.compile(r"(\d+)\s+(?:OPEN|open)\s*/\s*(\d+)\s+(?:CLOSED|closed)\s*/\s*(\d+)")
DECISIONS_RE = re.compile(r"\bdecisions\s+(\d+)\b")
# BUG-669: the LIVE census lives on a "Register truth"/"Register:" marker line that may sit INSIDE a
# tiered section, and it is 2-part ("N open / N closed") with a decisions + bugs count. The 3-part
# CENSUS_RE above never matched it (position + format blindspot). Match the WHOLE line: a bare
# "register" mention with a later colon (prose) is NOT a live census and must not be flagged, so the
# marker and the numbers are one regex.
LIVE_CENSUS_RE = re.compile(
    r"\bRegister\b(?:\s+truth\b)?[^:\n]*:\s*"
    r"(\d+)\s+decisions\b"
    r"[^\n]*?"
    r"(\d+)\s+bugs\b"
    r"[^\n]*?"
    r"\(\s*(\d+)\s+open\s*/\s*(\d+)\s+closed",
    re.IGNORECASE,
)


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


def check_live_census(path: Path, bug: dict, dec: dict) -> list[str]:
    """BUG-669: the LIVE census is on a ``Register truth``/``Register:`` marker line ANYWHERE in the file
    (not just the pre-tier header block). It restates ``N decisions · N bugs (N open / N closed)`` and every
    number must equal the register."""
    problems: list[str] = []
    open_n, closed_n, total_ids = bug["open_n"], bug["closed_n"], bug["total_ids"]
    total_dec = dec.get("total_decisions") or dec.get("total")
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        m = LIVE_CENSUS_RE.search(line)
        if not m:
            continue
        dec_c, bugs_c, open_c, closed_c = (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
        if (dec_c, bugs_c, open_c, closed_c) != (int(total_dec), int(total_ids), open_n, closed_n):
            problems.append(
                f"{path.name}:{n} restates census {dec_c} decisions / {bugs_c} bugs "
                f"({open_c} open / {closed_c} closed) but the register says "
                f"{int(total_dec)} / {int(total_ids)} ({open_n} / {closed_n})")
    return problems


def check_buglog_tiers(buglog: Path, open_ids: set[int], known: set[int]) -> list[str]:
    """BUG-669: every ``| BUG-<id> |`` table row in the buglog's TOP tiered summary (🔴/🟠/🟡/✅) sits in an
    OPEN tier and must name a bug the register knows and holds OPEN. The CLOSED tier uses bullets (not table
    rows). Scanning STOPS at the first non-tier ``## `` header (the start of append-only history, e.g.
    ``## BUG-253 — ...``) so historical "appended inbox" tables are never re-checked."""
    problems: list[str] = []
    section_open: bool | None = None
    for n, line in enumerate(buglog.read_text(encoding="utf-8").splitlines(), start=1):
        if line.startswith("## "):
            if TIER_RE.match(line):
                section_open = any(icon in line for icon in "🔴🟠🟡")
                continue
            break  # end of the tiered summary; the rest is append-only history
        m = BUG_ROW_RE.match(line)
        if not m or section_open is None:
            continue
        bid = int(m.group(1))
        if bid not in known:
            problems.append(f"buglog.md:{n} names BUG-{bid} which the register does not carry (unknown id)")
            continue
        if section_open and bid not in open_ids:
            problems.append(f"buglog.md:{n} names BUG-{bid} in an OPEN tier but the register says CLOSED")
        elif not section_open and bid in open_ids:
            problems.append(f"buglog.md:{n} names BUG-{bid} in a CLOSED tier but the register says OPEN")
    return problems


def _selftest_live_census_regex() -> bool:
    m = LIVE_CENSUS_RE.search(
        "Register: 993 decisions · 434 bugs (162 open / 272 closed; highest OPEN = BUG-670).")
    return bool(m) and (m.group(1), m.group(2), m.group(3), m.group(4)) == ("993", "434", "162", "272")


def _selftest_live_census_ignores_prose() -> bool:
    bug = {"open_n": 162, "closed_n": 272, "total_ids": 434}
    dec = {"total_decisions": 993}
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "face.md"
        p.write_text("a FALSE claim in the register. Enforced by scripts in just health: enabled: true.\n",
                     encoding="utf-8")
        return check_live_census(p, bug, dec) == []


def _selftest_live_census_agree() -> bool:
    bug = {"open_n": 162, "closed_n": 272, "total_ids": 434}
    dec = {"total_decisions": 993}
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "face.md"
        p.write_text("Register: 993 decisions · 434 bugs (162 open / 272 closed).\n", encoding="utf-8")
        return check_live_census(p, bug, dec) == []


def _selftest_live_census_disagree() -> bool:
    bug = {"open_n": 160, "closed_n": 274, "total_ids": 434}
    dec = {"total_decisions": 993}
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "face.md"
        p.write_text("Register: 993 decisions · 434 bugs (162 open / 272 closed).\n", encoding="utf-8")
        return len(check_live_census(p, bug, dec)) == 1


def _selftest_buglog_tiers() -> bool:
    known = {640, 650}
    open_ids = {640}  # BUG-650 is CLOSED in this synthetic register
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "buglog.md"
        p.write_text("## 🔴 OPEN — MUST\n| BUG-650 | 2026-01-01 | x | |\n", encoding="utf-8")
        return len(check_buglog_tiers(p, open_ids, known)) == 1


def selftest() -> int:
    """Known-answer controls in BOTH directions (a control nothing runs is a comment, BUG-492)."""
    rows = [
        ("a CLOSED claim on an OPEN bug must fire",
         status_word("RESOLVED") == "closed" and status_word("OPEN") == "open"),
        ("a negated status word forces OPEN (BUG-429 family)",
         status_word("UNRESOLVED") == "open" and status_word("PARTIAL") == "open"),
        ("an unlabelled cell makes no claim",
         status_word("some prose with no status") is None),
        # BUG-669 controls: live census regex + tier scan must fire in BOTH directions.
        ("the 2-part live census regex parses decisions·bugs(open/closed)",
         _selftest_live_census_regex()),
        ("a prose 'register...:' mention with no census is ignored (not flagged)",
         _selftest_live_census_ignores_prose()),
        ("a Register-truth marker with a matching census makes no problem",
         _selftest_live_census_agree()),
        ("a Register-truth marker restating a STALE census must fire",
         _selftest_live_census_disagree()),
        ("a buglog OPEN-tier row naming a CLOSED bug must fire",
         _selftest_buglog_tiers()),
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
    open_ids = known - closed
    problems: list[str] = []
    for face in FACES:
        if not face.exists():
            problems.append(f"{face.name}: missing face (cannot check what is not there)")
            continue
        problems.extend(check_bug_rows(face, closed, known))
        problems.extend(check_header_census(face, bug, dec))
        problems.extend(check_live_census(face, bug, dec))
    if BUGLOG_FACE.exists():
        problems.extend(check_buglog_tiers(BUGLOG_FACE, open_ids, known))
    else:
        problems.append(f"{BUGLOG_FACE.name}: missing face (cannot check what is not there)")
    if problems:
        print("FAIL governance-faces: " + str(len(problems)) + " face(s) contradict the register:")
        for p in problems:
            print("  " + p)
        return 1
    print("ok governance-faces: bug-status table rows and header/live census agree with the register "
          "(" + str(len(FACES)) + " restatement face(s) + buglog tiers, " + str(len(known)) + " bug ids)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
