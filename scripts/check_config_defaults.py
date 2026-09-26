#!/usr/bin/env python3
"""check_config_defaults.py - D-2644: a config value read with a code default is an UNDECLARED value.

WHY. BUG-504's INSTANCE was one silent default in the S5 score axis (stage5.nli_model_fallback -> ""), which
would have made the verifier read an EMPTY model name with no error anywhere. The CLASS is that every
receiver.get(key, <literal>) moves a value's effective setting OUT of config and INTO code: a config miss is
not an error, it is a silent fallback. The instance was fixed; the class is COUNTED here, because a class that
is never measured grows back.

POPULATION (stated, so the number is reproducible - a count with no stated population is a rumour): every .py
under the registry scan_roots is AST-parsed. A SITE is a Call whose func is Attribute(attr="get") ROOTED at a
Name in config_reads.receivers, with a string-literal key and a SECOND argument (the default). A chained read
roots at the receiver through the chain, so cfg.get(a, {}).get(b, x) is TWO sites - the container read falls
back to {} and is counted, because an absent block silently empties everything below it. Classification is by
the key's LAST DOTTED SEGMENT: SHADOWED-DECLARED when that leaf name is a key anywhere under config_glob,
UNDECLARED otherwise. Both ceilings count DISTINCT keys, so copying a line never raises them.

RULER (D-2642: one derived value, one home). config/derivations.yaml#config_reads.ceilings IS the number and
THIS RAIL writes it, never a human transcribing a probe. While measured_by is a probe, the rail owns the number
in EITHER direction and records the change; once measured_by is the rail it may only LOWER a ceiling, and a
measurement above the declaration is drift that is NEVER written (an undeclared value must not become declared
by census).

TRI-STATE (BUG-457): 0 in sync | 1 drift (measured above the ceiling) | 2 owner-owed (the declared number was
stale - loud, NOT fatal).
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
PREFIX = "check-config-defaults"
REGISTRY = ROOT / "config" / "derivations.yaml"
RAIL_REL = "scripts/check_config_defaults.py"
# RAIL_DATE was a hardcoded "2026-09-25" that wrote a FALSE date once the rail measured on 2026-09-26. The run
# date is now DERIVED (yaml_guard.today()): a date constant is a value that can only go stale (C12/C20).
EXIT_CLEAN, EXIT_DRIFT, EXIT_OWED = 0, 1, 2
CONTROLS_KEYS = {"alpha", "beta"}

sys.path.insert(0, str(ROOT / "scripts"))
from lib import yaml_guard  # noqa: E402 - D-2648: the ONE home for "verify the bytes before writing"
from lib.write_guard import OWNED_ANY, write_document  # noqa: E402 - D-401/I1 (C6: crash-safe write)


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
        else:
            return None


def node_sites(tree: ast.AST, receivers: set[str]) -> list[str]:
    """Every leaf key read with a literal default through a declared receiver, in source order."""
    keys: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "get" or root_name(node.func.value) not in receivers:
            continue
        if len(node.args) < 2 or isinstance(node.args[0], ast.Starred):
            continue
        # MEASURED 2026-09-26 (known-answer control 5): a NON-LITERAL default is not a site. The debt
        # is a VALUE hidden in code; a fallback that is a NAME points at something already named and
        # visible to a reader, so counting it would inflate the census with honest reads (D-2644).
        try:
            ast.literal_eval(node.args[1])
        except (ValueError, SyntaxError, TypeError):
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            keys.append(first.value.split(".")[-1])
    return keys


def census(source: str, receivers: set[str], keys: set[str]) -> tuple[set[str], set[str], int]:
    """Return (shadowed_declared, undeclared, site_count) for ONE module's source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set(), set(), 0
    leaves = node_sites(tree, receivers)
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


def scan(receivers: set[str], keys: set[str], roots: list[str]) -> tuple[set[str], set[str], int, int]:
    """Walk every declared scan root; fail closed on a root that is not a directory (C16)."""
    shadowed: set[str] = set()
    undeclared: set[str] = set()
    sites = files = 0
    for rel in roots:
        d = ROOT / str(rel)
        if not d.is_dir():
            raise SystemExit("FAIL " + PREFIX + ": scan_roots names " + str(rel) + ", which is not a directory - a "
                             "scan root that silently does not exist narrows the census and still prints ok (C16)")
        for path in sorted(d.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            files += 1
            sh, un, n = census(path.read_text(encoding="utf-8", errors="replace"), receivers, keys)
            shadowed |= sh
            undeclared |= un
            sites += n
    return shadowed, undeclared, sites, files


def record_ceiling(measured: dict[str, int], previous: dict[str, int]) -> str:
    """Write the rail's OWN measurement into the registry, keeping the old number as history (D-2642)."""
    text = REGISTRY.read_text(encoding="utf-8")
    new_map = ("ceilings: {shadowed_declared: " + str(measured["shadowed_declared"]) + ", undeclared: "
               + str(measured["undeclared"]) + "}")
    # MEASURED 2026-09-26: config/derivations.yaml declares ceilings as a BLOCK mapping, so the old
    # flow-mapping-only reader refused to write and the rail could NEVER own its number in the file that
    # declares it. Refusing was correct and useless. Point at whichever shape the file actually has, and
    # when it is a block insert measured_by AFTER undeclared - inside the block it would be a key of
    # ceilings, not of config_reads (D-2642: the RAIL owns the number).
    text = re.sub(r"(?m)^(\s*)measured_by:.*$", "", text, count=1)
    text, n = re.subn(r"(?m)^  ceilings:[ \t]*\{[^}]*\}[ \t]*$", "  " + new_map, text, count=1)
    if n == 1:
        text = re.sub(r"(?m)^(  ceilings:.*)$", "  measured_by: " + RAIL_REL, text, count=1)
    else:
        shad = r"(?m)^(\s*)shadowed_declared:[ \t]*\d+[ \t]*$"
        unde = r"(?m)^(\s*)undeclared:[ \t]*\d+[ \t]*$"
        text, n1 = re.subn(shad, r"\1shadowed_declared: " + str(measured["shadowed_declared"]), text, count=1)
        text, n2 = re.subn(unde, r"\1undeclared: " + str(measured["undeclared"]) + chr(10)
                           + r"\1measured_by: " + RAIL_REL, text, count=1)
        n = 1 if (n1 == 1 and n2 == 1) else 0
    if n != 1:
        raise SystemExit("FAIL " + PREFIX + ": config_reads.ceilings is neither a block nor a flow mapping - "
                         "refusing to write a number this rail cannot point at (D-2642)")
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
    return new_map


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
    ]


def main(argv: list[str]) -> int:
    """Run the known-answer controls, or measure the census and join it to the declared ceilings."""
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
    reads = declared(registry, "config_reads", "config/derivations.yaml")
    receivers = {str(r) for r in declared(reads, "receivers", "config_reads")}
    config_glob = str(declared(reads, "config_glob", "config_reads"))
    ceilings = declared(reads, "ceilings", "config_reads")
    roots = [str(r) for r in declared(registry, "scan_roots", "config/derivations.yaml")]
    shadowed, undeclared, sites, files = scan(receivers, declared_keys(config_glob), roots)

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
    by_rail = str(reads.get("measured_by") or "").strip() == RAIL_REL
    grew = sorted(k for k in measured if measured[k] > before[k])
    if grew and by_rail:
        print("FAIL " + PREFIX + ": the undeclared-default debt GREW - " + line)
        for key in grew:
            print("  !!  " + key + ": declared " + str(before[key]) + " -> measured " + str(measured[key])
                  + " - a ceiling may only be LOWERED (D-2644); raising it is a decision, not an edit")
        print("  a config value read with a code default has no home in config: DECLARE the key and read it "
              "loudly, or stop reading it (D-2644).")
        return EXIT_DRIFT
    changed = sorted(k for k in measured if measured[k] != before[k])
    if changed:
        record_ceiling(measured, before)
        print("owner-owed (loud, NOT fatal - BUG-457): the declared ceiling was stale - " + line)
        for key in changed:
            print("  ->  " + key + ": " + str(before[key]) + " -> " + str(measured[key])
                  + " (recorded in config/derivations.yaml#config_reads.ceiling_changed)")
        if not by_rail:
            print("  (first measurement by the RAIL: the probe's number was a claim, so the rail replaced it in "
                  "either direction - D-2642. Shrink-only applies from the next run on.)")
        return EXIT_OWED
    print("ok " + PREFIX + ": " + line + " - within the declared shrink-only ceiling " + str(before))
    return EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
