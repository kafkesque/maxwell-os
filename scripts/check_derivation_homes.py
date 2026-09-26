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
     decides it must fail loudly rather than quietly.
SCOPE (stated, because an unstated scope reads as coverage): this rail does NOT prove the home is the only
WRITER of the stored value and it does not re-derive values - that is each row's parity rail. It proves the
ONE-HOME property, which is what the class needed.

TRI-STATE (BUG-457): 0 clean | 1 drift | 2 owner-owed (non-homed rows BELOW the declared shrink-only ceiling).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
PREFIX = "check-derivation-homes"
REGISTRY = ROOT / "config" / "derivations.yaml"
EXIT_CLEAN, EXIT_DRIFT, EXIT_OWED = 0, 1, 2
STATUSES: tuple[str, ...] = ("homed", "orphan_magic_threshold", "dead_but_read", "declared_but_empty")
NO_HOME_STATUSES: tuple[str, ...] = ("dead_but_read", "declared_but_empty")


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
            out[path.relative_to(ROOT).as_posix()] = path.read_text(encoding="utf-8", errors="replace")
    return out


def check_rows(rows: list[dict], sources: dict[str, str]) -> tuple[list[str], int]:
    """Join every registry row to reality. Returns (problems, non_homed_count)."""
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
    sources = sources_under(roots)
    problems, non_homed = check_rows(rows, sources)
    homed = len(rows) - non_homed
    line = (str(len(rows)) + " registered derivation(s) over " + str(len(sources)) + " module(s): " + str(homed)
            + " homed, " + str(non_homed) + " not homed (declared ceiling " + str(ceiling) + ", shrink-only)")
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
    print("ok " + PREFIX + ": every registered home exists, is UNIQUE, and no writer appeared where home is null "
          "- " + line)
    return EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
