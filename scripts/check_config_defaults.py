#!/usr/bin/env python3
"""check_config_defaults.py - D-2644: a config value read with a code default is an UNDECLARED value.

WHY. BUG-504's INSTANCE was one silent default in the S5 score axis (stage5.nli_model_fallback -> ""), which
would have made the verifier read an EMPTY model name with no error anywhere. The CLASS is that every
receiver.get(key, <literal>) moves a value's effective setting OUT of config and INTO code: a config miss is
not an error, it is a silent fallback. The instance was fixed; the class is COUNTED here, because a class that
is never measured grows back.

POPULATION (stated, so the number is reproducible - a count with no stated population is a rumour): every .py
under the registry scan_roots is AST-parsed. A SITE is a Call whose func is Attribute(attr="get") ROOTED at a
Name in config_reads.receivers - or at a BLOCK ALIAS of one, see ALIAS - with a string-literal key and a SECOND
argument (the default). A chained read roots at the receiver through the chain, so cfg.get(a, {}).get(b, x) is
TWO sites - the container read falls back to {} and is counted, because an absent block silently empties
everything below it. Classification is by the key's LAST DOTTED SEGMENT: SHADOWED-DECLARED when that leaf name
is a key anywhere under config_glob, UNDECLARED otherwise. Both ceilings count DISTINCT keys, so copying a line
never raises them.

INSTRUMENT (D-2982). A count is only comparable to a count taken with the SAME instrument, so the COVERAGE is
fingerprinted: rule version + receivers + config glob + scan roots + alias rule, hashed into
config_reads.coverage_fingerprint. When the fingerprint moves, this rail says so and refuses to compare - "the
INSTRUMENT changed, not the debt" - and it re-measures BOTH populations, because the receipt carries the
previous coverage. The delta is therefore attributed two ways: newly VISIBLE (coverage) vs genuinely NEW
(code, same coverage). The pre-2026-10-13 ledger shows why this matters: the ceiling was raised SEVEN times in
eighteen days, and each raise was indistinguishable from debt, because nothing recorded what had changed.
`--rebaseline --because D-xxxx` is the only act that may raise a ceiling, and the cited id must exist in
config/decisions.yaml: a raise is a DECISION, never an edit (D-2644).

ALIAS (D-2982). The pre-D-2982 rule saw only a receiver literal. `_SERVING = _CFG.get("serving", {})` followed
by `_SERVING.get("golden_anchor_mode", "name_then_id")` therefore escaped the census entirely: the block alias
hid every leaf read behind it (measured 2026-10-13: 99 sites / 88 declared keys INVISIBLE - a 27% undercount
that was itself being reported as the debt). An alias resolves per SCOPE, and only when the name is bound
EXACTLY ONCE in that scope from a config-rooted expression: a name reused for something else (`s4 =
load_jsonl(...)` beside `s4 = cfg.get("stage4", {})`) is NOT an alias, because a detector that fires on an
honest local variable is noise, and noise is how a rail gets switched off (BUG-492). STATED LIMIT: function
ARGUMENTS are not collected as bindings, so an argument shadowing a module alias is not resolved as a shadow.

RULER (D-2642: one derived value, one home). config/derivations.yaml#config_reads.ceilings IS the number and
THIS RAIL writes it, never a human transcribing a probe. While measured_by is a probe, the rail owns the number
in EITHER direction and records the change; once measured_by is the rail it may only LOWER a ceiling, and a
measurement above the declaration is drift that is NEVER written (an undeclared value must not become declared
by census).

DEBT IS A SET (D-2982). config/config_defaults_census.json carries the measured KEY SET, not only a count. Two
keys paid while two other keys appear is NOT "the same number": the debt ROTATED, and a count-only comparison
cannot see it. The receipt also carries the coverage that produced it, which is what makes the two-way
attribution above possible at all.

TRI-STATE (BUG-457): 0 in sync | 1 drift (measured above the ceiling, or the debt set changed) | 2 owner-owed
(the declared number was stale - loud, NOT fatal).
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
PREFIX = "check-config-defaults"
REGISTRY = ROOT / "config" / "derivations.yaml"
RECEIPT = ROOT / "config" / "config_defaults_census.json"
DECISIONS = ROOT / "config" / "decisions.yaml"
RAIL_REL = "scripts/check_config_defaults.py"
# D-2982: the SITE rule's version - bumped when the RULE changes shape (not when a receiver is added). It is
# part of the coverage fingerprint, so a rule change can never be misread as a change in the debt.
RULE_VERSION = "3"
RECEIPT_SCHEMA = "1"
# D-2982: a coverage change cites the decision that justifies the wider instrument; the id must exist in the
# live registry (fail-closed: an unknown id refuses, so a raise can never be smuggled through a typo).
DECISION_ID_RE = re.compile(r"(?m)^- id: (D-\d+)$")
# RAIL_DATE was a hardcoded "2026-09-25" that wrote a FALSE date once the rail measured on 2026-09-26. The run
# date is now DERIVED (yaml_guard.today()): a date constant is a value that can only go stale (C12/C20).
EXIT_CLEAN, EXIT_DRIFT, EXIT_OWED = 0, 1, 2
CONTROLS_KEYS = {"alpha", "beta"}

sys.path.insert(0, str(ROOT / "scripts"))
from lib import (  # noqa: E402 - D-2648: the ONE home for "verify the bytes before writing"
    yaml_guard,
)
from lib.write_guard import (  # noqa: E402 - D-401/I1 (C6: crash-safe write)
    OWNED_ANY,
    write_document,
)


def load_yaml(path: Path) -> dict:
    """Parse a YAML document, or fail loudly - a registry nobody can parse decides nothing."""
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def declared(doc: dict, key: str, where: str) -> Any:
    """FAIL CLOSED: an absent declaration is the error, never a default (D-2644)."""
    if key not in doc:
        raise SystemExit("FAIL " + PREFIX + ": " + where + " declares no " + repr(key)
                         + " - a rule read with a code default is the defect this rail measures")
    return doc[key]


def root_name(node: ast.AST) -> str | None:
    """The Name a chained read starts from, so cfg.get(a).get(b) roots at cfg."""
    while True:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        elif isinstance(node, ast.Subscript):
            node = node.value
        else:
            return None


def config_rooted(node: ast.AST, receivers: set[str]) -> bool:
    """True when an expression READS the config surface: a receiver, or a chain/subscript of one (D-2982).

    Reading THROUGH a call is deliberately NOT resolving: `_load_yaml(_TAXONOMY_PATH)` roots at `_load_yaml`,
    which is not a receiver, so a loader's local variable is never mistaken for a config block alias.
    """
    current = node
    while True:
        if isinstance(current, ast.Name):
            return current.id in receivers
        if isinstance(current, (ast.Attribute, ast.Subscript)):
            current = current.value
            continue
        if isinstance(current, ast.Call):
            current = current.func
            continue
        return False


def scope_bindings(body: list[ast.stmt], receivers: set[str]) -> dict[str, list[bool]]:
    """Every binding of every name in ONE scope, with the config-rootedness of its right-hand side (D-2982).

    Nested scopes are NOT descended into (their bindings belong to them), but control-flow blocks ARE (a name
    bound inside `try:` or `if` still binds in this scope, and a REBINDING - even one that is not executed -
    is enough to disqualify the name as an alias, which is the conservative direction).
    """
    out: dict[str, list[bool]] = {}

    def names_of(node: ast.AST) -> list[str]:
        return [n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)]

    def note(targets: list[str], value: ast.AST | None) -> None:
        rooted = value is not None and config_rooted(value, receivers)
        for name in targets:
            out.setdefault(name, []).append(rooted)

    def walk(stmt: ast.stmt) -> None:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            note([stmt.name], None)
            return
        if isinstance(stmt, ast.Assign):
            note([n for target in stmt.targets for n in names_of(target)], stmt.value)
        elif isinstance(stmt, ast.AnnAssign):
            note(names_of(stmt.target), stmt.value)
        elif isinstance(stmt, ast.AugAssign):
            note(names_of(stmt.target), stmt.value)
        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            note(names_of(stmt.target), stmt.iter)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            for item in stmt.items:
                if item.optional_vars is not None:
                    note(names_of(item.optional_vars), item.context_expr)
        elif isinstance(stmt, ast.Try):
            for handler in stmt.handlers:
                if handler.name:
                    note([handler.name], None)
        for _field, value in ast.iter_fields(stmt):
            for child in (value if isinstance(value, list) else [value]):
                if isinstance(child, ast.stmt):
                    walk(child)

    for statement in body:
        walk(statement)
    return out


class SiteCollector(ast.NodeVisitor):
    """Collect every SITE - a .get(key, literal) rooted at a receiver or at a block alias (D-2982).

    The scope stack holds (every bound name, alias names) for each enclosing scope, outermost first, so a name
    resolves at its INNERMOST binding: a function that rebinds a module alias to something else shadows it, and
    the census says so instead of counting its reads as config reads.
    """

    def __init__(self, receivers: set[str], aliases: bool, report_at: str) -> None:
        self.receivers = receivers
        self.aliases = aliases
        self.report_at = report_at
        self.keys: list[str] = []
        self.locations: dict[str, list[str]] = {}
        self._scopes: list[tuple[set[str], set[str]]] = []

    def _resolves(self, name: str) -> bool:
        """A declared RECEIVER is an axiom; a scope binding only ever decides an ALIAS (D-2982).

        MEASURED 2026-10-13: resolving the receivers through the scope stack first collapsed the census
        from 461 sites to 130, because a receiver is itself a module-level binding (`_CFG = yaml.safe_load
        (...)`) whose right-hand side is NOT config-rooted, so the innermost-binding rule disqualified the
        receiver that declares the whole surface. The declared roots are read from the registry and cannot
        be re-decided by the code under measurement.
        """
        if name in self.receivers:
            return True
        for bound, aliases in reversed(self._scopes):
            if name in bound:
                return self.aliases and name in aliases
        return False

    def _visit_scope(self, body: list[ast.stmt], extras: Sequence[ast.AST]) -> None:
        for extra in extras:
            self.visit(extra)
        if self.aliases:
            bindings = scope_bindings(body, self.receivers)
            alias_names = {n for n, roots in bindings.items() if len(roots) == 1 and roots[0]}
            self._scopes.append((set(bindings), alias_names))
        else:
            self._scopes.append((set(), set()))
        for statement in body:
            self.visit(statement)
        self._scopes.pop()

    def visit_Module(self, node: ast.Module) -> None:
        self._visit_scope(node.body, [])

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        extras: list[ast.AST] = list(node.decorator_list)
        extras += list(node.args.defaults)
        extras += [d for d in node.args.kw_defaults if d is not None]
        if node.returns is not None:
            extras.append(node.returns)
        self._visit_scope(node.body, extras)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_scope(node.body, list(node.decorator_list) + list(node.bases))
        return None

    def visit_Call(self, node: ast.Call) -> None:
        key = self._site_key(node)
        if key is not None:
            self.keys.append(key)
            self.locations.setdefault(key, []).append(f"{self.report_at}:{node.lineno}")
        self.generic_visit(node)

    def _site_key(self, node: ast.Call) -> str | None:
        """The leaf key of a SITE, or None when the call is not one (the whole rule, in one place)."""
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "get":
            return None
        if len(node.args) < 2 or isinstance(node.args[0], ast.Starred):
            return None
        # MEASURED 2026-09-26 (known-answer control 5): a NON-LITERAL default is not a site. The debt
        # is a VALUE hidden in code; a fallback that is a NAME points at something already named and
        # visible to a reader, so counting it would inflate the census with honest reads (D-2644).
        try:
            ast.literal_eval(node.args[1])
        except (ValueError, SyntaxError, TypeError):
            return None
        first = node.args[0]
        if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
            return None
        root = root_name(func.value)
        if root is None or not self._resolves(root):
            return None
        return first.value.split(".")[-1]


def collect(tree: ast.AST, receivers: set[str], aliases: bool, report_at: str) -> SiteCollector:
    """Run the ONE rule over a parsed module (both node_sites and the location map come from here)."""
    collector = SiteCollector(receivers, aliases, report_at)
    collector.visit(tree)
    return collector


def node_sites(tree: ast.AST, receivers: set[str], aliases: bool = True) -> list[str]:
    """Every leaf key read with a literal default through a receiver or a block alias, in source order."""
    return collect(tree, receivers, aliases, "<string>").keys


def census(source: str, receivers: set[str], keys: set[str],
           aliases: bool = True) -> tuple[set[str], set[str], int]:
    """Return (shadowed_declared, undeclared, site_count) for ONE module's source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set(), set(), 0
    leaves = node_sites(tree, receivers, aliases)
    return {k for k in leaves if k in keys}, {k for k in leaves if k not in keys}, len(leaves)


def declared_keys(config_glob: str) -> set[str]:
    """Every key name anywhere in the declared config surface (the DECLARED half of the census)."""
    keys: set[str] = set()
    for path in sorted(ROOT.glob(config_glob)):
        stack: list[Any] = [yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                for k, v in node.items():
                    keys.add(str(k))
                    stack.append(v)
            elif isinstance(node, list):
                stack.extend(node)
    return keys


def scan(receivers: set[str], keys: set[str], roots: list[str], aliases: bool = True
         ) -> tuple[set[str], set[str], int, int, dict[str, list[str]]]:
    """Walk every declared scan root; fail closed on a root that is not a directory (C16).

    Returns (shadowed, undeclared, sites, files, locations) - the LOCATIONS are what lets a failure name the
    work to do instead of only the size of the problem (D-2982: an unactionable red is raised, not fixed).
    """
    shadowed: set[str] = set()
    undeclared: set[str] = set()
    locations: dict[str, list[str]] = {}
    sites = files = 0
    for rel in roots:
        d = ROOT / str(rel)
        if not d.is_dir():
            raise SystemExit("FAIL " + PREFIX + ": scan_roots names " + str(rel) + ", which is not a directory"
                             " - a scan root that silently does not exist narrows the census and still prints"
                             " ok (C16)")
        for path in sorted(d.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            files += 1
            source = path.read_text(encoding="utf-8", errors="replace")
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            found = collect(tree, receivers, aliases, str(path.relative_to(ROOT)))
            leaves = found.keys
            shadowed |= {k for k in leaves if k in keys}
            undeclared |= {k for k in leaves if k not in keys}
            sites += len(leaves)
            for key, where in found.locations.items():
                locations.setdefault(key, []).extend(where)
    return shadowed, undeclared, sites, files, locations


def coverage_of(receivers: set[str], config_glob: str, roots: list[str]) -> dict[str, Any]:
    """The coverage a measurement is taken under: hashed by `fingerprint`, declared by the rebaseline.

    ONE definition, used by main() and by the spec contract, so a test can never assert a coverage the rail
    does not actually use (D-2982/D-2642).
    """
    return {"rule": RULE_VERSION, "receivers": sorted(receivers), "config_glob": config_glob,
            "scan_roots": sorted(roots), "aliases": True}


def fingerprint(coverage: Mapping[str, Any]) -> str:
    """The COVERAGE of this instrument, hashed: a number is only comparable to one taken the same way."""
    return hashlib.sha256(json.dumps(dict(coverage), sort_keys=True).encode("utf-8")).hexdigest()[:16]


def read_receipt() -> dict:
    """The last measured census (the debt SET plus the coverage that produced it), or {} (absent is not an error)."""
    if not RECEIPT.exists():
        return {}
    try:
        data = json.loads(RECEIPT.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit("FAIL " + PREFIX + ": " + str(RECEIPT.relative_to(ROOT)) + " is not readable JSON ("
                         + str(exc) + ") - a receipt that cannot be read cannot bound a comparison (C16)"
                         ) from exc
    return data if isinstance(data, dict) else {}


def write_receipt(measured: dict[str, int], shadowed: set[str], undeclared: set[str], sites: int, files: int,
                  coverage: Mapping[str, Any], coverage_id: str) -> None:
    """Record the debt SET under the coverage that measured it (D-2982: the metric is a set, not a number)."""
    payload = {"schema_version": RECEIPT_SCHEMA, "rail": RAIL_REL, "measured_at": yaml_guard.today(),
               "coverage": dict(coverage, fingerprint=coverage_id),
               "counts": {"shadowed_declared": measured["shadowed_declared"],
                          "undeclared": measured["undeclared"], "sites": sites, "modules": files},
               "keys": {"shadowed_declared": sorted(shadowed), "undeclared": sorted(undeclared)}}
    write_document(RECEIPT, json.dumps(payload, indent=1, sort_keys=True) + chr(10), writer=RAIL_REL,
                   owned_keys={OWNED_ANY}, backup=True)


def decision_ids() -> set[str]:
    """Every decision id in the live registry (a raise must cite one that exists - D-2982/D-2644)."""
    return set(DECISION_ID_RE.findall(DECISIONS.read_text(encoding="utf-8", errors="replace")))


def flag_value(argv: list[str], flag: str) -> str:
    """The value that follows a flag, or '' when absent - a raise names its decision (D-2982)."""
    if flag in argv:
        index = argv.index(flag)
        if index + 1 < len(argv):
            return str(argv[index + 1])
    return ""


def set_ceilings(text: str, measured: dict[str, int]) -> str:
    """Upsert the two ceiling numbers, whichever shape the declared block has (D-2642).

    MEASURED 2026-09-26: config/derivations.yaml declares ceilings as a BLOCK mapping, so the old
    flow-mapping-only reader refused to write and the rail could NEVER own its number in the file that
    declares it. Refusing was correct and useless. Point at whichever shape the file actually has, and
    when it is a block insert measured_by AFTER undeclared - inside the block it would be a key of
    ceilings, not of config_reads (D-2642: the RAIL owns the number).
    """
    new_map = ("ceilings: {shadowed_declared: " + str(measured["shadowed_declared"]) + ", undeclared: "
               + str(measured["undeclared"]) + "}")
    text = re.sub(r"(?m)^(\s*)measured_by:.*$", "", text, count=1)
    text, n = re.subn(r"(?m)^  ceilings:[ \t]*\{[^}]*\}[ \t]*$", "  " + new_map, text, count=1)
    if n == 1:
        return re.sub(r"(?m)^(  ceilings:.*)$", r"\1" + chr(10) + "  measured_by: " + RAIL_REL, text, count=1)
    shad = r"(?m)^(\s*)shadowed_declared:[ \t]*\d+[ \t]*$"
    unde = r"(?m)^(\s*)undeclared:[ \t]*\d+[ \t]*$"
    text, n1 = re.subn(shad, r"\1shadowed_declared: " + str(measured["shadowed_declared"]), text, count=1)
    text, n2 = re.subn(unde, r"\1undeclared: " + str(measured["undeclared"]) + chr(10)
                       + r"\1measured_by: " + RAIL_REL, text, count=1)
    if not (n1 == 1 and n2 == 1):
        raise SystemExit("FAIL " + PREFIX + ": config_reads.ceilings is neither a block nor a flow mapping - "
                         "refusing to write a number this rail cannot point at (D-2642)")
    return text


def record_ceiling(measured: dict[str, int], previous: dict[str, int]) -> str:
    """Write the rail's OWN measurement into the registry, keeping the old number as history (D-2642)."""
    text = set_ceilings(REGISTRY.read_text(encoding="utf-8"), measured)
    # MEASURED 2026-09-26 (D-2648 class): the old form appended this sentence at END OF FILE, so it landed after
    # `enforcement.direction`, and because it carries a colon-space it made config/derivations.yaml UNPARSEABLE -
    # the homes rail then died inside yaml before it could load its own registry. Prose belongs INSIDE the block
    # it belongs to (append_to_block computes the insertion point from the file's own indentation), the bytes are
    # verified to parse BEFORE the write, and the write is crash-safe through the ONE guarded writer (C6, D-401):
    # the old bare REGISTRY.write_text had no tempfile/fsync/os.replace and no backup.
    text = yaml_guard.append_to_block(text, "ceiling_changed", [
        "REMEASURED " + yaml_guard.today() + " by " + RAIL_REL + ": shadowed_declared "
        + str(previous.get("shadowed_declared")) + " -> " + str(measured["shadowed_declared"]) + ", undeclared "
        + str(previous.get("undeclared")) + " -> " + str(measured["undeclared"]) + ". The RAIL owns the number "
        "(D-2642): the probe's value was a CLAIM, and a claim is not a measurement. From here the ceiling may "
        "only be LOWERED."])
    yaml_guard.assert_yaml(text, "config/derivations.yaml", RAIL_REL)
    write_document(REGISTRY, text, writer=RAIL_REL, owned_keys={OWNED_ANY}, backup=True)
    return "ceilings: {shadowed_declared: " + str(measured["shadowed_declared"]) + ", undeclared: " \
           + str(measured["undeclared"]) + "}"


def record_rebaseline(measured: dict[str, int], previous: dict[str, int], coverage: Mapping[str, Any],
                      coverage_id: str, because: str) -> str:
    """The ONLY act that may RAISE a ceiling, because a change of COVERAGE is not new debt (D-2982).

    The fingerprint is written into config_reads (the instrument's own home), the ceilings are re-cut from
    this measurement, and the ledger names the change so a later reader can tell a wider instrument from a
    bigger mess. The decision that justifies it is cited in the ledger line and must already exist.
    """
    text = REGISTRY.read_text(encoding="utf-8")
    line = "  coverage_fingerprint: " + coverage_id
    text, n = re.subn(r"(?m)^  coverage_fingerprint:.*$", line, text, count=1)
    if n == 0:
        text, n = re.subn(r"(?m)^(  config_glob:.*)$", r"\1" + chr(10) + line, text, count=1)
    if n != 1:
        raise SystemExit("FAIL " + PREFIX + ": config_reads has no config_glob line to anchor "
                         "coverage_fingerprint to - refusing to write a fingerprint this rail cannot point at "
                         "(D-2642)")
    text = set_ceilings(text, measured)
    text = yaml_guard.append_to_block(text, "ceiling_changed", [
        "COVERAGE CHANGE " + yaml_guard.today() + " by " + RAIL_REL + ", cited " + because + ": rule "
        + str(coverage["rule"]) + ", " + str(len(coverage["receivers"])) + " receiver(s), aliases "
        + str(coverage["aliases"]).lower() + ", fingerprint " + coverage_id + ". shadowed_declared "
        + str(previous.get("shadowed_declared")) + " -> " + str(measured["shadowed_declared"]) + ", undeclared "
        + str(previous.get("undeclared")) + " -> " + str(measured["undeclared"]) + ". This is a RE-MEASUREMENT "
        "under a wider instrument, not new debt (D-2982). From here the ceiling may only be LOWERED."])
    yaml_guard.assert_yaml(text, "config/derivations.yaml", RAIL_REL)
    write_document(REGISTRY, text, writer=RAIL_REL, owned_keys={OWNED_ANY}, backup=True)
    return "coverage_fingerprint: " + coverage_id


def attribute_delta(shadowed: set[str], receipt: Mapping[str, Any], keys: set[str],
                    roots: list[str]) -> dict[str, Any]:
    """Split a delta into newly VISIBLE (coverage) vs NEW code debt (same coverage), by RE-MEASURING (D-2982).

    A delta of COUNTS cannot make this split: that is precisely how seven ceiling raises went unattributed
    (BUG-758). Re-running the scan with the coverage the receipt was taken under holds the code constant and
    varies only the instrument, so `shadowed - previous_shadowed` is attributable to COVERAGE and
    `previous_shadowed - previous_keys` is attributable to the CODE. Extracted from main() because an
    invariant that cannot be exercised by a test is a claim, not a contract (D-2978).

    Returns {"previous": fingerprint or "", "visible": [...], "new": [...], "paid": [...]}.
    """
    previous_coverage = receipt.get("coverage") if receipt else None
    if not isinstance(previous_coverage, dict) or not previous_coverage.get("fingerprint"):
        return {"previous": "", "visible": [], "new": [], "paid": []}
    previous_shadowed = scan([str(r) for r in previous_coverage.get("receivers", [])], keys, roots,
                             aliases=bool(previous_coverage.get("aliases", False)))[0]
    previous_keys = set(receipt.get("keys", {}).get("shadowed_declared", []))
    return {"previous": str(previous_coverage["fingerprint"]),
            "visible": sorted(shadowed - previous_shadowed),
            "new": sorted(previous_shadowed - previous_keys),
            "paid": sorted(previous_keys - previous_shadowed)}


def controls() -> list[tuple[str, bool]]:
    """Known-answer controls (BUG-492: a detector nobody has seen fail is not a detector)."""
    rcv = {"_CFG", "cfg", "config", "conf", "settings"}
    return [
        ("a receiver .get with a literal key and default is a SITE, SHADOWED when the key is declared",
         census('_CFG.get("alpha", 1)', rcv, CONTROLS_KEYS) == ({"alpha"}, set(), 1)),
        ("a chained read roots at the receiver, and the CONTAINER read counts too (an absent block becomes {})",
         census('_CFG.get("alpha", {}).get("beta", 2)', rcv, CONTROLS_KEYS) == ({"alpha", "beta"}, set(), 2)),
        ("a .get with NO default is an honest read, not a site",
         census('_CFG.get("alpha")', rcv, CONTROLS_KEYS) == (set(), set(), 0)),
        ("a non-receiver .get is not a site",
         census('other.get("alpha", 1)', rcv, CONTROLS_KEYS) == (set(), set(), 0)),
        ("a NON-LITERAL default is not a site: the fallback is a variable, not a value hidden in code",
         census('_CFG.get("alpha", FALLBACK)', rcv, CONTROLS_KEYS) == (set(), set(), 0)),
        ("a key declared nowhere is UNDECLARED, never silently counted as shadowed",
         census('_CFG.get("no_such_key_zz", 1)', rcv, CONTROLS_KEYS) == (set(), {"no_such_key_zz"}, 1)),
        ("the receiver match is EXACT: cfg2 is not a receiver",
         census('cfg2.get("alpha", 1)', rcv, CONTROLS_KEYS) == (set(), set(), 0)),
        ("the ROOT is the receiver even under an attribute chain",
         census('settings.stage5.get("alpha", 1)', rcv, CONTROLS_KEYS) == ({"alpha"}, set(), 1)),
        # D-2982 controls: the block-alias escape hatch, and the two ways a name must NOT be an alias.
        ("a name bound ONCE to a config block IS an alias: its leaf reads are SITEs (D-2982)",
         census('_S = _CFG.get("alpha", {})\n_S.get("beta", 2)', rcv, CONTROLS_KEYS) == ({"alpha", "beta"}, set(), 2)),
        ("a MODULE alias is visible INSIDE a function (an enclosing scope is searched, D-2982)",
         census('_S = _CFG.get("alpha", {})\ndef f():\n    return _S.get("beta", 2)', rcv, CONTROLS_KEYS)
         == ({"alpha", "beta"}, set(), 2)),
        ("a name REBOUND in the same scope is NOT an alias - a reused local must not become debt (D-2982)",
         census('_S = _CFG.get("alpha", {})\n_S = other()\n_S.get("beta", 2)', rcv, CONTROLS_KEYS)
         == ({"alpha"}, set(), 1)),
        ("a name bound to something NOT config-rooted is NOT an alias (D-2982)",
         census('_S = other.load()\n_S.get("beta", 2)', rcv, CONTROLS_KEYS) == (set(), set(), 0)),
        ("an inner scope that SHADOWS a module alias resolves to the inner binding, not the alias (D-2982)",
         census('_S = _CFG.get("alpha", {})\ndef f():\n    _S = other.load()\n    return _S.get("beta", 2)',
                rcv, CONTROLS_KEYS) == ({"alpha"}, set(), 1)),
        ("a LOADER call is not a config alias: _load_yaml(PATH) roots at the loader, not the surface (D-2982)",
         census('_S = _load_yaml(PATH)\n_S.get("beta", 2)', rcv, CONTROLS_KEYS) == (set(), set(), 0)),
    ]


def main(argv: list[str]) -> int:
    """Run the known-answer controls, or measure the census and join it to the declared ceilings.

    BUG-660: a health rail is a PROBE - it measures and reports, never writes. The census is joined to the
    declared ceilings read-only by default; `--record` is the explicit resolve act that may re-record the
    ceiling in config/derivations.yaml (and only ever LOWER it, D-2644). `--check` is the read-only default
    and is accepted for explicitness.

    D-2982: `--rebaseline --because D-xxxx` is the SECOND resolve act and the only one that may RAISE a
    ceiling, because a change of COVERAGE is not new debt. The cited decision must exist in the live
    registry - a raise is a decision, never an edit.
    """
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

    record = "--record" in argv
    rebaseline = "--rebaseline" in argv
    because = flag_value(argv, "--because")

    registry = load_yaml(REGISTRY)
    reads = declared(registry, "config_reads", "config/derivations.yaml")
    receivers = {str(r) for r in declared(reads, "receivers", "config_reads")}
    config_glob = str(declared(reads, "config_glob", "config_reads"))
    ceilings = declared(reads, "ceilings", "config_reads")
    roots = [str(r) for r in declared(registry, "scan_roots", "config/derivations.yaml")]
    keys = declared_keys(config_glob)

    coverage = coverage_of(receivers, config_glob, roots)
    coverage_id = fingerprint(coverage)
    declared_coverage = str(reads.get("coverage_fingerprint") or "").strip()
    receipt = read_receipt()

    shadowed, undeclared, sites, files, locations = scan(receivers, keys, roots, aliases=True)
    measured = {"shadowed_declared": len(shadowed), "undeclared": len(undeclared)}
    before = {"shadowed_declared": int(ceilings.get("shadowed_declared", -1)),
              "undeclared": int(ceilings.get("undeclared", -1))}
    for key, value in before.items():
        if value < 0:
            raise SystemExit("FAIL " + PREFIX + ": config_reads.ceilings declares no numeric " + key + " - a "
                             "ceiling with no number is a comment, and a comment cannot fail")
    line = ("measured " + str(sites) + " config-default SITE(s) over " + str(files) + " module(s) under "
            + str(roots) + ": " + str(measured["shadowed_declared"]) + " distinct SHADOWED-DECLARED key(s), "
            + str(measured["undeclared"]) + " distinct UNDECLARED key(s)")

    # ── D-2982: the INSTRUMENT is part of the measurement ────────────────────────────────────────────
    if coverage_id != declared_coverage:
        print("owner-owed: the INSTRUMENT changed, not (necessarily) the debt - " + line)
        print("  ->  coverage_fingerprint: declared " + (declared_coverage or "(none)")
              + " -> measured " + coverage_id)
        print("  ->  coverage: rule " + str(coverage["rule"]) + ", " + str(len(coverage["receivers"]))
              + " receiver(s), aliases " + str(coverage["aliases"]).lower() + ", config_glob " + config_glob
              + ", " + str(len(coverage["scan_roots"])) + " scan root(s)")
        split = attribute_delta(shadowed, receipt, keys, roots)
        if split["previous"]:
            print("  ->  attributed by re-measuring WITH the previous coverage " + split["previous"] + ": "
                  + str(len(split["visible"])) + " key(s) newly VISIBLE (coverage), " + str(len(split["new"]))
                  + " key(s) NEW (code, same coverage), " + str(len(split["paid"])) + " key(s) PAID")
            if split["visible"]:
                print("      newly visible: " + ", ".join(split["visible"][:24])
                      + (" ..." if len(split["visible"]) > 24 else ""))
            if split["new"]:
                print("      new code debt: " + ", ".join(split["new"][:24]))
                for key in split["new"][:6]:
                    print("      " + key + " @ " + ", ".join(locations.get(key, [])[:2]))
        if not rebaseline:
            print("  a coverage change is resolved by a DECISION, never by editing a number: re-run with "
                  "--rebaseline --because D-xxxx, and that id must exist in config/decisions.yaml "
                  "(D-2982/D-2644)")
            return EXIT_DRIFT
        if not because:
            print("FAIL " + PREFIX + ": --rebaseline needs --because <D-id> - a raise cites the decision that "
                  "justifies the wider instrument, and an uncited raise is exactly what D-2982 exists to stop")
            return EXIT_DRIFT
        known = decision_ids()
        if because not in known:
            print("FAIL " + PREFIX + ": --because " + because + " is not an id in config/decisions.yaml ("
                  + str(len(known)) + " known) - mint the decision FIRST, then re-measure (D-2660/D-2982)")
            return EXIT_DRIFT
        record_rebaseline(measured, before, coverage, coverage_id, because)
        write_receipt(measured, shadowed, undeclared, sites, files, coverage, coverage_id)
        print("ok " + PREFIX + " --rebaseline: the coverage change is RECORDED and cited by " + because
              + " - " + line)
        return EXIT_OWED

    # ── D-2982: the DEBT IS A SET - a frozen count must not hide a rotating debt ─────────────────────
    by_rail = str(reads.get("measured_by") or ceilings.get("measured_by") or "").strip() == RAIL_REL
    previous_keys = set(receipt.get("keys", {}).get("shadowed_declared", [])) if receipt else set()
    added = sorted(shadowed - previous_keys) if receipt else []
    paid = sorted(previous_keys - shadowed) if receipt else []
    grew = sorted(k for k in measured if measured[k] > before[k])
    changed = sorted(k for k in measured if measured[k] != before[k])

    if added and by_rail:
        print("FAIL " + PREFIX + ": the undeclared-default debt GREW by SET - " + line)
        for key in added:
            print("  !!  NEW shadowed-declared key: " + key + "  @ "
                  + ", ".join(locations.get(key, [])[:2]))
        for key in grew:
            print("  !!  " + key + ": declared " + str(before[key]) + " -> measured " + str(measured[key])
                  + " - a ceiling may only be LOWERED (D-2644); raising it is a decision, not an edit")
        print("  a config value read with a code default has no home in config: DECLARE the key and read it "
              "loudly (pipeline/pipeline_paths.required), or stop reading it (D-2644/D-2982).")
        return EXIT_DRIFT

    if grew and by_rail:
        print("FAIL " + PREFIX + ": the undeclared-default debt GREW - " + line)
        for key in grew:
            print("  !!  " + key + ": declared " + str(before[key]) + " -> measured " + str(measured[key])
                  + " - a ceiling may only be LOWERED (D-2644); raising it is a decision, not an edit")
        print("  a config value read with a code default has no home in config: DECLARE the key and read it "
              "loudly, or stop reading it (D-2644).")
        return EXIT_DRIFT

    if changed or paid:
        if not record:
            print("owner-owed (loud, NOT fatal - BUG-457): the declared ceiling is stale - " + line)
            for key in changed:
                print("  ->  " + key + ": " + str(before[key]) + " -> " + str(measured[key])
                      + " (NOT recorded: a health check is read-only - BUG-660; re-run with --record to "
                      "re-record in config/derivations.yaml#config_reads.ceiling_changed)")
            if paid:
                print("  ->  debt PAID since the last receipt (" + str(len(paid)) + " key(s) no longer "
                      "shadowed): " + ", ".join(paid[:24]) + (" ..." if len(paid) > 24 else ""))
            return EXIT_OWED
        record_ceiling(measured, before)
        write_receipt(measured, shadowed, undeclared, sites, files, coverage, coverage_id)
        print("owner-owed (loud, NOT fatal - BUG-457): the declared ceiling was stale - " + line)
        for key in changed:
            print("  ->  " + key + ": " + str(before[key]) + " -> " + str(measured[key])
                  + " (recorded in config/derivations.yaml#config_reads.ceiling_changed)")
        if not by_rail:
            print("  (first measurement by the RAIL: the probe's number was a claim, so the rail replaced it in "
                  "either direction - D-2642. Shrink-only applies from the next run on.)")
        return EXIT_OWED

    if not receipt:
        print("owner-owed (loud, NOT fatal - BUG-457): no measured receipt yet - " + line)
        print("  ->  the debt is a SET (D-2982), so the first measurement of the set is an owner-owed act: "
              "re-run with --record to record " + str(RECEIPT.relative_to(ROOT)))
        return EXIT_OWED

    print("ok " + PREFIX + ": " + line + " - within the declared shrink-only ceiling " + str(before)
          + ", and the measured KEY SET equals the receipt (" + str(len(previous_keys)) + " key(s), "
          + str(previous_coverage_ids(receipt, coverage_id)) + ")")
    return EXIT_CLEAN


def previous_coverage_ids(receipt: Mapping[str, Any], coverage_id: str) -> str:
    """A one-line statement of the coverage the receipt was taken under (same fingerprint = comparable)."""
    taken = str((receipt.get("coverage") or {}).get("fingerprint") or "?")
    return "coverage " + taken + ("" if taken == coverage_id else " != " + coverage_id)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
