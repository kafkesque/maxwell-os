#!/usr/bin/env python3
"""check_register_divergence.py - the LOG and the REGISTER diverge: THREE shapes, all RED (BUG-481, BUG-571, D-3032).

WHY. scripts/bug_status.py folds STATUS EVENTS, and a status event is a HEADER. A closure written as a body
paragraph is invisible, so the machine register over-reports: MEASURED 2026-09-25, 8 ids carry an explicit
`**Status:** FIXED|RESOLVED|CLOSED` in the body while their last header classifies OPEN. The register said
"114 open" and the C15 handoff rule was driven by that phantom count.

check_bug_status.py CANNOT catch this: it re-derives the register from the same headers and byte-compares, so
it certifies the PARSER, never the LOG (the BUG-467 class - a rail whose evidence is the same source as the
artifact it checks).

THE RULE: one fact has one HOME (the header event). The other place is made LOUD. The declared list in
config/register_divergence.yaml is SHRINK-ONLY: an id listed there that is no LONGER divergent is itself a
failure, so the list can only be emptied by promoting each closure to a header event or re-opening the bug.

THE THIRD SHAPE (D-3032, T-166 - MEASURED 2026-10-16). The declared_uncarried list declares the log's
ARCHAEOLOGY: names no machine home owns and that D-2645 refuses to backfill. An id a decision or a task CLAIMS as
one of its own bugs is NOT archaeology - it is a LIVE assertion the register cannot answer (D-2660) - so it may
not be declared here and the two sets may not intersect. WHERE a claim lives is DECLARED (claim_homes below, C12),
and a rule with no subject set is a fault rather than a silence (BUG-487/D-2644).
Fail closed (C16).
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

# BUG-571: the id SHAPE as the log writes it. This is a TOKEN read, and the rail is careful about what that
# means - see uncarried_ids(): it does not decide what a bug IS, it reports which NAMES the register cannot
# answer for, and the resulting set is pinned BY IDENTITY (D-2645).
TOKEN_RE = re.compile(r"BUG-\d+")

REPO = Path(__file__).resolve().parents[1]
BUGLOG = REPO / "governance" / "buglog.md"
CONFIG = REPO / "config" / "register_divergence.yaml"
HEADER_RE = re.compile(r"^#{2,3}\s+(BUG-\d+)\b[\s:—‑-]*(.*)$")
# An EXPLICIT status field, not prose: `**Status:** FIXED`, `**status**: FIXED`, `**Status: RESOLVED**`.
STATUS_FIELD_RE = re.compile(
    r"\*\*\s*status\s*:?\s*\*\*\s*:?\s*(FIXED|RESOLVED|CLOSED|INVALID|RETRACTED)", re.I)


def _load_parser():
    """Import scripts/bug_status.py so this rail cannot drift from the register's own classifier."""
    spec = importlib.util.spec_from_file_location("bug_status_rail", REPO / "scripts" / "bug_status.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def divergent_ids(lines: list[str]) -> dict[str, str]:
    """Return {bug_id: evidence} where the last header says OPEN but the body asserts a closure."""
    parser = _load_parser()
    spans: dict[str, list[int]] = {}
    for i, line in enumerate(lines):
        m = HEADER_RE.match(line)
        if m:
            spans.setdefault(m.group(1), []).append(i)
    out: dict[str, str] = {}
    for bid, idxs in spans.items():
        last = idxs[-1]
        end = len(lines)
        for j in range(last + 1, len(lines)):
            if HEADER_RE.match(lines[j]):
                end = j
                break
        state = parser.classify(parser.status_slot(HEADER_RE.match(lines[last]).group(2).strip()))
        if state != "open":
            continue
        body = "\n".join(lines[last + 1:end])
        m = STATUS_FIELD_RE.search(body)
        if m:
            out[bid] = f"header is OPEN but the body asserts **Status: {m.group(1).upper()}**"
    return out


def carried_ids(lines: list[str]) -> set[str]:
    """The ids the REGISTER carries - its own projection of the log: one HEADER event per id (BUG-428)."""
    return {m.group(1) for m in (HEADER_RE.match(l) for l in lines) if m}


def uncarried_ids(lines: list[str], carried: set[str]) -> dict[str, int]:
    """
    Return {id: 1-based first line naming it} for every id the LOG names that the register does NOT carry (BUG-571).

    PURE on purpose (no parser, no filesystem): a rule that can only be run against the LIVE log cannot be
    REHEARSED, and a rule that cannot be made to fail is not a rule (D-2676).

    WHY A TOKEN READ IS NOT THE REFUSED PROSE SCAN. buglog.md refused 'a regex over every BUG-<n> token' because
    such a control would 'invent ids from archaeology, quoted decisions and this very block'. MEASURED
    2026-09-27, that objection is now a NUMBER rather than a fear: the walker reports 62 ids, and every one of
    them is a real name in real use (a legacy row, a legacy bullet, or BUG-492, quoted 33 times by the standing
    rule). Nothing here decides what a bug IS or what state it has: it decides which NAMES the machine register
    cannot answer for, and that set is declared, pinned by identity and SHRINK-ONLY - so the walker cannot
    invent debt, it can only ADD TO A LIST A HUMAN MUST EDIT.
    """
    out: dict[str, int] = {}
    for i, line in enumerate(lines, start=1):
        for tok in TOKEN_RE.findall(line):
            if tok not in carried:
                out.setdefault(tok, i)
    return out


def _records(text: str) -> list[tuple[str, list[str]]]:
    """Split a register into (record id, lines) at a TOP-LEVEL id marker - a nested id is not a record (BUG-587)."""
    out: list[tuple[str, list[str]]] = []
    rid, buf = "", []
    for line in text.splitlines():
        if line.startswith("- id:"):
            if buf or rid:
                out.append((rid, buf))
            rid = line[len("- id:"):].strip()
            buf = []
        buf.append(line)
    if buf:
        out.append((rid, buf))
    return out


def claim_homes(cfg: dict) -> list[dict]:
    """The DECLARED places a bug may be CLAIMED as this system's own (D-3032). PURE, and fail-closed (C16).

    A claim is a FIELD WHOSE SEMANTIC IS OWNERSHIP - a decision record's bugs: list, a task record's source:
    field. Everything else is a NAME, and a name is what declared_uncarried is for. An entry that names no
    path or no field is refused rather than defaulted, because where a claim lives is a declaration (C12).
    """
    homes = cfg.get("claim_homes")
    if not isinstance(homes, list) or not homes:
        return []
    for h in homes:
        if not isinstance(h, dict) or not str(h.get("path") or "").strip() or not str(h.get("field") or "").strip():
            raise SystemExit("FATAL: config/register_divergence.yaml#claim_homes has an entry with no path or no "
                             "field - where a claim lives is a declaration, never a default (C12/D-2644)")
    return [{"path": str(h["path"]).strip(), "field": str(h["field"]).strip()} for h in homes]


def claimed_ids(homes: list[dict], texts: dict) -> dict[str, list[str]]:
    """{bug id: [record#field, ...]} for every id a DECLARED claim home asserts as its own bug (D-3032).

    PURE on purpose (D-2676): the texts are INJECTED, so a known-answer control and the live rail run the same
    code. A field is read on ITS OWN LINE plus any continuation line indented past it; a mention in another
    field of the same record is a NAME, not a claim - which is the whole distinction this shape rests on.
    """
    out: dict[str, list[str]] = {}
    for home in homes:
        path = str(home.get("path") or "")
        field = str(home.get("field") or "")
        pat = re.compile("^\\s{2}" + re.escape(field) + ":\\s*(.*)$")
        for rid, lines in _records(texts.get(path, "")):
            value = ""
            for i, line in enumerate(lines):
                m = pat.match(line)
                if not m:
                    continue
                value = m.group(1)
                for cont in lines[i + 1:]:
                    if cont.startswith("    ") and cont.strip():
                        value += " " + cont.strip()
                    else:
                        break
                break
            for tok in TOKEN_RE.findall(value):
                out.setdefault(tok, [])
                label = rid + "#" + field
                if label not in out[tok]:
                    out[tok].append(label)
    return out


def _sorted(ids) -> list[str]:
    """Register order: by id NUMBER, so a diff is readable (a set's order is not evidence)."""
    return sorted(ids, key=lambda b: int(re.sub(r"\D", "", str(b)) or 0))


def faults(live: dict[str, str], declared: set[str], declared_max: int,
           uncarried: dict[str, int], declared_uncarried: set[str], declared_max_uncarried: int,
           limit: int = 8, claimed: dict[str, list[str]] | None = None,
           claim_homes_n: int = 1) -> list[str]:
    """ALL THREE divergence shapes against their declared, shrink-only lists. PURE (D-405): same code, live and rehearsed."""
    claimed = claimed or {}
    bad: list[str] = []
    new = _sorted(set(live) - declared)
    stale = _sorted(declared - set(live))
    if new:
        bad.append("UNDECLARED divergence (" + str(len(new)) + "): "
                   + ", ".join(str(b) + " (" + str(live[b]) + ")" for b in new[:limit]))
    if stale:
        bad.append("STALE declaration (" + str(len(stale)) + "): " + ", ".join(stale[:limit]) + " - no longer "
                   "divergent; the list is SHRINK-ONLY, remove the entry (BUG-481)")
    if len(declared) > declared_max:
        bad.append("declared " + str(len(declared)) + " exceeds declared_max " + str(declared_max) + " - raising "
                   "the ceiling requires a declared decision, not an edit")
    named = _sorted(set(uncarried) - declared_uncarried)
    carried_again = _sorted(declared_uncarried - set(uncarried))
    if named:
        bad.append("UNDECLARED uncarried id (" + str(len(named)) + "): "
                   + ", ".join(b + " @line " + str(uncarried[b]) for b in named[:limit]) + " - the log NAMES an id "
                   "no machine home carries (BUG-571). Give it a HEADER event (it is a bug) or remove the name (it "
                   "is not): a citation naming nothing is worse than no citation (D-2660), and the register cannot "
                   "count what no header carries.")
    if carried_again:
        bad.append("STALE uncarried declaration (" + str(len(carried_again)) + "): " + ", ".join(carried_again[:limit])
                   + " - the register now CARRIES it; the list is SHRINK-ONLY, remove the entry (BUG-571)")
    if len(declared_uncarried) > declared_max_uncarried:
        bad.append("declared_uncarried " + str(len(declared_uncarried)) + " exceeds declared_max_uncarried "
                   + str(declared_max_uncarried) + " - raising the ceiling requires a declared decision, not an edit")
    declared_but_claimed = _sorted(set(declared_uncarried) & set(claimed))
    if declared_but_claimed:
        bad.append("DECLARED BUT CLAIMED (" + str(len(declared_but_claimed)) + "): " + ", ".join(
            b + " claimed by " + ", ".join(claimed[b][:3]) for b in declared_but_claimed[:limit])
            + " - a NAME may be declared (archaeology, D-2645); a CLAIM may not. A decision or a task asserting"
              " that this id is one of its bugs is a LIVE question the register cannot answer (D-2660), so the id"
              " must be PROMOTED to a header event and DELETED from declared_uncarried - raising the ceiling for"
              " it is not a remedy (D-3032/T-166).")
    if claim_homes_n < 1:
        bad.append("no claim home is declared - a rule with no subject set is green by vacancy (BUG-487/D-2644): "
                   "config/register_divergence.yaml#claim_homes must name where a bug may be CLAIMED")
    return bad


def selftest() -> int:
    """Known-answer controls over SYNTHETIC logs and lists: BOTH shapes, BOTH directions (D-2676, BUG-492)."""
    ok = fail = 0

    def check(name: str, got, want, why: str) -> None:
        nonlocal ok, fail
        if got == want:
            ok += 1
            print("  ok  selftest/" + name)
        else:
            fail += 1
            print("FAIL selftest/" + name + ": got " + repr(got) + ", expected " + repr(want) + " - " + why)

    def count(bad: list[str], needle: str) -> int:
        return len([b for b in bad if needle in b])

    log = ["# Bug log", "", "## BUG-001 (LOW): a real bug", "see BUG-999 for the cause", "| BUG-002 | 2026-01-01 | x |"]
    carried = carried_ids(log)
    check("the_register_projection_ignores_prose", carried, {"BUG-001"},
          "the register's domain is HEADER events, not tokens")
    check("uncarried_id_is_reported", uncarried_ids(log, carried), {"BUG-999": 4, "BUG-002": 5},
          "an id the log names and no header carries must be reported with its first line")
    check("carried_id_is_silent", uncarried_ids(log, {"BUG-001", "BUG-002", "BUG-999"}), {},
          "the negative control: nothing named is uncarried -> nothing is reported")
    check("a_fault_is_not_the_first_only", len(uncarried_ids(log, {"BUG-001"})), 2,
          "an id is not a prefix of another id's report")
    one = faults({}, set(), 0, {"BUG-999": 4}, set(), 0)
    check("undeclared_uncarried_id_is_a_fault", count(one, "UNDECLARED uncarried id"), 1, "a NEW name is RED")
    two = faults({}, set(), 0, {}, {"BUG-999"}, 62)
    check("a_pin_that_is_now_carried_is_stale", count(two, "STALE uncarried declaration"), 1,
          "the pin is SHRINK-ONLY: it may not go stale (D-2645)")
    pins = {"BUG-" + str(i).zfill(3) for i in range(62)}
    three = faults({}, set(), 0, {}, pins, 61)
    check("the_uncarried_ceiling_is_read", count(three, "exceeds declared_max_uncarried"), 1,
          "raising the ceiling is an edit a human reads, not a quiet growth")
    four = faults({"BUG-007": "header is OPEN but the body asserts **Status: FIXED**"}, set(), 0, {}, set(), 0)
    check("the_first_shape_still_fires", count(four, "UNDECLARED divergence"), 1, "BUG-481 is not weakened")
    five = faults({"BUG-007": "ev"}, {"BUG-007"}, 1, {"BUG-002": 5}, {"BUG-002"}, 1)
    check("clean_is_silent", five, [], "the negative control over BOTH shapes")
    six = faults({"BUG-007": "ev"}, {"BUG-007"}, 0, {}, set(), 0)
    check("the_divergence_ceiling_is_read", count(six, "exceeds declared_max "), 1, "BUG-481's ceiling is read")
    ten = faults({}, set(), 0, {"BUG-999": 4}, {"BUG-999"}, 39, claimed={"BUG-999": ["D-3004#bugs"]})
    check("a_declared_id_that_is_CLAIMED_is_a_fault", count(ten, "DECLARED BUT CLAIMED"), 1,
          "an id a decision or a task owns may not be declared away (D-3032): promote it")
    eleven = faults({}, set(), 0, {"BUG-999": 4}, {"BUG-999"}, 39, claimed={"BUG-998": ["D-1#bugs"]})
    check("a_declared_id_that_is_only_NAMED_is_silent", eleven, [],
          "the negative control: archaeology stays declared, and the rule fires on the CLAIM, not on a count")
    homes = [{"path": "p.yaml", "field": "bugs"}, {"path": "q.yaml", "field": "source"}]
    texts = {"p.yaml": "- id: D-1\n  bugs: '[BUG-804, BUG-807]'\n- id: D-2\n  evidence: 'names BUG-810 only'\n",
             "q.yaml": "- id: T-1\n  source: BUG-804; D-3004\n"}
    check("a_claim_is_read_from_its_OWN_field", claimed_ids(homes, texts),
          {"BUG-804": ["D-1#bugs", "T-1#source"], "BUG-807": ["D-1#bugs"]},
          "a mention in another field is a NAME, not a claim - the distinction the shape rests on")
    twelve = faults({}, set(), 0, {}, set(), 0, claim_homes_n=0)
    check("a_rule_with_no_claim_home_is_a_fault", count(twelve, "no claim home is declared"), 1,
          "green by vacancy is the BUG-487 disease, so an undeclared subject set is RED (D-2644)")
    print("ok register divergence selftest: " + str(ok) + " known-answer control(s) fire, both directions,"
          " all three shapes")
    if fail:
        print("FAIL register divergence selftest: " + str(fail) + " control(s) did not fire")
        return 1
    return 0


def main() -> int:
    """Compare the live divergence with the declared, shrink-only list. Require exact agreement."""
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true",
                    help="known-answer controls over SYNTHETIC logs and lists (BUG-492)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    lines = BUGLOG.read_text(encoding="utf-8").splitlines()
    carried = carried_ids(lines)
    declared = {str(e["id"]) for e in (cfg.get("declared_divergent") or [])}
    declared_uncarried = {str(x) for x in (cfg.get("declared_uncarried") or [])}
    homes = claim_homes(cfg)   # D-3032: DECLARED, never hardcoded (C12)
    missing = [h["path"] for h in homes if not (REPO / h["path"]).exists()]
    if missing:
        print("FAIL register divergence: a declared claim home is ABSENT - " + ", ".join(missing)
              + " - a declaration whose subject is gone is an assertion, not a control (D-405/BUG-488)")
        return 1
    texts = {h["path"]: (REPO / h["path"]).read_text(encoding="utf-8") for h in homes}
    claimed = claimed_ids(homes, texts)
    bad = faults(divergent_ids(lines), declared, int(cfg.get("declared_max", 0)),
                 uncarried_ids(lines, carried), declared_uncarried,
                 int(cfg.get("declared_max_uncarried", 0)), claimed=claimed,
                 claim_homes_n=len(homes))
    if bad:
        print("FAIL register divergence (BUG-481/BUG-571):")
        for b in bad:
            print("  !!", b)
        print("  a bug belongs in a HEADER, where the register can see it; the body is made loud, not silent. "
              "Reconcile governance/buglog.md, then re-run scripts/bug_status.py.")
        return 1
    print("ok register divergence: " + str(len(declared)) + " declared divergence(s), all still divergent; "
          + str(len(declared_uncarried)) + " named-but-uncarried id(s) declared, all still uncarried; ceilings "
          + str(int(cfg.get("declared_max", 0))) + "/" + str(int(cfg.get("declared_max_uncarried", 0)))
          + " (shrink-only); " + str(len(carried)) + " id(s) carried; " + str(len(claimed))
          + " claimed id(s) read from " + str(len(homes)) + " declared claim home(s), none of them declared")
    return 0


if __name__ == "__main__":
    sys.exit(main())
