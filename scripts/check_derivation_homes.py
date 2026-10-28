#!/usr/bin/env python3
"""check_derivation_homes.py - ONE DERIVED VALUE, ONE HOME (D-2646; the BUG-499/BUG-502 class).

WHY. BUG-499 had the label rule VERBATIM IN THREE PLACES and BUG-502 had one rule in two scripts, with nothing
reporting divergence: two copies of one rule are two truths waiting to disagree, and the divergence surfaces as
an unexplainable stored value, never as an error. config/derivations.yaml declares each derived value with its
home; this rail JOINS that declaration to reality on every run.

WHAT IT CHECKS (the population is every row of config/derivations.yaml):
  1. a row declares a name, declares it ONCE, and carries a status from the CLOSED vocabulary below;
  2. a row with a home ("file::func") cites a module under the declared scan roots that DEFINES that function at
     module level, and NO OTHER module defines a function of that name - a rival implementation is the defect
     this registry exists to find;
  3. a row with home null declares a no-home status, and a module-level definition named after the row's last
     segment is DRIFT: home null states "no code decides this", so a writer appearing while the row says nobody
     decides it must fail loudly rather than quietly;
  4. a row's COORDINATE (`table:` + `column:`, the claim about WHERE the value lives) RESOLVES to the census home
     that config/derivations.yaml#coordinate_homes declares for that table (D-2661, the BUG-553 class: two fields of
     every row were read by NO rail, so a row could cite a coordinate that exists nowhere and still print ok). The
     two kinds are machine-distinct - a document coordinate must exist, parse, carry the column as a top-level key
     and name an existing producer; a store coordinate is DELEGATED to its declared column census, whose declared
     table must match, whose rail must exist, and whose membership map must carry the column.
  5. a row's PARITY RAIL (the claim about WHAT RE-DERIVES the value) RESOLVES too (D-2662, the BUG-553 class a
     THIRD time - the field was read by no machine either): the named script must EXIST, and the DECLARED ladder
     must INVOKE it, because a rail nothing runs protects nothing (the BUG-508/BUG-510 class) and a mention inside
     a comment is not a run. A row claiming status 'homed' may NOT leave it null: 'homed' is the strongest status
     the vocabulary has, and a home with nothing that re-proves it against the store is a mismatch INSIDE ONE
     RECORD (the BUG-550 class). The null case is joined to the row's OWN status - two fields of one record - so
     the three declared-defective rows keep their null legally and a new homed row cannot.
SCOPE (stated, because an unstated scope reads as coverage): this rail does NOT prove the home is the only
WRITER of the stored value, and it does NOT re-derive any value - it proves that each row's parity rail EXISTS and
that the declared ladder RUNS it; comparing re-derived bytes against the stored corpus is that rail's own job. It
does not measure the STORE either: it proves the ONE-HOME property, coordinate EXISTENCE + MEMBERSHIP (delegated)
and parity EXISTENCE + INVOCATION. It NEVER
opens the store: the store carries a vec0 virtual table, so a store open here would raise `no such module: vec0`
and kill the rail on its first run. VALUE parity is never this rail's job.

TRI-STATE (BUG-457): 0 clean | 1 drift | 2 owner-owed (non-homed rows BELOW the declared shrink-only ceiling).
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any, Callable

import yaml

ROOT = Path(__file__).resolve().parent.parent
PREFIX = "check-derivation-homes"
REGISTRY = ROOT / "config" / "derivations.yaml"
EXIT_CLEAN, EXIT_DRIFT, EXIT_OWED = 0, 1, 2
STATUSES: tuple[str, ...] = ("homed", "orphan_magic_threshold", "dead_but_read", "declared_but_empty")
NO_HOME_STATUSES: tuple[str, ...] = ("dead_but_read", "declared_but_empty")
# D-2661: the CLOSED vocabulary of coordinate kinds. Each kind is a distinct MACHINE rule, never a label (BUG-492);
# an unknown kind fails CLOSED, because a kind nobody implements is a coordinate nobody reads.
COORDINATE_KINDS: tuple[str, ...] = ("document", "store_census")
# D-2662: the ONE status that CLAIMS the value has a working home. A row carrying it with no parity rail states a
# home and names nothing that re-proves it against the store, which is a mismatch INSIDE ONE RECORD (BUG-550), so it
# is FATAL rather than unexamined. The other statuses already declare a defect; their null repeats that statement,
# and joining the two fields of the row is what makes the repetition checkable instead of assumed.
HOMED_STATUS = "homed"


def load_yaml(path: Path) -> dict:
    """Parse a YAML document, or fail loudly - a registry nobody can parse decides nothing."""
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def declared(doc: dict, key: str, where: str) -> Any:
    """FAIL CLOSED: an absent declaration is the error, never a default (D-2644)."""
    if key not in doc:
        raise SystemExit("FAIL " + PREFIX + ": " + where + " declares no " + repr(key)
                         + " - a registry read with a code default is the defect this rail measures")
    return doc[key]


def module_defs(source: str) -> set[str]:
    """Every MODULE-LEVEL function name: a home is a module-level definition, not a nested helper."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    return {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def rivals(name: str, sources: dict[str, str]) -> list[str]:
    """Every module defining `name` at module level: more than one is a SECOND TRUTH (BUG-502)."""
    return sorted(rel for rel, src in sources.items() if name in module_defs(src))


def sources_under(roots: list[str]) -> dict[str, str]:
    """Read every module under the declared scan roots; a root that is not a directory is drift (C16)."""
    out: dict[str, str] = {}
    for rel in roots:
        d = ROOT / str(rel)
        if not d.is_dir():
            raise SystemExit("FAIL " + PREFIX + ": scan_roots names " + str(rel) + ", which is not a directory - a "
                             "scan root that silently does not exist narrows the join and still prints ok (C16)")
        for path in sorted(d.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            rel = path.relative_to(ROOT).as_posix()
            try:
                out[rel] = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                # D-2646/D-2442: SOURCE text is UTF-8 by contract (the interpreter and ruff both require it), so
                # this read is STRICT like its sibling `load_artifact` below - the rail that decides whether silent
                # repairs are allowed may not itself repair a byte. It paid the class, not the instance: a named
                # refusal instead of `errors="replace"`, because a repaired byte could hide a rival definition and
                # a bare UnicodeDecodeError would name no artifact (C16).
                raise SystemExit("FAIL " + PREFIX + ": " + rel + " is not valid UTF-8 (first bad byte at offset "
                                 + str(exc.start) + ") - source text is UTF-8 by contract, and this rail may not "
                                 "read it through a repair (D-2646: the one decode home is "
                                 "scripts/lib/artifact_encoding.py)") from exc
    return out


def load_artifact(rel: str) -> tuple[str, Any]:
    """(state, parsed) for a cited coordinate artifact: missing | unparsable | ok - unreadable is NOT clean (C16).

    The text is read STRICTLY, with no `errors=` argument, and that omission is the point: a silent repair inside
    the rail that decides whether silent repairs are allowed would be this class eating itself, and the sibling
    register keys this file's ONE remaining repair site by CONTENT precisely because a second such call would be a
    second truth. An unreadable byte is a STATE this function reports, never a byte it repairs.
    """
    path = ROOT / rel
    if not path.is_file():
        return "missing", None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return "unparsable", None
    try:
        return "ok", json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
    except (ValueError, yaml.YAMLError):
        return "unparsable", None


def load_text(rel: str) -> tuple[str, str]:
    """(state, text) for a cited NON-YAML artifact: missing | unreadable | ok - unreadable is not clean (C16).

    Read STRICTLY, with no errors= argument, for the same reason load_artifact is: a rail that audits silent
    repairs may not perform one. The except clause RETURNS A STATE - nothing is repaired and nothing is swallowed.
    """
    path = ROOT / rel
    if not path.is_file():
        return "missing", ""
    try:
        return "ok", path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return "unreadable", ""


def member_map(doc: dict, dotted: str) -> dict | None:
    """Resolve a DECLARED dotted key path inside a census document; an absent path is None, never a default (D-2644).

    Returned as None rather than {} so the caller can tell "the census does not carry that block" from "the block is
    empty": the first is a broken declaration, the second is a census that measures nothing.
    """
    node: Any = doc
    for part in str(dotted).split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, dict) else None


def ladder_invokes(text: str, script: str) -> bool:
    """True iff a ladder RECIPE LINE actually INVOKES script (D-2662).

    A mention inside a comment is not a run (BUG-492: a kind is a rule, not a label), so the comment half of each
    line is dropped first; an @-prefixed recipe line executes the very same command, so the prefix is stripped. The
    path must be a WHOLE TOKEN: a substring test would read scripts/x.py.bak as scripts/x.py (the BUG-528 class,
    where one path reads as another).
    """
    for raw in text.splitlines():
        code = raw.split("#", 1)[0].replace("@", " ")
        tokens = code.split()
        if tokens and tokens[0] in ("python3", "python") and script in tokens:
            return True
    return False


def parity_problems(name: str, row: dict, status: str, ladder: tuple[str, str], ladder_rel: str) -> list[str]:
    """Join ONE row's declared parity_rail to reality: EXISTENCE + INVOCATION, joined to its OWN status (D-2662).

    VALUE parity is not this rail's job: comparing re-derived bytes against the stored corpus is the parity rail's
    own measurement. This proves the machine is there AND that the ladder runs it, and it joins the null case to the
    row's own status rather than demanding a rail the row's other field contradicts.
    """
    rail = str(row.get("parity_rail") or "").strip()
    if not rail:
        if status == HOMED_STATUS:
            return [name + ": claims status " + repr(HOMED_STATUS) + " while declaring parity_rail null - a homed "
                    "value with nothing that re-derives it is a mismatch INSIDE ONE RECORD (the BUG-550 class): the "
                    "row states the value has ONE home and no machine re-proves it against the store. Name the rail "
                    "that re-derives it, or stop claiming it is homed (D-2662)."]
        return []
    state, text = ladder
    if state != "ok":
        return [name + ": declares parity_rail " + rail + " but the DECLARED ladder " + ladder_rel + " is " + state
                + " - whether that rail ever runs cannot be established, and an unreadable ladder is not clean (C16)"]
    found: list[str] = []
    if not (ROOT / rail).is_file():
        found.append(name + ": declares parity_rail " + rail + ", which does NOT exist - the row claims a "
                     "re-derivation that no file performs (a rail is a path before it is a promise)")
    elif not ladder_invokes(text, rail):
        found.append(name + ": parity_rail " + rail + " exists but " + ladder_rel + " never INVOKES it (a mention "
                     "inside a comment is not a run) - a rail nothing runs protects nothing (the BUG-508/BUG-510 "
                     "class), so the row's re-derivation is a claim, not a machine")
    return found


def coordinate_problems(name: str, row: dict, homes: dict,
                        load: Callable[[str], tuple[str, Any]]) -> list[str]:
    """Join ONE row's cited `table:`/`column:` to the census home declared for that table (D-2661).

    Existence + membership, delegated, never value. `load` is injected so the known-answer controls can drive every
    arm (missing / unparsable / present) without a fixture on disk - a detector nobody has seen fire is a comment.
    """
    table = str(row.get("table") or "").strip()
    column = str(row.get("column") or "").strip()
    if not table or not column:
        return [name + ": declares table " + repr(table) + " and column " + repr(column) + " - a row whose "
                "coordinate is unnamed cannot be joined to anything, and an unjoined claim is the BUG-553 shape"]
    entry = homes.get(table)
    if not isinstance(entry, dict):
        return [name + ": cites table " + repr(table) + " but config/derivations.yaml#coordinate_homes declares no "
                "census home for it - the coordinate is UNVERIFIABLE, and a claim no machine reads is the defect "
                "(D-2661). Declare its census home, or stop citing the coordinate."]
    kind = str(entry.get("kind") or "").strip()
    if kind not in COORDINATE_KINDS:
        return [name + ": coordinate_homes." + table + " declares kind " + repr(kind) + " which is not one of "
                + str(list(COORDINATE_KINDS)) + " - an unknown kind is read as no kind at all, so it fails CLOSED "
                "(C16) instead of passing as unexamined"]
    if kind == "document":
        state, doc = load(table)
        if state == "missing":
            return [name + ": cites the document coordinate " + table + ", which does NOT exist under the repo "
                    "root - a coordinate is a claim about the tree at the moment the rail runs"]
        if state != "ok" or not isinstance(doc, dict):
            return [name + ": the document coordinate " + table + " does not read as a mapping, so membership of "
                    + repr(column) + " cannot be established - unreadable is not clean (C16)"]
        found: list[str] = []
        if column not in doc:
            found.append(name + ": " + table + " carries no top-level key " + repr(column) + " - the row cites a "
                         "coordinate the document does not have (top-level keys: "
                         + ", ".join(sorted(str(k) for k in doc)[:12]) + ")")
        key = str(entry.get("producer_key") or "").strip()
        if not key:
            found.append(name + ": coordinate_homes." + table + " declares kind document but names no "
                         "producer_key - a coordinate whose producer is unnamed is a fact nobody owns (D-2649)")
        else:
            producer = str(doc.get(key) or "").strip()
            if not producer:
                found.append(name + ": " + table + " carries no " + key + " - the document does not name who "
                             "writes it, so the coordinate has no home on the writing side either")
            elif not (ROOT / producer).exists():
                found.append(name + ": " + table + "#" + key + " names " + producer + ", which does not exist - "
                             "the document's own declared producer is a claim about the tree")
        return found
    census_rel = str(entry.get("census") or "").strip()
    if not census_rel:
        return [name + ": coordinate_homes." + table + " declares kind store_census but names no census - the "
                "column question then has no home to DELEGATE to, and re-measuring it here would be the "
                "second-census defect (D-2646)"]
    state, census = load(census_rel)
    if state == "missing":
        return [name + ": the declared column census " + census_rel + " for table " + repr(table) + " does NOT "
                "exist - the delegation target is a path nothing holds"]
    if state != "ok" or not isinstance(census, dict):
        return [name + ": the declared column census " + census_rel + " does not read as a mapping - the "
                "coordinate's home exists and cannot be read, which is DRIFT, not a pass (C16)"]
    rail = str(census.get("rail") or "").strip()
    found = []
    if not rail:
        found.append(name + ": " + census_rel + " names no rail - a census with no machine is a comment (BUG-492)")
    elif not (ROOT / rail).exists():
        found.append(name + ": " + census_rel + " names rail " + rail + ", which does not exist - the delegation "
                     "target has no machine behind it")
    declared_table = str(census.get("table") or "").strip()
    if declared_table != table:
        found.append(name + ": cites table " + repr(table) + " while its declared census " + census_rel
                     + " measures table " + repr(declared_table) + " - delegating to a census of a DIFFERENT table "
                     "proves nothing about this coordinate")
        return found
    membership = str(entry.get("membership") or "").strip()
    if not membership:
        return found + [name + ": coordinate_homes." + table + " declares no membership path - which key of the "
                        "census lists the measured columns is a DECLARATION, never a code default (D-2644)"]
    measured = member_map(census, membership)
    if measured is None:
        return found + [name + ": " + census_rel + " carries no " + membership + " mapping - the declared "
                        "membership path does not resolve, so membership cannot be established (fails CLOSED)"]
    if column not in measured:
        found.append(name + ": column " + repr(column) + " is absent from " + census_rel + "#" + membership
                     + " (" + str(len(measured)) + " column(s) measured) - the coordinate's OWN census is blind to "
                     "it, so the row cites a column no machine has measured")
    return found


def check_rows(rows: list[dict], sources: dict[str, str], homes: dict,
               load: Callable[[str], tuple[str, Any]], ladder: tuple[str, str],
               ladder_rel: str) -> tuple[list[str], int]:
    """Join every row to reality: its HOME, its COORDINATE (D-2661) and its PARITY RAIL (D-2662)."""
    problems: list[str] = []
    non_homed = 0
    seen: set[str] = set()
    for row in rows:
        name = str(row.get("name") or "").strip()
        status = str(row.get("status") or "").strip()
        home = row.get("home")
        if not name:
            problems.append("a row declares no name - an unnamed derivation cannot be joined to anything")
            continue
        if name in seen:
            problems.append(name + ": declared TWICE - one derived value, ONE row (D-2646)")
        seen.add(name)
        if status not in STATUSES:
            problems.append(name + ": status " + repr(status) + " is not in the CLOSED vocabulary "
                            + str(list(STATUSES)) + " - an unclassified row is not a declaration")
            continue
        if home:
            rel, _, func = str(home).partition("::")
            if rel not in sources:
                problems.append(name + ": home " + rel + " is not a module under the declared scan roots")
            elif not func:
                problems.append(name + ": home names a file but no function - a file is not a home")
            elif func not in module_defs(sources[rel]):
                problems.append(name + ": " + rel + " does not define " + func + " at module level - the registry "
                                "cites a home that does not exist")
            else:
                others = [r for r in rivals(func, sources) if r != rel]
                if others:
                    problems.append(name + ": " + func + " is ALSO defined in " + ", ".join(others) + " - TWO "
                                    "implementations of ONE rule with nothing reporting divergence "
                                    "(BUG-499/BUG-502). One derived value, one home (D-2646).")
        else:
            non_homed += 1
            if status not in NO_HOME_STATUSES:
                problems.append(name + ": home is null but status " + repr(status) + " claims a home (declared "
                                "no-home statuses: " + str(list(NO_HOME_STATUSES)) + ")")
            writer = name.split(".")[-1]
            found = rivals(writer, sources)
            if found:
                problems.append(name + ": home is null, yet a module-level " + writer + " exists in "
                                + ", ".join(found) + " - a writer appeared while the registry still says NO code "
                                "decides it (home null is a statement, not a blank)")
        problems.extend(coordinate_problems(name, row, homes, load))
        problems.extend(parity_problems(name, row, status, ladder, ladder_rel))
    return problems, non_homed


def controls() -> list[tuple[str, bool]]:
    """Known-answer controls (BUG-492: a detector nobody has seen fail is not a detector)."""
    two = {"a.py": "def derive_things():\n    return 1\n", "b.py": "def derive_things():\n    return 2\n"}
    nested = {"c.py": "def outer():\n    def derive_things():\n        return 1\n"}
    return [
        ("a module-level def IS a home", module_defs(two["a.py"]) == {"derive_things"}),
        ("a NESTED helper is NOT a home (a home is module-level)", module_defs(nested["c.py"]) == {"outer"}),
        ("the same rule in TWO files is the BUG-502 shape and is DETECTED",
         rivals("derive_things", two) == ["a.py", "b.py"]),
        ("ONE definition is not a rival", rivals("derive_things", {"a.py": two["a.py"]}) == ["a.py"]),
        ("an unparsable module yields NO defs rather than a silent pass", module_defs("def (") == set()),
        ("the status vocabulary is CLOSED and names the four known states", len(STATUSES) == 4),
        ("a no-home status may not claim a home", "homed" not in NO_HOME_STATUSES),
    ] + coordinate_controls() + parity_controls()


def coordinate_controls() -> list[tuple[str, bool]]:
    """The COORDINATE join's known-answer controls (D-2661): one per arm, and EVERY arm must be able to FAIL."""

    def loader(docs: dict[str, Any]) -> Callable[[str], tuple[str, Any]]:
        """A fixture census: absent -> missing, None -> unparsable, else ok. Each arm is reachable by design."""
        def load(rel: str) -> tuple[str, Any]:
            if rel not in docs:
                return "missing", None
            if docs[rel] is None:
                return "unparsable", None
            return "ok", docs[rel]
        return load

    def probe(row: dict, homes: dict, docs: dict) -> list[str]:
        return coordinate_problems("probe.row", row, homes, loader(docs))

    live_producer = "config/derivations.yaml"   # a path that EXISTS: the arm needs one that does not
    doc_row = {"table": "d.json", "column": "summary"}
    doc_home = {"d.json": {"kind": "document", "producer_key": "written_by"}}
    doc_ok = {"d.json": {"summary": {}, "written_by": live_producer}}
    store_row = {"table": "t", "column": "c"}
    store_home = {"t": {"kind": "store_census", "census": "c.yaml", "membership": "measured.columns"}}
    census_ok = {"c.yaml": {"table": "t", "rail": "scripts/check_store_columns.py",
                            "measured": {"columns": {"c": {}}}}}
    return [
        ("a document coordinate's key, PRESENT in the document, resolves", probe(doc_row, doc_home, doc_ok) == []),
        ("a document coordinate's key, ABSENT from the document, is DETECTED",
         bool(probe({"table": "d.json", "column": "nope"}, doc_home, doc_ok))),
        ("a cited document path that does NOT exist is DETECTED", bool(probe(doc_row, doc_home, {}))),
        ("an UNPARSABLE document is DETECTED, never a silent pass",
         bool(probe(doc_row, doc_home, {"d.json": None}))),
        ("a document producer that does NOT exist is DETECTED",
         bool(probe(doc_row, doc_home, {"d.json": {"summary": {}, "written_by": "scripts/nope_zzz.py"}}))),
        ("a document coordinate with NO producer_key declared is DETECTED",
         bool(probe(doc_row, {"d.json": {"kind": "document"}}, doc_ok))),
        ("a store coordinate's column, PRESENT in its census membership, resolves",
         probe(store_row, store_home, census_ok) == []),
        ("a store coordinate's column the census is BLIND to is DETECTED",
         bool(probe({"table": "t", "column": "zz"}, store_home, census_ok))),
        ("a census measuring a DIFFERENT table proves nothing and is DETECTED",
         bool(probe(store_row, store_home, {"c.yaml": {"table": "other",
                                                       "rail": "scripts/check_store_columns.py",
                                                       "measured": {"columns": {"c": {}}}}}))),
        ("a census whose declared RAIL does not exist is DETECTED",
         bool(probe(store_row, store_home, {"c.yaml": {"table": "t", "rail": "scripts/nope_zzz.py",
                                                       "measured": {"columns": {"c": {}}}}}))),
        ("a cited table with NO declared census home is DETECTED (unverifiable coordinate)",
         bool(probe({"table": "z", "column": "c"}, store_home, census_ok))),
        ("an UNPARSEABLE census HOME is DETECTED",
         bool(probe(store_row, store_home, {"c.yaml": None}))),
        ("an UNKNOWN coordinate kind fails CLOSED",
         bool(probe(store_row, {"t": {"kind": "vibes", "census": "c.yaml"}}, census_ok))),
        ("a row naming no column is DETECTED", bool(probe({"table": "t"}, store_home, census_ok))),
        ("a declared membership path that does not RESOLVE fails CLOSED, not open",
         bool(probe(store_row, {"t": {"kind": "store_census", "census": "c.yaml", "membership": "nope.deep"}},
                    census_ok))),
        ("a store_census home with NO membership path declared fails CLOSED (no code default, D-2644)",
         bool(probe(store_row, {"t": {"kind": "store_census", "census": "c.yaml"}}, census_ok))),
    ]


def parity_controls() -> list[tuple[str, bool]]:
    """The PARITY join's known-answer controls (D-2662): one per arm, and EVERY arm must be able to FAIL.

    The fixture ladder is written with REAL newlines rather than escapes, so a control's text has exactly the shape
    a recipe line has. Arms proved: exists-and-invoked | missing | never-invoked | comment-only | unreadable ladder,
    plus two ANTI-OVERREACH arms (a non-homed null is LEGAL, an @-prefixed line IS a run) and the substring arm.
    """
    live = "scripts/check_store_columns.py"        # a path that EXISTS: the missing arm needs one that does not
    ok_ladder = ("ok", """health:
    python3 """ + live + """ --check || exit 1
""")
    other_ladder = ("ok", """health:
    python3 scripts/nope_other_zzz.py --check || exit 1
""")
    comment_ladder = ("ok", """health:
    # the parity rail is """ + live + """
    python3 scripts/nope_other_zzz.py --check || exit 1
""")
    at_ladder = ("ok", """health:
    @python3 """ + live + """ --check || exit 1
""")
    suffix_ladder = ("ok", """health:
    python3 """ + live + """.bak --check || exit 1
""")
    return [
        ("a homed row whose rail EXISTS and whose ladder INVOKES it resolves",
         parity_problems("probe.row", {"parity_rail": live}, "homed", ok_ladder, "justfile") == []),
        ("an @-prefixed recipe line IS a run (the @ is not part of the path)",
         ladder_invokes(at_ladder[1], live)),
        ("a parity rail that does NOT exist is DETECTED",
         bool(parity_problems("probe.row", {"parity_rail": "scripts/nope_zzz.py"}, "homed", ok_ladder, "justfile"))),
        ("a parity rail the ladder NEVER runs is DETECTED",
         bool(parity_problems("probe.row", {"parity_rail": live}, "homed", other_ladder, "justfile"))),
        ("a parity rail mentioned ONLY IN A COMMENT is not a run and is DETECTED",
         bool(parity_problems("probe.row", {"parity_rail": live}, "homed", comment_ladder, "justfile"))),
        ("an UNREADABLE ladder is DETECTED, never a silent pass",
         bool(parity_problems("probe.row", {"parity_rail": live}, "homed", ("missing", ""), "justfile"))),
        ("a HOMED row with NO parity rail is DETECTED (a claim with nothing re-deriving it)",
         bool(parity_problems("probe.row", {"parity_rail": None}, "homed", ok_ladder, "justfile"))),
        ("a NON-homed row with no parity rail is TOLERATED (its null repeats its own status)",
         parity_problems("probe.row", {"parity_rail": None}, "dead_but_read", ok_ladder, "justfile") == []),
        ("a path that is only a SUBSTRING of another is not an invocation (BUG-528 class)",
         not ladder_invokes(suffix_ladder[1], live)),
    ]


def main(argv: list[str]) -> int:
    """Run the known-answer controls, or join the registry's homes to the tree."""
    if "--selftest" in argv:
        rows = controls()
        for name, ok in rows:
            print(("  ok  " if ok else "  !!  ") + name)
        failed = [n for n, ok in rows if not ok]
        if failed:
            print("FAIL " + PREFIX + " --selftest: " + str(len(failed)) + " of " + str(len(rows))
                  + " known-answer control(s) did not fire")
            return EXIT_DRIFT
        print("ok " + PREFIX + " --selftest: " + str(len(rows)) + "/" + str(len(rows))
              + " known-answer control(s) fire")
        return EXIT_CLEAN

    registry = load_yaml(REGISTRY)
    rows = declared(registry, "derivations", "config/derivations.yaml")
    roots = [str(r) for r in declared(registry, "scan_roots", "config/derivations.yaml")]
    enforcement = declared(registry, "enforcement", "config/derivations.yaml")
    ceiling = int(enforcement.get("max_non_homed", -1))
    if ceiling < 0:
        raise SystemExit("FAIL " + PREFIX + ": config/derivations.yaml#enforcement declares no numeric "
                         "max_non_homed - a ceiling with no number is a comment (BUG-491 class)")
    homes = declared(registry, "coordinate_homes", "config/derivations.yaml")
    if not isinstance(homes, dict) or not homes:
        raise SystemExit("FAIL " + PREFIX + ": config/derivations.yaml declares no coordinate_homes mapping - the "
                         "coordinate half of every row would be joined by nothing, which is the BUG-553 defect: a "
                         "read with a code default is not a declaration (D-2644).")
    ladder_rel = str(enforcement.get("ladder") or "").strip()
    if not ladder_rel:
        raise SystemExit("FAIL " + PREFIX + ": config/derivations.yaml#enforcement declares no ladder - the place "
                         "that runs the parity rails is a DECLARATION (C12), never a path hardcoded here (D-2662), "
                         "and a rail nothing runs protects nothing.")
    ladder = load_text(ladder_rel)
    if ladder[0] != "ok":
        raise SystemExit("FAIL " + PREFIX + ": the declared ladder " + ladder_rel + " is " + ladder[0]
                         + " - whether any parity rail ever runs cannot be established from a ladder nobody can "
                         "read, and unreadable is not clean (C16)")
    sources = sources_under(roots)
    problems, non_homed = check_rows(rows, sources, homes, load_artifact, ladder, ladder_rel)
    homed = len(rows) - non_homed
    named = [str(r.get("parity_rail") or "").strip() for r in rows if str(r.get("parity_rail") or "").strip()]
    line = (str(len(rows)) + " registered derivation(s) over " + str(len(sources)) + " module(s): " + str(homed)
            + " homed, " + str(non_homed) + " not homed (declared ceiling " + str(ceiling) + ", shrink-only); "
            + str(len(rows)) + " cited coordinate(s) joined to " + str(len(homes))
            + " declared census home(s); " + str(len(named)) + " cited parity rail(s) over "
            + str(len(set(named))) + " distinct script(s), ladder " + ladder_rel)
    if problems:
        print("FAIL " + PREFIX + ": " + str(len(problems)) + " home problem(s) - " + line)
        for p in problems:
            print("  !!  " + p)
        return EXIT_DRIFT
    if non_homed > ceiling:
        print("FAIL " + PREFIX + ": non-homed derivations EXCEED the declared ceiling - " + line)
        return EXIT_DRIFT
    if non_homed < ceiling:
        print("owner-owed (loud, NOT fatal - BUG-457): " + str(non_homed) + " non-homed row(s) are below the "
              "declared ceiling " + str(ceiling) + " - lower it (a ceiling may only be LOWERED; raising it is a "
              "decision) - " + line)
        return EXIT_OWED
    print("ok " + PREFIX + ": every registered home exists, is UNIQUE, every cited coordinate RESOLVES to its "
          "declared census home, every cited parity rail EXISTS and is INVOKED by the declared ladder, and no "
          "writer appeared where home is null (the store is never opened here: the column question is DELEGATED to "
          "its own rail, D-2646/D-2661/D-2662) - " + line)
    return EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
