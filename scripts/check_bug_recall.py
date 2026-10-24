#!/usr/bin/env python3
"""check_bug_recall.py — D-3047: THE REGISTER'S RECALL.

WHY THIS EXISTS (measured, not asserted). The bug register is this repository's memory of what went
wrong, and MEASURED 2026-10-16 it can answer only two questions: how many findings exist, and what
state each one is in. It cannot answer the three a LATER reader actually asks:

  (1) WHICH FINDINGS ARE CHRONIC — a heading EVENT is one AMENDMENT to one finding, never a recurrence.
      MEASURED: BUG-712 carries twelve headings because it took twelve sittings to characterise ONE
      defect ("MAGNITUDE CORRECTED", "ROOT CAUSE FOUND"), and BUG-736/737/748/749 carry five each. The
      register's own census face already counts them (`events`) and NOTHING read it. A finding that
      resists N sittings of attention is a worklist item that says "attention alone has not worked
      here" — a different debt from severity, and one no reading named.
  (2) WHICH CLOSED FINDINGS LEFT NO TRACE — a remedy that names no artifact, no ruling and no control is
      a fix a later reader cannot open, cannot re-run and cannot watch go red. That is the
      recurrence-prone set, and the register cannot see it.
  (3) WHICH FINDINGS ARE NEIGHBOURS OF A GIVEN ONE — THE RECALL STEP ITSELF. A finding arrives, and
      instead of re-deriving its history by reading a 1.6 MB log, the reader NAMES the findings that
      share a cited artifact or a cited ruling, the rulings that RESOLVE, and the RAILS that own the
      cited artifacts. MEASURED 2026-10-16: no artifact in this repository computed which findings share
      a shape; the hand-maintained recall map is a DOCUMENT, and BUG-846 already measured that a
      document is not a register. This reader is the derived form, so it cannot drift from the register.

WHAT IT IS NOT.
  * NOT a taxonomy. Nothing here decides what KIND of defect a finding is: that would be a semantic
    judgement, and BUG-852's lesson is that a CLASS must be MEASURED from the bytes, never asserted.
  * NOT a model. No LLM, no embedding, no similarity score. The ONLY relation it knows is a SHARED,
    RESOLVABLE REFERENCE — the repository's own currency (D-3034).
  * NOT a writer. It opens the register READ-ONLY and leaves no face: a reading that cannot be
    re-derived is a copy.
  * NOT a second parser. The fold of a heading into a status — fenced-block masking (BUG-634), the
    status slot, event order — is owned by ONE reader, loaded FROM ITS DECLARED HOME (D-2646). This
    rail adds only the SPANS and the TRACES, which nobody computed.

WHAT IT DECLARES (C12). Every path, pattern, threshold, ceiling and sample size lives in ONE declared
home. This module restates none of them and PROVES it by reading its own bytes (control 12).

EXIT: 0 every reading within its declared ceiling | 1 FATAL (an unreadable declaration, an absent key,
a pattern that does not compile, or a census face that disagrees with the register's own fold: a stale
face is a reading no later reader can trust) | 2 a class ABOVE its shrink-only ceiling — DEBT, loud and
NOT fatal (BUG-457), so the ladder keeps running and the debt gets a row instead of a shrug.
--selftest runs the known-answer controls on a FIXTURE register (writes nothing, reads no live state).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
CFG = REPO / "config" / "bug_recall.yaml"

RC_OK, RC_FATAL, RC_DEBT = 0, 1, 2

#: The known-answer controls, in the order they run. A control nothing runs is a comment (BUG-492), and
#: each is SEEN on a fixture that carries its defect AND on the fixture without it.
CONTROL_LABELS: tuple[str, ...] = (
    "a_closed_finding_that_names_no_trace_reads_UNTRACED",
    "a_closed_finding_that_names_a_control_or_a_ruling_is_NOT_untraced",
    "a_finding_whose_heading_events_reach_the_declared_threshold_reads_CHRONIC",
    "a_finding_below_the_declared_threshold_is_not_CHRONIC",
    "a_named_artifact_that_does_NOT_resolve_is_REPORTED_and_never_counted_as_a_trace",
    "a_named_ruling_the_declared_home_does_not_carry_is_REPORTED",
    "a_citation_to_a_sibling_finding_the_register_lacks_is_REPORTED",
    "recall_names_the_finding_that_shares_a_reference_and_never_a_stranger",
    "recall_joins_a_cited_artifact_to_the_capability_that_declares_it_owns",
    "a_debt_above_its_declared_ceiling_is_LOUD_and_NOT_fatal",
    "an_absent_declaration_key_is_FATAL_and_never_defaulted",
    "the_reader_names_no_declared_path_pattern_threshold_or_ceiling_of_its_own",
    "a_census_face_that_disagrees_with_the_register_fold_is_FATAL",
    "a_reference_cited_by_more_findings_than_the_declared_ceiling_is_EXCLUDED_and_COUNTED",
    "a_finding_related_ONLY_by_a_sibling_citation_is_not_a_neighbour",
    "a_neighbour_sharing_fewer_references_than_the_declared_minimum_is_not_a_relation",
    "a_decision_citation_resolves_regardless_of_the_hyphen_the_register_wrote",
)

class RecallError(SystemExit):
    """Fail-closed: an unreadable declaration is a fault, never a silent default (C16/C12)."""


def load(cfg: Path = CFG) -> dict[str, Any]:
    """Read the ONE declared home. Unreadable/unparseable is FATAL; nothing here is defaulted."""
    import yaml

    try:
        doc = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — any failure means this rail cannot know anything
        raise RecallError(f"FATAL: {cfg} cannot be read ({type(exc).__name__}: {exc})") from exc
    if not isinstance(doc, dict):
        raise RecallError(f"FATAL: {cfg} is not a mapping — there is no declaration to read")
    return doc


def declared(doc: dict[str, Any], *path: str) -> Any:
    """Fail-closed navigation of a key the DECLARATION owns: absent is a fault, never a code default."""
    node: Any = doc
    for part in path:
        if not isinstance(node, dict) or part not in node:
            raise RecallError(f"FATAL: {CFG.name}#{'.'.join(path)} is not declared — this rail restates "
                              f"no path, pattern, threshold or ceiling of its own, so an absent key is a "
                              f"fault (C12/C16)")
        node = node[part]
    return node


def load_parser(home: Path) -> Any:
    """Load the ONE folder of a heading event FROM ITS DECLARED HOME (D-2646: never re-implement)."""
    spec = importlib.util.spec_from_file_location("bug_recall_parser", home)
    if spec is None or spec.loader is None:
        raise RecallError(f"FATAL: the declared parser home {home} cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "scan"):
        raise RecallError(f"FATAL: the declared parser home {home} names no scan() — the fold of a "
                          f"heading into a status is owned by ONE reader and is never re-implemented here "
                          f"(D-2646)")
    return module


def compile_traces(doc: dict[str, Any]) -> list[tuple[str, bool, re.Pattern[str]]]:
    """Compile the DECLARED trace vocabulary. A pattern that does not compile is FATAL (C16)."""
    out: list[tuple[str, bool, re.Pattern[str]]] = []
    for name, spec in declared(doc, "traces").items():
        if not isinstance(spec, dict) or "pattern" not in spec or "must_resolve" not in spec:
            raise RecallError(f"FATAL: {CFG.name}#traces.{name} declares no pattern/must_resolve — an "
                              f"undeclared trace class is an assertion (C12)")
        try:
            out.append((str(name), bool(spec["must_resolve"]), re.compile(str(spec["pattern"]))))
        except re.error as exc:
            raise RecallError(f"FATAL: {CFG.name}#traces.{name}.pattern does not compile ({exc})") from exc
    if not out:
        raise RecallError(f"FATAL: {CFG.name}#traces is empty — there is no vocabulary to measure with")
    return out


def id_set(records: Any, field: str, pattern: re.Pattern[str]) -> set[str]:
    """The ids a declared home carries: a record whose declared field IS the reference (D-3034)."""
    found: set[str] = set()
    for rec in records if isinstance(records, list) else []:
        if isinstance(rec, dict) and field in rec:
            token = str(rec[field]).strip()
            if pattern.fullmatch(token):
                found.add(token)
    return found


def spans(bugs: dict[str, dict], n_lines: int) -> dict[str, tuple[int, int]]:
    """One body span per finding id: from its first heading to the next heading of ANY finding.

    The heading LINES come from the declared parser's own fold — this function computes arithmetic over
    them, never a second fold (D-2646)."""
    heads = sorted({int(ev["line"]) for rec in bugs.values() for ev in rec.get("events") or []})
    out: dict[str, tuple[int, int]] = {}
    for bid, rec in bugs.items():
        lines = [int(ev["line"]) for ev in rec.get("events") or []]
        start, last = min(lines), max(lines)
        after = [h for h in heads if h > last]
        out[bid] = (start, after[0] if after else n_lines + 1)
    return out


def canonical_id(token: str) -> str:
    """The DECISION id's canonical form: the hyphen is FORMATTING, never identity.

    The declared trace pattern `D-?\\d{3,4}` already treats the optional hyphen as ONE reference class,
    so a citation written `D-3047` and a ruling id written `D3047` are the SAME ruling (D-3034: the
    number IS the reference). The register and the ruling home drifted to two conventions, so comparison
    must fold the hyphen out on BOTH sides or the rail reports a ruling it actually carries as unresolved.
    """
    return token.replace("-", "").upper()


def extract(text: str, traces: list[tuple[str, bool, re.Pattern[str]]],
            resolvers: dict[str, Any]) -> tuple[dict[str, set[str]], list[tuple[str, str]]]:
    """The references a span NAMES, split into the ones that RESOLVE and the ones that do not.

    `must_resolve` is D-3034 applied to the register: a reference the reader cannot land inside is
    REPORTED, and it is never counted as a trace the fix left."""
    found: dict[str, set[str]] = {name: set() for name, _, _ in traces}
    unresolved: list[tuple[str, str]] = []
    for name, must_resolve, pattern in traces:
        for hit in pattern.findall(text):
            token = str(hit).strip()
            key = canonical_id(token) if name == "decision" else token
            if must_resolve and name in resolvers and not resolvers[name](key):
                unresolved.append((name, token))
                continue
            found[name].add(key)
    return found, unresolved


def capability_index(doc: dict[str, Any], repo: Path) -> dict[str, dict[str, str]]:
    """Which declared capability OWNS each path it names (read, never restated)."""
    caps = load_declared_yaml(doc, "capabilities", repo)
    index: dict[str, dict[str, str]] = {}
    for cap in caps.get("capabilities") or []:
        if not isinstance(cap, dict):
            continue
        for owned in cap.get("owns") or []:
            index.setdefault(str(owned), {"id": str(cap.get("id")), "check": str(cap.get("check") or ""),
                                          "entrypoint": str(cap.get("entrypoint") or "")})
    return index


def load_declared_yaml(doc: dict[str, Any], key: str, repo: Path) -> dict[str, Any]:
    """Read a declared YAML home. Unreadable is FATAL: a rail that cannot read its subject is red."""
    import yaml

    path = repo / str(declared(doc, "sources", key))
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise RecallError(f"FATAL: the declared home for {key} ({path}) cannot be read "
                          f"({type(exc).__name__}: {exc})") from exc
    if not isinstance(loaded, dict):
        raise RecallError(f"FATAL: the declared home for {key} ({path}) is not a mapping")
    return loaded


def cited_rulings(doc: dict[str, Any], repo: Path) -> dict[str, str]:
    """The ruling ids the declared home carries, with their titles. A ruling is read, never inferred."""
    rulings = load_declared_yaml(doc, "decisions", repo)
    list_key = str(declared(doc, "sources", "decisions_list_key"))
    id_field = str(declared(doc, "sources", "decisions_id_field"))
    out: dict[str, str] = {}
    for rec in rulings.get(list_key) or []:
        if isinstance(rec, dict) and id_field in rec:
            out[str(rec[id_field]).strip()] = str(rec.get("title") or "")[:120]
    if not out:
        raise RecallError(f"FATAL: {CFG.name}#sources.decisions names a home whose {list_key}[].{id_field} "
                          f"carries no ruling — a citation would resolve against nothing (C16)")
    return out


def measure(doc: dict[str, Any], *, register_lines: list[str] | None = None, repo: Path | None = None,
            rulings: dict[str, str] | None = None,
            caps: dict[str, dict[str, str]] | None = None,
            census: dict[str, Any] | None = None) -> dict[str, Any]:
    """The three readings plus everything the recall step needs. ONE code path for the fixture and the
    live register, so a control exercises the code the ladder runs."""
    repo = repo or REPO
    live = register_lines is None
    if register_lines is None:
        register_lines = (repo / str(declared(doc, "sources", "register"))).read_text(
            encoding="utf-8").splitlines()
    parser = load_parser(repo / str(declared(doc, "sources", "parser_home")))
    bugs: dict[str, dict] = parser.scan(register_lines)
    if not bugs:
        raise RecallError("FATAL: the declared register folded to ZERO findings — an empty register is "
                          "not a green one (D-795)")
    rulings = rulings if rulings is not None else cited_rulings(doc, repo)
    rulings = {canonical_id(k): v for k, v in rulings.items()}
    traces = compile_traces(doc)
    decision_pattern = next((p for n, _, p in traces if n == "decision"), None)
    if decision_pattern is None:
        raise RecallError(f"FATAL: {CFG.name}#traces declares no decision class — a ruling registry "
                          f"cannot be resolved against nothing")
    findings = set(bugs)
    art_root = repo / str(declared(doc, "sources", "artifact_root"))
    resolvers: dict[str, Any] = {
        "artifact": lambda ref: (art_root / ref).exists(),
        "decision": lambda ref: ref in rulings,
        "finding": lambda ref: ref in findings,
    }
    span = spans(bugs, len(register_lines))
    traces_by_bug: dict[str, dict[str, set[str]]] = {}
    unresolved_by_bug: dict[str, list[tuple[str, str]]] = {}
    for bid, (start, end) in span.items():
        text = "\n".join(register_lines[start - 1:end - 1])
        found, unresolved = extract(text, traces, resolvers)
        traces_by_bug[bid] = found
        unresolved_by_bug[bid] = unresolved
    keeps_a_trace = {str(n) for n in declared(doc, "trace_sufficiency",
                                              "traces_that_make_a_closed_finding_TRACED")}
    relation_ceiling = int(declared(doc, "report", "max_reference_frequency"))
    frequency: dict[tuple[str, str], int] = {}
    for found in traces_by_bug.values():
        for name, refs in found.items():
            for ref in refs:
                frequency[(name, ref)] = frequency.get((name, ref), 0) + 1
    common = {pair for pair, seen in frequency.items() if seen > relation_ceiling}
    chronic_at = int(declared(doc, "thresholds", "chronic_events"))
    counts = {
        "closed_findings_with_no_trace": sorted(
            bid for bid, rec in bugs.items()
            if rec["status"] == "closed" and not any(traces_by_bug[bid].get(k) for k in keeps_a_trace)),
        "open_findings_at_or_above_chronic_events": sorted(
            (bid for bid, rec in bugs.items()
             if rec["status"] == "open" and len(rec.get("events") or []) >= chronic_at),
            key=lambda b: (-len(bugs[b]["events"]), b)),
        "cited_references_that_do_not_resolve": sorted(
            {f"{k}:{v}" for pairs in unresolved_by_bug.values() for k, v in pairs}),
    }
    disagreements: list[str] = []
    if bool(declared(doc, "sources", "agreement_is_checked")) and (live or census is not None):
        if census is None:
            census_home = repo / str(declared(doc, "sources", "census"))
            try:
                census = json.loads(census_home.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                raise RecallError(f"FATAL: the declared census face {census_home} cannot be read "
                                  f"({type(exc).__name__}: {exc})") from exc
        live_open = sum(1 for rec in bugs.values() if rec["status"] == "open")
        if int(census.get("total_ids", -1)) != len(bugs) or int(census.get("open_n", -1)) != live_open:
            disagreements.append(
                f"the census face says {census.get('total_ids')} ids / {census.get('open_n')} open, the "
                f"register's own fold says {len(bugs)} / {live_open} — the face is STALE")
    return {"bugs": bugs, "spans": span, "traces": traces_by_bug, "unresolved": unresolved_by_bug,
            "counts": counts, "disagreements": disagreements, "rulings": rulings,
            "caps": caps if caps is not None else capability_index(doc, repo),
            "keeps_a_trace": keeps_a_trace, "chronic_at": chronic_at, "common": common,
            "frequency": frequency}


def recall_lines(bug_id: str, m: dict[str, Any], doc: dict[str, Any]) -> list[str]:
    """THE RECALL STEP. Name the finding's neighbours, the rulings it cites that RESOLVE, and the rails
    that own the artifacts it names — so a new act starts from this register instead of re-deriving it."""
    bugs, traces = m["bugs"], m["traces"]
    if bug_id not in traces:
        return [f"  {bug_id}: the register carries no such finding"]
    rec = bugs[bug_id]
    common = m["common"]
    relation_classes = {str(n) for n in declared(doc, "report", "relation_classes")}

    def own(t: dict[str, set[str]]) -> dict[str, set[str]]:
        """A finding's references with the COMMON substrate removed: a shared config file is furniture."""
        kept = {n: {r for r in rs if (n, r) not in common} for n, rs in t.items()
                if n != "control" and n in relation_classes}
        return {n: rs for n, rs in kept.items() if rs}

    mine = own(traces[bug_id])
    lines = [f"  {bug_id} [{rec['status']}, {len(rec.get('events') or [])} heading event(s)] "
             f"{str(rec.get('title') or '')[:100]}"]
    min_shared = int(declared(doc, "report", "min_shared_references"))
    neighbours: list[tuple[float, int, int, str, dict[str, list[str]]]] = []
    thin = 0
    mine_n = sum(len(v) for v in mine.values())
    for other, theirs in traces.items():
        if other == bug_id:
            continue
        their = own(theirs)
        shared = {n: sorted(refs & their[n]) for n, refs in mine.items() if n in their and refs & their[n]}
        if not shared:
            continue
        overlap = sum(len(v) for v in shared.values())
        if overlap < min_shared:
            thin += 1
            continue
        their_n = sum(len(v) for v in their.values())
        neighbours.append((overlap / (min(mine_n, their_n) or 1), their_n, overlap, other, shared))
    #: Strength first, then SPECIFICITY: among equally strong neighbours the SMALLER finding is named
    #: first, because a finding whose references are almost all shared with this one is a sub-finding of
    #: it, while another mega-entry is only a sibling in size. Declared in the home (report.why_the_relation).
    neighbours.sort(key=lambda t: (-t[0], t[1], t[3]))
    sample = int(declared(doc, "report", "sample_n"))
    per = int(declared(doc, "report", "refs_per_neighbour"))
    excluded = sorted({f"{n}:{r}" for n, r in common if n != "control"})
    lines.append(f"  SHARED HISTORY — {len(neighbours)} finding(s) share a RARE reference with it, "
                 f"ranked by STRENGTH (shared references over the SMALLER finding's own set). "
                 f"{len(excluded)} reference(s) are cited by more findings than the declared ceiling and "
                 f"are excluded as COMMON substrate, and {thin} finding(s) share fewer references than the "
                 f"declared minimum and are excluded as coincidence - both printed here rather than "
                 f"dropped silently:")
    for strength, _, _, other, shared in neighbours[:sample]:
        parts = []
        for name, refs in sorted(shared.items()):
            more = f" (+{len(refs) - per} more)" if len(refs) > per else ""
            parts.append(f"{name}={','.join(refs[:per])}{more}")
        lines.append(f"    {strength:5.0%}  {other} [{bugs[other]['status']}] via " + ", ".join(parts))
    if not mine:
        lines.append("    (this finding names ONLY references that are common substrate — it has no RARE "
                     "reference to relate on, which is a reading about the finding, not the register)")
    rulings = sorted(ref for ref in traces[bug_id].get("decision", set()) if ref in m["rulings"])
    lines.append(f"  RULINGS IT CITES THAT RESOLVE — {len(rulings)}:")
    for ref in rulings:
        lines.append(f"    {ref}: {m['rulings'][ref]}")
    lines.append("  THE RAILS THAT OWN WHAT IT NAMES (the capability a fix can be routed to):")
    owned = 0
    for ref in sorted(traces[bug_id].get("artifact", set())):
        cap = m["caps"].get(ref)
        if cap:
            owned += 1
            lines.append(f"    {ref} -> {cap['id']}  check: {cap['check'] or cap['entrypoint']}")
    if not owned:
        lines.append("    (none: the artifacts this finding names are owned by no declared capability — "
                     "the route graph has a route for them or it does not)")
    for kind, ref in m["unresolved"].get(bug_id, []):
        lines.append(f"    CITED BUT UNRESOLVED ({kind}): {ref} — a reference that lands inside nothing "
                     f"(D-3034), reported and never counted as a trace")
    return lines


def render(m: dict[str, Any], doc: dict[str, Any]) -> tuple[list[str], int]:
    """The live reading. A class ABOVE its declared ceiling is DEBT — loud, never fatal (BUG-457)."""
    counts = m["counts"]
    mapping = {"untraced_closed": "closed_findings_with_no_trace",
               "chronic_open": "open_findings_at_or_above_chronic_events",
               "unresolved_reference": "cited_references_that_do_not_resolve"}
    classes = declared(doc, "ceilings", "classes")
    sample = int(declared(doc, "report", "sample_n"))
    bugs = m["bugs"]
    lines = [f"bug-recall: {len(bugs)} finding(s) | {sum(1 for r in bugs.values() if r['status'] == 'open')} "
             f"open | {sum(1 for r in bugs.values() if r['status'] == 'closed')} closed "
             f"(fold of the declared register, joined to the census face)"]
    debt = 0
    for name in classes:
        count = len(counts[mapping[name]])
        ceiling = int(declared(doc, "ceilings", "classes", name, "ceiling"))
        verdict = "above its ceiling — DEBT" if count > ceiling else "within its ceiling"
        lines.append(f"  {name}: {count} {verdict} (ceiling {ceiling}, "
                     f"row {declared(doc, 'ceilings', 'classes', name, 'row')})")
        lines += [f"    {bid}" for bid in counts[mapping[name]][:sample]]
        if count > ceiling:
            debt = RC_DEBT
    for line in m["disagreements"]:
        lines.append(f"  !! {line}")
    if m["disagreements"]:
        return lines, RC_FATAL
    return lines, debt


def code_only(text: str) -> str:
    """The file's CODE with prose blanked, line numbers preserved (the D-3046 idiom): a citation belongs
    in prose and a VALUE belongs in the declaration, so this control is a statement about code."""
    blanked = re.sub(r'"""(?:.|\n)*?"""', lambda mm: re.sub(r"[^\n]", " ", mm.group(0)), text)
    return _blank_comments(blanked)


def _blank_comments(text: str) -> str:
    """Blank a comment with spaces, preserving every byte position and line break."""
    return re.sub(r"(?m)#.*$", lambda mm: " " * len(mm.group(0)), text)


def selftest() -> int:
    """The known-answer controls, on a FIXTURE register. Both directions: each defect is SEEN, and its
    absence is SEEN to be green (BUG-492)."""
    fixture_doc = load()
    #: The relation's declared ceiling is TIGHTENED for the fixture so the exclusion is exercised with
    #: three findings instead of twenty-one: the rule under test is "more than the ceiling", not the
    #: number the live register happens to need.
    fixture_doc["report"]["max_reference_frequency"] = 2
    fixture_rulings = {"D-3047": "the register's recall is declared", "D-2646": "never re-implement a reader"}
    fixture_register = [
        "# FIXTURE — a register carrying every defect this rail claims to catch",
        "## BUG-001 (MED - FIXED 2026-01-01) - closed, and it names scripts/run_ladder.py, pipeline/harness_env.py and D-3047",
        "## BUG-002 (MED - FIXED 2026-01-02) - closed and names nothing at all",
        "## BUG-003 (MED - OPEN 2026-01-03) - chronic, first amendment",
        "## BUG-003 (MED - OPEN 2026-01-04) - chronic, second amendment",
        "## BUG-003 (MED - OPEN 2026-01-05) - chronic, third amendment",
        "## BUG-004 (MED - OPEN 2026-01-06) - quiet, one heading only",
        "## BUG-005 (MED - FIXED 2026-01-07) - cites scripts/nowhere_at_all_xyz.py and D-9999 and BUG-999",
        "## BUG-006 (MED - OPEN 2026-01-08) - names scripts/run_ladder.py AND pipeline/harness_env.py: BUG-001's neighbour",
        "## BUG-007 (MED - OPEN 2026-01-09) - names config/bug_recall.yaml, which three findings cite",
        "## BUG-008 (MED - OPEN 2026-01-10) - also names config/bug_recall.yaml, so it is COMMON substrate",
        "## BUG-009 (MED - OPEN 2026-01-11) - a third citation of config/bug_recall.yaml, making it common",
        "## BUG-010 (MED - OPEN 2026-01-12) - related to BUG-001 only by MENTIONING it, never by a subject",
        "## BUG-011 (MED - OPEN 2026-01-13) - shares ONE rare reference with BUG-006: coincidence, not a relation",
    ]
    fixture_caps = {"scripts/run_ladder.py": {"id": "ladder", "check": "python3 scripts/run_ladder.py "
                                                                        "--receipt-check", "entrypoint": ""}}
    m = measure(fixture_doc, register_lines=fixture_register, rulings=fixture_rulings, caps=fixture_caps)
    counts = m["counts"]
    results: list[tuple[str, int, int]] = []

    def check(label: str, got: Any, want: Any) -> None:
        results.append((label, int(got == want), 1))

    untraced = counts["closed_findings_with_no_trace"]
    check(CONTROL_LABELS[0], "BUG-002" in untraced, True)
    check(CONTROL_LABELS[1], "BUG-001" in untraced, False)
    check(CONTROL_LABELS[2], "BUG-003" in counts["open_findings_at_or_above_chronic_events"], True)
    check(CONTROL_LABELS[3], "BUG-004" in counts["open_findings_at_or_above_chronic_events"], False)
    check(CONTROL_LABELS[4], "artifact:scripts/nowhere_at_all_xyz.py" in counts["cited_references_that_do_not_resolve"], True)
    check(CONTROL_LABELS[4] + "_and_it_is_not_a_trace", "BUG-005" in untraced, True)
    check(CONTROL_LABELS[5], "decision:D-9999" in counts["cited_references_that_do_not_resolve"], True)
    check(CONTROL_LABELS[6], "finding:BUG-999" in counts["cited_references_that_do_not_resolve"], True)
    named = "\n".join(recall_lines("BUG-006", m, fixture_doc))
    check(CONTROL_LABELS[7], "BUG-001" in named and "BUG-004" not in named and "BUG-002" not in named, True)
    check(CONTROL_LABELS[8], "scripts/run_ladder.py -> ladder" in named, True)
    loud_doc = load()
    loud_doc["ceilings"]["classes"] = {k: dict(v, ceiling=0) for k, v in
                                       declared(loud_doc, "ceilings", "classes").items()}
    _, rc_debt = render(m, loud_doc)
    check(CONTROL_LABELS[9], rc_debt, RC_DEBT)
    absent = load()
    absent.pop("thresholds", None)
    try:
        declared(absent, "thresholds", "chronic_events")
        fatal = False
    except RecallError:
        fatal = True
    check(CONTROL_LABELS[10], fatal, True)
    own = code_only(Path(__file__).read_text(encoding="utf-8"))
    leaked = [str(declared(fixture_doc, "sources", k)) for k in
              ("register", "census", "parser_home", "decisions", "capabilities")]
    leaked += [str(spec["pattern"]) for spec in declared(fixture_doc, "traces").values()]
    check(CONTROL_LABELS[11], [tok for tok in leaked if tok in own], [])
    stale = measure(fixture_doc, register_lines=fixture_register, rulings=fixture_rulings,
                    caps=fixture_caps, census={"total_ids": 999, "open_n": 0})
    fresh = measure(fixture_doc, register_lines=fixture_register, rulings=fixture_rulings,
                    caps=fixture_caps, census={"total_ids": 11, "open_n": 8})
    check(CONTROL_LABELS[12], render(stale, fixture_doc)[1], RC_FATAL)
    check(CONTROL_LABELS[12] + "_and_a_matching_face_is_NOT", render(fresh, fixture_doc)[1] != RC_FATAL, True)
    from_common = "\n".join(recall_lines("BUG-007", m, fixture_doc))
    check(CONTROL_LABELS[13], ("artifact", "config/bug_recall.yaml") in m["common"], True)
    check(CONTROL_LABELS[13] + "_and_the_excluded_reference_breaks_no_relation",
          "BUG-008" in from_common or "BUG-009" in from_common, False)
    check(CONTROL_LABELS[13] + "_and_the_exclusion_is_PRINTED", "COMMON substrate" in from_common, True)
    mentions_only = "\n".join(recall_lines("BUG-001", m, fixture_doc))
    check(CONTROL_LABELS[14], "BUG-010" in mentions_only, False)
    thin_only = "\n".join(recall_lines("BUG-006", m, fixture_doc))
    check(CONTROL_LABELS[15], "BUG-001" in thin_only and "BUG-011" not in thin_only, True)
    #: The DECISION id's hyphen is FORMATTING, not identity (the declared trace pattern is `D-?`, so both
    #: forms are ONE reference): a no-hyphen citation must resolve against a hyphenated ruling id.
    check(CONTROL_LABELS[16], canonical_id("D-3047"), canonical_id("D3047"))
    norm = measure(fixture_doc, register_lines=["## BUG-050 (MED - FIXED 2026-01-01) - cites D3047 and D-9999"],
                   rulings=fixture_rulings, caps=fixture_caps)
    check(CONTROL_LABELS[16] + "_and_the_resolver_folds_the_hyphen",
          "decision:D3047" in norm["counts"]["cited_references_that_do_not_resolve"], False)

    failed = 0
    for label, ok, _total in results:
        if ok:
            print(f"ok   {label}")
        else:
            failed += 1
            print(f"FAIL {label}")
    print(f"selftest: {len(results) - failed}/{len(results)}")
    return 1 if failed else 0


def main() -> int:
    """One declared home, three readings, one recall. READ-ONLY: this rail never writes the register."""
    ap = argparse.ArgumentParser(description="D-3047: the bug register's RECALL - chronic, untraced, "
                                             "unresolved, and the neighbours of a finding.")
    ap.add_argument("--recall", metavar="BUG-NNN", help="the RETRIEVE step: name this finding's "
                                                        "neighbours, its resolving rulings and the rails "
                                                        "that own what it cites")
    ap.add_argument("--measure", action="store_true",
                    help="print the three counts and IGNORE the ceilings - the ONE mode that does, used "
                         "when a ceiling is being SET from a reading, never to excuse one")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls on a FIXTURE register")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    doc = load()
    try:
        m = measure(doc)
        if args.recall:
            print("\n".join(recall_lines(args.recall, m, doc)))
            return RC_OK
        lines, rc = render(m, doc)
        if args.measure:
            counts = m["counts"]
            lines.append("  MEASURE (ceilings ignored): " + " | ".join(
                f"{k}={len(v)}" for k, v in counts.items()))
            rc = RC_OK
    except RecallError as exc:
        print(str(exc))
        return RC_FATAL
    print("\n".join(lines))
    if rc == RC_DEBT:
        print("OWNER-OWED: a class is ABOVE its shrink-only ceiling. The count IS the debt — declare the "
              "route for an item, or lower the ceiling with a reading. Never raise it (D-3023/D-2644).")
    return rc


if __name__ == "__main__":
    sys.exit(main())
