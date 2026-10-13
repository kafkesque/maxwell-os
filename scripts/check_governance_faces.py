#!/usr/bin/env python3
"""check_governance_faces.py - the governance Markdown FACES must not contradict the machine register (BUG-588/D-2692).

WHY (the SEVENTH rail). The first six rails watch the machine register against its OWN re-derivation. The
hand-edited Markdown faces (DECISION-LOG.md, MASTER-TASK-REGISTER.md) restate derived facts as prose, and those
restatements are what drifted (BUG-625/BUG-626 marked OPEN while the register said RESOLVED; a header restated
"145 OPEN / 220 CLOSED / 365" while the register said 132/234/366). A count restated in prose is stale the moment
it is written (BUG-588); a header may not RESTATE a count (D-2692). This rail compares the faces' CURRENT-STATE
claims to the authoritative registers and fails closed on contradiction.

Scope discipline (why it will not false-positive on append-only history): FIVE surfaces are checked -
  (1) bug-status TABLE rows ``| BUG-<id> | <STATUS> |`` in the DECISION-LOG/MTR faces (bug status is binary and
      fully derivable from governance/bug_status.json, so a row that disagrees is drift, not history);
  (2) census restatements in the HEADER BLOCK ONLY (the first lines above the first tiered ``## <icon>``
      section) — the legacy 3-part ``N OPEN / N CLOSED / N`` form;
  (3) the LIVE census on a ``Register truth``/``Register:`` marker line ANYWHERE in the file (BUG-669: the live
      face moved inside a tiered section and switched to a 2-part ``N open / N closed`` form that the header
      scan never matched);
  (4) the buglog.md tiered tables (BUG-669): every ``| BUG-<id> |`` row sits in an OPEN tier and must be OPEN
      in the register. Historical entries in the DONE sections are append-only snapshots that were true when
      written and are never re-checked (they use bullets / ``## BUG-<id>`` prose headers, not table rows);
  (5) the CLAIM SURFACE of the declared history region (D-2984, BUG-760): a live-claim label, a live census
      marker, a decision row and a present-tense "BUG-N is OPEN" assertion are all claims about NOW unless
      they DECLARE THE MOMENT they speak about (D-2660). Surfaces (1)-(4) read tables and marker lines; this
      one reads PROSE, which is where the faces were measured telling the owner a closed decision was still
      pending (``| D2622 | ACTIVE |`` under "OPEN / PENDING - highest priority first" while the register said
      RESOLVED). Its scope rule is the whole reason it cannot false-positive on history: a claim's moment is
      its section heading (table rows) or its date-stamped entry (prose), both of which the append-only files
      already carry - so the rule reports ZERO faults in buglog.md and NO history byte was rewritten.

Exit: 0 all faces agree with the registers | 1 a face contradicts a register (fail closed).
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
BUG_STATUS = REPO / "governance" / "bug_status.json"
DECISIONS_SUMMARY = REPO / "config" / "decisions_summary.json"
FACES = (REPO / "DECISION-LOG.md", REPO / "MASTER-TASK-REGISTER.md")
# BUG-669: the buglog.md tiered tables are a live face too. Every ``| BUG-<id> |`` table row sits in an
# OPEN tier (🔴/🟠/🟡); the CLOSED tier uses bullets, so only the OPEN direction is table-checked.
BUGLOG_FACE = REPO / "governance" / "buglog.md"

# ---------------------------------------------------------------- D-2984: the CLAIM SURFACE
# Everything below the GOV-HISTORY marker is DECLARED to be "DATED HISTORY: append-only, NOT a register"
# (D-2981). MEASURED 2026-10-13 (BUG-760): that declaration was never enforced, so the region could - and
# did - make LIVE claims beside the derived block. MASTER-TASK-REGISTER.md carried a second "CURRENT OPEN
# INDEX ... the live face" and a restated census ("highest OPEN = BUG-750") while the register said BUG-757;
# DECISION-LOG.md listed `| D2622 | ACTIVE |` and `| D2621 | PROPOSED |` under "OPEN / PENDING - highest
# priority first" while config/decisions.yaml said RESOLVED. The DERIVED block was right; the hand prose
# next to it was wrong, and the four surfaces checked above never read prose. A claim is either JOINED to
# the register or it DECLARES THE MOMENT it speaks about (D-2660). There is no third state.
DECISIONS_REGISTER = REPO / "config" / "decisions.yaml"
HIST_MARKER_RE = re.compile(r"GOV-HISTORY:START")
DATE_RE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")
HEADING_RE = re.compile(r"^#{1,6}\s")
#: A label that POINTS AT the live state. It has ONE home (the derived block above the marker); a second
#: pointer is a second home (D-2642), which is why this limb has NO date exemption: "this is the live face"
#: is not a claim about a moment, it is a claim about WHERE THE CURRENT STATE IS. The label must LEAD the
#: line: MEASURED 2026-10-13, the phrase also occurs in prose that DISCUSSES the face (buglog.md:9241, the
#: BUG-669 entry), and a rule that fires on a discussion of a pointer is not a rule about pointers.
LIVE_LABEL_RE = re.compile(
    r"^\s*(?:>\s*)*(?:[*_]{0,2})?\s*(?:CURRENT\s+OPEN\s*(?:/\s*PENDING)?\s*INDEX|the\s+live\s+face)\b",
    re.IGNORECASE,
)
#: The highest-open bug is a DERIVED value: ONE home (the derived block), D-2642. A hand line may state it only
#: as a claim about a moment (D-2660) - which is how "highest OPEN then BUG-695" stays true while the
#: register moves on. MEASURED 2026-10-13: MASTER-TASK-REGISTER.md:61 said "highest OPEN = BUG-750" with no
#: moment at all, while the register's own answer was BUG-757.
HIGHEST_OPEN_RE = re.compile(r"highest\s+OPEN\b", re.IGNORECASE)
#: A moment named IN WORDS rather than as a date. The field above must carry one on its OWN line - an entry
#: stamp one line up is not enough for a DERIVED value, because the value is the thing that moved.
MOMENT_TOKEN_RE = re.compile(r"\b(then|as\s+of|at\s+the\s+time|that\s+date)\b", re.IGNORECASE)
DEC_ROW_RE = re.compile(r"^\|\s*[*_`'\"]*\s*(D-?[0-9]+[a-z]?)\b")
#: MEASURED 2026-10-13, AFTER the first version of this rule landed (the D-2984 verification pass): the row
#: parser above originally required a BARE id cell, so two row SHAPES were invisible to the join - a bolded id
#: (`| **D-274b** | **RESOLVED** | ... |`, DECISION-LOG.md:343) and an id with a label appended
#: (`| D2546 SHACL+OWL | PLANNED | ... |`, :3260, a table whose own header reads "| ID | Registry state | True
#: status |"). Both instances sat in DATED sections, so seeing them changed no verdict - but a claim surface
#: the rule cannot SEE is not covered by the rule, and one undated row in either shape could have hidden a
#: stale state exactly as the two D-2984 found. The claim a row makes is the id it LEADS with, after any
#: emphasis is stripped; the state it claims is still the LAST bare state cell.
BARE_STATE_RE = re.compile(r"^[*_`'\"]*([A-Za-z][A-Za-z /-]{1,18}?)[*_`'\"]*$")
#: `BUG-539, still OPEN` / `BUG-695 remains OPEN` / `BUG-333 is OPEN`. The id and the claim must be ADJACENT:
#: a line that merely mentions a closed bug beside a claim about another one is not a claim about it.
OPEN_ASSERT_RE = re.compile(
    r"\bBUG-(\d+)\s*,?\s*(?:is|remains|stays|still|is\s+still)\s+OPEN\b"
    r"|\bBUG-(\d+)[^.\n]{0,24}?\bis\s+(?:still\s+)?OPEN\b",
    re.IGNORECASE,
)

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


def canon_decision_id(raw: str) -> str:
    """One spelling for a decision id. MEASURED 2026-10-13: config/decisions.yaml carries 691 bare ids
    (``D2622``) and 420 dashed ones (``D-2983``) for the same kind of object, with ZERO collisions under
    this normalisation - so a row and the register can be compared without inventing a second registry
    (D-2693: one spelling, one declared route)."""
    return re.sub(r"^D-?", "D", raw.strip().upper())


def load_decision_states() -> dict[str, str]:
    """id -> state from config/decisions.yaml (the register). A missing or shapeless register is a defect,
    not an empty config (C16): the faces cannot be joined to a register that is not there."""
    if not DECISIONS_REGISTER.exists():
        raise SystemExit("FAIL-CLOSED (C16): config/decisions.yaml missing - the faces cannot be joined "
                         "to a register that is not there")
    doc = yaml.safe_load(DECISIONS_REGISTER.read_text(encoding="utf-8"))
    recs = doc.get("decisions") if isinstance(doc, dict) else doc
    if not isinstance(recs, list):
        raise SystemExit("FAIL-CLOSED (C16): config/decisions.yaml carries no decision list")
    out: dict[str, str] = {}
    for rec in recs:
        if isinstance(rec, dict) and rec.get("id"):
            out[canon_decision_id(str(rec["id"]))] = str(rec.get("state", "")).strip().upper()
    return out


def history_start(lines: list[str]) -> int:
    """The index AFTER the GOV-HISTORY marker: the first line a face has DECLARED to be dated history. A face
    that declares no history has no history region, so nothing below is policed (an absent declaration is not
    an implicit one)."""
    for i, line in enumerate(lines):
        if HIST_MARKER_RE.search(line):
            return i + 1
    return len(lines)


def first_date(text: str) -> str | None:
    """The moment a line declares, if it declares one."""
    m = DATE_RE.search(text)
    return m.group(1) if m else None


def section_date(lines: list[str], i: int, start: int) -> str | None:
    """A TABLE ROW's declared moment is its SECTION's: the date on the nearest preceding heading, if it
    carries one. Bounded by the history marker so a heading ABOVE the region (a live tier label) can never
    date a claim inside it."""
    for j in range(i, start - 1, -1):
        if HEADING_RE.match(lines[j]):
            return first_date(lines[j])
    return None


def entry_date(lines: list[str], i: int, start: int) -> str | None:
    """A PROSE claim's declared moment is its ENTRY's: the nearest preceding line that carries a date. This is
    how an append-only log stays honest without being rewritten - MEASURED 2026-10-13: all nine present-tense
    "still OPEN" claims in governance/buglog.md sit under entries that already declare their date, so the rule
    reports ZERO faults there and NO history byte had to be edited."""
    for j in range(i, start - 1, -1):
        d = first_date(lines[j])
        if d:
            return d
    return None


def claimed_state(cells: list[str], vocab: set[str]) -> str | None:
    """The state a row CLAIMS: the LAST cell that names a register state word and nothing else. This is what
    makes a 4-column TRANSITION row (``| D2546 | PLANNED | RESOLVED | the ship |``) readable without a second
    parser: its claim is RESOLVED, the state it ended in. A long prose cell is not a state claim, so a row
    that merely discusses "resolved" in a sentence makes no claim in that cell."""
    last: str | None = None
    for cell in cells:
        m = BARE_STATE_RE.match(cell.strip())
        if not m:
            continue
        word = m.group(1).strip().upper()
        if word in vocab:
            last = word
    return last


def history_faults(path: Path, lines: list[str], states: dict[str, str],
                   closed_bugs: set[int], known_bugs: set[int]) -> list[str]:
    """D-2984: the CLAIM SURFACE of a face's declared history region. Four limbs, each with its repair:

    (1) a live-claim LABEL has one home (the derived block) - no exemption;
    (2) a LIVE census marker may not stand in a region declared "NOT a register" - no exemption, because the
        marker IS the live one by definition (its repair is to name the moment and stop being the marker);
    (3) a decision ROW is a claim about the register - joined, unless its section declares its moment;
    (4) a present-tense assertion that a BUG is OPEN is a claim about now - joined, unless its entry declares
        its moment.

    History is never deleted (R-D410): every fault names the repair, and the repair is a date scope or a
    present-tense correction (D-405: a fault that names no remedy is prose)."""
    start = history_start(lines)
    if start >= len(lines):
        return []
    vocab = {s for s in states.values() if s}
    problems: list[str] = []
    for i in range(start, len(lines)):
        line = lines[i]
        n = i + 1
        own_date = first_date(line)
        if LIVE_LABEL_RE.search(line):
            problems.append(
                f"{path.name}:{n} carries the live-claim label in the history region - the DERIVED index above "
                f"the marker is the one place that points at the current state (D-2642): relabel it a snapshot")
        if LIVE_CENSUS_RE.search(line):
            problems.append(
                f"{path.name}:{n} states the LIVE census inside a region declared 'NOT a register': name the "
                f"moment on the marker line so it is a dated snapshot, or leave the number to the derived block")
        if HIGHEST_OPEN_RE.search(line) and not (own_date or MOMENT_TOKEN_RE.search(line)):
            problems.append(
                f"{path.name}:{n} states which bug is highest-OPEN with no moment: that field has ONE home (the "
                f"derived block). Date-scope it ('highest OPEN then ...') or leave it to the derived block")
        m = DEC_ROW_RE.match(line)
        if m and not own_date and not section_date(lines, i, start):
            key = canon_decision_id(m.group(1))
            cells = [c.strip() for c in line.strip().strip("|").split("|")][1:]
            claim = claimed_state(cells, vocab)
            if key not in states:
                problems.append(
                    f"{path.name}:{n} names {m.group(1)} which config/decisions.yaml does not carry - a citation "
                    f"whose subject is absent is an assertion (D-405): correct it to the id that carries the "
                    f"decision, or date-scope the row so it is history")
            elif claim is not None and claim != states[key]:
                problems.append(
                    f"{path.name}:{n} claims {m.group(1)} is {claim} but the register says {states[key]} - "
                    f"date-scope the row (name its moment) or correct it (D-2660)")
        a = OPEN_ASSERT_RE.search(line)
        if a and not entry_date(lines, i, start):
            bid = int(a.group(1) or a.group(2))
            if bid not in known_bugs:
                problems.append(f"{path.name}:{n} asserts BUG-{bid} is OPEN but the register does not carry that "
                                f"id: correct the citation, or date-scope the claim so it is history")
            elif bid in closed_bugs:
                problems.append(f"{path.name}:{n} asserts BUG-{bid} is OPEN but the register says CLOSED - "
                                f"date-scope the claim or correct it")
    return problems


def _selftest_history_faults() -> list[tuple[str, bool]]:
    """Known-answer controls for D-2984, in BOTH directions: every limb fires on a claim that contradicts the
    register and stays quiet on the same claim once it declares its moment (BUG-492: a detector nobody has
    seen fail is not a detector; a detector nobody has seen stay quiet is not one either)."""
    states = {"D1": "ACTIVE", "D2": "RESOLVED", "D3": "RESOLVED"}
    closed_bugs, known_bugs = {539, 631}, {539, 631, 700}
    marker = "<!-- GOV-HISTORY:START (D-2981) -->"

    def faults(body: list[str]) -> list[str]:
        return history_faults(Path("FACE.md"), [marker] + body, states, closed_bugs, known_bugs)

    return [
        ("a live-claim LABEL in the history region must fire",
         len(faults(["> **CURRENT OPEN INDEX (the live face).**"])) == 1),
        ("the same words ABOVE the marker are not a history claim",
         len(history_faults(Path("FACE.md"), ["> the live face", marker], states, closed_bugs, known_bugs)) == 0),
        ("a decision row that disagrees with the register must fire",
         len(faults(["| D2 | ACTIVE | something |"])) == 1),
        ("a decision row that agrees makes no problem",
         len(faults(["| D2 | RESOLVED | something |"])) == 0),
        ("a 4-column transition row is read by its LAST state cell (so it agrees)",
         len(faults(["| D3 | PROPOSED | RESOLVED | the ship |"])) == 0),
        ("a decision row under a DATED section heading is history, not a claim",
         len(faults(["## 2026-10-03 - the flips", "| D2 | ACTIVE | something |"])) == 0),
        ("a decision row naming an id the register does not carry must fire",
         len(faults(["| D9 | ACTIVE | something |"])) == 1),
        # BUG-760 verification pass: the row SHAPES the first version of this rule could not SEE.
        ("a row whose id cell carries MARKDOWN EMPHASIS is still a claim",
         len(faults(["| **D2** | **ACTIVE** | something |"])) == 1),
        ("a row whose id cell carries a LABEL SUFFIX is still a claim",
         len(faults(["| D2 practicality filter | ACTIVE | something |"])) == 1),
        ("a row whose first cell is a BUG id is not a decision claim",
         len(faults(["| BUG-625 | RESOLVED | the D2 follow-on |"])) == 0),
        ("asserting a CLOSED bug is OPEN must fire",
         len(faults(["BUG-539 still OPEN."])) == 1),
        ("the same assertion inside a DATED entry is history",
         len(faults(["## 2026-09-26 - carried", "BUG-539 still OPEN."])) == 0),
        ("naming a closed bug BESIDE a claim about another one must NOT fire",
         len(faults(["BUG-700 is OPEN; BUG-539 was the same class."])) == 0),
        ("a live census marker standing in the history region must fire",
         len(faults(["Register truth: 1111 decisions / 523 bugs (184 open / 339 closed)."])) == 1),
        ("a line that merely DISCUSSES the live label must NOT fire",
         len(faults(["Gap 1 - the MTR 'CURRENT OPEN INDEX' (the machine-derived live face) sits in a section."]))
         == 0),
        ("the highest-OPEN field with no moment must fire",
         len(faults(["Registry unchanged: highest OPEN BUG-750."])) == 1),
        ("the highest-OPEN field carrying its moment is history",
         len(faults(["The register then stood at 460 bugs (163 open, highest OPEN then BUG-695)."])) == 0),
    ]


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
        # D-2984: the claim-surface controls (both directions) - unpacked so each is a NAMED known answer.
        *_selftest_history_faults(),
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
    states = load_decision_states()
    closed = bug_closed_set(bug)
    known = bug_known_ids(bug)
    open_ids = known - closed
    problems: list[str] = []
    for face in FACES:
        if not face.exists():
            problems.append(f"{face.name}: missing face (cannot check what is not there)")
            continue
        face_lines = face.read_text(encoding="utf-8").splitlines()
        problems.extend(check_bug_rows(face, closed, known))
        problems.extend(check_header_census(face, bug, dec))
        problems.extend(check_live_census(face, bug, dec))
        problems.extend(history_faults(face, face_lines, states, closed, known))
    if BUGLOG_FACE.exists():
        problems.extend(check_buglog_tiers(BUGLOG_FACE, open_ids, known))
        problems.extend(history_faults(BUGLOG_FACE, BUGLOG_FACE.read_text(encoding="utf-8").splitlines(),
                                       states, closed, known))
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
