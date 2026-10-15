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
  (6) the LIVE region ABOVE the marker (D-2985, BUG-762): the label that points at the current state, a file a
      live claim names, and the OWNER LANE the register's own task axes require the face to LEAD with.
  (7) the HEADINGS between the two regions (D-2986, BUG-761): a heading that LEADS with a tier/state token is an
      INDEX heading, and below the marker it must declare WHAT IT IS - a HAND INDEX, row-joined and never the
      authority - and may not carry a count (a count has ONE home, BUG-588/D-2642). MEASURED 2026-10-13: twelve
      such headings sat inside the region every face declares "NOT a register" while claiming a current state,
      two of them restating a count that had drifted (477 against 565 ACTIVE; 97 against 348 closed).

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
    r"^\s*(?:#{1,6}\s*)?(?:>\s*)*(?:[*_`]{0,2}\s*)*(?:[^\w\s]{1,3}\s*)*"
    r"(?:CURRENT\s+OPEN\s*(?:/\s*PENDING)?\s*INDEX|the\s+live\s+face)\b",
    re.IGNORECASE,
)
#: MEASURED 2026-10-13 (D-2985), the day AFTER this rule first landed: the pattern above was blind to a label
#: behind a heading marker. DECISION-LOG.md:12 read `## 🔴 CURRENT OPEN / PENDING INDEX (machine-derived
#: 2026-10-03 — the live face; history below)` - a HAND heading, dated ten days earlier, calling itself
#: machine-derived and the live face, sitting two lines above the block that claimed the same title. The
#: first version of this limb required the label to LEAD the line and so could not see the ONE instance the
#: owner opens the file on. The label may now carry a heading marker, quote markers, emphasis and an icon -
#: and it must still LEAD the line, which is what keeps the prose that DISCUSSES a pointer (buglog.md's
#: BUG-669 entry) from firing.
#: The highest-open bug is a DERIVED value: ONE home (the derived block), D-2642. A hand line may state it only
#: as a claim about a moment (D-2660) - which is how "highest OPEN then BUG-695" stays true while the
#: register moves on. MEASURED 2026-10-13: MASTER-TASK-REGISTER.md:61 said "highest OPEN = BUG-750" with no
#: moment at all, while the register's own answer was BUG-757.
HIGHEST_OPEN_RE = re.compile(r"highest\s+OPEN\b", re.IGNORECASE)
#: A moment named IN WORDS rather than as a date. The field above must carry one on its OWN line - an entry
#: stamp one line up is not enough for a DERIVED value, because the value is the thing that moved.
MOMENT_TOKEN_RE = re.compile(r"\b(then|as\s+of|at\s+the\s+time|that\s+date)\b", re.IGNORECASE)
DEC_ROW_RE = re.compile(r"^\|\s*[*_`'\"]*\s*(D-?[0-9]+[a-z]?)\b")#: MEASURED 2026-10-13, AFTER the first version of this rule landed (the D-2984 verification pass): the row
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

# ------------------------------------------------ D-2985: the LIVE region is a claim surface too
# D-2984 policed everything BELOW the history marker. MEASURED 2026-10-13: the region ABOVE it - the one the
# owner actually opens - was unpoliced, and it was wrong in three ways at once. DECISION-LOG.md:12 read
# `## 🔴 CURRENT OPEN / PENDING INDEX (machine-derived 2026-10-03 - the live face; history below)`: a HAND
# heading, ten days stale, claiming to BE the live index while the derived block below claimed the same title.
# A file a live claim names had no checker (config/task_register.yaml cited scripts/check_gov_sync.py, which
# does not exist - the D-405 class, the same class as BUG-761's dangling D2537). And no face declared WHO must
# move the work, so the top of every face led with a standing rule and two owner-gated tasks rendered as
# "MUST ... open". Three claims, three joins, one sentence: the LIVE region is a claim surface too.
GOV_SYNC_CFG = REPO / "config" / "gov_sync.yaml"
#: BUG-839 - A CITATION IS NOT A PATH SEGMENT. \b matched INSIDE a home-relative path, so the citation
#: "~/.config/goose/config.yaml:311" yielded the repo-relative path "config/goose/config.yaml" and this rail
#: reported a D-405 fault against a claim the face never made - the subject is a HARNESS HOME that exists, and
#: the segment after the dot is not a statement about this repository (T-157). The prefix must therefore START a
#: token: it may not be preceded by a path character, so ".config/..." is not a citation while "config/..." at a
#: line start, after a space, after "(" or after a quote still is.
LIVE_PATH_RE = re.compile(
    r"(?<![\w./~-])((?:scripts|pipeline|config|governance|specs|tests|agent|lib)/[A-Za-z0-9_./-]+\.(?:py|yaml|yml|md|json))\b")


def gov_sync_config() -> dict:
    """The owner-lane label, the task axes and the heading rule - ONE home (config/gov_sync.yaml), never a
    literal here (C12)."""
    doc = yaml.safe_load(GOV_SYNC_CFG.read_text(encoding="utf-8")) or {}
    for key in ("face_owner_lane_label", "task_movers", "face_index_head_tokens", "face_hand_index_token",
                "face_head_declaration_re", "state_glyphs"):
        if key not in doc:
            raise SystemExit(f"FAIL-CLOSED (C16): {GOV_SYNC_CFG.name} declares no {key!r} (D-2985/D-2986/D-2987)")
    return doc


def owner_moved_count() -> int:
    """How many live tasks the register says only the OWNER can move (config/task_register.yaml)."""
    reg = yaml.safe_load((REPO / "config" / "task_register.yaml").read_text(encoding="utf-8")) or {}
    return sum(1 for t in (reg.get("tasks") or [])
               if str(t.get("state")) not in ("done", "superseded", "rule") and t.get("mover") == "owner")


def live_faults(path: Path, lines: list[str], cfg_d: dict, owner_moved: int) -> list[str]:
    """D-2985: the LIVE region (above the history marker) is a claim surface. Three limbs, each with its repair:
    (1) a hand line may not claim to BE the live index - the label has one home;
    (2) a file a live claim NAMES must exist (D-405: a citation whose subject is absent is an assertion);
    (3) when the register declares owner-moved work, the face LEADS with the owner lane.
    """
    end = history_start(lines)
    label = str(cfg_d["face_owner_lane_label"])
    lane = re.compile(rf"^>\s*(?:[*_`]*\s*)*\*\*{re.escape(label)}\b")
    problems: list[str] = []
    if owner_moved and not any(lane.search(ln) for ln in lines[:end]):
        problems.append(f"{path.name}: config/task_register.yaml declares {owner_moved} OWNER-moved task(s) and "
                        f"this face carries no '{label}' row: a face that does not say what only the OWNER can "
                        f"move cannot be acted on by anyone (D-2985) - relabel the lane, or run "
                        f"scripts/gov_sync.py --apply")
    for i, line in enumerate(lines[:end]):
        n = i + 1
        if LIVE_LABEL_RE.search(line):
            problems.append(f"{path.name}:{n} claims to BE the live index. The label has ONE home - the derived "
                            f"block above the history marker (D-2642): relabel this line a tier heading, or "
                            f"date-scope it so it reads as a snapshot")
        for m in LIVE_PATH_RE.finditer(line):
            rel = m.group(1)
            if not (REPO / rel).exists():
                problems.append(f"{path.name}:{n} cites {rel}, which does not exist - a citation whose subject is "
                                f"absent is an assertion (D-405): cite the file that runs, or drop the citation")
    return problems


# ------------------------------------------------ D-2986: a HEADING is a claim
# D-2984 policed the ROWS and the prose of the declared history region; D-2985 policed the LIVE region above
# the marker. MEASURED 2026-10-13 (BUG-761 - the residual both acts deliberately left, because a fix had to
# come with a join for the tier LABELS or not at all): the HEADINGS between the two regions were policed by
# nothing. Twelve of them sat below the marker claiming a CURRENT state inside a region the face declares
# "NOT a register", and two restated a count that had drifted:
#   DECISION-LOG.md:241  `## 🟢 ACTIVE — in effect (477)`   vs 565 ACTIVE in config/decisions.yaml
#   DECISION-LOG.md:295  `## ⚪ DONE / CLOSED — bottom (97)` vs 348 closed (resolved 313 + superseded 16 +
#                                                            archived 8 + rejected 11)
# A count restated in prose is stale the moment it is written (BUG-588); a count has ONE home, the derived
# block (D-2642). The shape that discriminates an INDEX heading from a RECORD heading is the LEADING token:
# `## 🔴 OPEN — MUST` and `## 🟢 ACTIVE` are heading-then-rows indexes, while `## BUG-331 (MED, OPEN)` leads with
# the ID and is the register's own status slot (scripts/bug_status.py's surface). MEASURED the same day: a
# word-ANYWHERE form of this rule fires on 399 record headings in buglog.md, so the rule reads the leading token
# ONLY. What the heading owes when it leads with one: it must SAY what it is - a HAND INDEX, non-authoritative -
# because the owner navigates by these sections and a heading that models the register without being joined to
# it is the thing this file exists to refuse.
HEAD_COUNT_RE = re.compile(r"\(\s*\d[\d,]*\s*\)")


def heading_faults(path: Path, lines: list[str], cfg_d: dict) -> list[str]:
    """D-2986: the HEADINGS below the marker. An INDEX heading (one that LEADS with a declared tier/state token
    after any icon/emphasis) must (1) carry the declared HAND INDEX token - it is not the authority for the
    current state, and it says so - and (2) carry no count, because a count has ONE home (BUG-588/D-2642).
    Two limbs, each with its repair; nothing is deleted, because the rows below such a heading are already
    joined (D-2984's decision-row join, scripts/bug_status.py's record headings, check_buglog_tiers)."""
    start = history_start(lines)
    tokens = [str(t) for t in cfg_d["face_index_head_tokens"]]
    token = str(cfg_d["face_hand_index_token"])
    declare = re.compile(str(cfg_d["face_head_declaration_re"]), re.IGNORECASE)
    head = re.compile(r"^\s*#{1,6}\s*(?:[^\w\s]{1,3}\s*)*(?:[*_`]{0,2}\s*)*"
                      r"(?:" + "|".join(re.escape(t) for t in tokens) + r")\b", re.IGNORECASE)
    problems: list[str] = []
    for i in range(start, len(lines)):
        line = lines[i]
        if not head.match(line):
            continue
        n = i + 1
        if not declare.search(line):
            problems.append(
                f"{path.name}:{n} is an INDEX heading naming a current state inside the region this face "
                f"declares makes no live claim: declare it a {token} - non-authoritative, row-joined, with the "
                f"DERIVED block above as the ONE authority for the current state (D-2986)")
        m = HEAD_COUNT_RE.search(line)
        if m:
            problems.append(
                f"{path.name}:{n} restates the count {m.group(0)} in a heading - a count has ONE home, the "
                f"derived block above (BUG-588/D-2642): drop it from the label (D-2986)")
    return problems


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


#: D-2987: the states the DERIVED block renders UNCONDITIONALLY - each is printed on EVERY run,
#: whatever the register holds (the open-state keys, the four severities, and the five settled states on the
#: decisions summary line). So the sign for each must be PRESENT in the block: a map that is declared and never
#: rendered is a declaration with no reader (BUG-492).
#: D-2987 (BUG-765): the four DECLARED decision-state buckets. Their union must EQUAL the states the census
#: counts and they must be pairwise disjoint - that is the whole invariant, and it is what the defect violated.
DECISION_BUCKET_KEYS = ("open_decision_states", "decision_in_effect_states", "decision_closed_states",
                        "decision_void_states")


def glyph_faults(d: dict, path: Path | None = None) -> list[str]:
    """D-2987: every DECLARED state carries a sign, and the AUTHORITY renders it.

    MEASURED 2026-10-13: the DERIVED block - the ONE authority (D-2981/D-2985) - printed every state as a bare
    lowercase word, while the hand INDEXES below the marker, which D-2986 declares make NO live claim, led with
    the tier icons. The colour sat on the region that claims NOTHING and was absent from the region that OWNS
    the state, so an owner scanning by sign was reading the non-authoritative index. That is BUG-761's defect
    one layer down: a surface that misleads about its own authority.

    Two limbs, both joinable:
      (1) COMPLETENESS - every token declared on any axis (the task states, the task priorities, the severity
          tokens, the open decision states, and the states the census counts) must carry a sign. A NEW state
          therefore cannot be added to any axis without giving it one, which is the whole point: a state the
          owner cannot scan for is a state the face does not show.
      (2) PRESENCE - the block must actually RENDER the sign beside the word, for every state it prints on
          every run. A map nothing reads is a comment (BUG-492). The pair (sign + WORD) is checked, not the
          sign alone, because two settled states deliberately share a sign.

    PURE when `path` is None (completeness only), so the oracle is testable without touching a face. The
    required tokens come from the DECLARED axes (config/gov_sync.yaml), never from whatever the census happens
    to count: MEASURED 2026-10-13, the first version of this limb read the census's `summary` keys and so
    demanded signs for `total` and `by_category` - a fault of the RULE, not of the map (the D-2986 lesson).
    """
    gl = d.get("state_glyphs")
    if not isinstance(gl, dict) or not gl:
        return [f"{GOV_SYNC_CFG.name} declares no state_glyphs - every declared state must carry a sign "
                f"(D-2987)"]
    required = (set(d["task_states"]) | set(d["task_priorities"]) | set(d["severity_tokens"])
                | set().union(*(set(d.get(k) or []) for k in DECISION_BUCKET_KEYS)))
    out = [f"{GOV_SYNC_CFG.name} declares the state {w!r} on an axis but state_glyphs gives it NO sign - a "
           f"state the owner cannot scan for is a state the face does not show (D-2987)"
           for w in sorted(w for w in required if w not in gl)]
    if path is None:
        return out
    lines = path.read_text(encoding="utf-8").splitlines()
    block = "\n".join(lines[:history_start(lines)])
    summary = (json.loads(DECISIONS_SUMMARY.read_text(encoding="utf-8")).get("summary") or {})
    # DECISIONS: every declared state the register ACTUALLY COUNTS must render its sign. A zero-valued state
    # is suppressed by the renderer (C28 - the face is a VIEW), so the required set is the JOIN of the
    # declared axis with the census, not a static list that would red spuriously the day a state hits 0.
    present = {s for k in DECISION_BUCKET_KEYS for s in (d.get(k) or []) if int(summary.get(s) or 0)}
    # BUGS: all four severities are rendered unconditionally, so all four are required unconditionally.
    present |= set(d["severity_tokens"])
    for word in sorted(present):
        g = str(gl.get(word, ""))
        if g and f"{g} {word}" not in block:
            out.append(f"{path.name}: the DERIVED block does not render the sign {g!r} beside the state "
                       f"{word!r} the register counts - a declared sign nothing renders is a comment (D-2987)")
    return out


def partition_faults(d: dict, census: dict | None = None) -> list[str]:
    """D-2987 (BUG-765): the DECLARED decision-state buckets must PARTITION the states the register counts.

    MEASURED 2026-10-13, by the first run of the sign limb: the DERIVED decisions line summed to 981 of 1114.
    The 133 decisions it never accounted for were exactly those in state `ratified` - a state no file under
    governance declared, printed or signed - so 12% of the register was invisible in the ONE authority, on a
    line that printed its own total two words earlier. A state with no sign is a state the face does not show
    (BUG-757's shape, on the decisions axis).

    Two limbs: (1) the buckets are pairwise DISJOINT - a state in two buckets is counted twice by whoever reads
    either; (2) their union EQUALS the census's state keys - a state the census counts that no bucket holds is
    a state the authority does not account for. With a complete partition the rendered counts are exact BY
    CONSTRUCTION, which is why the invariant is the PARTITION and not a separate sum comparison.
    """
    if census is None:
        census = json.loads(DECISIONS_SUMMARY.read_text(encoding="utf-8"))
    summary = census.get("summary") or {}
    groups = {k: [str(s) for s in (d.get(k) or [])] for k in DECISION_BUCKET_KEYS}
    out = [f"{GOV_SYNC_CFG.name} declares no {k} - the decision-state axis must be a DECLARED partition, not "
           f"whatever the census happens to count (D-2987)"
           for k in DECISION_BUCKET_KEYS if not groups[k]]
    seen: dict[str, str] = {}
    for k in DECISION_BUCKET_KEYS:
        for s in groups[k]:
            if s in seen:
                out.append(f"the decision state {s!r} sits in BOTH {seen[s]!r} and {k!r} - a partition "
                           f"requires exactly ONE bucket per state (D-2987)")
            seen[s] = k
    counted = {str(k) for k in summary if k not in ("total", "total_decisions", "by_category")}
    missing = sorted(counted - set(seen))
    extra = sorted(set(seen) - counted)
    if missing:
        n = sum(int(summary.get(k) or 0) for k in missing)
        out.append(f"the census counts the state(s) {missing} ({n} decision(s)) but NO declared bucket holds "
                   f"them - a state the authority does not account for is a state the face does not show "
                   f"(D-2987/BUG-765)")
    if extra:
        out.append(f"the declared buckets hold {extra}, which the census does not count - either the state is "
                   f"not real or the census is stale (D-2987)")
    return out


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


def _selftest_live_region(cfg_d: dict) -> list[tuple[str, bool]]:
    """D-2985: the LIVE region's three limbs, in BOTH directions (BUG-492)."""
    def faults(body: list[str], owner: int = 0) -> list[str]:
        return live_faults(Path("FACE.md"), body, cfg_d, owner)

    lane = "> **OWNER LANE (1) — what ONLY YOU can move:**"
    return [
        ("a HAND HEADING that claims to be the live index must fire (the shape the first rule was blind to)",
         len(faults(["## 🔴 CURRENT OPEN / PENDING INDEX (machine-derived 2026-10-03 — the live face)."])) == 1),
        ("the same words in a line that DISCUSSES the faces must not fire",
         len(faults(["Gap 1 — the MTR 'CURRENT OPEN INDEX' (the machine-derived live face) sits in a section."])) == 0),
        ("a live claim may not name a file that does not exist",
         len(faults(["see scripts/no_such_rail.py for the join"])) == 1),
        ("a live claim naming a file that EXISTS makes no problem",
         len(faults(["see config/gov_sync.yaml for the join"])) == 0),
        # BUG-839: a HOME-RELATIVE path is not a repo citation. The first version matched the segment after the
        # dot and faulted a harness home that exists (T-157's row in the live region).
        ("a home-relative citation makes no problem, because it claims nothing about this repo",
         len(faults(["MEASURED 2026-10-15: ~/.config/goose/config.yaml:311 reads active_provider: custom_deepseek"])) == 0),
        ("a genuinely dangling repo citation still fires BESIDE the same home path (the fix must not blind the rule)",
         len(faults(["~/.config/goose/config.yaml:311 and scripts/no_such_rail.py"])) == 1),
        ("owner-moved work with no owner lane in the face must fire",
         len(faults(["the face says nothing about who moves what"], owner=2)) == 1),
        ("the same face carrying the owner lane makes no problem",
         len(faults([lane], owner=2)) == 0),
    ]


def _selftest_heading_claims(cfg_d: dict) -> list[tuple[str, bool]]:
    """D-2986: the INDEX heading's two requirements, in BOTH directions (BUG-492)."""
    marker = "<!-- GOV-HISTORY:START (D-2981/D-2986) -->"
    ok = "## 🔴 OPEN — MUST (data integrity) — HAND INDEX (not a register; the DERIVED block above owns it)"

    def faults(body: list[str]) -> list[str]:
        return heading_faults(Path("FACE.md"), [marker] + body, cfg_d)

    return [
        ("an INDEX heading that names a current state and declares nothing must fire",
         len(faults(["## 🔴 OPEN — MUST (data integrity / correctness / safety)"])) == 1),
        ("the same heading declaring itself a HAND INDEX makes no problem",
         len(faults([ok])) == 0),
        ("an INDEX heading restating a COUNT must fire (a count has one home)",
         len(faults(["## 🟢 ACTIVE — in effect (477) — HAND INDEX"])) == 1),
        ("the count-free form of that heading makes no problem",
         len(faults(["## 🟢 ACTIVE — in effect — HAND INDEX"])) == 0),
        ("the D-2984 SNAPSHOT form already declares the authority, so it stays quiet",
         len(faults(["### Pending from registry (SNAPSHOT 2026-10-03 — dated history; the DERIVED index at the "
                     "top owns the current state, D-2984)"])) == 0),
        ("a per-bug RECORD heading is the register's own status slot, not an index heading",
         len(faults(["## BUG-331 — Serving-gate write to the production DB (MED, OPEN)"])) == 0),
        ("a tier heading ABOVE the marker is the live tier heading, not a history claim",
         len(heading_faults(Path("FACE.md"), ["## 🔴 OPEN — MUST", marker], cfg_d)) == 0),
    ]


def _selftest_state_signs(cfg_d: dict) -> list[tuple[str, bool]]:
    """D-2987, BOTH directions: the real map must be COMPLETE, a state with no sign must fire, and a face whose
    derived block renders no sign must fire. A rule whose control has never been seen to fail is not a control
    (BUG-492)."""
    real = glyph_faults(cfg_d)
    hole = {k: v for k, v in (cfg_d.get("state_glyphs") or {}).items() if k != "MED"}
    broke = glyph_faults({**cfg_d, "state_glyphs": hole})
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "FACE.md"
        p.write_text("a face with no derived block at all\n", encoding="utf-8")
        silent = glyph_faults(cfg_d, p)
    # D-2987/BUG-765: the PARTITION, measured on the real census AND on the exact shape of the defect that
    # was found - a state the census counts that no bucket holds (the 133 `ratified` decisions).
    real_part = partition_faults(cfg_d)
    orphan = partition_faults(cfg_d, {"summary": {"total": 100, "open": 60, "active": 30, "quiesced": 10}})
    doubled = partition_faults({**cfg_d, "decision_void_states": ["stale", "revoked", "abandoned", "open"]})
    return [
        ("the REAL state_glyphs map covers every declared state (D-2987)", real == []),
        ("a declared state with NO sign must fire (D-2987)", any("'MED'" in f for f in broke)),
        ("a face whose DERIVED block renders no sign must fire (D-2987)",
         any("does not render the sign" in f for f in silent)),
        ("the REAL decision-state buckets PARTITION the census (D-2987/BUG-765)", real_part == []),
        ("a state the census counts that NO bucket holds must fire (the BUG-765 shape)",
         any("NO declared bucket holds" in f for f in orphan)),
        ("a state sitting in TWO buckets must fire (D-2987)",
         any("BOTH" in f for f in doubled)),
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
        # D-2985: the LIVE region (above the marker) - the surface the owner actually opens.
        *_selftest_live_region(gov_sync_config()),
        # D-2986: the HEADINGS between the two regions - the surface that named a state with nothing joining it.
        *_selftest_heading_claims(gov_sync_config()),
        # D-2987: every declared state CARRIES A SIGN, and the authority renders it.
        *_selftest_state_signs(gov_sync_config()),
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
    sync_cfg = gov_sync_config()
    owner_moved = owner_moved_count()
    problems: list[str] = list(partition_faults(sync_cfg))
    for face in FACES:
        if not face.exists():
            problems.append(f"{face.name}: missing face (cannot check what is not there)")
            continue
        face_lines = face.read_text(encoding="utf-8").splitlines()
        problems.extend(check_bug_rows(face, closed, known))
        problems.extend(check_header_census(face, bug, dec))
        problems.extend(check_live_census(face, bug, dec))
        problems.extend(history_faults(face, face_lines, states, closed, known))
        problems.extend(live_faults(face, face_lines, sync_cfg, owner_moved))
        problems.extend(heading_faults(face, face_lines, sync_cfg))
        problems.extend(glyph_faults(sync_cfg, face))
    if BUGLOG_FACE.exists():
        problems.extend(check_buglog_tiers(BUGLOG_FACE, open_ids, known))
        blog_lines = BUGLOG_FACE.read_text(encoding="utf-8").splitlines()
        problems.extend(history_faults(BUGLOG_FACE, blog_lines, states, closed, known))
        problems.extend(live_faults(BUGLOG_FACE, blog_lines, sync_cfg, owner_moved))
        problems.extend(heading_faults(BUGLOG_FACE, blog_lines, sync_cfg))
        problems.extend(glyph_faults(sync_cfg, BUGLOG_FACE))
    else:
        problems.append(f"{BUGLOG_FACE.name}: missing face (cannot check what is not there)")
    if problems:
        print("FAIL governance-faces: " + str(len(problems)) + " face(s) contradict the register:")
        for p in problems:
            print("  " + p)
        return 1
    print("ok governance-faces: bug-status table rows, header/live census, the history claim surface, the "
          "LIVE region, the INDEX headings and the STATE SIGNS agree with the register (" + str(len(FACES)) + " restatement "
          "face(s) + buglog tiers, " + str(len(known)) + " bug ids, " + str(owner_moved) + " owner-moved task(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
