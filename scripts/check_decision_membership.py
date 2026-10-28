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

# one bug-heading grammar, one home (BUG-428)
from bug_status import HEADER_RE as BUG_HEADER_RE  # noqa: E402

# one spelling rule, one home (D-2646/C21)
from recompute_decision_summary import DECISIONS_YAML, normalized_id  # noqa: E402

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


def _walk_tokens(value: object, pattern: re.Pattern, out: list[str]) -> None:
    """BUG-1108: collect every D-token a record's value tree cites, recursively over str/list/dict."""
    if isinstance(value, str):
        out.extend(m.group(0) for m in pattern.finditer(value))
    elif isinstance(value, list):
        for item in value:
            _walk_tokens(item, pattern, out)
    elif isinstance(value, dict):
        for v in value.values():
            _walk_tokens(v, pattern, out)


def citation_problems(records: list, block: dict) -> list[str]:
    """BUG-1108: a D-token cited INSIDE a record must resolve to a minted record (or an allowed id).

    This is the register's INTERNAL join - the membership join above verifies the LOG names only minted ids;
    this verifies the RECORDS cite only minted ids in their own fields. REPORT-ONLY by default (D-2949/D-2951):
    a regex cannot separate a decision citation from an iron-rule reference (R-D410) or a config value (D150 cap),
    so it REPORTS candidates for owner resolution rather than firing on false positives (BUG-540).
    """
    if not block:
        return []
    minted = set(top_level_ids(records))
    allowed = {normalized_id({"id": str(a)}) for a in (block.get("allow_ids") or [])}
    pattern = re.compile(str(block.get("pattern") or r"\b(?<!R-)D-?\d{3,4}[a-z]?\b"))
    problems: list[str] = []
    for r in records:
        if not isinstance(r, dict) or not r.get("id"):
            continue
        rid = normalized_id(r)
        tokens: list[str] = []
        _walk_tokens(r, pattern, tokens)
        for tok in sorted({t.replace("D-", "D").upper() for t in tokens}):
            if tok in minted or tok in allowed:
                continue
            problems.append(rid + " cites " + tok + ", which names no minted record and is not an allowed id - "
                            "a declaration that does not resolve (D-3034); owner decides MINT / DROP / REPOINT")
    return problems


def _registry_citation_problems(records: list, pattern: object, registry: set, label: str) -> list[str]:
    """BUG-1108 follow-on: a token of ONE family cited inside a record must resolve in that family's registry.

    The D- family resolves through `citation_problems` against the minted decision set; this generalises the SAME
    walk (`_walk_tokens`) to the BUG- and T- families, whose tokens resolve against their OWN source registries -
    the buglog's `#{2,3}` headings and task_register.yaml's `- id:` entries. The caller applies report-vs-fatal
    semantics (D-2949/D-2951); this function only names the dangling tokens.
    """
    if not pattern:
        return []
    p = re.compile(str(pattern))
    problems: list[str] = []
    for r in records:
        if not isinstance(r, dict) or not r.get("id"):
            continue
        rid = normalized_id(r)
        tokens: list[str] = []
        _walk_tokens(r, p, tokens)
        for tok in sorted({t.upper() for t in tokens}):
            if tok in registry:
                continue
            problems.append(rid + " cites " + tok + ", which names no " + label + " - a declaration that does not "
                            "resolve (D-3034); owner decides MINT / DROP / REPOINT")
    return problems


def bug_citation_problems(records: list, block: dict) -> list[str]:
    """BUG-1108 follow-on: a BUG- token cited inside a record must resolve to a buglog heading.

    The canonical bug-id set is the buglog's own `#{2,3}` headings (one heading grammar, one home: BUG-428), read
    through BUG_HEADER_RE per line exactly as scripts/bug_status.py scans it - never a derived census that could
    drift (D-2646: one fact, one home).
    """
    path = str(block.get("bug_register") or "")
    if not path:
        return []
    p = ROOT / path
    if not p.exists():
        return [path + ": absent - the BUG- registry the citation join reads is a path, and this one is not on disk"]
    text = p.read_text(encoding="utf-8")
    registry = {m.group(1) for line in text.splitlines() if (m := BUG_HEADER_RE.match(line))}
    return _registry_citation_problems(records, block.get("bug_pattern"), registry, "bug heading")


def task_citation_problems(records: list, block: dict) -> list[str]:
    """BUG-1108 follow-on: a T- token cited inside a record must resolve to a task_register id (authority D-2981)."""
    path = str(block.get("task_register") or "")
    if not path:
        return []
    p = ROOT / path
    if not p.exists():
        return [path + ": absent - the T- registry the citation join reads is a path, and this one is not on disk"]
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    registry = {t.get("id") for t in (doc.get("tasks") or []) if isinstance(t, dict) and t.get("id")}
    return _registry_citation_problems(records, block.get("task_pattern"), registry, "task id")


def control_slug(name: str) -> str:
    """The control's name as a marker a mutation can be SEEN to red through (D-2676 iv)."""
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def header_problems(log_text: str, rules: dict | None = None) -> list[str]:
    """BUG-588: the log's header may POINT at the census; it may never RESTATE a count.

    A count in prose is a second home for a derived fact (D-2646/BUG-585 class) and it is UNFALSIFIABLE where it
    sits: MEASURED 2026-09-27, line 3 declared '(651 decisions)' while the census read 820 - stale by 169, and
    no rail joined the two. Rules live in config/decisions_policy.yaml#log_header (ONE home, C12).
    """
    if rules is None:
        if not POLICY_YAML.exists():
            return [POLICY_YAML.relative_to(ROOT).as_posix() + ": ABSENT - the header rule has no home on disk"]
        policy_doc = yaml.safe_load(POLICY_YAML.read_text(encoding="utf-8")) or {}
        rules = policy_doc.get("log_header") or {}
        if not rules:
            return [POLICY_YAML.relative_to(ROOT).as_posix() + "#log_header: not declared - the rule that a prose "
                    "header may not restate a derived count must live where a reader can FAIL on it (D-2644)"]
    name = str(rules.get("file") or "the log")
    head = log_text.splitlines()[: int(rules.get("scan_lines") or 5)]
    problems: list[str] = []
    pointer = str(rules.get("census_pointer") or "")
    if pointer and not any(pointer in line for line in head):
        problems.append(name + ": its header does not name the census (" + pointer + ") - a count with no single "
                        "home is the defect (D-2646/BUG-588)")
    pattern = re.compile(str(rules.get("forbidden_count_pattern") or r"(\d+)\s+decisions"))
    for n, line in enumerate(head, start=1):
        if pattern.search(line):
            problems.append(name + " line " + str(n) + ": the header RESTATES a decision count - the census is the "
                            "ONE home; a prose count went stale by 169 (BUG-588)")
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
        # BUG-989: the third surface is the BARE PARAGRAPH entry ('D-3134 (ACTIVE ...): **...**'), which neither
        # the table row nor the heading pattern could see. The new pattern matches a line-START D-id followed by a
        # parenthesised annotation ONLY - an inline prose reference ('D-9002 limb (iv)') and a list label ('D1')
        # must NOT be treated as a naming, or every prose citation would need a record (a rail nobody can satisfy
        # is not a rail, BUG-540).
        ("named_ids reads the BARE PARAGRAPH entry and leaves prose references and list labels unmatched (BUG-989)",
         named_ids("D-9001 (ACTIVE 2026-10-24): **A rule.**\nD-9002 limb (iv) SATISFIED\nD1 — a list label\n",
                   [r"^(D-?\d+[a-z]?)\s*\("]) == ["D9001"]),
        ("a policy with no membership block is a NAMED fault, not a traceback (BUG-487)",
         bool(policy_problems({}))),
        ("a policy whose membership block is missing its subject set is a NAMED fault",
         bool(policy_problems({"membership": {"log": "DECISION-LOG.md", "legacy_orphan_ids": []}}))),
        # D-2692: this control's input carried a count and NO census pointer, so it fired for the POINTER reason
        # and stayed green when the count pattern was neutered - a control that cannot tell its two reasons apart
        # proves neither (BUG-492), and the mutation gate REFUSED the entry until the input isolated the reason.
        ("a header that POINTS at the census and STILL restates a count is a NAMED fault (BUG-588)",
         any("RESTATES" in p for p in header_problems(
             "> **Updated:** 2026-09-20 | **Count:** `config/decisions_summary.json` (651 decisions)\n",
             {"file": "DECISION-LOG.md", "scan_lines": 5,
              "census_pointer": "config/decisions_summary.json",
              "forbidden_count_pattern": r"(\d+)\s+decisions"}))),
        ("a header that POINTS at the census and states no count is quiet (both directions, BUG-492)",
         not header_problems("# DECISION LOG\n\n> Count: `config/decisions_summary.json`\n",
                             {"file": "DECISION-LOG.md", "scan_lines": 5,
                              "census_pointer": "config/decisions_summary.json",
                              "forbidden_count_pattern": r"(\d+)\s+decisions"})),
        # BUG-1108: the citation join's known-answer controls - a citation to a minted id is quiet, to an unminted
        # id fires, an allowed id (sentinel/legacy orphan) is quiet, an iron-rule reference (R-D410) is NOT a
        # citation, and a 3-digit id IS matched (the grammar must not miss the 130 three-digit records).
        ("a record that cites only minted ids is quiet (BUG-1108)",
         not citation_problems([{"id": "D-9001", "category": "X (D-9002)"}, {"id": "D-9002"}],
                               {"pattern": r"\b(?<!R-)D-?\d{3,4}[a-z]?\b", "allow_ids": []})),
        ("a record that cites an unminted id fires (BUG-1108)",
         bool(citation_problems([{"id": "D-9001", "category": "X (D-9005)"}],
                                {"pattern": r"\b(?<!R-)D-?\d{3,4}[a-z]?\b", "allow_ids": []}))),
        ("an ALLOWED id (sentinel) is quiet, not a false positive (BUG-1108)",
         not citation_problems([{"id": "D-9001", "measured": "cap D-9999 sentinel"}],
                               {"pattern": r"\b(?<!R-)D-?\d{3,4}[a-z]?\b", "allow_ids": ["D-9999"]})),
        ("an IRON-RULE reference (R-D410) is NOT read as a citation (BUG-1108)",
         not citation_problems([{"id": "D-9001", "decision": "NEVER delete (R-D410)"}],
                               {"pattern": r"\b(?<!R-)D-?\d{3,4}[a-z]?\b", "allow_ids": []})),
        ("a THREE-digit id is matched by the grammar, never missed (BUG-1108)",
         bool(citation_problems([{"id": "D-9001", "title": "see D-150 cap"}],
                                {"pattern": r"\b(?<!R-)D-?\d{3,4}[a-z]?\b", "allow_ids": []}))),
        ("an absent citation block is quiet (the join is report-only and optional), not a crash",
         not citation_problems([{"id": "D-9001", "title": "cites D-9999"}], {})),
        # BUG-1108 follow-on: the BUG-/T- citation joins' known-answer controls - a token that resolves to a
        # canonical bug heading / task id is quiet, a phantom fires, and the BUG- vs T- grammars never cross.
        ("a record that cites a MINTED bug id is quiet (BUG-1108 BUG-family)",
         not _registry_citation_problems([{"id": "D-9001", "decision": "see BUG-9001"}],
                                         r"\bBUG-\d+\b", {"BUG-9001"}, "bug heading")),
        ("a record that cites a PHANTOM bug id fires (BUG-1108 BUG-family)",
         bool(_registry_citation_problems([{"id": "D-9001", "decision": "see BUG-9999"}],
                                          r"\bBUG-\d+\b", {"BUG-9001"}, "bug heading"))),
        ("a record that cites a MINTED task id is quiet (BUG-1108 T-family)",
         not _registry_citation_problems([{"id": "D-9001", "decision": "see T-101"}],
                                         r"\bT-\d+\b", {"T-101"}, "task id")),
        ("a record that cites a PHANTOM task id fires (BUG-1108 T-family)",
         bool(_registry_citation_problems([{"id": "D-9001", "decision": "see T-999"}],
                                          r"\bT-\d+\b", {"T-101"}, "task id"))),
        ("a BUG- token never matches the T- grammar and vice versa (BUG-1108, no cross-family false positive)",
         not _registry_citation_problems([{"id": "D-9001", "decision": "see BUG-9001"}],
                                         r"\bT-\d+\b", {"T-101"}, "task id")),
    ]


def selftest() -> int:
    """Run the membership rail's known-answer controls; return 1 if any control did NOT fire."""
    rows = controls()
    for name, ok in rows:
        print(("  ok  " if ok else "  !!  ") + name)
    failed = [n for n, ok in rows if not ok]
    if failed:
        for name in failed:
            print("  FAIL selftest/" + control_slug(name))
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
    found = faults(named, records, pinned) + header_problems(log_path.read_text(encoding="utf-8"))
    if found:
        print("FAIL " + NAME + ": " + str(len(found)) + " fault(s):")
        for problem in found:
            print("  - " + problem)
        return 1
    absent = len(top - set(named))
    summary = ("ok " + NAME + ": " + str(len(named)) + " id(s) NAMED in " + str(block["log"]) + ", " + str(len(top))
               + " TOP-LEVEL record(s), " + str(len(pinned)) + " pinned legacy orphan(s), 0 fault(s); "
               + str(absent) + " record(s) carry no log entry (the log is a TIERED face of the registry - its own "
               "header - so that direction is DECLARED, never asserted)")
    # BUG-1108: the register's INTERNAL citation joins. The D- family is FATAL (report_only false, owner-ruled);
    # the BUG-/T- families are REPORT-ONLY (bug_task_report_only) until the owner rules their dangling set.
    citation = (yaml.safe_load(POLICY_YAML.read_text(encoding="utf-8")) or {}).get("citation") or {}
    cited = citation_problems(records, citation)
    if cited:
        report_only = bool(citation.get("report_only", True))
        label = "REPORT" if report_only else "FAIL"
        print(label + " " + NAME + " citation: " + str(len(cited)) + " dangling D-token(s) inside record fields:")
        for problem in cited:
            print("  - " + problem)
        if not report_only:
            return 1
        summary += "; " + str(len(cited)) + " dangling D-citation(s)"
    bug_task_report_only = bool(citation.get("bug_task_report_only", True))
    for family, fam_cited in (("BUG", bug_citation_problems(records, citation)),
                              ("T", task_citation_problems(records, citation))):
        if not fam_cited:
            continue
        label = "REPORT" if bug_task_report_only else "FAIL"
        print(label + " " + NAME + " " + family + " citation: " + str(len(fam_cited)) + " dangling " + family
              + "-token(s) inside record fields (report-only, owner-gated):")
        for problem in fam_cited:
            print("  - " + problem)
        if not bug_task_report_only:
            return 1
        summary += "; " + str(len(fam_cited)) + " dangling " + family + "-citation(s) REPORTED"
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

