#!/usr/bin/env python3
"""scripts/check_retired_names.py — the RETIRED-NAME rail (D-2995, closes BUG-776).

WHY. A retirement is not a debt. D-2994/T-107 removed `borp_score` from the three SERVING surfaces (the
wire an agent reads) and proved it from the payload's own AST keys. The MACHINE kept reading it: a rank
clause fell back to it when a gate was off, two SELECTs pulled it into a graph payload, a monitor averaged
it into a metric that could never move, and an evaluator formatted it into a prompt line. A wire-only
retirement leaves the machine's own view false wherever the degraded path is taken, and the register's
`why` ("nothing writes it") was itself contradicted by the S6 INSERT default that fabricated the 0.0.

WHAT THIS RAIL ASSERTS (both directions, because one direction is satisfiable by an empty registry):
  * a file that NAMES a retired name and is NOT declared in config/retired_names.yaml -> FATAL
  * a DECLARED file that no longer names it (or no longer exists)                  -> FATAL (stale)
  The second direction is the one that matters later: it forbids an allowance outliving its reason — the
  D-2987/INV-12 rule that a completed word is joined in BOTH directions.

ONE HOME (D-2642). What counts as a REFERENCE is NOT restated here: the rule has ONE implementation, the
one the anti-resurrection rail already uses and tests (`scripts/check_revoked_references.py::python_refs` —
an inline string, an identifier, an attribute or a keyword name IS a reference; a COMMENT and a DOCSTRING
are archaeology and are not). A second implementation would be a rival definition of the same rule (the
BUG-499/BUG-502 class that D-2646 exists to find).

EXIT: 0 clean | 1 a retired name is read by undeclared code, or an allowance is stale | 2 the registry
cannot be read (a rail that cannot see its own subject must never report clean — BUG-457).

Usage: python3 scripts/check_retired_names.py [--selftest] [--list]
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "config" / "retired_names.yaml"
PREFIX = "check-retired-names"
EXIT_CLEAN = 0
EXIT_DEFECT = 1
EXIT_UNRESOLVABLE = 2

sys.path.insert(0, str(ROOT / "scripts"))
from check_revoked_references import build_patterns, python_refs  # noqa: E402  D-2642: the rule has ONE home

#: A RESERVED fixture name: the controls must exercise the rail WITHOUT naming its live subject (F1 rule
#: inherited from check_revoked_references — a rail's own controls must not become a reference to it).
FIXTURE_NAME = "fixture_retired_name_zz"


def declared(doc: dict, key: str, where: str) -> object:
    """Read a declared key or FAIL CLOSED — an absent declaration is the error, never a default (D-2644)."""
    if key not in doc or doc[key] is None:
        raise SystemExit(f"FAIL {PREFIX}: {where} declares no '{key}' — a default here would be undeclared")
    return doc[key]


def python_files(root: Path, scan_roots: list[str], scan_files: list[str]) -> list[Path]:
    """Every scannable .py under the declared roots plus the declared single files (no __pycache__)."""
    found: list[Path] = []
    for rel in scan_roots:
        base = root / rel
        if not base.is_dir():
            raise SystemExit(f"FAIL {PREFIX}: declared scan_root '{rel}' is not a directory")
        found.extend(sorted(p for p in base.rglob("*.py") if "__pycache__" not in p.parts))
    for rel in scan_files:
        path = root / rel
        if not path.is_file():
            raise SystemExit(f"FAIL {PREFIX}: declared scan_file '{rel}' does not exist")
        found.append(path)
    return found


def scan_one(name: str, root: Path, scan_roots: list[str], scan_files: list[str]) -> dict[str, list[int]]:
    """Return {relative path: [lineno, ...]} for every CODE reference to `name` (comments/docstrings skipped)."""
    pats = build_patterns([name])
    refs: dict[str, list[int]] = {}
    for path in python_files(root, scan_roots, scan_files):
        hits = python_refs(path, pats)
        if not hits:
            continue
        rel = str(path.relative_to(root))
        if any(lineno < 0 for lineno, _ in hits):
            raise SystemExit(f"FAIL {PREFIX}: {rel} does not parse — an unreadable file is not a clean one (C16)")
        refs[rel] = sorted({lineno for lineno, _ in hits})
    return refs


def join_names(registry: dict, root: Path) -> tuple[list[str], list[str], list[str]]:
    """The both-directions join. Returns (undeclared, stale, report lines)."""
    scan_roots = [str(x) for x in declared(registry, "scan_roots", "config/retired_names.yaml")]
    scan_files = [str(x) for x in declared(registry, "scan_files", "config/retired_names.yaml")]
    retired = declared(registry, "retired", "config/retired_names.yaml")
    if not isinstance(retired, dict) or not retired:
        raise SystemExit(f"FAIL {PREFIX}: 'retired' must be a non-empty mapping — an empty registry is not a clean one")
    undeclared: list[str] = []
    stale: list[str] = []
    report: list[str] = []
    for name, spec in sorted(retired.items()):
        if not isinstance(spec, dict):
            raise SystemExit(f"FAIL {PREFIX}: retired.{name} must be a mapping of word/decision/reason/may_name")
        for key in ("word", "decision", "reason", "may_name"):
            declared(spec, key, f"config/retired_names.yaml#retired.{name}")
        refs = scan_one(str(name), root, scan_roots, scan_files)
        allowed: dict[str, str] = {}
        for entry in spec["may_name"]:
            if not isinstance(entry, dict) or "path" not in entry or "why" not in entry:
                raise SystemExit(f"FAIL {PREFIX}: retired.{name}.may_name entries need BOTH 'path' and 'why'")
            allowed[str(entry["path"])] = str(entry["why"])
        for path in sorted(refs):
            if path not in allowed:
                undeclared.append(f"{name} named by {path}:{refs[path]} — not declared in config/retired_names.yaml")
        for path, why in sorted(allowed.items()):
            if path not in refs:
                stale.append(f"{name}: allowance for {path} is STALE — the file no longer names it ({why[:60]}...)")
        report.append(
            f"  {name}: word={spec['word']} decision={spec['decision']} "
            f"| naming files {len(refs)}/allowances {len(allowed)}"
        )
        for path in sorted(refs):
            report.append(f"      names it: {path}:{refs[path]}" + ("" if path in allowed else "   <-- UNDECLARED"))
    return undeclared, stale, report


def controls() -> list[tuple[str, bool]]:
    """Known-answer controls. A guardrail never seen failing is not a guardrail (BUG-492)."""
    pats = build_patterns([FIXTURE_NAME])
    results: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "pipeline").mkdir()
        # (a) an INLINE STRING reference in an undeclared file must be SEEN (a reader is a reference)
        (root / "pipeline" / "reader.py").write_text(f'SQL = "SELECT {FIXTURE_NAME} FROM fbs"\n', encoding="utf-8")
        refs = scan_one(FIXTURE_NAME, root, ["pipeline"], [])
        results.append(("an_inline_string_reference_is_seen", "pipeline/reader.py" in refs))
        # (b) an IDENTIFIER reference must be SEEN too — a declaration shape no string scan can see
        (root / "pipeline" / "reader.py").write_text(
            f"{FIXTURE_NAME}: float = 1.0\n", encoding="utf-8"
        )
        refs = scan_one(FIXTURE_NAME, root, ["pipeline"], [])
        results.append(("a_bare_identifier_reference_is_seen", "pipeline/reader.py" in refs))
        # (c) a COMMENT is archaeology and must NOT be a reference
        (root / "pipeline" / "reader.py").write_text(f"# the retired {FIXTURE_NAME} used to live here\nX = 1\n", encoding="utf-8")
        results.append(("a_comment_is_not_a_reference", scan_one(FIXTURE_NAME, root, ["pipeline"], []) == {}))
        # (d) a DOCSTRING is archaeology and must NOT be a reference
        (root / "pipeline" / "reader.py").write_text(f'"""why {FIXTURE_NAME} left this module."""\nX = 1\n', encoding="utf-8")
        results.append(("a_docstring_is_not_a_reference", scan_one(FIXTURE_NAME, root, ["pipeline"], []) == {}))
        # (e) an unparsable file must be REPORTED, never silently clean
        (root / "pipeline" / "reader.py").write_text("def broken(:\n", encoding="utf-8")
        try:
            scan_one(FIXTURE_NAME, root, ["pipeline"], [])
            results.append(("an_unparsable_file_is_reported", False))
        except SystemExit:
            results.append(("an_unparsable_file_is_reported", True))
        # (f) the both-directions join: an undeclared reader fires AND a stale allowance fires
        (root / "pipeline" / "reader.py").write_text(f'S = "{FIXTURE_NAME}"\n', encoding="utf-8")
        (root / "pipeline" / "quiet.py").write_text("S = 1\n", encoding="utf-8")
        registry = {
            "scan_roots": ["pipeline"],
            "scan_files": [],
            "retired": {
                FIXTURE_NAME: {
                    "word": "retire",
                    "decision": "D-0000",
                    "reason": "control fixture",
                    "may_name": [
                        {"path": "pipeline/reader.py", "why": "declared allowance (control)"},
                        {"path": "pipeline/quiet.py", "why": "STALE allowance (control)"},
                    ],
                }
            },
        }
        undeclared, stale, _ = join_names(registry, root)
        results.append(("a_declared_allowance_does_not_fire", undeclared == []))
        results.append(("a_stale_allowance_fires", len(stale) == 1 and "quiet.py" in stale[0]))
        # (g) the reverse of (f): the SAME reference from an UNDECLARED file must fire
        registry["retired"][FIXTURE_NAME]["may_name"] = [{"path": "pipeline/quiet.py", "why": "control"}]
        undeclared, _, _ = join_names(registry, root)
        results.append(("an_undeclared_reader_fires", len(undeclared) == 1 and "reader.py" in undeclared[0]))
        # (h) the shared reference rule resolves its own controls (comments skipped, strings seen)
        results.append(("the_shared_rule_is_resolved", pats[0][1].search(FIXTURE_NAME) is not None))
    return results


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="the retired-name rail (D-2995)")
    parser.add_argument("--selftest", action="store_true", help="run the known-answer controls")
    parser.add_argument("--list", action="store_true", help="print the join without judging it")
    args = parser.parse_args(argv)

    if args.selftest:
        ran = controls()
        for label, ok in ran:
            print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        failures = [label for label, ok in ran if not ok]
        if failures:
            print(f"FAIL {PREFIX} --selftest: {len(failures)} control(s) did not fire: {', '.join(failures)}")
            return EXIT_DEFECT
        print(f"OK {PREFIX} --selftest: {len(ran)}/{len(ran)} controls fire")
        return EXIT_CLEAN

    if not REGISTRY.is_file():
        print(f"FAIL {PREFIX}: {REGISTRY.relative_to(ROOT)} is absent — the registry is the rail's SUBJECT (BUG-457)")
        return EXIT_UNRESOLVABLE
    try:
        registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8")) or {}
        undeclared, stale, report = join_names(registry, ROOT)
    except SystemExit as exc:
        print(str(exc))
        return EXIT_UNRESOLVABLE

    for line in report:
        print(line)
    if args.list:
        return EXIT_CLEAN
    if undeclared or stale:
        for line in undeclared:
            print(f"DEFECT {PREFIX}: {line}")
        for line in stale:
            print(f"DEFECT {PREFIX}: {line}")
        print(
            f"FAIL {PREFIX}: {len(undeclared)} undeclared reader(s), {len(stale)} stale allowance(s) — a "
            "retired name is read by nothing, or its allowance is declared WITH a reason (both directions)"
        )
        return EXIT_DEFECT
    print(f"OK {PREFIX}: every retired name is named only by its declared allowances (both directions)")
    return EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
