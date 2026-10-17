#!/usr/bin/env python3
"""check_freeze_window.py - A FREEZE IS A WINDOW, AND A WINDOW ENDS BY ITS OWN TERMS (D-2688).

WHY (the class, not the instance). A freeze is the one governance act that takes effect by being BELIEVED: it
is pure prose by construction. MEASURED 2026-09-27, the META-LANE FREEZE was asserted in fifteen places and
existed in no file a machine could read, so it failed three ways at once:
  (i)   NOTHING READ IT    - "held behind the freeze" is a claim about work NOT done, and a claim about an
        absence can never fail (BUG-492, one level up);
  (ii)  IT HAD NO EXIT     - an unwritten exit makes a WINDOW indistinguishable from a POLICY, and a policy has
        no horizon: it outlives the reason it was opened for (the D-337 permanent-freeze trap);
  (iii) IT COUNTED NOTHING - the parked set could grow for ever, so "we are frozen" and "we are stuck" printed
        the same way.
The ONE home is config/freeze_window.yaml; this is the ONE reader. It settles what a machine can settle: is the
declared EXIT met, has the declared HORIZON passed, is every parked id REAL, and has the parked set outgrown
its declared ceiling. It does not decide policy - it reports whether the window can still END.

Exit: 0 the window is OPEN, its exit UNMET and it is inside its horizon (the normal state) - or it is CLOSED
        and its exit is MET (the ended state; a closed window whose exit is UNMET is a FAULT, clause (f))
      1 a fault - a parked id the register does not carry, a set past its ceiling, a malformed declaration
      2 OWNER-OWED, loud, NOT fatal (BUG-457): the EXIT IS MET (close it), or the HORIZON PASSED with the exit
        unmet (re-rule it) - renewing by default is how a window becomes a policy
--selftest: known-answer controls over SYNTHETIC windows and a synthetic register (no I/O, BUG-492).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
CFG = REPO / "config/freeze_window.yaml"
REGISTER = REPO / "governance/bug_status.json"
#: Each criterion NAMES its subject, and a reader must be able to SEE which key that is. `opening_set_closed` carries
#: its ids in `bugs`; `nothing_still_held` carries NO key of its own because its subject is window.held BY CONSTRUCTION
#: (there it already has to exist in the register, not be doubled, and be inside max_held).
VALID_CLAUSES = {"opening_set_closed": "bugs", "nothing_still_held": None}
#: The reader's INPUT CONTRACT. A human edits config/freeze_window.yaml, so a typo must be a NAMED FAULT, never a
#: traceback: a reader that crashes says NOTHING about the window, and C16 says fail CLOSED, not fail UGLY.
SHAPE = {"held": list, "not_frozen": list, "exceptions_spent": list, "released": dict, "exit": dict}
REQUIRED = ("id", "state", "opened", "scope", "held", "exit")


def open_ids(register: dict) -> set[str]:
    """The ids the register carries as OPEN.

    Read from the DERIVED register, never re-parsed from the log: "which bugs are open" already has ONE home
    (scripts/bug_status.py) and scripts/check_bug_status.py certifies it, so a second parser here would be the
    D-2646 two-homes defect.
    """
    return {str(x.get("id") if isinstance(x, dict) else x) for x in (register.get("open") or [])}


def carried_ids(register: dict) -> set[str]:
    """Every id the register carries, OPEN or CLOSED: a parked id must EXIST, not necessarily still be open."""
    out = open_ids(register)
    out |= {str(x.get("id") if isinstance(x, dict) else x) for x in (register.get("closed") or [])}
    return out


def exit_state(win: dict, open_now: set[str]) -> tuple[list[str], list[str]]:
    """PURE (ONE reader): which DECLARED exit clauses are MET and which are not.

    The clause ids are the declared ids, so every verdict names a clause a human can go and read. A released id
    is no longer parked: a ruling recorded in the ONE home is what drains the window.
    """
    met: list[str] = []
    unmet: list[str] = []
    released = {str(k) for k in (win.get("released") or {})}
    held = [str(x) for x in (win.get("held") or [])]
    for c in ((win.get("exit") or {}).get("criteria") or []):
        cid = str(c.get("id") or "")
        if cid == "opening_set_closed":
            bugs = [str(b) for b in (c.get("bugs") or [])]
            still = [b for b in bugs if b in open_now]
            if bugs and not still:
                met.append(cid)
            else:
                unmet.append(cid + " (" + str(len(still)) + " still open: " + ", ".join(still) + ")")
        elif cid == "nothing_still_held":
            held_open = [b for b in held if b in open_now and b not in released]
            if not held_open:
                met.append(cid)
            else:
                unmet.append(cid + " (" + str(len(held_open)) + " still parked)")
        else:
            unmet.append(cid + " (no reader can settle this criterion id)")
    return met, unmet


def parse_date(value: object) -> dt.date | None:
    """A horizon is a DATE or it is not a horizon."""
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError:
        return None


def shape_faults(win: object) -> list[str]:
    """PURE (ONE reader): the declaration's OWN SHAPE, settled before a byte of it is read (C16)."""
    if not isinstance(win, dict):
        return ["(a) config/freeze_window.yaml#window is " + type(win).__name__ + ", not a mapping - a window a reader "
                "cannot open cannot end (D-2688)"]
    faults: list[str] = []
    for key, want in SHAPE.items():
        got = win.get(key)
        if got is not None and not isinstance(got, want):
            faults.append("(a) window." + key + " is " + type(got).__name__ + ", not " + want.__name__
                          + ": the reader cannot read the declaration it was given (C16)")
    exitd = win.get("exit")
    if isinstance(exitd, dict):
        criteria = exitd.get("criteria")
        if criteria is not None and not isinstance(criteria, list):
            faults.append("(a) window.exit.criteria is " + type(criteria).__name__ + ", not a list: a clause a reader "
                          "cannot enumerate cannot be MET")
        elif isinstance(criteria, list):
            for c in criteria:
                if not isinstance(c, dict):
                    faults.append("(a) an exit criterion is " + type(c).__name__ + ", not a mapping: a clause a reader "
                                  "cannot open cannot be MET")
    return faults


def window_faults(win: dict, carried: set[str], open_now: set[str], today: dt.date) -> list[str]:
    """PURE (ONE reader): is the declaration complete enough to be READ, and is every subject REAL (C16)?"""
    if not win:
        return ["(a) config/freeze_window.yaml declares no 'window:' - a freeze that names no window can only be believed (D-2688)"]
    faults: list[str] = shape_faults(win)
    if faults:
        return faults
    for key in REQUIRED:
        if key not in win:
            faults.append("(a) the window declares no '" + key + "': a window that cannot be read cannot end (D-2688)")
    if faults:
        return faults
    state = str(win.get("state") or "")
    if state not in ("open", "closed"):
        faults.append("(a) window.state is " + repr(state) + ", not one of open|closed")
    opened = parse_date(win.get("opened"))
    exitd = win.get("exit") or {}
    review_by = parse_date(exitd.get("review_by"))
    if opened is None:
        faults.append("(a) window.opened is not a date: a window with no opening has no age")
    if review_by is None:
        faults.append("(a) window.exit.review_by is not a date - a WINDOW has a horizon and a POLICY does not (D-337)")
    if opened and review_by and opened > review_by:
        faults.append("(a) the horizon " + str(review_by) + " precedes the opening " + str(opened) + ": that is not a horizon")
    held = [str(x) for x in (win.get("held") or [])]
    if len(set(held)) != len(held):
        faults.append("(a) window.held names an id TWICE - one fact, one home (D-2646)")
    for bug in held:
        if bug not in carried:
            faults.append("(b) window.held names " + bug + ", which the register does NOT carry: a stale declaration, not a hold (D-405/C19)")
    ceiling = win.get("max_held")
    if not isinstance(ceiling, int):
        faults.append("(a) window.max_held is " + repr(ceiling) + ", not an integer: a parked set with no ceiling can never be said to have grown")
    elif len(held) > ceiling:
        faults.append("(c) the PARKED SET grew to " + str(len(held)) + " past its declared ceiling " + str(ceiling) + ": raise max_held in the SAME change that parks the bug - a set that grows silently is the policy this file removes")
    for bug, reason in (win.get("released") or {}).items():
        if str(bug) not in held:
            faults.append("(d) window.released names " + str(bug) + ", which window.held does NOT: a ruling about nothing (D-405)")
        if not str(reason or "").strip():
            faults.append("(d) window.released[" + str(bug) + "] states no reason: a release an owner did not have to justify is not a ruling")
    criteria = exitd.get("criteria")
    if not criteria:
        faults.append("(a) the window declares NO exit criteria - an exit written nowhere never arrives, and that is what makes a window a policy (D-2688)")
    else:
        for c in criteria:
            cid = str(c.get("id") or "")
            if cid not in VALID_CLAUSES:
                faults.append("(a) the exit declares criterion " + repr(cid) + ", which no reader can settle (known: " + ", ".join(sorted(VALID_CLAUSES)) + ")")
                continue
            key = VALID_CLAUSES[cid]
            extra = sorted(set(c) - {"id", "claim"} - ({key} if key else set()))
            if extra:
                faults.append("(a) the exit criterion " + cid + " carries " + ", ".join(extra) + ", which NO reader "
                              "reads: a subject a reader ignores is an assertion (D-405)")
            if key is None:
                continue
            subjects = c.get(key) or []
            if not subjects:
                faults.append("(a) the exit criterion " + cid + " names no subject: a clause with no subject cannot be MET")
            for bug in subjects:
                if str(bug) not in carried:
                    faults.append("(b) the exit criterion " + cid + " names " + str(bug) + ", which the register does NOT carry (D-405)")
    _, unmet = exit_state(win, open_now)
    if state == "closed" and unmet:
        faults.append("(f) the window declares state: closed while its exit is UNMET (" + "; ".join(unmet) + ") - closing is a claim, and only the MET exit makes it true")
    return faults


def verdict(win: dict, carried: set[str], open_now: set[str], today: dt.date) -> tuple[int, list[str], list[str], list[str]]:
    """(rc, faults, met, unmet). rc 1 = a fault; rc 2 = OWNER-OWED (the exit is MET, or the horizon passed)."""
    faults = window_faults(win, carried, open_now, today)
    if faults:
        return 1, faults, [], []
    met, unmet = exit_state(win, open_now)
    if str(win.get("state")) == "closed":
        return 0, [], met, unmet
    review_by = parse_date((win.get("exit") or {}).get("review_by"))
    stale = bool(review_by) and today >= review_by
    return (2 if (not unmet or stale) else 0), [], met, unmet


def selftest() -> int:
    """Known-answer controls over SYNTHETIC windows and a synthetic register.

    A window that never reports a fault, and an exit that can NEVER be met, are both indistinguishable from a
    policy - which is the defect this rail exists to remove (BUG-492/D-2688).
    """
    ok = fail = 0

    def check(name: str, got: object, want: object, why: str) -> None:
        nonlocal ok, fail
        if got == want:
            ok += 1
            print("  ok   selftest/" + name + ": " + why)
        else:
            fail += 1
            print("  FAIL selftest/" + name + ": " + why + " (got " + repr(got) + ", want " + repr(want) + ")")

    today = dt.date(2026, 9, 27)
    carried = {"BUG-577", "BUG-575", "BUG-571", "BUG-585", "BUG-584"}
    opening = {"BUG-577", "BUG-575", "BUG-571"}     # the bugs the window was OPENED to finish (MEASURED: CLOSED)
    held_open = {"BUG-585", "BUG-584"}              # the REGISTER's open set: the LIVE day-0 shape, not a union of ids
    nothing_open: set[str] = set()                  # the exit-MET world, where every clause is true

    def win(**kw: object) -> dict:
        base: dict = {"id": "W-1", "state": "open", "opened": "2026-09-27", "scope": "fixture",
                      "held": ["BUG-585", "BUG-584"], "max_held": 2, "released": {},
                      "exit": {"criteria": [{"id": "opening_set_closed", "bugs": ["BUG-577", "BUG-575", "BUG-571"]},
                                            {"id": "nothing_still_held"}], "review_by": "2026-10-11"}}
        base.update(kw)
        return base

    rc, f, met, unmet = verdict(win(), carried, held_open, today)
    check("open_window_is_quiet", (rc, len(f), len(met), len(unmet)), (0, 0, 1, 1),
          "an open window with an UNMET exit inside its horizon is the NORMAL state")

    rc, f, _, _ = verdict(win(), carried, nothing_open, today)
    check("exit_is_met_when_every_clause_is_satisfied", rc, 2,
          "every clause true -> OWNER-OWED: the window is due to CLOSE (a window outliving its exit is a policy)")

    rc, f, _, _ = verdict(win(released={"BUG-585": "owner ruling", "BUG-584": "owner ruling"}), carried, held_open, today)
    check("a_released_id_is_no_longer_parked", rc, 2,
          "a ruling recorded in the ONE home drains the parked set, and the exit follows")

    rc, f, _, _ = verdict(win(), carried, held_open, dt.date(2026, 10, 12))
    check("horizon_passed_with_the_exit_unmet", rc, 2,
          "a horizon passed with the exit unmet is OWNER-OWED: re-rule it, never renew by default (D-337)")

    rc, f, _, _ = verdict(win(held=["BUG-585", "BUG-0000"]), carried, opening, today)
    check("parked_id_the_register_does_not_carry", len([x for x in f if "(b)" in x]), 1,
          "a parked id the register does not carry is a STALE declaration, not a hold (D-405)")

    rc, f, _, _ = verdict(win(held=["BUG-585", "BUG-584", "BUG-571"], max_held=2), carried, opening, today)
    check("parked_set_past_its_ceiling", len([x for x in f if "(c)" in x]), 1,
          "a parked set grown past its ceiling is a window turning into a policy without anyone reading it")

    rc, f, _, _ = verdict(win(released={"BUG-572": "not held here"}), carried, held_open, today)
    check("release_about_a_bug_the_window_does_not_hold", len([x for x in f if "(d)" in x]), 1,
          "a ruling about nothing is a stale declaration (D-405)")

    rc, f, _, _ = verdict(win(released={"BUG-585": "   "}), carried, held_open, today)
    check("release_without_a_reason", len([x for x in f if "(d)" in x]), 1,
          "a release an owner did not have to justify is not a ruling")

    rc, f, _, _ = verdict(win(exit={"review_by": "2026-10-11"}), carried, opening, today)
    check("window_with_no_exit_written_down", len([x for x in f if "NO exit criteria" in x]), 1,
          "the DEFECT this file removes: an unwritten exit makes a window a policy")

    rc, f, _, _ = verdict(win(exit={"criteria": [{"id": "vibes", "bugs": ["BUG-577"]}], "review_by": "2026-10-11"}),
                          carried, opening, today)
    check("a_criterion_no_reader_can_settle", len([x for x in f if "no reader can settle" in x]), 1,
          "an exit clause no machine can settle is an exit that never arrives")

    rc, f, _, _ = verdict(win(state="closed"), carried, held_open, today)
    check("closed_while_the_exit_is_unmet", len([x for x in f if "(f)" in x]), 1,
          "closing is a claim; only a MET exit makes it true")

    rc, f, _, _ = verdict(win(exit={"criteria": [{"id": "opening_set_closed",
                                                  "bugs": ["BUG-577", "BUG-575", "BUG-571"]}],
                              "review_by": "2026-09-01"}), carried, opening, today)
    check("horizon_before_the_opening", len([x for x in f if "precedes the opening" in x]), 1,
          "a horizon that precedes the opening is not a horizon")

    rc, f, _, _ = verdict(win(held="BUG-585", released=[], exit={"criteria": "nothing_still_held", "review_by": "2026-10-11"}),
                          carried, held_open, today)
    check("a_malformed_declaration_is_a_fault_not_a_traceback", (rc, len(f)), (1, 3),
          "held/released/criteria of the WRONG SHAPE are three named faults: a reader that crashes reports nothing (C16)")

    rc, f, _, _ = verdict(win(exit={"criteria": [{"id": "nothing_still_held", "held": ["BUG-585"]}], "review_by": "2026-10-11"}),
                          carried, held_open, today)
    check("a_criterion_carrying_a_key_no_reader_reads", len([x for x in f if "NO reader" in x]), 1,
          "a clause key the reader ignores is an assertion, not a subject (D-405): the clause would be settled by window.held instead")

    rc, f, _, _ = verdict({}, carried, opening, today)
    check("no_window_declared", len(f), 1, "a freeze that names no window can only be believed")

    print("freeze-window controls: " + str(ok) + "/" + str(ok + fail) + " known-answer control(s) fire")
    return 1 if fail else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="THE FREEZE WINDOW: what is parked, and what ends it (D-2688)")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls over synthetic windows")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not CFG.is_file():
        print("FAIL-CLOSED: config/freeze_window.yaml is absent - a freeze with no home can only be believed (C16)")
        return 1
    doc = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
    if not REGISTER.is_file():
        print("FAIL-CLOSED: " + str(REGISTER.relative_to(REPO)) + " is absent - a parked id with no register to check against is an assertion (C16)")
        return 1
    reg = json.loads(REGISTER.read_text(encoding="utf-8"))
    win = doc.get("window") or {}
    today = dt.date.today()
    open_now = open_ids(reg)
    rc, faults, met, unmet = verdict(win, carried_ids(reg), open_now, today)
    opened = parse_date(win.get("opened"))
    review_by = parse_date((win.get("exit") or {}).get("review_by"))
    held = [str(x) for x in (win.get("held") or [])]
    released = {str(x) for x in (win.get("released") or {})}
    still = [b for b in held if b in open_now and b not in released]
    if opened:
        span = " of " + str((review_by - opened).days) + ", review_by " + str(review_by) if review_by else ""
        print("freeze window: " + str(win.get("id")) + " state=" + str(win.get("state")) + " opened=" + str(opened)
              + " day " + str((today - opened).days) + span + "; parked " + str(len(held)) + " (ceiling "
              + str(win.get("max_held")) + "), still OPEN " + str(len(still)) + ", released " + str(len(released)))
    if faults:
        print("")
        print("FAIL freeze window: " + str(len(faults)) + " fault(s) - a freeze whose claims cannot be checked is a belief (D-2688):")
        for x in faults:
            print("  - " + x)
        return rc
    for c in met:
        print("  exit MET:   " + c)
    for c in unmet:
        print("  exit UNMET: " + c)
    if rc == 2:
        if not unmet:
            print("  OWNER-OWED: the declared EXIT is MET - CLOSE the window (state: closed) or re-rule its exit; a window that outlives its own exit is a policy (D-2688)")
        else:
            print("  OWNER-OWED: the horizon " + str(review_by) + " has passed with the exit UNMET - RE-RULE the window (a new review_by with a reason) or close it; renewing by default is how a window becomes a policy (D-337)")
        return 2
    if str(win.get("state")) == "closed":
        print("  ok   the window is CLOSED and its declared EXIT is MET: it ended by its own terms, and the parked set stays COUNTED (D-2688)")
        return 0
    print("  ok   the window is OPEN with its exit written DOWN and UNMET inside its horizon: the parked set is COUNTED and the exit is DECLARED (D-2688)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
