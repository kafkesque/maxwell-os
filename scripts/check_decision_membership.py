#!/usr/bin/env python3
"""BUG-587 (D-2690): DECISION-LOG.md and config/decisions.yaml must name the SAME records, one way.

WHY THIS FILE EXISTS (D-405). tools/sync_decisions.py was RETIRED 2026-09-23 (BUG-402) and its tombstone
declares: 'What it never did: membership (registry ids vs log headings). That check is
scripts/check_decision_membership.py.' That file DID NOT EXIST: the ONE oracle that would have caught an ABSORBED
mint was named by a declaration and implemented nowhere - and a declaration whose subject is absent is an
assertion, not a control.

THE DIRECTION THAT IS SETTLEABLE (MEASURED 2026-09-27). Every id NAMED in DECISION-LOG.md must name a TOP-LEVEL
record in config/decisions.yaml. The REVERSE direction is NOT asserted: the log's own header calls it a TIERED
face of the registry, so it carries the OPEN/ACTIVE/DONE tiers and dated history while the full append-only
history lives in archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md. MEASURED: 194 ids are named in the log
against 820 records, so an equality join would RED on ~680 legitimate records - a loud rail nobody can satisfy is
not a rail (BUG-540).

THE SIGNATURE IT CATCHES (BUG-587, MEASURED). A hand-rolled append re-indented a record's block, so the record
parsed as ONE MORE ENTRY of the PREVIOUS record's files: list. Its bytes were in the file, the YAML LOADED, every
rail stayed GREEN, the census did not move - and the log entry that named the minted id had no record to name.
This rail is the join that sees it.

WHAT IS DELIBERATELY OUT OF SCOPE (a DECLARED gap, never a silent one). The log's header also declares a COUNT
('config/decisions.yaml (651 decisions)') which is stale by 169 and lives in an append_only file where no append
can repair it. FILED as BUG-588, because a count belongs in the DERIVED census (D-2646 one fact, one home).

READ BY: just health (--selftest and the live check). RULES: config/decisions_policy.yaml#membership (the ONE
home). The id SPELLING rule is IMPORTED from the reconciler, never restated (D-2646/C21).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from recompute_decision_summary import DECISIONS_YAML, normalized_id  # noqa: E402 - one spelling rule, one home

POLICY_YAML = ROOT / "config" / "decisions_policy.yaml"
NAME = "decision-membership"


def policy_problems(doc: dict) -> list[str]:
    """Every reason the membership RULES cannot be read - NAMED, never defaulted (D-2644/BUG-487)."""
    problems: list[str] = []
    block = (doc or {}).get("membership")
    if not isinstance(block, dict):
        problems.append("declares no membership: mapping - the join would run against a belief about itself")
        return problems
    if not str(block.get("log") or "").strip():
        problems.append("membership.log: absent - the file the join reads is a path, and this one is not declared")
    patterns = block.get("id_patterns")
    if not isinstance(patterns, list) or not [p for p in patterns if str(p).strip()]:
        problems.append("membership.id_patterns: absent or empty - a join with no subject set reads nothing")
    pinned = block.get("legacy_orphan_ids")
    if not isinstance(pinned, list):
        problems.append("membership.legacy_orphan_ids: absent or not a list - the legacy debt of this join is "
                        "pinned BY IDENTITY, so an empty list must be written, never omitted (D-2682)")
    return problems


def named_ids(log_text: str, patterns: list[str]) -> list[str]:
    """Every id NAMED in the log, NORMALISED, deduped: the log repeats an id across tiers (MEASURED)."""
    found: set[str] = set()
    for pattern in patterns:
        for hit in re.findall(pattern, log_text, re.M):
            found.add(normalized_id({"id": hit}))
    return sorted(found)


def top_level_ids(records: list) -> list[str]:
    """The ids of the TOP-LEVEL records: an id nested inside another record's list is NOT a record (BUG-587)."""
    return [normalized_id(r) for r in records if isinstance(r, dict)]


def faults(named: list[str], records: list, pinned: list[str]) -> list[str]:
    """Return (orphans, stale pins) as NAMED faults, joining BOTH directions (D-405)."""
    top = set(top_level_ids(records))
    named_set = set(named)
    problems: list[str] = []
    for n in sorted(named_set):
        if n not in top and n not in pinned:
            problems.append("DECISION-LOG.md names " + n + " and config/decisions.yaml carries no TOP-LEVEL record "
                            "with that id - either the record was ABSORBED into another record's list (BUG-587) or "
                            "the log names a decision that was never minted")
    for p in sorted(set(pinned)):
        if p in top:
            problems.append(p + " is pinned as a legacy orphan and IS a top-level record now: a STALE declaration "
                            "(D-405) - remove it from membership.legacy_orphan_ids")
        elif p not in named_set:
            problems.append(p + " is pinned as a legacy orphan and DECISION-LOG.md no longer names it: a STALE "
                            "declaration (D-405) - remove it from membership.legacy_orphan_ids")
    return problems


def controls() -> list[tuple[str, bool]]:
    """Known-answer controls (BUG-492): a join nobody has seen fire is a comment. Synthetic, never the live tree."""
    recs = [{"id": "D-9001"}, {"id": "D-9002"}, {"id": "D-9003"}]
    absorbed = [{"id": "D-9001"}, {"id": "D-9002", "files": [{"id": "D-9004"}]}, {"id": "D-9003"}]
    return [
        ("an id the log names AND the registry carries at TOP LEVEL is quiet",
         not faults(["D9001", "D9002", "D9003"], recs, [])),
        ("an id named in the log with no record fires",
         bool(faults(["D9001", "D9004"], recs, []))),
        ("an id that exists only NESTED in another record fires (the BUG-587 ABSORBED shape)",
         bool(faults(["D9001", "D9004"], absorbed, []))),
        ("a pinned legacy orphan is TOLERATED - the pin is the declaration that the debt is known",
         not faults(["D9001", "D637"], recs, ["D637"])),
        ("a pin that became a TOP-LEVEL record is a STALE declaration and fires (D-405)",
         bool(faults(["D9001"], recs, ["D9001"]))),
        ("a pin the log no longer names is a STALE declaration and fires (D-405)",
         bool(faults(["D9001"], recs, ["D637"]))),
        ("an id named TWICE in the log is NOT a fault - the log repeats an id across its tiers",
         not faults(["D9001", "D9001"], recs, [])),
        ("named_ids reads the D2552 TABLE ROW and the historical HEADING, and normalises both spellings",
         named_ids("| D-9001 | OPEN | x |\n## 2026-09-27 - D9002 does a thing\n", 
                   [r"^\|\s*(D-?\d+[a-z]?)\s*\|", r"^#{1,4}[^\n]*?\b(D-?\d+[a-z]?)\b"]) == ["D9001", "D9002"]),
        ("a policy with no membership block is a NAMED fault, not a traceback (BUG-487)",
         bool(policy_problems({}))),
        ("a policy whose membership block is missing its subject set is a NAMED fault",
         bool(policy_problems({"membership": {"log": "DECISION-LOG.md", "legacy_orphan_ids": []}}))),
    ]


def selftest() -> int:
    """Run the membership rail's known-answer controls; return 1 if any control did NOT fire."""
    rows = controls()
    for name, ok in rows:
        print(("  ok  " if ok else "  !!  ") + name)
    failed = [n for n, ok in rows if not ok]
    if failed:
        print("FAIL selftest:" + str(len(failed)) + " of " + str(len(rows)) + " known-answer control(s) did not "
              "fire - a membership join nobody has seen refuse is a comment (BUG-492)")
        return 1
    print("ok " + NAME + ": " + str(len(rows)) + "/" + str(len(rows)) + " known-answer control(s) fire")
    return 0


def load_policy() -> tuple[dict, list[str]]:
    """Read the ONE home of the rules; return (block, named faults). An absent file is a fault, not a crash."""
    if not POLICY_YAML.exists():
        return {}, [POLICY_YAML.relative_to(ROOT).as_posix() + ": ABSENT - the membership rules have no home on disk"]
    try:
        doc = yaml.safe_load(POLICY_YAML.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return {}, [POLICY_YAML.relative_to(ROOT).as_posix() + ": does not parse as YAML (" + str(exc) + ")"]
    problems = policy_problems(doc)
    return (doc.get("membership") or {}), problems


def main(argv: list[str]) -> int:
    """Live check: every id the log NAMES must name a TOP-LEVEL record in the registry."""
    if "--selftest" in argv:
        return selftest()
    block, problems = load_policy()
    if problems:
        print("FAIL " + NAME + ": " + "; ".join(problems))
        return 1
    log_path = ROOT / str(block["log"])
    if not log_path.exists():
        print("FAIL " + NAME + ": " + str(block["log"]) + " does not exist - the join's subject is absent (D-405)")
        return 1
    data = yaml.safe_load(DECISIONS_YAML.read_text(encoding="utf-8")) or {}
    records = data.get("decisions") or []
    named = named_ids(log_path.read_text(encoding="utf-8"), [str(p) for p in block["id_patterns"]])
    pinned = [normalized_id({"id": p}) for p in (block.get("legacy_orphan_ids") or [])]
    top = set(top_level_ids(records))
    found = faults(named, records, pinned)
    if found:
        print("FAIL " + NAME + ": " + str(len(found)) + " fault(s):")
        for problem in found:
            print("  - " + problem)
        return 1
    absent = len(top - set(named))
    print("ok " + NAME + ": " + str(len(named)) + " id(s) NAMED in " + str(block["log"]) + ", " + str(len(top))
          + " TOP-LEVEL record(s), " + str(len(pinned)) + " pinned legacy orphan(s), 0 fault(s); "
          + str(absent) + " record(s) carry no log entry (the log is a TIERED face of the registry - its own "
          "header - so that direction is DECLARED, never asserted)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

