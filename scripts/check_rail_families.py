#!/usr/bin/env python3
"""check_rail_families.py - THE INVARIANT PARTITION (T-207 phase-1(a), under the registry's authority D-2665).

WHY (the class, not the instance). The registry (scripts/check_rail_registry.py, D-2665) settles, per ONE rail,
"is it invoked or declared dormant, and is its declared writer's remedy proven?" It does NOT answer "which
INVARIANT has no owner": an entire family of rails could vanish and every surviving rail would still answer
"owned". A FAMILY is the set of rails that guard ONE invariant - the thing that breaks TOGETHER - so a rail in
ZERO families and a family whose member no longer exists are the same defect one level up, and a per-rail registry
cannot name either (BUG-492's class at the family grain).

WHAT THIS IS. A pure reader over TWO declared homes (C12: no path, pattern or count in code):
  * the ladder's own bytes (config/rail_registry.yaml#ladder, #recipes) -> the set of rail SUBJECTS (script paths);
  * config/rail_registry.yaml#families -> each invariant family's member SUBJECTS.
It verifies the families section is a PARTITION and a CENSUS - both directions, so a change to either side is a
RED rail, never a silent drift (the BUG-1030 coupling #3 class: an unverified path):
  (i)  every ladder subject is in EXACTLY ONE family (no unowned rail, no rail with two owners);
  (ii) every family subject is a REAL ladder subject (no stale reference to a renamed/deleted rail);
  (iii) a family member is a SUBJECT (a bare script path), never a command form with flags - flags belong to the
        guards/writers sections, which pin a SPECIFIC invocation, while a family owns the INVARIANT a script
        serves (a script's --selftest and --check are ONE member, two faces of the same invariant).
The banner echo and the `{{just_executable()}} --list` template line are NOT rails (output + a harness self-check),
so they carry no family and are not part of the partition.

It does NOT decide which family a rail belongs to (that is a DECLARATION in the registry) and it does NOT read the
rails' internals - it reports whether the declared partition covers the ladder exactly, in both directions.

Exit: 0 ok | 1 fault(s) (a missing or malformed families section is a fault, fail closed, C16).
--selftest: known-answer controls over SYNTHETIC ladders (no NLI, no live-tree write, BUG-492).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import check_rail_registry as crr

REPO = Path(__file__).resolve().parents[1]
# A rail SUBJECT is a script path (scripts/ pipeline/ agent/), .py or .sh. This is the INCLUSIVE set: the
# registry's own rail regex (D-2665) is narrower (scripts|pipeline, .py only) because it audits the .py rail
# scripts on disk, while a FAMILY must also own the .sh hook (F1) and the agent adapter (F9) the ladder invokes.
SUBJECT = re.compile(r"((?:scripts|pipeline|agent)/[\w./-]+\.(?:py|sh))")
SUBJECTS = "subjects"
MEMBERS = "members"


def ladder_subjects(text: str, recipes: list[str]) -> set[str]:
    """The rail SUBJECTS the ladder actually declares, read from its own bytes (never a census in code)."""
    inv = crr.ladder_invocations(text, [str(r) for r in recipes])
    out: set[str] = set()
    for cmd in inv:
        m = SUBJECT.search(cmd)
        if m:
            out.add(m.group(1))
    return out


def member_class(s: str) -> str:
    """'subject' | 'command-form' | 'garbage' - what KIND of family member this is (a bare path, a path WITH
    flags, or not a script path at all)."""
    if SUBJECT.fullmatch(s):
        return "subject"
    if SUBJECT.search(s):
        return "command-form"
    return "garbage"


def partition_faults(ladder_subjects: set[str], families: dict) -> list[str]:
    """PURE: name every partition fault - the one function both --check and --selftest exercise."""
    faults: list[str] = []
    if not isinstance(families, dict) or not families:
        return ["(iv) the registry declares no families section - a partition with no members makes the "
                "claim 'every rail has an owner' vacuous (C16)"]

    # (iii) first: a member that is not a bare subject can never be matched, so classify it before the join.
    # (i) + (ii): the join itself - both directions.
    owner: dict[str, list[str]] = {}
    for fam, members in families.items():
        if not isinstance(members, list):
            faults.append(f"(iii) families[{fam}] is not a list of subjects - a family is a SET of rails, "
                          f"not a scalar")
            continue
        for s in members:
            s = str(s)
            kind = member_class(s)
            if kind == "command-form":
                faults.append(f"(iii) families[{fam}] names {s!r}, a COMMAND FORM not a subject - flags belong "
                              f"to guards/writers, which pin one invocation; a family owns the INVARIANT a "
                              f"script serves (a script's --selftest and --check are ONE member)")
                continue
            if kind == "garbage":
                faults.append(f"(iii) families[{fam}] names {s!r}, which is not a script path - a declaration "
                              f"whose subject is not a rail (D-405)")
                continue
            if s not in ladder_subjects:
                faults.append(f"(ii) families[{fam}] names {s}, which the ladder does not invoke - a stale "
                              f"reference to a renamed or deleted rail (C19)")
            owner.setdefault(s, []).append(fam)

    for s in sorted(ladder_subjects):
        fams = owner.get(s)
        if not fams:
            faults.append(f"(i) {s} is a ladder rail with NO family - the invariant it guards has no owner "
                          f"(BUG-492's class at the family grain)")
        elif len(fams) > 1:
            faults.append(f"(i) {s} is declared in BOTH {fams[0]} and {fams[1]} - a rail with two owners is two "
                          f"invariants that disagree (the partition must be a PARTITION)")
    return faults


def audit(text: str, recipes: list[str], families: dict) -> tuple[list[str], dict]:
    """Return (faults, census) for one ladder text, one recipe set, one families declaration."""
    subjects = ladder_subjects(text, recipes)
    faults = partition_faults(subjects, families)
    census = {"subjects": len(subjects), "families": len(families),
              "members": sum(len(v) for v in families.values() if isinstance(v, list)),
              "unowned": len([s for s in subjects if s not in
                              {m for v in families.values() if isinstance(v, list) for m in v}])}
    return faults, census


def load() -> tuple[str, list[str], dict]:
    """Fail closed (C16): the ladder, recipes and families are READ from the registry's own declaration."""
    cfg = crr.load_cfg()
    ladder = REPO / str(cfg["ladder"])
    if not ladder.is_file():
        raise SystemExit(f"FAIL-CLOSED: config/rail_registry.yaml#ladder names {cfg['ladder']}, which is absent")
    text = ladder.read_text(encoding="utf-8")
    recipes = [str(r) for r in cfg.get("recipes") or []]
    families = cfg.get("families") or {}
    return text, recipes, families


def selftest() -> int:
    """Known-answer controls over SYNTHETIC ladders and families: a partition that never reports a fault is not
    a partition. Every control asserts the EXACT fault count, never a model's opinion (D-3036)."""
    ok = fail = 0

    def check(name: str, got: int, want: int, why: str) -> None:
        nonlocal ok, fail
        if got == want:
            ok += 1
            print(f"  ok   selftest/{name}: {why}")
        else:
            fail += 1
            print(f"  FAIL selftest/{name}: {why} (got {got} fault(s), want {want})")

    L = ("health:\n"
         "    python3 scripts/check_a.py --selftest || exit 1\n"
         "    python3 scripts/check_a.py --check || exit 1\n"
         "    python3 scripts/check_b.py --check || exit 1\n")
    FAM = {"F1": ["scripts/check_a.py"], "F2": ["scripts/check_b.py"]}

    f, _ = audit(L, ["health"], FAM)
    check("clean_partition", len(f), 0, "two rails each in one family is silent")

    f, _ = audit(L, ["health"], {"F1": ["scripts/check_a.py"]})
    check("unowned_rail", len([x for x in f if "(i)" in x and "NO family" in x]), 1,
          "a ladder rail in ZERO families is reported (i) - the invariant has no owner")

    f, _ = audit(L, ["health"], {"F1": ["scripts/check_a.py"], "F2": ["scripts/check_a.py",
                                                                     "scripts/check_b.py"]})
    check("double_owned_rail", len([x for x in f if "two owners" in x]), 1,
          "a ladder rail in TWO families is reported (i) - the partition must be a PARTITION")

    f, _ = audit(L, ["health"], {"F1": ["scripts/check_a.py"], "F2": ["scripts/check_gone.py"]})
    check("stale_member", len([x for x in f if "(ii)" in x]), 1,
          "a family member the ladder does not invoke is reported (ii) - a stale reference (C19)")

    f, _ = audit(L, ["health"], {"F1": ["scripts/check_a.py --selftest"], "F2": ["scripts/check_b.py"]})
    check("command_form_member", len([x for x in f if "(iii)" in x]), 1,
          "a family member written as a command form (flags) is refused (iii) - families own invariants, "
          "guards/writers own invocations")

    f, _ = audit(L, ["health"], {"F1": ["the ingest door"]})
    check("garbage_member", len([x for x in f if "(iii)" in x and "not a script path" in x]), 1,
          "a family member that is not a script path is refused (iii)")

    f, _ = audit(L, ["health"], {})
    check("families_absent", len([x for x in f if "(iv)" in x]), 1,
          "an absent families section is reported (iv), fail closed - the census is vacuous without it")

    print(f"rail-families controls: {ok}/{ok + fail} known-answer control(s) fire")
    return 1 if fail else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="the invariant partition: every rail in exactly one family")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls over synthetic ladders")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    text, recipes, families = load()
    faults, census = audit(text, recipes, families)
    print(f"rail families: {census['subjects']} ladder subject(s), {census['families']} famil(ies), "
          f"{census['members']} declared member(s)")
    if faults:
        print(f"\nFAIL rail families: {len(faults)} fault(s) - the partition does not cover the ladder exactly:")
        for x in faults:
            print("  - " + x)
        return 1
    print("  ok   the families section is a PARTITION and a CENSUS: every ladder rail is in exactly one family, "
          "every family member is a real ladder subject, and no family names a command form or a non-rail path")
    return 0


if __name__ == "__main__":
    sys.exit(main())
