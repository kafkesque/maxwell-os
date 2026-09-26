#!/usr/bin/env python3
"""check_encoding_homes.py - the rail that DETECTS a second implementation of the decode rule (D-2646/D-2644).

MEASURED 2026-09-26: "how do I decode this artifact's bytes" had ZERO home and NINE copies - five byte-identical
`DECODE_ORDER = ("utf-8-sig","utf-8","mac_roman","cp1252")` literals, an inline copy in normalize_owner_workbook.py,
the same tuple in ingest_panel_column.py, `ENCODINGS = ("utf-8","latin-1")` in verify_anchor_family_registry.py, an
inline ("utf-8","cp1252","latin-1") in scan_review_artifacts.py, and a bare open(..., encoding="cp1252") in
audit_human_verification.py. Three vocabularies, one rule - and because every single-byte codec "succeeds", two
modules reading ONE artifact could decode it differently and NEITHER would raise (0xD1 is an em dash in MacRoman
and an N-tilde in cp1252 - BUG-511). The home is scripts/lib/artifact_encoding.py; this rail makes the invariant
MACHINE-DETECTED instead of remembered: an invariant no machine enforces is a comment (BUG-492).

It looks for an AST string CONSTANT equal to a non-UTF-8 codec name (a tuple element, an `encoding=` argument, a
.decode() argument). It does NOT grep: a comment deciding nothing is invisible to an AST, and `encoding="utf-8"` is
the FORMAT default (a YAML/JSON is UTF-8 by spec), not a guess about an artifact.

TRI-STATE (BUG-457): 0 clean | 1 a NEW copy appeared, or the declared ceiling was widened (shrink-only, D-2642) |
2 declared debt only (the allow-list: loud, NOT fatal). CLI: --selftest | --check | --list (measure, no verdict).
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "config" / "encoding_homes.yaml"
LABELS = ("mac_roman", "macroman", "cp1252", "latin-1", "latin_1", "iso-8859-1", "iso8859-1", "utf-8-sig", "utf8-sig")
PREFIX = "encoding-homes"
EXIT_CLEAN, EXIT_DRIFT, EXIT_OWED = 0, 1, 2


def findings_in(source: str) -> list[tuple[str, int]]:
    """Every non-UTF-8 codec name a module names for itself, as (label, line). A comment is invisible (AST)."""
    out = {(n.value.strip().lower(), n.lineno) for n in ast.walk(ast.parse(source))
           if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.strip().lower() in LABELS}
    return sorted(out)


def scan(cfg: dict, repo: Path = REPO) -> tuple[dict[str, list[tuple[str, int]]], list[str]]:
    """{relative path: findings} for every module outside the home and the exempt directories."""
    exempt = [repo / str(e) for e in cfg.get("exempt") or []]
    found, broken = {}, []
    for root in cfg.get("scan_roots") or []:
        for path in sorted((repo / str(root)).rglob("*.py")):
            if "__pycache__" in path.parts or any(path == e or e in path.parents for e in exempt):
                continue
            try:
                hits = findings_in(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError) as exc:
                broken.append(path.relative_to(repo).as_posix() + ": " + type(exc).__name__); continue
            if hits:
                found[path.relative_to(repo).as_posix()] = hits
    return found, broken


def verdict(found: dict, allowed: dict[str, set[str]], ceiling: int) -> tuple[int, list[str], list[str]]:
    """An undeclared copy is a DEFECT; declared debt above the declared ceiling is DRIFT (a ceiling shrinks only)."""
    unknown, debt = [], []
    for rel, hits in sorted(found.items()):
        labels = {label for label, _ in hits}
        if rel not in allowed:
            unknown.append(rel + " names " + ", ".join(sorted(labels)) + " with no allow entry")
        elif not labels <= allowed[rel]:
            unknown.append(rel + " names " + ", ".join(sorted(labels - allowed[rel])) + " beyond its allow entry")
        else:
            debt.append(rel)
    if unknown:
        return EXIT_DRIFT, debt, unknown
    if len(debt) > ceiling:
        return EXIT_DRIFT, debt, ["the declared ceiling is " + str(ceiling) + " but " + str(len(debt))
                                 + " module(s) still carry the rule - a ceiling is SHRINK-ONLY (D-2642)"]
    return (EXIT_OWED if debt else EXIT_CLEAN), debt, []


def load(repo: Path = REPO) -> dict:
    """The policy: which modules may still carry the rule, and how much debt that is allowed to be."""
    return yaml.safe_load((repo / "config" / "encoding_homes.yaml").read_text(encoding="utf-8"))


def owed(cfg: dict) -> dict[str, set[str]]:
    return {str(e["path"]): {str(x) for x in e.get("labels") or []} for e in cfg.get("allow") or []}


def controls() -> list[tuple[str, bool]]:
    """Known-answer controls (BUG-492): the detector must be SEEN to fire, and SEEN to stay quiet, on known cases."""
    allowed, ceiling = {"scripts/legacy.py": {"mac_roman", "cp1252"}}, 2
    return [
        ("a local DECODE_ORDER naming mac_roman IS flagged",
         findings_in('DECODE_ORDER = ("utf-8-sig", "utf-8", "mac_roman", "cp1252")\n') == [("cp1252", 1), ("mac_roman", 1), ("utf-8-sig", 1)]),
        ("a hardcoded open(..., encoding=\"cp1252\") IS flagged",
         findings_in('open(p, encoding="cp1252")\n') == [("cp1252", 1)]),
        ("encoding=\"utf-8\" is NOT flagged (UTF-8 is the format default, not a guess)",
         findings_in('yaml.safe_load(p.read_text(encoding="utf-8"))\n') == []),
        ("a COMMENT that mentions cp1252 is NOT flagged (a comment decides nothing - AST, not grep)",
         findings_in("# read it as cp1252 because the buglog says latin-1\nX = 1\n") == []),
        ("a module that only reads through the home is NOT flagged",
         findings_in("from lib import artifact_encoding\nartifact_encoding.open_artifact(p, REPO)\n") == []),
        ("declared debt is a DEFECT above the ceiling and OWED at or below it (shrink-only)",
         verdict({"scripts/legacy.py": [("mac_roman", 3)]}, allowed, ceiling)[0] == EXIT_OWED
         and verdict({"scripts/legacy.py": [("mac_roman", 3)]}, allowed, 0)[0] == EXIT_DRIFT),
        ("a copy with no allow entry is a DEFECT, and a NEW label on an allowed module is too",
         verdict({"scripts/new.py": [("cp1252", 1)]}, allowed, ceiling)[0] == EXIT_DRIFT
         and verdict({"scripts/legacy.py": [("utf-8-sig", 9)]}, allowed, ceiling)[0] == EXIT_DRIFT),
    ]


def main(argv: list[str]) -> int:
    """--selftest | --check | --list. Any other argument is refused (C16: an ignored argument is a silent error)."""
    ap = argparse.ArgumentParser(add_help=False)
    for flag in ("--selftest", "--check", "--list"):
        ap.add_argument(flag, action="store_true")
    args, unknown = ap.parse_known_args(argv)
    if unknown or sum([args.selftest, args.check, args.list]) != 1:
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): pass exactly ONE of --selftest | --check | --list (unknown: "
                         + str(unknown) + ")")
    if args.selftest:
        rows = controls()
        for name, ok in rows:
            print(("  ok  " if ok else "  !!  ") + name)
        failed = [n for n, ok in rows if not ok]
        if failed:
            print("FAIL " + PREFIX + ": " + str(len(failed)) + " of " + str(len(rows)) + " control(s) did not fire")
            return EXIT_DRIFT
        print("ok " + PREFIX + ": " + str(len(rows)) + "/" + str(len(rows)) + " known-answer control(s) fire")
        return EXIT_CLEAN
    cfg = load()
    found, broken = scan(cfg)
    if args.list:
        for rel, hits in sorted(found.items()):
            print("   " + rel + " : " + ", ".join(label + "@" + str(line) for label, line in hits))
        print("LIST: " + str(len(found)) + " module(s) outside the home decide a non-UTF-8 encoding")
        return EXIT_CLEAN
    code, debt, unknown = verdict(found, owed(cfg), int(cfg.get("ceiling", 0)))
    for rel in debt:
        print("  owed  " + rel + " - declared debt; repoint to " + str(cfg["home"]) + " (D-2646)")
    for rel in broken:
        print("  BAD   " + rel + " does not parse (a rail cannot certify what it cannot read)")
    for line in unknown:
        print("  DRIFT " + line)
    mark = "ok " if code == EXIT_CLEAN else ("OWED " if code == EXIT_OWED else "FAIL ")
    print(mark + PREFIX + ": debt " + str(len(debt)) + " of ceiling "
          + str(cfg.get("ceiling")) + " | unknown " + str(len(unknown)) + " | home " + str(cfg["home"]))
    return EXIT_DRIFT if broken else code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
